# Focused route correction v3

Route v3 fixes both local regressions and preserves all three known successful beach loops. It is not promoted because two westbound route runs still take damage. Focused v4 remains selected.

| Check | Selected v4 | Route v2 | Route v3 |
| --- | ---: | ---: | ---: |
| Complete four-goal routes | 0/9 | 2/9 | 3/9 |
| Ordered waypoints reached | 19/36 | 22/36 | 25/36 |
| Navigation damage across routes | 20 | 16 | 12 |
| Route deaths | 1 | 1 | 0 |
| Original local successes | 46/48 | 46/48 | 46/48 |
| Additional local successes | 39/48 | 43/48 | 43/48 |
| Fresh local successes | 46/48 | 46/48 | 46/48 |
| Damage across all local panels | 0 | 4 | 0 |

All three beach_return starts succeed without damage. Every v4 local success and every successful route from route v1/v2 is preserved. The original damaged case now succeeds in 26 actions without damage, and the repaired fresh case remains successful in 14 actions without damage. All local start fingerprints match their references.

The west_return route reaches three goals from house and beach, then times out. Beach takes eight health units of damage; approach takes four, reaches only the first goal, and times out. All room_loop starts still stall on goal three without damage. Zero route damage is the only failed boolean promotion condition; unresolved route timeouts remain substantive limitations even though the gate only requires improvement in complete-route count.

## Diagnosis and correction

The damaged original local case first disagrees with v4 at action index 11. Collection uses the original successful v4 path and candidate prefixes of 8, 11, and 14 actions. The repaired fresh path is an explicit successful training example.

Every waypoint of successful beach loops is independently replayed: house and approach from route v2, beach from route v1. The lost beach return is searched from its handoff at action 383 and prefixes at 387 and 407.

Westbound selected v4 traces themselves take damage, so they are not used as safe reference paths. From route v2's physical trajectories, beach first loses health at action index 353 and approach at 190. Corrections start at the handoff, four actions later, and three actions before that first loss. All nine beach/west recovery origins produce damage-free successful paths. Finding such paths does not guarantee the learned policy will follow them or retain safety later in the route.

There are 26 collection origins and 50 replay-verified successful paths, totaling 2,372 actions. Shortest observed suffix labeling yields 1,871 unique masked-input states, with 45 conflicting states. Each label retains path/row/hash provenance. Successful route anchors are explicit supervised examples, rather than only probability-retention examples.

One fixed final-epoch candidate initializes from route v2, trains eight epochs at learning rate 5e-6 with retention KL weight eight, and balances each supervised batch equally across damage correction, fresh preservation, beach routes, and westbound correction groups. Retention covers 346,536 original cache rows and 8,668 previous demonstration rows. Architecture and feature normalization are unchanged. No intermediate epoch is selected using evaluation results.

## Verification and boundaries

All 48 tests pass. The three original sword-to-goal chains remain successful without damage in 49, 49, and 45 navigation actions. Pause/resume at action 470 after the first waypoint matches the uninterrupted actions, fingerprint, counters, damage, and final status exactly.

The damaged original case's episode was already retired by the v3 local-correction experiment. The fresh case was retired during route v2. The registry remains at 79 retired cohorts; future untouched panels must exclude them. These are known development/training regression cases, not held-out generalization results. Reserved evaluation is unused, supplied goals remain scripted, the privileged D harness is unchanged, and game completion is not evaluated.

Artifacts:

- `scripts/navigation_route_focus_v3.py`: diagnostic positions, collection jobs, and fixed plan.
- `scripts/train_navigation_routes.py`: balanced supervised groups and parent retention.
- `scripts/report_navigation_routes.py`: paired evaluation and union of earlier route successes for preservation.
- `reports/navigation-routes-v3.json`: portable metrics and gate result.
- `runs/navigation-routes-v3`: ignored local source snapshots, data, model, traces, and evaluation driver.

The next correction can concentrate on the two remaining harmful westbound trajectories while retaining this candidate's zero-damage local results and all three successful beach loops. The room-loop cliff detour still needs a verified demonstration. No ROM, emulator state, or model weight is added to Git.
