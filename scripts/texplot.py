"""Generate publication figures as pgfplots/TikZ source, so the plot text uses the paper's own fonts.

Data are written as inline coordinates, so a figure is reproducible from the .tex file alone.
Preamble needs: pgfplots (compat 1.17+) with the fillbetween, groupplots and positioning TikZ libraries, and the
colors defined by PREAMBLE_COLORS (Okabe–Ito-style, safe for colour-blind readers and for grayscale printing when
combined with the dash styles used here).
"""
from __future__ import annotations

import math
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


def _fmt(v: float) -> str:
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        raise ValueError("non-finite value in plotted data")
    return "%.6g" % v


def _coords(x: Iterable[float], y: Iterable[float], limit: int = 700) -> str:
    xs, ys = list(x), list(y)
    if len(xs) != len(ys):
        raise ValueError("x and y differ in length")
    step = max(1, math.ceil(len(xs) / limit))
    idx = list(range(0, len(xs), step))
    if idx[-1] != len(xs) - 1:
        idx.append(len(xs) - 1)
    return " ".join("(%s,%s)" % (_fmt(xs[i]), _fmt(ys[i])) for i in idx)


class Axis:
    """One pgfplots axis with line, band, step, scatter and reference-line series."""

    def __init__(self, xlabel: str = "", ylabel: str = "", *, width: str = r"0.84\linewidth", height: str = "5.4cm",
                 xmin=None, xmax=None, ymin=None, ymax=None, legend: str | None = "above", legend_columns: int | None = None,
                 extra: str = ""):
        self.opts = [f"width={width}", f"height={height}", "scale only axis", f"xlabel={{{xlabel}}}", f"ylabel={{{ylabel}}}",
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

    def line(self, x, y, color="main", style="solid", width=1.1, label=None, marks=None):
        opt = [f"color={color}", f"line width={width}pt"]
        if DASH[style]:
            opt.append(DASH[style])
        if marks:
            opt += [f"mark={marks}", "mark size=1.8pt"]
        else:
            opt.append("no marks")
        self.body.append(r"\addplot[%s] coordinates {%s};" % (",".join(opt), _coords(x, y))
                         + (r"\addlegendentry{%s}" % label if label else ""))
        return self

    def band(self, x, lo, hi, color="main", opacity=0.14, label=None):
        self._band += 1
        a, b = f"lo{self._band}", f"hi{self._band}"
        self.body.append(r"\addplot[name path=%s,draw=none,forget plot] coordinates {%s};" % (a, _coords(x, lo)))
        self.body.append(r"\addplot[name path=%s,draw=none,forget plot] coordinates {%s};" % (b, _coords(x, hi)))
        self.body.append(r"\addplot[%s,fill opacity=%s] fill between[of=%s and %s];" % (f"fill={color}", opacity, a, b)
                         + (r"\addlegendentry{%s}" % label if label else ""))
        return self

    def stairs(self, values: Sequence[float], edges: Sequence[float], color="main", width=1.3, label=None, style="solid"):
        """Piecewise-constant series: values[i] holds on [edges[i], edges[i+1]]."""
        if len(edges) != len(values) + 1:
            raise ValueError("edges must have one more entry than values")
        pts = []
        for i, v in enumerate(values):
            pts += [(edges[i], v), (edges[i + 1], v)]
        opt = [f"color={color}", f"line width={width}pt", "no marks"] + ([DASH[style]] if DASH[style] else [])
        self.body.append(r"\addplot[%s] coordinates {%s};" % (",".join(opt), " ".join("(%s,%s)" % (_fmt(a), _fmt(b)) for a, b in pts))
                         + (r"\addlegendentry{%s}" % label if label else ""))
        return self

    def scatter(self, x, y, color="main", mark="*", size=2.0, label=None):
        self.body.append(r"\addplot[only marks,mark=%s,mark size=%spt,color=%s] coordinates {%s};" % (mark, size, color, _coords(x, y, limit=5000))
                         + (r"\addlegendentry{%s}" % label if label else ""))
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
        self.body.append(r"\node[anchor=%s,font=\footnotesize] at (axis cs:%s,%s) {%s};" % (anchor, _fmt(x), _fmt(y), text))
        return self

    def label(self, x, y, text, color="black", anchor="west", dx="3pt", dy="0pt"):
        """Direct label next to a curve (preferred to a legend when there are few series)."""
        self.body.append(r"\node[anchor=%s,font=\footnotesize,text=%s,xshift=%s,yshift=%s] at (axis cs:%s,%s) {%s};" % (anchor, color, dx, dy, _fmt(x), _fmt(y), text))
        return self

    def tex(self) -> str:
        return "\\begin{axis}[%s]\n%s\n\\end{axis}" % (",\n ".join(self.opts), "\n".join(self.body))


def figure_env(axes_tex: str, caption: str, *, placement: str = "htbp", label: str | None = None) -> str:
    """Wrap pgfplots axes in a figure with a caption below (and an optional label for cross-references)."""
    lab = "\\label{%s}" % label if label else ""
    return "\\begin{figure}[%s]\\centering\n\\begin{tikzpicture}\n%s\n\\end{tikzpicture}\n\\caption{%s}%s\n\\end{figure}\n" % (placement, axes_tex, caption, lab)


def hbar_chart(labels: Sequence[str], values: Sequence[float], colors: Sequence[str], xlabel: str, *, width=r"0.66\linewidth",
               height="5.4cm", xmax: float | None = None, unit: str = "L") -> str:
    """Horizontal bar chart with value labels; labels are listed top to bottom."""
    n = len(labels)
    xm = xmax if xmax is not None else max(values) * 1.3
    step = 5 if xm > 12 else 1
    ticks = ",".join(str(v) for v in range(0, int(xm) + 1, step))
    opts = [f"width={width}", f"height={height}", "scale only axis", "xbar", "bar width=11pt", "xmin=0", f"xmax={_fmt(xm)}", "y dir=reverse",
            "ytick={%s}" % ",".join(str(i) for i in range(n)), "yticklabels={%s}" % ",".join("{%s}" % l for l in labels),
            "xtick={%s}" % ticks, f"xlabel={{{xlabel}}}", "xmajorgrids=true", "ymajorgrids=false", "grid style={gray!22}",
            "tick label style={font=\\footnotesize}", "label style={font=\\small}", "enlarge y limits=0.12", "ytick style={draw=none}"]
    body = []
    for i, (v, c) in enumerate(zip(values, colors)):
        body.append(r"\addplot[xbar,bar shift=0pt,fill=%s,draw=none,nodes near coords,every node near coord/.append style={font=\footnotesize,anchor=west},"
                    r"point meta=explicit symbolic] coordinates {(%s,%d) [%.2f\,%s]};" % (c, _fmt(v), i, v, unit))
    return "\\begin{axis}[%s]\n%s\n\\end{axis}" % (",\n ".join(opts), "\n".join(body))


def heatmap_panels(cubes: Sequence[Sequence[Sequence[float]]], titles: Sequence[str], xlabel: str, ylabel: str,
                   extent: tuple[float, float], vmin: float, vmax: float, *, cbar_label: str = "",
                   xticks: Sequence[float] = (), yticks: Sequence[float] = ()) -> str:
    """Several matrix plots in one row sharing a colour scale. Each cube[i][j] is the value at x-index i, y-index j."""
    nx, ny = len(cubes[0]), len(cubes[0][0])
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
    return "\n".join(out)


def flow_diagram(boxes: Sequence[str], *, node_width: str = "2.35cm") -> str:
    """Left-to-right roadmap of boxes joined by arrows (TikZ)."""
    nodes = []
    for i, text in enumerate(boxes):
        pos = "" if i == 0 else "right=0.45cm of n%d" % (i - 1)
        nodes.append(r"\node[draw=teal,line width=0.7pt,rounded corners=2pt,align=center,text width=%s,minimum height=1.35cm,font=\footnotesize,%s] (n%d) {%s};" % (
            node_width, pos, i, text.replace("\n", r"\\ ")))
    arrows = [r"\draw[-{Stealth[length=2.2mm]},clay,line width=0.8pt] (n%d) -- (n%d);" % (i, i + 1) for i in range(len(boxes) - 1)]
    return "\n".join(nodes + arrows)
