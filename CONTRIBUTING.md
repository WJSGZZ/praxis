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
