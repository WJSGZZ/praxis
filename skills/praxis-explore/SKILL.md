---
name: praxis-explore
description: 面对陌生问题、不知道用什么模型、想找更好的办法或没有标准答案时使用：发现问题背后的数学结构，比较几条结构不同的路线，攻击并淘汰它们，保留中间结果、重组，在没有答案时用实验数学（猜想、反例、高精度检验）产出可验证的结论，并把经验存成可迁移的课程。用于“这题属于什么类型”“还有没有别的路”“这个结论站得住吗”“没有答案怎么办”。不替代计算与独立验证。
license: MIT
---

# Praxis · 结构、路径与探索

BUNDLE 指 `praxis` 技能目录。标准题不必展开：写一行“为什么选它、放弃了什么”即可。问题陌生、第一条路线太顺、结论影响大或没有标准答案时，才按下面做。

## 做什么

1. **发现结构**：按 [structure-discovery.md](../../references/structure-discovery.md) 的问题清单提问，用 `probe_structure`、`dimensional_analysis`、`check_total_unimodularity` 低成本探测；把发现的结构、依据等级和推论写下来。现实机制到数学结构的对应表也在那里。
2. **比较路线**：按 [path-search.md](../../references/path-search.md)，从结构各取一条再加最简基线，至少三条结构不同的路线；廉价探索、正面攻击（逆向、事前验尸、证伪、反例搜索、独立方法）、淘汰并留存中间结果、重组、收敛。用 `route_graph` 保存记录；工具会拒绝没有原因的淘汰、没有存活攻击的选定、少于三条的比较和没有后备的假设。
3. **没有答案时**：按 [research-mode.md](../../references/research-mode.md) 做实验数学：算小例子 → `guess_sequence`、`find_relation` 猜规律 → `test_conjecture`、`find_counterexample` 检验与证伪 → 尝试证明；每条结论标把握等级，声称新之前先检索文献。
4. **留下经验**：任务收尾按 [learning-loop.md](../../references/learning-loop.md) 复盘，`lesson_add` 存课程，新题开始前 `lesson_search`；用 `evals.planted` 的已知答案题做回归与盲测。

## 怎么调用

在仓库（或插件）根目录运行；命令行与 Python 两种入口等价：

```bash
uv run --locked python -m scripts.mcp_server --list                  # 工具及字段（带 * 的必填）
uv run --locked python -m scripts.mcp_server --describe probe_structure   # 一个工具的完整输入格式
uv run --locked python -m scripts.mcp_server --call probe_structure '{"property":"convexity","expression":"x**2+y**2","names":["x","y"],"bounds":[[-1,1],[-1,1]]}'
```

| 工具 | Python 入口 |
|---|---|
| `probe_structure`、`dimensional_analysis`、`check_total_unimodularity` | `modeling.structure` |
| `route_graph`、`route_to_lesson` | `modeling.routes.apply`、`modeling.routes.draft_lesson` |
| `lesson_add`、`lesson_search` | `modeling.lessons.add_lesson`、`search_lessons` |
| `test_conjecture`、`find_counterexample`、`guess_sequence`、`check_recurrence`、`find_relation` | `modeling.experiment`（`test_conjecture` 另有 mpmath 高精度版） |

不在仓库根目录用 Python 导入时设置 `PYTHONPATH` 指向它。字段缺失或写错时，报错会列出必填字段与全部字段。

## 边界

- 结构是假设：探测找不到反例只是证据，找到反例才是证明。结论里按证据等级表述。
- 探索有预算。证据足够就停，不为显得全面而增加路线。
- 工具只记录和探测，不替人判断路线是否合适；选择及理由由人和 Agent 共同负责，必要时与用户按 [praxis-dialogue](../praxis-dialogue/SKILL.md) 讨论。
- 结构探测给出的是证据：要把“凸”“单调”这类结论升级成“已推导”，需要另外做解析推导（如 Hessian、导数符号）；工具的 `proved` 字段只在找到反例时为真。路线记录和课程放在用户项目里，不上传，不写入未公开材料。

## 产出与交接

在 planning/tasks.md 记录路线结论（选了什么、放弃了什么、为什么、哪个假设失效时转向哪里），附 `route_graph` 的记录。选定路线后交给 praxis-compute 实现，结果交给 praxis-verify 检验；检验推翻路线时回到这里重开，不在下游改假设。
