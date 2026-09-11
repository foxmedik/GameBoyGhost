# Large parallel data workset

The collection target is **16,777,216 recorded emulator actions**. This is data
collection, without optimizer updates or automatic policy promotion. It combines
the selected learned sword policy with explicitly scripted, randomized
exploration, preserving successful prefixes, damage, deaths, and timeouts.

The host has 32 CPU cores, 256 GiB of physical RAM, and about 1.4 TiB free disk
at setup. Available RAM is lower because other applications also use the machine.
Collection does not allocate memory merely to fill it.

## Frozen batch

`runs/data-workset-16m-v1` owns its complete runtime snapshot and assets. Every
worker uses one numerical-library thread. The scaling benchmark compares
8, 16, 24, 32, 48, and 64 worker processes on the same 128 episode specifications,
with a 768-action episode budget and the actual Parquet/screenshot writer enabled.
Process startup is reported separately. The selected count is the smallest within
10% of the best measured throughput among configurations without worker errors.
Benchmark records have their own splits and never enter the training corpus.

Measured results (all six configurations produced identical action hashes,
final fingerprints, and row counts for every episode):

| Workers | Recorded actions/second | Peak process RSS |
| ---: | ---: | ---: |
| 8 | 2,395 | 2.9 GiB |
| 16 | 4,614 | 5.5 GiB |
| 24 | 6,624 | 8.2 GiB |
| 32 | 7,072 | 10.8 GiB |
| 48 | 6,923 | 16.0 GiB |
| 64 | 6,806 | 21.3 GiB |

The default economy selector chose 24 workers. This batch explicitly selects
**32 workers**, the fastest measured configuration, to prioritize the requested
large collection. The 16-million-action batch is launched detached with an idle
sleep assertion tied to the supervisor PID. `runs/latest-data-workset.json`
points to it; `launch.json` and `collection.log` record the launch and output.
Shutdown or logout can still interrupt collection.

The collection limits are:

- 16,777,216 committed actions, with a maximum of 4,096 actions per episode.
- Eight hours of active collection across restarts, excluding the benchmark.
- 256 GiB of committed episode output, at least 100 GiB free disk, and at least
  32 GiB available system RAM.
- Stop after 20 worker failures in one supervisor session.

Resource limits stop new episode dispatch; in-flight episodes drain before the
batch pauses. They can therefore exceed a resource/time threshold by the bounded
in-flight work. Status files report rows, episodes, deaths, sword acquisitions,
output size, resource use, failures, and the supervisor PID.

## Distribution and evaluation boundary

Training rotates the existing house, beach, and close-approach starts. Their
health and equipment are inherited from recorded gameplay; no healing or RAM
edits are used to manufacture starts. The inherited privilege-D environment
still contains game-specific observations, reward knowledge, and assistance.

Each episode has a deterministic seed, 16–255 initial idle actions, and a short
physical movement perturbation. Sword execution uses the frozen selected policy.
Exploration rotates random-intervention probabilities of 0%, 2%, 5%, 10%, and 20%,
with short directional commitments layered onto visited-position and hazard
memory. Every actual action is recorded, including setup and interventions.

`frozen-eval.json` reserves 96 future evaluation specifications with separate
seeds and 256–319 idle actions. These are **not collected into training**. They
still share the same three base savestates, so they are a held-out perturbation
set, not independent games or proof of generalization. Existing evaluation
artifacts are never read as demonstration inputs.

Many episodes share the learned sword prefix. Raw action count is not the number
of independent skills or useful imitation examples. Random exploration and deaths
must retain their labels; downstream imitation training should select appropriate
successful segments and inspect duplicate observations rather than treating all
actions as expert advice. Full-game completion and Tail Cave remain unevaluated.

## Storage contract

Each episode attempt has a UUID directory. Its `manifest.json` is the commit
marker; partial attempts and `failure.json` directories are excluded. A completed
episode contains Zstandard-compressed `steps.parquet`, a final emulator state,
and skill/damage/outcome events. The manifest records:

