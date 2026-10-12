# Coverage, capacity and local bottlenecks

[简体中文](README.md) · **English** · [Case gallery](../README.en.md)

Three facilities must meet demand at three locations. Having enough capacity in total is only one condition: that capacity must also reach the places that need it. This original synthetic example finds a least-cost allocation, checks which resource requirements are necessary, and then tests the result under bounded position errors and a facility failure.

![Synthetic service graph and tight geometric bounds for all nine distances](assets/coverage.png)

*Figure 1. Coverage and location error.* The left panel uses local Cartesian coordinates in km and an equal aspect ratio. Squares mark facilities; circles mark demand locations. Blue edges survive every admissible position error. Dashed C–u is exactly 5 km at the nominal coordinates and can become longer. The grey circle is C's nominal 5-km boundary. The right panel shows all nine nominal distances and their tight geometric bounds; these are not confidence intervals. Facility C is at **(0,8)** and demand w at **(0,7)**. A [vector PDF](assets/coverage.pdf) is available.

## The fixed scenario

The coordinates are explicitly declared as a synthetic local Cartesian plane, not a real city, road network, travel-time map or river. A facility can serve a demand directly when their Euclidean distance is **at most 5 km**, including equality. Demand is divisible. Installed capacity is a nonnegative continuous quantity, capped at eight units per facility.

| Facility | Coordinates (km) | Cost per capacity unit |
|---|---|---:|
| A | (0,0) | 3 |
| B | (6,0) | 2 |
| C | (0,8) | 1 |

Demand locations u, v and w are at **(0,3), (6,3) and (0,7)**, with quantities **4, 5 and 3** respectively. Bold distances indicate allowed nominal edges:

| Distance (km) | u | v | w |
|---|---:|---:|---:|
| A | **3** | √45 ≈ 6.7082 | 7 |
| B | √45 ≈ 6.7082 | **3** | √85 ≈ 9.2195 |
| C | **5** | √61 ≈ 7.8102 | **1** |

The LP minimizes `3a + 2b + c`. It meets every demand using only allowed edges and keeps each facility's assigned flow within its installed capacity. SciPy supplies Euclidean distances; the existing `solve_lp` interface uses HiGHS for capacities and flows.

| Coverage requirement | Minimum cost | Capacity (A,B,C) | An allocation attaining the bound |
|---|---:|---|---|
| Nominal coordinates | **17** | **(0,5,7)** | B→v=5; C→u=4; C→w=3 |
| Every admissible position error | **25** | **(4,5,3)** | A→u=4; B→v=5; C→w=3 |

## A feasible vector is not a list of necessary minima

At the nominal coordinates, full service is equivalent to `0≤a,b,c≤8` together with **b≥5, c≥3 and a+c≥7**. Only B can reach v, only C can reach w, and A plus C must cover the combined seven units at u and w. These conditions are sufficient too: assign five units to v and three to w, then split u's remaining four units between A and C.

The feasible vector `(4,5,3)` therefore does not prove that nominal service requires `a≥4`. The counterexample `(0,5,7)` meets every demand. Each coordinate can individually attain the minima `(0,5,3)`, yet that assembled vector is infeasible because `a+c=3<7`. An analytic cost bound also checks the optimizer: `b≥5` and `a+c≥7` imply `3a+2b+c≥17+2a≥17`, attained by `(0,5,7)`.

## What changes with error or failure

Every facility and demand point may independently move within a **closed 0.1-km disk**. A nominal distance d has the tight range `[max(0,d−0.2), d+0.2]`. A–u, B–v and C–w are always allowed. C–u is merely possible, with range **[4.8,5.2] km**. The other five edges remain unavailable. No probability distribution for the errors is assumed.

The fixed allocation using only the three always-allowed edges guarantees service with capacity `(4,5,3)`. Its cost is also optimal across all admissible configurations, even if flows can be reassigned after positions become known: moving C to **(0,8.1)** and u to **(0,2.9)**, while leaving other points unchanged, is admissible and makes C–u **5.2 km**. That configuration forces A, B and C to provide at least 4, 5 and 3 units, giving a lower bound of 25. This explicit witness matters. In general, individually possible edges need not be jointly attainable, and optimizing on always-allowed edges supplies a sufficient guarantee without automatically proving robust optimality.

When B fails, v has no reachable active facility. Even a hypothetical transfer of B's five capacity units to C, leaving active capacities **(4,0,8)** and a total of **12**, can serve at most the **7** units at u and w. The **5** units at v remain unserved. Preserving total capacity does not repair an empty local neighborhood.

An unlabeled longitude/latitude table requires verification of coordinate order, angular units, CRS/datum and an appropriate projected or geodesic metric before ground distances can be used. The demo rejects unknown angular coordinates instead of treating degrees as kilometers. A 5-km service graph and resource recommendations would otherwise be unsupported. See the [spatial-analysis guidance](../../references/spatial-analysis.md).

## Reproduce and inspect

Run from the source checkout and choose output paths that do not yet exist:

```bash
uv run --locked python -m examples.spatial_analysis_demo --output /path/to/new-spatial-run
uv run --locked python demos/spatial-analysis/build_figure.py --run /path/to/new-spatial-run --output /path/to/new-spatial-figure
```

The execution source contains the fixed specification. Optional `--input /path/to/fixed-fixture.json` accepts original JSON bytes of that same specification and checks their SHA-256 identity before and after analysis. Outputs include the nine-edge audit, actual LP matrices and variable order, both allocations, the necessity audit, an adverse position witness, B-failure results, an unknown-CRS rejection and `report.json`. Files are created only in the chosen new directory.

Author-process arithmetic checks the solver against integer squared distances, rational thresholds, all seven nonempty demand-subset capacity cuts, flow conservation and analytic cost bounds. An empty-neighborhood cut independently bounds service after B fails. The figure generator rechecks the original coordinates and complete arrays, records the actual artists, labels and legend, and exports PNG plus a vector PDF with embedded fonts. Inspect the rendered result as well as its data. Selected identities are retained in [demo.json](demo.json). This evidence covers a fixed synthetic calculation and its presentation; it establishes no real GIS validation, blind isolation, causal benefit or competition award.
