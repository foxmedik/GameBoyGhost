# First learned goal-conditioned navigation experiment

The selected experimental navigator reaches **42/48 local development goals**
with **zero deaths and zero damage**. The existing explorer reaches 11/48; a
simple goal-directed controller reaches 41/48 with no deaths and four raw health
units of damage. The one-case advantage over that strong baseline is small and
does not establish statistical superiority.

The fixed learned sword controller also hands off to this navigator in a
continuous episode. All three prepared starts leave the sword room without
damage, but only the house start reaches the exact requested destination.
The other two stall afterward. The navigator is **experimental**, and does not
replace the default explorer or establish reliable Tail Cave progression.

## Training

The corrected cache contains 346,536 training action examples from 43,317
navigation-candidate segments, plus 41,632 development examples from 5,204
segments. Sampling caps each `(base start, destination room)` group at 1,536
training or 192 development segments. This reduces dominance by common beach
rooms while retaining rare destinations. Each selected 32-action segment supplies
one deterministically varied sample from each four-action block.

Inputs contain structured controller state, inventory/location/health fields,
nearby terrain and entity observations, current/target room encodings, target
pixels, and relative goal features. The network has 250 inputs and two 256-unit
hidden layers, with separate movement and button outputs. It emits ordinary
movement/A/B actions. Training uses hindsight goals from scripted exploration;
these are observed successful segments, not expert or optimal trajectories.

The initial cache sampled every eighth action. This accidentally selected only
the A-press phase of the explorer's alternating button pattern. That cache and
its model are preserved as a diagnostic and excluded from selection. The corrected
cache contains 173,005 release and 173,531 press examples, and uses the same
48 live test specifications frozen before the first optimizer update.

Two models were evaluated:

| Model | Epochs | Offline development movement accuracy | Live goal success |
| --- | ---: | ---: | ---: |
| Includes previous movement | 24 | 89.3% | 10/48 |
| Masks previous movement | 64 | 63.0% | 42/48 |

The first model often persisted in its prior direction. Masking that input forced
greater reliance on current state and the goal. Offline imitation accuracy fell
while actual goal-reaching improved sharply. Previous button remains available
so the controller can learn press/release timing. The final checkpoint was selected
by development loss within the 64-epoch ablation; the architecture/input change
was informed by the first live development result.

## Paired emulator comparison

The 48 local cases are balanced across house/beach/approach base starts and
same-room/cross-room goals, with one case per source episode. Each emulator starts
from its source savestate and replays the exact recorded prefix. Its observation
must match the source at handoff. Paired agents' initial fingerprints match.

All agents get the same target, 128-action budget, and success condition: alive,
in the target room, within eight Manhattan pixels of its target point.
The explorer's movement policy does not use the target; it is checked against
the same stopping condition. The additional greedy baseline moves toward target
pixels, or toward the target overworld room's grid direction, with alternating
sword presses and dialogue dismissal. It has no obstacle-aware path planner.

| Controller | Same-room goals | Cross-room goals | Deaths | Damage units |
| --- | ---: | ---: | ---: | ---: |
| Previous-movement model | 6/24 | 4/24 | 2 | 27 |
| Selected masked-input model | 21/24 | 21/24 | 0 | 0 |
| Existing explorer | 9/24 | 2/24 | 0 | 16 |
| Goal-directed baseline | 21/24 | 20/24 | 0 | 4 |

Unchanged baseline traces are reused for the ablation after checking identical
case definitions/budgets and matching replay fingerprints. These are grouped
development comparisons, not independent held-out benchmark results. The 96
reserved evaluation specifications remain unused. All experiments inherit
privilege-D assistance and the same fixed-ROM limitations.

## Continuous sword-to-navigation handoff

Destination: room `(0, 0, 226)` / `E2`, pixel `(36, 121)`, using a target from
the frozen local development specification. Each run first executes the unchanged
selected sword policy, then switches to the navigator without resetting or
loading a new state. The navigation budget is 384 actions.

