"""Independent contract checks for image_analysis.binary_components."""
import copy
import numpy as np
import pytest

from modeling.image_analysis import binary_components


def _bfs(mask, connectivity):
    """Small independent flood fill used only as a test oracle."""
    rows, cols = len(mask), len(mask[0])
    neighbors = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    if connectivity == 8:
        neighbors += [(-1, -1), (-1, 1), (1, -1), (1, 1)]
    seen = set()
    groups = []
    for row in range(rows):
        for col in range(cols):
            if not mask[row][col] or (row, col) in seen:
                continue
            stack = [(row, col)]
            seen.add((row, col))
            group = []
            while stack:
                point = stack.pop()
                group.append(point)
                for dr, dc in neighbors:
                    nxt = (point[0] + dr, point[1] + dc)
                    if 0 <= nxt[0] < rows and 0 <= nxt[1] < cols and mask[nxt[0]][nxt[1]] and nxt not in seen:
                        seen.add(nxt)
                        stack.append(nxt)
            groups.append(group)
    return groups


def test_rectangle_bbox_centroid_and_anisotropic_calibration():
    mask = [[0, 0, 0, 0, 0], [0, 1, 1, 0, 0], [0, 1, 1, 0, 0], [0, 0, 0, 0, 0]]
    result = binary_components(mask, pixel_size=[2.0, 3.0], unit="mm")
    component = result["components"][0]
    assert component["bbox"] == [1, 1, 3, 3]
    assert component["centroid"] == [1.5, 1.5]
    assert component["pixel_area"] == 4
    assert component["physical_area"] == 24.0
    assert result["physical_foreground_area"] == result["physical_filtered_area"] == 24.0
    assert component["physical_centroid"] == [4.0, 6.0]
    assert result["calibration"]["status"] == "caller_declared_not_verified"


def test_diagonal_connectivity_and_empty_foreground():
    diagonal = [[1, 0], [0, 1]]
    four = binary_components(diagonal, connectivity=4)
    eight = binary_components(diagonal, connectivity=8)
    assert four["raw_component_count"] == 2
    assert eight["raw_component_count"] == 1
    empty = binary_components([[0, 0], [0, 0]])
    assert empty["raw_component_count"] == empty["filtered_component_count"] == 0
    assert empty["foreground_pixels"] == empty["filtered_pixels"] == 0


def test_border_small_filter_and_truncation_preserve_raw_statistics():
    mask = [[1, 0, 0, 0, 1], [0, 0, 0, 0, 0], [0, 0, 1, 1, 0], [0, 0, 0, 0, 0], [1, 0, 0, 0, 0]]
    result = binary_components(mask, exclude_border=True, min_pixels=2, max_components=0)
    assert result["raw_component_count"] == 4
    assert result["foreground_pixels"] == 5
    assert result["excluded_border_components"] == 3
    assert result["excluded_small_components"] == 0
    assert result["filtered_component_count"] == 1
    assert result["filtered_pixels"] == 2
    assert result["filters"] == {"min_pixels": 2, "exclude_border": True, "filter_order": "border_then_small; mutually exclusive rejection counts"}
    assert result["returned_component_count"] == 0
    assert result["truncated"] is True
    small = binary_components([[1, 0, 0], [0, 1, 0], [0, 0, 0]], connectivity=4, min_pixels=2)
    assert small["excluded_small_components"] == 2
    assert small["filtered_component_count"] == 0


def test_input_is_unchanged_and_padding_transpose_preserve_area():
    mask = [[0, 1, 1], [0, 0, 0]]
    original = copy.deepcopy(mask)
    baseline = binary_components(mask)
    assert mask == original
    padded = [[0] * 5] + [[0] + row + [0] for row in mask] + [[0] * 5]
    transposed = [list(row) for row in zip(*mask)]
    assert binary_components(padded)["foreground_pixels"] == baseline["foreground_pixels"]
    assert binary_components(transposed)["foreground_pixels"] == baseline["foreground_pixels"]
    assert binary_components(transposed)["raw_component_count"] == baseline["raw_component_count"]


