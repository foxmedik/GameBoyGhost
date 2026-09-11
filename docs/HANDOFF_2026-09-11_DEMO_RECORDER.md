# GameBoyGhost human-demo recorder handoff — 2026-09-11

## Purpose

This session built the first usable human-demonstration recorder for Link's Awakening DX. It is intended to collect small, labeled gameplay clips that can become supervised training data: game frames, per-frame controller state, grouped input segments, game-state metadata, and human success/contrast markers.

The immediate collection target is the **house-to-sword checkout**. The player starts from the house save state, demonstrates two sustained shield pushes that move urchins out of the path, reaches the sword, and saves the run.

## Current repository and deployment state

- Repository: `https://github.com/foxmedik/GameBoyGhost.git`
- Branch: `main`
- Current Studio revision at handoff: `be51192` (`Persist completed demos and upload them to Studio`)
- Studio checkout: `/Users/studio/Developer/GameBoyAgent`
- Mini checkout: `/Users/benjaminhetrick/Developer/GameBoyAgent`
- Mini recorder launcher used by the user: `/Users/benjaminhetrick/Developer/GameBoyGhost Demo Recorder.app`

The launcher at the latter path was replaced during this session with a copy of the current generic launcher from the Mini checkout. This matters because the older launcher incorrectly referenced the Studio source path and was responsible for the stale behavior seen earlier.

## Recorder behavior

The app source is [`apps/human_demo_app.py`](../apps/human_demo_app.py). It is an SDL/PyBoy application and opens as a resizable window.

The top of the window contains the game preview, a compact panel map, and controller/delivery status. The lower card spans the full window width and shows the current task's objective, good-tag guidance, bad-tag guidance, saved count, and run controls.

Current controller mapping:

| Control | Meaning |
| --- | --- |
| D-pad / A / B / Start / Select | Recorded and passed to the emulator as gameplay input |
| L2 | Good marker (`l2_good`) |
| R2 | Bad/contrast marker (`r2_bad`) |
| X | Discard the active run and reload the save state |
| Y | Select the next task while idle; skip the five-second wait and begin the queued next run |

While a run is active, the map/status panel displays live L2/R2 tag counters and briefly flashes when a tag is recorded.

At the end of a valid attempt, the user clicks **SAVE**. This:

1. Closes the raw data files.
2. Writes `manifest.json` (`human-demo-v4`) with task ID, frame count, good/bad tag counts, and completion timestamp.
3. Updates the persistent local progress file at `~/Library/Application Support/GameBoyGhost Demo Recorder/runs/progress.json`.
4. Creates a `.tar.gz` archive for the entire session.
5. Uploads that archive to the Studio.
6. Starts a five-second visual countdown for the next run unless the task's target count is complete.

Only sessions with a manifest count as completed runs. Incomplete raw captures remain on the Mini but do not advance the counter.

## Current task

[`configs/human_demo_tasks.json`](../configs/human_demo_tasks.json) currently contains one task:

- ID: `recorder-checkout-house-to-sword`
- Target: 5 completed runs
- Save state: `runs/navigation-chain-house-v1/initial.state`
- Limit: 120 seconds per run
- Success behavior: two sustained shield pushes that move urchins aside, then reach the sword
- Good tagging: L2 after house exit, each completed urchin push, beach entry, and sword pickup
- Bad tagging: R2 after damage, collision, wrong turn, or recovery

This is intentionally a recorder and transport checkout, not yet a complete combat dataset.

## Data format and locations

The Mini writes sessions to:

```text
/Users/benjaminhetrick/Library/Application Support/GameBoyGhost Demo Recorder/runs/
```

Each completed session has this shape:

```text
recorder-checkout-house-to-sword-YYYYMMDD-HHMMSS/
  actions.jsonl          # one record per emulation frame
  input_segments.jsonl   # contiguous button-hold periods
  tags.jsonl             # L2/R2 timestamped annotations
  frames/                # PNG game frame for every record
  manifest.json          # completion marker and summary
```

Each `actions.jsonl` state includes room, overworld room, Link coordinates, health, toadstool state, and `sword_level`. `sword_level` was added during this session so future runs can be verified for actual sword acquisition.

