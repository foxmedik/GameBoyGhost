# Initial setup status

Both v2 handoff documents remain canonical. This file records implementation status, not changes to their requirements.

## Acquired

- All 14 repositories from `bootstrap_repos_v2.sh`, under `references/`.
- Exact fetched commits and origin URLs recorded in `configs/references.lock.json`. The bootstrap still follows upstream branches; this manifest records this particular acquisition.
- Isolated Python 3.11 environment at `.venv-ladx` on macOS arm64.
- Core LADX dependencies, including upstream pins PyBoy 2.0.0, Gymnasium 0.29.1, NumPy 1.26.4, Torch 2.2.2, and SB3 2.3.0.
- Direct requirements and resolved dependencies in `configs/requirements-ladx-baseline.in` and `.txt`. Transitive versions are newly resolved, so this is not an exact restoration of upstream's entire 2024 environment.
- Root `.gitignore` excludes reference checkouts, ROMs, saves, local environments, secrets, and generated training artifacts.

Recreate the baseline environment from the project root:

```bash
uv venv --python 3.11 .venv-ladx
uv pip sync --python .venv-ladx/bin/python configs/requirements-ladx-baseline.txt
uv pip check --python .venv-ladx/bin/python
```

The dependency consistency check passed. SB3 2.3.0 is yanked for a PyTorch 1.13 loading issue; this baseline uses upstream's Torch 2.2.2 pin. Runtime verification is still necessary.

## Findings before full LADX reproduction

Runtime smoke checks passed: core imports including the LADX environment module, Torch MPS availability, ROM boot, and loading the upstream emulator savestate. Replaying the same 24-frame input sequence twice from an in-memory savestate produced identical framebuffer and work-RAM hashes. This is a small emulator check, not full environment replay or ROM-revision validation. The smoke check used a temporary ROM copy and did not alter the original ROM or reference checkout.

- The upstream requirements file is UTF-16 and includes unrelated packages. The local baseline selects core environment and SB3 dependencies.
- `load_info_json` and `save_info_json` use Windows backslash paths. Checkpoint handling needs portable paths and output isolation.
- The upstream training module imports the optional JAX implementation unconditionally; that implementation imports `sbx`, which is absent from upstream requirements and the local baseline.
- The environment factory imports the streaming wrapper unconditionally, requiring `websockets` even when streaming is disabled. The wrapper points to an external broadcast server. A local baseline should explicitly disable broadcasting and avoid the unnecessary import.
- Upstream training starts at module import and needs a main guard before using macOS multiprocessing.
- The handoff's example bootstrap filename lacks the `_v2` suffix present on disk.

## First environment and training run completed

Run `d7d12c06-d7a6-4db8-8d7e-34e3b91e4f83` passed:

- SB3 environment checker and strict finite-value/observation-space validation.
- Two identical 16-action sequences from the fixed savestate produced equal observations, rewards, and terminal flags.
- 256 PPO training steps, two 128-step episodes, finite parameters, and confirmed parameter updates.
- Policy save/load preserved the deterministic action for a fixed observation; the loaded policy ran 16 further inference steps.
- Training took approximately 1.08 seconds on CPU with four Torch threads. This short run is not a scaling benchmark.
- The final framebuffer was inspected. The upstream checkout remains clean.

Run artifacts are under `runs/<run_id>/`: `run.json`, `replay-check.json`, `policy.zip`, `monitor.csv`, TensorBoard events, `screen.png`, and local ROM/state copies. Metadata records configuration, source/ROM/state hashes, upstream commit, versions, and privilege level. Outputs use unique UUID directories. No broadcasting is enabled.

Rerun from the project root:

```bash
.venv-ladx/bin/python scripts/run_ladx_baseline.py
# A longer bounded run:
.venv-ladx/bin/python scripts/run_ladx_baseline.py --steps 4096 --seed 1
```

The project-owned `src/gameboy_agent/ladx_baseline.py` subclasses the upstream environment and imports its feature extractor directly, avoiding broken training imports. It preserves action/reward computation while making these explicit changes:

- Uses the supplied fixed savestate; automatic checkpoint curriculum and checkpoint writes are disabled for this experiment.
- Converts observations to their declared dtypes, fixes entity IDs to 0–255, and permits signed entity offsets. Invalid/non-finite observations raise errors without clipping.
- Removes the upstream step exception swallowing and distinguishes death termination from time-limit truncation.
- Enables frame rendering and uncapped headless emulation; cleans up hooks and avoids writing battery saves on close.
- Uses Gymnasium's reset signature and seed initialization.

The runner uses upstream's custom feature extractor and 1024/1024 policy network. It deliberately reduces rollout length, batch size, update epochs, and episode length for a smoke test. Checker warnings about unusual observation shapes are expected for this custom extractor; these are not standard image-CNN inputs.

This run is labeled harness privilege D and `completion_evaluated=false`: game-specific progress observations/rewards and RAM-based inventory switching remain inherited. Upstream also calls a script to grant magic powder in the witch's hut, remove duplicate inventory items, and can refill magic powder through its progress logic. These inherited helpers must be separated from neutral evaluation before measuring autonomous completion. It is not a new-game completion benchmark or a reproduction of upstream's full training results. The replay check covers fixed-start observations/rewards, not complete mid-run resume. The saved SB3 artifact does not capture emulator, curriculum, and world-memory state together.

## Next milestone

Phase-aware transitions, sword/push fixtures, and verified single-environment PPO save/resume are implemented. The 32,768-step pilot completed across a deliberate process restart; 18 regressions pass. See `docs/TRAINING_AND_RESUME.md` for exact results, checkpoints, and limitations. Earlier audits remain supporting history. Canonical Parquet/event schemas, broader transition/death coverage, completion detection, PufferLib comparisons, multi-environment scaling, and the planner remain pending.
