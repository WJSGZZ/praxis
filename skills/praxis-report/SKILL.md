---
name: praxis-report
description: 把有效结果写成读者能核查的论文或报告：摘要、章节顺序、命题与证明、模型验证写法、图表选择与图注、数字与引用一致、AI 使用披露、PDF 逐页检查与冻结。用于“写论文、改摘要、审我的稿子、检查 PDF”。不替代建模与验证，缺证据时返回上游。
license: MIT
---

# Praxis · 论文与交付

BUNDLE 指 `praxis` 技能目录。先读 [writing.md](../../references/writing.md)（含“论文骨架、验证与图表”）与 [visualization.md](../../references/visualization.md)。

## 做什么

- 竞赛论文从完整研究“收敛”而来：先按 [convergence.md](../../references/convergence.md) 的账本决定哪些进正文、附录、证据池，摘要先于正文成形，正文不讲工具与流程。
- 结构：摘要先写问题、方法、关键数字与条件；每个模型按“假设—推导—求解—检验—局限”；证明简短但完整；以真实结果支撑的结论收尾。
- 图表：每张图回答一个读者的问题，图注写明数据版本、单位与比较依据；不画不支持结论的图。
- 排版：论文用 LaTeX，不手拼 PDF。起点是 `templates/cumcm-paper.tex`（中文，ctex）与 `templates/mcm-paper.tex`（英文）；线图、柱状图、热图和流程图用 `scripts/texplot.py` 生成 pgfplots／TikZ 源码，字体与正文一致；用 XeLaTeX 或 tectonic 编译两遍，检查日志里没有缺字，再逐页渲染。
- 来源与披露：参考文献不可省略——外部的参数、公式、方法、数据都在使用处标号并在文末列全；有 DOI 的条目运行 `scripts/check_references.py` 核对（它只证明记录存在、题名年份相符，不证明该文献支持这个论断）。需付费的文献请使用者通过学校图书馆或知网取得全文再引用，没读过的不引。真实使用的来源在使用处引用；AI 使用按实际写，不用程序日志冒充完整对话。同一道题的评述、他人解答和优秀论文不进入该题的案例。
- 一致性：报告数字与有效运行逐项对应；缺证据返回 praxis-verify 或 praxis-compute，不在写作中补造依据或把条件结论写成事实。
- 比赛或团队交付：先读 [context-and-team.md](../../references/context-and-team.md) 确认实际规则、人数与格式；PDF 用 `scripts/check_pdf.py` 做预检（加 `--margins` 渲染每页，列出左右空白不一致或贴近页边的页面）、`scripts/freeze_pdf.py` 冻结，再逐页渲染查看公式、图表与版面。预检不等于合规认证。

## 交接

写作中发现的论证缺口，写回对应任务 ID。最终交付沿用用户已有文件与规范；公开、上传或提交需要明确授权。
