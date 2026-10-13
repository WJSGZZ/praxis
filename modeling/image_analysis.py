"""Connected-component measurements for an explicitly supplied 2-D binary mask.

This reports properties of mask regions only. It does not segment images, classify
objects, or certify that components correspond to real particles or organisms.
"""
import math

import numpy as np
from scipy import ndimage


def _integer(value, name, low, high):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise ValueError(f"{name} must be an integer from {low} to {high}")
    value = int(value)
    if not low <= value <= high:
        raise ValueError(f"{name} must be an integer from {low} to {high}")
    return value


def _real_number(value):
    return isinstance(value, (int, float, np.integer, np.floating)) and not isinstance(value, (bool, np.bool_))


def _finite_positive(value, name):
    if not _real_number(value):
        raise ValueError(f"{name} must be an explicit positive finite real number")
    try:
        number = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{name} must be an explicit positive finite real number") from exc
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"{name} must be an explicit positive finite real number")
    return number


def _binary_mask(mask):
    if isinstance(mask, (str, bytes)):
        raise ValueError("mask must be a rectangular 2-D boolean or finite numeric 0/1 array")
    try:
        source = np.asarray(mask)
    except (TypeError, ValueError) as exc:
        raise ValueError("mask must be a rectangular 2-D boolean or finite numeric 0/1 array") from exc
    if source.ndim != 2 or source.shape[0] == 0 or source.shape[1] == 0:
        raise ValueError("mask must be nonempty and two-dimensional")
    if source.shape[0] > 512 or source.shape[1] > 512 or source.size > 65536:
        raise ValueError("mask dimensions must each be at most 512 and total pixels at most 65536")
    if source.dtype.kind == "b":
        return np.array(source, dtype=bool, copy=True)
    if source.dtype.kind not in "iuf":
        raise ValueError("mask must contain booleans or finite real numeric 0/1 values")
    if not np.isfinite(source).all() or not np.logical_or(source == 0, source == 1).all():
        raise ValueError("mask numeric values must be finite and exactly 0 or 1")
    return np.array(source, dtype=bool, copy=True)


