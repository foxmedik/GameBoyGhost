# Selective sword teacher on v7 movement — rejected for collection

The unchanged terrain-motion sword gate does **not** preserve selected v7 when used with v7's own movement decisions. Reject it for training-data collection. No new training demonstrations were curated, no model was trained, and selected route v7 remains unchanged.

| Measure | Unmodified v7 | V7 + selective sword gate |
| --- | ---: | ---: |
| Goal successes | 46/48 | 35/48 |
| Actual sword-animation starts | 582 | 233 |
| Sword-press actions | 582 | 233 |
| Raw health-unit damage | 0 | 12 |
| Deaths | 0 | 1 |
| Actions | 1,155 | 1,922 |
| Emulator frames | 12,670 | 20,141 |

Swings fall 60.0%, but eleven baseline successes are lost, none gained, and two cases take extra damage. All 96 rollouts independently replay to the exact final fingerprint. Paired starts match, and every unmodified-v7 start/final matches the historical v7 result. These are the same 48 known development cases; no reserved evaluation is used.

## What changed

Both arms use the identical selected v7 policy on the current observation. In the experimental arm, the existing terrain-motion gate suppresses only proposed sword presses; every executed movement component equals v7's proposal at that decision. The gate, radius, foliage rules, conservative exit handling and motion horizon are unchanged. No forced movement sequence, coordinates, recovery route, or fake controller history is inserted.

The gate's 20-frame lookahead came from an alternating teacher and does not guarantee v7's next sword opportunity. More fundamentally, changing buttons changes subsequent observations and physical motion timing. Matching a movement function does not match its resulting trajectory.

## Complete regression audit

| Case prefix | Outcome | Main repeated position | Extra damage |
| --- | --- | --- | ---: |
| e180088302d8 | Lost success | F1 (92,96), 125 actions | 0 |
| a45a26acffba | Existing timeout | F3 (36,42), 127 actions | 4 |
| 763b4286fbad | Lost success | E1 (124,49), 120 actions | 0 |
| c975b2fd3b62 | Lost success | E2 (108,130), 125 actions | 0 |
| 84b11d6f3a8d | Lost success | E1 (20,64), 115 actions | 0 |
| 25d047d467a4 | Lost success | F2 (87,96), 124 actions | 0 |
| 98d4f3095a33 | Lost success | E1 (144,90), 124 actions | 0 |
| 4b4081e2a601 | Lost success | E2 (32,87), 117 actions | 0 |
| 115a958140af | Lost success | E2 (36,90), 57 actions | 0 |
| f7a2cedad4d0 | Lost success | F0 (132,74), 64 actions | 0 |
| 6bacd401212d | New death | F3 (69,42), 20 actions | 8 |
| 6bfd067a9019 | Lost success | F2 (21,64), 124 actions | 0 |

All twelve cases have first-divergence, preceding/final state windows, repeated positions, entity records, and damage windows in `reports/v7-sword-teacher-v1-audit.json`. These observations locate the failures; they do not establish a unique cause.

The original bush case 763b... starts at (52,49). V7 keeps proposing right+sword, while the gate repeatedly executes right without sword. Link reaches (124,49) and continues pushing right. No swing starts. In the earlier straight-line-teacher experiment, the movement teacher turned toward the bush and cut it; that outcome does not transfer to this v7 trajectory.

Extra damage in a45a... occurs near the same sand crab as earlier experiments, now versus v7's zero-damage baseline. Case 6bac... loses eight health units and dies during sand-crab encounters after becoming stuck while trying to move up. A nearby/closing-threat sword allowance does not ensure correct facing or escape.

The gate suppresses 1,460 proposed presses as clear path. It allows 192 for exit uncertainty, 20 for nearby threat, 17 for closing threat, and four for reachable foliage; 229 actions are unchanged. No active-swing suppression occurs. Lower swing count here is partly associated with repeated failed movement and is not competent navigation.

## Previous-button diagnostic: limited evidence

`control_context.py` includes the previous button in input index 4. Three failed final states were independently physically replayed, then queried without executing any action. Changing only this model input from previous-button none to A changes the proposed sword press to no button in all three cases, but leaves movement unchanged:

- Bush failure: right → right.
- F1 failure: down → down.
- E2 failure: right → right.

An artificial previous-B input changes one movement decision, but it is not the actual missing A history. Thus the experiment confirms button-history sensitivity in the button output at these states, not that history correction fixes navigation. No counterfactual input was fed into a live rollout. Recorded fingerprints stay unchanged throughout the queries. See `reports/v7-sword-button-history.json`.

## Decision

Do not curate favorable cases from this rejected teacher as if its adoption gate passed. Preserve raw diagnostic trajectories only. Training transfer is not the sole problem: this selective-button teacher already regresses before training when coupled to v7. The next work needs to address navigation under changed sword timing and trajectory distribution; another button fine-tune from these runs is unsupported. Any future change needs a new frozen comparison.

Artifacts: frozen plan and traces under `runs/v7-sword-teacher-v1`; `reports/v7-sword-teacher-v1.json`; the audit and button-history reports above; `scripts/evaluate_v7_sword_teacher.py`, `scripts/audit_v7_sword_teacher.py`, and `scripts/inspect_v7_button_history.py`. Prior experiments, source snapshots, selection and ROM exclusions remain intact. Nothing was committed or uploaded.
