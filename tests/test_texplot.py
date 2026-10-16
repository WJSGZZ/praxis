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


@pytest.mark.parametrize("kind", ["line", "band", "stairs", "scatter"])
@pytest.mark.parametrize("label", [None, ""])
def test_context_series_does_not_take_the_next_named_legend_image(kind, label):
    ax = texplot.Axis("Time (s)", "Value (m)")
    if kind == "band":
        ax.band([0, 1], [0, 0], [1, 1], color="muted", label=label)
    elif kind == "stairs":
        ax.stairs([0, 1], [0, .5, 1], color="muted", label=label)
    else:
        getattr(ax, kind)([0, 1], [0, 0], color="muted", label=label)
    ax.line([0, 1], [1, 2], color="main", label="Measured")
    # PGFplots associates legend text with remembered plots, not with its
    # adjacent addplot. The grey reference and both band bounds are excluded.
    remembered = [plot for plot in ax.body if r"\addplot[" in plot
                  and "forget plot" not in plot]
    assert len(remembered) == 1
    assert "color=main" in remembered[0]
    assert r"\addlegendentry{Measured}" in remembered[0]


def test_named_band_keeps_its_fill_legend_but_not_its_hidden_bounds():
    ax = texplot.Axis("Time (s)", "Value (m)")
    ax.band([0, 1], [0, 0], [1, 1], color="accent", label="Range")
    remembered = [plot for plot in ax.body if "forget plot" not in plot]
    assert len(remembered) == 1
    assert "fill=accent" in remembered[0]
    assert r"\addlegendentry{Range}" in remembered[0]


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


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_numpy_single_precision_nonfinite_values_are_rejected_in_steps(value):
    import numpy as np
    with pytest.raises(ValueError, match="non-finite"):
        texplot.Axis("Time (s)", "Value (m)").stairs([np.float32(value)], [0, 1])


