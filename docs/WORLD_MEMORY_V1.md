# Persistent world memory v1

The first world-memory implementation imports the three replay-verified progression-interface development traces. It requires no new gameplay or optimizer updates. Run `.venv-ladx/bin/python scripts/build_world_memory.py --out runs/world-memory-next` to reproduce it in a fresh output directory.

## What exists

`src/gameboy_agent/world_memory.py` provides versioned, content-hashed JSON snapshots, idempotent trace import, deterministic directed route queries, movement-outcome queries, and explicit generation inheritance. Import verifies fixture artifact hashes, contiguous decision numbers, journal/trajectory agreement and replay-success provenance before committing. `verify_evidence()` reconstructs every observation from its original hashed trace. Loading a snapshot validates its content hash and observation references; use evidence verification to also check external source files.

Each observation references a trace hash/path, line/decision, frame and event ID where available. Historical inventory, health and quest conditions remain attached to evidence. They are not the new episode's possessions or completed milestones; the planner must read current episode state from the environment.

Connections are directed. Their positions are explicitly an action-boundary bracket and a settled arrival, not exact doorway/collision coordinates. Route queries find a shortest observed room chain and return its evidence and historical conditions. They do not yet validate present prerequisites or execute movement. Missing return evidence yields an unknown route rather than an invented reverse edge.

Movement attempts preserve both no-displacement and displaced outcomes in the same coarse cell/direction. Mixed outcomes remain visible, and passability stays unknown. A stationary frame can reflect an animation or temporary obstruction. Damage observations retain their event position and raw health loss with cause unassigned; the imported safe traces contain no damage, so that path is currently covered by a separately labeled synthetic test.

Landmark observations include recorded dialogue IDs and sword acquisition locations. Exact text, speaker identity, prerequisites, repeatability and untraversed exits remain unknown. This initial memory contains discoveries from gameplay traces, not facts imported from the supplied map artwork.

## Acceptance evidence

`reports/world-memory-v1.json` records:

- Three verified source traces and 1,243 evidence-backed observations across 13 rooms.
- 779 presence observations, 442 movement attempts, 14 directed connection observations and eight landmark observations.
- All 1,243 observations re-derived from immutable trace evidence.
- All 169 room-pair route queries identical before/after save/load and in the inherited generation.
- House-to-sword query returns 12 observed connections; sword-to-house and sword-to-Tail-Key correctly return unknown.
- Seven tests cover directed routing, every-pair roundtrip, import order/idempotence, inheritance isolation, tamper rejection, mixed movement outcomes and damage attribution boundaries.

Snapshots and route examples are in `runs/world-memory-v1/`. Generation 1 inherits knowledge from generation 0 and records its parent hash; it contains no new discoveries yet. This establishes storage/query inheritance, not an efficiency improvement through generations. Source traces remain required for a full evidence audit. Filesystem paths are local provenance and must be deliberately rebased when moving the dataset.

## Next integration

Connect the room-chain query to a goal manager and local navigation. Validate the action-boundary approach positions before treating them as control targets. Add newly observed directed crossings to the next memory generation and retain failed attempts. For the unknown Tail Key route, use the explicitly assisted map/quest references to propose targets, verify physical transitions, and keep provided hints separate from discovered knowledge.

No live navigation run using this memory, autonomous frontier discovery, exact NPC text decoding or memory-efficiency experiment has occurred. These belong to subsequent integration and evaluation stages. The 96 historical reserved navigation specifications remain untouched.

Full regression: 86/86 tests passed in 36.343 seconds. Evidence: `reports/world-memory-v1-regression.json`. Memory implementation/source hashes still match the recorded build.
