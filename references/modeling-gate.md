# 算前门禁：把模型写成可检查的契约

完整建模先产出 `planning/model-contract.json`，再交 compute。schema 2 每次运行前核必填字段与下列一致性；schema 1 沿用原行为。契约是作者声明，机器核声明的一致性，遗漏的方程及现实解释仍需独立审查。

| 检查 | 契约产出与人工核查 |
|---|---|
| 符号一义 | `symbols[{symbol,unit,object,uses:[{equation,object}]}]`：逐方程列每个符号的物理对象。各处对象文字不同，给 `same_object_justification` 说明为何仍是同一对象；列出全部实际用法。 |
| 量纲 | 在符号单位、参数单位、`mechanisms[*].equation` 所指方程中逐项核左右量纲与时间／空间／币值尺度；将单位复算写入 `cheapest_refutation`。脚本校验字段，量纲结论由实际复算支持。 |
| 守恒／平衡 | `conserved_quantities[{name,check_name}]`，检查名用 `balance:<name>`；独立验证器给同名通过的 check。逐项核适用的质量、数量、能量或现金，明确源汇与边界。 |
| 概率独立性 | `probability_combinations[{expression,independence,justification}]`，independence 为 assumed/derived/not_assumed；假定独立须给理由，乘法组合核共同失败与依赖。 |
| 逻辑类型 | `logical_claims[{claim,type,proof_ref}]`，type 为 sufficient/necessary/both；用可行见证、必要界与证明支持对应量词。 |
| 极限情形 | `limiting_cases[{case,expected}]`：列 0、趋于无穷或单个对象等适用情形及预期，再以手算／小例核对。 |
| 参数量级 | `parameters[{symbol,value,unit,source_level,source,real_world_quantity}]`；source_level 取 measured/literature/fitted/declared。真实量给 `reference_magnitude{value,unit,source,ratio_ok}`；默认比值区间 `[0.1,10]` 为实验参数，越界给 `magnitude_justification`。超过七成参数仅声明情景时收据告警。 |
| 信息时点 | `information_time`：谁知道什么、何时与何种精度取得；`spatial` 为布尔值，空间对象的基准写在任务记录。 |
| 最便宜反驳 | `cheapest_refutation{method,result}`：method 为 hand_calc/small_example/unit_check；写实际计算、预期、结果及支持范围。 |

机制另列 `mechanisms[{id,cause,effect_variable,sign,equation}]`，sign 为 `+`、`-` 或 `±`。无适用项的清单给空数组并在任务记录解释，按实际模型选择检查。

字段与错误结果唯一见 [automation.md](automation.md#模型与验证器)；模型选择归 [methods.md](methods.md)，结构与数学检查见 [structure-discovery.md](structure-discovery.md)、[mathematical-reasoning.md](mathematical-reasoning.md)。
