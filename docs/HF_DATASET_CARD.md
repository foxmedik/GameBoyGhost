---
pretty_name: GameBoyGhost LADX motor collection
language:
- en
size_categories:
- 10M<n<100M
tags:
- reinforcement-learning
- imitation-learning
- game-agents
- trajectories
- parquet
configs:
- config_name: raw
  default: true
  data_files:
  - split: collection
    path: raw/*.parquet
- config_name: episodes
  data_files:
  - split: collection
    path: metadata/episodes.parquet
- config_name: curated_navigation
  data_files:
  - split: train
    path: curated/train/hindsight_navigation.parquet
  - split: validation
    path: curated/dev/hindsight_navigation.parquet
- config_name: curated_imitation
  data_files:
  - split: train
    path: curated/train/imitation.parquet
  - split: validation
    path: curated/dev/imitation.parquet
---
# GameBoyGhost-LADX

A dataset of **16,777,216 emulator actions across 8,133 episodes**, collected
for the GameBoyGhost research project in Link's Awakening DX. Source and
experiment documentation: [GameBoyGhost](https://github.com/foxmedik/GameBoyGhost).

## Contents

- `raw/`: 64 Parquet shards, retaining full episodes and all committed rows.
  Each Parquet row group contains one complete source episode.
- `metadata/episodes.parquet`: episode provenance, source checksums, shard and
  row-group lookup, original curation split/cohort and duplicate relationships.
- `metadata/observation-layout.json`: exact byte layout of structured observations.
- `curated/train` and `curated/dev`: clean sword imitation, hindsight navigation,
  damage events, recovery and failure indexes referencing the raw rows.
- `manifest.json` and `checksums.json`: release details and file integrity.

Rows include physical actions, structured before/after observations, sampled
PNG screenshots, room/position/health, sword state, reward components, timing,
termination flags, skill and supervision labels. Observation columns are packed
binary arrays; decode them with the published layout and the project's
`gameboy_agent.dataset.unpack_observation` helper. Actions encode movement
(0 none, 1 up, 2 down, 3 left, 4 right) and buttons (0 none, 1 A, 2 B).

Producer identifiers are pseudonymized. All other raw row values are preserved.
ROM files, savestates, reference checkouts, local paths and the reserved
evaluation specifications are not included.

## Collection and supervision

The fixed sword policy is followed by scripted novelty exploration, with varied
physical setup waits and movement perturbations. Collection uses the inherited
**privilege-D assisted harness**, including structured game state and upstream
assistance. It is not a neutral pixels-only dataset or a set of human expert
trajectories. Full-game completion was not evaluated.

There are 5,348 death outcomes, 1,026 sword timeouts and 1,759 budget-exhausted
episodes. Death-ending episodes can contain useful earlier behavior: curation
retains safe prefixes and separately labels damage/recovery/failure contexts.
Raw data retains 672 duplicate episodes. The curated indexes deduplicate source
episodes and contain 321,083 overlapping segments, not 321,083 independent runs.

Only the clean sword lane is imitation-eligible by default. Navigation and
recovery are observed-outcome candidates; a successful trajectory can still
contain inefficient or conflicting action labels. Users should not blindly
clone every action in a successful or failed episode.

## Splits and evaluation

The raw `split` column says `train` because it records the original collection
partition. It is **not** the subsequent model-training/development assignment.
Use episode metadata and curated cohort assignments for that purpose.

The original curation used grouped train/development splits. Some development
cohorts were subsequently used for corrective training. These are flagged
`development_retired=true` in episode metadata and curated indexes. Do not use
those rows as validation for the published correction experiments. Even the
remaining development data shares prepared base states; it is not an independent
generalization benchmark. The 96 reserved evaluation specifications were not
collected or included in this release.

## Loading

```python
from datasets import load_dataset

# Stream the raw collection without materializing all observations in RAM.
rows = load_dataset("foxmedik/GameBoyGhost-LADX", "raw",
                    split="collection", streaming=True)
row = next(iter(rows))
```

To resolve a curated segment locally, read its `release_shard` at
`release_row_group`, then slice `step_start:step_end` within that episode.
`source_path` and `source_sha256` retain the pre-release episode provenance.
The source checksum differs from the consolidated release-shard checksum.

## Verification and limitations

The original collection passed full source/schema checks and sampled exact
emulator replay. Every released raw row group was additionally compared
value-for-value against its committed source episode after producer-ID
pseudonymization. File checksums cover the complete release.

This initial release contains the original collection and its historical
curated indexes. Later focused correction demonstrations and model weights are
separate local artifacts and are not included here.

Game content remains attributable to its respective owners. No license grant
for underlying game assets or third-party material is asserted by this card.
