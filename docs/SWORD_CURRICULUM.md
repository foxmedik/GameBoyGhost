# Sword curriculum and map correction

The six-run overnight comparison finished with four full 524,288-step candidates and two transition failures. None of its 16 final evaluation episodes acquired a sword. The failed state was gameplay 7, subtype 5: the interactive world map, not a loading screen.

## Map input

`WorldMapInteractiveHandler` in the byte-matched disassembly accepts joypad input at gameplay 7/subtype 5. The controller now delivers policy-selected buttons in that phase. It retains the stable-world gate for room transitions, and does not commit a new room while viewing the map. It does not automatically dismiss the map or edit RAM. The real-ROM regression opens the map with Select and exits with B. Other unsupported modes still fail explicitly at the bounded timeout.

## Curriculum starts

`scripts/build_sword_curriculum.py` replays the existing physical-button fixture to produce two starts under `runs/sword-curriculum-v1`:

- `sword_approach.state`: frame 7,823, room F2, health 8, owl dialogue already completed, before approaching/picking up the sword.
- `beach_route.state`: frame 5,039, room E1, health 12, farther back along the route.

Both start with sword level zero and no sword in inventory. Health and items are inherited from gameplay; no RAM edits, healing, or item grants create these starts. The manifest includes source-state, sequence, and resulting state hashes. These are scripted curriculum starts and must not be reported as learned house-to-sword routes. A regression confirms 1,000 idle frames do not award the sword, then verifies the physical fixture suffix reaches it.

## Focused training

`--sword-curriculum` keeps the existing assisted structured observations/actions but replaces the scalar training reward with +10 for sword acquisition, -1 for death, and -0.001 otherwise. A pure read of `wSwordLevel` (DB4E) detects acquisition. Success ends the curriculum episode and is recorded separately from death; full-game completion remains unevaluated. Baseline reward components remain available in environment info. The first pilot uses only the close approach start, not an automatic multistage schedule.

```sh
.venv-ladx/bin/python scripts/train_ladx.py --steps 32768 \
  --initial-state runs/sword-curriculum-v1/sword_approach.state \
  --sword-curriculum --checkpoint-every 8192
```

The earlier beach start is prepared for a subsequent harder experiment after checking the close-start policy. No larger unattended batch is launched automatically by this pilot.

The new curriculum mode and initial state are saved in full checkpoints and restored before episode replay. The existing source-hash compatibility gate intentionally rejects older checkpoints against changed environment code; no silent migration or weight promotion is performed.

Evaluation disables learning and uses one deterministic episode plus three fixed stochastic seeds from the checkpoint's initial state. `scripts/overnight_batch.py --untrained` creates a fresh seed-0 policy of the same architecture as a control. This small fixed-start evaluation is a diagnostic, not a generalization benchmark. Learned house-start performance remains an open requirement.

## Verified pilot results

Pilot: `runs/cdd6659b-d37c-4ffd-ae18-acb0577da0da`, 32,768 steps, 364 completed episodes, 335 sword successes, 29 deaths. All 256 shard hashes and 32,768 contiguous row indices validate; every success is terminal. Recomputing the 8,192-step suffix from checkpoint 8,192 exactly matches checkpoint 16,384 in environment, policy tensors, and optimizer.

Final evaluation versus fresh seed-0 policy, both from the identical close start:

| Policy | Deterministic success | Stochastic successes | Successful episode lengths |
| --- | --- | --- | --- |
| Untrained | 0/1 | 3/3 | 96, 135, 84 steps |
| Trained 32,768 | 0/1 | 3/3 | 85, 84, 83 steps |

Both deterministic evaluations timed out after 2,048 steps. The trained stochastic samples were faster, but these four episodes do not establish a reliable learned controller or improved success rate. No house-start progress is established, and no model has been promoted. A harder-start experiment and broader evaluation remain necessary before scaling again.

The map regression also reruns seed 2 with the original 524,288-step horizon, stopping at 12,288: `runs/a39f0099-a81e-4318-9120-ad10d7c673bb`. Its first 11,904 recorded actions, observation hashes, rewards, and phases exactly match the failed run. It then passes the former failure point and records seven interactive-map policy steps. The original failed artifacts remain untouched.

Validation: the 19 existing tests passed, plus the new real map regression (after correcting the test's Select pulse duration) and the new curriculum reachability/idle/success regression. No large background training remains active.
