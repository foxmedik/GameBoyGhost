# Phase aware training and verified resume

The requested transition controller, remaining combat fixtures, checkpoint/resume path, and longer pilot run are implemented and verified for the current single-environment CPU baseline. All 18 integration tests pass.

## Transition handling

`src/gameboy_agent/training_env.py` adds a separate phase-aware training environment. The earlier reproduction and neutral runners remain available for comparison.

Readiness follows the matched English 1.1 `ReadJoypadState` logic: world gameplay, interactive subtype 7, no room scroll, transition sequence 4, and no palette transition. `transitions.py` additionally requires eight consecutive ready frames with a consistent room identity after a transition. This bridges the transient idle gap in the captured house exit.

Each policy action gets ten usable frames. Controls are released during waits; remaining action frames are delivered after readiness returns. The controller waits one frame at a time instead of advancing fixed 40/60-frame chunks, and publishes a committed room identity only after stability. A 600-frame wait budget raises an explicit `TransitionTimeout`; it never claims completion or silently converts a failed transition to an ordinary episode ending. Death can stop an action before its full budget is delivered.

A real house-exit/scroll regression confirms complete action budgets and stable returned phases. Synthetic tests exercise transient idle gaps and bounded failure. This is verified on the current gameplay fixtures, not every dungeon, cutscene, menu, or ending. Unsupported longer transitions should produce a diagnostic failure to investigate.

Training retains upstream progression observations/rewards and item/inventory assistance, labeled privilege D. The neutral environment continues to use only physical controls, framebuffer observations, and zero reward. The new training environment also consumes push events once without registering hooks from a reward getter.

## Combat fixture coverage

`configs/fixtures/house_to_sword_and_push.json` records **9,474 frames** of scripted physical controls from the original house savestate. The route was developed interactively, including a bounded search over button sequences. No gameplay RAM edits or item grants were used in fixture capture. The existing shield in the supplied starting savestate is disclosed.

The fixture acquires the sword through the game and exercises all four corrected hooks:

| Hook | Raw executions |
| --- | ---: |
| Solid collision | 3,793 |
| Shield projectile block | 2 |
| Urchin push | 240 |
| Sword damage | 1 |

Repeated executions are not distinct combat events or kills. The sword hook executes at frame 9,161. Two complete hooked replays match exactly; all recorded gameplay state and framebuffers also match an unhooked run. Expected hashes, inventory changes, and counts accompany the controls. Screenshots at sword/shield events were inspected.

The fixtures are scripted regression data, kept separate from autonomous training shards. They do not establish learned sword acquisition or autonomous completion.

## Checkpoints and restore

`src/gameboy_agent/checkpoint.py` publishes checkpoints after a complete PPO optimizer update. The runner does not checkpoint partial rollouts. Each checkpoint directory contains:

| Artifact | Saved state |
| --- | --- |
| `policy.zip` | SB3 policy, optimizer, counters, last observation, and algorithm configuration |
| `emulator.state` | Emulator snapshot for inspection and provenance |
| `initial.state` | Starting state required to reconstruct the current episode |
| `environment.pkl` | Observation/world-memory arrays, visited sets, reward bookkeeping, transition tracker, control history, spaces/RNGs, cached observation, and other Python environment state |
| `rng.pkl` | Python, NumPy, and Torch CPU random states |
| `vector.pkl` | Single-environment vector wrapper buffers and reset state |
| `experiment.json` | Curriculum, episode IDs/counters, complete shard lineage and next row index, planned horizon, run/producer IDs, and progress metrics |
| `manifest.json` | Artifact/source hashes, versions, ROM identity, thread count, boundary, and expected environment fingerprint |

The manifest is written last. Restore verifies artifact hashes, code hashes, dependency versions, and ROM identity before loading trusted local pickle artifacts. Checkpoints from untrusted sources must not be deserialized.

PyBoy 2.0 direct reload did not consistently restore framebuffer behavior in earlier testing. Restore therefore creates a new environment and deterministically replays the current episode, compares framebuffer/work-RAM/cached-observation fingerprints, then restores saved Python state, vector buffers, model/optimizer, and RNGs. The emulator snapshot remains a separately recorded artifact; it is not falsely presented as sufficient on its own. Replay cost grows with current episode length.

