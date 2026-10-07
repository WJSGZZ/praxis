import math
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts import texplot


def test_axis_collects_series_in_order():
    ax = texplot.Axis("x", "y", xmin=0, xmax=3, ymin=0, ymax=2)
    ax.line([0, 1, 2], [0, 1, 0], label="a").band([0, 1, 2], [0, .5, 0], [1, 1.5, 1]).stairs([1, 2], [0, 1, 3]).hline(1).vline(1)
    tex = ax.tex()
    assert tex.count(r"\addplot") == 5  # line, two band bounds, fill between, stairs
    assert "fill between" in tex and r"\addlegendentry{a}" in tex
    assert tex.index("(0,0) (1,1) (2,0)") < tex.index("fill between")


def test_rejects_non_finite_and_mismatched_data():
    with pytest.raises(ValueError):
        texplot.Axis().line([0, 1], [0, math.nan])
    with pytest.raises(ValueError):
        texplot.Axis().line([0, 1, 2], [0, 1])
    with pytest.raises(ValueError):
        texplot.Axis().stairs([1, 2], [0, 1])


def test_long_series_is_thinned_but_keeps_endpoints():
    n = 5000
    coords = texplot._coords(range(n), [float(i) for i in range(n)], limit=700)
    pts = coords.split(" ")
    assert len(pts) <= 702 and pts[0] == "(0,0)" and pts[-1] == "(4999,4999)"


def test_bar_chart_has_one_series_per_bar_with_labels():
    tex = texplot.hbar_chart(["a", "b, c"], [1.0, 2.0], ["teal", "clay"], "x")
    assert tex.count(r"\addplot") == 2 and "yticklabels={{a},{b, c}}" in tex and "bar shift=0pt" in tex


@pytest.mark.skipif(not (shutil.which("xelatex") or (Path.home() / ".local/bin/tectonic").exists()), reason="no TeX engine")
def test_figure_compiles(tmp_path):
    ax = texplot.Axis("x", "y", xmin=0, xmax=2, ymin=0, ymax=2).line([0, 1, 2], [0, 1, 0], label="a").band([0, 1, 2], [0, .5, 0], [1, 1.5, 1]).hline(1)
    doc = "\\documentclass{article}\n" + texplot.PREAMBLE + "\\begin{document}\n" + texplot.figure_env(ax.tex(), "Test", label="fig:t") + "\\end{document}\n"
    (tmp_path / "t.tex").write_text(doc)
    engine = [shutil.which("xelatex"), "-interaction=nonstopmode", "-halt-on-error"] if shutil.which("xelatex") else [str(Path.home() / ".local/bin/tectonic")]
    res = subprocess.run(engine + ["t.tex"], cwd=tmp_path, capture_output=True, text=True)
    assert res.returncode == 0, res.stdout[-800:] + res.stderr[-800:]
    assert (tmp_path / "t.pdf").exists()
