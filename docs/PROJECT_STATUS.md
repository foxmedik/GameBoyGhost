> **Historical status log.** Current authority: [CURRENT_STATUS.md](CURRENT_STATUS.md), [NEXT_SESSION.md](handoffs/NEXT_SESSION.md), and `configs/handoff_state.json`. The preserved entries below describe different earlier phases and must not override current scope, authorization, gates or blockers.

# Project status — House → Boss Door phase

## Active objective

Open Tail Cave's boss door **at full health**, with sword A / feather B, then stop grounded outside the boss room. Follow the [full-health route and checkpoint plan](HOUSE_TO_BOSS_DOOR_FULL_HEALTH.md) and `configs/house_to_boss_door_v2.json`. Final boss/cello are separate. Full-route teacher qualification and training remain blocked.

New optimization evidence: the feather return reaches room `0x0E` at **24/24**, compared with 8/24 on the prior route, using **578 fewer emulated frames** from the same refill. The direct room-`0x04` jump eliminates the room-`0x05` detour; guarded room-`0x0D` combat clears without damage. This is one development comparison, not a reliability result. The room-`0x0E` guard then timed out without damage. Preferred full-health handoff: `runs/full-health-worm-guard-v1/room0e-full-health-continuation.json`. Furthest overall progression remains the earlier half-heart miniboss arrival below.

## Latest verified progression

**The Nightmare Key is acquired and the guided route reaches Rolling Bones, the miniboss in room `0x11`. The boss door is not open.** The new [route progress report](HOUSE_BOSS_DOOR_ROUTE_PROGRESS.md) records the complete evidence and remaining blockers.

The reusable Nightmare Key controller passes its nominal check but only **1/2 fresh timing checks**, with exact replay for all three. The failed case exposes enemy contact at the room-`0x0E` jump landing. The corrected state-checked room-`0x10` crossing reaches the miniboss alive in one nominal check. These results do not qualify the full-route teacher.

The bounded lower-lane miniboss check preserved half-heart health for all 3,000 frames and reduced enemy health 8→5, but did not clear the room. It failed and is stopped. No training labels or optimizer updates were produced; sealed validation remains untouched.

Preferred fresh miniboss handoff: `runs/tail-cave-room10-state-check-v2/continuation.json`, room `0x11`, `(17,72)`, health 4, Nightmare Key and no Small Keys held, frame 52,180. Earlier damage-free first-bar crossing: `runs/tail-cave-room10-crossing-v4/miniboss-approach-continuation.json`. The full-health feather backup is still `runs/tail-cave-feather-v2/feather-full-health-continuation.json`.

Next: establish a bounded miniboss attack/disengagement controller, then the antechamber and door opening. Repair the earliest route reliability failure before any full-route teacher gate or training. Boss-door endpoint software tests pass; live opening verification is pending.

## Current decision: recovery research closed

Forward game progression now takes priority over further room-15 recovery training. The fixed takeover experiment was stopped without qualification after three primary clears: a serialization bug in its new verifier prevented replay acceptance. No replacement takeover panel, paired integration panel, or additional recovery candidate will run. See [decision and evidence corrections](ROOM15_ARCHITECTURAL_DECISION.md).

The qualified deterministic teacher remains the room-entry progression controller. A supplemental check at new offsets cleared **4/5**, with **3/4 actual half-heart zero-damage clears and 5/5 exact replays**; it failed its gate. Base13/idle313 died and remains an unresolved deterministic progression blocker. The historical 43/43 qualification does not establish reliability at every timing offset.

The earlier full-health, zero-damage room-15 continuation remains preserved at `runs/room15-entry-fallback-check/continuation.json`; onward work has now extended it as described above. Result report for that earlier decision: `reports/room15-takeover-decision-result.json`. Neither milestone is an autonomous promotion.

The sections below are historical milestones and earlier research proposals, not current instructions.

