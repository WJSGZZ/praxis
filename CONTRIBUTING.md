# 参与开发 · Contributing

Praxis 的公开源码、开发时产生的工作材料和最终插件包有不同的文件边界。维护同一份方法和计算实现，使用导出器生成各宿主的安装包。

## 文件放在哪里

| 用途 | 位置 | Git 与安装包 |
|---|---|---|
| 核心技能、方法与工具 | `SKILL.md`、`skills/`、`references/`、`modeling/` | 提交源码，按导出规则进入插件 |
| 测试、CI、构建与演示源 | `tests/`、`.github/`、`scripts/`、`examples/`、`packaging/` | 提交源码；仅运行/使用需要的部分导出 |
| 经过整理的公开案例 | `demos/` | 提交选定资料和交付物；复现临时输出不提交 |
| 私人笔记、内部草稿 | `.local/` 或仓库外工作区 | 不提交、不导出 |
| 用户题目、数据与运行证据 | 用户自己的项目工作区 | 不放进插件源码或安装目录 |
| 构建产物与临时文件 | `dist/`、`build/`、`.session/` | 默认忽略；生成新包不覆盖现有内容 |

`dev/` 不是特殊保护目录。公开维护文件不应仅因为“属于开发”就被排除。`.gitignore` 只影响未跟踪文件；已有文件是否进入Git，使用 `git ls-files` 检查。不要提交密钥、私人材料或未经许可的外部内容。

## 验证与导出

```bash
uv sync --locked
uv run --locked python -m pytest
uv run --locked python -m scripts.build_plugin --host codex --output dist/codex/praxis
```

输出目录须尚不存在；其他宿主见[安装指南](references/installation.md)。发布包由 `scripts/build_plugin.py` 的资源选择规则生成，不是对仓库或工作区整体压缩。测试和CI留在源码仓库，用户工作数据留在用户工作区。修改打包规则时，检查必要资源、排除边界、相对链接、最终哈希和实际工具启动。

发布前按改动运行 `scripts.release_check` 和相关长检查，核对案例记录未漂移。提交推送、版本发布与商店上架分别处理，不由一次本地导出自动触发。

## Working on the source

Keep the public repository useful to contributors: tests, CI and build scripts belong in version control alongside the modeling code. Local notes and user cases belong outside the distributable source, while generated files go into ignored output directories.

Build each host package through `scripts.build_plugin`; do not zip an entire checkout. Export rules decide what ships, independently of Git's ignore rules. The commands above run checks and produce a Codex package in a fresh destination; the [English setup guide](references/installation.en.md) covers other agents. Verify the exported package, not just the source, and keep user problems and run evidence in their own workspace.

## 维护边界与变更

保持模块化单体：入口负责选择能力与协调；`modeling/` 负责有输入条件和保证范围的计算；pipeline负责执行快照与有效性；专业技能共用方法线；赛事适配负责当届交付；研究与评测保存证据。只在真实重复或职责冲突时拆模块，不为覆盖清单先拆目录。

信息按种类归属：推理与变更影响以 `references/methods.md` 为准；数值执行契约以 `references/automation.md` 为准；具体题目的定义在其任务记录，当前有效结果指向实际运行，贡献另记事件；公开展示从有效证据生成。区分官方硬规则、数学／执行不变量、工作策略和风格默认，不把默认配色或章节习惯升级为官方要求。变更规则时在所属源替代旧规则或明确条件，其他入口引用，不在多处追加互相冲突的完整版。

每次修改先定位共同根因与实际下游，再实施有限而完整的变更：核对调用方、返回状态、文档与生成索引、已接受结果和最终展示；测试包含独立答案和明确拒绝的坏输入。保存原审查意见，确认后才修；失败修复过程也保留，不能用最终测试通过抹掉它。跨模块且可能反复争论的决定在项目的唯一状态入口记录理由、替代方案与代价，普通润色不建额外决策文件。

研究用途与完成方式分别标记。少量旗舰维护当前结论、复现与展示；普通研究归档固定源码、环境和论文版本，不因插件升级全部重排。确认受影响或主动迁移时才创建修订关系，保留历史成品。`research/` 不默认进入安装包；同题参考论文、购买资料和私人交互不自动公开。干净检出和独立目录保证版本清楚，不能据此声称答案或模型预训练已隔离。

Treat a change as one complete correction: trace the cause through its callers, evidence and published claims, then test both a known valid case and the failure that exposed it. Keep the shared method and execution contracts authoritative. Frozen research archives retain their original environments; only affected or explicitly migrated artifacts need rebuilding. Repository cleanliness is version control evidence, not proof of an unseen or isolated evaluation.
