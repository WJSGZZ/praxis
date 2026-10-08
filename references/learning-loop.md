# 学习回路：每做完一题都变得更强一点

不要让“得到答案、对话结束”成为终点。收尾时做一次简短复盘，把**可迁移的东西**存起来，下一题开始前先查。存的不是答案，而是：问题的结构、当时认出了什么、试过哪些路线、为什么失败、哪个变换起了作用、怎样验证、能迁移的原则。

## 什么时候做

- 每个完整任务结束时做一次，限时任务也留出几分钟；
- 路线被推翻、模型被修正、或被用户纠正时，当场记一条；
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

路线记录完成后，`route_to_lesson` 从记录自动起草课程草稿（你只需补写可迁移的原则），再交给 `lesson_add`。

新题开始前用 `lesson_search` 按关键词和标签找相关课程，并看 `patterns` 里反复出现的结构。检索到的课程只是提示，不替代对本题的检验；证据等级低的课程要先验证再用。

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

教训可以带三个可选字段：`failure_pattern`（失败的做法）、`detected_by`（怎么发现的）、`signal`（下次该留意什么信号）；它们和其余字段一起被检索。启动新问题时由 `route_graph` 的 `lessons_path` 在生成候选路线之前取出，不要等到复盘才看。
