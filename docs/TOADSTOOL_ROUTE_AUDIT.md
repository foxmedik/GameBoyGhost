# Toadstool route audit

## Result

The exact outdoor edge graph from the verified forest checkpoint does not reach the toadstool room. The route instead passes through a cave and requires pushing specific movable rock tiles to open the way. Ordinary room-distance navigation is insufficient.

This closes the first mapping pass. It does not claim that the toadstool has been reached or that the full route has been solved.

## Confirmed target

The matched ROM places `ENTITY_SLEEPY_TOADSTOOL` in overworld room `50` at source tile coordinates `(3, 2)`. Its handler gives the magic-powder inventory item and latches `wHasToadstool` at `DB4B` only after the physical pickup sequence finishes. The qualifying progression run must observe that latch; this audit did not touch the item.

## Verified route so far

The current continuous development trace reaches the forest along this observed sequence:

```text
D0 → C0 → C1 → B0 → A0 → 90 → 80 → 70 → 60 → 61 → 51
```

Leaving room `51` to the north does not produce its geometric neighbour `41`. Tarin sets the Mysterious Woods "lost" flag while Link is in the northern portion of that room, and the room-transition handler redirects a northward exit to `63`. The v5 trace then takes `63 → 53 → 52`.

From the v5 arrival state in room `52`, an exploratory physical traversal of all reachable screen-edge branches produced 79 distinct arrival states and no arrival in room `50`. This confirms that simply giving the local planner more outdoor edge budget will not find the toadstool.

The exploratory branch search used reconstructed emulator states to avoid repeating the prefix for every diagnostic branch. It is route-mapping evidence only and is not a qualifying episode or learner evaluation.

## Transition evidence

When room `52` loads, the game exposes two warp records:

| Warp tile index | Destination category/map/room | Destination position |
| --- | --- | --- |
| `55` | `01 / 1F / E1` | `(88, 80)` |
| `33` | `01 / 10 / A7` | `(80, 124)` |

The ROM stores these tile indices as part of the room's warp data. They are not enough to trigger a transition on their own: the game first needs the appropriate entrance, stair, pit, or similar interaction to initiate map loading. A short diagnostic approach to those grid cells did not transition, so the next implementation must identify the actual triggering object and approach direction instead of treating a warp position as a walkable waypoint.

## What changes next

Add a narrow cave-transition skill that, in a reached room, reads the loaded warp records and source-backed entrance objects, approaches only the known cave candidate, waits for a settled map change, and records the resulting map/room/position. It must distinguish a successful indoor transition from an ordinary collision or enemy interruption. Start with room `52`; do not broaden outdoor exploration or start policy training.

The cave entrance is now physically verified. From the v5 forest checkpoint, the route is `52 → 42 → 43 → 44 → 54 → 64 → 65`; approaching room `65` tile `24` from below and holding up settles in indoor map `0E`, room `A2`. This diagnostic traversal took damage in hostile outdoor rooms, so it is route evidence, not a replacement for the full-health forest regression.

Inside the cave, identify `OBJECT_PUSHABLE_BLOCK` (`A7`) from the live room-object grid and push only those tiles. The game requires 64 frames of sustained physical collision before a block moves, so the action must hold the relevant direction long enough to complete the push and then verify the changed room grid or newly reachable path. Ordinary rock tiles remain obstacles; do not generalize the push action from appearance.

The first cave room `0E:A2` is a side-scrolling room and has no `A7` block. Link falls from the entry at `(80,122)` to a stable ledge near `(80,86)`, so the cave runner must wait for that physical landing before it treats movement as a failed control. Moving right reaches a heavy obstacle and opens dialogue `08D`: “you won't be able to lift it with just your bare hands.” This cave branch is therefore gated by an unavailable item and cannot be the current toadstool route. It remains recorded as a verified, rejected branch; the next search targets a different cave entrance or a reachable push-block path.

The alternate entrance is now verified: from room `52`, move south into room `62`, approach the live warp at tile `37` from the reachable cell `(7,4)`, and enter room `0A:BD`. This is the toadstool cave branch. Its initial object grid contains two real `A7` blocks at `(4,4)` and `(5,5)`; the room must be solved by physical sword and movement actions, with every push verified against the post-action object grid. The local GameFAQs guide describes the required room order: defeat Keese, move stones to the 50-rupee chest, avoid the crumbling edge floor, continue north, defeat the Gels, then go left and move the stones until an escape path opens. Only then should the runner take the southern cave exit and pick up the mushroom.

The guide's cave description matches the ROM data exactly: `IndoorsBBD` has four Keese, two `OBJECT_PUSHABLE_BLOCK` tiles (`44` and `55`), and the room's exterior-return warp. This is now the source authority for the training trace: use short motion pulses near crumbling floor, sword actions to clear hostile or breakable obstructions, and only 64-frame sustained collision once the intended `A7` block and push direction are physically established.

Live control probe: the room is entered at `(80,123)`. Three-frame pulses move Link safely along the lower corridor (`right` to `(84,123)`, then `up` to `(84,106)`, then `left` to `(48,106)`). Longer holds are unsafe: they can collapse the floor or take the exterior-return warp. This makes pulse duration part of the cave skill's action contract, alongside the 64-frame push requirement.

The room-transition gate is separate from the motion gate: after the cave map first appears, 180 real emulation frames settle Link from `(80,123)` to `(74,94)`. Crystal and push stance checks must start after that landing, never during the entry fall.

General cave rule: if the live room contains both sword-breakable `DD` crystals and `A7` pushable blocks, the agent enters a `clear_crystals` phase first. Each target crystal requires a physical sword action and object-grid change before the local planner may enter `push_blocks`. This preserves the distinction between “a block is visible” and “a valid stance for a block push exists.”

## Verified stone-room route

The user-supplied route annotation is now grounded in the live object grid. From `0A:BD`, the crumbling-floor trace reaches `0A:AC`; an up phase followed by a left/up approach enters stone room `0A:AB`. This room has no visible `DD` crystals, so the generic crystal gate does not apply here.

At the right-hand entrance, the exact push sequence is:

1. Move down to the stance for object `55` (`(7,3)`) and hold **left** for 64 frames. Its original `A7` entry changes to `0D`.
2. Follow the red walking lane down to object `87` (`(7,5)`) and hold **down** for 64 frames. Its original `A7` entry changes to `0D`.
3. Walk left through the opened lane, then take the lower exit as shown in the red annotation.

The runner records both grid changes before it may attempt the exit. `toadstool_stone_push_plan` encodes these two room-specific, verified actions; it does not infer a push order for other cave rooms.

Once that skill reaches room `50`, stop adjacent to the source-defined toadstool position and separately validate physical pickup plus the `DB4B` transition. That pickup validation is the following step, not part of this audit.

## Evidence

- Continuous forest prefix: `runs/progression-forest-terrain-v5/trajectory.jsonl`
- Forest result and replay: `runs/progression-forest-terrain-v5/result.json`
- Aggregate checkpoint: `reports/progression-forest-progress-v1.json`
- Toadstool placement: `references/LADX-Disassembly/src/data/entities/overworld.asm`
- Toadstool pickup/latch: `references/LADX-Disassembly/src/code/entities/bank3.asm`
- Forest redirection: `references/LADX-Disassembly/src/code/entities/05_tarin.asm` and `references/LADX-Disassembly/src/code/room_transition.asm`
- Warp structure and trigger semantics: `references/LADX-Disassembly/src/constants/memory/wram.asm` and `references/LADX-Disassembly/src/code/bank0.asm`
