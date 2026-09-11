# Terrain-aware sword teacher v2: decision

**Terrain plus motion passes the frozen teacher adoption gate on the 48 known development cases.** Terrain without motion is rejected. This result does not establish learned selective sword use or full-game completion.

| Metric | Cadence | Terrain + exit guard | Terrain + exit guard + motion |
| --- | ---: | ---: | ---: |
| Goal successes | 41/48 | 42/48 | 42/48 |
| Actual sword-animation starts | 747 | 263 | 250 |
| Sword-press actions | 747 | 263 | 250 |
| Raw health-unit damage | 4 | 8 | 4 |
| Deaths | 0 | 0 | 0 |
| Actions | 1,529 | 1,063 | 1,058 |
| Emulator frames | 16,318 | 11,658 | 11,608 |
| Lost baseline successes | — | 0 | 0 |
| Cases with increased damage | — | 1 | 0 |

The motion arm reduces actual swings by **66.5%**, preserves all 41 cadence successes, and gains one (b85b0c...). It matches cadence's nonzero damage rather than becoming damage-free. Each of 144 rollouts has an independent exact final replay. All paired start fingerprints match, and every rerun cadence start/final matches v1. No reserved cases were used.

## Mechanistic evidence and remaining limitations

The confirmed bush-stall case 763b4286... reaches its goal in both terrain arms with one swing rather than cadence's nine. All four foliage-authorized presses in each experimental arm have their sampled tile change within three actions in the same room. This supplies observed before/after evidence for the source-derived predicate on these cases; it is not exhaustive reach or terrain coverage.

The only regression across either experimental arm is the previously identified sand-crab case a45a26... in Terrain without motion. Link spends 127 of 128 actions at (36,42), attempting left while the crab approaches from the right. Two hits total eight health units versus cadence's four. Terrain+motion still times out but takes four units, matching baseline. The separately measured motion change removes this per-case damage regression; its timing/RNG effects mean this is not proof of a general combat solution. Full preceding damage windows, entities, repeated positions, and final states are in the audit report.

The urchin-entry case ad8190... succeeds without damage in both terrain arms, with four swings versus cadence's eleven. The conservative exit guard preserves a proposed press before the previously unseen room. It does not use destination map knowledge. Of 250 motion-arm allowed presses, 163 are exit uncertainty, 76 nearby threat, four reachable foliage, and seven closing threat; 267 proposed presses are suppressed on clear paths. There are no active-swing suppressions, so that condition again has no demonstrated benefit. Exit conservatism accounts for most remaining presses and may swing against blocked room edges.

Six motion-arm cases still time out, including the stuck crab case. The teacher movement rule is unchanged and has no new detour or combat-facing recovery. These 48 known cases are development evidence only. The rejected v1 experiment remains intact.

## Deliverables and next fixed candidate

- Frozen protocol: `docs/PROXIMITY_SWORD_48_V2.md`; immutable execution snapshot and traces under `runs/proximity-sword-48-v2`.
- Portable metrics: `reports/proximity-sword-48-v2.json`; all-regression audit and cutting observations: `reports/proximity-sword-48-v2-audit.json`.
- Source: `scripts/terrain_sword.py`, `scripts/evaluate_terrain_sword.py`, `scripts/report_terrain_sword.py`, and `scripts/diagnose_sword_v1.py`.
- Verification: all 62 tests pass, including six new terrain/motion tests; ROM identity matches rebuilt disassembly, and revision-specific symbols resolve differing address comments.
- **42 safe demonstrations / 290 rows** were collected by `scripts/collect_terrain_sword.py` with original goals and two physical feature/action replays, matched back to the experiment's start/final fingerprints. Their dedicated manifest records scripted teacher privilege, not learned actions.
- `scripts/freeze_sword_candidate.py` froze one final-epoch candidate under `runs/navigation-sword-v1` from selected route v7, mixing the verified quiet-sword demonstrations with 202 inherited v7 preservation paths (6,773 rows), original-data/prior-path retention, and action-margin supervision. It does not invoke training.

Selected route v7 remains unchanged. The next candidate must pass all 144 known local cases with preservation of all 135 safe successes, all successful routes/waypoints, original continuous chains, and exact physical resume/replay, plus a matched learned-sword evaluation. The independently demonstrated cliff detour remains a later navigation objective; teacher waypoints are not inserted into learned runtime.
