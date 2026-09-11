# Source and artifact storage

GitHub hosts project source, tests, documentation, configuration and compact
result summaries. Generated artifacts stay outside the Git repository:

| Location | Contents |
|---|---|
| GitHub: foxmedik/GameBoyGhost | Source, tests, docs, experiment configurations and reports |
| Hugging Face dataset repository (pending) | Versioned Parquet shards, manifests, checksums and dataset card |
| Local `runs/` and `data/` | Raw immutable episodes, development outputs, corrections and checkpoints |
| Local ROM and `references/` | User-supplied ROM and separate upstream checkouts |

The Hugging Face repository URL and download instructions will be added after
creation and upload. No dataset upload has been performed as part of initial
GitHub setup. Checkpoints are separate artifacts; their exact hashes and local
paths are recorded in controller configurations.

## Fresh checkout

Create a Python 3.11 environment using the pinned requirements in README.
The optional data tooling additionally requires
`configs/requirements-data-workset.txt`. Fetch the reference checkouts with
`bootstrap_repos_v2.sh`; the commits used for the recorded experiments are
listed in `configs/references.lock.json`. The bootstrap follows upstream heads,
so use the recorded revisions when reproducing those experiments.

A local ROM matching `configs/ladx-rom-verification.json` is required for
emulator runs and integration tests. Pretrained controller commands also need
the corresponding checkpoint files at the paths in the configurations. A fresh
source clone alone does not include those artifacts.

The future dataset release should preserve immutable episode identifiers,
observation layouts, supervision labels, checksums, and split provenance.
The 96 reserved evaluation specifications stay outside the training release.
Raw-ROM files, emulator savestates, and reference-repository copies are not
part of the shard upload.
