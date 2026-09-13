# Current status — House to Nightmare Door

Authoritative closeout: 2026-09-12. Read this with `configs/handoff_state.json` and
`docs/handoffs/NEXT_SESSION.md`. This document supersedes historical narrative
status and task queues, not their raw evidence. The current session is closed
for exploration: no new progression, collection, learner training or uploads.

## Objective and exact endpoint

The milestone is **HOUSE → OPEN NIGHTMARE BOSS DOOR**, not the Cello. Start from
the supplied house state (shield already present), progress through physical
gameplay, obtain required dungeon items/keys, and observe the closed-to-open
boss-door transition. Stop **outside** boss room `0x06`, in antechamber `0x0B`,
at full health (`health == 8 * max_hearts`, currently 24/24), sword A, Roc's
Feather B, grounded, movement released, world settled, dialogue closed, door
animation finished, and no pending damage or healing. Physical healing is
allowed; full health is required at the endpoint, not at every frame.

Rolling Bones blocks this route and remains in scope when development resumes.
Moldorm and the Full Moon Cello are later, separate objectives. The door has not
been opened in a complete live route. No full-route teacher or learner qualifies.

## Authority map

| Concern | Current authority |
| --- | --- |
| Current status and read order | This file; `docs/handoffs/NEXT_SESSION.md` |
| Machine-readable closeout and authorization | `configs/handoff_state.json` |
| Research pointers | `configs/research_focus.json`; generic legacy success flags are scoped historical fields |
| Active progression protocol and endpoint/gate criteria | `configs/house_to_boss_door_v2.json` |
| Route and training design | `docs/HOUSE_TO_BOSS_DOOR_FULL_HEALTH.md` |
| Furthest route evidence | `docs/HOUSE_BOSS_DOOR_ROUTE_PROGRESS.md`, `reports/house-boss-door-route-progress-v1.json` |
| Latest health-preserving development | `reports/full-health-route-development-v1.json` |
| Failed Nightmare Key timing check | `reports/nightmare-key-route-smoke-v1.json`; frozen `configs/nightmare_key_route_smoke_v1.json` |
| Room-15 closure | `docs/ROOM15_ARCHITECTURAL_DECISION.md`, `reports/room15-takeover-decision-result.json` |
| Selected local controllers | `configs/sword_controller.json`, `configs/navigation_experiment.json`, `configs/progression_local_controller.json`, `configs/tail_cave_controller.json` |
| Historical selected room-15 teacher | `configs/tail_cave_compass_room_controller.json`; its collection authorization is historical, not permission for new labels |
| Reproducibility inventory and checks | `reports/handoff-closeout-2026-09-12/` |
| Release plan and wipe blockers | `configs/house_boss_door_checkpoint_v1.json`, `docs/WIPE_READINESS.md` |

## Verified progression and claim boundaries

Continuous guided progression includes house → sword → mushroom → witch →
Tarin → Tail Key → Tail Cave, the first Small Key, room-15 combat, Compass, Map,
Roc's Feather, physical full healing, the third collected Small Key, Nightmare
Key and arrival at Rolling Bones. Acquired keys are subsequently spent; collected
count is not the same as current keys held.

The historical guided house-to-first-key panel passed **20/20 with exact replay**.
Its cave teacher took over before the first model proposal executed in all cases.
The best continuous result with no cave-teacher fallback was **17/20**, below
18/20; the rest of that quest still includes guided/local control. Neither
number is autonomous House-to-Nightmare-Door performance.

The revised post-feather route arrives at room `0x0E` at **24/24 instead of 8/24**
and saves **578 emulator frames** from the same refill. A direct room-`0x04` jump
removes the room-`0x05` detour; shielded room-`0x0D` combat clears without damage.
This is one development comparison, not varied-start qualification.

The reusable Nightmare Key controller passes nominally but only **1/2 fresh
timing checks**; all three replay exactly. The new room-`0x10` crossing has one
nominal state-checked success. Rolling Bones was reached, not defeated. A
3,000-frame lower-lane probe survived at half a heart and reduced enemy health
8→5, then failed its budget. It is stopped, not a cleared or extendable gate.

## Living handoffs and exact replay

