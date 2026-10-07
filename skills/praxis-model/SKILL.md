---
name: praxis-model
description: 把原题变成可回答的任务和最小可验证的模型：读题与定义、变量与假设、没有数据时怎样给参数找依据、路线与模型选择、可辨识性／尺度／优化结构判断。用于“这题怎么做、用什么模型、假设合不合理、参数怎么定”。不负责大规模计算或写论文；整题推进用 praxis。
license: MIT
---

# Praxis · 问题与模型

BUNDLE 指 `praxis` 技能目录（仓库根目录，或插件里的同级 `praxis/`），脚本与全部参考都在那里；本文件的相对链接在两种布局下都有效。

## 做什么

把请求转成任务 Q1、Q2……每项都有目标量、单位、约束、成功条件，再给出能回答它的最小模型、假设及其依据、验证设计。读 [methods.md](../../references/methods.md) 的“明确问题”“形成路线”“模型与验证一起选择”。

- 只有会改变答案的歧义才读 [definition-review.md](../../references/definition-review.md)；其余写成假设并说明影响。
- 参数可辨识性、量纲、优化保证、概率区间、干预结论需要判断时，读 [mathematical-reasoning.md](../../references/mathematical-reasoning.md) 的对应分支。
- 没有数据可拟合时，用标准关联式、守恒关系和已发表测量约束参数范围，中心值、范围、依据等级写成表；没有依据的参数单列为情景；找依据时用宿主的论文检索工具读到全文位置，做法见 [writing.md](../../references/writing.md) 的“来源服务于具体论断”。依据不足的取值不要藏在代码常数里。
- 常见方法的适用条件、可用工具与必做检查见 [model-library.md](../../references/model-library.md)。
- 候选模型逐个记录：回答哪项任务、需要什么数据、额外假设、失效条件、独立验证办法。先做最容易推翻路线的手算或小例子。问题陌生或结论影响大时，先发现结构并比较至少三条结构不同的路线，见 [praxis-explore](../praxis-explore/SKILL.md)。

- 有物理、化学、生物或工程机制的题，先列出题目依赖哪些领域知识、各自的权威来源（常见机制的方程与量级见 [domain-models.md](../../references/domain-models.md)），再建模；能用计算机直接模拟（热传导、传染、排队、碰撞等）就做数值模拟，并用守恒量、解析极限、网格或步长加密、独立积分器核对。参数按“依据—范围—中心值”逐个标定，先看量纲与量级，再做敏感性；不凭调到结果好看来定参数，调参过程与被否决的取值留在记录里。
- 用户在场时，定路线前只确认会改变答案的一两件事；基线结果出来后的复盘与方法改进见 [praxis-dialogue](../praxis-dialogue/SKILL.md)。

## 产出与交接

在工作项目的 planning/tasks.md（格式见 [tasks-template.md](../../references/tasks-template.md)）写入任务、基线、假设表和候选表。基线能运行后交给 praxis-compute；需要判断结论强度时交给 praxis-verify。题意或机制被推翻时，从这里重开，不在下游悄悄改假设。