| Prepared start | Sword actions | Actions to enter E2 | Exact destination outcome | Navigation damage |
| --- | ---: | ---: | --- | ---: |
| House | 412 | 38 | Reached in 66 navigation actions | 0 |
| Beach | 268 | 38 | Timed out at `(36, 90)` | 0 |
| Approach | 83 | 34 | Timed out at `(39, 90)` | 0 |

The house run totals 478 actions and finishes at `(43, 120)`, exactly eight
Manhattan pixels from the target. Entering E2 means leaving the sword room F2;
it does not mean completing the entire beach region or reaching Tail Cave.
The two endpoint failures remain recorded regression cases for precision and
recovery work. No fallback controller silently completes their route.

## Resume and checks

Training checkpoints preserve policy, optimizer, normalization, shuffle RNG,
Torch RNG, epoch history, and data/source identity. The corrected 24-epoch run
was paused after epoch 8 and resumed. A separate uninterrupted run matches its
final policy tensors, optimizer, RNG states, and normalization exactly. A small
regression independently verifies resumed optimizer/model equality and rejects
corrupted checkpoints.

The continuous house run was paused at action 430, after the skill handoff.
Resumption reconstructs the episode with physical-action replay and verifies its
fingerprint before continuing. It reproduces all 478 actions and the final state,
skill counts, damage, and success outcome exactly. All 42 project tests pass.

## Run it

From the project root:

```sh
.venv-ladx/bin/python scripts/run_navigation_chain.py \
  --checkpoint runs/navigation-model-no-history-v1/epoch-064.pt \
  --goal 0 0 226 36 121 --out runs/NEW_NAVIGATION_RUN
```

The five goal values are indoor flag, map ID, room ID, pixel X, and pixel Y.
Use `--start beach` or `--start approach` for the other prepared starts.
`--stop-after 430` pauses after that many total episode actions; resume with:

```sh
.venv-ladx/bin/python scripts/run_navigation_chain.py \
  --resume runs/PAUSED_NAVIGATION_RUN --out runs/NEW_RESUMED_RUN
```

Reproduce training or evaluation in fresh output directories:

```sh
.venv-ladx/bin/python scripts/train_navigation.py train \
  --cache runs/navigation-cache-v2 --out runs/NEW_MODEL \
  --epochs 64 --no-movement-history
.venv-ladx/bin/python scripts/evaluate_navigation.py \
  --cache runs/navigation-cache-v2 --checkpoint runs/NEW_MODEL/epoch-064.pt \
  --out runs/NEW_LIVE_COMPARISON --workers 8
```

Local PyTorch checkpoints are trusted project artifacts. No cross-version
checkpoint migration is implemented. Training sources are copied into each
model run; source/data identities are recorded in checkpoint sidecars.

## Artifacts and next work

- Experimental selection and policy hash: `configs/navigation_experiment.json`.
- Corrected data and frozen live cases: `runs/navigation-cache-v2`.
- Selected model: `runs/navigation-model-no-history-v1/epoch-064.pt`.
- Original paired comparison: `runs/navigation-live-v2/result.json`.
- Selected comparison: `runs/navigation-live-no-history-v1/result.json`.
- Continuous results: `runs/navigation-chain-comparison-v1.json`.
- Training resume proof: `runs/navigation-model-v2/resume-verification.json`.
- Controller resume proof: `runs/navigation-chain-resume-verification.json`.

The next correction should target the two continuous endpoint stalls and the
six failed local goals. The current successful-segment training distribution
underrepresents blocked and off-route states; those cases need recovery supervision
and fresh evaluation before claiming reliable longer navigation.

## Follow-up

The [targeted recovery experiment](NAVIGATION_RECOVERY.md) fixes the continuous
endpoint stalls. Its broader regressions prevent promotion; the model selected
in this document remains the general experimental parent.
