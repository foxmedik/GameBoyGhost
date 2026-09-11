# Human capture playlist: House to Toadstool

Record these as short, repeatable takes. Each clip should begin from the named
state or room, pursue one observable outcome, and stop as soon as that outcome
is clear. The recorder supplies raw frames, exact input holds, Link position,
room/panel, health, and inventory automatically; add only the listed manual
tags.

The full route is a final integration clip, not the primary source of training
examples. The earlier clips give the model reusable control and interaction
skills that make the final route understandable.

## Capture rules

- Keep one clip focused on one decision or one local skill.
- Capture two to five clean successes for each clip.
- Add one or two near misses from the same situation where useful: a blocked
  attack, late shield, wrong turn, missed swing, or collision. Tag the result.
- After each meaningful event, tag the action and outcome. Do not annotate each
  grid cell or every movement frame.
- Avoid resets in the middle of a clip unless the reset itself is the intended
  recovery example.

## Playlist

| # | Clip | Start | Stop / success mark | Takes | Manual tags |
| --- | --- | --- | --- | --- |
| 01 | House controls and exit | House state | Leave the house and settle outside | 3 | `transition`, `route_landmark` |
| 02 | Village movement | Outside house | Reach the first route landmark without damage | 3 | `route_landmark`; `damage` only if it occurs |
| 03 | Sword pickup interaction | Sword beach approach | Pick up sword; inventory changes | 3 | `item_acquired`, `dialogue_advanced` |
| 04 | Equip and basic slash | Safe post-sword area | Equip sword and land several normal slashes | 4 | `attack_hit`, `attack_missed` |
| 05 | Spin slash timing | Safe enemy area | Charge, release, and hit with a spin slash | 5 | `spin_start`, `attack_hit`, `attack_missed` |
| 06 | Shield projectile block | Projectile enemy room | Block a projectile without damage | 5 | `projectile_seen`, `blocked`, `damage` |
| 07 | Melee approach, strike, retreat | One melee enemy | Defeat it without damage | 5 | `enemy_defeated`, `attack_hit`, `damage` |
| 08 | Cuttable terrain | Grass/bush in route area | Terrain disappears and path opens | 4 | `cut_terrain`, `terrain_changed` |
| 09 | Non-cuttable obstacle | Similar-looking blocked terrain | Attempt fails, then route around it | 2 | `terrain_blocked`, `recovery` |
| 10 | Forest entry and redirect | Mysterious Woods entrance | Follow the correct route through the forest redirect | 3 | `transition`, `route_landmark`, `recovery` |
| 11 | Forest enemy lane | Any hostile forest panel | Cross the lane safely using sword/shield | 4 | `enemy_defeated` or `blocked`, `damage` |
| 12 | Cave mouth approach | Forest room `52` | Move south to `62`, enter cave `0A:BD` | 4 | `entrance_used`, `transition` |
| 13 | Crumbling-floor crossing | Cave `0A:BD` | Reach room `0A:AC` without falling | 5 | `route_landmark`, `damage` or `recovery` |
| 14 | Crystal clearance | Any cave crystal gate | Break crystal and observe open path | 4 | `crystal_broken`, `terrain_changed` |
| 15 | First rock push | Stone room `0A:AB` | Push block at `(7,3)` left until it moves | 5 | `push_start`, `object_moved` |
| 16 | Second rock push | Stone room after first push | Push block at `(7,5)` down until it moves | 5 | `push_start`, `object_moved` |
| 17 | Opened-lane exit | Stone room after both pushes | Walk through lane and take lower exit to room `50` | 4 | `transition`, `route_landmark` |
| 18 | Toadstool approach | Overworld room `50` | Walk into pickup range at the Toadstool | 4 | `item_seen`, `item_contact` |
| 19 | Toadstool narration | Pickup animation / dialog `00F` | Advance narration and observe Toadstool acquired | 4 | `dialogue_advanced`, `item_acquired` |
| 20 | Full clean integration | House state | Toadstool latch set; no avoidable damage | 3 | Milestone tags only: `item_acquired`, `transition`, `object_moved` |

## What “enough” looks like

The first useful batch is **80–100 short takes**: the clean takes above plus
roughly 20 near-miss examples. A practical first session is clips 01–09. A
second session can cover forest/cave clips 10–17. Finish with clips 18–20 after
the local skills are recorded.

For the cave route, preserve the visible choice points instead of rushing them:
the crumbling-floor trace, each successful 64-frame rock push, and the final
exit are individually more valuable than several near-identical full runs.

## Tag meanings

Use these terms consistently when adding tags through the app:

| Tag | Meaning |
| --- | --- |
| `attack_hit` / `attack_missed` | Sword or spin result was visible |
| `blocked` | Shield prevented a projectile or contact outcome |
| `damage` | Link lost health |
| `enemy_defeated` | Enemy disappeared after the interaction |
| `terrain_changed` | Grass, crystal, or other route terrain changed |
| `object_moved` | A confirmed pushable block moved |
| `transition` | Room, cave, door, stairs, or exit transition settled |
| `item_acquired` | Game inventory/quest state changed after pickup |
| `dialogue_advanced` | A physical A/B press advanced the message |
| `recovery` | A deliberate correction after an error or blocked route |
