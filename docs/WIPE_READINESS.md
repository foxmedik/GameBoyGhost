# Mac Studio wipe-readiness checklist — NOT READY

No wipe, cleanup, deletion, commit or upload is authorized by this checklist.
`wipe_ready=false`. A local manifest, Git commit, successful emulator replay or
old HF dataset alone is not a recoverable backup. Check items only after verifying
the external copy and recording its location, immutable revision and checksum.

## Source and research-state preservation

- [ ] Review the complete tracked/untracked working tree listed in closeout
  `repository-after.json`. Commit all intended source/config/docs/tests/scripts
  and allowed compact reports, including the new handoff. Resolve accidental
  edits without rewriting historical evidence. Do not indiscriminately add local
  ROMs, secrets, savestates or sealed evaluation contents.
- [ ] Push the reviewed commit to `foxmedik/GameBoyGhost`; verify it from a fresh
  clone. Record branch, commit and remote revision. Current base commit
  `6ae99a894afaf9c53e5e60202d9a1f92c34dfa78` is insufficient by itself.
- [ ] Back up the authoritative status, machine handoff, gate configs, source
  inventories, research decisions, rejected results and upload/restore receipts.
  Export any essential session notes/attachments that only exist outside the repo.
- [ ] Preserve private Git history/patches or an encrypted repository backup if
  historical evidence cannot go to the public source repository. Decide how
  sealed hashes/manifests are stored privately; no automatic publication here.

## Models and datasets

- [ ] Back up every selected/retained model in closeout `model-inventory.json`,
  preserving configured paths, weights, architecture/features/actions and hashes.
  Include the sword tree, experimental navigator and v7 fallback, mushroom and
  downstream models, first-key specialist and retained v5 proposal model.
- [ ] Preserve rejected candidates and experiment manifests, including room-15
  V1–V5 and late cave candidates. Preserve optimizer states, RNG/shuffle state,
  training logs, dependency versions and dataset provenance where present. A
  final inference weight file does not guarantee exact training resume.
- [ ] Select a verified HF model/private-storage destination; no new model repo
  is selected today. Verify uploaded hashes and record immutable revisions.
- [ ] Preserve raw development episodes, continuous correction branches,
  accepted historical labels and their manifests, grouped splits, curated
  indexes, source snapshots and failure traces under `runs/` and `data/`.
  Keep development/gate/label provenance separate. Do not promote diagnostics.
- [ ] Inventory and hash the complete artifact backup, including artifacts not
  enumerated by the focused model inventory. Check sizes and file counts against
  the external copy. Account for any external drives or symlink targets.
- [ ] Verify the historical 16,777,216-action dataset at pinned HF revision
  `5a11ac080f056e2b1d9e4bf5a489b960399ff1fd`; its 83-file receipt is historical,
  not proof that current models or newer runs are backed up. Do not overwrite it.

## Frozen definitions, sealed evidence and physical replay

- [ ] Preserve all frozen development/evaluation definitions, budgets, source
  hashes, experiment configs, retired-cohort registries and results. The active
  full-route criteria exist, but new case manifests are not yet frozen; record
  that absence instead of inventing a gate. Project completion is not a condition
  for backup, but its actual incomplete state must survive.
- [ ] Back up sealed validation privately: the original longrun plan, all 20
  `cases/validation-house-*` directories, shared results/verification and report;
  the reserved `runs/data-workset-16m-v1/frozen-eval.json` and smoke versions.
  Use `sealed-integrity.json` as an integrity reference. Do not parse them to
  diagnose development, include them in training, or publish the trajectories.
- [ ] Preserve each continuation's complete ordered `replay_segments`, original
  house state, ROM dependency, manifests, request logs, journals, controller/source
  snapshots, fingerprints and final evidence. Copying just continuation JSONs or
  final screenshots will not restore a runnable route.
- [ ] Preserve the annotated videos and their manifests/descriptions, plus any
  original private recordings/reference assets needed by the project.

## Private runtime dependencies

- [ ] Privately preserve the legally obtained ROM and required emulator states;
  keep them out of public uploads. Verify ROM SHA-256
  `6285ba6201f17bc8595c600ebc2477d52561f0aff29b11f7fc3343bacb2e230b`.
  Preserve the supplied house-state dependency and its recorded hash. A ROM
  checksum is identification, not a copy of the ROM.
- [ ] Preserve reference checkout commits from `configs/references.lock.json`.
  Closeout checked clean matching local commits, but remote availability alone
  is not a private backup of required state files. Preserve upstream assets and
  any future local patches separately. Bootstrap follows heads; explicitly
  restore the pinned revisions for reproduction.
- [ ] Preserve requirements files and `environment.json`, including Python
  3.11.16, PyBoy 2.0.0, Torch 2.2.2, NumPy 1.26.4, Gymnasium 0.29.1, SB3 2.3.0,
  imageio-ffmpeg 0.6.0 and Pillow 10.3.0. Record OS/architecture, FFmpeg and fonts
  needed to reproduce the presentation. Local virtual environments are not a
  substitute for a tested reinstall procedure.
- [ ] Ensure account access, backup encryption/recovery keys and necessary
  private credentials survive in a secure password/secret store. Do not copy
  plaintext secrets into this repository or publish them in manifests.
- [ ] Keep at least one verified copy off this Mac, with sufficient free space,
  accessible credentials and a second independent copy of irreplaceable data.

## Restore procedure and acceptance

1. On another clean machine or isolated clean environment, clone the pinned
   current source commit. Do not rely on this Mac's working tree or caches.
2. Restore references at recorded commits; obtain private ROM/state dependencies.
3. Create the Python environment using the checked requirements and reconcile
   against `environment.json`. Use the appropriate optional data/video packages.
4. Restore exact model/data/run paths from the external artifact inventory.
   Check every file hash, including sealed data by opaque hash only.
5. Run the recorded closeout regression command with the sealed-definition test
   excluded. Verify that expected local-fixture tests actually ran; investigate
   missing dependencies/skips rather than treating them as success.
6. Run `scripts/verify_house_door_handoffs.py` to an unused output path. Both
   complete physical replays must match every command and final state without
   save/load shortcuts or new gameplay. Compare with closeout evidence.
7. Verify selected controller loading and, if required, training-resume behavior
   using isolated software fixtures—not a new learner campaign or sealed panel.
8. Record restore machine, pinned source/artifact revisions, dependency versions,
   checksums, test/replay reports and unresolved issues in a signed-off restore
   receipt. Test retrieval of private backups and decryption before erasing.

Only after all required backups and this independent restore pass may a later,
explicitly authorized wipe decision be considered. No clean-environment restore
has been demonstrated by this closeout. **Do not erase the Mac Studio.**
