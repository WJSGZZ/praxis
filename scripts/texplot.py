"""Generate publication figures as pgfplots/TikZ source, so the plot text uses the paper's own fonts.

Data are written as inline coordinates, so a figure is reproducible from the .tex file alone.
Preamble needs: pgfplots (compat 1.17+) with the fillbetween, groupplots and positioning TikZ libraries, and the
colors defined by PREAMBLE_COLORS (Okabe–Ito-style, safe for colour-blind readers and for grayscale printing when
combined with the dash styles used here).
"""
from __future__ import annotations

import warnings

import math
import re
import hashlib
from bisect import bisect_right
from typing import Iterable, Sequence

PREAMBLE = r"""\usepackage{pgfplots}
\pgfplotsset{compat=1.17}
\usepgfplotslibrary{fillbetween,groupplots}
\usetikzlibrary{arrows.meta,positioning,calc}
""" + "\n".join(
    r"\definecolor{%s}{HTML}{%s}" % (name, code)
    for name, code in [
        # Colour carries meaning: main = the quantity of interest, accent = the contrast or highlight, muted = context/bounds.
        # Okabe-Ito blue and vermilion stay distinguishable for colour-blind readers and in grayscale (with the dash styles).
        ("main", "0072B2"), ("accent", "D55E00"), ("muted", "7A7F85"), ("light", "B8BDC2"),
        ("oigreen", "009E73"), ("oiorange", "E69F00"), ("oisky", "56B4E9"), ("oiyellow", "F0E442"),
        # project identity colours, for cover graphics only
        ("teal", "17766E"), ("clay", "9E6440"), ("slate", "5D696E"), ("sand", "AAA69B"),
    ]
)

DASH = {"solid": "", "dashed": "dashed", "dotted": "dotted", "dashdot": "dash pattern=on 4pt off 2pt on 1pt off 2pt"}


def _font_profile(tex: str, profile: str | None) -> str:
    """Select ordinary plot-text roles without changing archived defaults or data.

    Final imported-figure scaling must still be checked in the paper PDF.
    """
    if profile is None:
        return tex
    if profile != 'mcm-v3':
        raise ValueError('Unknown plot font profile')
    return re.sub(r'font=\\(?:scriptsize|footnotesize|small)\b',
                  lambda _: r'font=\normalsize', tex)


def tex_text(s: str) -> str:
    """Escape the characters that break LaTeX in plain labels (%, &, #, _). Text that already contains a backslash or a $ is left alone,
    because its author is writing LaTeX."""
    if "\\" in s or "$" in s:
        return s
    for ch in "%&#_":
        s = s.replace(ch, "\\" + ch)
    return s


def _fmt(v: float) -> str:
    if v is None or not math.isfinite(v):
        raise ValueError("non-finite value in plotted data")
    return "%.6g" % v


def _coords(x: Iterable[float], y: Iterable[float], limit: int | None = None) -> str:
    """Serialize every point; size limits must never silently remove evidence."""
    xs, ys = list(x), list(y)
    if len(xs) != len(ys):
        raise ValueError("x and y differ in length")
    if not xs:
        raise ValueError("plotted series is empty")
    # Validate the entire input, including points that an old stride skipped.
    coords = [(float(a), float(b)) for a, b in zip(xs, ys)]
    if not all(math.isfinite(a) and math.isfinite(b) for a, b in coords):
        raise ValueError("non-finite value in plotted data")
    if limit is not None and (limit < 1 or len(coords) > limit):
        raise ValueError("point limit exceeded; explicitly prepare and document aggregation instead of silent thinning")
    return " ".join("(%s,%s)" % (_fmt(a), _fmt(b)) for a, b in coords)


