---
name: praxis-scientific-writing
description: 组织和修改科研论证与论文语言，让问题、模型取舍、公式、结果和讨论形成读者能核查的主线。用于“写得像论文、AI味太重、这一段逻辑不顺、公式如何解释、英文科研表达”。Scientific prose, academic writing, argument structure, mathematical exposition and manuscript revision. 只处理论证与表达；组稿、模板和PDF交付归 praxis-report，缺失科学证据归模型与验证，不提供检测器分数或隐瞒AI来源。
license: MIT
---

# Praxis · 科研论证与表达

BUNDLE=`praxis` 技能目录；脚本 `BUNDLE/scripts/`；Python 3.12、uv（`uv run --locked`）；无终端仅设计。执行见 [automation.md](../../references/automation.md)。

## 做什么

- 按 [scientific-writing.md](../../references/scientific-writing.md) 区分组织、含混与证据缺口，围绕实际问题和答案安排论证，段落按职责组织。
- 按 [writing.md](../../references/writing.md) 冻结数字、单位、变量、比较、条件、引用与强度；原位修订，未改变模型沿用有效证据。
- 核主题链、主体与动作、公式前后及图表到结论的依赖，写出模型取舍与真实证据，不用故事补缺。
- 支持结果与边界就近交代，术语稳定，保留反面证据、研究不确定性与真实披露，删除无意义重复辩解。
- 中英文分别组织再对照事实；逐项核含义和强度，重要改写做未标方向的清楚度审读，真实读者、AI评阅和自查分别记录。

## 交接

模型交 [model](../praxis-model/SKILL.md)，主张核验交 [verify](../praxis-verify/SKILL.md)，文献交 [literature-review](../praxis-literature-review/SKILL.md)，图形交 [visualization](../praxis-visualization/SKILL.md)，整稿／PDF交 [report](../praxis-report/SKILL.md)，整体评价交 [review](../praxis-review/SKILL.md)。
