# 新题英文报告独立角色审读

审读者：Codex 同模型 family 的另一个 Agent 角色；没有参与本题建模与正文起草，不是人类评委，也不能排除同模型共有盲点。本文不是奖项预测，不提供获奖概率。

范围：全文审读 `final-paper/paper.tex`（包括 Summary Sheet、全部正文、表格文字、图注、信、参考文献与 AI 使用说明）；核对 `cases/mcm-2017-merge/runs/20261008T164910-dfd093b8/output/results.json` 的选定设计、全部模拟汇总、finite_buffers、occupancy_bounds、service_stress、配置与最小数量向量；读取官方题面 PDF 全部可提取文字。没有读取同题答案。没有在本角色中重新求解或逐页视觉验收 PDF，排版验收由主执行者另做。图中坐标与图注读过，但不把此操作冒充视觉验收。

读取版本指纹（记录时）：

- paper.tex SHA256 `3dd2e60b5cef1932b993295f5753b18b27b0b6373861461b59c3ab9cb572b84c`
- results.json SHA256 `84da11ab2a6d0799111c599fff71c3f68fae041b9a290f593acedd40e1c6c09e`
- 官方题面 SHA256 `894958230ec9da6df87015ae5462d8107d9ae4b217d57c24949854b2b3e2b003`

以下行号对应本次读取的源稿，之后编辑可能变化。

## 总体判断

全文主线清楚：付款兼容性使总服务率不可直接相加；切割条件说明容量；几何给出一种可执行结构；有限时段排队比较性能；有限占用进一步否定“多亭必然更好”；服务变慢时原扩建建议失效。这条主线在摘要、正文和信中基本一致，英语总体自然且可直接读懂。未发现需要推翻核心网络结论的英文语义错误。

当前最值得修的是两处表格对读者的误导和两处小范围条件／对象补全，不需要整体重写。没有必要为“更像论文”增加套话、重复声明或无验证的新主张。

## 必要或有价值的修改

1. **P2：占用下界舍入掩盖了取整原因。** 源稿155行显示连续下界 `12.00`，却给整数最小值 `13`。JSON 的 `occupancy_bounds.robust.nominal.continuous_lower_bound` 实际为 `12.000399999999999`，因而 ceil 得13是合理的；显示12.00会诱发错误质疑。建议该格写 `12.0004` 或以表注说明取整用未舍入值。本项是呈现问题，不能据此把数值结论判错。
2. **P2：有限占用表应明确八亭指 robust 设计。** 源稿162–173行列头仅 `8-booth wait (s)`，而此前有 initial/nominal/robust 三种八亭设计。JSON `finite_buffers` 的八亭列均为 `policy:robust`；尤其 electronic-heavy 的7.8秒不能误读为 nominal 的358.5秒。建议表头 `Robust 8-booth wait (s)` 或在图注明确。附近文字174行虽明确 robust，独立读表仍有歧义。
3. **P2：摘要可就近交代11亭结论依赖原服务均值。** 摘要27行直接给11亭最小值；正文197行和结论205行正确指出15/10/3秒时11亭不再覆盖全部混合情景，14仅是必要下界。建议在摘要的11亭句中加入原服务均值12/6/2秒的条件；若版面允许，补一句更慢服务会失去该保证即可，不必在摘要复述所有 stress 数字。这是摘要覆盖改善；全文已经有限制，不属于隐藏或捏造结论。
4. **P2：信中的扩容效果应明确属于已测试占用情景。** 源稿215行 `Larger downstream occupancy removes this particular modeled penalty.` 是概括性表达，当前实测支持K=64相对K=16，而不是任意“更大”都足够。建议把K=64及对应8.3秒写明。这不改变数值或机制，只把对象定位到实际检查。
5. **P3：表格的输出和清空时间列明确是 heavy。** 源稿133–147行同时有 light/heavy wait，后面的 `Output` 与 `Clearance` 均来自 heavy 记录，图注未直接标明。建议写 `Heavy output` / `Heavy clearance`，避免读者认为这两列也包括light汇总。
6. **P3：几处英文可更直接。** 见下方原文→建议，不需改变模型或重算。

## 原文→建议（事实、数字与条件保持）