class Axis:
    """One pgfplots axis; only series with an explicit label enter its legend.

    Unlabelled context must not consume PGFplots' deferred legend-image queue.
    """

    def __init__(self, xlabel: str = "", ylabel: str = "", *, width: str = r"0.84\linewidth", height: str = "5.4cm",
                 xmin=None, xmax=None, ymin=None, ymax=None, legend: str | None = "above", legend_columns: int | None = None,
                 extra: str = "", font_profile: str | None = None):
        _font_profile('', font_profile)
        self.font_profile = font_profile
        if (not xlabel or not ylabel) and "label" not in extra:
            warnings.warn("Axis without an x or y label: every axis needs a quantity and its unit, e.g. 'Time (s)'", stacklevel=2)
        self.opts = [f"width={width}", f"height={height}", "scale only axis", f"xlabel={{{tex_text(str(xlabel))}}}", f"ylabel={{{tex_text(str(ylabel))}}}",
                     "axis lines=left", "axis line style={gray!70}", "grid=major", "grid style={gray!18}",
                     "tick label style={font=\\footnotesize}", "label style={font=\\small}",
                     "every axis plot/.append style={line cap=round}", "clip=false"]
        for key, val in (("xmin", xmin), ("xmax", xmax), ("ymin", ymin), ("ymax", ymax)):
            if val is not None:
                self.opts.append(f"{key}={_fmt(val)}")
        if legend:
            base = "legend style={font=\\footnotesize,draw=none,fill=none,"
            where = {"above": "at={(0.5,1.04)},anchor=south," + ("" if legend_columns else "legend columns=-1,") + "/tikz/every even column/.append style={column sep=8pt},",
                     "right": "at={(1.02,0.5)},anchor=west,",
                     "north east": "at={(0.98,0.97)},anchor=north east,draw=gray!50,fill=white,",
                     "south west": "at={(0.02,0.03)},anchor=south west,draw=gray!50,fill=white,",
                     "south east": "at={(0.98,0.03)},anchor=south east,draw=gray!50,fill=white,",
                     "north west": "at={(0.02,0.97)},anchor=north west,draw=gray!50,fill=white,"}[legend]
            cols = f"legend columns={legend_columns}," if legend_columns else ""
            self.opts.append(base + where + cols + "}")
        if extra:
            self.opts.append(extra)
        self.body: list[str] = []
        self._band = 0
        self._legend_entries: list[tuple[str, tuple[str, ...]]] = []

    def _remember_legend(self, label, options):
        if label:
            self._legend_entries.append((str(label), tuple(options)))

    def line(self, x, y, color="main", style="solid", width=1.1, label=None, marks=None):
        opt = [f"color={color}", f"line width={width}pt"]
        if DASH[style]:
            opt.append(DASH[style])
        if marks:
            opt += [f"mark={marks}", "mark size=1.8pt"]
        else:
            opt.append("no marks")
        if not label:
            opt.append("forget plot")
        self._remember_legend(label, opt)
        self.body.append(r"\addplot[%s] coordinates {%s};" % (",".join(opt), _coords(x, y))
                         + (r"\addlegendentry{%s}" % tex_text(str(label)) if label else ""))
        return self

    def band(self, x, lo, hi, color="main", opacity=0.14, label=None):
        self._band += 1
        a, b = f"lo{self._band}", f"hi{self._band}"
        self.body.append(r"\addplot[name path=%s,draw=none,forget plot] coordinates {%s};" % (a, _coords(x, lo)))
        self.body.append(r"\addplot[name path=%s,draw=none,forget plot] coordinates {%s};" % (b, _coords(x, hi)))
        opt = [f"fill={color}", f"fill opacity={opacity}"]
        if not label:
            opt.append("forget plot")
        self._remember_legend(label, [*opt, "area legend"])
        self.body.append(r"\addplot[%s] fill between[of=%s and %s];" % (",".join(opt), a, b)
                         + (r"\addlegendentry{%s}" % tex_text(str(label)) if label else ""))
        return self

    def stairs(self, values: Sequence[float], edges: Sequence[float], color="main", width=1.3, label=None, style="solid"):
        """Piecewise-constant series: values[i] holds on [edges[i], edges[i+1]]."""
        if len(edges) != len(values) + 1:
            raise ValueError("edges must have one more entry than values")
        pts = []
        for i, v in enumerate(values):
            pts += [(edges[i], v), (edges[i + 1], v)]
        opt = [f"color={color}", f"line width={width}pt", "no marks"] + ([DASH[style]] if DASH[style] else [])
        if not label:
            opt.append("forget plot")
        self._remember_legend(label, opt)
        self.body.append(r"\addplot[%s] coordinates {%s};" % (",".join(opt), " ".join("(%s,%s)" % (_fmt(a), _fmt(b)) for a, b in pts))
                         + (r"\addlegendentry{%s}" % tex_text(str(label)) if label else ""))
        return self

    def scatter(self, x, y, color="main", mark="*", size=2.0, label=None):
        opt = ["only marks", f"mark={mark}", f"mark size={size}pt", f"color={color}"]
        if not label:
            opt.append("forget plot")
        self._remember_legend(label, opt)
        self.body.append(r"\addplot[%s] coordinates {%s};" % (",".join(opt), _coords(x, y, limit=5000))
                         + (r"\addlegendentry{%s}" % tex_text(str(label)) if label else ""))
        return self

    def errorbar(self, x, y, lo, hi, *, interval: str, color="main", label=None, mark="*"):
        """Plot absolute lower/upper bounds; ``interval`` names their meaning.

        Bounds may describe confidence, spread or scenarios; this method does
        not estimate them or infer a statistical interpretation. The meaning
        appears in the legend, alongside the optional series name.
        """
        if not isinstance(interval, str) or not interval.strip() or '\n' in interval or '\r' in interval:
            raise ValueError("Declare the interval meaning as a nonempty single line")
        xs, ys, lows, highs = map(list, (x, y, lo, hi))
        _coords(xs, ys)
        _coords(xs, lows)
        _coords(xs, highs)
        rows = []
        for a, b, lower, upper in zip(xs, ys, lows, highs):
            if not lower <= b <= upper:
                raise ValueError("Each errorbar bound must contain its plotted value")
            rows.append("%s %s %s %s" % (_fmt(a), _fmt(b), _fmt(b-lower), _fmt(upper-b)))
        options = [f"color={color}", f"mark={mark}", "only marks"]
        legend_label = f"{label} ({interval.strip()})" if label else interval.strip()
        self._remember_legend(legend_label, options)
        self.body.append("% Interval meaning: " + interval.strip() + '\n' +
                         r"\addplot[%s,error bars/y dir=both,error bars/y explicit] " % ','.join(options) +
                         "table[x=x,y=y,y error minus=lower,y error plus=upper] {x y lower upper\n" +
                         '\n'.join(rows) + '\n};' +
                         (r"\addlegendentry{%s}" % tex_text(legend_label)))
        return self

    def histogram(self, samples, edges, *, density=False, color="main", label=None):
        """Count [left,right) bins, including the final right edge in the last.

        Explicit edges and rejection of outside samples prevent silent clipping.
        Density integrates to one even for bins of unequal widths.
        """
        samples, edges = list(samples), list(edges)
        if not samples or len(edges) < 2:
            raise ValueError("Histogram needs samples and at least two edges")
        if not all(math.isfinite(float(v)) for v in [*samples, *edges]):
            raise ValueError("non-finite value in histogram data")
        if any(a >= b for a, b in zip(edges, edges[1:])):
            raise ValueError("Histogram edges must strictly increase")
        counts = [0] * (len(edges)-1)
        for value in samples:
            if value < edges[0] or value > edges[-1]:
                raise ValueError("Histogram sample outside explicit edges")
            counts[min(bisect_right(edges, value)-1, len(counts)-1)] += 1
        heights = [count / (len(samples)*(edges[i+1]-edges[i])) if density else count
                   for i, count in enumerate(counts)]
        options = ["ybar interval", f"fill={color}!35", f"draw={color}"]
        self._remember_legend(label, options)
        if not label:
            options.append("forget plot")
        self.body.append(r"\addplot[%s] coordinates {%s};" %
                         (','.join(options), _coords(edges, heights+[0])) +
                         (r"\addlegendentry{%s}" % tex_text(str(label)) if label else ""))
        return self

    def boxplot(self, samples, *, position=1, width=.5, whisker=1.5, color="main", label=None):
        """Tukey box, linear-interpolated quartiles and explicit outlier points.

        Whiskers end at actual samples within ``whisker * IQR`` of the box,
        or at the quartile when interpolation leaves no sample on that side.
        Coordinates are drawn directly, without altering the archived preamble.
        """
        values = sorted(float(v) for v in samples)
        if not values or not all(math.isfinite(v) for v in values):
            raise ValueError("Boxplot needs nonempty finite samples")
        if not all(math.isfinite(float(v)) for v in (position, width, whisker)) or width <= 0 or whisker < 0:
            raise ValueError("Boxplot position, width and whisker must be finite; width positive, whisker nonnegative")
        def quantile(p):
            index = (len(values)-1)*p
            lower = math.floor(index)
            return values[lower] + (values[math.ceil(index)]-values[lower])*(index-lower)
        q1, median, q3 = (quantile(p) for p in (.25, .5, .75))
        iqr = q3-q1
        low = min((v for v in values if q1-whisker*iqr <= v <= q1), default=q1)
        high = max((v for v in values if q3 <= v <= q3+whisker*iqr), default=q3)
        left, right = position-width/2, position+width/2
        # Each primitive remains a normal pgfplots series, so bounds include
        # whiskers/outliers and the numerical coordinates remain inspectable.
        box = _coords([left, left, right, right, left], [q1, q3, q3, q1, q1])
        options = [f"draw={color}", f"fill={color}!20", "no marks"]
        self._remember_legend(label, [*options, "area legend"])
        self.body.append(r"\addplot[%s] coordinates {%s};" %
                         (','.join(options + ([] if label else ['forget plot'])), box) +
                         (r"\addlegendentry{%s}" % tex_text(str(label)) if label else ""))
        for xs, ys in (([left, right], [median, median]), ([position, position], [low, q1]),
                       ([position, position], [q3, high]), ([left, right], [low, low]),
                       ([left, right], [high, high])):
            self.body.append(r"\addplot[draw=%s,no marks,forget plot] coordinates {%s};" % (color, _coords(xs, ys)))
        outliers = [v for v in values if v < low or v > high]
        if outliers:
            self.body.append(r"\addplot[only marks,mark=o,color=%s,forget plot] coordinates {%s};" %
                             (color, _coords([position]*len(outliers), outliers)))
        return self

    def hline(self, y, style="dotted", color="black", width=0.8):
        d = (", " + DASH[style]) if DASH[style] else ""
        self.body.append(r"\draw[%s, line width=%spt%s] ({rel axis cs:0,0}|-{axis cs:0,%s}) -- ({rel axis cs:1,0}|-{axis cs:0,%s});" % (color, width, d, _fmt(y), _fmt(y)))
        return self

    def vline(self, x, style="dotted", color="black", width=0.8):
        d = (", " + DASH[style]) if DASH[style] else ""
        self.body.append(r"\draw[%s, line width=%spt%s] ({axis cs:%s,0}|-{rel axis cs:0,0}) -- ({axis cs:%s,0}|-{rel axis cs:0,1});" % (color, width, d, _fmt(x), _fmt(x)))
        return self

    def note(self, x, y, text, anchor="south west"):
        self.body.append(r"\node[anchor=%s,font=\footnotesize] at (axis cs:%s,%s) {%s};" % (anchor, _fmt(x), _fmt(y), tex_text(text)))
        return self

    def label(self, x, y, text, color="black", anchor="west", dx="3pt", dy="0pt"):
        """Direct label next to a curve (preferred to a legend when there are few series)."""
        self.body.append(r"\node[anchor=%s,font=\footnotesize,text=%s,xshift=%s,yshift=%s] at (axis cs:%s,%s) {%s};" % (anchor, color, dx, dy, _fmt(x), _fmt(y), tex_text(text)))
        return self

    def tex(self) -> str:
        return _font_profile("\\begin{axis}[%s]\n%s\n\\end{axis}" % (",\n ".join(self.opts), "\n".join(self.body)), self.font_profile)


