# Roc's Feather and third Small Key

The guided development route has advanced through Roc's Feather and the third collected Small Key. The Nightmare Key, dungeon boss, and cello are still ahead. This is physical guided progression, not a new autonomous result.

## Verified milestones

| Result | Evidence |
| --- | --- |
| Spike-trap crossing | Half-heart entry remained at health 4; crossed in 171 frames |
| Roc's Feather | Inventory item `0x0A`, receipt `0x97` closed; frame 45,275 |
| Full heal | Floating heart reached with feather; health 4 → 24 |
| Full-health feather handoff | Room `0x18`, `(40,16)`, frame 45,836; one key held |
| Third Small Key | `DBD0=2` after the earlier door consumed one of the first two |
| Receipt escape | Closing dialogue → jump left, health unchanged at 4 |
| Furthest living handoff | Empty room `0x08`, `(75,127)`, frame 48,919, health 4; two keys held |
| Replay | Both full attempts match fingerprints, snapshots, frames, events, and final journals |
| Stage-contract tests | 5 passed; wrong rooms/missing traps/dead destinations reject before movement |

## What changed

The prior direct crossing entered the traps' activation band before passing their row. The new development controller in `src/gameboy_agent/feather_approach.py` validates the room, health, position, dialogue, and two observed traps. It triggers the charge at `y=113`, retreats to `y=122`, waits until both traps are returning outward (`x<=48` and `x>=112`), then crosses the center lane to `y<=68`. The actual half-heart episode completed this sequence without damage. One success does not qualify the controller for training-label generation.

After collecting the feather, a physical jump crossed the traps on return. Another jump collected the floating heart and restored full health. The underground return used platform jumps successfully. The subsequent main-dungeon route lost health during failed lower-route crossings, pit traversal and enemy contact; every mistake remains in the trace.

The first attempt acquired the new Small Key in room `0x0E`, then died as the receipt dialogue closed beside a Spark. A development retry reconstructed the same house-to-dialogue prefix and used physical left/jump inputs as control returned. It escaped without damage, verified two keys held, and entered empty room `0x08` alive.

The lower part of `0x08` did not provide the assumed eastward passage to `0x09`. Returning south and attempting the outer route in `0x0E` ended in another Spark death. That terminal failure is preserved separately from the living key handoff. No claim of Nightmare Key or cello acquisition is made.

## Handoffs

- Furthest living milestone: `runs/tail-cave-key-exit-v1/third-key-safe-room-continuation.json`
- Full-health feather backup: `runs/tail-cave-feather-v2/feather-full-health-continuation.json`
- Trap decisions: `runs/tail-cave-feather-v2/trap-crossing.json`
- First complete attempt, including later death: `runs/tail-cave-feather-v2/summary.json`
- Key-receipt retry, including later death: `runs/tail-cave-key-exit-v1/summary.json`
- Machine-readable report: `reports/tail-cave-feather-and-third-key.json`

The living handoffs contain ordered command segments and hashes. Reconstruct from the original house state; the stored convenience emulator states were not loaded during these episodes. Terminal `continuation.json` files are explicitly marked not resumable. The full-health backup offers more survival margin; the forward handoff preserves the extra key at half-heart health.

Next work is safe Spark passage through `0x0E` toward `0x0F` and the `0x09` staircase, then the Nightmare Key and boss route. Use observed enemy positions and actual facing, and stop on unexpected room or health changes before extending a route assumption. Preserve existing room-15 research closure and all frozen gates. No labels, optimizer updates, sealed-validation use, or autonomous promotion occurred in this session.
