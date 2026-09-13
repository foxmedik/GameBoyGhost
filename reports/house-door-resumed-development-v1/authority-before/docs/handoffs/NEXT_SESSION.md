# Read first — House to Nightmare Door handoff

Closeout date: 2026-09-12. Exploration is stopped. This session performed
documentation, integrity checks, tests and exact replay of existing evidence
only. No new progression, labels, route training, uploads or wipe occurred.

Read in order:
1. This file.
2. `docs/CURRENT_STATUS.md` and `configs/handoff_state.json`.
3. `configs/house_to_boss_door_v2.json` and `docs/HOUSE_TO_BOSS_DOOR_FULL_HEALTH.md`.
4. `reports/handoff-closeout-2026-09-12/verification-summary.json` and
   `docs/WIPE_READINESS.md` before any release/restore claim.

## Mission and honest status

From the supplied house state, physically open the Nightmare boss door and
finish outside the boss room at full health (currently 24/24), sword A,
Feather B, grounded, no dialogue/animation or pending damage/healing. Moldorm
and the Cello are later. Rolling Bones remains in scope because it blocks the
door route, but do not explore it during handoff closeout.

Verified guided progression reaches the Nightmare Key and Rolling Bones alive
at half a heart. Rolling Bones is undefeated; the boss door is not open.
The improved post-feather return reaches earlier room `0x0E` at full health,
16 raw health better and 578 frames faster than the old development route.
Its room-`0x0E` guard then exhausted 600 decisions without damage or a clear.

## Two primary handoffs — do not merge their claims

Preferred health-preserving route:
`runs/full-health-worm-guard-v1/room0e-full-health-continuation.json`
→ frame 47,692, room `[1,0,14]`, `(11,68)`, 24/24, one Small Key, no Nightmare Key.

Furthest fresh progression:
`runs/tail-cave-room10-state-check-v2/continuation.json`
→ frame 52,180, room `[1,0,17]`, `(17,72)`, 4/24, Nightmare Key, zero Small Keys.

Backup: `runs/tail-cave-feather-v2/feather-full-health-continuation.json` at frame
45,836, room `0x18`, `(40,16)`, full health. The primary two handoffs passed fresh
closeout replays of 10,963 and 13,722 commands; all dependency hashes, snapshots,
fingerprints, frame counts, events and final items matched. Secondary artifacts
retain earlier evidence; do not claim they each received another fresh replay.

Run from repository root, with dependencies/ROM restored, to verify only:

```sh
.venv-ladx/bin/python scripts/verify_house_door_handoffs.py --output runs/next-session-handoff-replay.json
```

Choose an unused output filename. This tool executes only the existing ordered
commands, writes a new verification report, and does not extend either route.
Never silently load a midroute savestate to stand in for continuous replay.

## First task, then the bounded next development step

First verify the hashes and reproduce the preferred full-health arrival with
zero new commands. If any artifact is missing or a fingerprint differs, stop
and recover the matching source/runtime/artifact; do not repair evidence or
lower checks to make it pass.

When the user resumes development, inspect the existing
`runs/full-health-worm-guard-v1/guard0e-evidence.json`, `requests.jsonl`,
`trajectory.jsonl` and `summary.json`. Identify the first non-progress state in
the 600-decision guard, then freeze one bounded state-checked encounter/key/exit
plan. Do not begin with another training batch or a timer/threshold sweep.
After room `0x0E`, connect to the Nightmare Key, solve Rolling Bones with safe
attack/disengagement, verify health recovery and physically open the door.

## Non-negotiable evidence rules

- Room-15 learned recovery is closed: no new label-weighting, threshold, timer
  or data-volume sweeps. The deterministic entry teacher is allowed for future
  guided development, but its later 4/5 supplemental check failed; 43/43 is
  historical scoped qualification, not full-route reliability.
- Room-15 V1–V4 are rejected (13, 7, 14, 15 of 20 on different panels). V5 6/8
  and 5/8 probes are training-source diagnostics, not valid promotion gates.
- Historical guided house-to-first-key 20/20 is teacher-assisted. Best continuous
  no-cave-fallback result is 17/20, rejected; other route sections were guided.
  The selected first-key specialist's 18/20 is room-local only.
- No full-route learner, frozen learning experiment, or approved whole-route
  dataset exists. Current development traces are not labels.
- Full teacher gate remains 20/20 house + 4/4 actual half-heart challenges, every
  finish full-health/battle-ready and every replay exact. Case manifests/budgets
  must be frozen after the first continuous proof, before qualification runs.
- Teacher qualification precedes separate demonstration collection, then frozen
  splits/config/budget before learning. Model gate remains 18/20 + 4/4 with zero
  fallback. Guided, autonomous and intervention metrics stay separate.
- Sealed 20-case validation and separate 96 reserved specs are off limits for
  development. Integrity hashes/private backup are allowed; parsing/evaluating,
  mining or relabeling them is not. Do not run `test_progression_longrun.py` during
  closeout: it regenerates those sealed case definitions.

## Software, source and preservation

171 regression tests passed, zero failures/errors/runtime skips; the one
sealed-definition test file was excluded. Tests include temporary optimizer
resume fixtures, not route training. See the recorded test command/log and
verification summary. The boss-door endpoint is software-tested, not live-proven.

Base commit `6ae99a894afaf9c53e5e60202d9a1f92c34dfa78` does not include the many
uncommitted changes. Preserve the working tree, including untracked source.
Do not reset, clean, stage everything blindly, or use an old handoff as current
authority. `repository-before.json` and `repository-after.json` document the
boundary. No commit/upload was made in this closeout.

Current weights and dependency hashes are in `model-inventory.json`; runtime
and clean reference commits in `environment.json`. The latest local evidence
package is not a backup or a qualified model release. Git ignores runs, data,
weights, ROMs and savestates. **wipe_ready=false** until external backup and a
clean restore/replay are verified. Follow `docs/WIPE_READINESS.md`.