- 源稿28行：`Eight paired replications over 30 minutes show nominal heavy-traffic mean waiting falling from 66.1 s to 21.8 s in the unlimited-holding comparison.`
  → `Across eight paired 30-minute demand episodes with unlimited downstream holding, mean waiting under nominal heavy traffic falls from 66.1 s to 21.8 s.`
  理由：把30分钟明确为到达时段，避免被读成排队在30分钟时截断；全文实际保留排空过程。计量对象和结果不变。
- 源稿28行：`with 16 downstream slots per exit group, the longer expanded design waits 54.3 s on average.`
  → `With 16 downstream slots per exit group, vehicles in the longer expanded design wait 54.3 s on average.`
  理由：等候主体是车辆，设计不会“wait”。数值不变。
- 源稿44行：`Table ... defines transparent design scenarios; none of its numerical service, cost or behavior inputs is presented as a measured New Jersey value.`
  → `Table ... states the service, cost and behavior assumptions used in the design scenarios; these inputs are not measurements from New Jersey.`
  理由：删除自我评价transparent，直接说输入身份。事实不变。
- 源稿114行：`The robust design keeps that nominal threshold and improves the electronic-heavy threshold from 2,400 to 4,000 vehicles/hour, at an additional assumed capital cost of $60,000.`
  → `Relative to the nominal design, the robust design retains the 4,000-vehicle/hour nominal threshold and raises the electronic-heavy threshold from 2,400 to 4,000 vehicles/hour for an additional assumed capital cost of $60,000.`
  理由：明确比较对象；否则紧接 initial/nominal 两种比较可能使电子重载2,400的来源不清。所有数字与结论强度不变。
- 源稿128行：`It uses a 451 m fan-in with assumed full-build cost $3,965,256.`
  → `Its departure zone, including recovery and taper, is 451.44 m long, with an assumed full-build cost of $3,965,256.`
  理由：与表中451.44m及“length includes recovery and taper”保持清楚一致，避免fan-in被理解为仅taper。451.44来自同一JSON，不引入新结果。
- 源稿215行：`Larger downstream occupancy removes this particular modeled penalty.`
  → `At 64 slots per group, the expanded design's nominal heavy-traffic mean waiting falls to 8.3 seconds, removing this particular modeled penalty in the tested scenario.`
  理由：具体化已检查条件，并保留模型和情景范围。数据已在正文174行及JSON中。

这些是编辑建议，不是已实施的前后稿；本角色未修改主报告。主执行者采纳后应按有效版本核对摘要、表头、信及最终版面。

## 不应修改或错误质疑应拒绝的事项

- `3,306 veh/h` 的有限到达窗输出大于基线 `3,000 veh/h` 稳态混合容量，并非自动构成反例。源稿87行已正确区分指定付款构成的可持续到达阈值与有限时间内出流；队列可导致完成车辆构成不同。不要仅为使两个数字大小符合直觉而改数据。
- 源稿197行准确称14亭为必要数量，没有声称构造了14亭可行设计。不要把14写成经验证的新推荐。
- 源稿152行明确占用界仅必要、不充分；图表对finite-buffer与unlimited-holding分开，未宣称满足该界就不会排队。
- AV独立混合假设、只有AV–AV对使用短间隔，以及以均值确定性出流间隔的敏感性限制均明确；不应改成已模拟真实混合车队。
- 几何有序中心线与碰撞预防不等价，源稿95/102/201行保持准确区分。文章没有假造事故降低百分比。
- $60,000差额与结果一致：同一面积下robust的设备费用高于nominal。这里不是运营成本、投资收益或现实报价，现有范围应保留。
- 11亭最小数量来自各付款类必要条件，另有构造布局达到全部情景，不只是枚举失败推断不可能。此逻辑讲清了，需保留。
- 信长1–2页以及全部正文页数需由主执行者实际PDF核对；官方题面要求一页Summary、1–2页信、解答最多20页，合计最多23页且附录/参考不计。阅读源稿不能认证最终分页。

## 尚未解决的研究覆盖范围

官方题面明确关注事故预防与土地/道路成本，当前作品给出条件性几何和资本情景，却没有实地安全性能模型或土地成本情景。这是实际应用与建模深度的限制，文中已明确，不能通过英文润色“补成完成”。如预算不足，保留范围；如继续提升，优先把安全储存与空间可行性对应起来，而不是新增笼统宣传词。该观察不是对网络公式的否定，也不是奖项预测。

没有真实人类读者反馈；本次提供的是作者外同模型角色的全文阅读反馈。未复核所有参考网页原文，也没有重新执行作者的独立验证程序，因此不对其历史执行真实性作额外认证。
