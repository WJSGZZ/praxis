---
name: praxis-data-analysis
description: 理解数据实际测量什么，开展探索性分析、缺失与采样审查、单位和多表连接核验，并形成可供建模的数据契约。用于“这份数据说明什么、先做EDA、检查缺失、这些表怎么连接、样本是否有偏”。Understand a dataset, exploratory data analysis, missingness, sampling, measurement units and join cardinality. 文件接收和运行快照共用 praxis-compute；统计推断交 praxis-statistics，完整任务仍由 praxis 协调。
license: MIT
---

# Praxis · 数据理解与探索

BUNDLE=`praxis` 技能目录；脚本 `BUNDLE/scripts/`；Python 3.12、uv（`uv run --locked`）；无终端仅设计。执行见 [automation.md](../../references/automation.md)。

## 做什么

- 按 [data-analysis.md](../../references/data-analysis.md) 定义行、实体、测量、单位、独立样本与抽样框；缺字典时先查结构，未知含义保留待核。
- 区分真零、未记、不适用、未检出和删失；依 [data-computing.md](../../references/data-computing.md) 保全原件，变换生成有说明的派生数据。
- 声明键、时效与基数，`audit_join` 或 Pandas merge 后核空键、唯一性、别名、覆盖、行膨胀及关键分组总量。
- EDA 查分组／时序覆盖、稳健摘要、异常与合理处理的敏感性，交代扫描／抽样范围；机制判断保留证据边界。
- 版本账本保留实体×事件×字段的可用时点，`asof_join` 选择截点前原行；缺时点与同刻冲突留未决。
- 交数据字典、处理与影响、覆盖／缺失／连接证据，核已知小例与高风险边界；Pandas／NumPy 优先，Pandera 等按实际环境选用。

## 交接

推断交 [statistics](../praxis-statistics/SKILL.md)，文本交 [text-analysis](../praxis-text-analysis/SKILL.md)，预测交 [time-series](../praxis-time-series/SKILL.md)，定义回 [model](../praxis-model/SKILL.md)，前提交 [assumptions](../praxis-assumptions/SKILL.md)，运行／独立核验交 [compute](../praxis-compute/SKILL.md)／[verify](../praxis-verify/SKILL.md)。
