# Curated navigation, damage, and recovery data

`data/curated/ladx-navigation-v1` contains **321,083 labeled segment indexes**
derived from the verified 16,777,216-action batch. The raw episodes remain
unchanged. Each index identifies its source batch, run, episode, Parquet hash,
and exact half-open step range (`step_start` inclusive, `step_end` exclusive).
Observations and screenshots are read from the original shards when needed.

The curator excludes 672 duplicate episodes, representing 1,096,631 raw rows,
from the derived indexes. Duplicate identity combines the starting-state hash,
complete physical-action hash, and final emulator/observation fingerprint.
The source inventory retains every excluded episode and its canonical counterpart.
This is episode deduplication, not a claim that all remaining state/action pairs
are unique. Common prefixes can still repeat.

## Labels

| Label | Segments | Interpretation |
| --- | ---: | --- |
| Clean sword acquisition | 6,317 | A damage-free learned-policy segment reaches the sword alive |
| Observed safe navigation | 274,148 | Local movement succeeds without damage through an additional safety window |
| Damage event | 19,947 | Nearby damage steps clustered into a contextual event |
| Observed safe recovery | 7,658 | Movement after damage with no further hit or ending within the observation horizon |
| Recovery with repeated damage | 2,975 | Another hit occurs within the recovery window |
| Recovery ending in death | 3,008 | Death occurs within the recovery window |
| Recovery without net progress | 1,235 | Survives the horizon but makes insufficient net movement |
| Censored recovery | 54 | Too little future data or an episode boundary prevents a full recovery judgment |
| Death context | 5,016 | The final actions of a death episode |
| Sword-timeout context | 725 | The final actions before the collector's sword timeout |

Navigation candidates contain 32 exploration actions and require another 16
recorded actions without damage or an episode ending. Their endpoint must be in
a different room or at least 24 Manhattan pixels from the starting position.
That observed endpoint is a **hindsight target**, not a goal supplied to the
original controller and not proof of optimal navigation.

Damage steps separated by at most eight actions are clustered. Each event keeps
up to 16 actions of preceding/following context. Recovery begins after the last
hit in that cluster and is observed for up to 64 actions. A lethal final hit has
no subsequent recovery attempt. A safe recovery label requires the complete
horizon, no subsequent hit/ending, and the same room-change/displacement test.
These are observed outcomes; they do not prove that a particular action caused
or prevented damage.

Successful prefixes from episodes that later die remain useful. The curator
evaluates each segment locally rather than discarding an entire episode because
of its eventual outcome. Conversely, a death-context label does not mean that
every preceding action was bad. Segment windows across different lanes can
overlap, so sums of range lengths are not unique transition counts.

## Training lanes and development split

| Lane | Training segments | Development segments |
| --- | ---: | ---: |
| Imitation | 5,671 | 646 |
| Hindsight navigation candidates | 247,492 | 26,656 |
| Damage events | 17,957 | 1,990 |
| Recovery outcomes | 13,468 | 1,462 |
| Failure contexts | 5,142 | 599 |

Only clean sword acquisition is marked `imitation_eligible`. Setup actions are
excluded from those demonstrations. Exploration candidates require explicit
opt-in for downstream goal-conditioned experiments; their success labels do not
convert scripted/random exploration into expert demonstrations. Damage, recovery,
and failure indexes support outcome modeling and later targeted collection.

Training/development membership is a fixed hash of starting-state identity and
the full physical setup sequence. All exploration-setting variants of that setup
remain in one split. Roughly 10% of setup groups are assigned to development.
The development split shares the same three base savestates and may share similar
observations across groups; it is not an independent benchmark. The separately
reserved 96 evaluation cases remain untouched.

## Loading data

The index files are under `train/` and `dev/`, with one Parquet file per lane.
`segments.parquet` is their combined index; `manifest.json` records hashes,
thresholds, source identity, and counts. The exact curator sources are copied
alongside it. The indexes occupy about 78 MiB and reference the raw corpus.

From the project root:

```python
import sys
import pyarrow.parquet as pq
sys.path.insert(0, 'src')
from gameboy_agent.curation import load_segment

curated = 'data/curated/ladx-navigation-v1'
segment = pq.read_table(curated + '/train/imitation.parquet').to_pylist()[0]
sample = load_segment(curated, segment)
# sample['observations']: decoded structured observations
# sample['rows']: physical actions, rewards, next observations, and other raw fields
```

The default loader rejects development records and non-imitation labels. To
inspect another lane, set `allow_candidates=True`; development loading also
requires `allowed_split='dev'`. Loading checks the registered index record and
source Parquet hash. Keep the original raw batch at the location recorded in
the curated manifest. This loader is a correctness-oriented reference; a large
learner should batch segment reads by source episode instead of re-reading a
shard and verifying the same hash for every overlapping window.

## Reproduce and audit

Use a fresh output directory:

```sh
.venv-ladx/bin/python scripts/curate_workset.py runs/data-workset-16m-v1 \
  --out data/curated/NEW_VERSION --workers 8
.venv-ladx/bin/python scripts/verify_curation.py data/curated/NEW_VERSION \
  --output runs/NEW_VERIFICATION.json
```

The audit checks every segment against its source observations/state columns,
all source/index artifact hashes, split membership and cohort separation,
lane-index completeness, boundaries, target positions, label preconditions, and
loader restrictions. Raw finite-observation and emulator replay evidence remains
in the completed batch audit. All data retains privilege-D provenance; full-game
completion and Tail Cave remain unevaluated. No model training is launched by
the curation command.

The completed v1 audit passed for all 321,083 segments drawn from 7,458 source
episodes (three retained episodes had no qualifying segment). All 38 project
tests pass. In particular, 4,707 clean sword-acquisition demonstrations were
preserved from episodes that later ended in death. The verification report is
`runs/curation-v1-verification.json`; it also confirms source/index hashes,
disjoint setup cohorts, and successful sample loading from all five lanes.
