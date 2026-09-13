# Room 15 recovery experiment report

**Superseded interpretation:** Read `ROOM15_ARCHITECTURAL_DECISION.md` before using the conclusions below. The first-trigger cases named half-heart actually had eight health units, while the project's half-heart criterion is four. The eight source cases were reused for training; the later 6/8 and 5/8 probes did not implement replay verification or the promised post-escape gate. Early-versus-terminal comparisons are not controlled causal evidence. Mid-room recovery research is now closed; the qualified deterministic room-entry teacher is the progression path. The historical text below is preserved for audit.

## Scope

This report covers the learned controller for Tail Cave room `0x15` after the first Small Key. The completion contract is: enter room 15 alive, clear all four Gel/Zol enemies, remain in room 15 alive, and independently replay every physical input trace exactly.

The sealed 20-case validation evidence was not loaded for any collection, training, or selection in this work. It remains evaluation-only. All panels described below are development panels with separate, frozen configurations.

## Control terminology

| Label | Meaning |
| --- | --- |
| Autonomous | The learned room-15 policy selected every room-15 action. There was no teacher fallback. |
| Guided | The learned V4 policy acted normally, but a state-checked recovery controller could inject bounded left-and-shield actions after an early y=80 plateau. Guided results are not autonomous performance. |
| Teacher | A state-checked hand-written controller acted continuously. Teacher clears are training-source and diagnostic evidence, not learned-policy evidence. |
| Exact replay | A fresh emulator replay reproduced every recorded command, state fingerprint, observation, frame count, events, and final journal. |

## Experiment history

| Version | Change | Autonomous result | Decision |
| --- | --- | --- | --- |
| V1 | Clean teacher demonstrations | 13/20 clears; 2/4 half-heart | Rejected |
| V2 | Naively mixed broad correction data | 7/20; 2/4 half-heart | Rejected; recovery behavior displaced nominal combat |
| V3 | Added recent intended direction and observed displacement | 14/20; 3/4 half-heart; 20/20 exact replay | Rejected; awareness improved but post-detection action did not |
| V4 | Added a physical 120-frame wait action and 204 bounded recovery labels, lightly sampled and loss-weighted | 15/20; 3/4 half-heart; 20/20 exact replay | Rejected by frozen 18/20 and 4/4 gate |

V4 is a meaningful rejected milestone: it expanded the action vocabulary without destroying nominal imitation, but it did not meet the precommitted reliability bar.

## V4 protocol and result

The V4 training set contained 7,794 rows: 7,590 clean rows and 204 bounded recovery rows. Recovery rows were sampled into 8% of updates and given a 0.25 loss weight. The nominal development split held 6,158 rows and contained zero recovery rows. The final-epoch candidate reached 93.3% nominal held-out agreement.

The first V4 gate at offsets 86–105 is invalidated. Its evaluator attempted to submit the new 120-frame wait macro through a short-action interface and rejected it before physical execution. Those results are not performance evidence.

The corrected V4 gate used 20 new offsets, 106–125. It produced:

| Metric | Result | Required |
| --- | ---: | ---: |
| Autonomous clears | 15/20 | 18/20 |
| Half-heart clears | 3/4 | 4/4 |
| Exact replays | 20/20 | 20/20 |
| Candidate selection | Rejected | Gate pass |

The five failed cases all reached the decision budget alive. Four were stationary y=80 loops; the fifth was a lower-room combat/route stall. There were no deaths among those five. This changed the diagnosis from survivability to recovery-policy execution.

Primary evidence: [V4 corrected gate summary](../runs/room15-student-v4-gate-v2/summary.json).

## Guided early-recovery diagnostic

The V5 early controller watched the live room state. At y=80–84 after a stationary plateau it issued a bounded left-and-shield bypass. This was explicitly guided behavior, not autonomous policy.

A 30-minute development batch completed 78 episodes:

| Metric | Result |
| --- | ---: |
| Guided clears | 43/78 (55.1%) |
| Exact replays | 78/78 |
| Guided interventions | 254 |
| Episodes with at least one intervention | 54/78 |
| First-trigger clears | 29/54 |
| First-trigger stalled again | 22/54 |
| First-trigger deaths | 3/54 |

The trigger is active in the right failure neighbourhood, but the fixed recovery sequence is weak. It can repeat without rejoining a productive combat route. Trigger timing alone is therefore not the missing capability.

Primary evidence: [guided 30-minute batch summary](../runs/room15-v5-guided-30m/summary.json).

## Terminal-versus-early recovery finding

Teacher recovery was tested from the five V4 terminal states after the 700-decision budget had already been exhausted:

| Starting state class | Teacher result |
| --- | --- |
| Wait-cycle stall | Recovered |
| Lower-route stall | Recovered |
| Three y=80 stalls, including a half-heart state | Did not recover before teacher budget/death |

Result: 2/5 exact terminal-state recoveries. By contrast, the teacher was tested from eight representative **first-trigger** states, before the guided controller applied any action:

| First-trigger branch set | Clears | Exact replays | Half-heart branches |
| --- | ---: | ---: | ---: |
| y=80, y=83–84, successful and stalled guided examples | 8/8 | 8/8 | 2/2 |

This is the central causal result: recovery must begin at the first sustained trigger state. Waiting for the policy to exhaust its budget makes several y=80 states unrecoverable even for the teacher.

Primary evidence: [terminal-state audit](../runs/room15-v5-terminal-stall-spans/summary.json) and [first-trigger teacher spans](../runs/room15-v5-first-trigger-teacher-spans/summary.json).

## Current V5 plan

V5 is frozen as a **separate recovery skill**, rather than another indiscriminate broad-policy augmentation. Its input states begin immediately at the first state-checked y=80/y83/y84 trigger. Its trajectories end once Link has moved at least 16 Manhattan pixels from the trigger state; the full teacher clear remains outcome evidence rather than label volume.

The recovery skill must first pass an 8/8 exact first-trigger recovery gate. Only then may a separate, frozen integration experiment test whether an autonomous policy can invoke the skill without degrading nominal combat. No V5 training or integration has begun.

Plan: [room15_student_v5_recovery_skill.json](../configs/room15_student_v5_recovery_skill.json).

## Promotion criteria for V5

### Standalone recovery-skill gate

The learned `RECOVER_FROM_BLOCKED_STATE` skill must recover all eight frozen first-trigger states. Each result must exactly replay, remain alive, include both half-heart branches, move at least 16 Manhattan pixels from the trigger, leave the original blocked region, and avoid returning to the same stationary y=80/y=83/y=84 condition within 48 post-escape decisions. The gate records escape decisions, frames, damage, first teacher-direction agreement, terminal productivity, and immediate re-stall.

### Autonomous integration gate

Only after the standalone skill passes may a separate integration experiment be frozen. It must use a fresh 20-case development panel and satisfy all of the following: at least 18/20 autonomous room clears, all 4/4 half-heart clears, 20/20 exact replays, and zero teacher fallback. The sealed validation panel remains untouched until then.

## What is established

1. Temporal intent/outcome features improved recognition of recovery-relevant context.
2. A real physical wait macro can be represented and exactly replayed.
3. The remaining dominant failure mode is escaping/replanning after the trigger, not initial low-health survival.
4. A first-trigger teacher can recover representative y=80 and low-health states reliably; terminal recovery is too late for several of them.
5. No learned candidate currently satisfies the autonomous room-15 selection gate.

## Next decision

Build the recovery-skill extractor and its standalone gate from the eight verified first-trigger spans. Do not add more generic demonstrations, tune on sealed validation, or select a model until the separate recovery skill and a fresh autonomous integration gate both pass.
