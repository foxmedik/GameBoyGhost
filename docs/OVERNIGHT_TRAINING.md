# Overnight training batch

The UI is deferred. This batch compares PPO entropy coefficients 0.01 and 0.03 over seeds 0, 1, and 2, with 524,288 steps per run (3,145,728 total). All candidates start fresh from the same upstream house savestate with a shield. The previous 32,768-step pilot is preserved. Training uses the existing single-environment CPU harness, four Torch threads, 2,048-step episodes, and unchanged rewards and observations.

Each run saves full resumable checkpoints every 32,768 steps and at its endpoint, plus immutable diagnostic shards every 128 steps. The existing verified source/checkpoint contract is unchanged. The batch stops after eight hours or before starting another candidate if free disk space drops below 20 GiB. An individual failed run is recorded and the next candidate proceeds. The batch does not silently change game logic to bypass failures. A time-limit interruption may leave an incomplete checkpoint directory; only directories containing a valid manifest are usable.

Each completed candidate is evaluated without optimizer updates from the same fixed starting state: one deterministic episode and three stochastic episodes with fixed evaluation seeds. Reports include reward, rooms, death, and read-only sword-level observations (`wSwordLevel`, DB4E in the matched ROM). This is an assisted, fixed-start comparison, not a full-game completion or generalization benchmark. No policy is automatically promoted based only on shaped reward.

The batch's `status.json` identifies all candidate run directories, commands, checkpoints, evaluations, errors, and launch script hashes. Per-candidate stdout/stderr lives beside it. A macOS `caffeinate -i` assertion prevents idle system sleep while the batch runs; the display may sleep. Closing the app does not intentionally terminate the detached process; shutdown or logout can interrupt it.

Launch:

```sh
.venv-ladx/bin/python scripts/overnight_batch.py --directory runs/NEW_BATCH_NAME
```

Resume an interrupted candidate from its last complete checkpoint:

```sh
.venv-ladx/bin/python scripts/train_ladx.py --resume runs/RUN_ID/checkpoints/STEP --checkpoint-every 32768
```

Resume uses the entropy coefficient saved inside the model and preserves the original planned training horizon. The checkpoint interval only controls future save frequency.

Validation before the overnight launch: two 256-step smoke candidates completed training, full checkpoint restore, and all four short evaluation episodes each. The existing regression suite is also run before launch.

## First batch stopped and replaced

The first overnight candidate reached approximately 396,000 steps, but its log exposed repeated PyBoy callback exceptions while removing the push breakpoint from inside its own callback. The batch was stopped, and all original logs/shards/checkpoints retained under `runs/overnight-20260910-082811`. Its results are marked invalid for comparison.

The hook now only sets a boolean during callback execution. Removal happens after emulator ticking returns, preserving one boolean push event per action. A real 9,474-frame sword/push fixture regression exercises repeated registration and removal. The batch supervisor now terminates and records candidates when runtime tracebacks appear, including exceptions swallowed by the emulator.

This source correction intentionally makes the old checkpoints fail the existing code-hash compatibility check. The replacement batch starts fresh; old checkpoints are not silently migrated. `runs/latest-overnight.json` points to the replacement launch.
