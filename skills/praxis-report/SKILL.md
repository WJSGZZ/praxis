---
name: praxis-report
description: 把有效结果写成读者能核查的论文或报告：摘要、章节顺序、命题与证明、模型验证写法、图表选择与图注、数字与引用一致、AI 使用披露、PDF 逐页检查与冻结。用于“写论文、改摘要、中文润色、英文科研表达、审我的稿子、检查 PDF”。不替代建模与验证，缺证据时返回上游。
license: MIT
---

# Praxis · 论文与交付

BUNDLE 指 `praxis` 技能目录。按当前请求读 [writing.md](../../references/writing.md) 的对应小节；纯语言修改只读“语言专项”，涉及图表才读 [visualization.md](../../references/visualization.md)。

## 调用契约

输入：指定原稿或有效结果、事实表与交付要求。产出：自然清楚且事实一致的修订或完整报告。依赖与边界：语言仅用写作参考，图表与PDF按需；不新增科学主张。

## 做什么

- 完整报告按 [convergence.md](../../references/convergence.md) 从有效证据决定正文、附录与证据池的取舍；局部改稿直接处理当前缺口，不重做研究流程。
- 结构：摘要先写问题、方法、关键数字与条件；每个模型按“假设—推导—求解—检验—局限”；证明简短但完整；以真实结果支撑的结论收尾。
- 图表：按 visualization.md 先比较不画、用表与其他图形的表达价值；不设最低图数，不把图框当模板必填项。每张保留的图回答一个读者的问题，图注写明数据版本、单位与比较依据；不画不支持结论的图。由实际有效数据通过成熟科学绘图库生成，核对坐标变换、插值、采样／网格与统计区间含义；数值核验和最终尺寸视觉验收都通过后才进入正文。
- 排版：模板组件按需选用：不强制子标题、目录、符号表、算法框或通用章节清单；只锁定实际使用组件的样式。必需提交结构以当届规则为准，不能为了模板凑空章节。沿用用户当前源文件与宿主可用编译器。新国赛论文复用 `templates/cumcm-paper.tex`／`templates/cumcm-style.tex`（ctex），交付前用同一检查器加 `--contest cumcm`；新美赛论文必须复用 `templates/mcm-paper.tex` 或 `scripts.paper_template.preamble/summary_header`，版式权威源为 `templates/mcm-style.tex`。新题只换内容／队号／题号，不自行另写字体、页边距、行距和页眉；正式交付前运行 `python -m scripts.paper_template main.tex`。有明确赛事差异或用户指定才显式调整版式版本；图表工具见 visualization.md。编译成功后仍须导出 PDF 逐页查看，不能以编译日志代替视觉审查。
- 来源与披露：参考文献不可省略——外部的参数、公式、方法、数据都在使用处标号并在文末列全；有 DOI 的条目运行 `scripts/check_references.py` 核对（它只证明记录存在、题名年份相符，不证明该文献支持这个论断）。需付费的文献请使用者通过学校图书馆或知网取得全文再引用，没读过的不引。真实使用的来源在使用处引用；AI 使用按实际写，不用程序日志冒充完整对话。同题资料按 [learning-loop.md](../../references/learning-loop.md) 的学习／封存／正式赛事用途处理，保持真实暴露记录，不将对照后的开发案例称盲测。
- 一致性：报告数字与有效运行逐项对应；缺证据返回 praxis-verify 或 praxis-compute，不在写作中补造依据或把条件结论写成事实。
- 比赛或团队交付：按 [context-and-team.md](../../references/context-and-team.md) 接续实际赛事／届次和规范，不能用模板或通用摘要替代当届官方文件。规则检查见 [contest-playbook.md](../../references/contest-playbook.md)；PDF 预检、检查数核对与冻结的执行契约见 [automation.md](../../references/automation.md)。最终 PDF 逐页核查后再冻结；正式编译走 `scripts.paper_template <源文件> --contest mcm|cumcm --compile --output-directory <新目录>`，固定编译器与资源包；最终 PDF 通过 `scripts.freeze_pdf <PDF> <新快照> --tex <源文件> --contest mcm|cumcm --build-receipt <同次编译的.build.json>` 冻结；模板失败先回修，不能省略参数改用通用快照绕过。冻结前确认本次编译产物与源文件对应，并逐页验收。预检不等于合规认证。

## 交接

写作中发现的论证缺口，写回对应任务 ID。最终交付沿用用户已有文件与规范；公开、上传或提交需要明确授权。