Current selected room-15 teacher: **43/43 continuous gate clears**, including 40 fresh timing cases and three explicit regressions, with **10/10 zero-damage half-heart clears** and 43/43 exact replays. Movement bypass, directional projectile defense, and delayed pickup dialogue recovery are repaired. This is guided control; autonomous model results are unchanged and no new model training has run. See [teacher recovery evidence](ROOM15_TEACHER_RECOVERY.md). The overnight result below describes the earlier draft.

The first room-15 autonomous student is rejected at 13/20 fresh continuous cases and 2/4 half-heart cases, despite 92.95% held-out action agreement. It controlled every room-15 command without fallback. Its seven failures are nonlethal repeated-action stalls and are the source states for the next separate correction collection. See [student v1 evidence](ROOM15_STUDENT_V1.md).

That correction collection is complete: the selected teacher recovered all 7/7 student-created states in continuous exact replay, yielding 1,106 teacher actions. This is approved development evidence for a new frozen correction-data experiment, but not yet training data.

A subsequent fresh demonstration panel cleared 40/40. Its 34 zero-damage runs yielded 13,782 verified teacher-action labels; damaged runs and all diagnostic/gate trajectories were excluded. Freeze the student learning experiment before any training. Data coverage excludes start 18, which had no zero-damage demonstration in that panel.

Latest overnight evidence: the unselected room-15 draft completed 134/400 continuous timing variants, with 126 zero-damage clears, 234 decision-budget failures, and 32 deaths. All 400 attempts replay exactly. This was teacher-only diagnostic collection; no training or autonomous evaluation occurred. The teacher remains unselected. See [overnight diagnostics](ROOM15_OVERNIGHT_DIAGNOSTICS.md) for the current blocker and full results; earlier milestones below remain historical evidence.

The continuous physical house → sword → mushroom → witch → Tarin → Tail Key → Tail Cave → first Small Key route now passes 20/20 varied development starts with exact replay. The selected cave specialist passes its frozen autonomous room-local gate at 18/20, with zero damage in all 18 successes. Reliable full-route deployment uses a state-checked disengagement teacher. Human demonstration recorder work remains shelved.

The cave specialist is learned AI-model behavior in its autonomous room-local evaluation. The 20/20 full-route result is guided behavior and must not be reported as fully autonomous model control. The v5 model disagreed with the recovery teacher on cave decision zero in all 20 cases, so none of its cave proposals executed in that result.

Two larger integration DAgger rounds are preserved as rejected development evidence. They collected 40,796 successful teacher correction rows across 400 timing variants and trained on 48,829 total rows. The first new checkpoint scored 162/200 on held-out offsets 10–19. The second scored 136/200 on the deliberately harsher offsets 20–29 and reached the strongest autonomous continuous result, 17/20, but missed the frozen 18/20 gate. Two subsequent recovery-focused candidates scored 13/20 and 16/20 on fresh full-route panels and were also rejected. The selected autonomous specialist remains v3; reliable execution uses the improved teacher.

The [one-hour varied-start run](PROGRESSION_LONGRUN_HOUR.md) finished:235 cases, all exact replays, but0/20 house development and0/20 house validation successes. The unperturbed control still passes. Development-only repairs replaced the recorded-prefix handoff with state checks and recovery. The selected [state-driven teacher](STATE_DRIVEN_TEACHER_V1.md) now passes 18/20 development starts. The prior 20 validation specifications/results remain sealed evaluation evidence.

## Current evidence

