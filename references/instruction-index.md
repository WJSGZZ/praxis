# 指令阶段与按需细则索引

由 `scripts/instruction_packet.py --print-index` 从运行时资源定义生成；勿手工修改。

无终端时按下表直接读取文件与指定区段。core 指唯一 `<!-- praxis:core:start -->` 至 `<!-- praxis:core:end -->` 内的正文；全文包括技能头信息。章节指同名标题及其下级内容，至下一个同级或更高标题。

每阶段均包含完整 integrity 安全文与 learning-loop 的“同题资料与接触范围”节。研究阶段另外必读 research 原文，不继承竞赛清单或 MCM current 命令；竞赛阶段才增加竞赛清单与交付核心。

公共核心限制9390字符；研究额外必读与条件细则另计，研究全部阅读不受此数字代表。无终端或工具不支持选区时，实际加载量未知；如读取了更多正文须如实计入，不能声称已运行、已精确限量或已通过执行检查。

普通链接不自动递归；实际缺口出现时按本索引继续选择细则，并记录加载。

## 阶段必读

| 阶段 | 文件 | 范围 |
|---|---|---|
| model | [SKILL.md](../SKILL.md) | 全文 |
| model | [skills/praxis-model/SKILL.md](../skills/praxis-model/SKILL.md) | 全文 |
| model | [references/methods.md](methods.md) | core |
| model | [references/modeling-gate.md](modeling-gate.md) | core |
| model | [references/automation.md](automation.md) | core |
| model | [references/integrity.md](integrity.md) | 全文 |
| model | [references/learning-loop.md](learning-loop.md) | 章节：同题资料与接触范围 |
| compute | [SKILL.md](../SKILL.md) | 全文 |
| compute | [skills/praxis-compute/SKILL.md](../skills/praxis-compute/SKILL.md) | 全文 |
| compute | [references/methods.md](methods.md) | core |
| compute | [references/modeling-gate.md](modeling-gate.md) | core |
| compute | [references/automation.md](automation.md) | core |
| compute | [references/integrity.md](integrity.md) | 全文 |
| compute | [references/learning-loop.md](learning-loop.md) | 章节：同题资料与接触范围 |
| verify | [SKILL.md](../SKILL.md) | 全文 |
| verify | [skills/praxis-verify/SKILL.md](../skills/praxis-verify/SKILL.md) | 全文 |
| verify | [references/methods.md](methods.md) | core |
| verify | [references/automation.md](automation.md) | core |
| verify | [references/integrity.md](integrity.md) | 全文 |
| verify | [references/learning-loop.md](learning-loop.md) | 章节：同题资料与接触范围 |
| report | [SKILL.md](../SKILL.md) | 全文 |
| report | [skills/praxis-report/SKILL.md](../skills/praxis-report/SKILL.md) | 全文 |
| report | [references/methods.md](methods.md) | core |
| report | [references/writing.md](writing.md) | core |
| report | [references/automation.md](automation.md) | core |
| report | [references/integrity.md](integrity.md) | 全文 |
| report | [references/learning-loop.md](learning-loop.md) | 章节：同题资料与接触范围 |
| contest | [SKILL.md](../SKILL.md) | 全文 |
| contest | [skills/praxis-model/SKILL.md](../skills/praxis-model/SKILL.md) | 全文 |
| contest | [skills/praxis-compute/SKILL.md](../skills/praxis-compute/SKILL.md) | 全文 |
| contest | [skills/praxis-verify/SKILL.md](../skills/praxis-verify/SKILL.md) | 全文 |
| contest | [skills/praxis-report/SKILL.md](../skills/praxis-report/SKILL.md) | 全文 |
| contest | [references/methods.md](methods.md) | core |
| contest | [references/modeling-gate.md](modeling-gate.md) | core |
| contest | [references/automation.md](automation.md) | core |
| contest | [references/writing.md](writing.md) | core |
| contest | [references/contest-paper-checklist.md](contest-paper-checklist.md) | core |
| contest | [references/contest-delivery.md](contest-delivery.md) | core |
| contest | [references/integrity.md](integrity.md) | 全文 |
| contest | [references/learning-loop.md](learning-loop.md) | 章节：同题资料与接触范围 |
| research | [SKILL.md](../SKILL.md) | 全文 |
| research | [skills/praxis-model/SKILL.md](../skills/praxis-model/SKILL.md) | 全文 |
| research | [skills/praxis-compute/SKILL.md](../skills/praxis-compute/SKILL.md) | 全文 |
| research | [skills/praxis-verify/SKILL.md](../skills/praxis-verify/SKILL.md) | 全文 |
| research | [skills/praxis-report/SKILL.md](../skills/praxis-report/SKILL.md) | 全文 |
| research | [references/methods.md](methods.md) | core |
| research | [references/modeling-gate.md](modeling-gate.md) | core |
| research | [references/automation.md](automation.md) | core |
| research | [references/writing.md](writing.md) | core |
| research | [references/integrity.md](integrity.md) | 全文 |
| research | [references/learning-loop.md](learning-loop.md) | 章节：同题资料与接触范围 |
| research | [references/research-mode.md](research-mode.md) | 额外必读 detail `research`；全文 |

