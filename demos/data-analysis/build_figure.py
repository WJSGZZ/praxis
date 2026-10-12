"""Build a scientific figure from the verified store-week demo's real summaries.

Use a new output directory. This changes presentation, never the model fit.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import pandas as pd
import pypdfium2 as pdfium
from scripts import paper_template, texplot


def build(run, output):
    run, output = Path(run).absolute(), Path(output).absolute()
    report = json.loads((run / "report.json").read_text())
    verification = json.loads((run / "independent-verification.json").read_text())
    if report["status"] != "verified_synthetic_demo" or verification["status"] != "passed":
        raise ValueError("The input must be an independently checked synthetic demo run")
    for name, digest in report["original_input_sha256"].items():
        if hashlib.sha256((run / name).read_bytes()).hexdigest() != digest:
            raise ValueError("Demo input changed: " + name)
    frame = pd.read_csv(run / "store-summary.csv")
    raw = pd.read_csv(run / "observations.csv").merge(
        pd.read_csv(run / "stores.csv"), on="store_id", how="left", validate="many_to_one"
    )
    expected = raw.groupby(["store_id", "campaign"], as_index=False).agg(
        weekly_sales_mean=("sales", "mean"), observations=("sales", "size")
    )
    pd.testing.assert_frame_equal(frame.sort_values("store_id").reset_index(drop=True),
                                  expected.sort_values("store_id").reset_index(drop=True))
    if len(frame) != 12 or set(frame["campaign"]) != {0, 1} or not (frame["observations"] == 4).all():
        raise ValueError("Expected twelve store means, each based on four weeks")
    output.mkdir(parents=True, exist_ok=False)
    ax = texplot.Axis("Campaign status", "Mean weekly sales (units)",
                      width="10.5cm", height="5.4cm", xmin=-.4, xmax=1.4,
                      ymin=40, ymax=65, font_profile="mcm-v3", legend_columns=2,
                      extra="xtick={0,1},xticklabels={No campaign,Campaign}")
    # Grey mean indicators have no legend; they must not take named series slots.
    for group in (0, 1):
        mean = float(frame.loc[frame.campaign == group, "weekly_sales_mean"].mean())
        ax.line([group - .18, group + .18], [mean, mean], color="muted", style="dashed")
    series = []
    for group, name, color, mark in [(0, "No campaign", "main", "*"),
                                      (1, "Campaign", "accent", "square*")]:
        rows = frame.loc[frame.campaign == group].sort_values("store_id")
        if len(rows) != 6:
            raise ValueError("Expected six distinct stores in each category")
        x = [group + (index - 2.5) * .035 for index in range(6)]
        y = rows.weekly_sales_mean.tolist()
        ax.scatter(x, y, color=color, mark=mark, label=name)
        series.append({"label": name, "store_ids": rows.store_id.tolist(), "x": x, "y": y,
                       "color": color, "mark": mark, "observations_per_point": 4})
    if sum(r"\addplot" in part and "forget plot" not in part for part in ax.body) != 2:
        raise RuntimeError("Only the two labelled store series may enter the legend")
    source = (r"\documentclass[12pt,border=6pt]{standalone}\usepackage{newtxtext,newtxmath}" +
              texplot.PREAMBLE + r"\begin{document}\begin{tikzpicture}" + ax.tex() +
              r"\end{tikzpicture}\end{document}")
    tex = output / "store-means.tex"
    tex.write_text(source, encoding="utf-8")
    paper_template.compile_paper(tex, None, output / "compiled")
    pdf_path = output / "compiled/store-means.pdf"
    pdf = pdfium.PdfDocument(pdf_path)
    if len(pdf) != 1:
        raise RuntimeError("Expected one standalone figure page")
    page = pdf[0]
    page.render(scale=3).to_pil().save(output / "store-means.png")
    page.close()
    pdf.close()
    metadata = {"source_summary_sha256": hashlib.sha256((run / "store-summary.csv").read_bytes()).hexdigest(),
                "run_input_sha256": report["original_input_sha256"],
                "series": series, "x_offset": "Deterministic visual separation of six stores; has no quantitative meaning",
                "reference_lines": "Within-category store means, not confidence intervals",
                "caption": "Store means over four weeks. Each point is one synthetic store; six stores per category. Grey dashes show category means. These synthetic associations do not identify a causal campaign effect.",
                "pdf_sha256": hashlib.sha256(pdf_path.read_bytes()).hexdigest(),
                "visual_review": "required"}
    (output / "figure-data.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.run, args.output), indent=2))
