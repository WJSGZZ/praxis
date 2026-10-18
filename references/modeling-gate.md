# 算前门禁：把模型写成可检查的契约

完整建模先产出 `planning/model-contract.json`，再交 compute。schema 2 每次运行前核必填字段与下列一致性，一次列出全部问题；schema 1 沿用原行为。契约是作者声明，机器核声明的一致性，遗漏的方程及现实解释仍需独立审查。

| 检查 | 契约产出与人工核查 |
|---|---|
| 符号一义 | `symbols[{symbol,unit,object,uses:[{equation,object}]}]`，至少一个符号：逐方程列每个符号的物理对象。顶层 `object` 与各处用法文字不同且未给 `same_object_justification` 时只告警，帮助独立审查定位，不拒绝，也不代表对象语义已核；描述字段仍必填，列出全部实际用法。真正比较对象身份需另设短标识。比较符号时去掉空格、花括号和反斜杠（`H_z` 与 `H_{z}` 是同一符号）；`mechanisms[*].effect_variable` 与 `parameters[*].symbol` 必须已在 symbols 中声明。 |
| 量纲 | 在符号单位、参数单位、`mechanisms[*].equation` 所指方程中逐项核左右量纲与时间／空间／币值尺度；将单位复算写入 `cheapest_refutation`。脚本校验字段，量纲结论由实际复算支持。 |
| 守恒／平衡 | `conserved_quantities[{name,check_name}]`，检查名用 `balance:<name>`；独立验证器给同名通过的 check。逐项核适用的质量、数量、能量或现金，明确源汇与边界。 |
| 概率独立性 | `probability_combinations[{expression,independence,justification}]`，independence 为 assumed/derived/not_assumed；假定独立须给理由，乘法组合核共同失败与依赖。 |
| 逻辑类型 | `logical_claims[{claim,type,proof_ref}]`，type 为 sufficient/necessary/both；用可行见证、必要界与证明支持对应量词。 |
| 极限情形 | `limiting_cases[{case,expected}]`：列 0、趋于无穷或单个对象等适用情形及预期，再以手算／小例核对。 |
| 参数量级 | `parameters[{symbol,value,unit,source_level,source,real_world_quantity}]`；source_level 取 measured/literature/fitted/declared，或仅与 `value: null` 搭配的 unknown。真实量给 `reference_magnitude{value,unit,source,ratio_ok}`；默认比值区间 `[0.1,10]` 为实验参数，越界给 `magnitude_justification`；自定 `ratio_ok` 下界须大于 0，比默认区间宽时同样须给理由。拿不到数值时写 `"value": null` 加 `"source_level": "unknown"`：不拒绝，收据 `model_contract_warnings` 告警，量级检查跳过并告警。超过七成参数仅声明情景时收据告警。 |
| 信息时点 | `information_time`：谁知道什么、何时与何种精度取得；`spatial` 为布尔值，空间对象的基准写在任务记录。 |
| 最便宜反驳 | `cheapest_refutation{method,result}`：method 为 hand_calc/small_example/unit_check；写实际计算、预期、结果及支持范围。 |

机制另列 `mechanisms[{id,cause,effect_variable,sign,equation}]`，sign 为 `+`、`-` 或 `±`。无适用项的清单给空数组并在任务记录解释，按实际模型选择检查。各类理由字段至少含 3 个字母或汉字，“.”不算理由。`balance:` 检查的 method 只能是 conservation、analytic 或 bound。

题面条目（`planning/requirements.json`，schema 2）：每个 requirement 必填 `kind`（answer/forecast/decision/proof）；所挂题面原句含 forecast、predict、projection、future、预测、未来、趋势而 kind 不是 forecast 时，须写 `kind_justification`。`quote` 至少 4 个英文词或 15 个字母、数字或汉字（中文按字数），条目间不得重复；跨行断词的连字符（`reser-` 换行 `voir`）两边都可去掉后比对。init 记录 `problem-extracted.txt` 的哈希，之后改动须在 `problem_text_corrections[{before,after,reason}]` 逐条列出。契约被拒不消耗 workflow 尝试次数，`next` 返回 prepare 并列出问题；评审 `mechanism_audit.symbols_checked` 不少于契约声明的符号数。workflow 在 init 时记录案例 schema，之后改动即拒绝；status 把 schema 2 收据在 schema 已改的案例中标为过期。

字段与错误结果唯一见 [automation.md](automation.md#模型与验证器)；模型选择归 [methods.md](methods.md)，结构与数学检查见 [structure-discovery.md](structure-discovery.md)、[mathematical-reasoning.md](mathematical-reasoning.md)。
