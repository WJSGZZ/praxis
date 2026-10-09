# 收费之后，瓶颈在哪里？

**2017 MCM B · Merge After Toll**　[English](README.en.md) · [完整英文报告](paper/paper.pdf) · [首稿](baseline/paper.pdf) · [计算结果](reference/accepted.json)

多开几个收费窗口，真的能让车更快离开吗？这份研究把支付方式、出口车道、汇合几何和有限排队空间放进同一个问题。它既构造了更好的条件性方案，也找到了扩建反而加重等待的情景。

这是一次 **AI 自主开发研究**，作为研究归档保存；国赛和美赛两个旗舰 Demo 继续各自维护。用途与执行方式分别记录，不把反复改进的研究当作首次盲测。

终稿版式已与原美赛旗舰统一，采用共享模板 `praxis-mcm-v1`；数学内容与数值不变，历史首稿保持原样。旧全文语义审阅及本次版式验收的关系见[版式修订记录](reviews/layout-revision.json)。

## 先看结果

以下均为明确假设下的模型结果，不是某座真实收费站的测量。

| 发现 | 条件与证据 |
|---|---|
| 不能直接相加所有窗口的服务能力 | 初始布局的总量上界为5,400辆/小时，但按名义支付构成只能持续接收3,000辆/小时；支付兼容流量网络给出准确的条件阈值。 |
| 八窗口名义方案达到4,000辆/小时 | 441种连续分组／支付聚类布局中选出4/3/1窗口配置；另与6,750种不限制聚类的矩阵比较。独立最大流与LP核验，限定当前参数。 |
| 支付比例会改变扩建必要性 | 三种支付情景、服务均值12/6/2秒下，至少需要11窗口才能覆盖3,600辆/小时；已构造满足条件的布局。服务改为15/10/3秒后，14仅是必要数量，未构造14窗口方案。 |
| 扩建可能让等待变长 | 名义重交通、每组16个收费后占用名额时，稳健八窗口平均等待21.9秒，11窗口方案54.3秒；64名额时后者降到8.3秒。更长的通道占用更多空间。 |
| 安全控制需要与几何一起说明 | 平行恢复区91.44米加230米名义渐变段；共同速度／行程下，入口计量与出口递推等价。只得到条件性同组间距依据，没有现场事故预测。 |

完整报告17页：一页摘要、完整解答、四幅图、一页管理部门建议函、参考文献和一页AI使用说明。按历史题面要求组织；不将此归档认证为现行比赛合规或工程安全设计。

## 怎样从首稿改到终稿

1. **找出兼容性缺口。** 总服务率只是上界，不能让现金车辆使用空闲电子窗口。用支付类型→出口组网络替换 pooled 推论，证明最小割条件，并构造可行流量。
2. **补回恢复区。** 阅读历史FHWA通用设计指南后，将收费后加速恢复与汇合渐变分开，重新计算面积、成本、行程与等待。
3. **用反例检查扩建。** 无限储车的比较支持扩建，有限占用却会反转偏好。Little定律给出必要占用下界，独立解析流量证书达到该界；下界不是充分储车设计。
4. **拒绝不合目标的优化。** 最小化最大资源利用率的路由候选，在部分情景改善、另一些恶化等待，因此保留原路由作比较，不宣称找到最小等待策略。
5. **修改整篇表达。** 独立角色全文审读后，补齐表格对象、服务条件和占用精度，统一摘要、正文与信；最终逐页渲染查看。

首稿9页，保存的是最初计算和较早几何假设下的完整稿。它在候选研究进行时形成，**不是冻结完整首稿后开展的对照试验**。原始失败、混合结果和版本范围见[研究记录](reviews/study.md)，不能把首稿与终稿之差当作插件A/B效果。

## 自己复现

在Praxis仓库根目录，用锁定环境执行。输出目录须不存在；命令不覆盖这里的冻结文件。

```bash
uv run --locked python research/merge-after-toll/reproduce.py --output .session/merge-replay
```

这一条会重算候选布局、运行验证器和作者外角色编写的审计，比较冻结数值并检查归档哈希。当前机器单次主计算约3秒；实际时间与环境见[manifest.json](manifest.json)。审计包含256组独立LP对照、手算队列、有限／无限占用对照、解析储车界与入口计量等价检查。

```bash
# 重放保留的路由候选，或最初基线
uv run --locked python research/merge-after-toll/reproduce.py --candidate --output .session/merge-candidate
uv run --locked python research/merge-after-toll/reproduce.py --baseline --output .session/merge-baseline

# 从冻结数值生成可编辑论文；正式PDF使用固定Tectonic入口
uv run --locked python research/merge-after-toll/paper/build_report.py \
  --results research/merge-after-toll/reference/accepted.json --output .session/merge-paper
```

## 文件与证据

- [paper/](paper/)：英文终稿PDF、LaTeX和数据驱动的生成器。
- [baseline/](baseline/)：最初完整稿及其计算源码；旧假设保持可见。
- [code/](code/)：当前模型、参数、有限队列、独立验证器及被拒路由候选。
- [reference/](reference/)：接受结果、候选、基线与相应检查；[独立审计](reference/independent-audit.json)。
- [reviews/](reviews/)：研究过程、英文审读及评估范围。奖项评估未校准，不从内部诊断分推奖项。
- [manifest.json](manifest.json)：有效源码指纹、环境、时间、来源、暴露范围、运行收据指纹和文件哈希。

## 来源与边界

题目来自[COMAP官方题面](https://www.contest.comap.com/undergraduate/contests/mcm/contests/2017/problems/2017_MCM_Problem_B.pdf)。归档不复制题面PDF或购买资料。通用参考是FHWA的[模型标定指导](https://ops.fhwa.dot.gov/trafficanalysistools/tat_vol3/sect5.htm)、[历史收费后区域指导](https://mutcd.fhwa.dot.gov/rpt/tcstoll/chapter642.htm)和[窗口布置指导](https://mutcd.fhwa.dot.gov/rpt/tcstoll/chapter224.htm)；历史指南不代表现行所有规范。

本轮没有读取同题解答或评委评论，预训练接触未知。另一Agent角色可见作者代码后进行审计，不是隔离盲评，也不是人工核验。没有使用者参与本题建模或核验的记录；开发者的产品要求与本题贡献分开。完整原始模型对话无法从摘要重建。

原创代码、说明与论文按仓库MIT许可提供；第三方题面与文献权利归原权利人。研究归档不随默认插件安装包分发，也不随每次技能调用加载。缺少实测服务、驾驶行为、几何储车映射、重车与制动数据，当前结论适合条件分析与方法检验。

正式排版（仓库根目录，输出目录须不存在）：

```bash
uv run --locked python -m scripts.paper_template research/merge-after-toll/paper/paper.tex --contest mcm --compile --output-directory outputs/toll-build-001
```

编译器与完整资源包固定于 `templates/typesetting-runtime.json`；逐页检查后再携带同次 `.build.json` 冻结，不把历史数学审阅冒充本次排版审阅。