def figure_env(axes_tex: str, caption: str, *, placement: str = "htbp", label: str | None = None) -> str:
    """Wrap pgfplots axes in a figure with a caption below (and an optional label for cross-references)."""
    lab = "\\label{%s}" % label if label else ""
    return "\\begin{figure}[%s]\\centering\n\\begin{tikzpicture}\n%s\n\\end{tikzpicture}\n\\caption{%s}%s\n\\end{figure}\n" % (placement, axes_tex, caption, lab)


def grouped_bar_chart(categories, series, xlabel, ylabel, *, colors=None,
                      width=r"0.72\linewidth", height="5cm", font_profile=None):
    """A dict of named series, in insertion order, at integer category positions."""
    categories = list(categories)
    if not categories or not series:
        raise ValueError("Grouped bars need categories and named series")
    values = {str(label): list(data) for label, data in series.items()}
    if any(not label.strip() for label in values) or len(values) != len(series):
        raise ValueError("Grouped bar series labels must be nonempty and distinct")
    for data in values.values():
        if len(data) != len(categories):
            raise ValueError("Grouped bar data must match the categories")
        _coords(range(len(categories)), data)
    palette = list(colors) if colors is not None else ["main", "accent", "oigreen", "oiorange", "muted"]
    if len(palette) < len(values) or any(not isinstance(c, str) or not c.strip() for c in palette):
        raise ValueError("Supply one nonempty color per grouped bar series")
    ymin = min(0, min(min(data) for data in values.values()))
    ymax = max(0, max(max(data) for data in values.values()))
    padding = (ymax-ymin)*.12 or 1
    ax = Axis(xlabel, ylabel, width=width, height=height, ymin=ymin-padding if ymin < 0 else 0,
              ymax=ymax+padding, font_profile=font_profile,
              extra=("ybar,bar width=8pt,enlarge x limits=0.25,xtick={%s},xticklabels={%s}" %
                     (','.join(str(i) for i in range(len(categories))),
                      ','.join('{%s}' % tex_text(str(c)) for c in categories))))
    for (label, data), color in zip(values.items(), palette):
        ax.body.append(r"\addplot[fill=%s!65,draw=%s] coordinates {%s};\addlegendentry{%s}" %
                       (color, color, _coords(range(len(categories)), data), tex_text(label)))
    return ax.tex()