| Role | Continuation | Verified end |
| --- | --- | --- |
| Preferred full-health development | `runs/full-health-worm-guard-v1/room0e-full-health-continuation.json` | Frame 47,692; room `[1,0,14]` = `0x0E`; `(11,68)`; 24/24; Map/Compass/Feather; 1 Small Key; no Nightmare Key |
| Furthest fresh progression | `runs/tail-cave-room10-state-check-v2/continuation.json` | Frame 52,180; room `[1,0,17]` = `0x11`; `(17,72)`; 4/24; Nightmare Key; 0 Small Keys; miniboss undefeated |
| Full-health feather backup | `runs/tail-cave-feather-v2/feather-full-health-continuation.json` | Frame 45,836; room `0x18`; `(40,16)`; 24/24 |
| Nightmare Key receipt | `runs/tail-cave-nightmare-route-v2/nightmare-key-continuation.json` | Frame 50,574; room `0x08`; `(72,40)`; 4/24; Nightmare Key; 1 Small Key |

The two primary handoffs were replayed again during closeout under the current
code: **10,963 and 13,722 commands**, respectively. Dependency hashes, every
command fingerprint/snapshot/frame/event, and final dungeon items matched.
No extra progression commands or midroute state loads were used. Evidence:
`reports/handoff-closeout-2026-09-12/replay-verification.json` and `replay.log`.
The other handoffs are preserved dependencies/history; no fresh independent
full replay of each secondary branch is claimed by this closeout.

Each continuation lists `start`, ordered `replay_segments`, dependency hashes
and final state. Restore all those files, not just the JSON or final savestate.
Savestate-local success is not continuous-route evidence. The idle13 failed
Nightmare smoke and room10-crossing-v2 falling end are unsafe continuations
despite positive raw health in old summaries; do not resume them as milestones.

## Models and guidance

| Artifact | Current disposition |
| --- | --- |
| `runs/tree-clean-route-v3/policy.json` | Selected learned sword tree, fixed-start/local scope |
| `runs/navigation-cliff-specialists-v2/model/epoch-256.pt` | Selected experimental known-goal navigator; v7 fallback preserved; not a general route planner |
| `runs/progression-dagger-v1-model/candidate.pt` | Selected bounded mushroom crossing |
| `runs/progression-downstream-recovery-v1-model/candidate.pt` | Selected bounded learned arrival followed by deterministic recovery |
| `runs/tail-cave-specialist-v3-model/candidate.pt` | Selected room-`0x16` specialist; autonomous local 18/20, all 18 zero damage |
| `runs/tail-cave-integration-dagger-v5-model/candidate.pt` | Rejected autonomous promotion at continuous 17/20; retained proposal model in guided execution |
| Tail Cave disengage v10 / balanced v11 | Rejected at 13/20 and 16/20 fresh continuous panels |
| Room-15 students V1/V2/V3/V4 | Rejected: 13/20, 7/20, 14/20, 15/20; different panels, not a controlled learning curve |
| Room-15 V5 recovery and elapsed-context models | Unqualified diagnostics, not promotion evidence; 6/8 and 5/8 on training-source episodes |
| House-to-open-door learner | Does not exist |

The historical room-15 deterministic teacher passed 43/43, including 10/10 true
half-heart cases. Its later supplemental check failed at 4/5 and 3/4 half-heart;
the base13/idle313 lethal failure remains a progression reliability blocker.
The attempted mid-room takeover was stopped after verifier serialization errors;
three primary clears did not qualify it. The learned recovery branch stays closed.

Paths, actual hashes and configured-hash checks for selected/retained weights
and named rejected candidates are in `model-inventory.json` under the closeout
report directory. All configured selected hashes checked there match. Preserve
other historical candidates, datasets and optimizer/RNG checkpoints as well;
this focused inventory is not an exhaustive backup manifest.

## Training authorization and gates

No new collection, imitation labels, model selection or learner training is
authorized by this handoff. Existing approved historical labels retain their
provenance; this does not authorize their use in a new experiment. Current
progression traces are development evidence, not automatic labels.

After development is explicitly resumed, the sequence remains: complete one
continuous full-health door proof → exact replay → freeze fresh teacher cases
and budgets → **20/20 house cases plus 4/4 actual half-heart recovery challenges**,
all satisfying the full-health/equipment/settled endpoint → collect separate
approved demonstrations → freeze grouped dataset split, observation/action
schema, learning config and compute budget → train/evaluate.

Model-only promotion remains **18/20 plus 4/4**, exact replay throughout and zero
teacher fallback. Assisted completion, autonomous completion, teacher-controlled
frames/interventions, health, damage/healing, frames and decisions stay separate.
The criteria are set, but the new full-route gate case manifests and learning
experiment are **not frozen**. Existing historical gates are unchanged.

## Sealed evaluation