@pytest.mark.parametrize("connectivity", [4, 8])
@pytest.mark.parametrize("seed", [2, 11, 29, 43])
def test_multiple_small_masks_against_independent_bfs(connectivity, seed):
    rng = np.random.default_rng(seed)
    for _ in range(12):
        mask = (rng.random((5, 6)) < 0.32).tolist()
        expected = _bfs(mask, connectivity)
        got = binary_components(mask, connectivity=connectivity)
        assert got["raw_component_count"] == len(expected)
        assert got["foreground_pixels"] == sum(map(len, expected))
        for actual, group in zip(got["components"], expected):
            rs, cs = [p[0] for p in group], [p[1] for p in group]
            assert actual["pixel_area"] == len(group)
            assert actual["bbox"] == [min(rs), min(cs), max(rs) + 1, max(cs) + 1]
            assert actual["centroid"] == pytest.approx([sum(rs) / len(rs), sum(cs) / len(cs)])


@pytest.mark.parametrize("mask", [[], [[]], [[1], [1, 0]], [[1 + 0j]], [["1"]], [[float("nan")]], [[float("inf")]], [[0, 2]], np.zeros((1, 1, 1)), "1"])
def test_rejects_malformed_masks(mask):
    with pytest.raises(ValueError):
        binary_components(mask)


@pytest.mark.parametrize("kwargs", [
    {"connectivity": True}, {"connectivity": 6}, {"min_pixels": False},
    {"min_pixels": 0}, {"max_components": True}, {"max_components": 1001},
    {"exclude_border": 1}, {"pixel_size": [1, 2]}, {"pixel_size": [1, float("inf")], "unit": "mm"},
    {"pixel_size": [1, 2], "unit": ""}, {"unit": "mm"}, {"pixel_size": [1, 2], "unit": "m" * 33},
])
def test_rejects_invalid_options(kwargs):
    with pytest.raises(ValueError):
        binary_components([[1]], **kwargs)


def test_accepts_dimension_and_area_limits():
    assert binary_components([[1] * 512])['shape'] == [1, 512]
    assert binary_components([[0] * 256 for _ in range(256)])['shape'] == [256, 256]
    with pytest.raises(ValueError):
        binary_components([[0] * 513])
    with pytest.raises(ValueError):
        binary_components([[0] * 257 for _ in range(256)])


def test_scale_rejects_numeric_strings_overflow_and_underflow_counterexamples():
    for scale in (["2", "3"], [1e308, 1e308], [1e-200, 1e-200]):
        with pytest.raises(ValueError):
            binary_components([[1]], pixel_size=scale, unit="mm")


def test_scale_representability_at_finite_boundaries():
    result = binary_components([[1]], pixel_size=[1e-150, 1e-150], unit="m")
    assert result["physical_foreground_area"] > 0
    assert np.isfinite(result["physical_foreground_area"])
    assert result["components"][0]["physical_area"] > 0
    ordinary = binary_components([[1]], pixel_size=[1e308, 1e-308], unit="m")
    assert ordinary["physical_foreground_area"] == pytest.approx(1.0)
    with pytest.raises(ValueError):
        binary_components([[1] * 256 for _ in range(256)], pixel_size=[1e152, 1e152], unit="m")


def test_empty_foreground_has_zero_physical_totals():
    result = binary_components([[0, 0], [0, 0]], pixel_size=[2, 3], unit="mm")
    assert result["physical_foreground_area"] == result["physical_filtered_area"] == 0.0


def test_zero_return_limit_keeps_aggregate_statistics_without_components():
    mask = np.indices((256, 256)).sum(axis=0) % 2 == 0
    result = binary_components(mask, connectivity=4, max_components=0)
    assert result["raw_component_count"] == result["foreground_pixels"] == 32768
    assert result["filtered_component_count"] == result["filtered_pixels"] == 32768
    assert result["returned_component_count"] == result["returned_pixels"] == 0
    assert result["truncated"] is True
