# Repeated observations, defensible comparisons

[简体中文](README.md) · **English** · [Case gallery](../README.en.md)

A chain tracks weekly sales at each store. Joining those observations to store attributes is only the first step: four weeks from one store are not four independent stores. This locally constructed example follows one analysis through data declarations, join checks, clustered inference and a complete multiple-testing family.

![Four-week mean sales at twelve synthetic stores](assets/store-means.png)

*Figure 1. Variation between stores.* Each point is a four-week store mean, with six stores in each category. Grey dashes show category means. Horizontal offsets separate coincident values and have no quantitative meaning. All forty-eight original observations are retained. A [vector version](assets/store-means.pdf) is also available.

## Results and their scope

The regression includes campaign status and centered calendar week. One-way CRV1 covariance clusters by store, with a Student-t reference on eleven degrees of freedom:

| Conditional association | Estimate | 95% interval | Units |
|---|---:|---:|---|
| Campaign versus no campaign | 7.00 | 2.89–11.11 | Sales units |
| Change per calendar week | 2.00 | 1.41–2.59 | Sales units per week |

These are associations in constructed data, not evidence of a campaign's causal effect in real stores. Twelve clusters is a small sample; neither a finite-sample correction nor a t reference establishes reliable coverage. A synthetic specification, an arithmetic check and a real sampling design provide different kinds of evidence.

## What the workflow checks

The observation is a store-week; the declared independent unit is a store. A plan saved before construction fixes the two comparisons and the complete Holm family. Store metadata must have one row per store. The valid many-to-one join retains every observation; a deliberate duplicate metadata key is rejected by Pandas' actual cardinality validator.

Statsmodels supplies the OLS fit and clustered inference through `ols_report(covariance="cluster", groups=...)`. `adjust_pvalues` handles the full comparison family. Separate group-score calculations check the sandwich matrix, with an exact rational check of **94/27** for the campaign coefficient's variance. The constructed coefficients are **50, 7 and 2**. A direct two-test formula checks Holm adjustment, and the original CSV hashes must survive the analysis.

The checks cover this deterministic fixture, invalid join rejection and source preservation. They do not validate real store data, causal identification or repeated-sampling coverage. See the [statistical guidance](../../references/statistical-analysis.md) and [data-analysis contract](../../references/data-analysis.md) for method conditions.

## Reproduce

From the source checkout or the prepared core directory of an exported plugin, choose an output path that does not yet exist:

```bash
uv run --locked python -m examples.data_analysis_demo --output /path/to/new-store-run
```

The output contains the original synthetic CSVs, analysis plan, data declarations and audit, valid and rejected join evidence, regression intervals, the comparison family, independent arithmetic checks and `report.json`. No data are downloaded or uploaded.

To rebuild the figure, use the pinned Tectonic environment and another new directory:

```bash
uv run --locked python demos/data-analysis/build_figure.py --run /path/to/new-store-run --output /path/to/new-store-figure
```

The generator rechecks store means against the original CSVs and retains the real arrays, colors, markers and legend labels. It produces a vector PDF and a PNG. Inspect the actual figure before delivery; an export manifest is not a visual check. Selected publication identities are in [demo.json](demo.json).
