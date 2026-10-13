"""Plot retained synthetic components with the shared Praxis pgfplots style."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import pypdfium2 as pdfium
from examples.image_analysis_demo import bfs_components
from scripts import paper_template, texplot

PALETTE = ["main", "accent", "oigreen", "oiorange", "oisky"]


def build_figure(run, output):
    run, output = Path(run).resolve(), Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"Choose a new output directory: {output}")
    output.mkdir(parents=True)
    mask = json.loads((run / "mask.json").read_text(encoding="utf-8"))
    results = json.loads((run / "measurements.json").read_text(encoding="utf-8"))
    selected = results["filtered_8"]["components"]
    groups = bfs_components(mask, 8)
    accepted = {component["id"]: component for component in selected}
    axis = texplot.Axis(
        "Column (zero-based pixel index)", "Row (zero-based; 0 at top)",
        width="8.75cm", height="7.0cm", xmin=-0.5, xmax=len(mask[0]) - 0.5,
        ymin=-0.5, ymax=len(mask) - 0.5, legend="right",
        extra="y dir=reverse,grid=none,xtick={0,10,20,30,39},ytick={0,8,16,24,31}",
    )
    all_points = [(r, c) for r, row in enumerate(mask) for c, value in enumerate(row) if value]
    included_points = set()
    for label_id, points in enumerate(groups, 1):
        if label_id not in accepted:
            continue
        color = PALETTE[(label_id - 1) % len(PALETTE)]
        rows, cols = [point[0] for point in points], [point[1] for point in points]
        axis.scatter(cols, rows, color=color, mark="square*", size=2.4,
                     label=f"Component {label_id}: {len(points)} px")
        c0, c1, r0, r1 = min(cols) - 0.5, max(cols) + 0.5, min(rows) - 0.5, max(rows) + 0.5
        axis.line([c0, c1, c1, c0, c0], [r0, r0, r1, r1, r0], color=color, width=1.0)
        included_points.update(points)
    excluded = [point for point in all_points if point not in included_points]
    if excluded:
        axis.scatter([c for r, c in excluded], [r for r, c in excluded], color="muted",
                     mark="square*", size=2.4, label="Excluded foreground pixels")
    tex = output / "components.tex"
    tex.write_text(
        r"\documentclass[12pt,border=6pt]{standalone}" +
        r"\usepackage{newtxtext,newtxmath}" + texplot.PREAMBLE +
        r"\begin{document}\begin{tikzpicture}" + axis.tex() +
        r"\end{tikzpicture}\end{document}", encoding="utf-8")
    compiled = output / "compiled"
    receipt = paper_template.compile_paper(tex, None, compiled)
    pdf_path = compiled / "components.pdf"
    document = pdfium.PdfDocument(pdf_path)
    if len(document) != 1:
        raise RuntimeError("Expected one-page synthetic component figure")
    page = document[0]
    png_path = output / "components.png"
    page.render(scale=3).to_pil().save(png_path)
    page.close()
    document.close()
    metadata = {
        "input_mask": "synthetic 32x40 binary mask from the demo run",
        "visible_components": [{"id": row["id"], "pixels": row["pixel_area"], "bbox": row["bbox"]} for row in selected],
        "excluded_foreground_pixels": len(excluded),
        "colors": {str(row["id"]): PALETTE[(row["id"] - 1) % len(PALETTE)] for row in selected},
        "axis_orientation": "row zero at top; pixel centers at integer coordinates; bounding-box edges at half integers",
        "pdf_sha256": receipt["pdf_sha256"],
        "visual_review": "required",
    }
    (output / "figure-data.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build_figure(args.run, args.output), indent=2))


if __name__ == "__main__":
    main()
