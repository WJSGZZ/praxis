# 工作流对照与本次取舍

核查日期：2026-10-07。固定提交与实际阅读文件见 third_party/workflow-review.json；原有数学依赖的来源记录见 third_party/dependencies.json。

| 项目 | 核验范围与许可 | 本次决定 |
|---|---|---|
| [Math Modeling Contest Workflow](https://github.com/user0928/math-modeling-contest-workflow/tree/40155106a7051fccff9c0b2ab60cdff2588524b4) | README、定义审查、独立核验与跨问整合说明；审查树未见 LICENSE，GitHub 许可字段为空，复用授权未明确 | 仅对照一般思想，不复制代码、文字、Skill 或测试集。Praxis 自行编写定义反例与结论边界指导，不采用其固定审查轮次或强制用户重新开启流程 |
| [Cookiecutter Data Science](https://github.com/drivendataorg/cookiecutter-data-science/tree/17c991b0b03668f6e36503a4416202900196f501) | LICENSE 与工作意见说明；MIT | 借鉴数据到结果的依赖追溯、轻量实验记录。已有原始数据保护与环境锁定保留，补上任务到证据的索引；不安装模板生成器，不换环境，不接外部云服务 |

## Praxis 的具体改进

1. references/definition-review.md 提供会区分不同解释的小例子，审查定义、信息时点与结论强度；跨任务复用时保留上游版本和限制。
2. pipeline evidence 将已记录数值任务连接到最新有效运行中的结果字段和独立检查，暴露漏字段、漏检查、重复检查名与过期证据。清单进入运行快照，修改后必须重跑。
3. 针对上述失败模式加入回归测试，验证已知解析结果，并刻意构造漏答、失败与修改清单的情形。测试不证明助手在任意真实题上都能理解完整要求。

## 继续改进的依据

实际任务出现失败时，在工作项目记录触发条件、实际影响与修复理由；只将去除私人内容、可公开且可复现的小例子转成回归测试。修改相应指导或工具，验证修复与直接依赖，再记录仍未覆盖的情况。没有观察到的问题不自动升级为通用强制步骤。

当前证据索引只覆盖用户／助手记录的清单；它不自动抽取任务，不判断检查是否科学，不验证单位一致性，也没有跨案例依赖图或文稿数字自动同步功能。


## 统一融合后的职责分配

Praxis 的目的、任务记录和推进逻辑先确定；上游经验按职责吸收，不按仓库划分阶段。

| 经验来源 | 在统一主线中的职责 | 合并／保留方式 | 触发条件与检查 |
|---|---|---|---|
| MathModelHub 的生命周期与追溯思路 | 把任务从问题推进到证据与交付 | 归入 methods.md 的单一主线，tasks.md 为同一任务记录 | 请求完整建模才推进全链；数字可回到有效运行 |
| 公开工作流的定义与独立核验思路（仅比较，无文本复用） | 明确原题含义、匹配结论强度 | 定义例子作为主线的条件参考；验证与跨任务规则并入主线，移除重复流程 | 真实歧义用区分例子；独立证据按结论选取 |
| Cookiecutter Data Science 的数据流与实验记录思路 | 支持可靠计算与依赖追溯 | 使用现有案例、快照与 JSON 记录，不叠加目录体系或生成器 | 原始输入保护、过期证据与依赖版本检查 |
| SALib／pyMCDM 数学工具 | 回答特定的不确定性／方案比较问题 | 留作条件调用的实现，不作为全题必经阶段 | 分布／偏好条件明确；已有解析与已知排序测试 |
| Praxis 的 evidence 索引 | 连接数值交付物和实际检查 | 使用同一任务 ID，不替代主记录与科学审核 | 数值交付才调用；漏字段、漏检查、失败与过期回归 |

统一方法见 methods.md。新增项目先说明缺口、职责、契约、替代关系、验收和许可；无实际收益不引入。实践中出现错误，修正对应职责的规则或工具，而非再添加平行流程。


## 数学方法与思想对照（2026-10-07）

星数是核查时的 GitHub API 快照，仅用于发现，不代表方法正确或适合当前题目。固定提交、许可与审查范围见 third_party/mathematical-review.json。

| 项目 | 星数快照 | 明确缺口与主线职责 | 本次取舍 |
|---|---:|---|---|
| [sympy/sympy](https://github.com/sympy/sympy/tree/319ea7a6186edf88bc23d502917242b10314ae51) | 14,993 | 形成路线前检查量纲与等价参数；独立符号核验 | Reuse already-installed dependency for dimensional and exact symbolic examples; representation and parameter-identifiability guidance |
| [scipy/scipy](https://github.com/scipy/scipy/tree/0aa66630fc0717788fd39b25bdaecfcc8d7002cd) | 15,086 | 取得结果并用独立界判断最优性 | Reuse already-installed dependency for LP solve contrasted with independent exact certificate |
| [cvxpy/cvxpy](https://github.com/cvxpy/cvxpy/tree/5c569b461c62aa7d93e06fd3994213ae3fc4af5c) | 6,356 | 依据连续／凸性结构选择优化路线 | Adopt structure-first reasoning and conditional DCP guidance; not installed or executed |
| [pymc-devs/pymc](https://github.com/pymc-devs/pymc/tree/19a783ff4564fcda6340477415b8efdd0f245871) | 9,795 | 需要概率区间时表达生成过程与检查分布假设 | Adopt conditional generative and prior/posterior predictive checking guidance; not installed or executed |
| [py-why/dowhy](https://github.com/py-why/dowhy/tree/b06369ed4a01a54c9d6422a24f103626fbcaec19) | 8,338 | 干预问题先核验因果假设与识别条件 | Adopt conditional causal-assumption and identification guidance; not installed or executed |
| [google/or-tools](https://github.com/google/or-tools/tree/100f66e6242ab8bf8d32feb8f3bf086db66ae2b5) | 14,156 | 离散任务按整数／组合结构选工具 | Candidate for discrete scheduling/routing beyond existing tools; not installed or executed |

没有从这些仓库复制算法代码、教程文字或数据。已安装的 SymPy／SciPy 支持自行编写的小例子，其余仅吸收有来源的一般方法与条件指导，不声明已验证这些库本身。主线与任务记录保持不变，具体条件见 mathematical-reasoning.md。
