---
name: praxis-report
description: 把有效结果组织成可核查的整篇论文或报告：摘要与章节、结果与图表、数字与引用一致、AI披露、PDF逐页检查与冻结。用于“组织论文、组稿、改摘要、检查PDF、交付报告”。科学论证与纯语言修订交 praxis-scientific-writing，整稿水平与奖档意见交 praxis-review。 Assemble validated results into a complete modeling paper or report; manage structure, figures, citations, AI disclosure and final PDF delivery.
license: MIT
---

# Praxis · 论文与交付

BUNDLE=`praxis` 技能目录；脚本 `BUNDLE/scripts/`；Python 3.12、uv（`uv run --locked`）；无终端仅设计。执行见 [automation.md](../../references/automation.md)。

## 做什么

- 按 [writing.md](../../references/writing.md) 接续原稿、有效证据、任务和生成源；纯语言修改只读“语言专项”，交 [scientific-writing](../praxis-scientific-writing/SKILL.md)；不新增科学主张。
- 正式主报告使用 `report.tex`／`report.pdf`，按 writing.md 的命名约定同步生成、编译和阅读入口；用户指定名及提交规范优先，历史冻结材料不追改。
- 完整稿按 [convergence.md](../../references/convergence.md) 取舍正文／附录；竞赛假设章及必备产出只按 [contest-paper-checklist.md](../../references/contest-paper-checklist.md)，研究结构按 [research-mode.md](../../references/research-mode.md)。
- 核题问—前提—输出—答案；比较默认给同口径基线及差值，缺项写理由。无有效结果回科学任务，数量指标不定档。
- 图表用途、系列数据与图例、字体及最终尺寸按 [visualization.md](../../references/visualization.md)；专项绘图交 [visualization](../praxis-visualization/SKILL.md)，全文核引用与条件。
- 来源支撑按 writing.md 核读；文献综合交 [literature-review](../praxis-literature-review/SKILL.md)，交付时加载 [integrity.md](../../references/integrity.md) 的 AI 披露与贡献，沿真实记录注明缺口。
- 赛事身份和格式按 [contest-delivery.md](../../references/contest-delivery.md)，当前编译、同 PDF 字体与全页 QA、冻结及 workflow.report 只按 [automation.md 当前交付门禁](../../references/automation.md#写作连接)。
- 完整稿交付前按 [automation.md](../../references/automation.md#当前交付的论文诊断全部先告警) 生成全页读者包，让全新上下文只看渲染页面、原问题与九条清单，保存绑定PDF SHA的 `reader_review`；逐项修复或说明保留理由，改后由同一读者定点复核，不再称盲读。缺记录写“未经独立读者审阅”，未关闭写“有 N 项未处理”，均只告警，不冒称已完成。
- 修订后按 [methods.md](../../references/methods.md#根因修复与全文变更影响) 同步受影响数字、条件、摘要、结论与关联产物，实际看最终页面；公开／上传／提交须明确授权。

## 交接

前提交 [assumptions](../praxis-assumptions/SKILL.md)，科学缺口交 [verify](../praxis-verify/SKILL.md)／[compute](../praxis-compute/SKILL.md)，完整作品交 [review](../praxis-review/SKILL.md)，真实共同研究与必要答辩材料交 [dialogue](../praxis-dialogue/SKILL.md) 并按 [defense-coaching.md](../../references/defense-coaching.md) 接续。
