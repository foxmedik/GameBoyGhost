# Map acquired; feather approach diagnosed

The dungeon map is acquired in one continuously reconstructed house-to-milestone episode. The living milestone is saved separately from two later terminal failures.

| Milestone | Observed result |
| --- | --- |
| Map room `0x14` | Both skeletons and both bats defeated |
| Map receipt | `DBCC=1`, dialogue `0xA6` dismissed |
| Inventory at map | Map, compass, two Small Keys |
| Health at map | 12 raw units (1.5 hearts) |
| Map milestone | Frame 39,609; `(135,58)` in room `0x14` |
| Northern door `0x07` → `0x04` | Opened; Small Keys 2 → 1 |
| Room `0x04` block puzzle | Rightward push opened west exit |
| Room `0x03` | Both spiked beetles defeated; stairs opened |
| Underground | Reached rooms `0x19`, `0x18` |
| Focused retry | Defeated final Goomba, climbed out, reached feather chest room `0x1D` |
| Feather / cello | Neither acquired |

All new control was interactively guided physical input with privileged read-only state and screenshots. No learned-policy improvement is claimed. Original house state only; each attempt reconstructs its entire prefix through physical inputs. No mid-encounter state reload, game RAM assignment, teacher-label generation, training, or sealed evaluation use occurred.

## Failure evidence

The initial extension collected the map, then died at frame 44,035 in underground room `0x18`. Before that encounter, attempted powder use on Sparks consumed three powder and failed to heal; this is a recorded failed action, not a recovery skill. Other damage came during combat and pit/trap traversal. The event journal reports raw health changes without individually attributing every cause.

One focused retry used the exact recorded prefix through frame 43,966, reconstructed from the original house. At that state, the last Goomba was to Link's right, but `hLinkDirection=1` and `wSwordDirection=4` showed left-facing orientation. A physical right turn set `hLinkDirection=0`; an ensuing sword attack defeated the Goomba without damage. This is one local development correction, not an independently qualified teacher or proof that every preceding failure had the same cause.

The retry then climbed out through `0x01` and `0x1C`, entering `0x1D`. Advancing directly through the paired spike traps from the half-heart state failed at frame 44,542. The chest remains unopened. No further retry was run in this session.

The parent failure and retry are retained independently, including all errors and health loss. Exact replay verifies physical reproducibility; it does not turn either terminal failure into a successful progression case.

## Continuations and next work

Use `runs/tail-cave-map-v1/map-continuation.json` as the current living milestone. It reconstructs the house through map acquisition and retains 1.5 hearts and two keys. The previous compass/second-key milestone remains intact.

Terminal traces are `runs/tail-cave-map-v1/trajectory.jsonl` and `runs/tail-cave-feather-retry-v1/trajectory.jsonl`; their terminal continuation metadata must not be used as living starts. `runs/tail-cave-map-v1/retry-prefix.jsonl` and `retry-handoff.json` identify the exact development branch before the Goomba correction. Request logs preserve the interactive control choices.

Next: build a bounded state-checked spike-trap crossing, tracking both trap positions and motion before committing to the lane. Verify actual facing before combat inputs; do not infer a turn succeeded merely because a directional button was pressed during another animation. Improve health preservation on the approach, collect Roc's Feather, then work toward the Nightmare Key, boss, and cello. Do not convert this route into training labels until its teacher passes a frozen reliability gate. Existing autonomous gates (18/20 overall, 4/4 actual half-heart) remain unchanged; room-15 learned recovery remains closed.
