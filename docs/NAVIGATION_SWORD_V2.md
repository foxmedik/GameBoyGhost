# Button-only selective sword v2 — rejected

The freeze mechanism works, but this candidate fails adoption. **Route v7 remains selected.** Changing buttons alone is sufficient to disrupt its navigation trajectories; preserving the movement function does not preserve the states on which that function operates.

| Measure | Selected v7 | Whole-network v1 | Button-only v2 |
| --- | ---: | ---: | ---: |
| Original local panel | 46/48 | 42/48 | 45/48 |
| Additional local panel | 43/48 | 42/48 | 43/48 |
| Fresh local panel | 46/48 | 47/48 | 46/48 |
| Local damage, raw units | 0 | 4 | 0 |
| Complete routes | 6/9 | 4/9 | 3/9 |
| Route waypoints | 30/36 | 28/36 | 27/36 |
| Route damage, raw units | 0 | 0 | 4 |
| Original continuous chains | 3/3 | 3/3 | 3/3 |
| Original-panel actual swings | 582 | 568 | 579 |

No deaths occur. V2 reduces swings by only **0.5%**, missing the required 25%, loses one local success and all three previously successful west-return routes, and adds damage to the beach-start room loop. Original-panel actions increase from 1,155 to 1,273, and frames from 12,670 to 13,850.

## Controlled training and verified invariants

This is a single fixed eight-epoch ablation from selected v7. Data, seed, learning rate 5e-6, balanced batches, retention, action-margin loss and final-epoch selection match v1. Only the final layer's three button-output rows are updated. Shared layers are frozen and movement-output gradients are masked. An assertion checks protected tensors after every optimizer step. No additional training or checkpoint shopping occurs.

Final-checkpoint comparison verifies identical bytes for every shared tensor and the five movement-output rows, plus unchanged normalization and feature mask. Movement logits are exactly equal to v7 on all 7,063 training rows. Only the button portions of `net.4.weight` and `net.4.bias` change. Standard checkpoint reload preserves this behavior; there is no runtime teacher gate. See `runs/navigation-sword-v2/frozen-movement-verification.json`.

On the 290 new teacher rows, button-label agreement remains 36.2%, the same as v7. Inherited-label agreement decreases from 99.4% to 96.3%. These are training-fit diagnostics, not live evidence; they show this particular constrained training recipe did not fit the new button behavior well. They do not prove button-only learning is impossible.

## Regression evidence

The lost original local case is 4b4081e2... . Its first difference is `[right, sword]` becoming `[right, no button]`; it later stalls at E2 (32,87). It also failed in whole-network v1. Here direct movement-weight drift is excluded by the invariant.

All three west-return starts reach three waypoints and fail the final return. Their first differing action changes only the button. House stalls at E1 (138,67) for 239 actions; beach and approach stall at E1 (124,71) for 236 and 234 actions respectively.

The beach-start room loop first differs at action 293 by dropping an upward sword press. During the second goal, health falls from 12 to 8 over actions 321–322 near E2 (51,127) / (49,128). The run later times out at the usual cliff goal. The audit records these damage windows; it does not claim an enemy identity or a single causal mechanism from the trace alone.

## Verification and decision

All 64 tests pass, including optimizer-step and checkpoint-reload protection tests. The same evaluation protocol completes: 192 local rollouts, nine routes and three original chains, all with independent exact final replay. Rerun v7 original fingerprints match historical results; all paired starts match. Route and chain pause/resume outputs match uninterrupted runs exactly. No reserved evaluation was used.

Reject v2. Both prior candidate and teacher artifacts remain unchanged. The teacher's 66.5% reduction is still a teacher-only result; learned selective sword use remains unresolved.

Before another training run, a useful next diagnostic would test selective sword collection along v7's own movement trajectories. The current new demonstrations come from a different, straight-line movement teacher. A passing teacher under v7 movement would provide better-matched training examples; it must first pass the same paired success/damage gates. This is a proposed next experiment, not an implemented runtime fix or completed collection.

Artifacts: `reports/navigation-sword-v2.json`, `reports/navigation-sword-v2-audit.json`, `configs/navigation_sword_v2_candidate.json`, and ignored run directory `runs/navigation-sword-v2`. New implementation is in `scripts/button_only_training.py`, `scripts/train_navigation_buttons.py`, `scripts/freeze_sword_buttons.py`, `scripts/evaluate_sword_buttons.py`, and `tests/test_button_only_training.py`. Nothing was committed or uploaded.