- Unique batch, producer, run/attempt, and stable episode IDs; seed and split.
- Start asset, physical setup sequence, exploration settings, status and labels.
- Observation layout, action hash, final replay fingerprint, artifact hashes,
  row count, wall time, room identities, health, and sword-acquisition step.

`gameboy-motor-v1` stores both observations at every action boundary. Observations
are lossless binary concatenations of typed arrays; each shard embeds the key,
shape, dtype/endianness, and byte-length layout. Use `unpack_observation` in
`src/gameboy_agent/dataset.py` to decode them. Each row also includes physical
action, active skill, supervision source, room/position/health before and after,
reward and components, actual advanced/wait frames, and termination flags.

PNG screenshots describe the **post-action** state, sampled every 32 actions
and at acquisition or environment termination. They are embedded in Parquet,
avoiding millions of standalone image files. This is sampled visual data, not
a full-resolution screenshot at every step. The structured observation's
low-resolution screen tensor is present on every row.

The episode outcome can also be `sword_timeout`, a collector boundary while the
emulator itself remains alive. Consumers must respect manifest episode boundaries
as well as the environment's per-row termination/truncation flags.

## Reproducibility and restart

`runtime.json` hashes the frozen project/upstream files and pins dependency
versions; `assets.json` hashes the ROM, three starting states, and selected policy.
Startup verifies these before collection. Each process owns its ROM copy and
emulator instances. There are no shared writable trajectory files between workers.
The supervisor alone appends the commit index and atomically updates status.

On restart, the supervisor verifies committed artifact hashes and reconciles
episode manifests. Already committed episode indices are skipped; incomplete
attempts are retained and can be retried under fresh attempt UUIDs. Resume is at
episode boundaries, not midway through unfinished episodes. A supervisor lock
prevents two collectors from operating on the same batch simultaneously.

The smoke run at `runs/data-workset-smoke-v2` produced 4,096 contiguous per-episode
rows across five episodes. All hashes and observation boundaries passed
validation. Three sampled episodes reproduced every observation, reward, terminal
flag, and final fingerprint through physical-action replay. Restarting that
completed run produced no duplicate episodes or rows. With collection dependencies
installed, all 33 tests passed before the scaling benchmark.

The production batch also passed a controlled graceful pause at 228,466 actions
across 115 episodes. Every committed artifact hash, per-episode step index,
observation boundary, and reward-component sum passed validation. Three sampled
production episodes replayed exactly, including two full 4,096-action episodes.
The report is `runs/data-workset-16m-v1-production-verification.json`. Collection
then resumed from those committed episodes using the same frozen runtime.

## Commands

Install optional data dependencies after setting up the baseline:

```sh
uv pip install --python .venv-ladx/bin/python -r configs/requirements-data-workset.txt
```

Create a new frozen batch and benchmark it:

```sh
.venv-ladx/bin/python scripts/data_workset.py --prepare --directory runs/NEW_BATCH
.venv-ladx/bin/python runs/NEW_BATCH/runtime/scripts/data_workset.py \
  --directory runs/NEW_BATCH --benchmark
```

Start or resume using the selected worker count:

```sh
.venv-ladx/bin/python runs/NEW_BATCH/runtime/scripts/data_workset.py \
  --directory runs/NEW_BATCH
```

Creating `runs/NEW_BATCH/STOP` requests a graceful pause after in-flight episodes.
Remove that file before resuming. SIGTERM to the supervisor also requests a
graceful pause. Consult `status.json` for its PID.

Validate committed shards and replay three sampled episodes, using a new report
path each time:

```sh
.venv-ladx/bin/python runs/NEW_BATCH/runtime/scripts/verify_data_workset.py \
  runs/NEW_BATCH --replay 3 --output runs/NEW_VERIFICATION.json
```

ROMs, data, and runtime snapshots remain local and excluded from versioned source.
