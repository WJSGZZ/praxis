# 参与记录与新手协作

本文件是贡献事件与工作模式的权威说明；论文披露仍服从当届规则。只在持续任务中启用，单次解释不建台账。使用者不必亲写代码才有贡献，助手也不能把自己的建模工作写成仅润色。

## 从题目开始记录

正常交互中由助手维护有意义的事件：题意修正、假设质疑、路线建议、方案取舍、审稿、发现错误、实际实现与独立核验。阶段性给用户看摘要供其纠正，不要求每轮填表。单纯“继续”只表示继续授权，不能计为方法创新；理解、采纳、实施与独立核验分别记录，不由一句确认互相推断。

事件写入用户工作区 `planning/contributions.jsonl`。用 `scripts/pipeline.py --workspace WORKSPACE contribution-add --case CASE --event EVENT.json` 添加，`contribution-summary --case CASE` 汇总；脚本从插件环境调用，文件写到用户工作区。EVENT 为本地 JSON：

```json
{"source":{"excerpt":"用户实际说过的话，或使用 message_ref 提供真实消息引用"},
 "proposer":"user", "matter":"具体质疑", "task":"Q2",
 "executor":"assistant", "kind":"challenge", "status":"proposed",
 "impact":"待核，尚未改变模型", "evidence":[],
 "mode":"collaboration", "origin":"contemporaneous"}
```

kind 可为 suggestion、challenge、decision、implementation、understanding、independent-verification、review、continuation；status 为 proposed、accepted、rejected、checked、implemented、unresolved。来源须有真实消息引用或原文摘录，时间未知不补造。事后补记用 retrospective。实际执行者未知可写 unknown，不能凭建议推断已经执行。已检查／实施必须给工作区内存在的证据文件，写入时记录哈希；文件存在及哈希只定位证据，不自动证明内容、主体或独立性。记录中不放隐私或无关聊天。

用户提出、AI实施是一条可追溯链；AI提出、用户采纳须分别记提案与决定。未采纳但触发了有效检查，也记录检查及不采纳理由。纠正旧记录追加 supersedes 指向旧事件id，不改写历史。摘要沿任务与实际影响组织，不算对话轮数或贡献比例；缺记录表示证据缺口，不能推断没有参与。

`planning/contributions.jsonl` 是新案例贡献事件的权威来源，任务沿用 tasks.md 的 ID，运行后的事件引用与处理状态放操作接续记录，不要求双写。旧表可作为注明位置的历史来源，由助手在最终说明中兼容汇总并按来源去重；当前 contribution-summary 只读事件日志，不自动解析旧表。迁移用 retrospective 保留来源，不凭迁移补造缺失事实。最终披露必须包含有证据、仅存在于事件日志的实际作用。

纯贡献追加不修改计算配置，也不改变数值运行有效性；需要时在 planning/progress.md 补一个事件引用；pipeline 整体哈希 tasks.md，纯补记不改 tasks.md，否则实际会触发过期保护。意见被采纳后若改变数据、代码、依赖、计算条件或 requirements，仍照 pipeline 的实际快照检查过期；贡献日志不能让失效结果恢复有效。

## 三种工作模式

| 模式 | 留存与说明 |
|---|---|
| autonomous | 自主演练与benchmark不虚构使用者；保留运行、失败、复现与真实人工介入 |
| collaboration | 日常协作自动记录有意义互动，阶段性汇总；不反复要求确认 |
| contest | 额外按赛事—赛项—届次的AI规则保留实际使用记录、判断和核实；规则未知不能声称已经满足 |

事件摘要和真实交互记录分开保存。宿主不能导出聊天时如实标缺失，不用摘要、脚本输出或虚构时间线代替完整记录。最终按真实记录说明人承担的判断和AI承担的建模、计算、写作；贡献摘要不代替规定披露与参赛责任。

## 把日常质疑转成检查

先解释输入、输出、关键假设、结果及失效条件。用户质疑后，明确它针对哪个假设，把它改写为可计算情景、边界检查或方案比较；交给 model/compute/verify，再按证据反馈是否采纳和对产物的影响。只问影响方向的判断，不为参与感制造确认。

示意：用户问“高峰期也能这样排队吗？”→ 检查原模型是否假设稳定到达率；若服务能力为每小时60人，比较到达率48人/小时与72人/小时，后者不满足稳态条件。返回上游采用分时到达模型或增加容量；不能继续用稳态均值预测高峰。这里是教学示意，不是某位真实用户的贡献。
