---
name: praxis-visualization
description: 设计、生成和审查科研数据图：读者问题、变量与单位、聚合和不确定性、实际系列数组与图例对象对应、坐标与色标、最终尺寸字体和导出。用于“这张科研图表达对吗、画结果图、图例错位、区间带怎么表示、检查图形数据和坐标”。Scientific visualization, data-to-legend correspondence, research figures, uncertainty plots and export review. 宣传图或界面设计另走其专业流程；不合成或提高科学证据。
license: MIT
---

# Praxis · 科研图形与数据表达

BUNDLE=`praxis` 技能目录；脚本 `BUNDLE/scripts/`；Python 3.12、uv（`uv run --locked`）；无终端仅设计。执行见 [automation.md](../../references/automation.md)。

## 做什么

- 按 [visualization.md](../../references/visualization.md) 先比较文字、表与图；每张图明确读者问题、量、对象、分母、单位和条件。
- 从有效数组生成，留筛选、聚合、变换、缺失、网格及区间定义，分清观测、拟合、插值与预测。
- 核 `series-id → 来源数组／单位／变换 → 实际 artist → label／颜色／符号`，图例显式 handles／labels，辅助线／带不占科学系列位置。
- 用已有 texplot／Matplotlib 等与共享字体，核最终嵌入字号和尺寸；图题／说明及正文引用按 [writing.md](../../references/writing.md)。
- 小例核端点、极值、阈值和面板，针对标签错位、缺失连线或变换加反例；实际看渲染中的图例、单位、截断、遮挡及灰度。
- 交生成源、完整数组或有效记录、系列映射、检查与最终文件身份；只有截图时标来源数组／嵌入字体等未验范围，技术来源查专业参考。

## 交接

数据交 [data-analysis](../praxis-data-analysis/SKILL.md)，区间／单位交 [statistics](../praxis-statistics/SKILL.md)，模型核验交 [verify](../praxis-verify/SKILL.md)，整稿正文、图注与页面交 [report](../praxis-report/SKILL.md)。
