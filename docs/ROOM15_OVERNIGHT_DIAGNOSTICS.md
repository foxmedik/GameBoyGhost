# Room 0x15 overnight diagnostics — 2026-09-12

The frozen draft teacher completed 134/400 room-15 attempts (33.5%). This batch provides reproducible development failures; it does not establish a reliable teacher or a model improvement. No training ran.

The plan crossed 20 development house starts with 20 physical idle offsets (0–19 frames) after the first Small Key. Each case reconstructed the guided house-to-key trace continuously before invoking the room-15 teacher, without an intermediate state reload. All room-15 control came from the teacher. Autonomous room-15 performance was not evaluated.

| Measure | Result |
| --- | ---: |
| Completed cases | 400/400 |
| Successful room clears | 134 |
| Zero-damage clears | 126 |
| Alive at termination, including timeouts | 368 |
| Alive with zero damage, including timeouts | 275 |
| Decision-budget failures | 234 |
| Deaths | 32 |
| Half-heart clears | 3/80 |
| Half-heart deaths | 32/80 |
| Independent exact replays | 400/400 |
| Verified case manifests | 400/400 |
| Recorded suffix commands | 192,316 |

Case runtimes total approximately 2 hours 23 minutes. Damage and survival metrics cover the recorded suffix after the verified first-key prefix. The suffix incurred 500 raw damage units in aggregate and no healing. Frozen input hashes remained unchanged.

All deaths came from the four half-heart starts (11, 12, 13, 15). Of those 80 attempts, 45 exhausted the decision budget while alive and only three cleared. Start 16 also timed out in every offset, without a death. Thus survival alone substantially overstates progress.

Failures frequently ended at y=80: the most common terminal positions were (98,80), 37 cases; (111,80), 26; and (105,80) and (106,80), 23 each. This suggests a movement/bypass stall cluster, but terminal positions alone do not prove each failure's cause. Exact continuous traces should be used to locate the earliest stalled decision and test bounded recovery. Half-heart projectile/combat survival remains a separate unresolved cluster.

The earlier 16/20 room-15 panel used an earlier teacher version. This batch tested the latest unselected draft, so its score must not be presented as a controlled comparison with that panel.

Next work is to reproduce representative failures continuously, repair movement and low-health recovery, and pass a newly frozen teacher gate before collecting corrections for a new training experiment. These trajectories remain diagnostic development evidence and are not approved imitation labels. No checkpoint was trained or selected. Existing 20 validation specifications/results remain sealed evaluation evidence; they were not loaded, tuned on, or relabeled.

Evidence: [aggregate report](../reports/room15-overnight-diagnostics-v1.json), [frozen plan](../configs/room15_overnight_diagnostics_v1.json), and `runs/room15-overnight-diagnostics-v1/summary.json`. The aggregate includes complete breakdowns by start and idle offset. Each case retains commands, observations/entities, outcome, replay evidence, and a manifest.