def shared_legend_panels(axes: Sequence[Axis], titles: Sequence[str], *, columns=2,
                         name=None, horizontal_sep="1.6cm", vertical_sep="1.5cm"):
    """Arrange Axis objects without changing their data, sharing one named legend.

    Same series labels must have identical styles across panels. Unnamed
    reference lines and bands are excluded from the legend as in Axis.tex().
    Explicit axis ranges remain the caller's responsibility when comparisons
    require a common scale. Each axis should use a width suitable for the grid.
    """
    axes, titles = list(axes), list(titles)
    if not axes or len(axes) != len(titles) or any(not isinstance(ax, Axis) for ax in axes):
        raise ValueError("Panels need Axis objects and one title per panel")
    if type(columns) is not int or columns < 1 or columns > len(axes):
        raise ValueError("Panel columns must be between one and the panel count")
    if name is None:
        # Named legends live at document scope. A fixed default would make a
        # later figure silently replace the earlier figure's legend.
        identity = repr((titles, [ax.tex() for ax in axes])).encode('utf-8')
        name = 'PraxisPanels' + hashlib.sha256(identity).hexdigest()[:16]
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9]*', name):
        raise ValueError("Panel name must be an ASCII identifier")
    profiles = {ax.font_profile for ax in axes}
    if len(profiles) != 1:
        raise ValueError("Panels must use the same font profile")
    entries = {}
    for ax in axes:
        for label, options in ax._legend_entries:
            if label in entries and entries[label] != options:
                raise ValueError("Conflicting shared legend style for " + label)
            entries[label] = options
    if not entries:
        raise ValueError("Shared legend needs at least one labelled series")
    legend_name = name + 'Legend'
    out = [r"\begin{groupplot}[group style={group name=%s,group size=%d by %d,horizontal sep=%s,vertical sep=%s}]" %
           (name, columns, math.ceil(len(axes)/columns), horizontal_sep, vertical_sep)]
    for index, (ax, title) in enumerate(zip(axes, titles)):
        opts = [option for option in ax.opts if not option.startswith('legend style=')]
        opts += ["title={%s}" % tex_text(str(title))]
        if index == 0:
            opts += [f"legend to name={legend_name}", "legend columns=-1",
                     r"legend style={draw=none,font=\footnotesize,/tikz/every even column/.append style={column sep=8pt}}"]
        out.append(_font_profile(r"\nextgroupplot[%s]" % ','.join(opts), ax.font_profile))
        for item in ax.body:
            for label, _ in ax._legend_entries:
                item = item.replace(r"\addlegendentry{%s}" % tex_text(label), '')
            item = item.replace(r'\addplot[', r'\addplot[forget plot,')
            out.append(_font_profile(item, ax.font_profile))
        if index == 0:
            for label, options in entries.items():
                out.append(r"\addlegendimage{%s}\addlegendentry{%s}" % (','.join(options), tex_text(label)))
    out.append(r"\end{groupplot}")
    out.append(r"\node[anchor=north,yshift=-1.1cm] at (current bounding box.south) {\pgfplotslegendfromname{%s}};" % legend_name)
    return '\n'.join(out)