Archives arrive on the Studio at:

```text
/Users/studio/Developer/GameBoyAgent/runs/human-demos/incoming/
```

These assets are local collection data and must not be committed to Git.

## SSH and upload setup

Two passwordless directions are configured:

- Studio → Mini inspection key: `/Users/studio/.ssh/gameboyghost_mini`
- Mini → Studio upload key: `/Users/benjaminhetrick/.ssh/gameboyghost_studio`

The Mini upload key is authorized on the Studio. The app uses it explicitly for `rsync` with `BatchMode=yes`; it does not wait for an interactive password prompt.

The exact Mini-to-Studio rsync path was smoke-tested during this session. The test file arrived in the Studio intake and was removed afterward.

## Verified checkout evidence

### Earlier incomplete captures

Two captures made before the corrected launcher was installed were inspected directly on the Mini:

1. `recorder-checkout-house-to-sword-20260911-090618`
   - 5,367 frames and actions
   - 155 input segments
   - 4 L2 good markers
   - No completion manifest
   - Useful as raw recorder checkout data, but does not count as an accepted training run.
2. `recorder-checkout-house-to-sword-20260911-091842`
   - 1,103 frames/actions
   - No input segments or tags
   - No completion manifest
   - Incomplete; do not curate as a successful example.

### End-to-end transport test

After the current launcher and SSH upload path were installed, a saved smoke run completed successfully:

- Session: `recorder-checkout-house-to-sword-20260911-100553`
- 447 frames/actions
- 1 input segment
- 0 tags, expected for a short save/upload smoke test
- `manifest.json` written as `human-demo-v4`
- Archive received on the Studio in `runs/human-demos/incoming/`

This proves that the save → archive → authenticated SSH upload path works.

## Validation tools

Run this locally on the Mini to inspect all sessions:

```bash
cd ~/Developer/GameBoyAgent
./.venv-ladx/bin/python scripts/inspect_human_demos.py
```

The inspector reports each session as `READY` or `INCOMPLETE`, plus frames, actions, input segments, tags, and manifest presence.

With Studio-to-Mini SSH available, the Studio can inspect the same folder directly:

```bash
ssh -i ~/.ssh/gameboyghost_mini benjaminhetrick@192.168.50.196 \
  './Developer/GameBoyAgent/.venv-ladx/bin/python \
  ./Developer/GameBoyAgent/scripts/inspect_human_demos.py'
```

## Important operational notes

- Use the app at `/Users/benjaminhetrick/Developer/GameBoyGhost Demo Recorder.app`, not an older copied launcher elsewhere.
- Restart the app after a Git pull; a running app keeps the older Python code in memory.
- Click **SAVE** after a successful run. Reaching the sword alone does not create a manifest, increment the count, or upload a file.
- Press **X** while recording to discard an attempt. It should reload the task state and begin the retry countdown.
- The existing 447-frame smoke run will count as `1/5`; the two older incomplete captures do not.

## Next work

1. Run four real house-to-sword examples with two sustained urchin pushes and the specified L2/R2 markers. Confirm each creates a manifest and archive on the Studio.
2. Add post-upload curation: unpack an incoming archive, verify manifest/frame/action agreement, and produce a canonical curated episode directory.
3. Add task-level automatic success checks where reliable, starting with `sword_level > 0` for this route. Human SAVE should remain the final assertion until those checks are trusted.
4. Restore the broader playlist after the recorder checkout: Octorok defense, standard slashes, spin slashes, cave crystal/block navigation, and the full toadstool route.
5. Add a training ingestion job that converts completed curated demonstrations into observation/action windows with tag-centered samples.

## Relevant commits

- `ea0f985` — timed task playlist
- `34e19a3` — local launcher checkout resolution
- `f692c02` — task layout and controller setup
- `1776df4` — L2/R2 tags and X discard mapping
- `3ea0dfe` — resizable window and bottom task card
- `9d65b4c` — local integrity inspector
- `be51192` — persistent completed counts, manifests, live tag counters, and Studio SSH upload
