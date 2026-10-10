# 决策研究案例：收费站布局与汇合排队

**2017 MCM B · Merge After Toll：把收费能力、支付兼容和出口空间连接起来，判断扩建何时有用。**

[English](README.en.md) · [完整论文](paper/paper.pdf) · [计算结果](reference/accepted.json) · [案例总览](../../demos/README.md) · [Praxis](../../README.md)

[主要结果](#主要结果) · [作品评议](#作品评议) · [计算复现](#计算复现)

## 问题与难点

多开几个收费窗口，是否一定能让车辆更快离开？题目要求设计收费站布局，并兼顾通行效率、费用与安全。

两类限制容易被忽略：现金车辆不能使用空闲的电子收费窗口；通过收费站的车辆仍需加速、汇合并占用出口空间。**收费能力提高，出口等待反而可能增加。** 本例研究这些机制怎样改变布局选择。

## 主要结果

以下为列明假设下的条件模型结果，尚非某座收费站的实测结论。

| 发现 | 条件与证据 |
|---|---|
| 总服务能力不能直接当作通行能力 | 初始布局的总量上界为 **5,400 辆/小时**，名义支付构成下只能持续接收 **3,000 辆/小时**；支付兼容网络给出阈值。 |
| 八窗口方案达到 **4,000 辆/小时** | 441 种连续分组／支付聚类布局中选出 **4/3/1** 窗口配置，另与 6,750 种不限制聚类的矩阵比较；独立最大流与 LP 检查一致。 |
| 支付构成改变扩建需求 | 三种支付情景、服务均值 12/6/2 秒下，至少需要 **11 窗口**才能覆盖 3,600 辆/小时，已有可行布局。改为 15/10/3 秒后，**14 窗口仅是必要数量**，未构造对应方案。 |
| 出口空间不足会反转方案偏好 | 名义重交通、每组 16 个收费后占用名额时，稳健八窗口平均等待 **21.9 秒**，11 窗口为 **54.3 秒**；64 名额时后者降到 **8.3 秒**。 |
| 几何设计还需要运行规则 | 名义方案含 **91.44 米**平行恢复区和 **230 米**渐变段；共同速度与行程条件下，入口计量等价于出口递推。间距论证不构成事故预测。 |

## 建模与验证

支付类型与出口组组成流量网络，最小割给出容量条件，避免把不兼容的空闲窗口计入可用能力。几何模型区分加速恢复区与汇合渐变段，面积、费用和行程时间据此计算。

排队模型同时比较无限储车与有限占用。Little 定律给出必要占用下界，解析流量证书达到该界；下界仍不是充分的安全储车设计。最小化最大资源利用率的路由候选在部分情景改善、另一些恶化等待，因此作为被拒候选保留，未被描述成最小等待策略。

计算证据包括 256 组独立 LP 对照、可手算队列、有限／无限占用对照、解析储车界及入口计量等价检查。[独立审计](reference/independent-audit.json)与[审计修订](reviews/routing-audit-revision.json)分别记录原核验和后来修正的策略输入比较；两份归档各通过 21 项新审计，原数值和失败候选保留。

## 作品评议

**论文较好地解释了扩建的收益为何取决于支付兼容与下游空间，而不是只比较窗口数量。**

主要优点是机制之间有实际连接：容量约束进入布局，几何进入行程与占用，有限队列再改变推荐。摘要、结果表和管理部门建议函的事实与条件一致。保留反转情景和不成功的路由，增强了论证的可核查性。

主要限制在现实映射：服务参数、驾驶行为和占用名额缺少现场标定，间距论证未覆盖重车、制动及所有安全因素。因此，当前作品适合条件分析与方法检验，尚不足以直接用于现场建设。

作者外 AI 完成全文源码与结果一致性评阅；独立数值审计与 PDF 版式核验另有记录。奖项判断没有可靠届次边界，现有评议未给档次。[全文评阅](reviews/final-review.json) · [评估范围](reviews/user-assessment.json)

## 论文与材料

| 资源 | 内容 |
|---|---|
| [完整 17 页英文论文](paper/paper.pdf) | 摘要、解答、四幅图、管理部门建议函、参考文献与 AI 使用说明 |
| [论文源码与生成器](paper/) | 由冻结结果生成表格、图形及 LaTeX |
| [参考结果](reference/) | 接受方案、被拒路由、原基线与核验记录 |
| [研究记录](reviews/study.md) | 实际过程、版本与失败 |

当前稿采用共享美赛模板；其中 1 页为 AI 使用说明。历史首稿保留原样，往年题解的交付结构不作为现行比赛或工程标准认证。

## 计算复现

在 Praxis 仓库根目录执行，输出目录须不存在：

```bash
uv sync --locked
uv run --locked python research/merge-after-toll/reproduce.py --output .session/merge-replay
```

入口重算当前方案，运行验证器和作者外角色编写的审计，比较冻结数值并检查归档哈希。它不覆盖已有论文或参考结果。

<details>
<summary>候选、基线与论文构建</summary>

```bash
uv run --locked python research/merge-after-toll/reproduce.py --candidate --output .session/merge-candidate
uv run --locked python research/merge-after-toll/reproduce.py --baseline --output .session/merge-baseline
uv run --locked python research/merge-after-toll/paper/build_report.py \
  --results research/merge-after-toll/reference/accepted.json --output .session/merge-paper
uv run --locked python -m scripts.paper_template research/merge-after-toll/paper/paper.tex \
  --contest mcm --compile --output-directory outputs/toll-build-001
```

第三条从冻结结果生成可编辑源码；第四条用固定 Tectonic 环境编译归档论文源，各自要求新输出目录。构建回执记录源码与 PDF 身份；新 PDF 需逐页检查后再采用。

</details>

## 文件结构

```text
paper/          英文终稿、LaTeX 与生成器
baseline/       历史首稿与当时计算源
code/           当前模型、独立验证器与被拒候选
reference/      冻结结果与数值审计
reviews/        全文评阅、研究过程与修订范围
manifest.json   源码、环境、时间、来源与文件哈希
reproduce.py    统一复现入口
```

## 资料与许可

题目来自 [COMAP 官方题面](https://www.contest.comap.com/undergraduate/contests/mcm/contests/2017/problems/2017_MCM_Problem_B.pdf)。通用参考包括 FHWA 的[模型标定指导](https://ops.fhwa.dot.gov/trafficanalysistools/tat_vol3/sect5.htm)、[历史收费后区域指导](https://mutcd.fhwa.dot.gov/rpt/tcstoll/chapter642.htm)与[窗口布置指导](https://mutcd.fhwa.dot.gov/rpt/tcstoll/chapter224.htm)，历史指南不代表完整现行规范。

本例是已接触同题材料的 AI 开发研究，非隔离盲测；各角色核验范围单独记录。原创代码、论文与说明采用仓库 [MIT 许可](../../LICENSE)，不复制外部题面或购买资料。研究归档不随默认插件安装包分发。

<details>
<summary>版本与研究身份</summary>

九页首稿在候选研究进行时形成，不能作为事先固定的对照组；[研究记录](reviews/study.md)保留实际时间与失败。项目此前读过同题论文 56731，历史暴露见[勘误](reviews/exposure-correction.json)；无法重建的上下文和原始对话不补造。本题无使用者建模或核验记录，产品开发要求另记。

[版式修订](reviews/layout-revision.json)与[首页修订](reviews/frontmatter-revision.json)分别绑定已有成品，不将旧数学评阅算作新排版验收。`manifest.json` 同时保留归档身份与本次说明文档的修订关系。

</details>
