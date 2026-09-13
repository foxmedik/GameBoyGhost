# State-driven progression teacher v1

The selected teacher reaches settled Tail Cave entry alive in **18 of 20 development house starts**. This meets the preregistered reliable-teacher gate. Every one of the 20 physical traces, including both failures, independently replays its actions, state, frames, event journal, and final outcome exactly.

This is a scripted state-driven teacher. It is not a newly trained quest model. It uses the already selected learned sword controller and selected navigation policy where declared, while quest stages, interactions, route targets, checks, and recovery remain explicit code.

## What changed

The earlier baseline replayed a timing-sensitive recorded command prefix before invoking quest traversal. Small startup changes could leave Link in the wrong room, after which route code indexed a nonexistent room delta and raised a `KeyError`. The replacement advances from observed state:

- Each quest stage checks the exact expected room, alive/settled mode, inventory, and prerequisite flags before traversal.
- Transitions release controls, settle for a bounded number of physical frames, and then recheck the stage.
- Nonadjacent, wrapped, indoor, and wrong-room routes raise `StageBlocked` with expected and observed state.
- Forest guidance follows verified spatial observations while checking current position and room. It does not replay the old command tape.
- Mushroom pickup observes the live pickup latch instead of assuming it appears after a fixed four-frame input.
- Room-local approach checks terrain and verifies the actual room crossing.
- Bounded aimed sword responses and lateral recovery address the room `0x52` and `0x42` movement/combat bottlenecks.

The development component panels measured sword at 20/20, forest at 18/20, mushroom at 18/20, and the witch chain at 18/20. Three frozen full-teacher candidates were then evaluated. Candidate v3 passed at 18/20; the remaining failures are combat deaths in rooms `0x52` and `0x42`.

## Selected evidence

The selected run is `runs/state-driven-teacher-development-v3`. It contains 94,754 recorded decisions and 635,596 emulated frames. Successful runs end in indoor Tail Cave room `[1, 0, 23]`; final health ranges from 8 to 24 raw units. Across all 20 runs, raw damage is 356 and raw healing is 172. The exact aggregate is in `reports/state-driven-teacher-v1.json`.

The run froze every relevant runtime source and both selected policy hashes before dispatch, checked them before each case, and verified them again after completion. The teacher checkpoint passed 119/119 tests; the current suite, including correction-history tests, passes 122/122.

## Evaluation separation

The 20 validation specifications and completed results from `runs/progression-longrun-hour-v1` remain sealed evaluation evidence. The state-driven teacher runner loads only `development-house-*` specifications. Those validation cases were not used for implementation choices, teacher tuning, model training, or model selection, and they are not relabeled as development data.

## Frozen learning experiment

`configs/progression_local_control_v1.json` freezes the next experiment before any optimizer update. It targets short-horizon movement and combat under explicit planner goals, concentrating on rooms `0x52` and `0x42`. Quest-stage selection and interaction checks remain state-driven. The learner must return a precise failure to recovery on an unexpected room, death, or budget exhaustion.

Only successful, exact-replay teacher trajectories may supply action labels. Four successful cases are fixed as visible learner-development cases; the other fourteen are learner-training sources. The two teacher deaths remain development evidence and are excluded as positive action labels. The sealed 20-case evaluation panel cannot be loaded during extraction, training, candidate selection, or recovery tuning.

The experiment was frozen before training. Replay-time extraction then reconstructed complete entity-aware observations and reverified every source decision, producing 6,895 training rows and 2,037 fixed visible-development rows without loading validation.

Three bounded candidates used the fixed data. Candidate 1 was rejected before live evaluation because it predicted no B/shield actions. Balanced room/button sampling in candidate 2 restored every class but missed the frozen button-accuracy gate. Candidate 3 passed the frozen offline gate at its fixed final epoch with 66.8% movement and 59.9% button accuracy on visible development.

Candidate 3 then failed its frozen live development panel at 3/20. Sixteen cases stalled, one died, and all 20 replayed exactly. Offline action classification did not transfer to closed-loop traversal. The candidate is rejected, the selected runtime policies are unchanged, and the three-candidate cap is reached. The local learning track stops for a strategy review; the 18/20 scripted state-driven teacher remains the progression baseline. Reports are `reports/progression-local-control-v1.json` through `v3.json` and `reports/progression-local-control-v3-live.json`.

The required strategy review opened a new, narrower experiment block. It held the southern exit goal fixed, collected 190 teacher corrections from states created by the rejected learner, added four decisions of action/duration history, and learned duration classes 1/3/10. The recovery teacher passed 20/20. The new model then passed 20/20 unseen local development crossings without recovery and 10/10 continuous crossing→cave→physical mushroom acquisitions, all at full health and with exact replay. It is selected only for the mushroom-stage room `0x52→0x62` skill; whole-quest preservation remains pending. See `reports/progression-dagger-v1.json`.

Full-teacher preservation then scored 16/20, below the required 18/20. All traces replay exactly. The learned crossing and mushroom pickup completed, but changed timing produced three later deaths in room `0x52` and one in `0x54`. The model remains a valid bounded local skill but is disabled in the full teacher. The original 18/20 state-driven teacher remains selected for the whole quest.
