# GameBoyGhost

A reproducible Game Boy agent research project, beginning with Link's Awakening DX. Both v2 handoff documents are canonical requirements.

The current implementation includes a learned house-to-sword controller that passes 70/70 evaluated start cases, plus a ROM-verified structured baseline, neutral emulator surface, deterministic fixtures, and verified checkpoint/resume. Full-game completion remains unevaluated.

The selected experimental navigator now fixes the last observed regression:
**46/48, 39/48, and 46/48** across three development/regression panels, with no
lost parent successes, damage, or deaths. All three continuous
sword-to-destination runs succeed without damage. See the
[focused fix](docs/NAVIGATION_FOCUSED_FIX_V4.md) and
[versioned results](reports/navigation-focused-v4.json). These are development
results; reserved evaluation data remains untouched.

Repository source lives here; ROMs, reference checkouts, generated datasets,
and model checkpoints are external artifacts. See
[artifact storage and setup](docs/ARTIFACT_STORAGE.md) before running a fresh clone.

Run the selected controller with `.venv-ladx/bin/python scripts/run_sword_controller.py`. See [the sword controller](docs/SWORD_CONTROLLER.md) for the evaluation scope, provenance, and resume commands.

Continue beyond acquisition with `.venv-ladx/bin/python scripts/run_skill_chain.py`.
The [skill chain](docs/SKILL_CHAIN.md) connects the learned sword controller to
bounded scripted exploration in the same episode, with verified planner and
emulator replay. The house pilot survives 2,000 exploration actions across seven
post-acquisition rooms; Tail Cave remains unevaluated.

The [large data workset](docs/DATA_WORKSET.md) adds parallel collection with
compressed Parquet episodes, complete structured observations, sampled screenshots,
frozen evaluation specifications, and episode-boundary restart.

The [curated training indexes](docs/CURATED_DATA.md) now separate clean sword
demonstrations, safe-navigation candidates, damage events, recovery outcomes,
and failure contexts, with deduplication and grouped development splits.

The [first navigation experiment](docs/NAVIGATION_EXPERIMENT.md) trains a
goal-conditioned controller that reaches 42/48 local development goals with no
damage. Continuous sword-to-navigation runs leave the sword room from all three
prepared starts, but two miss the precise destination. It remains experimental.

Start with [training and resume](docs/TRAINING_AND_RESUME.md) for results, limitations, and runnable commands. [Setup status](docs/SETUP_STATUS.md), the [environment audit](docs/ENVIRONMENT_AUDIT.md), and [ROM verification](docs/ROM_TRANSITION_AUDIT.md) document the supporting work.

```bash
uv venv --python 3.11 .venv-ladx
uv pip sync --python .venv-ladx/bin/python configs/requirements-ladx-baseline.txt
.venv-ladx/bin/python -m unittest discover -s tests -v
.venv-ladx/bin/python scripts/train_ladx.py --steps 32768
```

These commands require the reference checkouts and a locally supplied ROM matching the verified English 1.1 profile. ROMs, generated runs, checkpoints, and reference repositories stay outside versioned project source. Test fixtures are scripted; training is labeled with its inherited assistance.

The [targeted navigation recovery experiment](docs/NAVIGATION_RECOVERY.md) repairs
all three continuous endpoint runs and five of six targeted local goals, but
remains an unpromoted candidate because broader regressions and damage remain.

The [second recovery batch](docs/NAVIGATION_RECOVERY_BATCH_V2.md) tests preserving
parent predictions during correction; all three candidates retain continuous
route recovery, but none passes the broader regression gate.

The [live-trajectory correction experiment](docs/NAVIGATION_LIVE_CORRECTION_V3.md)
adds verified parent trajectories and off-route recoveries, restoring the
additional panel without damage; one original regression still blocks promotion.

The [Hugging Face dataset](https://huggingface.co/datasets/foxmedik/GameBoyGhost-LADX)
is now published: 16,777,216 actions in 64 verified shards, with curated indexes
and metadata. [Download the pinned release](docs/ARTIFACT_STORAGE.md). ROMs and
reserved evaluation specifications are excluded.
