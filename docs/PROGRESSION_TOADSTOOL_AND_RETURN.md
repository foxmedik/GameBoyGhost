# Physical toadstool acquisition and cave return

> Subsequent milestone: [the witch exchange is verified](PROGRESSION_WITCH_EXCHANGE.md). The room-42 blocker described below is historical; Tarin cure is now next.

The mushroom milestone and return to the forest now have continuous house-start action traces, frame-level event journals, verified block changes and independent exact action replay. The learned policies were not changed. These are scripted teacher baselines, not learned quest-completion results.

## Results

| Run | Outcome | Decisions | Emulator frames | Total damage / healing | Final health |
| --- | --- | ---: | ---: | ---: | ---: |
| `progression-toadstool-v1` | Mushroom acquired, both outbound pushes validated | 2,912 | 17,331 | 8 / 0 | 16 |
| `progression-witch-approach-v4` | Three return pushes validated; returned to outdoor room 62 with mushroom | 3,143 | 18,659 | 12 / 0 | 12 |
| `progression-witch-exchange-v2` | Reached outdoor room 42; bounded approach stopped with dialogue 08D open at (44,101) | 3,391 | 19,486 | 12 / 0 | 12 |

All three independently replay exactly, including per-command fingerprints, observed state, emulator-frame counts and journal events. Each starts at the original house state and replays the whole physical prefix, without intermediate state loads. The 2,349-decision forest prefix preserves its original fingerprints and zero damage/healing. Tail Key and Tail Cave success are not claimed.

## Implementation

`ProgressionEnv.step_input_events()` records exact emulator-frame press/release events for timed interactions, including diagonal input and 64-frame pushes. Unmentioned inputs retain their state; explicit releases are recorded. Every advanced frame updates the journal and consumes the shared episode frame budget. Death and truncation end the episode. Existing ready-frame command behavior remains unchanged.

`toadstool_teacher.py` preserves the known physical route while validating both original A7 block cells changed. The return search in `cave_navigation.py` uses live objects and matched ROM physics. It searches at most 4,096 geometry states and treats each moved block as immovable A6, as specified by `references/LADX-Disassembly/src/code/entities/03_pushed_block.asm`. The first return plan took 19 search states and proposed three pushes; all three original cells and A6 destinations were verified physically in v3/v4.

The first doorway required moving vertically clear of its jamb before lateral centering. The final cave doorway uses C1/C2 transition tiles, so the skill approaches the interior stance and checks the actual outdoor transition instead of requiring those tiles to be ordinary walkable floor.

## Preserved failures

- Return v1 established that the reloaded stone room had no ordinary eastward path.
- Return v2 found the block plan but stalled while centering sideways inside the doorway.
- Return v3 physically completed the three pushes and reached the first cave room, then exposed the special bottom doorway geometry.
- Return v4 verified the full cave return. It sustained one additional four-unit hit in that cave room; total damage is twelve, not zero.
- Witch-exchange v1 exposed an approach crossing a room edge before its separate transition check and took eight additional damage units.
- Witch-exchange v2 recognized early transitions and held the equipped shield. It took no further damage, but ended with the rock/lifting dialogue 08D open. The current controller does not resolve that interruption during local approach. Dismissing the prompt and reassessing the path is the next bounded work; a reliable physical witch interaction has not yet been demonstrated.

Each failed attempt also has an independently replayed trace. No unchanged implementation was run more than three times. No optimizer or human-recording collection was launched.

## Reproduction

Use a new ignored output directory each time. These commands require the existing local prefix artifacts and the verified ROM:

```sh
.venv-ladx/bin/python scripts/run_toadstool_progression.py --out runs/toadstool-new
.venv-ladx/bin/python scripts/run_toadstool_progression.py --stage witch-approach --out runs/return-new
.venv-ladx/bin/python scripts/run_toadstool_progression.py --stage witch-exchange --out runs/witch-new
```

The stage sources are explicit in the runner: forest v5 for acquisition, toadstool v1 for cave return, and return v4 for witch approach. Source artifact hashes are checked. These historical traces remain immutable; current helper changes can yield different subsequent behavior, which must be independently replayed before promotion.

Per-run limits are 12,288 decisions and 300,000 emulator frames. New return/witch extensions are capped at 512 decisions, with smaller local approach and transition budgets. Plans are written before execution. Runs write trajectory, journal, final snapshot, skill evidence, source hashes, result and manifest, followed by evidence-backed memory import after replay passes. Raw ROMs and runs remain ignored.

## Current next step

Implement bounded handling of the observed room-42 dialogue/path interruption and continue toward the witch. Keep sword/toadstool/cave-return proof as regressions, record damage separately from progress, and stop on the next demonstrated blocker. Human recorder work is shelved. No new training is justified by this result.

## Regression validation

All 112 repository tests passed in 37.234 seconds with no skips, using the pinned optional data dependencies in a temporary directory. New coverage checks exact-frame accounting/truncation, diagonal press/release replay, and block search that forbids pushing A6 a second time. All seven new run manifests were rechecked and all seven physical traces independently replayed. The selected navigation policy hash is unchanged. See `reports/progression-toadstool-integration-v1.json` for the compact ledger.
