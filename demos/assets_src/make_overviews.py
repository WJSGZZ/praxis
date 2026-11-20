"""Regenerate the homepage and case-page overview images of both demos from the archived numbers.

    uv run --locked python demos/assets_src/make_overviews.py

Numbers come from archived records. Verify their scope against the current papers before publication.
Canvas 1920x1080; prose is composed per language, glyph roles and fixed regions are shared.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from showcase import (ACCENT, BG, COMPARISON, GREY, INK, LAYOUT, ROLES, STROKES, Canvas,
                      FontSession, L, R)

ROOT = Path(__file__).resolve().parents[2]
CHART = LAYOUT['chart']


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
        "zh": dict(title="平均水温之下，藏着冷角落", sub="三维热网络 · 解析基线 · 独立积分与能量核验",
                   key=[("均值", ACCENT, "line"), ("最冷单元", COMPARISON, "dashed"), ("入口射流区以外的范围", ACCENT, "band")],
                   yl="水温 °C", xl="时间（分钟）· 最佳恒定流量",
                   claim="分 {n} 段调节补水，比最佳恒定流量少用约 {saved:.1f} L",
                   m=["最佳恒定流量", f"时变方案（{best['segments']} 段）", "理想充分混合", "能量下界"],
                   foot="40°C 起始 · 39–41°C 窗口 · 30 分钟 · 系数由教材关联式推导，非实测"),
        "en": dict(title="The cold corner of a warm bath", sub="Spatial heat balance, a proved benchmark, and independent numerical checks",
                   key=[("Mean", ACCENT, "line"), ("Coldest cell", COMPARISON, "dashed"), ("Range beyond the inlet jet", ACCENT, "band")],
                   yl="Water °C", xl="Time (min) · best constant rate",
                   claim="A {n}-segment schedule saves about {saved:.1f} L over the best constant rate",
                   m=["Best constant rate", f"Time-varying schedule ({best['segments']} segments)", "Ideal well-mixed optimum", "Conditional energy lower bound"],
                   foot="40°C start · 39–41°C window · 30 min · Textbook-correlation coefficients, not measured data"),
    }[lang]
    c = Canvas(lang)
    c.frame("CASE 02  ·  MCM 2016 A", txt["title"], txt["sub"])
    c.text(L, LAYOUT["caption_y"], txt["yl"], "caption")
    c.key(R, LAYOUT["caption_y"], txt["key"], ha="right")
    a = c.axes(*CHART)
    a.set_xlim(0, 30)
    a.set_ylim(38.81, 41.10)
    a.fill_between(t, T.min(1), hot, color=ACCENT, alpha=0.12, lw=0)
    a.plot(t, hot, color=ACCENT, alpha=0.25, lw=STROKES["guide"])
    a.plot(t, mean, color=ACCENT, lw=STROKES["primary"])
    a.plot(t, T.min(1), color=COMPARISON, lw=STROKES["secondary"], ls=(0, (4, 2.4)))
    a.set_xticks([0, 10, 20, 30])
    a.set_yticks([39.0, 39.5, 40.0, 40.5, 41.0])
    a.set_yticklabels(["39.0", "39.5", "40.0", "40.5", "41.0"])
    c.ticks(a)
    c.text((CHART[0] + CHART[1]) / 2, LAYOUT["axis_label_y"], txt["xl"], "key", ha="center")
    colours = ["lead", "lead", "context", "context"]  # the two water uses lead; the benchmarks are context
    c.facts([(label, f"{vals[key]:.2f} L", None, col)
             for label, key, col in zip(txt["m"], ["const", "sched", "ideal", "bound"], colours)])
    saved = vals["const"] - vals["sched"]
    c.footer(txt["claim"].format(saved=saved, n=best["segments"]), txt["foot"])
    c.save(out)
    return res, ext  # keep the references alive for callers that want to assert on them


# ---------------------------------------------------------------- CUMCM 1998 A
def cumcm(lang: str, variant: str, out: Path):
    ref = ROOT / "demos/cumcm-1998-a/reproduce/reference"

    def frontier(name):
        rows = list(csv.DictReader((ref / f"{name}-frontier.csv").open()))
        return np.array([float(r["risk_cap"]) for r in rows]) * 100, np.array([float(r["net_return"]) for r in rows]) * 100

    left, right = CHART[0], CHART[1]
    middle = (left + right) / 2
    sets = [("four", ACCENT, 1.0, 3.0, 2.55, 29.35, [5, 10, 15, 20, 25], [0, 1, 2, 3], left, middle - 70),
            ("fifteen", COMPARISON, 10.0, 60.0, 2.6, 43.5, [10, 20, 30, 40], [0, 20, 40, 60], middle + 70, right)]
    T = {
        "zh": dict(title="风险的边界，收益的选择", sub="费用、风险与回报，需要放在同一个模型里看",
                   names=["四资产", "十五资产"], xl="风险上限", value="最优净收益率",
                   claim="资金 100 万元，两组资产各自取不同的风险上限", cond="条件结果，不代表实际投资预测"),
        "en": dict(title="Bounded risk, chosen return", sub="Fees, risk and returns belong in the same decision model",
                   names=["4 assets", "15 assets"], xl="Risk limit", value="Optimal net return",
                   claim="A budget of CNY 1,000,000; each asset set has its own risk cap", cond="Conditional results, not investment forecasts"),
    }[lang]
    c = Canvas(lang)
    c.frame("CASE 01  ·  CUMCM 1998 A" if variant == "overview" else "CASE 01  ·  RESULTS", T["title"], T["sub"])
    facts = []
    for (name, col, cap, xmax, ymin, ymax, yt, xt, x0, x1), label in zip(sets, T["names"]):
        x, y = frontier(name)
        a = c.axes(x0, x1, CHART[2], CHART[3])
        a.set_xlim(0, xmax)
        a.set_ylim(ymin, ymax)
        a.fill_between(x, ymin, y, color=col, alpha=0.08, lw=0)
        a.plot(x, y, color=col, lw=STROKES["primary"])
        a.axhline(5, color=GREY, lw=STROKES["guide"], ls=(0, (4, 3)))
        i = int(np.argmin(abs(x - cap)))
        if abs(x[i] - cap) > 1e-8:
            raise ValueError('Selected risk limit is absent from the archived frontier')
        a.plot([x[i]], [y[i]], "o", ms=STROKES["marker"] + 3, mfc=col, mec=BG, mew=2.5, zorder=5)
        a.set_yticks(yt)
        a.set_yticklabels([f"{v}%" for v in yt])
        a.set_xticks(xt)
        a.set_xticklabels([f"{v:g}%" for v in xt])
        c.ticks(a)
        c.text(x0 - 76, LAYOUT["caption_y"], label, "caption")
        c.text((x0 + x1) / 2, LAYOUT["axis_label_y"], T["xl"] + " →", "key", ha="center")
        facts.append((f"{label} · 风险上限 {cap:g}%" if lang == "zh" else f"{label} · risk cap {cap:g}%",
                      f"{y[i]:.2f}%", T["value"], "lead" if col == ACCENT else "comparison"))
    if variant == "overview":
        lines = (["横轴：风险上限　纵轴：最优净收益率", "虚线：5% 银行收益率 · 原题数据与独立核验"] if lang == "zh" else
                 ["Axes: risk cap and optimal net return", "Dashed: 5% bank return · Independently checked"])
    else:
        lines = (["风险 = 最大单项风险损失额 ÷ 总资金", "虚线：5% 银行收益率 · 原题数据与独立核验"] if lang == "zh" else
                 ["Risk = maximum single-asset loss / budget", "Dashed: 5% bank return · Independently checked"])
    c.facts(facts, lines)
    c.footer(T["claim"], T["cond"])
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
