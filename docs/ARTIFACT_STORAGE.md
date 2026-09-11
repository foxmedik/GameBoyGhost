# Source and artifact storage

GitHub hosts project source, tests, documentation, configuration and compact
result summaries. Generated artifacts stay outside the Git repository:

| Location | Contents |
|---|---|
| GitHub: foxmedik/GameBoyGhost | Source, tests, docs, experiment configurations and reports |
| Hugging Face: foxmedik/GameBoyGhost-LADX | Versioned Parquet shards, manifests, checksums and dataset card |
| Local `runs/` and `data/` | Raw immutable episodes, development outputs, corrections and checkpoints |
| Local ROM and `references/` | User-supplied ROM and separate upstream checkouts |

The initial release is published at
https://huggingface.co/datasets/foxmedik/GameBoyGhost-LADX. All 83 uploaded files
passed remote hash verification. The exact revision is pinned in
`configs/artifact_repositories.json`; the release contains 16,777,216 actions in
64 raw shards, plus curated indexes and metadata. Checkpoints are separate artifacts; their exact hashes and local
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

## Download the published dataset

Use the verified revision pinned in `configs/artifact_repositories.json`:

```sh
uv venv --python 3.11 .venv-hub
uv pip sync --python .venv-hub/bin/python configs/requirements-hub.txt
.venv-hub/bin/python - <<'PY'
import hashlib
import json
from pathlib import Path
from huggingface_hub import snapshot_download

config = json.loads(Path('configs/artifact_repositories.json').read_text())
release = Path(config['local_release_path'])
snapshot_download(config['dataset_repository'], repo_type='dataset',
                  revision=config['dataset_revision'], local_dir=release)
for name, expected in json.loads((release / 'checksums.json').read_text()).items():
    digest = hashlib.sha256()
    with (release / name).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    assert digest.hexdigest() == expected, name
print('Dataset checksums verified')
PY
```

The dataset card explains packed observation decoding and curated-segment
lookup through release shard/row-group columns. Historical raw episode paths
are provenance identifiers, not paths to separately uploaded episode files.
