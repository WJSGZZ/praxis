"""Synthetic Cartesian coverage, capacity allocation and geometric error bounds.

Run from the checkout with a new output directory:
    uv run --locked python -m examples.spatial_analysis_demo --output /path/to/new-run

This fixed teaching fixture uses no real geographic data. Optional --input accepts
the same specification, preserving its original bytes and SHA-256 identity.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
from importlib.metadata import version
from itertools import combinations
import json
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from scipy.spatial.distance import cdist
from modeling.optimize import solve_lp


SPECIFICATION = {
    "title": "Synthetic service coverage and minimum resources",
    "coordinates": {"system": "declared local Cartesian plane", "unit": "km",
                    "provider_accuracy_radius_km": 0.1,
                    "crs_authority": "none, local synthetic coordinates; not latitude/longitude"},
    "sites": [
        {"id": "A", "xy": [0, 0], "capacity_max": 8, "unit_capacity_cost": 3},
        {"id": "B", "xy": [6, 0], "capacity_max": 8, "unit_capacity_cost": 2},
        {"id": "C", "xy": [0, 8], "capacity_max": 8, "unit_capacity_cost": 1},
    ],
    "demands": [
        {"id": "u", "xy": [0, 3], "quantity": 4},
        {"id": "v", "xy": [6, 3], "quantity": 5},
        {"id": "w", "xy": [0, 7], "quantity": 3},
    ],
    "service_radius_km": 5,
    "demand_splitting_allowed": True,
    "interpretation": "Service allowed exactly when Euclidean ground-plane distance<=radius; no claim about roads, travel time or river hydraulics. Every coordinate point may independently move within its stated closed error disk.",
    "tasks": [
        "Compute nominal distances and allowed edges, including equality at radius.",
        "Find a minimum cost capacity vector and feasible assignments; prove or independently check optimality.",
        "Audit the claim that capacity A>=4,B>=5,C>=3 is necessary because this particular assignment serves all demand. Find a counterexample or proof, separating joint feasibility from coordinatewise requirements.",
        "Give a robust guarantee with the stated coordinate error; distinguish always-feasible edges from merely possible ones.",
        "Explain whether unchanged total capacity establishes full service when B fails and why.",
        "Describe what can be concluded from an unlabeled longitude/latitude table; do not guess a CRS or convert degrees as kilometers.",
    ],
}


def _save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def _hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _require(condition, message):
    if not condition:
        raise RuntimeError(message)


def _validate(specification):
    coordinates = specification.get("coordinates", {})
    if coordinates.get("system") != "declared local Cartesian plane" or coordinates.get("unit") != "km":
        raise ValueError("Declared local Cartesian coordinates in km are required; unknown longitude/latitude CRS is not converted to kilometers")
    if specification != SPECIFICATION:
        raise ValueError("This demo accepts its fixed synthetic specification only")


def edge_audit(specification):
    """Euclidean nominal distances and tight pairwise closed-disk bounds."""
    sites, demands = specification["sites"], specification["demands"]
    distances = cdist([row["xy"] for row in sites], [row["xy"] for row in demands], metric="euclidean")
    radius = specification["service_radius_km"]
    error_sum = 2 * specification["coordinates"]["provider_accuracy_radius_km"]
    rows = []
    for i, site in enumerate(sites):
        for j, demand in enumerate(demands):
            distance = float(distances[i, j])
            low, high = max(0.0, distance - error_sum), distance + error_sum
            rows.append({"site": site["id"], "demand": demand["id"], "distance_km": distance,
                         "distance_min_km": low, "distance_max_km": high,
                         "nominal_allowed": bool(distance <= radius),
                         "always_allowed": bool(high <= radius),
                         "possibly_allowed": bool(low <= radius),
                         "classification": "always" if high <= radius else "possible_only" if low <= radius else "never"})
    return rows


def capacity_model(specification, edges):
    """Reuse the existing LP contract: capacities followed by allowed flows."""
    sites, demands = specification["sites"], specification["demands"]
    n = len(sites) + len(edges)
    objective = [float(site["unit_capacity_cost"]) for site in sites] + [0.0] * len(edges)
    upper, equal = np.zeros((len(sites), n)), np.zeros((len(demands), n))
    upper[:, :len(sites)] = -np.eye(len(sites))
    for k, edge in enumerate(edges, start=len(sites)):
        i = next(i for i, row in enumerate(sites) if row["id"] == edge["site"])
        j = next(j for j, row in enumerate(demands) if row["id"] == edge["demand"])
        upper[i, k] = 1
        equal[j, k] = 1
    contract = {"variable_order": ["capacity_" + site["id"] for site in sites] +
                                  [row["site"] + "_to_" + row["demand"] for row in edges],
                "c": objective, "A_ub": upper.tolist(), "b_ub": [0.0] * len(sites),
                "A_eq": equal.tolist(), "b_eq": [float(row["quantity"]) for row in demands],
                "bounds": [[0, row["capacity_max"]] for row in sites] + [[0, None]] * len(edges)}
    solution = solve_lp(contract["c"], A_ub=contract["A_ub"], b_ub=contract["b_ub"],
                        A_eq=contract["A_eq"], b_eq=contract["b_eq"], bounds=contract["bounds"])
    if not solution["success"]:
        raise RuntimeError("Coverage LP did not produce a feasible solution: " + solution["message"])
    capacity = {row["id"]: float(solution["x"][i]) for i, row in enumerate(sites)}
    assignments = [{"site": row["site"], "demand": row["demand"], "quantity": float(solution["x"][k])}
                   for k, row in enumerate(edges, start=len(sites))]
    return {"capacity": capacity, "assignments": assignments, "cost": solution["objective"],
            "lp_contract": contract, "solver": solution}


def _subset_cuts(capacity, edge_pairs, demands):
    """Check every nonempty demand subset by direct arithmetic, without a solver."""
    records = []
    for size in range(1, len(demands) + 1):
        for subset in combinations(demands, size):
            neighbors = sorted({site for site, demand in edge_pairs if demand in subset})
            available = sum(Fraction(str(capacity[site])) for site in neighbors)
            required = sum(Fraction(demands[demand]) for demand in subset)
            records.append({"demands": list(subset), "neighbors": neighbors,
                            "available_capacity": float(available), "required": float(required),
                            "satisfied": available >= required})
    return records


def _check_assignment(model, edge_pairs, specification):
    capacity = model["capacity"]
    assigned = {(row["site"], row["demand"]): Fraction(str(row["quantity"])) for row in model["assignments"]}
    _require(set(assigned) == set(edge_pairs), "Assignment edge identities differ from the independent graph")
    _require(all(value >= 0 for value in assigned.values()), "Negative service assignment")
    for demand in specification["demands"]:
        _require(sum(value for (site, item), value in assigned.items() if item == demand["id"]) == demand["quantity"],
                 "Assignment does not meet a demand exactly")
    for site in specification["sites"]:
        total = sum(value for (item, demand), value in assigned.items() if item == site["id"])
        _require(total <= Fraction(str(capacity[site["id"]])) <= site["capacity_max"], "Assignment exceeds a capacity bound")
    exact_cost = sum(Fraction(str(capacity[row["id"]])) * row["unit_capacity_cost"] for row in specification["sites"])
    _require(abs(float(exact_cost) - model["cost"]) < 1e-10, "Capacity cost is not the declared weighted sum")


def independent_checks(specification, edges, nominal, guaranteed):
    """Integer squared-distance answers, subset cuts and analytic lower bounds.

    These answers are fixed by hand from this fixture, not from LP output.
    This is independent arithmetic in the author process, not an independent
    agent evaluation or a blind research test.
    """
    square_oracle = [[9, 45, 49], [45, 9, 85], [25, 61, 1]]
    nominal_pairs = [("A", "u"), ("B", "v"), ("C", "u"), ("C", "w")]
    always_pairs = [("A", "u"), ("B", "v"), ("C", "w")]
    _require([(r["site"], r["demand"]) for r in edges if r["nominal_allowed"]] == nominal_pairs, "Inclusive nominal graph differs from the exact oracle")
    _require([(r["site"], r["demand"]) for r in edges if r["always_allowed"]] == always_pairs, "Guaranteed graph differs from the exact oracle")
    _require([(r["site"], r["demand"]) for r in edges if r["possibly_allowed"]] == nominal_pairs, "Possible graph differs from the exact oracle")
    for row, square in zip(edges, [value for line in square_oracle for value in line]):
        _require(abs(row["distance_km"] ** 2 - square) < 1e-12, "SciPy distance disagrees with the integer squared-distance oracle")
        # Squared comparison with rational thresholds avoids float ambiguity.
        exact_always = Fraction(square) <= (Fraction(5) - Fraction(1, 5)) ** 2
        exact_possible = Fraction(square) <= (Fraction(5) + Fraction(1, 5)) ** 2
        _require(row["always_allowed"] == exact_always and row["possibly_allowed"] == exact_possible,
                 "Error classification differs from exact rational squared thresholds")
    _check_assignment(nominal, nominal_pairs, specification)
    _check_assignment(guaranteed, always_pairs, specification)
    # Nominal: b>=5, a+c>=7 => 3a+2b+c >= 17+2a >= 17.
    # The feasible vector (0,5,7) attains 17. Under the adverse configuration,
    # only Au/Bv/Cw remain, so a>=4,b>=5,c>=3 and cost>=25.
    _require(nominal["capacity"] == {"A": 0.0, "B": 5.0, "C": 7.0} and abs(nominal["cost"] - 17) < 1e-10,
             "Nominal solution does not attain the independent bound 17")
    _require(guaranteed["capacity"] == {"A": 4.0, "B": 5.0, "C": 3.0} and abs(guaranteed["cost"] - 25) < 1e-10,
             "Guaranteed solution does not attain the independent bound 25")
    quantities = {row["id"]: row["quantity"] for row in specification["demands"]}
    nominal_cuts = _subset_cuts(nominal["capacity"], nominal_pairs, quantities)
    guaranteed_cuts = _subset_cuts(guaranteed["capacity"], always_pairs, quantities)
    _require(all(row["satisfied"] for row in nominal_cuts + guaranteed_cuts), "A demand-subset capacity cut fails")
    coordinate_minimum_cuts = _subset_cuts({"A": 0, "B": 5, "C": 3}, nominal_pairs, quantities)
    _require(not all(row["satisfied"] for row in coordinate_minimum_cuts), "Coordinate minima were incorrectly treated as jointly feasible")
    return {"status": "passed", "distance_squared_oracle_km2": square_oracle,
            "nominal_cost_lower_bound": 17, "guaranteed_cost_lower_bound": 25,
            "nominal_proof": "b>=5 and a+c>=7 imply 3a+2b+c>=17+2a>=17; (0,5,7) attains 17.",
            "robust_proof": "The admissible configuration C=(0,8.1),u=(0,2.9) removes Cu, forcing a>=4,b>=5,c>=3 and cost>=25; (4,5,3) uses only always-allowed edges and attains 25.",
            "nominal_subset_cuts": nominal_cuts, "guaranteed_subset_cuts": guaranteed_cuts,
            "coordinate_minimum_vector": {"A": 0, "B": 5, "C": 3},
            "coordinate_minimum_subset_cuts": coordinate_minimum_cuts,
            "scope": "Author-process independent arithmetic for this synthetic fixture; no blind test, real GIS validation or award claim"}


def failure_scenario(specification, edges):
    # Move B's five units to C: the total is still twelve and C stays <=8.
    capacity = {"A": 4, "B": 0, "C": 8}
    active_edges = [row for row in edges if row["nominal_allowed"] and row["site"] != "B"]
    upper = np.zeros((len(specification["sites"]) + len(specification["demands"]), len(active_edges)))
    for k, row in enumerate(active_edges):
        i = next(i for i, site in enumerate(specification["sites"]) if site["id"] == row["site"])
        j = next(j for j, demand in enumerate(specification["demands"]) if demand["id"] == row["demand"])
        upper[i, k] = 1
        upper[len(specification["sites"]) + j, k] = 1
    solution = solve_lp([1] * len(active_edges), maximize=True, A_ub=upper,
                        b_ub=list(capacity.values()) + [row["quantity"] for row in specification["demands"]])
    _require(solution["success"] and abs(solution["objective"] - 7) < 1e-10, "B-failure maximum service differs from its exact answer")
    # Independent cut {v}: empty neighborhood, capacity 0, demand 5.
    cuts = _subset_cuts(capacity, [(row["site"], row["demand"]) for row in active_edges],
                        {row["id"]: row["quantity"] for row in specification["demands"]})
    cut = next(row for row in cuts if row["demands"] == ["v"])
    _require(cut["neighbors"] == [] and cut["required"] == 5 and not cut["satisfied"], "B-failure bottleneck cut was missed")
    return {"capacity_after_redistribution": capacity, "total_capacity": 12, "total_demand": 12,
            "maximum_served": solution["objective"], "unserved_v": 5, "bottleneck_cut": cut,
            "proof": "After B fails, v has no reachable active facility. Service is at most u+w=7; Au=4 and Cw=3 attain this bound even when total active capacity remains 12.",
            "solver": solution}


def run_demo(output, input_path=None):
    output = Path(output).expanduser().absolute()
    if output.exists():
        raise FileExistsError("Output must be a new directory: " + str(output))
    started = datetime.now(timezone.utc).isoformat()
    original = None if input_path is None else Path(input_path).expanduser().absolute()
    raw = json.dumps(SPECIFICATION, indent=2).encode("utf-8") if original is None else original.read_bytes()
    initial_hash = hashlib.sha256(raw).hexdigest()
    specification = json.loads(raw)
    _validate(specification)
    output.mkdir(parents=True, exist_ok=False)
    (output / "input.json").write_bytes(raw)
    edges = edge_audit(specification)
    _save(output / "edge-audit.json", {"unit": "km", "radius_inclusive": 5, "independent_point_error_radius": 0.1,
                                      "pairwise_bound_formula": "[max(0,d-0.2),d+0.2]", "edges": edges})
    nominal = capacity_model(specification, [row for row in edges if row["nominal_allowed"]])
    guaranteed = capacity_model(specification, [row for row in edges if row["always_allowed"]])
    _save(output / "nominal-allocation.json", nominal)
    _save(output / "guaranteed-allocation.json", guaranteed)
    verification = independent_checks(specification, edges, nominal, guaranteed)
    failure = failure_scenario(specification, edges)
    _save(output / "b-failure.json", failure)
    necessity = {"nominal_joint_feasibility": "0<=a,b,c<=8; b>=5; c>=3; a+c>=7",
                 "coordinatewise_minima": {"A": 0, "B": 5, "C": 3},
                 "coordinatewise_minima_jointly_feasible": False,
                 "feasible_counterexample_to_a_ge_4": {"A": 0, "B": 5, "C": 7},
                 "original_feasible_vector": {"A": 4, "B": 5, "C": 3},
                 "interpretation": "One feasible allocation proves sufficiency, not that each installed coordinate is necessary. B>=5 and C>=3 are necessary here; A>=4 is necessary only for the worst-case location guarantee.",
                 "sufficiency_proof": "Serve v=5 from B and w=3 from C. Split u=4 between A and C using remaining capacities: a+(c-3)>=4. This is equivalent to a+c>=7."}
    _save(output / "necessity-audit.json", necessity)
    # An attained endpoint witness proves this fixture's robust lower bound,
    # rather than assuming independently classified possible edges co-occur.
    adverse = json.loads(json.dumps(specification))
    adverse["sites"][2]["xy"] = [0, 8.1]
    adverse["demands"][0]["xy"] = [0, 2.9]
    adverse_edges = edge_audit(adverse)
    _require([(r["site"], r["demand"]) for r in adverse_edges if r["nominal_allowed"]] == [("A", "u"), ("B", "v"), ("C", "w")],
             "The declared adverse location witness has the wrong graph")
    _save(output / "location-guarantee.json", {"uncertainty": "Every facility and demand independently moves in a closed radius-0.1-km disk; no probability distribution is specified",
                                             "adverse_witness": {"C": [0, 8.1], "u": [0, 2.9], "other_points": "unchanged", "C_u_distance_km": 5.2},
                                             "guarantee": "Capacity (4,5,3) with Au=4,Bv=5,Cw=3 serves every admissible configuration, even without reassigning flows.",
                                             "minimum_cost_with_recourse": 25,
                                             "scope": "Always-edge use is sufficient in general; its optimality for all configurations is established here by the explicit adverse witness. Pairwise possible edges need not be jointly realizable in general."})
    bad_coordinates = json.loads(json.dumps(specification))
    bad_coordinates["coordinates"] = {"system": "unlabeled longitude/latitude", "unit": "degrees"}
    try:
        _validate(bad_coordinates)
    except ValueError as error:
        coordinate_check = {"status": "rejected", "message": str(error),
                            "conclusion": "An unlabeled table supports only coordinate-value descriptions. Ground distances, a 5-km service graph and resource conclusions require verified coordinate order, angular units, CRS/datum and an appropriate projected or geodesic metric."}
    else:
        raise RuntimeError("Unknown angular coordinates were accepted as kilometers")
    _save(output / "unknown-crs-rejection.json", coordinate_check)
    _require(_hash(output / "input.json") == initial_hash, "Copied input changed during analysis")
    if original is not None:
        _require(_hash(original) == initial_hash, "Original input changed during analysis")
    verification["original_input_sha256"] = initial_hash
    verification["original_input_preserved"] = True
    _save(output / "independent-verification.json", verification)
    root = Path(__file__).resolve().parents[1]
    report = {"status": "verified_synthetic_spatial_demo", "started_utc": started,
              "completed_utc": datetime.now(timezone.utc).isoformat(), "output_directory": str(output),
              "scope": "Original synthetic local Cartesian service coverage; no real city, road, travel-time, river or GIS validation",
              "coordinates": specification["coordinates"], "original_input_sha256": initial_hash,
              "nominal_edges": [[row["site"], row["demand"]] for row in edges if row["nominal_allowed"]],
              "guaranteed_edges": [[row["site"], row["demand"]] for row in edges if row["always_allowed"]],
              "nominal_minimum_cost": nominal["cost"], "guaranteed_minimum_cost": guaranteed["cost"],
              "capacity_order": [row["id"] for row in specification["sites"]],
              "nominal_capacity": nominal["capacity"], "guaranteed_capacity": guaranteed["capacity"],
              "maximum_service_after_b_failure_with_total_capacity_12": failure["maximum_served"],
              "libraries": {name: version(name) for name in ["numpy", "scipy"]},
              "source_sha256": _hash(Path(__file__)),
              "implementation_sha256": {name: _hash(root / name) for name in ["examples/spatial_analysis_demo.py", "modeling/optimize.py"]},
              "scientific_limits": ["Closed disks give geometric worst-case bounds, not confidence intervals or probabilities.",
                                    "Demand and installed capacity are continuous; service may split across allowed edges.",
                                    "Pairwise possible edges do not generally define one jointly attainable configuration.",
                                    "The all-configurations optimum is proved for this fixture by an explicit adverse witness, not assumed from a conservative graph.",
                                    "Unknown angular CRS is rejected rather than converted as kilometers.",
                                    "Independent author-process arithmetic does not establish blind evaluation, causal benefits or competition quality."],
              "artifacts": sorted(path.name for path in output.iterdir()) + ["report.json"]}
    _save(output / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New output directory; existing paths are refused")
    parser.add_argument("--input", type=Path, help="Optional original JSON bytes of this fixed fixture")
    arguments = parser.parse_args()
    report = run_demo(arguments.output, arguments.input)
    print(json.dumps({"status": report["status"], "original_input_sha256": report["original_input_sha256"],
                      "nominal_minimum_cost": report["nominal_minimum_cost"],
                      "guaranteed_minimum_cost": report["guaranteed_minimum_cost"]}))


if __name__ == "__main__":
    main()
