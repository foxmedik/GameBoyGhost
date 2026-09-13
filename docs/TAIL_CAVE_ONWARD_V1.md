# Tail Cave: compass and second Small Key

The next concrete milestone is complete in a single continuous guided development episode. The route starts from the supplied house state, reconstructs the previously verified prefix, clears room `0x15` with the existing deterministic teacher, then collects the compass and second Small Key.

## Verified result

| Measurement | Result |
| --- | --- |
| Compass | Owned: `DBCD = 1` |
| Small Keys | Two: `DBD0 = 2` |
| Final room and position | Tail Cave `0x13`, `(135,58)` |
| Final health | 8 raw units, one heart |
| Dialogue | Closed after Small Key receipt (`0xAA`) |
| New physical commands | 563 |
| New emulator frames | 3,516 |
| Final episode frame | 38,289 |
| Independent replay | Every command matched fingerprint, snapshot, frame, events; final journal matched |
| New training / sealed validation use | None |

The 563-command extension was chosen interactively from live state and screenshots, with bounded coordinate checks and observed room transitions. It is guided physical development, not learned model execution. No intermediate state reload or game-memory write was used. A final emulator state was saved only after reaching the milestone; the authoritative continuation reconstructs the full episode from the house.

## What happened

In room `0x15`, a delayed pickup dialogue interrupted movement. Closing it allowed the approach around the chest plinth. Opening the chest set the compass flag, and its receipt dialogue was dismissed. The route returned east through rooms `0x16` and `0x17`, then went north to `0x13` with full health.

The first north-transition assertion incorrectly expected room `0x07`; it stopped after observing `0x13`. The matched ROM's `src/data/maps/layouts.asm` confirms that `0x13` is north of `0x17`. Numeric room IDs are not spatial coordinates.

In room `0x13`, the approach went around the upper side of the central pit to activate the floor switch. This spawned the chest on the right. The subsequent retreat went badly: the beetle/pit interaction and repeated movement into the pit area cost 16 raw health. RAM health events establish the loss; their individual causes are not assigned by the journal. All failed movement attempts and the recovery remain in the replay.

After returning to the bottom entrance area, the route used the outer right corridor, approached the chest from below, opened it, and dismissed the Small Key dialogue. Live memory confirmed two keys. The run ended alive, with the beetle still present.

## Limits and next work

This is one successful, exact-replay development case. It establishes progression, not reliability. The extension is not qualified as a teacher and must not produce imitation labels. Autonomous gates remain unchanged at 18/20 overall and 4/4 actual half-heart; no new model was selected. The room-15 recovery branch remains closed, including its supplemental base13/idle313 failure.

Continue with guided progression toward the dungeon map in room `0x14`, east of `0x13`. The matched chest table identifies that item. Begin by checking room `0x13`, positive health, compass ownership, two keys and closed dialogue; keep the one-heart state and surviving beetle explicit. Do not replay the failed switch retreat as a navigation policy. Use live state checks to choose the next physical actions and preserve the entire continuous trace.

Artifacts:

- `runs/tail-cave-onward-v1/summary.json`
- `runs/tail-cave-onward-v1/milestones.json`
- `runs/tail-cave-onward-v1/trajectory.jsonl`
- `runs/tail-cave-onward-v1/continuation.json`
- `runs/tail-cave-onward-v1/final.png`
- `runs/tail-cave-onward-v1/milestone.state` (convenience artifact; not the authoritative replay start)

The source disassembly is under `references/LADX-Disassembly/`; the relevant files are `src/data/maps/layouts.asm`, `src/data/chests/indoors_a.asm`, and `src/constants/memory/wram.asm`. No external guide or sealed evaluation specification was used.