def diverging_heatmap(values, x, y, xlabel, ylabel, *, center=0, limit=None, cbar_label="",
                      width=r"0.65\linewidth", height="5cm", font_profile=None):
    """Rows follow y, columns follow x; x/y are equally spaced cell centres.

    The color scale is symmetric about the stated reference ``center``.
    ``limit`` is a positive half-range and may not silently clip values.
    """
    matrix, xs, ys = [list(row) for row in values], list(x), list(y)
    if len(xs) < 2 or len(ys) < 2 or len(matrix) != len(ys) or any(len(row) != len(xs) for row in matrix):
        raise ValueError("Heatmap needs at least a 2 by 2 rectangular grid matching x and y")
    if not all(math.isfinite(float(v)) for v in [*xs, *ys, center, *(v for row in matrix for v in row)]):
        raise ValueError("non-finite value in diverging heatmap")
    for coordinates in (xs, ys):
        step = coordinates[1]-coordinates[0]
        if step <= 0 or any(not math.isclose(b-a, step, rel_tol=1e-9, abs_tol=1e-12)
                            for a, b in zip(coordinates, coordinates[1:])):
            raise ValueError("Heatmap cell centres must strictly increase with equal spacing")
    radius = max(abs(value-center) for row in matrix for value in row)
    if limit is None:
        limit = radius or 1
    if not math.isfinite(float(limit)) or limit <= 0 or limit < radius:
        raise ValueError("Heatmap limit must be positive, finite and contain every value")
    rows = ['\n'.join('%s %s %s' % (_fmt(a), _fmt(b), _fmt(value))
                      for a, value in zip(xs, row)) for b, row in zip(ys, matrix)]
    ax = Axis(xlabel, ylabel, width=width, height=height, legend=None, font_profile=font_profile,
              extra=("axis on top,enlargelimits=false,grid=none,xtick={%s},ytick={%s}," %
                     (','.join(_fmt(v) for v in xs), ','.join(_fmt(v) for v in ys)) +
                     r"colormap={praxisdiverging}{rgb255(0cm)=(0,114,178);rgb255(1cm)=(247,247,247);rgb255(2cm)=(213,94,0)},"
                     "point meta min=%s,point meta max=%s,colorbar,colorbar style={ylabel={%s}}" %
                     (_fmt(center-limit), _fmt(center+limit), tex_text(cbar_label))))
    ax.body.append(r"\addplot[matrix plot*,mesh/cols=%d,point meta=explicit,shader=flat corner,forget plot] table[meta=c] {x y c" % len(xs)
                   + '\n' + '\n\n'.join(rows) + '\n};')
    return ax.tex()


