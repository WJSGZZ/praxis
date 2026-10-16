# 参与记录与新手协作

持续任务沿既有工作区记录贡献事件，单次解释直接交流。人和助手的真实职责、AI披露及参与边界在 report 阶段按 [integrity.md](integrity.md#ai-披露与贡献) 核对；本文件说明接口、工作模式和教学协作。

## 从题目开始记录

助手在正常交互中记录有意义的题意修正、假设质疑、路线建议、取舍、审稿、错误、实现与核验。阶段性按关键任务汇总，请使用者纠正事实。每件事分别标提案、采纳、执行、理解、审阅与独立核验及其证据。

权威事件文件是用户工作区 `planning/contributions.jsonl`，任务沿 `tasks.md` 的 ID。通过插件环境调用：

```bash
python "$BUNDLE/scripts/pipeline.py" --workspace "$WORKSPACE" contribution-add --case "$CASE" --event EVENT.json
python "$BUNDLE/scripts/pipeline.py" --workspace "$WORKSPACE" contribution-summary --case "$CASE"
```

`EVENT.json` 例：

```json
{"source":{"excerpt":"用户实际说过的话，或用 message_ref 提供真实消息引用"},
 "proposer":"user", "matter":"具体质疑", "task":"Q2",
 "executor":"assistant", "kind":"challenge", "status":"proposed",
 "impact":"待核，尚未改变模型", "evidence":[],
 "mode":"collaboration", "origin":"contemporaneous"}
```

`kind` 为 suggestion、challenge、decision、implementation、understanding、independent-verification、review 或 continuation；`status` 为 proposed、accepted、rejected、checked、implemented 或 unresolved。来源有真实消息引用／摘录；事后补记用 retrospective，时间和执行者未知保留 unknown。checked／implemented 给出工作区内存在的证据文件，写入时绑定哈希；主体、独立方法和实际影响再由审阅者核内容。

用户提议与AI实施沿同一任务追踪；AI提议与用户采纳分别记提案、决定。未采纳但触发有效检查时保存检查及理由。纠正用 `supersedes` 追加引用旧事件，保留历史。摘要按实际影响组织，缺失单列证据缺口。旧表注明位置作为历史来源，最终按来源去重；`contribution-summary` 只读事件日志，最终披露还核仅存在于事件日志的实际作用。

纯贡献追加保持数值配置不变，运行后的事件引用与处理状态放 `planning/progress.md`。`tasks.md` 属计算快照；纯补记沿事件文件，意见实际改变数据、代码、依赖、条件或 requirements 时按 pipeline 重新检查有效性。有效结果由真实快照决定。

## 三种工作模式

| 模式 | 留存与说明 |
|---|---|
| autonomous | 保存自主演练／benchmark的运行、失败、复现和实际人工介入 |
| collaboration | 日常记录有意义互动并阶段性汇总 |
| contest | 额外按赛事—赛项—届次核AI使用记录、人的判断与规定检查 |

贡献事件与真实交互分别保留；交付阶段沿 [feedback.md](feedback.md) 接真实聊天、用途和明确缺口，再按 integrity 完成披露。

## 把日常质疑转成检查

先解释输入、输出、关键假设、结果和失效条件。将用户担忧定位到假设、数据或动作，转成可计算情景、边界或比较，交 model／compute／verify；按证据反馈采纳、拒绝及产物影响。仅提问影响真实取舍的事项。

教学示意：问“高峰也能这样排队吗？”时，核稳定到达前提。服务60人／小时，对照48与72人／小时，后者越过稳态条件；据此返回上游考虑分时到达或容量，按新模型回答高峰。示意与真实贡献记录分别标身份。

## 助手执笔与选手共同研究

重要决定前先听选手判断及理由，再给适量解释与备选；助手把问题转成检查、返回证据并整合运行和写作。用户承担实际判断的机会贯穿研究与修订，具体分工以发生的工作为准。

| 参与机会 | 有意义的行动与后续 |
|---|---|
| 定义问题 | 说明目标、约束或数据含义，将歧义修正记入任务 |
| 假设与路线 | 提出担忧、反例或备选理由，比较适用条件与代价 |
| 结果核验 | 实际做量级／单位检查、手算特例或证据审阅，记录方法与结果 |
| 结论与修订 | 指出失效情形与遗漏，检查主张及重算范围 |

阶段性核谁做了什么、依据、影响及未完成事项。缺口写具体任务，如“核心假设待人的判断”“关键结果待必要人工核验”；理解训练记 understanding，实际审阅记 review，独立核验给独立方法与证据。围绕最重要缺口继续讨论、反例、验证与取舍。后来实际完成的工作按发生阶段追加。

在约定时间内，选手暂时无法参与时先完成其余工作，保存待办与当前成果，正式协作的未完成项保持可见。答辩需要时用 [defense-coaching.md](defense-coaching.md) 教学和验收，普通问答按当前问题进行。
