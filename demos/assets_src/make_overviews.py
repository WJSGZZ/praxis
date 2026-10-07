"""Regenerate the homepage and case-page overview images of both demos from the archived numbers.

    uv run --locked python demos/assets_src/make_overviews.py

Every number comes from the demos' reference records and verification files, so the images cannot drift from the papers.
Canvas 1920x1080; Chinese and English are laid out separately (different fonts and wording).
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BG, INK, GREY, RULE = "#F6F5F0", "#1F262B", "#5E686E", "#D8D8D2"
TEAL, CLAY = "#166B5D", "#A5683E"
FONT = {"zh": {"serif": "Songti SC", "sans": "PingFang SC"}, "en": {"serif": "DejaVu Serif", "sans": "DejaVu Sans"}}
W, H = 1920, 1080


class Canvas:
    def __init__(self, lang: str):
        self.lang, self.f = lang, FONT[lang]
        self.fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor=BG)
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, W)
        self.ax.set_ylim(H, 0)
        self.ax.axis("off")

    def text(self, x, y, s, px, color=INK, kind="sans", ha="left", weight="normal", rotation=0):
        self.ax.text(x, y, s, fontsize=px * 0.72, color=color, family=self.f[kind], ha=ha, va="center", fontweight=weight, rotation=rotation)

    def frame(self, header_right, title, subtitle):
        self.text(125, 83, "P R A X I S", 18, TEAL, weight="bold")
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
            lab.set_family(self.f["sans"])
        return a

    def style_ticks(self, a):
        for lab in a.get_xticklabels() + a.get_yticklabels():
            lab.set_family(self.f["sans"])

    def save(self, path: Path):
        self.fig.savefig(path, dpi=100, facecolor=BG)
        plt.close(self.fig)


def pages(demo: str) -> int:
    v = json.loads((ROOT / "demos" / demo / "verification.json").read_text())
    return int(v["report_pages"] if "report_pages" in v else v["pdf"]["pages_total"])


# ---------------------------------------------------------------- MCM 2016 A
def mcm(lang: str, out: Path):
    ref = ROOT / "demos/mcm-2016-a/reproduce/reference"
    z = np.load(ref / "trajectory.npz")
    res = json.loads((ref / "results.json").read_text())
    ext = json.loads((ref / "extended.json").read_text())
    t = z["t"] / 60
    T = z["T"]
    mean = T @ z["volume"] / z["volume"].sum()
    vals = {"const": 24.14, "sched": 19.77, "ideal": 16.01, "bound": 15.41}  # recorded in the paper's Table 7; cross-checked below
    txt = {
        "zh": dict(title="水温要均匀，策略就不能只看平均值", sub="三维热网络 · 解析基线 · 独立积分与能量核验",
                   cap="最佳恒定流量下 · 青绿：均值 · 虚线：最冷单元 · 阴影：温度范围", yl="水温 / °C", xl="时间 / min",
                   m=["最佳恒定流量", "时变方案（12 段）", "理想充分混合", "能量下界"],
                   foot="40°C 起始 · 39–41°C 窗口 · 30 分钟 · 系数取自文献推导，非实测",
                   link=f"{pages('mcm-2016-a')} 页完整报告（含 AI 披露） · 17 项检查 · 查看美赛 Demo →"),
        "en": dict(title="A warm average can hide a cold corner", sub="Spatial heat balance, a proved benchmark, and independent numerical checks",
                   cap="Best constant rate: mean (teal) · coldest cell (dashed) · spatial range (shade)", yl="Temperature / °C", xl="Time / min",
                   m=["Best constant rate", "Time-varying schedule (12 segments)", "Ideal well-mixed optimum", "Conditional energy lower bound"],
                   foot="40°C start · 39–41°C window · 30 min · Literature-derived coefficients, not measured data",
                   link=f"Read the {pages('mcm-2016-a')}-page report with AI disclosure · Inspect 17 recorded checks →"),
    }[lang]
    c = Canvas(lang)
    c.frame("CASE 02  /  MCM 2016 A", txt["title"], txt["sub"])
    c.text(183, 351, txt["cap"], 22, GREY)
    a = c.plot_axes(182, 1066, 390, 820)
    a.set_xlim(0, 30)
    a.set_ylim(38.81, 41.10)
    a.fill_between(t, T.min(1), T.max(1), color=TEAL, alpha=0.14, lw=0)
    a.plot(t, T.max(1), color=TEAL, alpha=0.22, lw=1.2)
    a.plot(t, mean, color=TEAL, lw=2.4)
    a.plot(t, T.min(1), color=CLAY, lw=2.0, ls=(0, (4, 2.2)))
    a.axhline(39.0, color=GREY, lw=0.9, ls=":")
    a.set_xticks([0, 10, 20, 30])
    a.set_yticks([39.0, 39.5, 40.0, 40.5, 41.0])
    a.set_yticklabels(["39.0", "39.5", "40.0", "40.5", "41.0"])
    c.style_ticks(a)
    a.tick_params(labelsize=15)
    c.text(623, 874, txt["xl"], 25, GREY, ha="center")
    c.text(101, 604, txt["yl"], 25, GREY, ha="center", rotation=90)
    colours = [TEAL, INK, GREY, GREY]  # teal = the quantity drawn in the chart; the rest are comparison points
    for i, (label, key, col) in enumerate(zip(txt["m"], ["const", "sched", "ideal", "bound"], colours)):
        y = 401 + 135 * i
        c.text(1229, y, label, 27 if lang == "en" else 28, GREY)
        c.text(1229, y + 56, f"{vals[key]:.2f} L", 58, col)
    c.text(125, 962, txt["foot"], 25, GREY)
    c.text(125, 1012, txt["link"], 29, TEAL)
    c.save(out)
    return res, ext  # keep the references alive for callers that want to assert on them


# ---------------------------------------------------------------- CUMCM 1998 A
def cumcm(lang: str, variant: str, out: Path):
    ref = ROOT / "demos/cumcm-1998-a/reproduce/reference"

    def frontier(name):
        rows = list(csv.DictReader((ref / f"{name}-frontier.csv").open()))
        return np.array([float(r["risk_cap"]) for r in rows]) * 100, np.array([float(r["net_return"]) for r in rows]) * 100

    sets = [("four", TEAL, 1.0, 3.0, 2.55, 29.35, [5, 10, 15, 20, 25], [0, .5, 1, 1.5, 2, 2.5, 3], 163, 855),
            ("fifteen", CLAY, 10.0, 60.0, 2.6, 43.5, [5, 10, 15, 20, 25, 30, 35, 40], [0, 10, 20, 30, 40, 50, 60], 1056, 1747)]
    n = pages("cumcm-1998-a")
    L = {
        "zh": dict(title="风险的边界，收益的选择", sub="两组资产的最优方案与风险收益曲线，计算结果经过独立核验", names=["四资产", "十五资产"], risk="风险上限 {:g}%",
                   xl="风险上限", yl="最优净收益率", head="CASE 01  /  CUMCM 1998 A",
                   foot1="资金 100 万元 · 虚线为 5% 银行收益率 · 两组风险上限不同，非实际投资预测", link=f"{n} 页完整报告 · 12 项检查 · 查看国赛 Demo →",
                   rhead="CASE 01  /  RESULTS", rfoot1="资金 100 万元 · 虚线为 5% 银行收益率 · 两组采用不同风险上限",
                   rfoot2="风险口径：最大单项风险损失额 ÷ 总资金。模型结果不代表实际投资收益预测。"),
        "en": dict(title="Portfolio returns under risk constraints", sub="Two asset sets, with selected solutions verified against analytical upper bounds", names=["4 assets", "15 assets"], risk="Risk limit: {:g}%",
                   xl="Risk limit", yl="Optimal net return", head="CASE 01  /  CUMCM 1998 A",
                   foot1="Budget: CNY 1,000,000 · Dashed line: 5% bank return · Different risk limits, not an investment forecast", link=f"Read the {n}-page report · Inspect 12 recorded checks →",
                   rhead="CASE 01  /  RESULTS", rfoot1="Budget: CNY 1,000,000 · Dashed line: 5% bank return · Different risk limits across groups",
                   rfoot2="Risk = maximum single-asset loss / budget. Conditional model results, not investment forecasts."),
    }[lang]
    c = Canvas(lang)
    c.frame(L["head"] if variant == "overview" else L["rhead"], L["title"], L["sub"])
    for (name, col, cap, xmax, ymin, ymax, yt, xt, x0, x1), label in zip(sets, L["names"]):
        x, y = frontier(name)
        a = c.plot_axes(x0, x1, 421, 815)
        a.set_xlim(0, xmax)
        a.set_ylim(ymin, ymax)
        a.grid(axis="y", color=RULE, lw=0.9)
        a.set_axisbelow(True)
        a.fill_between(x, ymin, y, color=col, alpha=0.08, lw=0)
        a.plot(x, y, color=col, lw=2.6)
        a.axhline(5, color=GREY, lw=0.9, ls=(0, (4, 3)))
        i = int(np.argmin(abs(x - cap)))
        a.plot([x[i]], [y[i]], "o", ms=9, mfc=col, mec=BG, mew=2, zorder=5)
        a.set_yticks(yt)
        a.set_yticklabels([f"{v}%" for v in yt])
        a.set_xticks(xt)
        a.set_xticklabels([f"{v:g}%" if xmax <= 3 else f"{int(v)}%" for v in xt])
        a.set_xticklabels([(f"{v:.1f}%" if xmax <= 3 else f"{int(v)}%") for v in xt])
        c.style_ticks(a)
        a.tick_params(labelsize=15)
        c.text(x0, 368, label, 36 if lang == "zh" else 33, INK, "serif")
        c.text(x1, 357, f"{y[i]:.2f}%", 48, col, ha="right")
        c.text(x1, 397, L["risk"].format(cap), 19, GREY, ha="right")
        c.text((x0 + x1) / 2, 873, L["xl"], 22, GREY, ha="center")
        c.text(x0 - 80, 618, L["yl"], 22, GREY, ha="center", rotation=90)
    if variant == "overview":
        c.text(125, 962, L["foot1"], 25, GREY)
        c.text(125, 1013, L["link"], 29, TEAL)
    else:
        c.text(125, 958, L["rfoot1"], 19, INK)
        c.text(125, 1007, L["rfoot2"], 19, GREY)
    c.save(out)


def main():
    A = ROOT / "demos"
    for lang in ("zh", "en"):
        mcm(lang, A / "mcm-2016-a/assets" / f"overview-{lang}.png")
        cumcm(lang, "overview", A / "cumcm-1998-a/assets" / f"overview-{lang}.png")
    cumcm("zh", "results", A / "cumcm-1998-a/assets/risk-return-zh.png")
    cumcm("en", "results", A / "cumcm-1998-a/assets/risk-return.png")
    print("ok")


if __name__ == "__main__":
    main()
