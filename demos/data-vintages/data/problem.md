# Which demand version was available when the order was placed?

This original synthetic exercise has ten 08:00 UTC daily decisions for two products. A store orders integer units with total daily capacity40. Units cannot be carried forward. Predicted shortage penalties are6 per A unit and4 per B unit; overage costs1 per unit. These are declared cost units, not real money. Each forecast version has an event time and a declared availability time. Outcomes are disclosed only for retrospective evaluation.

1. Match every one of20 queries to the latest forecast strictly before08:00. Preserve missing availability, conflicting latest releases and not-yet-published forecasts as unresolved, rather than discard them.
2. For each day with both forecasts supported, minimize the declared forecast loss under the capacity. For unresolved days retain the day and explain the missing evidence required before an automated order.
3. Compare current-version orders with the predeclared20/20 baseline over the eight common supported days. Report forecast MAE, realized shortages/overages and declared realized cost. Repeat with the deliberately invalid final-snapshot forecasts to expose retrospective score inflation. Final-snapshot results are an upper-information comparison, never deployable forecasts.
4. Verify the selected versions by a separate timestamp scan and decisions by exact integer enumeration. Mutate values only in versions released after the cutoff and verify supported orders do not change. State what remains unknown about actual release provenance, uncertainty, external validity and forecasting skill.

All inputs and the scoring population are fixed before model execution. This is method demonstration, not a blind generalization test or an award-quality competition paper.