| Milestone | Verified evidence | Limit |
| --- | --- | --- |
| Forest prefix | Original 2,349 decisions reproduce exactly, with zero damage/healing | Known scripted/learned development prefix |
| Toadstool acquired | `reports/progression-toadstool-v1.json`: 2,912 decisions, 17,331 frames, both outbound pushes verified, latch observed, exact independent replay | Eight raw health units lost; final health 16 |
| Return to forest with mushroom | `reports/progression-witch-approach-v4.json`: 3,143 decisions, 18,659 frames, three return pushes verified and cave exited to room 62 | Twelve total health units lost; final health 12; exact independent replay |
| Witch exchange | `reports/progression-witch-exchange-v12.json`: 3,696 decisions, 23,053 frames, mushroom consumed and 32 powder received; receipt dialogue closed | Sixteen total health units lost; final health 8; exact independent replay |
| Tarin cure | `reports/progression-tarin-v3.json`: 4,302 decisions, 28,405 frames, observed DB48 0→1, dialogue closed after settling | Twenty total health units lost; final health 4, powder 24; exact independent replay |
| Tail Key acquired | `reports/progression-tail-key-v2.json`: 4,404 decisions, 30,229 frames, DB11 0→1, chest opened, dialogue closed | No additional damage after Tarin; final health 4, powder 24; exact independent replay |
| Tail Cave unlocked and entered | `reports/progression-tail-cave-v12.json`: 5,192 decisions, 33,991 frames, opened bit observed, settled indoor entrance alive, exact replay | Total damage20/healing16; final health20, powder24; single scripted development proof |
| First Tail Cave Small Key | `reports/tail-cave-first-key-v1.json`: specialist 18/20 autonomously; guided continuous route 20/20 with exact replay | Every guided cave run transferred to the teacher at decision zero; 19/20 cave segments took zero damage |

Every run above starts from the supplied house state and reconstructs the full prefix through physical actions. No intermediate state load, inventory write, runtime human rescue, optimizer update or reserved evaluation use occurred. The supplied house state already has a shield; this is not a power-on completion claim.

The toadstool, return, witch, Tarin, Tail Key and Tail Cave traversal still combine learned local policies with state-checked physical teachers. The room `0x16` specialist is a 39-input MLP trained on 8,033 verified development actions. Its autonomous result is limited to the frozen room-local panel. The continuous 20/20 result uses teacher control for the cave fight in every case.

## What changed

Exact emulator-frame input events now use the progression environment's frame accounting and journal. The old video-only route is preserved; the new runner records commands, health/events, fingerprints, manifests and independent action replay. A bounded room-local block planner treats A7 as movable and the resulting A6 as immovable, validating source and destination objects after each actual push. Physical doorway approaches verify resulting room transitions.

See [state-driven teacher evidence](STATE_DRIVEN_TEACHER_V1.md) for the repaired reliability baseline, [Tail Cave entry evidence](PROGRESSION_TAIL_CAVE_ENTRY.md) for the original complete quest proof, and the linked milestone reports for the preceding steps. The whole-quest selected policies are unchanged. The [project audit](PROJECT_AUDIT_2026-09-11.md) explains why recorder work was shelved.

## Next bounded work

The timing-sensitive prefix is gone. Stage contracts report wrong-room blockers precisely, the title dialogue is handled wherever it begins in the entrance corridor, and the guided first-key route clears its 18/20 development gate at 20/20. The route now has a continuous exact-replay proof through clearing room `0x15`, but the new teacher reaches only 16/20 on the frozen development panel. Autonomous cave control remains below its full-route gate and should stay a separate research track.

Preserve the full exact-replay proof, earlier zero-damage forest regression, and failed attempts. The reliable-teacher gate is met. The first three offline-imitation candidates remain rejected evidence. After strategy review, the bounded DAgger block used 640 learner decisions and 190 verified correction labels; its teacher passed 20/20, learned local skill passed 20/20, and following interaction passed 10/10. Full-teacher integration then passed 16/20, with four downstream combat deaths after timing changed. No sealed validation data was loaded. Keep the learned crossing disabled in the whole teacher and establish recovery from those downstream states before another integration candidate.

## Authority

The current focus is `configs/research_focus.json`; the active phase is `configs/house_to_boss_door_v2.json` and the [full-health plan](HOUSE_TO_BOSS_DOOR_FULL_HEALTH.md). The old `configs/progression_protocol_v1.json` and [PROGRESSION_EXECUTION_PLAN.md](PROGRESSION_EXECUTION_PLAN.md) are preserved historical scope and gates. Historical handoff and route notes must not override the active plan.
# 2026-09-12 downstream recovery update

