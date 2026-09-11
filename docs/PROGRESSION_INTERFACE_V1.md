# Honest progression interface v1

This is a separate implementation for the guided Tail Key milestone. `TrainingEnv`, the selected navigation checkpoint and historical experiment results remain unchanged. The full stage plan is `docs/PROGRESSION_EXECUTION_PLAN.md`.

## Implemented

- `src/gameboy_agent/progression_env.py`: physical movement/A/B plus explicit Start/Select pulses; inventory/status and map readiness; bounded action/wait/frame counts; fresh emulator reset; zero shaped reward. Historical two-integer movement/A/B actions remain usable, but the RAM inventory action is rejected.
- Inventory observations retain their existing order and shape, remove powder refill and duplicate-slot edits, and treat Tail Key possession as nonzero. No automatic powder grant. Observations update the environment's own history but never write game memory.
- `src/gameboy_agent/progression.py`: read-only snapshots and a frame-level event journal for raw damage/healing, slots, resource counts, trade item, dialogue IDs, stable room changes and source-grounded milestone candidates. Damage cause, NPC speaker and exact dialogue text are deliberately unknown until a validated attribution/decoding path exists.
- `src/gameboy_agent/progression_skills.py`: bounded physical equipping by observed slots/cursor, including moving an item between A and B. Missing item, dialogue/wrong mode, episode termination and budget exhaustion fail explicitly. Ocarina submenu behavior is not supported by this first equip skill.

Milestones latch acquisition, opening and settled entry separately. Initial key possession/open entrance/entrance-room state rejects a fresh quest. Death and unsettled/dialogue states cannot trigger successful entry. A terminal candidate requires both observed key acquisition and observed entrance opening in the episode. Source-grounded detection is not yet live quest validation.

## Evidence

`reports/progression-interface-v1.json` and `runs/progression-interface-v1-verified/` contain 13 passing interface tests and three physical gameplay/replay fixtures:

| Start | Sword actions | Total recorded decisions | Raw damage | Exact per-action replay |
| --- | ---: | ---: | ---: | --- |
| House | 412 | 428 | 0 | Pass |
| Beach | 268 | 268 | 0 | Pass |
| Approach | 83 | 83 | 0 | Pass |

House includes 16 additional decisions to equip the physically obtained sword onto B and back onto A. The house fixture recorded 12 stable room transitions and two dialogue-open events. A journal JSON roundtrip during replay matched the final journal. Each fixture stores a trajectory, event journal, final screenshot/state, fingerprints and artifact hashes. This is action-prefix reconstruction of emulator state, not a new arbitrary savestate-resume guarantee.

Synthetic tests separately exercise 100 read-only observation/progress calls with depleted powder, duplicate slots and raw Tail Key value 1; invalid controls; state reset; health loss followed by healing; dialogue identity; false entry/death boundaries; and bounded transition waiting. Test setup edits are not demonstration data or quest success evidence.

The first validator invocation exposed a replay keyword mismatch; its incomplete directory `runs/progression-interface-v1/` is retained. The corrected complete evidence is under `runs/progression-interface-v1-verified/`. Only the complete report counts.

Run again into a fresh directory:

```bash
.venv-ladx/bin/python scripts/validate_progression_interface.py --out runs/progression-interface-next-check
```

## Still pending

No continuous Tail Key journey, world-memory planner, exact NPC text extraction, new optimizer run or reserved evaluation occurred here. Toadstool pickup, witch exchange, raccoon cure, Tail Key pickup, keyhole opening and dungeon entry must be physically exercised and independently replayed during stage 3. The new mode has only revalidated these three sword starts; historical navigation or 70-case sword scores do not automatically transfer to it. The asset references are available but not consumed by a controller yet.

Full regression verification: 79/79 tests passed in 37.207 seconds, including the 13 new progression tests. See `reports/progression-interface-v1-regression.json`. The interface source hashes and selected navigation checkpoint hash were checked after the suite; both match their evidence records.
