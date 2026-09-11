# Selected house-to-sword controller

The selected learned controller acquires the sword deterministically from the supplied house savestate. It passed **70/70 evaluated start cases**: 58 development cases and 12 separately reserved validation cases. Evaluations use only the learned policy; no teacher or scripted route drives evaluation actions.

This is a demonstration-trained, LADX-specific controller in the existing privilege-D harness. The initial house savestate already has a shield. Full-game completion, new-game-to-credits performance, and generalization to other games remain unevaluated.

## Results

| Start | Development | Reserved validation | Total |
| --- | --- | --- | --- |
| Original house | 22/22 | 4/4 | 26/26 |
| Earlier beach state | 18/18 | 4/4 | 22/22 |
| Close sword approach | 18/18 | 4/4 | 22/22 |
| All starts | 58/58 | 12/12 | 70/70 |

Cases vary the physical startup actions and waiting time. These are fixed-ROM, fixed-savestate perturbation tests, not independent samples of different games or a statistical guarantee. Earlier stress cases were explicitly folded into corrective training; only the final 12-case validation set was reserved from that correction data.

The normal house run takes 412 policy actions in the selected standalone runner. Model/data hashes and per-case action traces accompany the results. The earlier PPO-only and initial imitation models remain preserved as comparisons; no previous raw outputs were overwritten.

## Why this version works

A successful stochastic policy episode supplied an initial route. Feedback-scripted teachers added recovery demonstrations, using ordinary physical actions without RAM edits by the teacher. Subsequent debugging removed incidental detours from that route and fixed specific house-furniture and forest-exit alignment cases.

The final teacher completed all 58 development setups. Its 15,763 labeled observations contain no conflicting labels under the selected compact input representation. A deterministic CART-style decision tree learned the action decisions; it matches all 15,763 training labels and passes the separate live evaluations above. Offline label matching is reported separately from gameplay success.

The selected input representation contains precise pixel position, dialogue state, previous button, and map coordinates from the existing structured observations. Previous movement, health, and moving-enemy details were excluded from this final fit after comparisons exposed less stable behavior. The tree does not call the teacher or follow an explicit waypoint list at inference. Its learned thresholds and leaves are serialized in a small JSON policy.

This controller is a successful specialized baseline. It does not replace the canonical planner/controller architecture, neutral harness, SB3/PufferLib comparisons, final completion detector, or broader-game evaluation requirements.

## Run it

From the project root, with the installed environment and local verified ROM:

```sh
.venv-ladx/bin/python scripts/run_sword_controller.py
```

`configs/sword_controller.json` selects the policy by path and SHA-256. Each invocation creates a fresh run directory, records labeled action/reward/phase rows, saves the final screenshot, and writes a checkpoint. The runner stops on sword acquisition, death, or its bounded action budget.

Other prepared starts:

```sh
.venv-ladx/bin/python scripts/run_sword_controller.py --start beach
.venv-ladx/bin/python scripts/run_sword_controller.py --start approach
```

Pause and resume a run:

```sh
.venv-ladx/bin/python scripts/run_sword_controller.py --stop-after 200
# Use the checkpoint path in that new run directory:
.venv-ladx/bin/python scripts/run_sword_controller.py --resume runs/RUN_ID/checkpoint-000200
```

## Checkpoints and validation

The tree runner saves the policy JSON, starting/emulator states, Python environment state, full episode action prefix, run/episode/producer provenance, and an integrity manifest. Restore checks local artifacts, source hashes, dependencies, and ROM identity before loading trusted local state. It reconstructs the episode with physical action replay and verifies its framebuffer/work-RAM/observation fingerprint. The deterministic tree has no optimizer or policy RNG.

The selected controller was tested uninterrupted and with a pause at step 200. Resumption reproduces the entire final action sequence and environment fingerprint exactly. The current run format gives a resumed producer a fresh run ID while retaining episode identity and checkpoint ancestry.

The existing 25-test suite passes, including the new supervised-optimizer resume and tree input/boundary tests. The supervised learner also saves policy/optimizer/shuffle/Torch state after whole epochs; its resume test matches uninterrupted model and optimizer values and rejects corrupted artifacts.

## Artifacts

- Selection: `configs/sword_controller.json`.
- Policy and final successful demonstration dataset: `runs/tree-clean-route-v3`.
- Development results: `runs/tree-final-development-28`, `runs/tree-final-development-18`, `runs/tree-final-development-12`.
- Reserved validation: `runs/tree-final-validation-12`.
- Final standalone/replay checks: `runs/sword-controller-final-full`, `runs/sword-controller-final-pause`, `runs/sword-controller-final-resume`.
- Historical experiment discussion: `docs/IMITATION_EXPERIMENT.md`.

The next game milestone is the route toward Tail Cave. Sword acquisition is now a usable learned prerequisite for that work. The [skill chain](SKILL_CHAIN.md) now hands off from this controller to bounded exploration in the same episode, with verified resume across the handoff.
