---
name: praxis-model
description: 把原题变成可回答的任务和最小可验证的模型：读题与定义、变量与假设、没有数据时怎样给参数找依据、路线与模型选择、可辨识性／尺度／优化结构判断。用于“这题怎么做、用什么模型、假设合不合理、参数怎么定”。不负责大规模计算或写论文；整题推进用 praxis。
license: MIT
---

# Praxis · 问题与模型

BUNDLE 指 `praxis` 技能目录（仓库根目录，或插件里的同级 `praxis/`），脚本与全部参考都在那里；本文件的相对链接在两种布局下都有效。

## 调用契约

输入：原题、数据条件、目标与约束。产出：明确题意、假设、基线与替代路线。依赖与边界：按缺口读模型参考；不认证数值结果或替写报告。

## 做什么

把请求转成任务 Q1、Q2……每项都有目标量、单位、约束、成功条件，再给出能回答它的最小模型、假设及其依据、验证设计。读 [methods.md](../../references/methods.md) 的“明确问题”“形成路线”“模型与验证一起选择”。

- 只有会改变答案的歧义才读 [definition-review.md](../../references/definition-review.md)；其余写成假设并说明影响。
- 参数可辨识性、量纲、优化保证、概率区间、干预结论需要判断时，读 [mathematical-reasoning.md](../../references/mathematical-reasoning.md) 的对应分支。
- 没有数据可拟合时，按 mathematical-reasoning.md 的参数范围规则列依据表，不把无依据取值藏在代码常数里；来源核验见 [writing.md](../../references/writing.md) 的“来源服务于具体论断”。
- 常见方法的适用条件、可用工具与必做检查见 [model-library.md](../../references/model-library.md)。
- 候选模型逐个记录：回答哪项任务、需要什么数据、额外假设、失效条件、独立验证办法。先做最容易推翻路线的手算或小例子。问题陌生或结论影响大时，先发现结构并比较至少三条结构不同的路线，见 [praxis-explore](../praxis-explore/SKILL.md)。

- 有物理、化学、生物或工程机制的题，先核对所需机制与量级，见 [domain-models.md](../../references/domain-models.md)。解析式、平衡关系足以回答时先用它们；需要时空过程才做数值模拟，按 [scientific-foundations.md](../../references/scientific-foundations.md) 设计守恒、解析极限与收敛检查。参数依据与标定见 mathematical-reasoning.md，不凭结果好看调值。
- 用户在场时，定路线前只确认会改变答案的一两件事；基线结果出来后的复盘与方法改进见 [praxis-dialogue](../praxis-dialogue/SKILL.md)。

## 产出与交接

持续任务按 [tasks-template.md](../../references/tasks-template.md) 更新已有任务记录，写入任务、基线、假设与路线取舍。模型、参数输入和验证设计明确后交给 praxis-compute 实现与运行；需要判断结论强度时交给 praxis-verify。题意或机制被推翻时，从这里重开，不在下游悄悄改假设。
