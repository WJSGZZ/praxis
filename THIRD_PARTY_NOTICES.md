# Sources and third-party notices

Praxis assembles an agent workflow and locally authored adapters; it does not claim to invent mathematical modeling or the upstream algorithms. LICENSE applies to the locally authored code and documentation. Dependencies retain their own licenses; no third-party library implementation, paper, dataset or binary is bundled here.

- [MathModelHub](https://github.com/Jaxon1216/MathModelHub), © 2026 MathModelHub, MIT. Workflow inspiration from [modeling lifecycle](https://github.com/Jaxon1216/MathModelHub/blob/8460b39b62480352de50d354bb86b11997b1cc6d/docs/guides/modeling-lifecycle.md) and [evidence and reproducibility](https://github.com/Jaxon1216/MathModelHub/blob/8460b39b62480352de50d354bb86b11997b1cc6d/docs/guides/evidence-and-reproducibility.md). Its full skill is not included or installed. Copyright and permission retained in third_party/licenses/MathModelHub-LICENSE.
- [SALib](https://github.com/SALib/SALib), MIT. Installed dependency for Sobol sampling and analysis; local wrapper adds input contracts and evaluation budgets. License retained in third_party/licenses/SALib-LICENSE.md. Follow upstream citation guidance when using the method in research.
- [pyMCDM](https://github.com/kotbaton/pymcdm), MIT. Installed dependency for TOPSIS; local wrapper adds explicit normalization, validation and weight scenarios. License retained in third_party/licenses/pymcdm-LICENSE. Follow upstream citation guidance in research.
- [pypdf](https://github.com/py-pdf/pypdf), BSD-3-Clause. Installed dependency for PDF text extraction and basic inspection. License retained in third_party/licenses/pypdf-LICENSE. It does not render pages or perform OCR.

Other installed scientific dependencies (NumPy, pandas, SciPy, matplotlib, scikit-learn, NetworkX, SymPy, statsmodels, openpyxl and their transitive dependencies) are not vendored; inspect each installed distribution's own license when redistributing dependencies. uv.lock records versions and archive hashes. third_party/dependencies.json distinguishes repository review commits from installed releases.

No guarantee of legal clearance or exclusive rights to the project name is made. This repository is not a fork of MathModelHub, is not endorsed by upstream authors, and does not include private user workspaces or conversation exports. The explicitly curated historical demonstration in demos/cumcm-1998-a is included for public development use.


Workflow review additions:

- [Cookiecutter Data Science](https://github.com/drivendataorg/cookiecutter-data-science), © 2016 DrivenData, Inc., MIT. Inspiration for reproducible data flow and lightweight experiment records; license retained in third_party/licenses/cookiecutter-data-science-LICENSE. No generator, templates or implementation copied.
- [Math Modeling Contest Workflow](https://github.com/user0928/math-modeling-contest-workflow/tree/40155106a7051fccff9c0b2ab60cdff2588524b4) was read for comparison. No clear license was found at the reviewed commit; no text, code, skill or evaluation dataset is included. Praxis's definition examples and evidence-index implementation are independently authored. This link is acknowledgment of comparison, not a claim of reuse permission.


Mathematical reasoning review:

- Existing installed [SymPy](https://github.com/sympy/sympy) and [SciPy](https://github.com/scipy/scipy) are used in locally authored synthetic structural checks; installed license texts retained as third_party/licenses/sympy-LICENSE and scipy-LICENSE. No library implementation is vendored.
- [CVXPY](https://github.com/cvxpy/cvxpy), [PyMC](https://github.com/pymc-devs/pymc), [DoWhy](https://github.com/py-why/dowhy), and [OR-Tools](https://github.com/google/or-tools) were reviewed as concept/tool references. No implementation, tutorial text, figures or datasets are copied, and these libraries are not installed or tested by this review. Their licenses do not become MIT through this repository's LICENSE.
- Repository license texts were verified at fixed commits before these references were made. Original guidance and examples are in references/mathematical-reasoning.md and examples/structural_reasoning_demo.py.


Capability references:

Matplotlib, Seaborn, scikit-learn, and Manubot are cited as concept/tool references for data processing, graphics and citation traceability. No source code, tutorial text or figures are included through this review; no new dependency is installed. Matplotlib and scikit-learn remain existing dependencies with their own distribution licenses.

Writing guidance briefly adapts general reader-oriented principles from Brett Mensh and Konrad Kording, “Ten simple rules for structuring papers” (2017), DOI 10.1371/journal.pcbi.1005619, with attribution and a link in references/writing.md. The publisher states Creative Commons Attribution; no full article text or figures are reproduced. Praxis's original task handoffs and guidance are locally authored.


Public demonstration:

- CUMCM 1998 A parameter tables are transcribed from page 11 of the organizer's [official historical problem collection](https://www.mcm.edu.cn/upload_cn/node/1/SkAh1A7Q6f2dd01e58aa621f920e79f45cd5d255.pdf). Numerical problem parameters retain this attribution; the official PDF and others' solutions are not redistributed.
- The demo's solution, code, report text, figures, and page previews are project-created materials. No official showcase paper text or images are copied. PDF font programs embedded for displaying the report are not standalone font distributions and are not relicensed by the repository MIT license.
- Original modeling code calls NumPy, SciPy/HiGHS, and Matplotlib; these dependencies are not vendored. The support archive includes original code and generated artifacts, not third-party library implementations.


Proof-artifact organization reference:

- [openai/math](https://github.com/openai/math/tree/fd4aeeb2ee4fc729c18d98444fed42fd0529eeeb), Apache-2.0, reviewed at `fd4aeeb2ee4fc729c18d98444fed42fd0529eeeb`. The repository README, Lean README and Comparator challenge instructions informed the original scope-checking guidance in references/methods.md: link a claim to its exact statement, assumptions, proof artifact and verification scope, and distinguish supporting results from main theorems. No manuscripts, reasoning summaries, Lean code, data or proof tools are copied or installed. The repository license does not make unverified mathematical claims correct; Praxis did not compile these proofs.
