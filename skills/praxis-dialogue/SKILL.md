---
name: praxis-dialogue
description: 和不太懂数学、但懂常理的用户一起想：讲清模型、共同质疑和取舍，将直觉变成可检验的问题；按实际作品教选手答辩、做模拟追问和补弱训练。用于“给我讲讲这个模型”“我觉得哪里不对”“我们来讨论一下”“教我答辩”。不替代计算与验证；结论仍由 praxis-verify 的证据决定。 Explain and discuss a model, turn user questions into checks and coach defense using real work.
license: MIT
---

# Praxis · 对话与共同思考

BUNDLE=`praxis` 技能目录；脚本 `BUNDLE/scripts/`；Python 3.12、uv（`uv run --locked`）；无终端仅设计。执行见 [automation.md](../../references/automation.md)。

## 做什么

- 用具体数字讲输入、单位、输出与失效条件，一次一个概念；事实、推断和偏好分开，推导按用户需要展开。
- 建模前只确认影响答案的目标、硬约束与偏好；用户说“你定”时推进可独立工作，保留待核前提。
- 基线后复盘原理解、关键假设与结果；把直觉改成可检查陈述，采纳与否均用结果解释并记录来源。
- 按需要选逆向、事前验尸、证伪、反例、量级或极端情形；路线分歧比较依据与代价，不为教学机械布置练习。
- 真实共同研究按 [contributions.md](../../references/contributions.md) 留事件，贡献真实性按 [integrity.md](../../references/integrity.md)；理解、接受前提与独立核验分别记，单次解释不建台账。
- 用户要求或目标阶段需要答辩时，按 [defense-coaching.md](../../references/defense-coaching.md) 用有效论文准备证据定位，真实选手先答、补弱后用新追问复查；AI自演只算准备。

## 交接

可计算质疑交 [verify](../praxis-verify/SKILL.md)，备选路线交 [explore](../praxis-explore/SKILL.md)，科学变更回 [model](../praxis-model/SKILL.md)；沿原任务反馈结果，对话不提升证据等级。