This covers all active state in the current single-environment CPU experiment. No planner is active (`planner: null`), and curriculum is the fixed upstream savestate. Future multi-environment learners, planners, new curricula, or data formats need corresponding checkpoint contracts. Portable artifact relocation and checkpoint migration across changed code/dependencies are not implemented. Parent shard paths must remain accessible.

## Longer pilot result

The pilot planned 32,768 steps with 2,048-step episode limits. It stopped at 16,384, then resumed in a separate process to the original target while preserving the learning horizon.

| Metric | Result |
| --- | ---: |
| Policy/environment steps | 32,768 |
| Bounded episodes | 16 |
| Distinct decoded room identities | 15 |
| Recorded deaths | 0 |
| Action-loop emulator frames | 355,371 |
| Transition wait frames included above | 27,691 |
| Invalid/unstable returned phases | 0 |
| Immutable diagnostic shards | 256 |
| Training-loop wall time across both processes | About 187 seconds |

Frame totals exclude reset settling and checkpoint reconstruction. This short CPU pilot is not a scaling benchmark. Episode progress remained at the starting aggregate value in the last episode; the run does not establish Dungeon 1 completion or learned sword acquisition. Completion remains explicitly unevaluated.

First process: `runs/46cd8efe-da6f-41ec-ac60-cf02f754e064`.

Resumed process and final checkpoint: `runs/7f60bad5-5b8d-47a8-a384-07ea742b48cf/checkpoints/000032768`.

Results and evidence in the resumed run:

- `result.json`: progress, parent lineage, curriculum, and shard records.
- `data-verification.json`: all shard hashes valid; exactly 32,768 contiguous indices, 16 episode IDs, and no gaps/duplicates. Float32 scalar rewards match summed components within approximately 1.4e-8.
- `resume-verification.json`: replaying the final 2,048 training steps from checkpoint 30,720 reproduces the final environment fingerprint, policy tensors, and optimizer state exactly.

The unit resume regression also crosses an episode reset and compares uninterrupted versus restored training. Integrity corruption is rejected. These are stronger checks than merely reloading a model for inference.

The training shards are explicitly versioned JSONL diagnostic records with hashes, action/reward/timing/state metadata, and provenance. They are not yet the canonical Parquet training corpus with all heavy observations; that remains a separate dataset milestone. Run/source identity uses UUIDs and source hashes; the project root still has no Git history.

## Commands

Run from the project root using the installed baseline environment:

```bash
# Full regression suite (local ROM required)
.venv-ladx/bin/python -m unittest discover -s tests -v

# New bounded pilot
.venv-ladx/bin/python scripts/train_ladx.py --steps 32768

# Planned pause without changing the eventual training horizon
.venv-ladx/bin/python scripts/train_ladx.py --steps 32768 --stop-after 16384

# Resume the saved run; use the checkpoint path printed by that process
.venv-ladx/bin/python scripts/train_ladx.py --resume runs/RUN_ID/checkpoints/000016384
```

Resume retains the saved target; requesting a different `--steps` value is rejected. It creates a new producer run directory with parent checkpoint/shard lineage and does not overwrite the previous run. Each shard is created exclusively and flushed before inclusion in a checkpoint. Unreferenced shards from work beyond an older checkpoint are not silently joined into a resumed branch.

To reproduce the production suffix verification (choose a new output filename):

```bash
.venv-ladx/bin/python scripts/verify_resume.py \
  runs/7f60bad5-5b8d-47a8-a384-07ea742b48cf/checkpoints/000030720 \
  runs/7f60bad5-5b8d-47a8-a384-07ea742b48cf/checkpoints/000032768 \
  --output runs/new-resume-verification.json
```

The next useful experiments are canonical trajectory storage and controlled curriculum/longer training comparisons. Completion detection, broader transition coverage, multi-environment/PufferLib comparisons, and the planner remain open canonical requirements.
