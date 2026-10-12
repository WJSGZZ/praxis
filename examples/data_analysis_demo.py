"""Store-week analysis: explicit data contract, m:1 join and cluster inference.

Run from the source checkout with a new output directory:
    uv run --locked python -m examples.data_analysis_demo --output /path/to/new-demo

All inputs are generated locally from the deterministic specification below.
The example is an auditable teaching fixture, not evidence about real stores.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from modeling.data_analysis import audit_join
from modeling.inference import adjust_pvalues
from modeling.regression import ols_report
from scripts.audit_data import audit


# These hypotheses and the model are fixed before data construction and fitting.
PLAN = {
    "scenario": "Association of weekly store sales with campaign status and calendar week",
    "observation_unit": "One synthetic store-week",
    "independent_unit_declared": "Store; four repeated weeks within each store",
    "population": "Twelve locally constructed synthetic stores; no real-world population is sampled",
    "estimands": [
        {"hypothesis_id": "campaign_association", "coefficient": "campaign", "null": "Coefficient equals zero", "unit": "sales units per campaign indicator"},
        {"hypothesis_id": "weekly_trend", "coefficient": "week_centered", "null": "Coefficient equals zero", "unit": "sales units per calendar week"},
    ],
    "model": "sales = intercept + campaign coefficient * campaign + week coefficient * (week - 2.5) + error",
    "family_id": "store_sales_two_associations", "family_method": "holm", "alpha": 0.05,
    "inclusion": "All twelve stores and four weeks; no data-dependent selection and no missing input values",
    "join": {"on": "store_id", "relationship": "many_to_one", "how": "left", "null_policy": "reject"},
    "covariance": "One-way store cluster CRV1; Student-t reference with G-1 degrees of freedom",
    "interpretation": "Conditional associations. Campaign is a synthetic store attribute; no causal identification is claimed.",
    "scope": "Plan is saved before this script constructs the synthetic data; this is a teaching workflow, not an independent preregistration or confidence-interval coverage study.",
}


def _save(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def _hash(path: Path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _require(condition, message):
    if not condition:
        raise RuntimeError(message)


def _synthetic_tables():
    # Within each campaign category store offsets sum to zero. Store slopes
    # sum to zero across all twelve stores. The within-store noise vector is
    # orthogonal to the intercept and centered calendar week. Thus the full
    # OLS coefficients have the exact independent answer [50, 7, 2].
    offsets = {0: [-5, -3, -1, 1, 3, 5], 1: [-4, -2, 0, 0, 2, 4]}
    observations, stores = [], []
    for store in range(12):
        campaign = store % 2
        store_id = f"store_{store + 1:02d}"
        stores.append({"store_id": store_id, "campaign": campaign})
        offset = offsets[campaign][store // 2]
        slope = (store - 5.5) / 4
        noise_amplitude = 1 + store % 3
        for week, noise in zip(range(1, 5), [1, -1, -1, 1]):
            centered = week - 2.5
            sales = 50 + 7 * campaign + 2 * centered + offset + slope * centered + noise_amplitude * noise
            observations.append({"store_id": store_id, "week": week, "sales": sales})
    return pd.DataFrame(observations), pd.DataFrame(stores)


def _independent_checks(joined, fit, family):
    """Verification only: known coefficients and an explicit group-score oracle."""
    design = np.column_stack([np.ones(len(joined)), joined["campaign"], joined["week_centered"]])
    truth = np.array([50.0, 7.0, 2.0])
    estimates = np.array([row["estimate"] for row in fit["coefficients"]])
    _require(np.allclose(estimates, truth, atol=1e-11, rtol=0), "OLS coefficients disagree with the constructed exact answer")
    residual = joined["sales"].to_numpy() - design @ truth
    store_ids = joined["store_id"].tolist()
    unique_stores = sorted(set(store_ids))
    scores = []
    for store in unique_stores:
        rows = [index for index, identity in enumerate(store_ids) if identity == store]
        scores.append(sum((design[index] * residual[index] for index in rows), start=np.zeros(3)))
    meat = sum((np.outer(score, score) for score in scores), start=np.zeros((3, 3)))
    bread = np.linalg.inv(design.T @ design)
    groups, observations, parameters = len(unique_stores), len(joined), design.shape[1]
    correction = Fraction(groups, groups - 1) * Fraction(observations - 1, observations - parameters)
    oracle = float(correction) * bread @ meat @ bread
    actual = np.asarray(fit["covariance"]["matrix"])
    _require(np.allclose(actual, oracle, atol=1e-11, rtol=0), "CRV1 covariance disagrees with the independent group-score oracle")
    # Campaign is the difference of six-store category means. Their offset
    # sum-of-squares are 70 and 40, so its CRV1 variance is exactly 94/27.
    _require(abs(oracle[1, 1] - float(Fraction(94, 27))) < 1e-12, "Campaign-variance rational check failed")
    rows = family["hypotheses"]
    pvalues = [row["p_value"] for row in rows]
    smaller = 0 if pvalues[0] <= pvalues[1] else 1
    larger = 1 - smaller
    expected = [None, None]
    expected[smaller] = min(1.0, 2 * pvalues[smaller])
    expected[larger] = min(1.0, max(expected[smaller], pvalues[larger]))
    _require(np.allclose([row["adjusted_p_value"] for row in rows], expected, atol=1e-14, rtol=0), "Two-hypothesis Holm adjustment disagrees with its direct formula")
    return {"status": "passed", "known_coefficients": truth.tolist(),
            "coefficient_absolute_errors": np.abs(estimates - truth).tolist(),
            "cluster_covariance_oracle": oracle.tolist(),
            "cluster_covariance_max_absolute_error": float(np.abs(actual - oracle).max()),
            "crv1_correction_exact": str(correction), "campaign_variance_exact": "94/27",
            "holm_two_hypothesis_oracle": expected,
            "scope": "Specific deterministic fixture and API arithmetic only; no real-data design, causal identification or repeated-sampling coverage validation"}


def run_demo(output: str | Path):
    output = Path(output).expanduser().absolute()
    # Refuse existing paths before writing any files; callers choose the output.
    output.mkdir(parents=True, exist_ok=False)
    started = datetime.now(timezone.utc).isoformat()
    _save(output / "analysis-plan.json", PLAN)
    observations, stores = _synthetic_tables()
    observations_path, stores_path = output / "observations.csv", output / "stores.csv"
    observations.to_csv(observations_path, index=False)
    stores.to_csv(stores_path, index=False)
    initial_hashes = {path.name: _hash(path) for path in (observations_path, stores_path)}
    contract = {"observation_unit": PLAN["observation_unit"], "population": PLAN["population"],
                "coverage": "Four synthetic weeks in twelve synthetic stores", "source": "Deterministic local construction in examples/data_analysis_demo.py",
                "columns": {"store_id": {"meaning": "Store identifier", "unit": "identifier", "kind": "string", "nullable": False},
                            "week": {"meaning": "Calendar week index", "unit": "week", "kind": "integer", "nullable": False, "minimum": 1, "maximum": 4},
                            "sales": {"meaning": "Weekly sales volume", "unit": "sales units", "kind": "numeric", "nullable": False, "finite": True, "minimum": 0}},
                "unique_keys": [["store_id", "week"]]}
    _save(output / "data-contract.json", contract)
    audit_report = audit(observations_path, contract=contract, keep_default_na=False)
    _require(audit_report["data_contract"]["status"] == "checked", "Synthetic observations violate the declared data contract")
    _save(output / "data-audit.json", audit_report)
    left, right = observations.to_dict(orient="records"), stores.to_dict(orient="records")
    join_report = audit_join(left, right, **PLAN["join"])
    _require(join_report["output_rows"] == 48 and join_report["left"]["unmatched_input_rows"] == 0,
             "Expected all 48 store-week observations to match twelve unique stores")
    _save(output / "join-audit.json", join_report)
    bad_right = right + [dict(right[0])]
    try:
        audit_join(left, bad_right, **PLAN["join"])
    except pd.errors.MergeError as error:
        bad_join = {"status": "rejected", "exception": type(error).__name__, "error": str(error),
                    "change": "Appended a second metadata row for store_01", "expected": "many_to_one must reject duplicate right keys"}
    else:
        raise RuntimeError("The deliberate invalid many-to-one join was accepted")
    _save(output / "bad-join-rejection.json", bad_join)
    joined = observations.merge(stores, on="store_id", how="left", validate="many_to_one", indicator=True)
    _require((joined["_merge"] == "both").all() and not joined.duplicated(["store_id", "week"]).any(),
             "Actual payload merge changed the observation identity or coverage")
    joined["week_centered"] = joined["week"] - 2.5
    fit = ols_report(joined[["campaign", "week_centered"]].to_numpy(), joined["sales"].to_numpy(),
                     names=["campaign", "week_centered"], covariance="cluster", groups=joined["store_id"].tolist())
    _require(fit["covariance"]["status"] == "computed" and fit["covariance"]["clusters"] == 12,
             "The store-cluster covariance was not computed")
    coefficients = {row["name"]: row for row in fit["coefficients"]}
    hypothesis_rows = [coefficients[item["coefficient"]] for item in PLAN["estimands"]]
    family = adjust_pvalues([row["p_value"] for row in hypothesis_rows],
                            hypothesis_ids=[item["hypothesis_id"] for item in PLAN["estimands"]],
                            family_id=PLAN["family_id"], method=PLAN["family_method"], alpha=PLAN["alpha"],
                            effects=[row["estimate"] for row in hypothesis_rows],
                            effect_definition="Campaign: sales units per indicator; weekly trend: sales units per calendar week. Both are conditional associations, not causal effects.")
    _save(output / "cluster-regression.json", fit)
    _save(output / "comparison-family.json", family)
    verification = _independent_checks(joined, fit, family)
    final_hashes = {path.name: _hash(path) for path in (observations_path, stores_path)}
    _require(initial_hashes == final_hashes, "Original synthetic CSV inputs were changed during analysis")
    verification["original_inputs_preserved"] = True
    _save(output / "independent-verification.json", verification)
    grouped = joined.groupby(["store_id", "campaign"], as_index=False).agg(weekly_sales_mean=("sales", "mean"), observations=("sales", "size"))
    grouped.to_csv(output / "store-summary.csv", index=False)
    report = {"status": "verified_synthetic_demo", "output_directory": str(output), "started_utc": started,
              "completed_utc": datetime.now(timezone.utc).isoformat(), "observations": 48, "independent_units_declared": 12,
              "original_input_sha256": initial_hashes, "coefficient_truth": [50, 7, 2],
              "scientific_limits": ["All data are synthetic, deterministic and local; results say nothing about real store performance.",
                                    "Store independence is a design declaration; four repeated weeks are not four independent stores.",
                                    "Twelve clusters is a small number; CRV1 correction and t reference do not establish reliable finite-sample coverage.",
                                    "Campaign association is not a causal effect. Clustering does not remove confounding or repair a misspecified mean model.",
                                    "Holm corrects the complete prespecified two-test family only; it cannot repair invalid p-values or undisclosed tests."],
              "libraries": {name: version(name) for name in ["numpy", "pandas", "statsmodels"]},
              "source_sha256": _hash(Path(__file__)),
              "implementation_sha256": {name: _hash(Path(__file__).resolve().parents[1] / name)
                                        for name in ["examples/data_analysis_demo.py", "scripts/audit_data.py", "modeling/data_analysis.py", "modeling/regression.py", "modeling/inference.py"]},
              "artifacts": sorted(path.name for path in output.iterdir()) + ["report.json"]}
    _save(output / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New output directory; existing directories are refused")
    arguments = parser.parse_args()
    report = run_demo(arguments.output)
    print(json.dumps({"status": report["status"], "output_directory": report["output_directory"],
                      "observations": report["observations"], "independent_units_declared": report["independent_units_declared"]}))


if __name__ == "__main__":
    main()
