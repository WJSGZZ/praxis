# Sources and third-party notices

ModelCraft assembles an agent workflow and locally authored adapters; it does not claim to invent mathematical modeling or the upstream algorithms. LICENSE applies to the locally authored code and documentation. Dependencies retain their own licenses; no third-party library implementation, paper, dataset or binary is bundled here.

- [MathModelHub](https://github.com/Jaxon1216/MathModelHub), © 2026 MathModelHub, MIT. Workflow inspiration from [modeling lifecycle](https://github.com/Jaxon1216/MathModelHub/blob/8460b39b62480352de50d354bb86b11997b1cc6d/docs/guides/modeling-lifecycle.md) and [evidence and reproducibility](https://github.com/Jaxon1216/MathModelHub/blob/8460b39b62480352de50d354bb86b11997b1cc6d/docs/guides/evidence-and-reproducibility.md). Its full skill is not included or installed. Copyright and permission retained in third_party/licenses/MathModelHub-LICENSE.
- [SALib](https://github.com/SALib/SALib), MIT. Installed dependency for Sobol sampling and analysis; local wrapper adds input contracts and evaluation budgets. License retained in third_party/licenses/SALib-LICENSE.md. Follow upstream citation guidance when using the method in research.
- [pyMCDM](https://github.com/kotbaton/pymcdm), MIT. Installed dependency for TOPSIS; local wrapper adds explicit normalization, validation and weight scenarios. License retained in third_party/licenses/pymcdm-LICENSE. Follow upstream citation guidance in research.
- [pypdf](https://github.com/py-pdf/pypdf), BSD-3-Clause. Installed dependency for PDF text extraction and basic inspection. License retained in third_party/licenses/pypdf-LICENSE. It does not render pages or perform OCR.

Other installed scientific dependencies (NumPy, pandas, SciPy, matplotlib, scikit-learn, NetworkX, SymPy, statsmodels, openpyxl and their transitive dependencies) are not vendored; inspect each installed distribution's own license when redistributing dependencies. uv.lock records versions and archive hashes. third_party/dependencies.json distinguishes repository review commits from installed releases.

No guarantee of legal clearance or exclusive rights to the project name is made. This repository is not a fork of MathModelHub, is not endorsed by upstream authors, and does not include users' case files or conversations.