def binary_components(mask, connectivity=8, min_pixels=1, exclude_border=False,
                      max_components=200, pixel_size=None, unit=None):
    """Measure connected foreground regions in a 2-D binary mask.

    Coordinates are zero-based ``[row, col]`` pixel-center indices. Bounding
    boxes use ``[row_min, col_min, row_max_exclusive, col_max_exclusive]``.
    ``pixel_size`` is ``[xsize, ysize]`` per pixel; physical coordinates use the
    top-left pixel corner as origin, so centers are shifted by one half pixel.
    Border exclusion has precedence over the minimum-size filter; the two counts
    therefore classify components into mutually exclusive rejection reasons.
    """
    connectivity = _integer(connectivity, "connectivity", 4, 8)
    if connectivity not in (4, 8):
        raise ValueError("connectivity must be 4 or 8")
    min_pixels = _integer(min_pixels, "min_pixels", 1, 65536)
    max_components = _integer(max_components, "max_components", 0, 1000)
    if type(exclude_border) is not bool:
        raise ValueError("exclude_border must be a boolean")
    if unit is not None and (not isinstance(unit, str) or not unit.strip() or len(unit) > 32):
        raise ValueError("unit must be a nonempty string of at most 32 characters")
    if pixel_size is None:
        if unit is not None:
            raise ValueError("unit requires pixel_size")
        scale = None
        cell_area = None
    else:
        if isinstance(pixel_size, (str, bytes)):
            raise ValueError("pixel_size must contain [xsize, ysize]")
        try:
            values = list(pixel_size)
        except TypeError as exc:
            raise ValueError("pixel_size must contain [xsize, ysize]") from exc
        if len(values) != 2:
            raise ValueError("pixel_size must contain [xsize, ysize]")
        sx, sy = (_finite_positive(value, "pixel_size values") for value in values)
        if unit is None:
            raise ValueError("pixel_size requires a nonempty unit")
        cell_area = sx * sy
        if not math.isfinite(cell_area) or cell_area <= 0:
            raise ValueError("pixel_size cell area must be positive, finite, and representable")
        scale = (sx, sy)

    binary = _binary_mask(mask)
    rows, cols = binary.shape
    structure = ndimage.generate_binary_structure(2, 1 if connectivity == 4 else 2)
    labels, raw_count = ndimage.label(binary, structure=structure)
    raw_count = int(raw_count)
    counts = np.bincount(labels.ravel(), minlength=raw_count + 1)
    objects = ndimage.find_objects(labels, max_label=raw_count)
    foreground_pixels = int(counts[1:].sum())
    components = []
    excluded_border = excluded_small = 0
    filtered_count = filtered_pixels = returned_pixels = 0
    filtered_area = 0.0 if scale is not None else None
    foreground_area = foreground_pixels * cell_area if scale is not None else None
    if scale is not None and foreground_pixels and (not math.isfinite(foreground_area) or foreground_area <= 0):
        raise ValueError("physical foreground area must be positive, finite, and representable")

    for label_id in range(1, raw_count + 1):
        pixels = int(counts[label_id])
        region = objects[label_id - 1]
        if pixels == 0 or region is None:
            raise RuntimeError("SciPy returned a missing region for a component label")
        r0, r1 = region[0].start, region[0].stop
        c0, c1 = region[1].start, region[1].stop
        touches = r0 == 0 or c0 == 0 or r1 == rows or c1 == cols
        if exclude_border and touches:
            excluded_border += 1
            continue
        if pixels < min_pixels:
            excluded_small += 1
            continue
        filtered_count += 1
        filtered_pixels += pixels
        if scale is not None:
            area = pixels * cell_area
            if not math.isfinite(area) or area <= 0:
                raise ValueError("physical component area must be positive, finite, and representable")
            filtered_area += area
            if not math.isfinite(filtered_area) or filtered_area <= 0:
                raise ValueError("physical filtered area must be positive, finite, and representable")
        # Only calculate geometric details for components that can appear in
        # the bounded result list. Counts and totals above cover every filter pass.
        if len(components) >= max_components:
            continue
        coordinates = np.argwhere(labels[region] == label_id)
        row_mean = float(coordinates[:, 0].mean() + r0)
        col_mean = float(coordinates[:, 1].mean() + c0)
        item = {
            "id": label_id,
            "pixel_area": pixels,
            "bbox": [int(r0), int(c0), int(r1), int(c1)],
            "centroid": [row_mean, col_mean],
            "touches_border": bool(touches),
        }
        if scale is not None:
            sx, sy = scale
            physical_area = pixels * cell_area
            physical_centroid = [(col_mean + 0.5) * sx, (row_mean + 0.5) * sy]
            if not math.isfinite(physical_area) or physical_area <= 0:
                raise ValueError("physical component area must be positive, finite, and representable")
            if any(not math.isfinite(value) for value in physical_centroid):
                raise ValueError("physical centroid must be finite and representable")
            item["physical_area"] = float(physical_area)
            item["physical_centroid"] = [float(value) for value in physical_centroid]
        components.append(item)
        returned_pixels += pixels

    result = {
        "schema_version": 1,
        "shape": [int(rows), int(cols)],
        "coordinate_contract": "zero-based [row, col] pixel-center indices; bbox is [row_min, col_min, row_max_exclusive, col_max_exclusive]",
        "connectivity": connectivity,
        "filters": {"min_pixels": min_pixels, "exclude_border": exclude_border, "filter_order": "border_then_small; mutually exclusive rejection counts"},
        "raw_component_count": raw_count,
        "foreground_pixels": foreground_pixels,
        "filtered_component_count": filtered_count,
        "filtered_pixels": filtered_pixels,
        "excluded_border_components": excluded_border,
        "excluded_small_components": excluded_small,
        "max_components": max_components,
        "returned_component_count": len(components),
        "returned_pixels": returned_pixels,
        "truncated": len(components) < filtered_count,
        "components": components,
        "interpretation": "Measurements describe connected regions in the supplied binary mask only; no image segmentation, semantic classification, or real-object count is certified.",
    }
    if scale is not None:
        result["physical_foreground_area"] = float(foreground_area)
        result["physical_filtered_area"] = float(filtered_area)
        result["calibration"] = {
            "pixel_size": [scale[0], scale[1]],
            "unit": unit,
            "area_unit": f"{unit}^2",
            "status": "caller_declared_not_verified",
            "origin": "top-left pixel corner",
        }
    else:
        result["area_unit"] = "pixels"
    return result
