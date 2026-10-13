"""Connected-component measurements on a fixed, locally constructed binary mask.

Run from the source checkout with a new output directory:
    uv run --locked python -m examples.image_analysis_demo --output /path/to/new-run
The fixture is synthetic and is not a picture of real specimens or particles.
"""
import argparse
from collections import deque
import json
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modeling.image_analysis import binary_components


def synthetic_mask():
    """Build a 32x40 fixture with a rectangle, L region, diagonal pair and controls."""
    mask = [[0] * 40 for _ in range(32)]
    for row in range(4, 10):
        for col in range(4, 11):
            mask[row][col] = 1
    for row in range(16, 21):
        for col in range(4, 6):
            mask[row][col] = 1
    for row in range(19, 21):
        for col in range(6, 12):
            mask[row][col] = 1
    for row, col in [(5, 28), (6, 29), (0, 38)]:
        mask[row][col] = 1
    for row in range(25, 27):
        for col in range(31, 33):
            mask[row][col] = 1
    mask[13][22] = 1
    return mask


def bfs_components(mask, connectivity):
    """Independent queue-based flood fill for fixture verification only."""
    rows, cols = len(mask), len(mask[0])
    neighbors = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    if connectivity == 8:
        neighbors.extend([(-1, -1), (-1, 1), (1, -1), (1, 1)])
    seen, groups = set(), []
    for row in range(rows):
        for col in range(cols):
            if not mask[row][col] or (row, col) in seen:
                continue
            seen.add((row, col))
            queue, points = deque([(row, col)]), []
            while queue:
                point = queue.popleft()
                points.append(point)
                for dr, dc in neighbors:
                    nxt = point[0] + dr, point[1] + dc
                    if (0 <= nxt[0] < rows and 0 <= nxt[1] < cols
                            and mask[nxt[0]][nxt[1]] and nxt not in seen):
                        seen.add(nxt)
                        queue.append(nxt)
            groups.append(points)
    return groups


def _metrics(points):
    rows, cols = [p[0] for p in points], [p[1] for p in points]
    n = len(points)
    return {
        "pixel_area": n,
        "bbox": [min(rows), min(cols), max(rows) + 1, max(cols) + 1],
        "centroid": [sum(rows) / n, sum(cols) / n],
    }


def _require(condition, message):
    if not condition:
        raise RuntimeError(message)


def run_demo(output):
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"Choose a new output directory: {output}")
    mask = synthetic_mask()
    four = binary_components(mask, connectivity=4)
    eight = binary_components(mask, connectivity=8)
    selected = binary_components(mask, connectivity=8, min_pixels=3, exclude_border=True,
                                 max_components=200, pixel_size=[0.2, 0.3], unit="mm")
    groups4, groups8 = bfs_components(mask, 4), bfs_components(mask, 8)
    _require(four["raw_component_count"] == len(groups4) == 7, "4-neighbor count disagrees with independent flood fill")
    _require(eight["raw_component_count"] == len(groups8) == 6, "8-neighbor count disagrees with independent flood fill")
    _require(four["foreground_pixels"] == eight["foreground_pixels"] == 72, "Foreground pixel conservation failed")
    for result, groups in ((four, groups4), (eight, groups8)):
        for actual, points in zip(result["components"], groups):
            expected = _metrics(points)
            _require(actual["pixel_area"] == expected["pixel_area"], "Independent pixel-area check failed")
            _require(actual["bbox"] == expected["bbox"], "Independent bounding-box check failed")
            _require(all(abs(a - b) < 1e-12 for a, b in zip(actual["centroid"], expected["centroid"])),
                     "Independent centroid check failed")
    expected_kept = []
    for label_id, points in enumerate(groups8, 1):
        geometry = _metrics(points)
        r0, c0, r1, c1 = geometry["bbox"]
        touches = r0 == 0 or c0 == 0 or r1 == len(mask) or c1 == len(mask[0])
        if touches or len(points) < 3:
            continue
        expected_kept.append((label_id, geometry))
    _require([(item["id"], item["pixel_area"], item["bbox"]) for item in selected["components"]]
             == [(label, geometry["pixel_area"], geometry["bbox"]) for label, geometry in expected_kept],
             "Independent filtering check failed")
    _require(selected["excluded_border_components"] == 1 and selected["excluded_small_components"] == 2,
             "Filter precedence/count check failed")
    _require(selected["physical_foreground_area"] == 4.32 and selected["physical_filtered_area"] == 4.08,
             "Declared-scale area totals disagree with exact pixel totals")

    output.mkdir(parents=True)
    (output / "mask.json").write_text(json.dumps(mask, separators=(",", ":")) + "\n", encoding="utf-8")
    results = {"connectivity_4": four, "connectivity_8": eight, "filtered_8": selected}
    (output / "measurements.json").write_text(json.dumps(results, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    verification = {
        "status": "passed",
        "oracle": "Independent queue-based breadth-first flood fill and direct pixel arithmetic; no SciPy-generated expected values.",
        "checks": {
            "shape": [32, 40], "foreground_pixels": 72,
            "component_counts": {"connectivity_4": len(groups4), "connectivity_8": len(groups8)},
            "rectangle_pixels": 42, "L_region_pixels": 22,
            "diagonal_pair": {"separate_at_4": True, "joined_at_8": True},
            "filtered_8": {"retained_components": 3, "retained_pixels": 68,
                            "border_excluded_first": 1, "small_excluded_after_border": 2},
            "declared_scale_mm": [0.2, 0.3],
            "expected_areas_mm2": {"foreground": 4.32, "filtered": 4.08},
        },
        "scope": "Deterministic synthetic mask and measurement implementation only; no segmentation validation, calibration verification, real-object counting, population inference, or imaging-system performance is established.",
    }
    (output / "independent-verification.json").write_text(json.dumps(verification, indent=2) + "\n", encoding="utf-8")
    return {"output": str(output), **verification}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run_demo(args.output), indent=2))


if __name__ == "__main__":
    main()