## 条件细则

只有对应缺口或明确阶段要求才读取；先选ID，再按真实文件/标题取文。被core/details分区的文件，细则取details区；标题未指定时取整个细则区，未分区的文件取全文；`@intro`取文件开头至首个二级标题前。

| ID | 文件 | 标题/范围 | 触发 |
|---|---|---|---|
| `environment-api` | [references/automation.md](automation.md) | @intro | 定位实际工具/环境/权限范围或runtime_info诊断 |
| `case-choice` | [references/automation.md](automation.md) | 先判断要不要走案例系统 | 已有可复现链或是否建案例需要取舍 |
| `parallel-budget` | [references/automation.md](automation.md) | 并行计算的预算 | 准备并行计算前核资源与小样本计时 |
| `case-intake` | [references/automation.md](automation.md) | 建立案例 | 首次接收文件/编码/目录/延后审计接口不清 |
| `content-boundary` | [references/automation.md](automation.md) | 内容理解不是脚本替代的 | 机器门与题意/独立性判断的职责不清 |
| `information-api` | [references/automation.md](automation.md) | 按信息截点映射版本 | 多版本预测或信息截点映射 |
| `math-results` | [references/automation.md](automation.md) | 数学工具的结果契约 | 调用数学工具前核返回/保证/范围 |
| `run-api` | [references/automation.md](automation.md) | 运行与接续 | 运行参数/快照/失败/过期或接续接口不清 |
| `writing-api` | [references/automation.md](automation.md) | 写作连接 | 跨多个交付诊断接口、需完整写作API；不用于默认入门 |
| `feedback-api` | [references/automation.md](automation.md) | 可选运行反馈 | 用户选择保存运行反馈 |
| `live-case-api` | [references/automation.md](automation.md) | 活案例：字段绑定、依赖与局部更新 | 选择活案例字段/依赖/局部更新操作 |
| `convergence` | [references/convergence.md](convergence.md) | 全文/整个details区 | 正文/附录取舍或整稿收敛仍不清 |
| `data` | [references/data-computing.md](data-computing.md) | 全文/整个details区 | 数据口径/连接/信息版本缺口 |
| `tasks` | [references/tasks-template.md](tasks-template.md) | 全文/整个details区 | 任务记录结构不清，需要骨架 |
| `tools` | [references/model-library.md](model-library.md) | 全文/整个details区 | 方法/工具适用范围或既有实现不明 |
| `scientific-writing` | [references/scientific-writing.md](scientific-writing.md) | 全文/整个details区 | 局部学术论证/公式解释需要专项修订 |
| `literature` | [references/literature-review.md](literature-review.md) | 全文/整个details区 | 需要综述而非普通来源核读 |
| `research` | [references/research-mode.md](research-mode.md) | 全文/整个details区 | 任务为研究而非完整竞赛 |
| `defense` | [references/defense-coaching.md](defense-coaching.md) | 全文/整个details区 | 实际共同研究或答辩准备 |
| `capabilities` | [references/capabilities.md](capabilities.md) | 全文/整个details区 | 请求超出四主责或需要专业分工 |
| `methods-failure` | [references/methods.md](methods.md) | 失败回到原因所在的环节 | 无法确定失败应退回哪个阶段 |
| `methods-records` | [references/methods.md](methods.md) | 工作单元与记录 | 跨案例依赖或任务ID记录不清 |
| `methods-models` | [references/methods.md](methods.md) | 模型与验证一起选择 | 已选模型需要对应基线/升级/核查速查 |
| `methods-assumptions` | [references/methods.md](methods.md) | 假设、理由与结论范围 | 实质前提用途/失效分析仍不清 |
| `methods-evidence` | [references/methods.md](methods.md) | 证据的层次 | 证明辅助性质或独立证据的覆盖范围不清 |
| `methods-stop` | [references/methods.md](methods.md) | 停止深挖与交付 | 预算中断或候选/有效版本接续不清 |
| `methods-change` | [references/methods.md](methods.md) | 根因修复与全文变更影响 | 跨章节变更影响/重算范围仍不清 |
| `methods-learning` | [references/methods.md](methods.md) | 吸收外部方法的统一规则 | 拟引入外部方法或新增永久步骤 |
| `writing-name` | [references/writing.md](writing.md) | 正式报告文件命名 | 改名或候选/正式文件管理问题 |
| `writing-chinese-english` | [references/writing.md](writing.md) | 中文论文与英文论文各按自己的习惯写 | 目标语言术语/句法/格式自然度问题 |
| `writing-argument` | [references/writing.md](writing.md) | 论证先于润色 | 主线/章节论证仍不清 |
| `writing-closeout` | [references/writing.md](writing.md) | 接收与交付 | 全文联核/引文/PDF文本诊断仍有疑点 |
| `delivery-style` | [references/contest-delivery.md](contest-delivery.md) | 共享模板与实际成品 | 样式漂移/特殊组件/历史版式问题 |
| `delivery-submit` | [references/contest-delivery.md](contest-delivery.md) | 披露与提交结构 | 提交对象/附件/支撑包差异不清 |
| `gate-fields` | [references/modeling-gate.md](modeling-gate.md) | 全文/整个details区 | 字段格式不清或契约门禁报错 |
| `paper-components` | [references/contest-paper-checklist.md](contest-paper-checklist.md) | 全文/整个details区 | 需要表格/Memo格式示例或检查组件缺项 |
| `writing-language` | [references/writing.md](writing.md) | 语言专项：先冻结含义，再分别写作 | 仅语言修订/自然度问题 |
| `writing-sources` | [references/writing.md](writing.md) | 来源服务于具体论断 | 需要检索/核读外部来源 |
| `writing-figures` | [references/writing.md](writing.md) | 论文骨架、验证与图表 | 图题/证明/参数解释或章节编辑缺口 |
| `delivery-api` | [references/automation.md](automation.md) | 竞赛模板与组件 API | 特殊组件或编译/冻结接口及报错无法由核心解决 |
| `reader-api` | [references/automation.md](automation.md) | 当前交付的论文诊断（全部先告警） | 独立读者包字段/诊断接口不清 |
| `model-api` | [references/automation.md](automation.md) | 模型与验证器 | 模型/验证器接口不清或运行契约报错 |
| `requirements-api` | [references/automation.md](automation.md) | 数值任务的证据索引 | requirements/evidence接口不清 |
| `workflow-api` | [references/automation.md](automation.md) | 可选任务协调 | 选择多轮workflow且其审阅字段/经验连接不清 |
| `intake-api` | [references/automation.md](automation.md) | 接收 Word 和 Excel 附件 | 复杂Word/Excel附件、对象抽取缺失 |
| `routes` | [references/structure-discovery.md](structure-discovery.md) | 全文/整个details区 | 结构/路线未知、常规基线与备选无法回答 |
| `math` | [references/mathematical-reasoning.md](mathematical-reasoning.md) | 全文/整个details区 | 表示/参数可辨识性/界/外推保证缺口 |
| `domain` | [references/domain-models.md](domain-models.md) | 全文/整个details区 | 领域机制/量级无法由现有契约确认 |
| `foundations` | [references/scientific-foundations.md](scientific-foundations.md) | 全文/整个details区 | 数值/统计/不确定性检查细节缺口 |
| `review` | [references/review-protocol.md](review-protocol.md) | 全文/整个details区 | 重要评语需复现并判断实际影响 |
| `figures` | [references/visualization.md](visualization.md) | 全文/整个details区 | 具体制图/图例/空间数据/最终字号问题 |
| `contest-profile` | [references/contest-delivery.md](contest-delivery.md) | 届次、格式与阅读文件 | 非默认赛事或需要核官方规范与项目选择 |
