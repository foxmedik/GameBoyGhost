# Proximity sword teacher: 48 matched sessions

The proximity gate sharply reduces sword use but fails the safety/success gate. It is not enabled for collection or the selected learned navigator.

| Metric | Alternating cadence | Proximity gate |
| --- | ---: | ---: |
| Goal successes | 41/48 | 36/48 |
| Actual sword-animation starts | 747 | 93 |
| Sword-press actions | 747 | 93 |
| Damage, raw health units | 4 | 12 |
| Deaths | 0 | 0 |
| Navigation actions | 1,529 | 1,760 |
| Emulator frames | 16,318 | 23,794 |

Actual swings decrease 87.6%. Six baseline successes become failures and one baseline failure becomes a success. Two cases take four additional health units of damage each. The same movement rule is used in both arms, but changing sword actions changes trajectories, timing, terrain, and subsequent movement decisions; these are live comparisons, not a fixed-action replay with buttons removed.

## Frozen protocol

The experiment uses the original 48 known development goal cases: 24 same-room and 24 cross-room cases across house, beach, and approach starts. Each case runs independently under both policies, giving 96 rollouts, with a 128-action limit and the existing eight-pixel Manhattan goal tolerance. Source data hashes and packed initial observations are checked. Every matched pair starts at the same complete emulator fingerprint. Every resulting trajectory is replayed independently to the exact final fingerprint.

Both variants use `navigation_recovery.teacher` with attempt zero: goal-directed movement and a sword press on alternating steps. The experimental variant only suppresses proposed sword presses. It requires a nonzero-status entity of a listed known enemy/hazard/projectile type within a 32-pixel Euclidean radius, using read-only entity positions. NPCs and pickups are excluded. It also suppresses presses during sword animation states 1–4. Dialogue and other item inputs are unchanged. This initial test does not predict motion, use facing, detect cuttable terrain, or classify every possible entity type.

The entity addresses, type constants, and sword states are checked against the local matching disassembly and baseline code. The predicate is an experimental teacher rule under the existing privileged D harness; it is not inserted into the learned navigator's inputs or runtime.

Sword-animation starts are counted frame by frame through the ordinary transition/readiness loop, independently of action-level press counts. The 93 allowed presses have nearby listed threats; 775 proposed sword presses are suppressed for no nearby threat. There are no additional suppressions due to the active-animation condition in this batch, so that condition's benefit is not established here. The remaining 892 actions are unchanged non-sword or interaction actions.

## Failure evidence

Case `763b4286fbad9a9da88b05c5193e729a743e00489d7a93e95683e45a0a961ebe` targets E1 (92,26). The distance-gated rollout stops at (82,39), below intact bushes. The successful cadence rollout cuts those bushes and reaches the goal. Independently replayed diagnostic screenshots verify the terrain difference. This demonstrates a necessary non-combat use of the sword that the gate omits; it does not establish the cause of all six lost successes.

Case `2b70007c69c8e7a7faa9399a6eea7e76e799e097862a30690fafdf1f90fa4f51` also regresses to a damage-free timeout, ending in E0 at (55,16) rather than reaching its D0 goal. Detailed per-action reasons and paired traces remain available for further diagnosis. Increased damage occurs in cases `a45a26acffba91348ea082faed603b2f2768dafade8d4071f8255b98d55a5439` and `ad819075151c6872ba4622cf0b6f321940e4f0ad957e2172c3da14a0bf760fcb`.

The next test should permit sword use for obstructing cuttable terrain and account for threats closing during the next action interval. A larger static radius or facing rule alone has not been tested, and no safety benefit is claimed for them.

## Artifacts and verification

- `scripts/proximity_sword.py`: isolated gate and read-only inputs.
- `scripts/evaluate_proximity_sword.py`: frozen 48-pair experiment and full replay checks.
- `scripts/inspect_proximity_failures.py`: paired screenshot diagnosis.
- `tests/test_proximity_sword.py`: six passing tests covering radius boundaries, NPC/inactive exclusion, active swing handling, dialogue/item preservation, and unchanged movement.
- `reports/proximity-sword-48-v1.json`: portable per-case results, summary, and rejected gate.
- `runs/proximity-sword-48-v1`: ignored frozen plan, source snapshots, action/event traces, and diagnostic images.

No training or model promotion occurs. All cases are known development/training-regression cases; the reserved evaluation set is unused. Selected route v7, ROM exclusions, and current runtime behavior remain unchanged.
