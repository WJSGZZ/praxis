# Information-Time Replenishment Case

This synthetic exercise matches each fixed query to the latest uniquely declared forecast available strictly before its 08:00 UTC cutoff. A day receives an automated order only when both SKU forecasts are supported. Orders minimize the stated point-forecast loss under a 40-unit capacity using integer quantities.

The as-of mapping covered 17 of 20 queries. 8 of 10 dates were actionable; unresolved dates remain in the daily table with the evidence needed for recovery.

## Common eight-day evaluation

All methods are evaluated on the same first eight dates and 16 SKU targets. Forecast MAE uses the submitted forecasts; realized shortage, overage, and cost use observed demand and the method's orders. Costs are declared units, not money.

| Method | MAE | Absolute error sum | Realized cost | Shortage units | Overage units | Eligible at cutoff |
|---|---:|---:|---:|---:|---:|:---:|
| declared_asof | 5.4375 | 87.000 | 248.000 | 46.000 | 34.000 | yes |
| baseline_20_20 | 3.9375 | 63.000 | 157.000 | 24.000 | 39.000 | yes |
| invalid_final_snapshot | 0.0000 | 0.000 | 36.000 | 9.000 | 0.000 | no |

The final-snapshot row intentionally uses information released after the decision cutoff. It is an invalid retrospective comparison, not an alternative operational policy. None of the realized costs establishes the best future policy or real-world savings.

## Daily decisions and unresolved evidence

| Date | A forecast | B forecast | Orders A / B | State |
|---|---:|---:|---|---|
| 2026-01-01 | 15 | 20 | 15 / 20 | A: matched; B: matched |
| 2026-01-02 | 18 | 18 | 18 / 18 | A: matched; B: matched |
| 2026-01-03 | 26 | 22 | 26 / 14 | A: matched; B: matched |
| 2026-01-04 | 20 | 16 | 20 / 16 | A: matched; B: matched |
| 2026-01-05 | 28 | 23 | 28 / 12 | A: matched; B: matched |
| 2026-01-06 | 14 | 20 | 14 / 20 | A: matched; B: matched |
| 2026-01-07 | 20 | 14 | 20 / 14 | A: matched; B: matched |
| 2026-01-08 | 18 | 20 | 18 / 20 | A: matched; B: matched |
| 2026-01-09 | unknown | unknown | unresolved | A: unknown_availability; B: ambiguous_latest |
| 2026-01-10 | unknown | 20 | unresolved | A: not_available; B: matched |

The fixed baseline has lower MAE and realized cost than the declared as-of forecasts on this constructed sample. Time eligibility corrects a false performance claim; it does not make a poor forecast useful. The zero-error final snapshot cannot justify replacing the baseline.

January 9 needs a documented release time for A and an authoritative resolution of the simultaneous B releases. January 10 needs a forecast available before its cutoff for A. Until those conditions are met, the automated order remains unresolved; an operational fallback is outside this task.

## Limits

Availability timestamps are declared synthetic metadata; this calculation cannot establish their real provenance or completeness. The exercise does not estimate forecast uncertainty, establish external validity, or demonstrate forecasting skill beyond this fixed eight-day sample. It is not a blind generalization test or an award-quality competition paper.

A future-value perturbation check is included as a model-side information-boundary check only. It is not an independent validator; the independent timestamp scan and exact enumeration are handled separately.
