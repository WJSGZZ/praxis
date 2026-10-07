# Sources and third-party notices

Praxis assembles an agent workflow and locally authored adapters; it does not claim to invent mathematical modeling or the upstream algorithms. LICENSE applies to the locally authored code and documentation. Dependencies retain their own licenses; no third-party library implementation, paper, dataset or binary is bundled here.

- [MathModelHub](https://github.com/Jaxon1216/MathModelHub), © 2026 MathModelHub, MIT. Workflow inspiration from [modeling lifecycle](https://github.com/Jaxon1216/MathModelHub/blob/8460b39b62480352de50d354bb86b11997b1cc6d/docs/guides/modeling-lifecycle.md) and [evidence and reproducibility](https://github.com/Jaxon1216/MathModelHub/blob/8460b39b62480352de50d354bb86b11997b1cc6d/docs/guides/evidence-and-reproducibility.md). Its full skill is not included or installed. Copyright and permission retained in third_party/licenses/MathModelHub-LICENSE.
- [SALib](https://github.com/SALib/SALib), MIT. Installed dependency for Sobol sampling and analysis; local wrapper adds input contracts and evaluation budgets. License retained in third_party/licenses/SALib-LICENSE.md. Follow upstream citation guidance when using the method in research.
- [pyMCDM](https://github.com/kotbaton/pymcdm), MIT. Installed dependency for TOPSIS; local wrapper adds explicit normalization, validation and weight scenarios. License retained in third_party/licenses/pymcdm-LICENSE. Follow upstream citation guidance in research.
- [pypdf](https://github.com/py-pdf/pypdf), BSD-3-Clause. Installed dependency for PDF text extraction and basic inspection. License retained in third_party/licenses/pypdf-LICENSE. It does not render pages or perform OCR.

Other installed scientific dependencies (NumPy, pandas, SciPy, matplotlib, scikit-learn, NetworkX, SymPy, statsmodels, openpyxl and their transitive dependencies) are not vendored; inspect each installed distribution's own license when redistributing dependencies. uv.lock records versions and archive hashes. third_party/dependencies.json distinguishes repository review commits from installed releases.

No guarantee of legal clearance or exclusive rights to the project name is made. This repository is not a fork of MathModelHub, is not endorsed by upstream authors, and does not include users' case files or conversations.


Workflow review additions:

- [Cookiecutter Data Science](https://github.com/drivendataorg/cookiecutter-data-science), © 2016 DrivenData, Inc., MIT. Inspiration for reproducible data flow and lightweight experiment records; license retained in third_party/licenses/cookiecutter-data-science-LICENSE. No generator, templates or implementation copied.
- [Math Modeling Contest Workflow](https://github.com/user0928/math-modeling-contest-workflow/tree/40155106a7051fccff9c0b2ab60cdff2588524b4) was read for comparison. No clear license was found at the reviewed commit; no text, code, skill or evaluation dataset is included. Praxis's definition examples and evidence-index implementation are independently authored. This link is acknowledgment of comparison, not a claim of reuse permission.

Review scope and adoption decisions are documented in references/upstream-review.md and third_party/workflow-review.json.
