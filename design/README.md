# Praxis 展示语言

用于 GitHub 首页、公开案例、结果图与项目分享。定位为**研究出版**：清楚、克制、有证据，让读者先理解项目，再看到可以核查的成果。

本规范约束公开展示；比赛论文按当届格式要求另行处理。展示规则不进入每个建模任务的必经流程。

## 颜色有职责

| 用途 | 色值 | 使用方式 |
|---|---|---|
| 暖白底 | `#F6F4EF` | 所有展示图片的底色 |
| 深墨色 | `#202B31` | 标题、正文、关键数值 |
| 次级灰 | `#5D696E` | 条件、刻度、来源与说明；不把小字压成浅灰 |
| 青绿色 | `#176B61` | 品牌、主序列、入口与选中点 |
| 陶土色 | `#A16B43` | 第二个比较序列；不表示失败或低质量 |
| 分隔线 | `#D3D8D3` | 细线、坐标轴与必要边界 |

主强调每幅图只用一种；第二强调仅在数据比较时启用。序列还必须用标题、位置、标注区分，不能只靠颜色。较大的空白用于分组和阅读，不填装饰纹理。

## 字体有层级

- **标题用衬线体**：中文常规宋体、西文 DejaVu Serif，形成出版物的阅读气质。标题不超过三行，句子直接表达用途或结果。
- **说明与数字用无衬线体**：中文清晰的 CJK 无衬线体、西文 DejaVu Sans。标签不和标题争夺注意力，数据使用易辨认的数字。
- **项目名保持文字标识**：`P R A X I S` 只用于页眉；正文写 `Praxis`。当前没有注册标识或专属图标的含义。
- 不混入第三套装饰字体，不使用斜体中文，不用超细字重。图中真实论文页保留原字体。

字号、色值、画布和图表线宽由 [tokens.json](tokens.json) 维护。[style.py](style.py) 提供共同页眉、文字角色、字体选择、画布与边界检查。

## 同一版式，不同职责

统一使用 **16:9、1920 × 1080** 画布，左右各留约 6.5% 空间；页眉为项目名与案例编号，细线分区。

| 类型 | 阅读顺序 | 保留的内容 |
|---|---|---|
| 首页封面 | 主张 → 工作过程 → 成果 → 入口 | 左侧一句用途与四步过程，右侧真实报告页，底部最多三项证据数字 |
| 案例结果图 | 问题 → 条件 → 数据 → 依据 | 同一网格排列比较图；指标和适用条件分开，脚注明确预算、口径及基线 |
| 报告预览 | 原页 → 页码／内容说明 → 完整报告 | 保留真实页面和比例，链接完整 PDF；拼接或截取不得改变原文与数值 |

过程用编号、间距和细线组织，避免每一句话都放进圆角卡片。图片自身只讲一个中心信息。README 负责解释、跳转和下载，不把整篇报告缩成小字堆在首页。

## 图表规则

轴名、单位、百分比精度和基线必须明确。不同范围的图并排展示时保留各自刻度，不用相同框宽暗示相同范围。代表点标记与大数字必须对应同一条记录。

统计图从记录数据生成，不手绘曲线、不为视觉效果平滑结果。低透明度填充只辅助阅读，不编码额外置信度。图表底部保留会改变理解的条件；脚注过长时缩短文案或转交案例页，不继续缩小字号。

## 文案规则

先说“能做什么”，再给一项真实成果和可核查入口。数字来自有效结果；检查数不改称独立算法数，演示不改称获奖或官方答案。标题可以有表达力，但不提升结论等级。中英文表达可以分别排版，数字、含义和证据保持一致。

## 生成与验收

从仓库根目录运行：

```bash
uv run --locked python demos/cumcm-1998-a/assets/build_overview.py
uv run --locked python demos/cumcm-1998-a/assets/build_preview.py
```

默认使用 macOS 已安装的宋体与 CJK 无衬线字体，不分发字体文件。其他平台设置 `PRAXIS_CJK_SERIF`、`PRAXIS_CJK_SANS` 为有权使用的本地字体路径；宋体 TTC 的常规字面默认索引为 6，可用 `PRAXIS_CJK_SERIF_INDEX` 配置。生成脚本使用现有 Matplotlib 及其字体工具，不新增运行依赖。

每次交付检查：图片原尺寸、README 约 900px 显示宽度和手机宽度；标题可读，数字与条件对应，无截断／重叠／缺字；再核对图片路径、点击入口与完整材料。自动文字边界检查只证明未越出画布，仍需视觉查看。手机上可以把完整数据图点开查看，不能假称所有脚注在缩略图中都可读。

新增案例沿用 tokens 与公共函数，替换案例编号、文案、原页与有效数据。修改公共样式后重生成相关图片；不要在每个脚本里另设一套颜色和字体。

---

## English overview

Praxis uses an editorial research style: warm paper, dark ink, a restrained teal accent, serif headings, and clear sans-serif labels. Terracotta is reserved for a second data series. Covers explain the workflow; charts explain results and conditions; report previews preserve the original pages.

All showcase assets share a 16:9 canvas, consistent gutters, a project/case header, and the tokens in this directory. Use the shared Python renderer, keep quantitative content tied to recorded data, and review both full-size and README-scale exports. CJK fonts are locally installed, not distributed. Competition report formatting remains separate from the public showcase style.
