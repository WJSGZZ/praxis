---
name: praxis
license: MIT
description: 将问题与数据推进为可解释、可复现的数学模型、独立验证与报告证据。用于整题建模、路线选择、专业分析、论文协作与竞赛交付，无需用户先选算法。Mathematical modeling, scientific analysis, independent validation, paper collaboration and competition delivery. 单个数学概念问答不必启动整题流程。
---

# Praxis

接续目标、场景、已有工作和预算，以相称的数学证据形成完整回答。用户不负责管理技能：选择一个当前主责，按缺口协作；小任务直接完成，不套整题流程。高奖项和研究价值是追求，不是保证。

## 接续与执行

本文件目录为 BUNDLE，用户工作区与源码分开。先读项目规则、唯一状态和当前产物，核对Git及有效改动。宿主或调用失败先读 [兼容指南](references/agent-compatibility.md)，不猜接口或重复造环境。

完整委托先读 [methods.md](references/methods.md)：固定任务、模式、允许输入、预算与完成条件；先有回答题问的基线，再处理最可能改变答案的缺口。持续授权内完成实现、独立检查、整稿及实际成品、必要回归与接续，不以初稿或计划结束。保留旧失败、冻结与预算；真阻塞记证据及恢复动作，继续不依赖它的工作。

单个标准数值或局部判断直接查 [模型工具表](references/model-library.md)，用 `uv run --locked python -m scripts.mcp_server --describe 工具名` 核输入并以独立答案或界检查，不建案例、不写 tasks.md；已有任务记录仍沿用。工具成功不证明模型适用；候选、界、证书与现实结论分开。

## 按问题选专业能力

职责、输入、产出及所有专项入口归 [能力分工](references/capabilities.md)，字段归 [工具索引](references/tool-index.md)。只加载当前需要的内容，不逐个调用全套。

| 当前缺口 | 专业方向 |
|---|---|
| 题意、前提、机制与路线 | model、assumptions、explore、dynamical-modeling |
| 文献、数据与测量 | literature-review、data-analysis、text-analysis、spatial-analysis |
| 推断、预测、识别与采集 | statistics、machine-learning、time-series、causal-analysis、experimental-design |
| 动作、资源与未知 | optimization、uncertainty-analysis |
| 执行与主张核验 | compute、verify |
| 图表、论证与交付 | visualization、scientific-writing、report |
| 整稿水平及共同研究 | review、dialogue |

完整题意与路线可直接进入 [praxis-model](skills/praxis-model/SKILL.md)，完整组稿用 [praxis-report](skills/praxis-report/SKILL.md)，整稿评价用 [praxis-review](skills/praxis-review/SKILL.md)。

专项名以 `praxis-` 为前缀，是独立可发现技能。纯论证与语言归scientific-writing，report负责组稿、模板和交付；机制动态与未来统计预测分别归dynamical-modeling／time-series。优化负责方案与保证，uncertainty-analysis负责联合未知的传播，verify决定独立支持强度。沿同一任务ID交接，不建重复工作板。

## 按条件加载

- 比赛、团队及限时读 [场景与届次](references/context-and-team.md)；已确认单人且需先交付用 [单人交付](references/solo-delivery.md)。主入口按能力和依赖协调，不按论文标题机械分工。
- 科学路线查 [覆盖地图](references/coverage-map.md)、[领域模型](references/domain-models.md)及 [结构推理](references/mathematical-reasoning.md)。外部方法核接口、依赖及许可，成熟库优先，不按现有算法选题。
- 接续用 [原任务记录](references/tasks-template.md) 与 [workflow](references/workflow.md)；路线形成前读取命中的经验，记录采用或不用的理由。
- 原件、执行、快照及过期判断用 [automation](references/automation.md)；学习和封存遵 [learning-loop](references/learning-loop.md)，新会话／新代理不清零暴露。
- 完整写作及取舍用 [convergence](references/convergence.md)。竞赛用 [contest-delivery](references/contest-delivery.md)，研究用 [research-mode](references/research-mode.md)；未知届次或期刊不继承其它要求。
- 真实贡献与记录遵 [contributions](references/contributions.md) 和 [feedback](references/feedback.md)；AI自演、程序日志与同题修订不冒充真人、完整聊天或首次自主成功。

## 验证与交付

关键数字及建议先核对象、单位、信息时点、可行性和独立依据。图用真实数组，写作不补造依据或提升最优／因果／泛化强度，缺证返回上游。现有文档原位改生成源，沿宿主编译并看实际页，源、成品、摘要、引用和结论同步。

完整作品及重要修订交review按 [分类标准](evals/judging.md) 给绑定当前版本的意见；争议按 [复核协议](references/review-protocol.md) 检查，角色切换不是校准。公开／提交沿实际授权，用户资料与插件分发分开。运行需Python3.12、uv及文件／终端，指导无需环境。收尾报告结果、证据、实际范围、未验证条件与原功能影响，决定写原唯一记录。