def hbar_chart(labels: Sequence[str], values: Sequence[float], colors: Sequence[str], xlabel: str, *, width=r"0.66\linewidth",
               height="5.4cm", xmax: float | None = None, xmin: float | None = None, unit: str = "L", decimals: int = 2,
               font_profile: str | None = None) -> str:
    """Horizontal bar chart with value labels; labels are listed top to bottom. Negative values are drawn to the left of zero (tornado style)."""
    labels, values, colors = list(labels), list(values), list(colors)
    n = len(labels)
    if not n or len(values) != n or len(colors) != n:
        raise ValueError("hbar labels, values and colors must have the same nonzero length")
    if not all(math.isfinite(float(v)) for v in values):
        raise ValueError("non-finite value in hbar data")
    if any(not isinstance(c, str) or not c.strip() for c in colors):
        raise ValueError("hbar colors must be nonempty strings")
    for bound in (xmin, xmax):
        if bound is not None and not math.isfinite(float(bound)):
            raise ValueError("hbar bounds must be finite")
    top = xmax if xmax is not None else max(max(values), 0) * 1.3
    bottom = xmin if xmin is not None else min(min(values), 0) * 1.3
    if top < bottom:
        raise ValueError("hbar xmax must not be below xmin")
    span = top - bottom
    step = 5 if span > 12 else 1 if span > 4 else (0.5 if span > 1.5 else 0.1)
    first = math.ceil(bottom / step) * step
    ticks = ",".join(_fmt(first + i * step) for i in range(int((top - first) / step) + 1))
    opts = [f"width={width}", f"height={height}", "scale only axis", "xbar", "bar width=11pt", f"xmin={_fmt(bottom)}", f"xmax={_fmt(top)}", "y dir=reverse",
            "ytick={%s}" % ",".join(str(i) for i in range(n)), "yticklabels={%s}" % ",".join("{%s}" % tex_text(l) for l in labels),
            "xtick={%s}" % ticks, f"xlabel={{{xlabel}}}", "xmajorgrids=true", "ymajorgrids=false", "grid style={gray!22}",
            "tick label style={font=\\footnotesize}", "label style={font=\\small}", "enlarge y limits=0.12", "ytick style={draw=none}"]
    if bottom < 0:
        opts.append("axis y line*=left")
        opts.append("y axis line style={draw=none}")
    body = []
    for i, (v, c) in enumerate(zip(values, colors)):
        side = "west" if v >= 0 else "east"
        body.append(r"\addplot[xbar,bar shift=0pt,fill=%s,draw=none,nodes near coords,every node near coord/.append style={font=\footnotesize,anchor=%s},"
                    r"point meta=explicit symbolic] coordinates {(%s,%d) [%.*f\,%s]};" % (c, side, _fmt(v), i, decimals, v, unit))
    if bottom < 0:
        body.append(r"\draw[gray!70] ({axis cs:0,0}|-{rel axis cs:0,0}) -- ({axis cs:0,0}|-{rel axis cs:0,1});")
    return _font_profile("\\begin{axis}[%s]\n%s\n\\end{axis}" % (",\n ".join(opts), "\n".join(body)), font_profile)


