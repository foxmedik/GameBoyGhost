# Room 0x15 teacher recovery

The revised guided teacher passed 43/43 continuous cases: 40 fresh cases (20 house starts × idle offsets 22 and 23) plus three explicit regressions from a failed gate. All ten half-heart cases cleared without damage. All 43 attempts replayed exactly; 35 clears were damage-free. This is teacher performance, not autonomous model performance.

## Repairs and evidence

The overnight draft requested y=92 while bypassing the chest, but the eastern wall stops Link at y=80. Correcting that target cleared three of four selected movement probes. The fourth reached combat and timed out; all four half-heart probes still died with combat unchanged. This eight-case movement-only experiment remains in `runs/room15-movement-v1`.

The old guard assumed shots traveled downward and walked upward to block them. A continuous lethal trace shows a diagonal shot reaching Link from the left during that movement. The new guard uses signed projectile velocity and predicted closest approach, turns toward the most imminent intersecting shot, and holds the shield stationary. It ignores receding shots and trajectories that miss. The four half-heart probes then cleared without damage; the remaining combat-timeout probe also cleared. These five exact replays remain in `runs/room15-projectile-v2`.

A bounded bypass escape exposed a separate pickup transition. The first frozen gate scored 37/40, with no deaths and three precise bypass blockers. Actors had stopped before the dialogue flag appeared. Continuing one failed trace without reloading revealed the dialogue after ten neutral frames. Recovery now allows a bounded 64-command shielded wait before geometric escapes, checks dialogue every command, and resets recovery after dialogue dismissal. Unresolved blocking still raises a location-specific error after two bounded escape attempts. Wrong-room entry is rejected before route movement.

The first gate remains failed evidence. The second gate was frozen before execution, used fresh offsets 22/23 plus the three explicitly identified regressions, and required all 43 clears and all ten half-heart cases to be damage-free. It passed without changing the candidate during execution. The same projectile logic also protects the room-clear settling period.

## Scope and data boundary

Each case reconstructs the verified guided house-to-first-key trace continuously, then runs the room-15 teacher without an intermediate state reload. The upstream trace replay is a diagnostic harness; room-15 decisions use live state. There is no autonomous room-15 model result and no new model training. The previously measured autonomous cave results remain unchanged.

The 400 overnight traces and both gate panels remain evidence, not imitation labels. A separate frozen demonstration collection follows acceptance; only its zero-damage, exact-replay successes may be exported. These are teacher demonstrations, not on-policy student corrections. The existing 20 validation specifications/results were not read, tuned on, or relabeled.

Acceptance files: `configs/room15_teacher_gate_v2.json`, `runs/room15-teacher-gate-v2/summary.json`, and `configs/tail_cave_compass_room_controller.json`. Failed gate: `runs/room15-teacher-gate-v1/summary.json`. Candidate source snapshots and development plans are preserved under `runs/room15-recovery-development/`.

## Fresh demonstration collection

After acceptance, the unchanged teacher cleared 40/40 additional cases at offsets 24/25, including all eight half-heart cases without damage. The exporter retained 13,782 room-15 action/observation pairs from 34 zero-damage runs and excluded six damaged runs. All labels were checked against their original command and observation indices, and every source manifest was verified. The dataset covers 19 of 20 house starts; start 18 has no zero-damage examples in this collection. This is a coverage limit for the next learning experiment.

Data: `runs/room15-teacher-labels-v1/labels.jsonl` and its `manifest.json`. Full machine-readable evidence: [recovery report](../reports/room15-teacher-recovery-v2.json). Across the movement probe, projectile probe, two gates, and fresh collection, 136 cases have exact replay and verified manifests. All 136 tests pass, including wrong-room rejection, directional threat prediction, bounded movement recovery, and refusal to export diagnostic or failed-gate data.

No optimizer updates ran. The next step is to freeze a separate student experiment, including representation, data split, and a fresh acceptance gate, before training. The teacher gate does not establish autonomous student competence.
