# Delayed-start exclusion

For the archived original 96-cell network at D=0.003 m²/s, a zero-flow prefix of at least 790 s cannot maintain every cell at or above 39°C throughout 1800 s, under any common measurable flow q(t) in [0,3] L/min. This is a sufficient exclusion, not the exact latest feasible start. The optimistic comparison permits each row to select its own most favorable flow, which physical common control cannot generally realize.

A two-stage witness waits 780 s, supplies 3 L/min for 90 s, then 0.9524284460 L/min to the 1800 s horizon (19.2626409135 L total). Independent DOP853 and 0.1 s chord bounds qualify all three stages, with a 2e-6°C integration allowance per phase propagated cumulatively; the floor bound is 39.004393°C. This positive witness is conditional floating qualification, whereas the exclusion uses an explicit discrete-method error radius. The pair leaves a ten-second gap, without certifying every earlier delay, global minimum water, or the sharp latest start. Two additional720/750s witnesses are archived separately in the same packet.

The primitive packet was reconstructed after the first producer run. The accepted archive-only replay is separately recorded: direct physical flux arithmetic, 18000 SSP2 passive steps, 1000000 optimistic Euler steps, rational truncation/rounding radius and an all-step state-domain induction. Ordinary IEEE binary64 arithmetic assumptions are explicit in rounding-proof.md; this is not formal BLAS verification, experimental validation or a continuum theorem. The stored producer states are a cross-check, not a substitute for the new independent error enclosure.

From the repository root:

```sh
.venv/bin/python demos/mcm-2016-a/reproduce/reference/delayed-upper/check.py > /tmp/praxis-delayed-upper-fresh.json
```

`check_pulse.py` prints a fresh independent three-policy receipt using the same immutable primitive packet and no model import.

The checker reads immutable primitive bytes, never imports the model/producer, and prints a fresh receipt without replacing accepted files. `inputs.json` retains the historical producer source hash as provenance; the public replay does not execute that private original program. Source/model identity, conditions, exact endpoint arithmetic and all current member hashes are checked by the paper consumer. The physical model is shared; only numerical assembly and error analysis are independent.
