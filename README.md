# GameBoyGhost

<p align="center">
  <img src="logo.png" alt="GameBoyGhost logo" width="320">
</p>

A reproducible Game Boy agent research project, beginning with Link's Awakening DX. Both v2 handoff documents are canonical requirements.

See [reference assets](docs/REFERENCE_ASSETS.md) for the organized locations of
guides, tilesets, and local research media.

Watch recorded training milestones on the [GameBoyGhost DX YouTube channel](https://www.youtube.com/@GameboyGhost-dx).

Active work follows the [staged progression execution plan](docs/PROGRESSION_EXECUTION_PLAN.md): continuous Tail Key acquisition and Tail Cave entry, evidence-backed memory, and bounded skill improvements. The [new progression interface](docs/PROGRESSION_INTERFACE_V1.md) removes inventory assistance and adds physical equipping and an event journal; the quest itself remains unverified. Further optimizer work is paused until a measured progression blocker exists. The [persistent world memory](docs/WORLD_MEMORY_V1.md) now reconstructs directed connections and observation evidence from verified traces, with deterministic route queries across saved generations.

For the current verified state, completed work, limitations, and the next milestones, see the [project status](docs/PROJECT_STATUS.md).

The [western crossing resolution](docs/PROGRESSION_CROSSING_RESOLUTION.md) corrects an invalid northward route and adds a bounded shielded corridor skill. A fresh house-to-D0 prefix completes with zero damage and exact replay; Tail Key progression remains unverified.

The [forest progression checkpoint](docs/PROGRESSION_FOREST_TERRAIN.md) extends that continuous prefix through forest exploration at full health, with exact replay. Local terrain planning, physical cutting and bounded dialogue handling are scripted; toadstool acquisition remains the next milestone.

The [toadstool route audit](docs/TOADSTOOL_ROUTE_AUDIT.md) shows that ordinary forest screen-edge traversal cannot reach the target room from the current checkpoint; the next bounded skill is non-edge transition discovery and traversal.

The current implementation includes a learned house-to-sword controller that passes 70/70 evaluated start cases, plus a ROM-verified structured baseline, neutral emulator surface, deterministic fixtures, and verified checkpoint/resume. Full-game completion remains unevaluated.

The selected experimental navigator completes **9/9 four-goal routes** and
preserves **46/48, 43/48, and 46/48** successes across the three local panels,
with zero damage or deaths. All three cliff loops and all three original
sword-to-destination chains succeed, with exact replay and pause/resume checks.
It uses two learned final-goal specialists over a frozen v7 fallback. See the
[learned cliff specialist experiment](docs/NAVIGATION_CLIFF_SPECIALISTS.md) and
[versioned results](reports/navigation-cliff-specialists-v2.json). These are known
development/training cases, not general detour-planning evidence; reserved
evaluation remains untouched.

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
