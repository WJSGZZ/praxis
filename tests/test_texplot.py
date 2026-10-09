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


def test_long_series_preserves_narrow_peak_and_all_points():
    n = 5000
    y = [0.] * n
    y[3] = 100.  # The former stride of eight missed this peak.
    pts = texplot._coords(range(n), y).split(" ")
    assert len(pts) == n and pts[3] == "(3,100)"
    assert pts[0] == "(0,0)" and pts[-1] == "(4999,0)"
    with pytest.raises(ValueError, match='silent thinning'):
        texplot._coords(range(n), y, limit=700)


def test_plot_rejects_empty_series_and_invalid_unsampled_point():
    with pytest.raises(ValueError, match='empty'):
        texplot._coords([], [])
    y = [0.] * 5000
    y[3] = math.nan
    with pytest.raises(ValueError, match='non-finite'):
        texplot._coords(range(5000), y)


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


def test_signed_bars_and_text_escaping():
    from scripts import texplot
    tex = texplot.hbar_chart(['a_b', '50% rule'], [-0.4, 0.9], ['accent', 'main'], 'effect', xmax=1.2, decimals=1, unit='')
    assert 'xmin=-0.52' in tex and 'anchor=east' in tex and 'anchor=west' in tex
    assert 'a\\_b' in tex and '50\\% rule' in tex
    assert texplot.tex_text('x_1 and 5%') == 'x\\_1 and 5\\%' and texplot.tex_text('$x_1$ \\alpha 5%') == '$x_1$ \\alpha 5%'
    positive = texplot.hbar_chart(['p', 'q'], [24.14, 16.01], ['main', 'muted'], 'L', xmax=31.38)
    assert 'xmin=0' in positive and 'anchor=east' not in positive


def test_unlabelled_axis_warns():
    import pytest
    from scripts.texplot import Axis
    with pytest.warns(UserWarning, match='label'):
        Axis()
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter('error')
        Axis('Time (s)', 'Temperature (°C)')
