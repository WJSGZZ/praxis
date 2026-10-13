# Forecast vintages and the orders they support

[简体中文](README.md) · **English** · [Case gallery](../README.en.md)

A synthetic store places an order for two products at 08:00 each day, subject to a 40-unit capacity. Demand forecasts are revised later. Reconstructing an earlier order from the final snapshot would put future information into the decision. This complete exercise follows the available version through allocation, retrospective cost and unresolved cases.

[Full analysis](report.md) · [Daily results](results.json) · [Independent checks](checks.json) · [Fixed task and inputs](data/problem.md)

| Same 8 days and 16 targets | Forecast MAE (units) | Realized cost (declared units) | Shortage / overage (units) | Available at cutoff |
|---|---:|---:|---:|---|
| Declared available forecasts | 5.4375 | 248 | 46 / 34 | Yes, within the synthetic ledger |
| Fixed 20/20 baseline | 3.9375 | 157 | 24 / 39 | Yes |
| Invalid final snapshot | 0 | 36 | 9 / 0 | No |

The fixed baseline outperforms the available forecasts in this sample. The final snapshot's zero error shows how leakage can inflate a score; it does not justify adopting the forecast. Capacity also matters: even a decision made with hindsight leaves 9 units unmet.

## Retain the unresolved decisions

The original roster contains 20 queries over 10 days. Seventeen have a unique available version. The remaining three have an unknown release time, simultaneous conflicting releases, or no release before the cutoff. Two daily orders remain unresolved. The report keeps all those rows: January 9 needs a documented A release and an authoritative B revision; January 10 needs an A forecast available before the cutoff. An operational fallback has not been modeled.

Pandas supplies the backward matching operation through `asof_join`; an event after the decision can still be valid when announced beforehand. HiGHS allocates integer orders under the declared asymmetric loss. A separate validator scans UTC timestamps and enumerates all 861 feasible integer pairs per day. Changing values in 17 post-cutoff versions leaves the supported mappings and orders unchanged.

## Reproduce

From the source checkout or an exported plugin's core directory, choose an output path that does not yet exist:

```bash
uv run --locked python demos/data-vintages/run.py --output /path/to/new-vintage-case
```

The run retains read-only input copies, model and independent validator, source and dependency snapshots, daily JSON results, an English analysis, checks and an evidence index for all four tasks. Existing directories are refused. This page selects one finished example; reproduction writes to a new user directory.

The release timestamps and loss weights are declared synthetic settings. These checks establish information boundaries and arithmetic for the fixture. They do not validate real publication history, ledger completeness, forecast uncertainty, commercial gains or award quality. Method conditions are in [data analysis](../../references/data-analysis.md#按决策时刻选择数据版本); [demo.json](demo.json) records artifact identities.
