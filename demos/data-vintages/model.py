#!/usr/bin/env python3
"""Point-in-time replenishment model for the frozen synthetic case.

Run as: python model.py --output DIR

The model reads only the frozen case's raw inputs. It does not read or import
the independent validator. Results are written as finite JSON plus a short
human-readable report.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CASE_ROOT = Path(__file__).resolve().parents[1]

from modeling.data_analysis import asof_join  # noqa: E402
from modeling.optimize import solve_milp  # noqa: E402


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"Timestamp must include a timezone: {value}")
    return parsed.astimezone(timezone.utc)


def finite_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{field} must be finite")
    return result


def run_join(queries: list[dict], versions: list[dict]) -> dict:
    return asof_join(
        queries,
        versions,
        on=["day", "sku"],
        decision_time="cutoff",
        available_time="available_at",
        allow_exact_matches=False,
    )


def allocate(forecast_a: float, forecast_b: float, capacity: int, shortage_a: float,
             shortage_b: float, overage_a: float, overage_b: float) -> dict:
    """Minimize declared asymmetric loss with integer order quantities."""
    # Variables: qA, qB, shortageA, shortageB, overageA, overageB.
    # Slack inequalities represent max(forecast - order, 0) and
    # max(order - forecast, 0); nonnegative costs make them tight at optimum.
    result = solve_milp(
        [0.0, 0.0, shortage_a, shortage_b, overage_a, overage_b],
        A_ub=[
            [1, 1, 0, 0, 0, 0],
            [-1, 0, -1, 0, 0, 0],
            [0, -1, 0, -1, 0, 0],
            [1, 0, 0, 0, -1, 0],
            [0, 1, 0, 0, 0, -1],
        ],
        b_ub=[capacity, -forecast_a, -forecast_b, forecast_a, forecast_b],
        bounds=[(0, capacity), (0, capacity), (0, None), (0, None),
                (0, None), (0, None)],
        integrality=[1, 1, 0, 0, 0, 0],
    )
    if not result.get("success") or not result.get("proved_optimal"):
        raise RuntimeError(f"MILP did not prove optimality: {result}")
    qa, qb = (int(round(result["x"][i])) for i in (0, 1))
    if qa + qb > capacity or qa < 0 or qb < 0:
        raise RuntimeError("MILP returned an infeasible integer order")
    forecast_loss = loss(qa, qb, forecast_a, forecast_b,
                         shortage_a, shortage_b, overage_a, overage_b)
    if not math.isclose(forecast_loss, result["objective"], rel_tol=1e-8, abs_tol=1e-7):
        raise RuntimeError("Recomputed objective differs from MILP objective")
    return {"q_A": qa, "q_B": qb, "total_order": qa + qb,
            "capacity": capacity, "forecast_loss": forecast_loss,
            "solver": "HiGHS MILP", "solver_proved_optimal": True}


def loss(q_a: int, q_b: int, f_a: float, f_b: float,
         shortage_a: float, shortage_b: float,
         overage_a: float, overage_b: float) -> float:
    return (shortage_a * max(f_a - q_a, 0.0)
            + shortage_b * max(f_b - q_b, 0.0)
            + overage_a * max(q_a - f_a, 0.0)
            + overage_b * max(q_b - f_b, 0.0))


def days_with_decisions(queries: list[dict], versions: list[dict], joined: dict,
                        plan: dict) -> tuple[list[dict], dict]:
    counts = dict(joined["counts"])
    query_days = {q["day"] for q in queries}
    mapping_by_index = {m["query_index"]: m for m in joined["mappings"]}
    sku_by_day = {day: {} for day in query_days}
    for idx, q in enumerate(queries):
        sku_by_day[q["day"]][q["sku"]] = {
            **mapping_by_index[idx], "forecast": (
                versions[mapping_by_index[idx]["matched_version_index"]]["forecast"]
                if mapping_by_index[idx]["matched_version_index"] is not None else None
            )
        }
    days = []
    for day in sorted(query_days):
        forecasts = {}
        status_by_sku = {}
        version_by_sku = {}
        for sku in ("A", "B"):
            item = sku_by_day[day].get(sku)
            if item is None:
                status_by_sku[sku] = "query_missing"
                forecasts[sku] = None
                version_by_sku[sku] = None
            else:
                status_by_sku[sku] = item["status"]
                forecasts[sku] = (None if item["status"] != "matched"
                                  else finite_number(item["forecast"], "forecast"))
                version_by_sku[sku] = item["matched_version_index"]
        actionable = all(forecasts[s] is not None for s in ("A", "B"))
        row = {"day": day, "cutoff": next(q["cutoff"] for q in queries if q["day"] == day),
               "forecasts": forecasts, "query_status": status_by_sku,
               "matched_version_indices": version_by_sku,
               "actionable": actionable}
        if actionable:
            decision = allocate(
                forecasts["A"], forecasts["B"], plan["capacity_units_per_day"],
                plan["shortage_penalty"]["A"], plan["shortage_penalty"]["B"],
                plan["overage_penalty"]["A"], plan["overage_penalty"]["B"],
            )
            row["status"] = "actionable"
            row["orders"] = {"A": decision["q_A"], "B": decision["q_B"]}
            row["forecast_loss"] = decision["forecast_loss"]
            row["capacity"] = decision["capacity"]
            row["solver_proved_optimal"] = decision["solver_proved_optimal"]
            row["abstention_reason"] = None
        else:
            row["status"] = "abstain"
            row["orders"] = None
            row["forecast_loss"] = None
            row["capacity"] = plan["capacity_units_per_day"]
            row["solver_proved_optimal"] = None
            unresolved = [s for s in ("A", "B") if forecasts[s] is None]
            row["abstention_reason"] = {
                "message": "At least one query has no unique, known-available forecast at cutoff.",
                "unresolved_skus": unresolved,
                "recovery_conditions": recovery_conditions(day, unresolved, status_by_sku),
            }
        days.append(row)
    return days, counts


def recovery_conditions(day: str, skus: list[str], statuses: dict) -> list[str]:
    needed = []
    for sku in skus:
        status = statuses[sku]
        if status == "unknown_availability":
            needed.append(f"A complete, timestamped availability ledger for {day}/{sku}.")
        elif status == "ambiguous_latest":
            needed.append(f"A unique authoritative release or tie-break record for {day}/{sku}.")
        elif status == "not_available":
            needed.append(f"A forecast version with verified availability before the cutoff for {day}/{sku}.")
        else:
            needed.append(f"A uniquely identified version with verified availability before cutoff for {day}/{sku}.")
    return needed


def final_snapshot_predictions(queries: list[dict], versions: list[dict]) -> tuple[dict[str, dict], dict[str, int]]:
    """Use the latest known release per target, ignoring its decision-time eligibility."""
    grouped: dict[tuple[str, str], list[tuple[int, datetime]]] = defaultdict(list)
    for index, version in enumerate(versions):
        if version.get("available_at") is not None:
            grouped[(version["day"], version["sku"])].append(
                (index, utc(version["available_at"]))
            )
    final: dict[str, dict] = defaultdict(dict)
    status_counts: Counter = Counter()
    for query in queries:
        rows = grouped.get((query["day"], query["sku"]), [])
        if not rows:
            final[query["day"]][query["sku"]] = {"status": "no_known_release", "forecast": None,
                                                   "version_index": None}
            status_counts["no_known_release"] += 1
            continue
        latest_time = max(time for _, time in rows)
        latest = [i for i, time in rows if time == latest_time]
        if len(latest) != 1:
            final[query["day"]][query["sku"]] = {"status": "ambiguous_latest", "forecast": None,
                                                   "version_index": None}
            status_counts["ambiguous_latest"] += 1
        else:
            index = latest[0]
            final[query["day"]][query["sku"]] = {
                "status": "latest_known_release", "forecast": finite_number(versions[index]["forecast"], "forecast"),
                "version_index": index,
            }
            status_counts["latest_known_release"] += 1
    return final, dict(status_counts)


def realized_metrics(name: str, forecast_rows: dict[str, dict], orders: dict[str, dict],
                     outcomes: list[dict], days: list[str], plan: dict) -> dict:
    truth = defaultdict(dict)
    for row in outcomes:
        truth[row["day"]][row["sku"]] = finite_number(row["demand"], "demand")
    daily = []
    absolute_errors = []
    for day in days:
        forecast = {sku: forecast_rows[day][sku]["forecast"] for sku in ("A", "B")}
        q_a, q_b = orders[day]["q_A"], orders[day]["q_B"]
        demand = {sku: truth[day][sku] for sku in ("A", "B")}
        for sku in ("A", "B"):
            absolute_errors.append(abs(forecast[sku] - demand[sku]))
        short_a, over_a = max(demand["A"] - q_a, 0.0), max(q_a - demand["A"], 0.0)
        short_b, over_b = max(demand["B"] - q_b, 0.0), max(q_b - demand["B"], 0.0)
        realized_cost = (plan["shortage_penalty"]["A"] * short_a
                         + plan["shortage_penalty"]["B"] * short_b
                         + plan["overage_penalty"]["A"] * over_a
                         + plan["overage_penalty"]["B"] * over_b)
        forecast_cost = loss(q_a, q_b, forecast["A"], forecast["B"],
                             plan["shortage_penalty"]["A"], plan["shortage_penalty"]["B"],
                             plan["overage_penalty"]["A"], plan["overage_penalty"]["B"])
        daily.append({
            "day": day,
            "forecast": forecast,
            "orders": {"A": q_a, "B": q_b},
            "forecast_cost": forecast_cost,
            "realized_cost": realized_cost,
            "shortage": {"A": short_a, "B": short_b, "total": short_a + short_b},
            "overage": {"A": over_a, "B": over_b, "total": over_a + over_b},
            "demand": demand,
        })
    return {
        "method": name,
        "eligible_at_cutoff_under_declared_metadata": name != "invalid_final_snapshot",
        "evaluation_days": len(days), "target_count": len(absolute_errors),
        "mae": sum(absolute_errors) / len(absolute_errors),
        "absolute_error_sum": sum(absolute_errors),
        "forecast_cost": sum(row["forecast_cost"] for row in daily),
        "realized_cost": sum(row["realized_cost"] for row in daily),
        "shortage": sum(row["shortage"]["total"] for row in daily),
        "overage": sum(row["overage"]["total"] for row in daily),
        "days": daily,
        "interpretation": (
            "Retrospective upper-information comparison; uses releases published after the order cutoff and is not deployable."
            if name == "invalid_final_snapshot" else
            "Declared cost units are ex-post diagnostics, not proven future-best orders or real monetary returns."
        ),
    }


def make_report(results: dict) -> str:
    lines = [
        "# Information-Time Replenishment Case",
        "",
        "This synthetic exercise matches each fixed query to the latest uniquely declared forecast available strictly before its 08:00 UTC cutoff. A day receives an automated order only when both SKU forecasts are supported. Orders minimize the stated point-forecast loss under a 40-unit capacity using integer quantities.",
        "",
        f"The as-of mapping covered {results['query_coverage']['matched']} of {results['query_coverage']['query_rows']} queries. {results['daily_actionable_days']} of {results['daily_decision_days']} dates were actionable; unresolved dates remain in the daily table with the evidence needed for recovery.",
        "",
        "## Common eight-day evaluation",
        "",
        "All methods are evaluated on the same first eight dates and 16 SKU targets. Forecast MAE uses the submitted forecasts; realized shortage, overage, and cost use observed demand and the method's orders. Costs are declared units, not money.",
        "",
        "| Method | MAE | Absolute error sum | Realized cost | Shortage units | Overage units | Eligible at cutoff |",
        "|---|---:|---:|---:|---:|---:|:---:|",
    ]
    for result in results["comparison"].values():
        lines.append(
            f"| {result['method']} | {result['mae']:.4f} | {result['absolute_error_sum']:.3f} | {result['realized_cost']:.3f} | {result['shortage']:.3f} | {result['overage']:.3f} | {'yes' if result['eligible_at_cutoff_under_declared_metadata'] else 'no'} |"
        )
    lines += [
        "",
        "The final-snapshot row intentionally uses information released after the decision cutoff. It is an invalid retrospective comparison, not an alternative operational policy. None of the realized costs establishes the best future policy or real-world savings.",
        "",
        "## Daily decisions and unresolved evidence",
        "",
        "| Date | A forecast | B forecast | Orders A / B | State |",
        "|---|---:|---:|---|---|",
    ]
    for row in results["daily_actions"]:
        forecasts = row["forecasts"]
        show = lambda x: "unknown" if x is None else f"{x:g}"
        orders = row["orders"]
        order_text = "unresolved" if orders is None else f"{orders['A']} / {orders['B']}"
        states = "; ".join(f"{sku}: {state}" for sku, state in row["query_status"].items())
        lines.append(f"| {row['day']} | {show(forecasts['A'])} | {show(forecasts['B'])} | {order_text} | {states} |")
    lines += [
        "",
        "The fixed baseline has lower MAE and realized cost than the declared as-of forecasts on this constructed sample. Time eligibility corrects a false performance claim; it does not make a poor forecast useful. The zero-error final snapshot cannot justify replacing the baseline.",
        "",
        "January 9 needs a documented release time for A and an authoritative resolution of the simultaneous B releases. January 10 needs a forecast available before its cutoff for A. Until those conditions are met, the automated order remains unresolved; an operational fallback is outside this task.",
        "",
        "## Limits",
        "",
        "Availability timestamps are declared synthetic metadata; this calculation cannot establish their real provenance or completeness. The exercise does not estimate forecast uncertainty, establish external validity, or demonstrate forecasting skill beyond this fixed eight-day sample. It is not a blind generalization test or an award-quality competition paper.",
        "",
        "A future-value perturbation check is included as a model-side information-boundary check only. It is not an independent validator; the independent timestamp scan and exact enumeration are handled separately.",
        "",
    ]
    return "\n".join(lines)


def build_results() -> dict:
    raw = CASE_ROOT / "raw"
    queries = read_json(raw / "data" / "queries.json")
    versions = read_json(raw / "data" / "versions.json")
    outcomes = read_json(raw / "data" / "outcomes.json")
    plan = read_json(raw / "data" / "plan.json")
    # Read the frozen problem statement as part of the task's declared input set.
    problem_text = (raw / "problem" / "problem.md").read_text(encoding="utf-8")
    if not problem_text.strip():
        raise ValueError("Frozen problem statement is empty")
    if len(queries) != 20 or len(versions) != 38 or len(outcomes) != 20:
        raise ValueError("Frozen input row counts differ from the registered task")

    joined = run_join(queries, versions)
    decisions, coverage = days_with_decisions(queries, versions, joined, plan)
    actionable = {row["day"]: row for row in decisions if row["actionable"]}
    common_days = plan["common_evaluation_days"]
    if any(day not in actionable for day in common_days):
        raise ValueError("A declared common evaluation date lacks a current as-of decision")

    baseline_forecasts = {day: {sku: {"forecast": float(plan["baseline_forecast"][sku]),
                                     "status": "predeclared_baseline", "version_index": None}
                                for sku in ("A", "B")} for day in common_days}
    baseline_orders = {day: {"q_A": int(plan["baseline_forecast"]["A"]),
                             "q_B": int(plan["baseline_forecast"]["B"])} for day in common_days}
    for day, order in baseline_orders.items():
        if order["q_A"] + order["q_B"] > plan["capacity_units_per_day"]:
            raise ValueError("Predeclared baseline exceeds capacity")

    current_forecasts = {day: {sku: {"forecast": actionable[day]["forecasts"][sku],
                                     "status": "matched",
                                     "version_index": actionable[day]["matched_version_indices"][sku]}
                              for sku in ("A", "B")} for day in common_days}
    current_orders = {day: {"q_A": actionable[day]["orders"]["A"],
                            "q_B": actionable[day]["orders"]["B"]} for day in common_days}

    final_by_day, final_status_counts = final_snapshot_predictions(queries, versions)
    final_forecasts = {day: final_by_day[day] for day in common_days}
    final_orders = {}
    for day in common_days:
        if any(final_forecasts[day][sku]["forecast"] is None for sku in ("A", "B")):
            raise ValueError("Final snapshot does not resolve a common evaluation date")
        chosen = allocate(final_forecasts[day]["A"]["forecast"], final_forecasts[day]["B"]["forecast"],
                          plan["capacity_units_per_day"], plan["shortage_penalty"]["A"],
                          plan["shortage_penalty"]["B"], plan["overage_penalty"]["A"],
                          plan["overage_penalty"]["B"])
        final_orders[day] = {"q_A": chosen["q_A"], "q_B": chosen["q_B"]}

    evaluation = {
        "asof": realized_metrics("declared_asof", current_forecasts, current_orders, outcomes, common_days, plan),
        "baseline": realized_metrics("baseline_20_20", baseline_forecasts, baseline_orders, outcomes, common_days, plan),
        "final_snapshot": realized_metrics("invalid_final_snapshot", final_forecasts, final_orders, outcomes, common_days, plan),
    }

    mutated = [dict(row) for row in versions]
    future_mutations = []
    cutoff_by_key = {(row["day"], row["sku"]): utc(row["cutoff"]) for row in queries}
    for index, version in enumerate(versions):
        available = version.get("available_at")
        key = (version["day"], version["sku"])
        if available is not None and utc(available) > cutoff_by_key[key]:
            before = finite_number(version["forecast"], "forecast")
            mutated[index]["forecast"] = before + 100.0
            future_mutations.append({"version_index": index, "day": version["day"], "sku": version["sku"],
                                     "available_at": available, "forecast_before": before,
                                     "forecast_after": before + 100.0})
    perturbed_join = run_join(queries, mutated)
    perturbed_decisions, perturbed_coverage = days_with_decisions(queries, mutated, perturbed_join, plan)
    base_indices = [{"query_index": m["query_index"], "status": m["status"],
                     "matched_version_index": m["matched_version_index"]} for m in joined["mappings"]]
    changed_indices = [{"query_index": m["query_index"], "status": m["status"],
                        "matched_version_index": m["matched_version_index"]}
                       for m in perturbed_join["mappings"]]
    base_orders = {row["day"]: row["orders"]
                   for row in decisions}
    changed_orders = {row["day"]: row["orders"]
                      for row in perturbed_decisions}
    if base_indices != changed_indices or base_orders != changed_orders:
        raise RuntimeError("Future-only forecast perturbation changed as-of mapping or orders")

    return {
        "schema_version": 1,
        "case": "synthetic-data-vintages",
        "information_policy": "strictly_before_cutoff",
        "mapping": joined,
        "query_coverage": {"query_rows": len(queries), **coverage},
        "daily_actionable_days": sum(row["actionable"] for row in decisions),
        "daily_decision_days": len(decisions),
        "daily_actions": decisions,
        "comparison": evaluation,
        "final_snapshot_status_counts": final_status_counts,
        "future_value_perturbation_check": {
            "method_side_check_only": True,
            "mutated_version_count": len(future_mutations),
            "mutations": future_mutations,
            "before_query_mappings": base_indices,
            "after_query_mappings": changed_indices,
            "before_daily_orders": base_orders,
            "after_daily_orders": changed_orders,
            "asof_indices_unchanged": base_indices == changed_indices,
            "orders_unchanged": base_orders == changed_orders,
            "perturbed_query_coverage": {"query_rows": len(queries), **perturbed_coverage},
            "is_independent_validator": False,
        },
        "limits": [
            "Availability timestamps are declared synthetic metadata; their real release provenance and ledger completeness are unknown.",
            "No forecast uncertainty model or calibrated risk policy is fitted.",
            "The eight-day fixed evaluation does not establish external validity or forecasting skill.",
            "Realized cost is an ex-post diagnostic, not proven future-best performance or real monetary return.",
            "The final-snapshot comparison uses future information and is not deployable.",
            "The perturbation check is not an independent validator.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    results = build_results()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "results.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    (args.output / "report.md").write_text(make_report(results), encoding="utf-8")


if __name__ == "__main__":
    main()
