# Restore house-to-boss-door-v1

This is a qualified guided teacher, not a learned autonomous route policy. Candidate27 passed the original20-house plus4 actual half-heart recovery gate, with independent exact replay for every case. No learner labels or training were generated.

The public repository supplies code, configs, tests, dependency pins, qualification summaries and manifests. The private USB backup at `GameBoyGhost/house-to-boss-door-v1/workspace` supplies ROM/state, models, traces, data, references, and all retained development failures. Never publish the ROM or private source media.

Restore the published release Git commit into a new directory. Copy `runs`, `references`, `data`, and `assets` from the verified private backup. The original qualified configs also exist at `runs/house-to-boss-door-v1-qualified-configs`; later research-status bookkeeping is distinct from the qualified controller.

Create a fresh environment using `uv venv --python 3.11.16 --managed-python .venv-restored`, then `uv pip install --no-cache --python .venv-restored/bin/python -r reports/house-to-boss-door-v1/requirements-lock.txt`. Do not copy or reuse the previous virtual environment.

Run `PYTHONPATH=src:tests .venv-restored/bin/python -m unittest discover -s tests`. The historical reserved-panel generator stays intentionally skipped. Verify sealed artifacts only by opaque byte hashes.

Run `PYTHONPATH=src .venv-restored/bin/python scripts/replay_house_door_release.py --output reports/restore-replay.json`. This starts from the supplied house, checks every recorded command fingerprint, event, frame and state, verifies the journal, and requires full health, sword A, Feather B, a settled opened door outside the boss room. There are no intermediate state loads.

The final release manifest records the exact public commit, private backup integrity receipt, and fresh restore results. Do not infer restoration success from the qualification result alone.
