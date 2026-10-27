---
name: praxis-review
description: 整稿水平与奖档意见：评阅完整竞赛论文或数学及应用建模研究，比较整体质量、主要差距与修改价值。用于“整篇论文到什么水平、能拿什么奖、研究贡献够不够”。局部数值与具体主张交 praxis-verify，组稿及PDF交付交 praxis-report。 Assess complete competition papers and mathematical or applied modeling research; review quality, contribution and revision priorities.
license: MIT
---

# Praxis · 作品评审

BUNDLE=`praxis` 技能目录；脚本 `BUNDLE/scripts/`；Python 3.12、uv（`uv run --locked`）；无终端仅设计。执行见 [automation.md](../../references/automation.md)。

## 做什么

- 接收原题／研究问题、当前完整稿、实际页面和证据，绑定版本与范围；按 [judging.md](../../evals/judging.md) 确认竞赛或研究，赛事—赛项—届次未知保留待核。
- 竞赛按 [contest-judging.md](../../evals/contest-judging.md) 三遍阅读：分诊阅读只看 Summary，再看图表、结论与 Memo／Letter，不复算；全文阅读核组成、机制并攻击关键主张；比较定档先定重点再比较同题真实论文，三遍结论分别保留。
- 分诊 `reader` 保留逐问答案、可信依据与追问；有参照的 `comparison` 保留参照身份、偏好、置信度和三条定位依据；无参照时的弃判断按竞赛权威执行。两块仍可选，连同 `issues.severity` 沿用旧 schema／聚合算术。
- 问题按 [review-protocol.md](../../references/review-protocol.md) 分级：`decisive` 改变主答案且原框架内无法局部修复，竞赛中只有这一级可以单独压档；`substantive` 与长处权衡，影响未明标待核；`local` 只列修改。同根因共用 issue，复算预算不超过评审三分之一。
- 评自家作品用全新上下文，只读原题、数据、成品 PDF 和评审规则，不读作者的任务记录、收据、内部评阅或方法指导；竞赛无同题参照不给档次。旧评语保留原版本。
- 研究按 [research-judging.md](../../evals/research-judging.md) 六维定性评价，以数学方法为主干，按实际主张补核学科证据与适用性，按其研究呈现顺序交付；研究生／开放竞赛仍归竞赛。缺完整稿标明范围。
- 完整稿另做 [独立读者检查](../../references/automation.md#当前交付的论文诊断全部先告警)：全新上下文只读渲染页面、原问题和九条清单，记录 `reader_review` 与PDF SHA，不读作者日志或内部评语。缺记录写“未经独立读者审阅”，有未处理问题列数量；修复或附理由保留后同一读者定点复核，明确是复核，不叫盲读。状态只是告警，不替代科学评审或新增拒绝。

## 交接

大量数学核验交 [praxis-verify](../praxis-verify/SKILL.md)，定义回 [model](../praxis-model/SKILL.md)，页面与表达交 [praxis-report](../praxis-report/SKILL.md)；评委辨别力按 [PROTOCOL.md](../../evals/PROTOCOL.md) 另验，规则接入不视作校准。