The 20 original validation specifications/results remain sealed evaluation
evidence, never development input: `runs/progression-longrun-hour-v1/plan.json`,
`cases/validation-house-*`, shared results/verification records, and
`reports/progression-longrun-hour-v1.json`. The separate 96 reserved specifications
are at `runs/data-workset-16m-v1/frozen-eval.json`; smoke versions also remain
preserved. No contents were parsed or evaluated in this closeout. Opaque
integrity hashes are recorded in `sealed-integrity.json`; final comparison is
recorded in `verification-summary.json`. Keep these artifacts in private backup,
outside training/public dataset releases. Historical evaluated sword results
are separate from these untouched reserved panels.

## Current blockers and next bounded work

1. Room `0x0E` guard preserves health but exhausts its fixed 600-decision budget;
   encounter, key receipt and safe exit are not solved. Separate timing smoke
   also exposes enemy contact at the landing.
2. Connect that safer route through the Nightmare Key without losing its health
   advantage; no timing sweep or favorable branch splice substitutes for proof.
3. Rolling Bones needs bounded safe attack/disengagement and a complete clear.
4. Final approach, physical healing if required, and full-health door opening
   have no complete live proof. Software endpoint tests do not establish it.
5. Full-route variation can still expose earlier room-15 and other failures.

First task for the next session: read the short handoff, verify artifact hashes
and reproduce the preferred 24/24 room-`0x0E` arrival with zero new commands. If
development is resumed, inspect the already-recorded room-`0x0E` 600-decision
stall and freeze one bounded encounter/pickup development plan before editing.
Do not start with a training batch, timer extension or Rolling Bones exploration.

## Repository, environment and release state

Base Git commit: `6ae99a894afaf9c53e5e60202d9a1f92c34dfa78`. This is **not** a
commit of the current working tree. Many earlier code/config/doc/test additions
and modifications were already uncommitted at entry; see `git-status-before.txt`
and the final status/inventory in the closeout reports. No commit, push, upload,
delete or wipe was performed. Existing modifications to the historical
`configs/progression_protocol_v1.json` predate closeout and were preserved.

Closeout regression result: **171 tests passed**, no failures/errors/runtime
skips. One test file (`test_progression_longrun.py`) was deliberately excluded
because it regenerates sealed case definitions. Existing temporary optimizer
resume tests are software tests, not learner campaigns. Syntax/JSON/link checks,
diff hygiene and final evidence integrity are recorded separately in the closeout
verification summary. This is not a claim that every experiment or backup works.

Runtime: Python 3.11.16, PyBoy 2.0.0, Torch 2.2.2, NumPy 1.26.4, Gymnasium
0.29.1, SB3 2.3.0. `environment.json` records all installed distributions,
platform and reference checkout commits; checked reference commits match the
lock file and are clean. ROM SHA-256:
`6285ba6201f17bc8595c600ebc2477d52561f0aff29b11f7fc3343bacb2e230b`.

GitHub: `foxmedik/GameBoyGhost`. The existing HF dataset is
`foxmedik/GameBoyGhost-LADX`, historically verified at revision
`5a11ac080f056e2b1d9e4bf5a489b960399ff1fd` (not remotely reverified here).
That old 16,777,216-action release does not back up current model/run artifacts.
Checkpoints are recorded as local-only. The new local development package at
`data/releases/house-boss-door-full-health-v1-development` is unpublished,
unqualified, contains zero training rows and no model weights, and predates this
closeout. Do not mistake it for a complete machine backup.

The annotated recording is at
`runs/videos/house-nightmare-route-development-v2/house-nightmare-route-development-annotated.mp4`
with source/video hashes, annotations and a YouTube description. It depicts
recorded guided input, not live inference; it stops before the miniboss clear.

**Wipe readiness is false.** Current source has no pinned release commit; model,
raw/private evidence and full research-state backups are unverified; no clean
restore and continuous replay from external backups has been demonstrated.

## Historical documents that must not drive the next session

`docs/PROJECT_STATUS.md` is now an indexed historical log, including conflicting
old statuses. `docs/handoffs/PROJECT_HANDOFF_v2.md` and `RICE_SESSION_HANDOFF.md`
are broad historical requirements, not current task queues. The demo-recorder
handoff, human-demo playlist, old progression execution plan, training strategy
audit, and old room-15 recovery/student reports preserve earlier decisions only.
`configs/progression_protocol_v1.json` covers the older quest; the alive-only
`configs/house_to_boss_door_v1.json` and `docs/HOUSE_TO_BOSS_DOOR_PLAN.md` are
superseded by the full-health v2 endpoint. Historical teacher success and label
authorization flags never override the explicit current scope and restrictions.