The learned mushroom crossing is now integrated with a bounded, state-checked downstream controller. A frozen 20-case teacher collection passed 20/20 with 2,014 exact-replay correction decisions; the frozen model then passed 20/20 unseen local development cases without fallback. Full quest development in `runs/state-driven-teacher-downstream-development-v3` passed 20/20 through sword, mushroom, witch exchange, Tarin, Tail Key, and settled Tail Cave entry with exact replay.

The full integration uses the model for the first 16 decisions in room 0x52 north on the witch leg, room 0x54 north on the Tarin return, and room 0x52 south on the Tarin return. It then hands off explicitly to a shielded teacher that checks the current room and inventory contract, replans from live terrain, and sidesteps entities blocking the next movement vector. The recovery is bounded to 512 decisions inside the existing 2,048-decision stage budget. Four successful development cases reached Tail Cave with only 4 raw health, so in-cave survival is still a separate development concern.

The existing 20 validation specifications and results remain sealed evaluation evidence. They were not loaded, tuned on, or relabeled as development data.

# 2026-09-12 first Small Key update

The first generic cave candidate failed at 4/20 recovery-assisted completions, and its first-divergence retrain reached 5/20 autonomously. A frozen specialist experiment replaced the generic navigation representation with explicit player, Hardhat, target-stance, key-drop, health, key-count, and four-command-history features. Its final checkpoint reached 99.44% offline movement and button accuracy, then passed the frozen autonomous development gate at 18/20. All 18 successes took zero damage, including all four half-heart starts.

Continuous integration first exposed a delayed Tail Cave title dialogue and then passed 14/20 without combat guarding. The entrance now checks for dialogue throughout the corridor. With pre-action teacher checking and explicit takeover, the final continuous development panel passes 19/20 from the supplied house state through the first dungeon Small Key, with 20/20 exact replays and zero cave damage in every success. The model's safe prefix ranges from 0 to 103 decisions; teacher recovery occurs in all 20 cases.

The follow-up integration DAgger work used only development routes. A 200-case offsets 0–9 teacher panel produced 21,086 successful correction rows; its checkpoint scored 162/200 on frozen offsets 10–19, below the 180 gate. Those failed cases then became development input: a second 200-case teacher panel produced 19,710 more successful rows. The final-epoch v5 checkpoint trained on 48,829 rows and scored 136/200 on the already-frozen offsets 20–29. It then completed 17/20 full physical house-to-key routes without a cave teacher. This is a real model-only improvement over the earlier 14/20 integration result, but it is rejected selection evidence because it remains below 18/20. The 20 existing validation specifications and results stayed sealed throughout.

# 2026-09-12 disengagement recovery update

Exact continuous branching reproduced the six cave deaths without save/load timing changes. The prior teacher recovered 9/15 branch cases. The revised teacher explicitly recognizes the lower-right pin, holds the shield while moving left, and then resumes state-derived combat. It passed all 9/9 exact failure branches and the complete 20/20 physical house-to-key development panel with exact replay.

The two recovery imitation experiments remain rejected: v10 passed 13/20 and balanced v11 passed 16/20 on fresh full-route development panels. The strongest autonomous continuous score is still v5 at 17/20. In the reliable 20/20 guided run, v5 disagreed at cave decision zero every time and the teacher took over before that action executed. The existing 20 validation specifications and results remain sealed evaluation evidence and were not loaded, tuned on, or relabeled.

# 2026-09-12 room 0x15 update

The continuous route has now entered room `0x15` after collecting the first Small Key and cleared all four Hiding Zols in one exact-replay smoke case. A frozen 20-case development panel then scored 16/20. An incidental combat-pickup dialogue caused the first observed timeout and is now handled explicitly.

The four remaining failures are cases 11, 12, 13, and 15. Each enters the room with four raw health. Live entity evidence identifies the collision: the right fire statue sends projectile type `0x7D` through the lane where the two right Hiding Zols emerge together, and one hit is lethal. Projectile shielding and a route around the chest plinth work after a development-only state reload, but the same draft recovery scored 0/4 in continuous replay because encounter timing differs. The room-15 teacher is therefore not selected, and no training is authorized from it yet. See `reports/tail-cave-compass-room-v1.json`.
