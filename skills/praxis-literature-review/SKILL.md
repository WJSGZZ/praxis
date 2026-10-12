---
name: praxis-literature-review
description: 检索、核读和综合研究证据，比较方法与已知结果、定位研究缺口，按真实范围完成叙述性／范围／系统综述。用于“找文献依据、别人怎么做、文献综述、研究定位、系统检索、这条引文支撑吗”。Literature review, evidence synthesis, research positioning, reproducible search and citation support. DOI元数据核对不代替读原文；不将普通背景查询升级成系统综述，论文语言交 praxis-scientific-writing。
license: MIT
---

# Praxis · 文献检索与综合

读 [literature-review.md](../../references/literature-review.md) 中符合当前用途的模式；共用 [writing.md](../../references/writing.md) 的来源核对及 [learning-loop.md](../../references/learning-loop.md) 的资料身份，不另建题库或证据平台。

## 调用契约

输入：需要支撑的论断／问题、对象与范围、已有文献、允许资料及实际可用检索入口。产出：可复查检索与阅读范围、来源—论断对应、不同研究的实质比较、可支持的结论与未取得全文；系统综述另交实际筛选及研究—报告关联。

## 专业处理

- 先判断是在找一个参数／公式、定位研究、综述证据还是执行系统综述。数据库、纳排标准、筛选和质量评价按用途选择，不设最低文献数。
- `search_literature` 找候选元数据与可能的开放全文；开放作者稿、机构库、出版社版本或宿主已有arXiv能力用于实际阅读。`find_open_access` 需要真实联系邮箱：只有已授权使用该邮箱才调用，不自行找邮箱、填假邮箱或为了普通检索要求用户发送个人信息。
- 核到实际使用的原句、式、表或方法位置，区分原论文、预印本和转述，保留版本、单位、对象、条件及纠错状态。`check_references` 只核DOI元数据，不证明引用支持论断。
- 按机制、方法和相同问题综合，而非逐篇摘要。不同样本／指标／信息条件不直接排胜负；多篇报告可能来自同一研究，不能重复计为独立证据。
- 拿不到全文、检索服务失败或同题资料未获放行时，标明实际范围，继续其他依据；不编造文献、补全实验内容或宣称没有先例。

## 交接与边界

数学式与关键数值的独立检查交 [praxis-verify](../praxis-verify/SKILL.md)，参数与路线选择交 [praxis-model](../praxis-model/SKILL.md)，文字组织交 [praxis-scientific-writing](../praxis-scientific-writing/SKILL.md)，整稿引文与交付交 [praxis-report](../praxis-report/SKILL.md)。本技能不执行付费检索、绕过资料许可或代替正式投稿审批；系统综述结论不由引用计数、来源声望或模板完成度认证。