@pytest.mark.skipif(not (shutil.which("xelatex") or (Path.home() / ".local/bin/tectonic").exists()), reason="no TeX engine")
def test_plain_axis_and_legend_labels_compile_as_literal_text(tmp_path):
    ax = texplot.Axis("x_1 (%)", "Flow & count").line([0, 1], [0, 1], label="group#1")
    doc = "\\documentclass[12pt]{article}\n" + texplot.PREAMBLE + "\\begin{document}\n" + texplot.figure_env(ax.tex(), "Literal labels") + "\\end{document}\n"
    source = tmp_path / "labels.tex"
    source.write_text(doc)
    engine = [shutil.which("xelatex"), "-interaction=nonstopmode", "-halt-on-error"] if shutil.which("xelatex") else [str(Path.home() / ".local/bin/tectonic")]
    result = subprocess.run(engine + [source.name], cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout[-800:] + result.stderr[-800:]
    from pypdf import PdfReader
    text = PdfReader(tmp_path / "labels.pdf").pages[0].extract_text()
    assert all(token in text for token in ("x_1 (%)", "Flow & count", "group#1"))


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
@pytest.mark.parametrize("font_profile", [None, "mcm-v3"])
def test_figure_compiles(tmp_path, font_profile):
    ax = texplot.Axis("Time", "Density", xmin=0, xmax=2, ymin=0, ymax=2, font_profile=font_profile).line([0, 1, 2], [0, 1, 0], label="series").band([0, 1, 2], [0, .5, 0], [1, 1.5, 1]).hline(1).note(1, 1, "note").label(2, 0, "direct")
    doc = "\\documentclass[12pt]{article}\n" + texplot.PREAMBLE + "\\begin{document}\n" + texplot.figure_env(ax.tex(), "Test", label="fig:t") + "\\end{document}\n"
    (tmp_path / "t.tex").write_text(doc)
    engine = [shutil.which("xelatex"), "-interaction=nonstopmode", "-halt-on-error"] if shutil.which("xelatex") else [str(Path.home() / ".local/bin/tectonic")]
    res = subprocess.run(engine + ["t.tex"], cwd=tmp_path, capture_output=True, text=True)
    assert res.returncode == 0, res.stdout[-800:] + res.stderr[-800:]
    assert (tmp_path / "t.pdf").exists()
    if font_profile == 'mcm-v3':
        from pypdf import PdfReader
        measured = {}
        def visitor(text, cm, tm, font, size):
            for token in ('Time', 'Density', 'series', 'note', 'direct'):
                if token in text:
                    measured[token] = size * (cm[0] ** 2 + cm[1] ** 2) ** .5 * 72.27 / 72
        PdfReader(tmp_path / 't.pdf').pages[0].extract_text(visitor_text=visitor)
        assert set(measured) == {'Time', 'Density', 'series', 'note', 'direct'}
        assert all(value == pytest.approx(12, abs=.02) for value in measured.values())


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


def _coordinate_sets(tex):
    import re
    return [[tuple(map(float, point)) for point in re.findall(r'\(([-+\deE.]+),([-+\deE.]+)\)', block)]
            for block in re.findall(r'coordinates\s*\{([^}]*)\}', tex)]


def test_errorbar_preserves_points_and_absolute_asymmetric_intervals():
    tex = texplot.Axis('Time (s)', 'Flow (L/s)').errorbar(
        [1, 3], [5, 8], [3, 7.5], [6, 12], interval='95% bootstrap confidence interval', label='Estimate').tex()
    # Offsets in PGFplots reconstruct the original bounds, rather than treating
    # the bounds themselves as error magnitudes.
    import re
    rows = re.search(r'\{x y lower upper\n(.*?)\n\};', tex, re.S).group(1)
    data = [list(map(float, row.split())) for row in rows.splitlines()]
    assert [(x, y, y-lower, y+upper) for x, y, lower, upper in data] == [(1, 5, 3, 6), (3, 8, 7.5, 12)]
    assert 'Interval meaning: 95% bootstrap confidence interval' in tex
    assert r'\addlegendentry{Estimate (95\% bootstrap confidence interval)}' in tex
    with pytest.raises(TypeError, match='interval'):
        texplot.Axis('x', 'y').errorbar([1], [2], [1], [3])
    for kwargs in ({'interval': ''}, {'interval': 'range', 'lo': [3]},
                   {'interval': 'range', 'hi': [math.nan]}, {'interval': 'range', 'lo': []}):
        inputs = dict(x=[1], y=[2], lo=[1], hi=[3], interval='range')
        inputs.update(kwargs)
        with pytest.raises(ValueError):
            texplot.Axis('x', 'y').errorbar(**inputs)


def test_grouped_bars_preserve_category_and_series_identity():
    tex = texplot.grouped_bar_chart(['a_1', 'b'], {'Observed': [2, -3], 'Predicted': [4, 1]},
                                    'Policy', 'Cost (USD)', colors=['main', 'accent'])
    assert _coordinate_sets(tex) == [[(0, 2), (1, -3)], [(0, 4), (1, 1)]]
    assert 'xticklabels={{a\\_1},{b}}' in tex and 'ymin=-3.84' in tex
    assert tex.index(r'\addlegendentry{Observed}') < tex.index(r'\addlegendentry{Predicted}')
    for categories, series, colors in [([], {'A':[1]}, None), (['a'], {'A': [1, 2]}, None),
                                        (['a'], {'A':[math.inf]}, None), (['a'], {'A':[1]}, [])]:
        with pytest.raises(ValueError):
            texplot.grouped_bar_chart(categories, series, 'Category', 'Value', colors=colors)


def test_histogram_counts_edges_and_density_without_dropping_samples():
    samples, edges = [0, .5, 1, 2.5, 3], [0, 1, 3]
    counts = texplot.Axis('Length (m)', 'Frequency').histogram(samples, edges).tex()
    density = texplot.Axis('Length (m)', 'Density (1/m)').histogram(samples, edges, density=True).tex()
    assert _coordinate_sets(counts) == [[(0, 2), (1, 3), (3, 0)]]
    assert _coordinate_sets(density) == [[(0, .4), (1, .3), (3, 0)]]
    assert .4 * (1-0) + .3 * (3-1) == pytest.approx(1)
    for bad_samples, bad_edges in [([], edges), ([4], edges), ([math.nan], edges),
                                     ([0], [0, 0, 1]), ([0], [0, math.inf])]:
        with pytest.raises(ValueError):
            texplot.Axis('x', 'y').histogram(bad_samples, bad_edges)


def test_boxplot_uses_sample_quartiles_whiskers_and_retains_outlier():
    # Linear quartiles of these nine observations are Q1=2, median=4, Q3=6;
    # the upper fence is 12, so 100 is an outlier and the top whisker is 7.
    tex = texplot.Axis('Group', 'Length (m)').boxplot([0, 1, 2, 3, 4, 5, 6, 7, 100], position=2, width=1).tex()
    coords = _coordinate_sets(tex)
    assert coords[0] == [(1.5, 2), (1.5, 6), (2.5, 6), (2.5, 2), (1.5, 2)]
    assert coords[1] == [(1.5, 4), (2.5, 4)]
    assert coords[2] == [(2, 0), (2, 2)] and coords[3] == [(2, 6), (2, 7)]
    assert coords[-1] == [(2, 100)]
    assert _coordinate_sets(texplot.Axis('x', 'y').boxplot([5]).tex())[0] == [(.75,5),(.75,5),(1.25,5),(1.25,5),(.75,5)]
    texplot.Axis('x', 'y').boxplot([0, 1], whisker=0)  # Interpolated quartile fallback.
    for samples, kwargs in [([], {}), ([math.inf], {}), ([1], {'width': 0}), ([1], {'whisker': -1})]:
        with pytest.raises(ValueError):
            texplot.Axis('x', 'y').boxplot(samples, **kwargs)


def test_shared_panels_preserve_all_series_and_one_truthful_legend():
    a = texplot.Axis('Time (s)', 'Flow (L/s)').band([0,1], [0,0], [2,2], color='muted').line([0,1], [1,2], label='Observed')
    b = texplot.Axis('Time (s)', 'Flow (L/s)').line([2,3], [4,5], label='Observed').line([2,3], [3,4], color='accent', label='Predicted')
    original = a.tex(), b.tex()
    tex = texplot.shared_legend_panels([a,b], ['(a) Start', '(b) End'])
    assert _coordinate_sets(tex) == _coordinate_sets(original[0]) + _coordinate_sets(original[1])
    assert tex.count(r'\addlegendentry{Observed}') == tex.count(r'\addlegendentry{Predicted}') == 1
    assert tex.count(r'\addlegendimage') == 2 and tex.count('legend to name=') == 1
    assert r'\addlegendimage{color=main,line width=1.1pt,no marks}\addlegendentry{Observed}' in tex
    assert (a.tex(), b.tex()) == original  # Combining panels does not mutate them.
    import re
    another = texplot.shared_legend_panels([a,b], ['(a) Other start', '(b) Other end'])
    assert re.search('legend to name=([^,]+)', tex).group(1) != re.search('legend to name=([^,]+)', another).group(1)
    with pytest.raises(ValueError, match='Conflicting'):
        texplot.shared_legend_panels([a, texplot.Axis('x','y').line([0],[1], color='accent',label='Observed')], ['a','b'])
    for axes, titles, kwargs in [([], [], {}), ([a], [], {}), ([a], ['a'], {'columns':0}),
                                ([a], ['a'], {'columns':1,'name':'bad name'})]:
        with pytest.raises(ValueError):
            texplot.shared_legend_panels(axes, titles, **kwargs)


def test_diverging_heatmap_preserves_orientation_values_and_reference_center():
    tex = texplot.diverging_heatmap([[-2,3],[4,-1]], [10,20], [100,200], 'X (m)', 'Y (m)', center=1, limit=4)
    import re
    rows = re.search(r'\{x y c\n(.*?)\n\};', tex, re.S).group(1)
    assert [tuple(map(float,row.split())) for row in rows.splitlines() if row] == [(10,100,-2),(20,100,3),(10,200,4),(20,200,-1)]
    assert 'point meta min=-3,point meta max=5' in tex
    assert 'rgb255(1cm)=(247,247,247)' in tex
    for values, x, y, kwargs in [([[1,2]], [0,1], [0,1], {}), ([[1,2],[3,math.nan]], [0,1], [0,1], {}),
                                  ([[1,2],[3,4]], [1,0], [0,1], {}), ([[1,2],[3,4]], [0,1], [0,1], {'limit':2}),
                                  ([[1,2,3],[3,4,5]], [0,1,3], [0,1], {})]:
        with pytest.raises(ValueError):
            texplot.diverging_heatmap(values,x,y,'X','Y',**kwargs)


@pytest.mark.skipif(not (shutil.which('xelatex') or (Path.home()/'.local/bin/tectonic').exists()), reason='no TeX engine')
def test_new_chart_kinds_compile_with_existing_preamble(tmp_path):
    axes = [texplot.Axis('Time (s)', 'Flow (L/s)', width='4cm').line([0,1],[2,3],label='Observed'),
            texplot.Axis('Time (s)', 'Flow (L/s)', width='4cm').line([2,3],[3,4],label='Observed')]
    charts = [texplot.Axis('Time (s)', 'Flow (L/s)').errorbar([0,1],[2,3],[1,2.5],[3,5],interval='Scenario range').tex(),
              texplot.grouped_bar_chart(['A','B'], {'Baseline':[2,3], 'Policy':[3,1]}, 'Policy', 'Cost (USD)'),
              texplot.Axis('Length (m)', 'Frequency').histogram([0,.5,1,2,3],[0,1,3]).tex(),
              texplot.Axis('Group', 'Length (m)').boxplot([0,1,2,3,4,5,6,7,100]).tex(),
              texplot.shared_legend_panels(axes, ['(a) Start', '(b) End']),
              texplot.diverging_heatmap([[-2,1],[2,-1]],[0,1],[0,1],'X (m)','Y (m)',cbar_label='Change (m)')]
    source = tmp_path/'new-charts.tex'
    source.write_text(r'\documentclass[12pt]{article}' + '\n' + texplot.PREAMBLE +
                      '\n' + r'\begin{document}' + '\n' +
                      '\n\\clearpage\n'.join(texplot.figure_env(chart, f'Chart {i+1}') for i,chart in enumerate(charts)) +
                      r'\end{document}', encoding='utf-8')
    engine = [shutil.which('xelatex'), '-interaction=nonstopmode', '-halt-on-error'] if shutil.which('xelatex') else [str(Path.home()/'.local/bin/tectonic')]
    result = subprocess.run(engine+[source.name], cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout[-1000:] + result.stderr[-1000:]
    from pypdf import PdfReader
    pdf = PdfReader(source.with_suffix('.pdf'))
    assert len(pdf.pages) == 6
    assert all(f'Chart {i+1}' in page.extract_text() for i,page in enumerate(pdf.pages))


def test_legacy_preamble_bytes_remain_unchanged():
    import hashlib
    # Embedded historical style blocks expand this exact preamble.
    assert hashlib.sha256(texplot.PREAMBLE.encode()).hexdigest() == '89da7b29a2e6c93b6a1674e3980da5cd7dea72bceadb2dd0bd41ac586dcd15c5'
