"""Regenerate the homepage and case-page overview images of both demos from the archived numbers.

    uv run --locked python demos/assets_src/make_overviews.py

Numbers come from archived records. Verify their scope against the current papers before publication.
Canvas 1920x1080; prose is composed per language, glyph roles and fixed regions are shared.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from showcase import FontSession, properties, validate_and_record

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
STYLE = json.loads((Path(__file__).parent / "visual-style.json").read_text())
COLOURS = STYLE["colors"]
BG, INK, GREY, RULE = (COLOURS[k] for k in ("background", "ink", "secondary", "rule"))
ACCENT, COMPARISON = COLOURS["accent"], COLOURS["comparison"]
W, H = STYLE["canvas"]


class Canvas:
    def __init__(self, lang: str):
        self.lang = lang
        self.fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor=BG)
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, W)
        self.ax.set_ylim(H, 0)
        self.ax.axis("off")

    def text(self, x, y, s, px, color=INK, kind="sans", ha="left", weight="normal", rotation=0):
        return self.ax.text(x, y, s, fontsize=px * 0.72, color=color, fontproperties=properties(kind), ha=ha, va="center", rotation=rotation)

    def frame(self, header_right, title, subtitle):
        self.text(125, 83, "P R A X I S", 18, ACCENT)
        self.text(1795, 83, header_right, 19, GREY, ha="right")
        for y in (135, 923):
            self.ax.plot([125, 1795], [y, y], color=RULE, lw=1.2)
        self.text(125, 212, title, 52 if self.lang == "zh" else 50, INK, "serif")
        self.text(125, 284, subtitle, 21, GREY)

    def plot_axes(self, left, right, top, bottom):
        a = self.fig.add_axes([left / W, 1 - bottom / H, (right - left) / W, (bottom - top) / H], facecolor="none")
        for s in ("top", "right"):
            a.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            a.spines[s].set_color(RULE)
        a.tick_params(colors=GREY, labelsize=15, length=4, width=0.8, color=RULE)
        for lab in a.get_xticklabels() + a.get_yticklabels():
            lab.set_fontproperties(properties())
            lab.set_fontsize(15)
        return a

    def style_ticks(self, a):
        for lab in a.get_xticklabels() + a.get_yticklabels():
            lab.set_fontproperties(properties())
            lab.set_fontsize(15)

    def save(self, path: Path):
        validate_and_record(self, path)
        self.fig.savefig(path, dpi=100, facecolor=BG)
        plt.close(self.fig)



# ---------------------------------------------------------------- MCM 2016 A
def mcm(lang: str, out: Path):
    ref = ROOT / "demos/mcm-2016-a/reproduce/reference"
    z = np.load(ref / "trajectory.npz")
    res = json.loads((ref / "results.json").read_text())
    ext = json.loads((ref / "extended.json").read_text())
    t = z["t"] / 60
    T = z["T"]
    mean = T @ z["volume"] / z["volume"].sum()
    nx, ny, nz = res["grid"]
    inlet = (ny // 2) * nz + nz - 1
    zone = np.linalg.norm(z["xyz"] - z["xyz"][inlet], axis=1) > res["parameters"]["inlet_exclusion"]
    hot = T[:, zone].max(1)  # hottest cell outside the inlet jet zone
    mesh = json.loads((ref / "mesh_check.json").read_text())
    best = mesh["accepted_schedule"]
    assert best and all(c["passed"] for c in mesh["checks"]), "No accepted schedule"
    vals = {"const": res["policy"]["water_l"], "sched": best["water_l"], "ideal": res["analytic"]["mixed_optimum_l"], "bound": res["analytic"]["energy_lower_bound_l"]}
    txt = {
        "zh": dict(title="水温要均匀，策略就不能只看平均值", sub="三维热网络 · 解析基线 · 独立积分与能量核验",
                   cap="最佳恒定流量下 · 群青：均值 · 虚线：最冷单元 · 阴影：入口射流区以外的温度范围", yl="水温 / °C", xl="时间 / min",
                   m=["最佳恒定流量", f"时变方案（{best['segments']} 段）", "理想充分混合", "能量下界"],
                   foot="40°C 起始 · 39–41°C 窗口 · 30 分钟 · 系数由教材关联式推导，非实测"),
        "en": dict(title="A warm average can hide a cold corner", sub="Spatial heat balance, a proved benchmark, and independent numerical checks",
                   cap="Best constant rate: mean (blue) · coldest cell (dashed) · range outside the inlet jet zone (shade)", yl="Temperature / °C", xl="Time / min",
                   m=["Best constant rate", f"Time-varying schedule ({best['segments']} segments)", "Ideal well-mixed optimum", "Conditional energy lower bound"],
                   foot="40°C start · 39–41°C window · 30 min · Textbook-correlation coefficients, not measured data"),
    }[lang]
    c = Canvas(lang)
    c.frame("CASE 02  /  MCM 2016 A", txt["title"], txt["sub"])
    c.text(183, 351, txt["cap"], 22, GREY)
    a = c.plot_axes(182, 1066, 390, 820)
    a.set_xlim(0, 30)
    a.set_ylim(38.81, 41.10)
    a.fill_between(t, T.min(1), hot, color=ACCENT, alpha=0.14, lw=0)
    a.plot(t, hot, color=ACCENT, alpha=0.22, lw=1.2)
    a.plot(t, mean, color=ACCENT, lw=2.4)
    a.plot(t, T.min(1), color=COMPARISON, lw=2.0, ls=(0, (4, 2.2)))
    a.axhline(39.0, color=GREY, lw=0.9, ls=":")
    a.set_xticks([0, 10, 20, 30])
    a.set_yticks([39.0, 39.5, 40.0, 40.5, 41.0])
    a.set_yticklabels(["39.0", "39.5", "40.0", "40.5", "41.0"])
    c.style_ticks(a)
    a.tick_params(labelsize=15)
    c.text(623, 874, txt["xl"], 25, GREY, ha="center")
    c.text(101, 604, txt["yl"], 25, GREY, ha="center", rotation=90)
    colours = [ACCENT, INK, GREY, GREY]  # accent = the quantity drawn in the chart; the rest are comparison points
    for i, (label, key, col) in enumerate(zip(txt["m"], ["const", "sched", "ideal", "bound"], colours)):
        y = 401 + 135 * i
        c.text(1229, y, label, 27 if lang == "en" else 28, GREY)
        c.text(1229, y + 56, f"{vals[key]:.2f} L", 58, col)
    c.text(125, 990, txt["foot"], 25, GREY)
    c.save(out)
    return res, ext  # keep the references alive for callers that want to assert on them


# ---------------------------------------------------------------- CUMCM 1998 A
def cumcm(lang: str, variant: str, out: Path):
    ref = ROOT / "demos/cumcm-1998-a/reproduce/reference"

    def frontier(name):
        rows = list(csv.DictReader((ref / f"{name}-frontier.csv").open()))
        return np.array([float(r["risk_cap"]) for r in rows]) * 100, np.array([float(r["net_return"]) for r in rows]) * 100

    sets = [("four", ACCENT, 1.0, 3.0, 2.55, 29.35, [5, 10, 15, 20, 25], [0, 1, 2, 3], 180, 610),
            ("fifteen", COMPARISON, 10.0, 60.0, 2.6, 43.5, [10, 20, 30, 40], [0, 20, 40, 60], 746, 1176)]
    L = {
        "zh": dict(title="风险的边界，收益的选择", sub="费用、风险与回报，需要放在同一个模型里看",
                   names=["四资产", "十五资产"], xl="风险上限", head="CASE 01  /  CUMCM 1998 A", rhead="CASE 01  /  RESULTS"),
        "en": dict(title="Portfolio choices under risk constraints", sub="Fees, risk and returns belong in the same decision model",
                   names=["4 assets", "15 assets"], xl="Risk limit", head="CASE 01  /  CUMCM 1998 A", rhead="CASE 01  /  RESULTS"),
    }[lang]
    c = Canvas(lang)
    c.text(125, 83, "P R A X I S", 18, ACCENT)
    c.text(1795, 83, L["head"] if variant == "overview" else L["rhead"], 19, GREY, ha="right")
    c.text(125, 232, L["title"], 68, kind="serif")
    c.text(125, 308, L["sub"], 26, GREY)
    c.ax.plot([1240, 1240], [403, 841], color=RULE, lw=.8)
    for index, ((name, col, cap, xmax, ymin, ymax, yt, xt, x0, x1), label) in enumerate(zip(sets, L["names"])):
        x, y = frontier(name)
        a = c.plot_axes(x0, x1, 463, 815)
        a.set_xlim(0, xmax)
        a.set_ylim(ymin, ymax)
        a.grid(axis="y", color=RULE, lw=0.7)
        a.set_axisbelow(True)
        a.fill_between(x, ymin, y, color=col, alpha=0.08, lw=0)
        a.plot(x, y, color=col, lw=2.0)
        a.axhline(5, color=GREY, lw=0.9, ls=(0, (4, 3)))
        i = int(np.argmin(abs(x - cap)))
        if abs(x[i] - cap) > 1e-8:
            raise ValueError('Selected risk limit is absent from the archived frontier')
        a.plot([x[i]], [y[i]], "o", ms=8, mfc=col, mec=BG, mew=2, zorder=5)
        a.set_yticks(yt)
        a.set_yticklabels([f"{v}%" for v in yt])
        a.set_xticks(xt)
        a.set_xticklabels([f"{v:g}%" for v in xt])
        c.style_ticks(a)
        c.text(x0, 410, label, 27)
        c.text((x0 + x1) / 2, 867, L["xl"] + " →", 22, GREY, ha="center")
        facts_y = 432 + index * 227
        fact_label = (f"{label} · 风险上限 {cap:g}%" if lang == "zh" else f"{label} · risk cap {cap:g}%")
        c.text(1300, facts_y, fact_label, 25)
        c.text(1300, facts_y + 79, f"{y[i]:.2f}%", 80, col)
        c.text(1300, facts_y + 143, "最优净收益率" if lang == "zh" else "Optimal net return", 22, GREY)
    c.ax.plot([125, 1795], [923, 923], color=RULE, lw=.8)
    c.text(125, 970, "资金 100 万元" if lang == "zh" else "Budget: CNY 1,000,000", 23)
    c.text(125, 1015, "两组风险上限不同；结果不代表实际投资预测" if lang == "zh" else "Different risk caps; conditional results, not investment forecasts", 21, GREY)
    if variant == "overview":
        lines = (["横轴：风险上限　纵轴：最优净收益率", "虚线：5% 银行收益率 · 原题数据与独立核验"] if lang == "zh" else
                 ["Axes: risk cap and optimal net return", "Dashed: 5% bank return · Independently checked"])
    else:
        lines = (["风险 = 最大单项风险损失额 ÷ 总资金", "虚线：5% 银行收益率 · 原题数据与独立核验"] if lang == "zh" else
                 ["Risk = maximum single-asset loss / budget", "Dashed: 5% bank return · Independently checked"])
    c.text(1795, 970, lines[0], 21, GREY, ha="right")
    c.text(1795, 1015, lines[1], 21, GREY, ha="right")
    c.save(out)


def main():
    A = ROOT / "demos"
    with FontSession():
        for lang in ("zh", "en"):
            mcm(lang, A / "mcm-2016-a/assets" / f"overview-{lang}.png")
            cumcm(lang, "overview", A / "cumcm-1998-a/assets" / f"overview-{lang}.png")
        cumcm("zh", "results", A / "cumcm-1998-a/assets/risk-return-zh.png")
        cumcm("en", "results", A / "cumcm-1998-a/assets/risk-return.png")
    print("ok")


if __name__ == "__main__":
    main()
