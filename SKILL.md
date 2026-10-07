---
name: praxis
license: MIT
description: 将问题与数据推进为可解释、可复现的数学模型、独立验证与报告证据。用于建模任务拆解、模型选择、实现、敏感性分析和论文协作；无需用户预先指定算法。单个数学概念问答不必启动完整流程。
---

# Praxis

通用 Agent Skills 入口。执行脚本需要本地文件与终端、Python 3.12 和 uv；仅方法指导无需运行环境。

按用户目标，把原始问题推进为有相称证据的回答。按实际场景、团队能力和交付时间安排工作；以完成为首要目标时，优先可交付的完整成果，复杂度服从剩余时间。以任务为工作单元，问题、模型、验证和交付使用相同任务 ID；不按外部项目来源拼流程，也不按算法库现有功能选题。

## 接续与统一入口

首次在新宿主执行工具前读 [references/agent-compatibility.md](references/agent-compatibility.md)，核对文件、终端和文档能力；不假设专有工具或界面存在。解析本文件真实路径得到技能目录 BUNDLE；用户工作项目 WORKSPACE 与技能目录可以不同。先读工作项目规则与已有状态，检查 Git 和有效改动，接续已有案例。没有题目时索取原文或文件，先做不依赖题目的环境检查，不造题或结果。PDF 必须查看原页的图表和公式；比赛规则由当前项目与当届官方要求提供。

读 [references/methods.md](references/methods.md)：这是唯一的推理主线，定义各环节的输入、产出、推进条件、方法选择与失败返回位置。按当前请求进入和结束，不默认每次全流程，不要求逐步审批。

用 [references/capabilities.md](references/capabilities.md) 按实际缺口选择分析、文献、模型、计算、验证、图表或写作能力；它定义职责与交接，不是另一套流程。只读需要的专业参考，同一任务 ID、版本、单位和结论边界贯穿各能力。

- 涉及比赛、团队分工或限时完整交付时，先读 [references/context-and-team.md](references/context-and-team.md)，接续赛事／届次、实际人数、成员能力与可用时间；通用建模不默认套赛事规则，不默认用户单人。
- 已确认单人且限时或强调先完成时，读 [references/solo-delivery.md](references/solo-delivery.md)。助手承担优先级、依赖与下一步协调，给用户一个当前事项；滚动形成完整稿，预算不足采用简化路线。
- 分析记录使用 [references/tasks-template.md](references/tasks-template.md)，写入案例 planning/tasks.md；所有环节更新同一份任务记录。
- 参数能否被观测区分、尺度、优化保证、概率区间或干预结论需要判断时，读 [references/mathematical-reasoning.md](references/mathematical-reasoning.md) 的对应条件分支；不增加全题必经阶段。
- 只有会改变答案的定义歧义，才读 [references/definition-review.md](references/definition-review.md) 的区分例子。
- 文件接收、模型执行、过期核查与数值任务证据索引，读 [references/automation.md](references/automation.md)。这些脚本服务于主线，不能代替题意判断或证明模型适用。
- 引入外部方法按 methods.md 的统一规则，出处与实际复用范围见 [references/upstream-review.md](references/upstream-review.md) 和 THIRD_PARTY_NOTICES.md。

## 执行边界

技术选择通常自行形成并说明。未知若不影响当前可逆步骤就先推进；只有关键输入、目标或真实偏好会改变结论才问。假设写明依据和影响，不默认为事实，不声称用户已人工核验。

模型与独立验证器写完并审核后才用运行器执行；原始数据保持不变，参数与失败运行保留。程序自动检查、科学判断和人工核验分别表述。数值任务清单与主记录使用相同 ID；evidence 只检查已记录连接，不证明任务覆盖完整。

交付沿用用户已有文件与实际规范；LaTeX 使用当前宿主实际可用的编辑与编译工具，在已有源文件上修改；无编译能力时保留源文件并说明未验证，最终导出 PDF 另做视觉检查。真实使用的来源在报告使用处引用。程序日志不能冒充完整 AI 对话，缺失记录如实说明。公开、上传或提交需要明确授权。

结束说明结果、依据、限制和真正需要用户决定的事项；重要决定维护在工作项目已有唯一记录处。本次临时实验用 .session 并清理，有用的实际结果保留。
