---
name: praxis-visualization
description: 设计、生成和审查科研数据图：读者问题、变量与单位、聚合和不确定性、实际系列数组与图例对象对应、坐标与色标、最终尺寸字体和导出。用于“这张科研图表达对吗、画结果图、图例错位、区间带怎么表示、检查图形数据和坐标”。Scientific visualization, data-to-legend correspondence, research figures, uncertainty plots and export review. 宣传图或界面设计另走其专业流程；不合成或提高科学证据。
license: MIT
---

# Praxis · 科研图形与数据表达

专业规范只归 [visualization.md](../../references/visualization.md)；先读其“先判断是否需要图”“数学与数据核验”“工具与检查”，按需读其他小节，不复制第二份字体、配色或图表格式。图注与正文组织仍归 [writing.md](../../references/writing.md)。

## 调用契约

输入：读者要判断的问题、当前有效数据／结果与生成源、变量和单位、筛选／聚合／区间定义、交付媒介与已确认样式。产出：有理由的表达选择、实际图形及源数据对应、数字与语义检查、最终尺寸和文件检查及未完成项。只有截图时可审观察到的表达，不能认证来源数组或字体嵌入。

## 专业判断与执行

- 比较文字、表与图能否更准确回答当前问题；保留的图声明实际量、比较对象、分母、时间／空间和适用条件。趋势、分布、位置与区间使用相应编码，不用美观补齐证据。
- 从有效实际数组生成；保留筛选、聚合、变换、网格／采样、missing处理和区间计算。观测、拟合、插值与预测分清；单位、基准、轴范围／色标和独立重复单位与数据定义一致。
- 每个科学系列绑定 `series-id → 来源数组／单位／变换 → 实际artist → label／颜色／符号`。检查生成对象的实际坐标和顺序，图例用明确的handles及其labels；无标签参考线、误差带和辅助对象不得占据后续科学系列的图例位置。哈希、导出manifest或编译成功不能替代这项对应核验。
- 使用已有 `scripts/texplot.py`、Matplotlib或任务确需的成熟库，复用共享字体配置与本稿目标尺寸，不改变科学数组修外观。既有数据表达、字体／版心／实际嵌入字号和导出命令统一按 visualization.md；不能据上游期刊预设认证当前比赛或稿件。
- 抽查端点、极值、阈值、面板和正文引用；针对当前风险使用标签错位、缺失连线或轴变换的反例。渲染后实际看最终尺寸的图例、单位、字体、截断、遮挡与灰度可读性，数据检查和成品审阅分别报告。

## 交付、验证与回退

保留图源、完整数组或其有效记录、系列映射、变换／区间说明、实际检查与最终文件身份。未取得来源、实际渲染或字体条件时明确相应未验范围；不称统计正确性、科学真实性或期刊合规已自动认证。

数据定义有误回 [praxis-data-analysis](../praxis-data-analysis/SKILL.md)，估计量／区间或独立单位有误回 [praxis-statistics](../praxis-statistics/SKILL.md)，模型数值需核验交 [praxis-verify](../praxis-verify/SKILL.md)。正文与图注交 [praxis-report](../praxis-report/SKILL.md)，完整稿和赛事路由仍归 praxis。

## 技术来源

[Matplotlib官方legend API](https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.legend.html)区分自动／显式handles与只传label的顺序依赖调用；核本机接口再用。[K-Dense scientific-visualization](https://github.com/K-Dense-AI/scientific-agent-skills/blob/a1043ef544e3a100c28e70a736b6cf32554d0677/skills/scientific-visualization/SKILL.md)（固定提交，MIT）提供真实编码、区间及导出边界的参考；它的导出元数据不验证系列语义。本文是Praxis职责整理，不安装上游栈或复制其服务推广。
