# 学习回路：每做完一题都变得更强一点

当任务暴露了可迁移的成功或失败时，把结构、识别信号、路线取舍与验证方法提炼成带条件的经验。任务记录保留本题的决定与证据；课程是可复用的提炼，不再建一套本题过程台账。

## 什么时候做

- 完整任务结束时简短判断是否有新经验；限时任务先完成必要验证与交付；
- 路线被推翻、模型被修正、或被用户纠正时，先修所属规则或工具及必要回归检查，再提炼经验；
- 没有新东西可学的任务不硬写。

## 复盘问什么

1. 这题的结构是什么？一开始认对了吗？什么时候才认出来？
2. 试过哪些路线？各自死在哪里（假设、数据、计算、验证）？
3. 起作用的变换或视角是什么（松弛、对偶、变量替换、分阶段、守恒……）？
4. 哪次检查发现了问题？有没有本该更早做的检查？
5. 哪条原则下次遇到类似问题可直接用？它在什么条件下才成立？
6. 哪些地方我其实不确定？用什么证据等级标注？

## 记录：`lesson_add` 与 `lesson_search`

课程存成 JSON 行，放在**用户的项目里**（如 `planning/lessons.jsonl`），不上传、不共享。

- 必填：`problem`、`structure`、`recognized`、`routes_tried`、`what_failed`、`what_worked`、`verified_by`、`principle`；
- 可选：`tags`、`evidence`（observed once / seen repeatedly / derived / checked on a held-out problem）；
- `principle` 要写成能迁移的规则，不是对本题的描述。

路线记录完成后，`route_to_lesson` 可起草课程。逐项审核草稿是否忠实于真实尝试，再补写适用条件与可迁移原则，交给 `lesson_add`；自动起草不代表已经学会或验证。

已有课程且当前结构可能相关时，用 `lesson_search` 按关键词和标签检索；`route_graph` 新建图时传 `lessons_path` 也会返回相关经验。候选形成前审读，检索命中只是提示，不替代本题检验。

## 回归与盲测：`evals.planted`

改动工具或指南后，用已知答案的合成题检验没有退步：

```bash
uv run --locked python -m evals.planted list
uv run --locked python -m evals.planted new queue 7
uv run --locked python -m evals.planted check queue 7 '{"mean_wait": 0.42}'
```

题目由 (类型, 种子) 生成，题面不含答案；`new` 输出的 `report` 字段给出答案要用的键名（如 `{"r0": ..., "final_size": ...}`）；`check` 按种子重算真值并评分。用没见过的种子做盲测，可以检验方法和工具，不能代表现实问题上的能力。

## 成长的边界

- 记录要真实：失败写失败，不改写成“当时就认出来了”。
- 不因为一次成功就把原则写成“规律”；证据等级随复现次数提升。
- 课程也会过期：工具、规范、数据源变化后，旧课程要重新检验。
- 不把用户的私人信息、赛题原文或未公开材料写进课程。

教训可带 `failure_pattern`（失败做法）、`detected_by`（发现方法）、`signal`（下次留意的信号）；它们和其余字段一起被检索。一个经验只有迁移到未见问题并经相称检查后，才提高证据等级；重复存储或被检索到不算新的验证。