def heatmap_panels(cubes: Sequence[Sequence[Sequence[float]]], titles: Sequence[str], xlabel: str, ylabel: str,
                   extent: tuple[float, float], vmin: float, vmax: float, *, cbar_label: str = "",
                   xticks: Sequence[float] = (), yticks: Sequence[float] = (),
                   font_profile: str | None = None) -> str:
    """Several matrix plots in one row sharing a colour scale. Each cube[i][j] is the value at x-index i, y-index j."""
    cubes = [[list(row) for row in cube] for cube in cubes]
    titles = list(titles)
    if not cubes or len(titles) != len(cubes) or not cubes[0] or not cubes[0][0]:
        raise ValueError("heatmap needs nonempty panels and one title per panel")
    nx, ny = len(cubes[0]), len(cubes[0][0])
    if any(len(cube) != nx or any(len(row) != ny for row in cube) for cube in cubes):
        raise ValueError("heatmap panels must be rectangular and share the same shape")
    if not all(math.isfinite(float(v)) for cube in cubes for row in cube for v in row):
        raise ValueError("non-finite value in heatmap data")
    if len(extent) != 2 or any(not math.isfinite(float(v)) or v <= 0 for v in extent):
        raise ValueError("heatmap extent must contain two finite positive lengths")
    if not math.isfinite(float(vmin)) or not math.isfinite(float(vmax)) or vmin > vmax:
        raise ValueError("heatmap color limits must be finite and ordered")
    if any(not math.isfinite(float(v)) for v in [*xticks, *yticks]):
        raise ValueError("heatmap ticks must be finite")
    xs = [(i + 0.5) * extent[0] / nx for i in range(nx)]
    ys = [(j + 0.5) * extent[1] / ny for j in range(ny)]
    out = [r"\begin{groupplot}[group style={group name=G,group size=%d by 1,horizontal sep=0.9cm,y descriptions at=edge left},"
           r"width=4.1cm,height=2.6cm,scale only axis,enlargelimits=false,axis on top,xmin=0,xmax=%s,ymin=0,ymax=%s,"
           r"colormap/viridis,point meta min=%s,point meta max=%s,tick label style={font=\scriptsize},label style={font=\footnotesize},"
           r"title style={font=\footnotesize},xtick={%s},ytick={%s},xticklabel style={/pgf/number format/fixed}]" % (
               len(cubes), _fmt(extent[0]), _fmt(extent[1]), _fmt(vmin), _fmt(vmax),
               ",".join(_fmt(v) for v in xticks), ",".join(_fmt(v) for v in yticks))]
    for k, cube in enumerate(cubes):
        out.append(r"\nextgroupplot[title={%s},xlabel={%s}%s]" % (titles[k], xlabel, (",ylabel={%s}" % ylabel) if k == 0 else ""))
        rows = []
        for j in range(ny):
            rows.append("\n".join("%s %s %s" % (_fmt(xs[i]), _fmt(ys[j]), _fmt(cube[i][j])) for i in range(nx)))
        out.append(r"\addplot[matrix plot*,mesh/cols=%d,point meta=explicit,shader=flat corner] table[meta expr=\thisrow{c}] {x y c" % nx + "\n" + "\n\n".join(rows) + "\n};")
    out.append(r"\end{groupplot}")
    mid = (len(cubes) + 1) // 2
    out.append(r"\begin{axis}[hide axis,scale only axis,width=0pt,height=0pt,at={(G c%dr1.south)},anchor=north,yshift=-1.0cm,"
               r"colormap/viridis,point meta min=%s,point meta max=%s,colorbar horizontal,"
               r"colorbar style={width=6.2cm,height=0.18cm,xlabel={%s},xlabel style={font=\footnotesize},tick label style={font=\scriptsize},"
               r"xticklabel style={/pgf/number format/fixed,/pgf/number format/precision=1}}]" % (mid, _fmt(vmin), _fmt(vmax), cbar_label))
    out.append(r"\addplot[draw=none] coordinates {(0,0)};")
    out.append(r"\end{axis}")
    return _font_profile("\n".join(out), font_profile)


def flow_diagram(boxes: Sequence[str], *, node_width: str = "2.22cm", font_profile: str | None = None) -> str:
    """Left-to-right roadmap of boxes joined by arrows (TikZ)."""
    nodes = []
    for i, text in enumerate(boxes):
        pos = "" if i == 0 else "right=0.45cm of n%d" % (i - 1)
        nodes.append(r"\node[draw=teal,line width=0.7pt,rounded corners=2pt,align=center,text width=%s,minimum height=1.35cm,font=\footnotesize,%s] (n%d) {%s};" % (
            node_width, pos, i, text.replace("\n", r"\\ ")))
    arrows = [r"\draw[-{Stealth[length=2.2mm]},clay,line width=0.8pt] (n%d) -- (n%d);" % (i, i + 1) for i in range(len(boxes) - 1)]
    return _font_profile("\n".join(nodes + arrows), font_profile)
