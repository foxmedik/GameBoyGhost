# House → Boss Door route progress

The Nightmare Key is acquired and the guided continuous route reaches Rolling Bones, the required miniboss in room `0x11`. The final boss door is **not open**, the miniboss is not cleared, and the full route is **not yet repeatable or qualified for training**. The final boss room was not entered.

All gameplay here uses physical emulator input with read-only state observations. Every completed attempt reconstructs the original house start and independently replays its complete command history. Replaying the prefix supplies reproducibility for development; it is not the varied-start route controller. No labels or optimizer updates were produced. Sealed validation and closed room-15 recovery research remain untouched.

## What advanced

| Segment | Evidence | Limit |
| --- | --- | --- |
| Room `0x08` lower floor → `0x0E` → upper `0x0F` → staircase room `0x09` | State-checked controller reaches the correct upper entrance without damage on the nominal arrival | The lower `0x0F` entrance is separated from the north exit by solid blocks |
| Staircase lock and Nightmare Key | Jump across the pit at y=96, spend one Small Key, climb the stairs, enter the raised chest lane, close receipt | First physical proof: frame 50,574, room `0x08`, `(72,40)`, health 4, Nightmare Key and one Small Key |
| Reusable Nightmare Key controller | Nominal check passes; two fresh timing checks score **1/2**, all three replay exactly | Idle13 fails on an enemy at the early room-`0x0E` jump landing. No teacher qualification |
| Return to room `0x10` | Sword-assisted bat passage and the lower `0x0F` exit; spend the remaining Small Key at the right door | Door requires y≈72 alignment; this return has only development evidence |
| Room `0x10` → miniboss entrance | Corrected controller observes the outer Spark moving clear, turns through the interior lane, jumps the eastern pit | One state-checked nominal success, health unchanged at 4; not a varied-start reliability result |
| First miniboss bar | Physical jump across the approaching bar, alive at `(65,112)` | One development success |
| Miniboss lower-lane experiment | Survived the entire 3,000-frame budget at half a heart; enemy health 8→5 | Budget exhausted, room not cleared; failed experiment |

Machine-readable results: `reports/house-boss-door-route-progress-v1.json`. Nightmare Key timing results: `reports/nightmare-key-route-smoke-v1.json`. The nominal check is separate from the two fresh timing cases; do not report this as a qualified 2/3 reliability gate.

## Route corrections

Room identity alone is insufficient for traversal. Entering `0x0F` at y≈86 puts Link below a solid barrier; the Nightmare Key approach must enter near y=48. The controller validates the entry lane before continuing north.

In `0x09`, walking along the pit's lower lip failed. The successful path approaches `(104,96)`, jumps left to the safe platform, unlocks the key block, and climbs to the upper passage. The chest approach has its own narrow geometry: approach from the right at y=32, then stand below it at `(72,40)`.

On return, the room-`0x0F` bats can be active. The shield-equipped return died; the sword-assisted passage succeeded. This is limited developmental evidence, not a causal reliability comparison over varied starts.

In `0x10`, sword movement along the top wall met a Spark. Attempts to jump along that wall or turn the jump across the upper pit lip also failed. The successful physical path waited for the outer Spark, walked through `(104,72)`, then jumped east. The new controller replaces the fixed wait with an observed Spark position/direction condition. Its first clearance condition failed and is preserved with source in `runs/tail-cave-room10-state-check-v1/controller.py`; the corrected condition has one passing nominal check in `runs/tail-cave-room10-state-check-v2`. Neither is a full-route teacher gate.

## Miniboss decision

The pursuit controller reduced enemy health 8→7, then chased it toward the rolling bar and took fatal damage. The separate lower-lane controller kept Link stationary near `(80,111)`, prioritized jumps over approaching bars, and attacked when the miniboss entered range. It survived but only reduced enemy health to 5 before the predeclared 3,000-frame budget.

That experiment is stopped as failed. No timer extension, sweep, or training batch follows it. The next progression problem is a bounded encounter controller with explicit safe attack and disengagement phases. The final boss remains outside this phase; Rolling Bones blocks the route to the door and therefore remains in scope.

## Safety and endpoint work

New helpers validate the room before entity or route lookup, verify equipment for jumps/armed passage, stop on damage, and bound movement and transitions. Additional onward checks reject falling motion and buffered damage even while raw health is still positive. The continuation runner now reports those pending-damage endings as non-resumable and records caught blockers. It also derives current dungeon milestones from the final item flags instead of carrying stale values forward from the parent handoff.

Two older diagnostic endings need care: the idle13 Nightmare Key smoke stops during health subtraction, and room10-crossing-v2 stops during a fall. Their original summaries contain positive raw health; these are **failed, unsafe continuation states**, not living progress milestones. Their original trace evidence is preserved.

The boss-door endpoint candidate is separate from the legacy progression journal so old snapshots and replay hashes remain compatible. It requires the Nightmare Key, the centered approach in room `0x0B`, an observed closed→open transition, finished animation, settled health, and remaining outside boss room `0x06`. It releases movement as opening begins. Unit tests pass, but live endpoint validation awaits reaching the door.

Validation: **23 focused tests pass** across route preconditions, falling/buffered-damage rejection, door success/failure semantics, and existing feather/Tail Cave contracts. These are software checks, not gameplay reliability evidence.

## Living handoffs and next session

- Preferred fresh miniboss arrival: `runs/tail-cave-room10-state-check-v2/continuation.json`, room `0x11`, `(17,72)`, health 4, Nightmare Key, no Small Keys held, frame 52,180.
- First bar crossed: `runs/tail-cave-room10-crossing-v4/miniboss-approach-continuation.json`, room `0x11`, `(65,112)`, health 4, frame 52,340. This uses the separately preserved earlier physical crossing.
- Lower-lane experiment end: `runs/tail-cave-miniboss-lane-v1/continuation.json`, health 4, enemy health 5. It is a failed experiment's live state, not a cleared milestone or an invitation to extend its budget.
- Nightmare Key receipt: `runs/tail-cave-nightmare-route-v2/nightmare-key-continuation.json`.
- Full-health feather backup remains `runs/tail-cave-feather-v2/feather-full-health-continuation.json`.

Next sessions have two explicit obligations: finish the miniboss/antechamber/door route, and repair the earliest observed repeatability failure at the room-`0x0E` landing before any full-route teacher qualification. Do not use the successful nominal traces to bypass the failed timing check. Once the entire route exists, freeze a fresh full-route teacher gate, then collect separate approved demonstrations and freeze training. The House → Boss Door phase remains incomplete until its declared gates are met.
