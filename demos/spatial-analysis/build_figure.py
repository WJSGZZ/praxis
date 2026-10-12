"""Plot actual synthetic geometry and tight distance bounds in a new directory.

Matplotlib exports a vector PDF and PNG. The saved metadata is read back from
the real plotted artists; coordinate errors are geometric bounds, not CIs.
"""
from __future__ import annotations

import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

from examples.spatial_analysis_demo import _validate, edge_audit, independent_checks


COLORS = {"always": "#0072B2", "possible_only": "#D55E00", "never": "#8B9096", "point": "#20252A"}


def _hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def _line_data(artist):
    return {"x": [float(value) for value in artist.get_xdata()],
            "y": [float(value) for value in artist.get_ydata()],
            "color": artist.get_color(), "linestyle": artist.get_linestyle(),
            "marker": artist.get_marker(), "label": artist.get_label()}


def build(run, output):
    run, output = Path(run).expanduser().absolute(), Path(output).expanduser().absolute()
    if output.exists():
        raise FileExistsError("Figure output must be a new directory: " + str(output))
    report = json.loads((run / "report.json").read_text(encoding="utf-8"))
    verification = json.loads((run / "independent-verification.json").read_text(encoding="utf-8"))
    if report["status"] != "verified_synthetic_spatial_demo" or verification["status"] != "passed":
        raise ValueError("A checked synthetic spatial demo run is required")
    if _hash(run / "input.json") != report["original_input_sha256"]:
        raise ValueError("The original run input changed")
    specification = json.loads((run / "input.json").read_text(encoding="utf-8"))
    _validate(specification)
    edges = json.loads((run / "edge-audit.json").read_text(encoding="utf-8"))["edges"]
    if edges != edge_audit(specification):
        raise ValueError("Saved edge arrays differ from the original geometry")
    nominal = json.loads((run / "nominal-allocation.json").read_text(encoding="utf-8"))
    guaranteed = json.loads((run / "guaranteed-allocation.json").read_text(encoding="utf-8"))
    independent_checks(specification, edges, nominal, guaranteed)
    output.mkdir(parents=True, exist_ok=False)
    # Neutral scientific typography; no branding or project Logo.
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11.5,
                         "axes.titlesize": 13, "axes.labelsize": 11.5,
                         "xtick.labelsize": 10.5, "ytick.labelsize": 11,
                         "pdf.fonttype": 42, "ps.fonttype": 42,
                         "axes.spines.top": False, "axes.spines.right": False})
    figure, (spatial, distance) = plt.subplots(1, 2, figsize=(12.2, 7.3),
                                             gridspec_kw={"width_ratios": [1.23, 1]})
    figure.subplots_adjust(left=.065, right=.97, top=.85, bottom=.26, wspace=.25)
    figure.suptitle("Coverage and location error", x=.065, y=.975, ha="left", fontsize=16)
    figure.text(.065, .925, "Synthetic Cartesian plane · service radius 5 km · independent closed error disks 0.1 km", fontsize=11.5)

    sites = {row["id"]: row for row in specification["sites"]}
    demands = {row["id"]: row for row in specification["demands"]}
    boundary = Circle(sites["C"]["xy"], specification["service_radius_km"],
                      fill=False, edgecolor=COLORS["never"], linestyle=":", linewidth=1.2)
    spatial.add_patch(boundary)
    boundary_note = spatial.text(-5.65, 12.85, "C: 5 km boundary", color="#656B72", fontsize=10.5)
    spatial.set_title("Local service graph", loc="left", pad=10)
    spatial.set(xlabel="x (km)", ylabel="y (km)", xlim=(-6.2, 9.2), ylim=(-1.5, 14))
    spatial.set_aspect("equal", adjustable="box")
    spatial.set_xticks([-5, 0, 5])
    spatial.set_yticks([0, 5, 10])
    spatial.grid(color="#E1E4E7", linewidth=.6)
    spatial.set_axisbelow(True)
    graph_artists = []
    labelled = set()
    # The boundary edge is drawn first; short guaranteed C-w stays visible.
    for row in sorted([row for row in edges if row["possibly_allowed"]], key=lambda row: row["always_allowed"]):
        category = row["classification"]
        text = "Guaranteed edge" if category == "always" else "Possible only: C-u"
        label = text if category not in labelled else "_nolegend_"
        labelled.add(category)
        first, second = sites[row["site"]]["xy"], demands[row["demand"]]["xy"]
        artist, = spatial.plot([first[0], second[0]], [first[1], second[1]],
                               color=COLORS[category], linewidth=2,
                               linestyle="-" if category == "always" else "--", label=label)
        graph_artists.append({"site": row["site"], "demand": row["demand"],
                              "classification": category, "artist": artist})
    facility_points = spatial.scatter([row["xy"][0] for row in sites.values()], [row["xy"][1] for row in sites.values()],
                                      marker="s", s=100, c=COLORS["point"], zorder=4, label="Facility")
    demand_points = spatial.scatter([row["xy"][0] for row in demands.values()], [row["xy"][1] for row in demands.values()],
                                    marker="o", s=75, facecolors="white", edgecolors=COLORS["point"],
                                    linewidths=1.5, zorder=5, label="Demand")
    notes = []
    for identity, dx, dy, alignment in [("A", -.45, -.3, "right"), ("B", .45, -.3, "left"), ("C", .4, .3, "left")]:
        xy = sites[identity]["xy"]
        notes.append(spatial.text(xy[0] + dx, xy[1] + dy, identity, ha=alignment, va="center", color=COLORS["point"]))
    for identity, dx, dy, alignment in [("u", -.45, 0, "right"), ("v", .45, 0, "left"), ("w", .45, -.05, "left")]:
        row = demands[identity]
        notes.append(spatial.text(row["xy"][0] + dx, row["xy"][1] + dy,
                                  f"{identity}: {row['quantity']} units", ha=alignment, va="center", color=COLORS["point"]))
    notes.append(spatial.text(-.35, 5.1, "C-u: 5 km", ha="right", color=COLORS["possible_only"], fontsize=10.5))
    handles, labels = spatial.get_legend_handles_labels()
    spatial.legend(handles, labels, loc="lower left", bbox_to_anchor=(-.025, -.30), ncol=2,
                   frameon=False, fontsize=10.5, columnspacing=1.2, handlelength=2.1)

    distance.set_title("Geometric distance bounds", loc="left", pad=10)
    distance.set_xlabel("Facility-to-demand distance (km)")
    distance.set_xlim(0, 10)
    distance.set_ylim(-.7, len(edges) - .3)
    distance.invert_yaxis()
    distance.set_yticks(range(len(edges)), [row["site"] + "-" + row["demand"] for row in edges])
    distance.grid(axis="x", color="#E1E4E7", linewidth=.6)
    distance.set_axisbelow(True)
    threshold = distance.axvline(specification["service_radius_km"], linestyle=":", color=COLORS["point"], linewidth=1.2)
    distance.text(5.12, -.28, "5 km", color=COLORS["point"], fontsize=10.5)
    interval_artists = []
    for index, row in enumerate(edges):
        color = COLORS[row["classification"]]
        bound, = distance.plot([row["distance_min_km"], row["distance_max_km"]], [index, index],
                                color=color, marker="|", markersize=11, linewidth=2)
        center, = distance.plot([row["distance_km"]], [index], color=color, marker="o", markersize=5, linestyle="None")
        interval_artists.append({"site": row["site"], "demand": row["demand"], "classification": row["classification"],
                                 "bound_artist": bound, "nominal_artist": center})
    distance.text(.0, -.16, "Dots: nominal distance. Bars: tight ±0.2 km bounds.\nGrey: beyond radius in every admissible configuration.",
                  transform=distance.transAxes, fontsize=10.5, va="top", linespacing=1.5)
    figure.text(.065, .035,
                "Capacities (A, B, C): nominal (0, 5, 7), cost 17; all-location guarantee (4, 5, 3), cost 25.", fontsize=11)

    pdf_path, png_path = output / "coverage.pdf", output / "coverage.png"
    # Stable PDF metadata avoids run-time timestamps affecting its identity.
    figure.savefig(pdf_path, format="pdf", metadata={"CreationDate": None, "ModDate": None, "Title": "Coverage and location error"})
    figure.savefig(png_path, format="png", dpi=180)
    handles, labels = spatial.get_legend_handles_labels()
    metadata = {
        "original_input_sha256": report["original_input_sha256"],
        "source_artifact_sha256": {name: _hash(run / name) for name in ["input.json", "edge-audit.json", "nominal-allocation.json", "guaranteed-allocation.json", "independent-verification.json"]},
        "scientific_caption": "A declared synthetic Cartesian plane in km, shown at equal aspect. Squares are facilities and circles are demands. Blue edges remain allowed for every independent radius-0.1-km point error; dashed C-u is nominally allowed at exactly 5 km but can reach 5.2 km. The C circle is its nominal 5-km boundary. Right-hand dots and bars show all nine actual nominal distances and tight geometric bounds, not confidence intervals. Demand v has only B as a possible neighbor.",
        "spatial_axis": {"xlabel": spatial.get_xlabel(), "ylabel": spatial.get_ylabel(),
                         "aspect": spatial.get_aspect(), "xlim": list(spatial.get_xlim()), "ylim": list(spatial.get_ylim())},
        "facilities": {"ids": list(sites), "xy": facility_points.get_offsets().tolist(), "marker": "s", "label": facility_points.get_label(),
                       "facecolors": facility_points.get_facecolors().tolist(), "sizes": facility_points.get_sizes().tolist(),
                       "actual_marker_path_vertices": [path.vertices.tolist() for path in facility_points.get_paths()]},
        "demands": {"ids": list(demands), "xy": demand_points.get_offsets().tolist(), "marker": "o", "label": demand_points.get_label(),
                    "facecolors": demand_points.get_facecolors().tolist(), "edgecolors": demand_points.get_edgecolors().tolist(), "sizes": demand_points.get_sizes().tolist(),
                    "actual_marker_path_vertices": [path.vertices.tolist() for path in demand_points.get_paths()]},
        "service_edges": [{key: value for key, value in row.items() if key != "artist"} | _line_data(row["artist"]) for row in graph_artists],
        "nominal_C_boundary": {"center": list(boundary.center), "radius_km": boundary.radius,
                               "linestyle": boundary.get_linestyle(), "edgecolor": list(boundary.get_edgecolor()),
                               "annotation": boundary_note.get_text(), "annotation_xy": list(boundary_note.get_position())},
        "spatial_annotations": [{"text": item.get_text(), "xy": list(item.get_position())} for item in notes],
        "legend_labels": labels,
        "legend_artist_types": [type(handle).__name__ for handle in handles],
        "distance_axis": {"xlabel": distance.get_xlabel(), "row_labels": [item.get_text() for item in distance.get_yticklabels()],
                          "xlim": list(distance.get_xlim()), "threshold_artist": _line_data(threshold)},
        "distance_series": [{"site": row["site"], "demand": row["demand"], "classification": row["classification"],
                             "bounds": _line_data(row["bound_artist"]), "nominal": _line_data(row["nominal_artist"])} for row in interval_artists],
        "capacity_summary": {"order": report["capacity_order"], "nominal": nominal["capacity"], "guaranteed": guaranteed["capacity"],
                             "nominal_cost": nominal["cost"], "guaranteed_cost": guaranteed["cost"]},
        "figure_generator_sha256": _hash(Path(__file__)),
        "runtime": {name: version(name) for name in ["matplotlib", "numpy"]},
        "artifacts": {"coverage.pdf": _hash(pdf_path), "coverage.png": _hash(png_path)},
        "visual_review": "required",
    }
    if metadata["facilities"]["xy"] != [row["xy"] for row in sites.values()] or metadata["demands"]["xy"] != [row["xy"] for row in demands.values()]:
        raise RuntimeError("Plotted points differ from the original coordinates")
    if len(metadata["distance_series"]) != 9 or metadata["spatial_axis"]["aspect"] != 1:
        raise RuntimeError("Expected all nine distance intervals and an equal-aspect spatial axis")
    if set(labels) != {"Guaranteed edge", "Possible only: C-u", "Facility", "Demand"}:
        raise RuntimeError("Legend labels do not match the intended actual artists")
    _save(output / "figure-data.json", metadata)
    plt.close(figure)
    return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    result = build(arguments.run, arguments.output)
    print(json.dumps({"original_input_sha256": result["original_input_sha256"], "distance_intervals": len(result["distance_series"]),
                      "legend_labels": result["legend_labels"], "visual_review": result["visual_review"]}))
