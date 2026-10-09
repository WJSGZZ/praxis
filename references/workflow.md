# 可接续的任务协调

整题或多轮任务需要接续时，`scripts/workflow.py` 将现有 pipeline、经验索引、审阅和报告绑定起来。数学路线与改进价值由执行 Agent 判断；脚本给出当前一个行动并守住运行边界。它不生成模型、自动阅读全部资料、启动后台研究或认证获奖水平。单个标准计算继续走轻量工具入口。

## 开始与接续

先按 [automation.md](automation.md) 完成案例 intake、问题映射和代码审查。使用安装包的环境，路径替换为实际位置：

```bash
BUNDLE="$HOME/.agents/skills/praxis"
WORKSPACE="/absolute/path/to/your/project"
"$BUNDLE/.venv/bin/python" "$BUNDLE/scripts/workflow.py" \
  --workspace "$WORKSPACE" init --case cases/example \
  --goal "完成题目要求并核验主要结论" --query "预测 时间序列 可用信息" \
  --budget-seconds 3600 --max-attempts 4 --per-run-timeout 120
"$BUNDLE/.venv/bin/python" "$BUNDLE/scripts/workflow.py" \
  --workspace "$WORKSPACE" next --case cases/example
```

`init` 在第一次工作流运行前检索工作区 `planning/lessons.jsonl`，最多记录三条相关经验的 ID、哈希和索引身份；可用 `--lessons-path` 选择同一工作区内的其他索引。执行者按这些 ID 阅读原条目、判断适用条件，再选择路线。无命中保持可见，不默认为全部经验都有效。关键词检索不保证语义召回，也不等于已经应用经验。

状态只保存在已有 `planning/progress.md` 的 `PRAXIS WORKFLOW STATE BEGIN/END` JSON 块，保留其余正文。不要另建影子状态或手改计数、预算和有效指针；重复、损坏的块拒绝覆盖。任务定义、参数和假设仍在 `tasks.md`／代码／配置，实际变化仍使相关数值证据失效。该文件由一个协调者顺序维护，不支持多个写入者并发操作。

新会话先读取 `case.json`、任务定义及 progress，再调用 `next`。返回 `prepare/run/repair/coverage/review/improve/report/delivered/closeout` 中一个行动。最新运行失败或过期时回到修复，不悄悄使用旧成功；已接受版本的身份和失败记录保留。截止或不能再启动计算时进入收尾，不能通过再次 init 重置同一任务预算。

## 运行、审阅与交付

`next` 可给出 `expected_source_sha256`。只有实际审核过对应源码，才将该值传给 `run --reviewed-source-sha256 HASH`；复制哈希本身不是代码审查。运行调用现有 pipeline，每次消耗一次尝试，保留实际耗时、失败与收据。启动前至少留足模型和验证各一次超时的壁钟；预算是本地壁钟和尝试数，无法计量的模型、token 与费用保持未知。整个委托的共享额度仍由上游协调者管理。

`accept --review-path reviews/current.json` 需要对应最新有效且要求已链接的运行，审阅文件至少包含：

```json
{
  "verdict": "pass",
  "actor": "实际审阅者标识",
  "scope": "实际核验范围、方法与限制",
  "run_id": "实际运行目录名",
  "receipt_sha256": "对应receipt.json哈希",
  "quality_decision": {
    "decision": "continue",
    "reason": "当前稿有效，但存在值得投入的具体缺口",
    "next_action": "取得可区分候选方案的新证据"
  }
}
```

能够交付与值得继续分开：`continue` 返回具体改进行动；决定收尾时另存真实审阅，用 `decision: stop` 和明确理由再次接受。没有实际核验，不写 pass；工具只能核对声明及身份，不能替审阅者证明数学正确、独立性或真人参与。

`report --report-path paper/report.md` 或 PDF 绑定当前已接受运行及实际报告哈希。PDF 还需同路径加 `.page-review.json`，包含实际查看者 `actor`、`pdf_sha256` 和全部实际页码 `pages: [1,2,...]`；脚本检查页数与身份，不能代替逐页查看。报告变化需重新登记；模型／输入／验证条件变化则重算相关结果，不能仅更新报告哈希。仅当有效证据、审阅、报告仍匹配且明确 stop 时，`next` 返回 delivered。

到达预算仍可登记真实收尾审阅和报告，但不得启动新的计算。不能完成时保留有效部分、失败、缺口和恢复条件。跨任务稳定性、宿主持续执行与插件因果收益需另用实际任务检验，不能由状态机通过测试推断。
