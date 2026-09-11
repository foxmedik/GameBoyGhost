# GameBoyGhost — RICE session handoff

Prepared 2026-09-10. RICE means **Role, Instructions, Context, Expected outcomes**.
This document preserves the current working state and intended next experiment for a fresh session. Read `PROJECT_HANDOFF_v2.md` for the broader project requirements; this document supplies the latest experimental state and immediate priorities. Recheck configs and reports if work has advanced since this snapshot.

## R — Role

You are the research and implementation partner for GameBoyGhost, a dataset-first Game Boy agent starting with Link's Awakening DX. Work in `/Users/studio/Developer/GameBoyAgent`.

The long-term goal is a general game-playing agent, with independently verified game completion as the headline benchmark. Keep planner and controller separate, record harness privilege, preserve reproducible replay/resume, and distinguish teacher assistance from learned capability. Current experiments use a privileged **D harness** and scripted known goals; full-game completion has not been evaluated.

Continue concrete, bounded experiments autonomously within the user's instructions. Preserve successful behavior while improving weak skills. Use evidence from local code, frozen plans, reports, and exact replay; do not infer success from an attractive video or aggregate score alone. Do not restart the broad architecture or research program just because the conversation is new.

The user is clearing conversation context, not asking to reset files, discard work, or start over. This handoff request itself does not authorize starting another batch before the new session.

## I — Instructions for the next working session

### Immediate objective: selective sword use that understands terrain

The user noticed frequent sword swings in a teacher demonstration, suggested enemy distance, authorized a large 48-session comparison, then pointed out that much of the foliage is cuttable. The intended behavior is:

> Swing when a nearby or approaching threat warrants it, or when cuttable foliage obstructs intended movement and can be reached by the sword. Skip unnecessary swings on clear ground.

Implement and evaluate this in the **data-collection teacher first**. The existing distance-only gate failed and must not become the collection default or learned runtime behavior. Terrain detection, sword reach/facing geometry, and threat approach prediction are **not implemented yet**.

1. Read `docs/PROXIMITY_SWORD_48_V1.md`, `reports/proximity-sword-48-v1.json`, `scripts/proximity_sword.py`, and `scripts/evaluate_proximity_sword.py`.
2. Derive cuttable tile identities, map-to-world coordinates, and sword cutting/reach rules from the matching local disassembly and baseline environment. Inspect `minimap_object` / `minimap_info` and the actual terrain-cutting handlers. Do not guess tile IDs or hardcode the known failure coordinate.
3. Start with a small, independently testable predicate for reachable cuttable terrain in the intended movement path. Account for facing and actual sword reach. Preserve dialogue, other item inputs, and the movement rule. Avoid redundant presses during an active swing where appropriate.
4. Inspect the two damage regressions before choosing threat handling. A static 32-pixel radius is insufficient evidence of safety. Consider a threat's closing motion over the next action interval; verify available state and units before using it. Prefer separately measured changes or ablations so foliage and threat effects remain interpretable.
5. Freeze a new versioned teacher experiment, for example `runs/proximity-sword-48-v2`, before execution. Keep the v1 artifacts immutable. Use the same 48 known cases, identical complete start fingerprints, 128-action budgets, existing goal tolerance, and independent exact final replay. Two arms mean **96 rollouts**, not 48 total rollouts. If adding an ablation arm, record the changed total explicitly.
6. Count actual sword-animation starts frame by frame, sword presses, goal successes, per-case damage, deaths, actions, and emulator frames. Preserve allowed/suppressed reasons and paired traces. Inspect all lost successes and damage increases, not just the aggregate.
7. Adoption requires materially fewer swings, **no lost baseline successes**, no per-case damage increases, and no new deaths. Compare against cadence, not merely against the already rejected proximity gate. Cadence has nonzero damage, so do not describe matching its damage as damage-free.
8. If the teacher experiment fails, record rejection and diagnose it. Do not train on a knowingly regressing teacher merely because it is quieter. If it passes, collect verified demonstrations and plan one fixed candidate with broad preservation supervision before training.
9. Any learned candidate must pass all known local, route, continuous-chain, and exact-resume gates against selected **route v7** before selection changes. Fewer swings alone is not a promotion criterion.

After this teacher/data work, the major navigation objective remains learning the physically demonstrated cliff detour and completing all nine routes without losing existing successes. Do not silently insert teacher waypoints or coordinate-specific recovery into the learned runtime to claim that objective is solved.

### Optional asset research: sprites and terrain tiles

The user asked whether a full sprite set would help this game and training for future games. Treat this as a useful research direction, not a prerequisite or a demonstrated improvement. The selected controller consumes structured features; collecting sprite images alone does not change its inputs or improve its weights.

User-provided asset reference: https://www.spriters-resource.com/game_boy_gbc/thelegendofzeldalinksawakeningdx/ . Search-index listings confirm Overworld Tileset, Map Objects, Link, and Overworld Map (GBC) entries. Initial direct page retrieval returned HTTP 403; the user later supplied local sheets, inventoried below. Start with the Overworld Tileset listing at https://www.spriters-resource.com/game_boy_gbc/thelegendofzeldalinksawakeningdx/asset/9445/page-1/ for visual foliage reference. Cross-check appearance against the running DX game and matching source; images alone do not establish collision, cutting behavior, or sword reach. A full world map would add privileged layout knowledge if supplied to the agent, so keep its use separate from perception evaluation.

For the immediate foliage problem, a terrain **tileset plus collision/cuttable metadata and coordinate mapping** is more directly useful than character/enemy sprites alone. Matching source and observed before/after cutting events can establish these labels. A sprite/animation atlas could help identify enemies, attack states, and visual examples for a future perception model, but isolated images omit movement, timing, occlusion, collision, and whether an action actually worked.

For cross-game work, prefer a reusable perception interface for properties such as obstacle, traversable space, threat position/motion, and interaction outcome. Use game-specific asset knowledge as teacher annotation or auxiliary supervision, and train/evaluate on real gameplay frames and action outcomes. Test unfamiliar rooms/appearances and eventually held-out games; do not infer transfer from memorizing this game's tile IDs. A structured-state versus structured-state-plus-vision comparison belongs to the existing broader project plan.

The user subsequently supplied downloaded sheets in `docs/tilesets`. They reported `/Volumes/Developer/GameBoyAgent/docs/tilesets`, but that volume path does not exist in the current session; the files are available at **`/Users/studio/Developer/GameBoyAgent/docs/tilesets`**. Inspection found 31 PNG/GIF images (32 total directory entries), including Overworld Tileset, Map Objects, Link, Minor Enemies, Weapons/Items/HUD, dungeon/house tiles, and full map/background images. The Overworld Tileset was visually inspected and contains terrain and vegetation reference art. Other images were inventoried by filename and dimensions, not individually visually validated. The earlier web retrieval limitation does not apply to these now-available local files.

Prioritize the files ending `Tilesets - Overworld Tileset.png` (410×427), `Tilesets - Map Objects.png` (517×354), `Playable Characters - Link.png` (533×361), and `Enemies & Bosses - Minor Enemies.png` (420×900). Sheet layout positions are not game tile IDs. Full map images must not silently become learner navigation knowledge. No new vision model or asset publication has occurred. Do not delay the bounded terrain-aware teacher experiment to build a complete asset library. Keep these reference assets local unless publication is explicitly requested.

### Latest discussion: how the assets help and useful additional examples

The controller does not currently train directly on tileset images. The immediate route is to match visual terrain references to verified game IDs/behavior, improve the collection teacher, record successful state/action trajectories, and train from those demonstrations. A future vision model could use sheets to help label real gameplay frames, but this requires a separate input/training experiment. Appearance alone does not establish collision, sword reach, threat timing, or cross-game transfer.

If the user wants to contribute more, prioritize short replayable demonstrations of foliage cutting versus uncuttable obstacles, combat approach/attack/retreat versus safe non-attacking movement, and successful cliff loops from varied starts. Failure timestamps in existing videos are also useful. Capture emulator state, button inputs, timing, provenance, and enough replay context to reconstruct exact observations; video alone is less useful for action supervision. A human-input demonstration recorder has been suggested, not implemented or verified in this session. Existing recording code produces a verified teacher replay video and should not be mistaken for that human-input recorder.

No additional assets or human demonstrations are required before continuing the bounded teacher experiment. The user has supplied enough artwork to begin; the next work is source-grounded terrain mapping, teacher improvement, and the frozen 48-case paired evaluation. No training or new batch was run during the handoff/asset discussion.

### Invariants

- Preserve existing uncommitted and untracked work. Do not reset, clean, or overwrite historical run directories.
- Keep ROMs out of Git and uploads. Never force-add ignored runtime artifacts. Never recursively upload the project root to Hugging Face.
- Never place credentials in this document, source, logs, commands, or uploads. Use normal local authentication if publishing is later requested.
- Keep the 96 reserved evaluation specifications untouched. All current panels are known development/training regressions, not held-out evidence.
- Use `configs/navigation_retired_cohorts.json` for future untouched-panel exclusions. The registry contains 126 retired cohorts at this snapshot.
- Preserve source snapshots, hashes, action prefixes, and exact fingerprints. A savestate alone does not reproduce all host/framebuffer state; full physical replay matters.
- Freeze training/evaluation choices in advance. Use the designated final-epoch candidate; no checkpoint shopping.
- Keep the learner's original goal in training inputs even when a privileged teacher uses intermediate waypoints for collection.

## C — Context and verified current state

### Selected navigator

`configs/navigation_experiment.json` is the selection source of truth:

| Item | Current value |
| --- | --- |
| Status | `experimental_not_default` |
| Selected checkpoint | `runs/navigation-routes-v7/model/epoch-008.pt` |
| SHA-256 | `6d26dcd6a2d7b22c0681d7e7a0c9b9d3f27c9d8caccbeca94426be0da97fc062` |
| Feature contract | `structured-goal-250-v1`, previous movement masked |
| Original local panel | 46/48 |
| Additional local panel | 43/48 |
| Fresh local panel | 46/48 |
| Complete routes | 6/9; 30/36 waypoints |
| Original continuous precise-goal chains | 3/3 |
| Navigation damage / deaths | 0 / 0 |

All 135 known safe local successes across 144 cases are preserved. The three beach-return and three west-return routes succeed. All three room-loop starts still time out at the third goal, above the cliff.

The older fallback is **focused v4**, `runs/navigation-focused-v4/model/epoch-008.pt`. It is different from the rejected **route v4** experiment. `configs/navigation_route_candidate.json` describes the latest rejected route v8 candidate, not the selected policy. A report's `promoted` field is a gate result; verify the actual selection config too.

The model is a 250-input, 256–256 feedforward MLP with eight outputs: five movement and three button choices. It uses fixed normalization and masks previous movement at feature index 3. `src/gameboy_agent/navigation.py` owns encoding, `NavigationNet`, and `NavigationController`. Goal completion requires the same room and Manhattan distance at most eight pixels.

`scripts/control_context.py` supplies normalized x, y, dialogue, previous movement, and previous button. `TrainingEnv(..., sword_curriculum=False)` avoids ending the episode at sword pickup. Continuous chains do not reset at goal handoff. The fixed sword controller remains `configs/sword_controller.json`, using `runs/tree-clean-route-v3/policy.json`.

### Latest completed experiment: proximity sword v1

`configs/proximity_sword_experiment.json` says **rejected_for_adoption**. No training occurred and runtime behavior was not changed.

The experiment used the original 48 known development cases: 24 same-room and 24 cross-room, across house, beach, and approach starts. Both arms used `navigation_recovery.teacher(state, goal, None, step, 0, {})`, a goal-directed movement rule with alternating sword presses. The experimental arm only suppressed proposed sword presses. All matched starts and all 96 independent final replays matched exactly.

| Metric | Cadence teacher | Distance gate |
| --- | ---: | ---: |
| Goal successes | 41/48 | 36/48 |
| Actual sword-animation starts | 747 | 93 |
| Sword-press actions | 747 | 93 |
| Damage, raw health units | 4 | 12 |
| Deaths | 0 | 0 |
| Navigation actions | 1,529 | 1,760 |
| Emulator frames | 16,318 | 23,794 |

Swings fell 87.6%, but six successes were lost and one was gained. Two cases took four additional raw health units each. Changing sword actions also changes terrain, timing, and subsequent movement decisions even though the movement rule is identical.

The gate requires a nonzero-status whitelisted hostile entity within 32 Euclidean pixels. NPCs and pickups are excluded. It preserves dialogue and other item inputs and suppresses presses during animation states 1–4. There were 775 suppressions for no nearby threat, 93 allowed nearby-threat presses, and 892 unchanged actions. **No active-animation suppressions occurred**, so that condition's benefit was not established. Facing, closing-speed prediction, terrain, and full entity classification were absent.

Confirmed foliage failure: case `763b4286fbad9a9da88b05c5193e729a743e00489d7a93e95683e45a0a961ebe`, goal E1 (92,26), stalls at (82,39) below intact bushes under the distance gate. Cadence cuts the bushes and succeeds. Independently replayed paired images are in `runs/proximity-sword-48-v1/diagnostics/`. This explains one failure, not necessarily all six.

Another timeout is case `2b70007c69c8e7a7faa9399a6eea7e76e799e097862a30690fafdf1f90fa4f51`: target D0 (55,131), ends in E0 (55,16). Damage-increase cases are `a45a26acffba91348ea082faed603b2f2768dafade8d4071f8255b98d55a5439` and `ad819075151c6872ba4622cf0b6f321940e4f0ad957e2172c3da14a0bf760fcb`. The portable report contains all paired case results.

Relevant files: `scripts/proximity_sword.py`, `scripts/evaluate_proximity_sword.py`, `scripts/inspect_proximity_failures.py`, `tests/test_proximity_sword.py`, and the v1 report/doc/run directory.

### Verified read-only game state and research starting points

| State | Address / interpretation |
| --- | --- |
| Link x / y | `0xFF98` / `0xFF99` |
| Link direction | `0xFF9E`: 0 right, 1 left, 2 up, 3 down |
| Entity x / y | `0xC200+i` / `0xC210+i` |
| Entity status / type | `0xC280+i` / `0xC3A0+i` |
| Sword animation | `0xC137`: 0 none, 1 draw, 2 swing start, 3 middle, 4 end, 5 holding |

Sword item ID is 1; the selected item may occupy A or B, represented by button choice 1 or 2. Use the existing helper rather than assuming A is always the sword. Actual animation starts are measured through PyBoy ticks inside the normal readiness/transition loop, not inferred from button counts alone.

Local references:

- `references/LADX-Disassembly/src/constants/entities.asm`
- `references/LADX-Disassembly/src/constants/directions.asm`
- `references/LADX-Disassembly/src/constants/gameplay.asm`
- `references/LADX-Disassembly/src/constants/memory/wram.asm`
- `references/LADX-Disassembly/src/constants/memory/hram.asm`
- `references/LADXExperiments/experiments/gym_env/link_awake_env.py`, especially `get_entities_info`, `get_entities_obs`, and minimap construction.

Entity observation distance is scaled; do not interpret it as raw pixels. The existing proximity experiment uses raw coordinates. Cuttable tile IDs and geometry remain to be derived from matching source.

### Navigation history and why preservation matters

Route v1–v5 repeatedly traded gains against local damage, timeouts, or lost routes. Route v6 added all 135 successful local action anchors and action-margin supervision, fixing local preservation but leaving a west return timeout. Route v7 added 20 targeted return paths and achieved the current six safe routes. See `docs/NAVIGATION_LIVE_PRESERVATION_V6_V7.md` and the versioned route reports.

Route v8 added physically verified cliff approach/return demonstrations. Its learned result was **4/9 routes**, losing two v7 west-return successes while still failing every cliff goal. Local scores were 46/48, 44/48, 46/48 with zero damage/deaths; that additional local gain did not override route regressions. v8 was rejected. Selected v7's additional score remains 43/48.

The teacher can physically complete the cliff loop from all three starts. It exits lower E2 into E1, uses the narrow western passage near x=126, then re-enters upper E2. Five safe approaches and 15 continuous safe returns were found after failed searches. Intermediate waypoints are collection assistance only. See `docs/NAVIGATION_CLIFF_V8.md`, `scripts/collect_cliff_detour.py`, `scripts/collect_cliff_returns.py`, `scripts/finalize_cliff_returns.py`, and `scripts/navigation_cliff_training_v8.py`.

Training is in `scripts/train_navigation_routes.py`: fixed eight epochs, masked inputs, original-data/prior-path KL retention, shortest-observed-suffix action labels, balanced sampling, and demonstrated-action margin 0.25 with weight 2 (button contribution 0.25). Provenance distinguishes inherited collection policies. Repeated narrow corrections caused regressions; retain broad successful-action anchors.

### Evaluation and data map

`configs/navigation_routes_v1.json` contains four-goal routes, tested from house, beach, and approach:

- Room loop: E2 (36,121) → E2 (89,94) → E2 (64,64) → E2 (36,121).
- Beach return: E2 (36,121) → F2 (68,18) → F2 (118,90) → E2 (36,121).
- West return: E2 (36,121) → E1 (131,110) → E1 (88,45) → E2 (33,101).

Each route goal has a 256-action budget. `scripts/run_navigation_route.py` executes continuous routes and strict physical-replay resume; `scripts/route_progress.py` manages cursor/budget/death ordering. `scripts/report_navigation_routes.py` gates prior complete-route successes, prior safe local successes, damage/deaths, three original chains, and exact resume.

The ignored `runs/navigation-routes-v8/evaluation_driver.py` is a useful full-gate example using selected v7 as baseline. Historical drivers can contain older baselines and hardcoded run paths: inspect and adapt them; do not overwrite or blindly rerun them.

| Panel | Cache | Baseline artifacts |
| --- | --- | --- |
| Original 48 | `runs/navigation-cache-v2` | `runs/navigation-live-v2` |
| Additional 48 | `runs/navigation-recovery-dev-v1` | `runs/navigation-recovery-baseline-v1` |
| Fresh 48 | `runs/navigation-live-correction-v3/fresh-panel` | `runs/navigation-live-correction-v3/fresh-parent` |

`scripts/evaluate_navigation.py` supports cache, checkpoint, new output directory, workers, and baseline arguments. `scripts/report_navigation_recovery.py compare` matches keys/fingerprints and reports gained/lost successes and damage. Inspect `--help` before composing a new invocation.

Raw workset: `runs/data-workset-16m-v1`, 16,777,216 rows and 8,133 episodes. Curated data: `data/curated/ladx-navigation-v1`. Original navigation cache: 346,536 training rows. The 135 local successes have become preservation/training anchors; none of the three panels should be described as untouched generalization. Future panel freezing in `navigation_recovery.py` and `navigation_live_correction.py` automatically unions the retired-cohort registry.

### Video artifacts and their meaning

`runs/videos/cliff-loop-demonstration/cliff-loop.mp4` is a roughly 67-second, silent, verified **teacher-demonstration replay**, starting after sword acquisition and completing all four goals without damage. It is not a trained-policy success.

The sharing version is `runs/videos/cliff-loop-demonstration/cliff-loop-share.mp4`: 320×344, 30 fps, 614,087 bytes, about 68% smaller than the 1,898,668-byte original. Both fully decoded successfully. The folder contains provenance `manifest.json`, poster, and preview. `scripts/record_cliff_loop.py` records through the normal emulator loop with exact final-fingerprint verification. The user's observation of sword spam in this clip motivated the current work.

### Environment, verification, and repositories

- Machine has 256 GiB RAM and historically reported 32 cores. Eight emulator workers have been used successfully. Benchmark concurrency rather than assuming 48 simultaneous workers is best.
- Use `.venv-ladx/bin/python` (Python 3.11, Torch 2.2.2, NumPy 1.26.4, PyArrow 21). This environment has no pip module; if needed, use `/opt/homebrew/bin/uv pip install --python .venv-ladx/bin/python PACKAGE`.
- Optional video dependency `imageio-ffmpeg` is installed; locate its binary with `imageio_ffmpeg.get_ffmpeg_exe()`. `.venv-hub` is the publishing environment.
- Last full suite before proximity additions: **50 tests passed**. Six new proximity tests subsequently passed separately. Do not claim a combined 56-test full run has already happened. Run `.venv-ladx/bin/python -m unittest discover -s tests -v` when appropriate for new changes.
- All 96 proximity trajectories were independently replay-verified. No active batch or automation is awaiting continuation at handoff.
- GitHub source: https://github.com/foxmedik/GameBoyGhost
- Hugging Face dataset: https://huggingface.co/datasets/foxmedik/GameBoyGhost-LADX
- `logo.png` was published to both repositories.
- Verified HF release `ladx-collection-v1`: 16,777,216 rows, 8,133 episodes, 64 shards, 83 verified files. `configs/artifact_repositories.json` pins the release revision; later logo changes do not invalidate that immutable release pin.
- Model weights and later correction data remain local. A fresh clone alone is insufficient. Read `docs/ARTIFACT_STORAGE.md`; local references, ROM, ignored runs, and checkpoints are required for reproduction. `configs/references.lock.json` records reference revisions; bootstrap scripts may otherwise follow upstream heads.
- Publishing uses explicit export/upload allowlists (`scripts/export_hf_dataset.py`, `scripts/upload_hf_release.py`), never `hf upload ... .` from the project root.

There is substantial uncommitted work. At handoff, modified tracked files include `README.md`, `configs/navigation_experiment.json`, `scripts/navigation_live_correction.py`, and `scripts/navigation_recovery.py`. New route v1–v8/proximity reports, configs, docs, collection/evaluation/training scripts, and tests are untracked. Preserve them all. This handoff does not include a commit or upload.

`.gitignore` already excludes case-insensitive GB/GBC/GBA/ROM extensions, saves, RAM/state files, references, virtual environments, data, runs, checkpoints, model weights, array/shard files, caches, and environment secrets. Keep these safeguards intact.

## E — Expected outcomes and restart checklist

The next implementation session should deliver a source-grounded terrain-aware sword predicate, meaningful tests, a frozen paired experiment with complete replay/provenance, a portable per-case report, and a short decision document. State clearly whether it passes adoption and what remains unresolved. Preserve selected v7 unless a separately trained candidate passes the full preservation gate.

Begin by checking the actual workspace rather than reconstructing artifacts from chat:

```sh
pwd
git status --short
cat configs/navigation_experiment.json
cat configs/proximity_sword_experiment.json
cat docs/PROXIMITY_SWORD_48_V1.md
```

Then inspect the gate/evaluator and matching terrain source, write the new experiment plan, and proceed with the bounded next step above. Historical artifacts are evidence, not instructions to rerun every prior experiment.

Suggested first message in the new session:

> Read RICE_SESSION_HANDOFF.md and PROJECT_HANDOFF_v2.md in /Users/studio/Developer/GameBoyAgent. Continue the terrain-aware selective-sword teacher experiment described in the handoff. Preserve selected route v7, all existing uncommitted work, ROM exclusions, and evaluation boundaries. Derive foliage and sword-reach rules from matching source, then run and report the frozen 48-case paired comparison before considering new training.


## Continuation update — terrain-aware sword v2 completed

This update supersedes the earlier immediate-next-experiment status. See `docs/PROXIMITY_SWORD_48_V2_RESULTS.md` for the decision and `docs/PROXIMITY_SWORD_48_V2.md` for the frozen protocol.

- Completed 48 cases in three arms (144 rollouts), with all independent exact final replays and paired/historical cadence fingerprints matching.
- Cadence: 41/48 success, 747 swings, four raw damage units, zero deaths. Terrain+exit guard: 42/48, 263 swings, eight damage units; rejected. Terrain+exit+motion: 42/48, 250 swings, four damage units, no lost baseline successes or per-case damage increases/new deaths; passed the frozen teacher gate.
- Source-grounded live foliage handling is in `scripts/terrain_sword.py`; four foliage-authorized presses per experimental arm have observed tile changes. Exit uncertainty preserves proposed presses near room boundaries. Linear motion is separately ablated. No claim of general combat safety or learned capability.
- All 62 tests pass. Disassembly rebuilt ROM and runtime ROM match exactly; actual revision addresses come from `azle-r1.sym`, not the sometimes-offset source comments.
- Collected 42 zero-damage successes / 290 feature-action rows, physically replayed twice with exact experiment fingerprints. Manifest: `runs/sword-teacher-v2-demonstrations/manifest.json`.
- Froze **one untrained candidate** at `runs/navigation-sword-v1/plan.json`: selected v7 parent, eight epochs, final epoch only, LR 5e-6, broad preservation (202 inherited paths / 6,773 rows), retention and action margin. All input hashes, 250-feature shapes and action labels validated. No model directory exists and no training ran.
- Next bounded work: train that fixed candidate, then run all known local, route, original-chain, and exact-resume/replay gates against selected route v7, plus the planned paired learned-sword metric. Reject any preservation regression; no checkpoint shopping. Teacher success does not authorize claiming the learned cliff detour is solved.
- Selected navigation config remains route v7. v1 artifacts, reserved evaluation, ROM exclusions, and existing uncommitted work were preserved. Nothing was committed or uploaded.


## Continuation update — learned sword candidate v1 completed and rejected

The user authorized training the frozen candidate. Eight fixed epochs completed; only epoch 008 was evaluated. See `docs/NAVIGATION_SWORD_V1.md`. The previous update's untrained status is superseded; the original frozen plan remains immutable.

Candidate local scores: 42/48, 42/48, 47/48 versus selected v7's 46/48, 43/48, 46/48. Five safe successes lost, one gained, four extra raw damage units in a separate still-successful case, no deaths. Routes drop from 6/9 to 4/9, losing west returns from beach and approach; waypoints drop 30 to 28. Original chains stay 3/3. Original 48-case actual swings drop only 582 to 568 (2.4%), missing the 25% gate.

All 192 local rollouts and all nine routes/three chains have independent exact final replays. Original v7 rerun fingerprints match historical results; paired starts match. Route and chain paused/resumed results exactly match uninterrupted runs. Evaluation completed without reserved cases. Full per-regression audits are in `reports/navigation-sword-v1-audit.json`.

The candidate is rejected in `configs/navigation_sword_candidate.json`. Route v7 remains selected. Teacher v2 still passes its distinct teacher gate; learned transfer remains unresolved. Next hypothesis: freeze shared representation and movement outputs and train only button outputs, with a new frozen experiment and unchanged preservation gates. No second candidate or new training plan was executed.


## Continuation update — button-only sword v2 completed and rejected

Following agreement with the button-only experiment, froze and trained `runs/navigation-sword-v2`: same v1 data/hyperparameters, selected v7 parent, eight fixed epochs, only final button rows trainable. Protected movement/shared tensors are asserted after every step; final protected bytes, normalization, mask, and movement logits on all 7,063 training rows match v7 exactly. All 64 tests pass.

V2 scores: 45/48, 43/48, 46/48, zero local damage/deaths; one original local success lost. Routes: 3/9, 27/36 waypoints, all three west returns lost, four raw damage units in beach-start room loop, no deaths. Original chains remain 3/3. Actual swings: 582 to 579 (0.5% reduction). All 192 local rollouts and nine routes/three chains independently replay exactly; both route and chain pause/resume checks match uninterrupted outputs.

Rejected in `configs/navigation_sword_v2_candidate.json`. Selected v7 and all prior artifacts remain unchanged. Read `docs/NAVIGATION_SWORD_V2.md` and portable reports/audit. Freezing movement prevents direct weight drift but does not prevent timing/state changes from button choices. Proposed next diagnostic: test teacher sword suppression while following v7's own movement decisions, before collecting more demonstrations or training again. No such experiment has run.


## Continuation update — v7-movement teacher diagnostic completed and rejected

User authorized the proposed diagnostic. Ran `runs/v7-sword-teacher-v1`: unchanged selected v7 versus v7 with existing `terrain_sword.gate(motion=True)` suppressing only proposed sword presses. Same 48 known cases, 96 rollouts, all exact final replays, paired starts and historical v7 fingerprints match.

V7: 46/48 success, 582 swings, zero damage/deaths. Gated v7: 35/48, 233 swings (60.0% reduction), 12 raw damage units, one death. Eleven successes lost, no gains; two damage-increase cases. Reject for collection. No demonstrations curated or training performed; selected v7 unchanged. Read `docs/V7_SWORD_TEACHER_V1.md` and corresponding portable result/audit.

Read-only counterfactual queries at three physically replayed failure states tested previous-button input. Changing none to A stops the sword proposal but does not change stuck movement in any of these three states. This does not support spoofing history as a remedy. No such action was executed; exact fingerprints remain unchanged. Details: `reports/v7-sword-button-history.json`.

The selective gate is unsafe with v7 before training, so another fine-tune from these paths is not justified. Next research must address navigation under different sword timing/state distributions, with a fresh frozen protocol. Do not claim a proven root cause or safe fix. Preserve all rejected artifacts and the earlier independently passing straight-line-teacher result as distinct evidence.


## Current priority — sword reduction paused; navigation reliability resumed

User agreed to keep selected v7, retain experimental artifacts, pause sword-reduction work and refocus on navigation reliability. No rollback was needed because no failed candidate had been selected. `configs/research_focus.json` records this project priority; it is not a runtime toggle. Do not restart sword-reduction experiments without a new user instruction.

The navigation objective is the demonstrated cliff detour / all nine routes, with all six v7 routes, 135 safe local successes, original chains and exact resume/replay preserved. No new training run started in this priority-change session.

A read-only audit verified all 20 cliff demonstration manifests, feature/action hashes and original goals. Five approach paths contain 956 rows; 15 returns contain 1,597. V8 matches 59.6% of approach movement labels and 73.9% of return labels versus v7's 41.9% / 35.4%. V8 matches only three of five approach opening movements and two of fifteen return opening movements. Training-row agreement is not live success. The raw demonstrations contain 87 exactly identical masked-input states with different successful movement labels; these may be valid alternative routes, not necessarily bad data or proof that memory is required. Existing shortest-suffix curation already chooses one label per input; inspect how these alternatives affect consistent route supervision before proposing a fix.

Audit: `reports/cliff-navigation-audit-v1.json`, generated by `scripts/audit_cliff_navigation.py`. Next bounded work is entry/label diagnosis and a coherent frozen navigation experiment, not another sword gate or an unexamined repeat of v8 training.


## Continuation update — cliff supervision repaired; navigation v9 rejected

User authorized the entry/label investigation and navigation experiment. Sword reduction remains paused. Read `docs/CLIFF_SUPERVISION_REPAIR.md` and `docs/NAVIGATION_ROUTES_V9.md` before continuing.

Exact curation audit corrects the earlier raw-opening interpretation: v8 already chooses the curated movement at all three v7 cliff handoffs. Physical exact-label lookup reaches uncovered states after 2 house actions and 54 beach actions; approach safely completes in 136. Some shortest-suffix splices work, others expose coverage gaps. Raw ambiguity alone does not establish bad data or a need for memory. The v8 approach handoff has matching coordinates but different encoded state and no exact curated entry.

Collected fresh, independently replayed feature trajectories using fixed source continuations. V7 approaches safely complete in 197/191/136 actions. Tested three frozen distinct return templates per repaired origin: seven of nine safe successes; canonical returns use 87/86/87 actions. Six canonical paths contain 784 rows and retain 22 movement-conflicting masked states. Duplicate v8 house/beach origins are excluded from canonical data; v8 approach continuation takes four damage units and is excluded. Continuous return prefixes and origin fingerprints are verified.

Froze and trained one v9 using unchanged v8 architecture/training settings, replacing 20 cliff paths with six repaired paths and retaining 202 preservation paths. Eight epochs, final epoch only. Combined 208 paths / 7,557 rows / 5,447 curated states. Original frozen plan remains immutable even where its pre-training status fields describe the freeze time.

Completed v9 evaluation: local panels 46/48, 43/48, 46/48, all 135 safe v7 successes preserved with zero damage/deaths. Routes fall from 6/9 to 3/9 and waypoints from 30/36 to 27/36: all beach returns pass, all west returns regress, all cliff loops still fail. Original chains remain 3/3. All 192 local and 12 route/chain runs replay exactly; both pause/resume checks pass. Candidate rejected in `configs/navigation_v9_candidate.json`; v7 remains selected and no rollback is needed.

Portable results and audit: `reports/navigation-routes-v9.json`, `reports/navigation-routes-v9-audit.json`. Canonical data and immutable plan are under ignored `runs/navigation-routes-v9`; original collection reports are `reports/cliff-splice-repair-v1.json` and `reports/cliff-splice-returns-v1.json`. All work is known development; reserved evaluation untouched. No commits, uploads or deletion of historical artifacts.

Next bounded investigation: diagnose actual learned cliff stalls and west-return regressions before another training candidate. Do not mistake repaired scripted teacher paths or higher training agreement for learned cliff completion. `configs/research_focus.json` records the rejection and continued navigation priority. Do not restart sword reduction without new user instruction.


## Current selection — cliff specialists v2, all nine routes pass

User asked to resolve the cliff stalls. Completed diagnosis, two fixed learned specialist candidates, bounded teacher probes, fresh live corrections, full preservation evaluation and a learned replay video. This update supersedes the previous selected-v7/unsolved-cliff status. Read `docs/NAVIGATION_CLIFF_SPECIALISTS.md`.

Selected checkpoint: `runs/navigation-cliff-specialists-v2/model/epoch-256.pt`, SHA-256 `9d2b24b28be5289fc3d32d85d46faa1835ca2068d73a1e8790630d77dbaf85ec`. Configuration: `configs/navigation_experiment.json`; status remains experimental_not_default. It contains the frozen v7 fallback and two same-architecture feed-forward experts keyed by the exact original final goals E2 (64,64) and E2 (36,121). Existing 250-feature contract, normalization and previous-movement mask are unchanged. No runtime teacher waypoints, route index, demonstration cursor, search or scripted action sequence. Known-goal specialization is not general navigation or game completion.

Diagnosis physically verified v9's goal-aligned upward stall under the cliff and all three v7 failures from safe teacher cliff endpoints. A first specialist candidate trained on existing data reached 7/9 routes, 32/36 waypoints, preserving all six v7 routes and 135 safe local successes. Beach cliff loop passed; house oscillated in upper E2 and approach oscillated in E1. That intermediate checkpoint remains eligible and preserved.

A separate clean-teacher lane probe produced nine safe 99–103-action approaches, but only one safe continuous return. A second return probe produced one safe success out of nine. These diagnostic paths are excluded from v2 training: faster safe arrival alone did not establish continuous safety.

Collected corrections on actual v1 trajectories at predetermined failure regions. Canonical house/approach/beach cliff paths have 196/92/159 actions; their unchanged learned-v1 returns complete safely in 73/81/83 actions. All fresh features and final fingerprints independently replay; prefixes connect exactly. Alternate house phase caused three return damage and was excluded. Three canonical cliff paths total 447 rows, plus 14 local-anchor rows; shortest-suffix curation yields 418 states with zero conflicting action labels.

V2 updates only the cliff-goal expert from v1, for 256 fixed epochs with correction-entry weighting. V7 fallback, v1 return expert, normalization and mask are independently verified unchanged. Only final checkpoint evaluated. Training fit 99.5% movement / 100% buttons is supplementary, not the success claim.

FINAL: **9/9 routes, 36/36 waypoints**, local panels **46/48, 43/48, 46/48**, all **135 safe local successes preserved**, **3/3 original chains**, zero local/route damage and deaths. Learned cliff/return actions: house 194/73, beach 157/81, approach 92/81. All 192 local and 12 route/chain runs replay exactly; original v7 historical fingerprints and paired starts match. Three exact pause/resume checks pass, including inside the cliff goal. All 66 tests pass. Results: `reports/navigation-cliff-specialists-v2.json`. Selection updates recorded in `runs/navigation-cliff-specialists-v2/selection.json`; previous config snapshot preserved there.

Verified learned house-loop recording: `runs/videos/learned-cliff-loop-v2/cliff-loop.mp4`, 64 seconds, silent, native emulator speed plus two-second end hold. Actual final fingerprint matches the successful learned run; representative frames visually checked. This is not a teacher recording.

Sword reduction remains paused and the fixed sword controller is unchanged. All cases are known development; 96 reserved evaluation specifications remain untouched. V7, rejected candidates, teacher artifacts and all pre-existing uncommitted work are preserved. No commits or uploads. Next work, if requested, should freeze a separate development stress protocol for these exact-goal specialists before broader claims. Do not resume sword reduction automatically.


## Continuation update — varied-start cliff stress test completed

User approved testing varied starting positions. Froze and ran 60 cases at `runs/navigation-cliff-stress-v1`: three known starts × four anchors (cliff entry, first western-room entry, upper-room re-entry, return entry) × unchanged control or four physical up/down/left/right setup actions. No teleports or RAM edits. Setup alternates the equipped sword; perturbations change timing/facing/combat state as well as position. Original remaining final goals are unchanged; each receives 256 learned actions starting at the stress handoff, with prefix/setup outside that budget.

RESULT: all **12 controls** reproduce historical action suffixes and final fingerprints safely. All **48 perturbed setups** are valid and cause zero damage; **43/48 complete**, **34/48 safely**, **9 complete with damage**, **5 time out**, **zero deaths**. Each damaged case loses four raw units (36 total). There are 48 unique perturbed initial fingerprints; 45 positions change and three movements are wall-blocked. All 60 independent physical replays and per-action feature comparisons pass. Strict stress gate fails.

By anchor, safe successes are cliff entry 8/12, western corridor 9/12, upper re-entry 8/12, return entry 9/12. Eight of nine first-damage events and three of five timeouts occur on the return goal; two timeouts are on cliff approach. All three downward cliff-entry shifts fail safe completion. All four house upper-entry shifts finish with damage. Two damaged cases had no setup position change, so do not claim position alone is the cause.

Read `docs/NAVIGATION_CLIFF_STRESS_V1.md`, `reports/navigation-cliff-stress-v1.json`, and `reports/navigation-cliff-stress-v1-audit.json`. Frozen plan SHA-256: `d615beb326b12a7888f3e413f611108ce682ea3bcbae59f1b3c4e03d78d2f3eb`. Latest-supervision input-match counts are a limited diagnostic, not proof of absence from all pretraining. These are fresh development perturbations of known routes, not reserved evaluation or unseen maps/goals.

Selected cliff-specialists-v2 remains unchanged, SHA-256 `9d2b24b28be5289fc3d32d85d46faa1835ca2068d73a1e8790630d77dbaf85ec`; original 9/9 route result remains valid. Selected config, sword config, retired registry, policy and runtime source hashes are verified unchanged. No training, curated correction demonstrations, rollback, commits or uploads occurred. Sword reduction remains paused; 96 reserved evaluation specifications untouched. `configs/research_focus.json` records the stress gaps.

Next proposed work is return safety/recovery under varied arrival states, then lower western-corridor entry recovery. If these stress cases are used for corrections, report them as development regression data and freeze separate stress cases before claiming improved generalization.


## Current priority — strategic reset after process audit

User explicitly requested a full step back to audit training goals, process and resource effectiveness. Completed a read-only evidence audit and wrote `docs/TRAINING_STRATEGY_AUDIT.md` plus reproducible `reports/training-process-audit.json` (`scripts/audit_training_process.py`). No optimizer, gameplay trial, runtime change or reserved-evaluation use occurred.

Main finding: the canonical objective is hierarchical game progression/first dungeon/eventual completion, while recent work optimizes behavior-cloning losses for fixed-coordinate routes. Selected exact-goal specialists are legitimate local tools, not demonstrated general navigation. The default skill planner still switches sword acquisition to scripted novelty exploration; no measured Tail Cave progression or completion result is established. Reproducibility, safety gates and fresh continuous corrections were useful; repeated patching without an explicit milestone link, early distributional tests or stop rules caused drift.

Ledger covers 13 candidates (routes v1–v9, sword v1/v2, specialist v1/v2): 1,872 candidate local cases, at least 2,112 local rollouts including explicit baseline reruns, 117 candidate route rollouts, excluding many teacher searches/replays and older experiments. Each MLP has 132,104 parameters; selected three-network system has 396,312. The large 16,777,216-action collection took 2,389.6 active seconds and wrote 5.316 GiB, but those actions are scripted-exploration data, not optimizer steps or expert demonstrations. Recent total train/eval/human/token/dollar costs are not adequately logged; do not invent totals or extrapolate from epochs.

Recommendation: pause manual cliff/sword tuning; define verified Tail Key/Tail Cave entry from post-sword state, then continuous house-to-milestone progression, then first-dungeon/Full Moon Cello. Establish a baseline and explicit planning/recovery interface before further optimizer work. Verify milestone semantics against matched source and distinguish supplied hints/teacher routes from autonomous planning. Use observed-map/transition memory and generic recovery as a bounded comparator, not a hidden hard-coded cliff walkthrough. If teacher is broadly reliable but learner fails on its own states, automate bounded aggregation of verified corrections; do not simply create another exact-goal expert.

The document proposes a staged experiment charter, validation separation, cost telemetry and stop rules. Its example case counts, thresholds and resource caps are proposals, not an experiment launched or approved by this audit. `configs/research_focus.json` now records navigation training paused pending the progression protocol and sword reduction still paused. Selected specialist v2 remains unchanged. Do not resume the previously suggested 14-case stress-failure repair automatically. Existing artifacts and uncommitted work remain intact; no commits/uploads.


## Confirmed next milestone — Tail Key and Tail Cave entry

User confirmed Tail Key acquisition and Tail Cave entry as the success story and asked how to get there. `docs/TAIL_KEY_ENTRY_PLAN.md` records the concrete sequence: separate honest progression mode and verified milestone fixtures; reusable menu/item/interact skills plus explicit goal manager; bounded post-sword baseline; only then targeted training if a proven blocker requires it; final continuous house-to-key-to-entry proof and varied-start checks. No new gameplay run or optimizer update was performed in this planning turn.

Critical prerequisite found in existing code: automatic powder grant in the witch's hut, powder refill during observation reads, and direct-RAM inventory switching would distort this quest. Preserve old reproduction experiments; disable these in a separate progression mode and revalidate interfaces. Use physical menu/item actions.

Matched-source detector leads: DB4B toadstool, DB4C powder count plus inventory/quest state, DB48 Tarin activity, DB11 Tail Key; exterior Tail Cave room D3 event bit 0x10, interior map00 room17 after settled transition. The inherited Tail Key inventory feature checks FF, while matched chest handling increments possession and the keyhole tests nonzero. Validate actual pickup via a live fixture; do not trust the inherited feature or unverified source comments as a complete detector.

`configs/research_focus.json` now records the confirmed milestone and next implementation step. Selected navigator is unchanged; navigation optimizer work and sword reduction remain paused. The high-level quest sequence is explicit assistance for the first guided baseline; no claim of zero-shot planning or power-on completion. Historical runs, reserved evaluation and prior uncommitted work preserved.

## Provided assets processed — 2026-09-11

User asked to process the tilesets/maps and whether useful now. Added `scripts/process_progression_assets.py`, `docs/PROGRESSION_ASSETS.md`, `reports/progression-assets-v1.json`; updated the Tail Key plan. Generated offline viewer and manifest in `runs/progression-assets-v1`: 31 normalized image references with source hashes, 256 exact overworld room crops, 451 distinct 16×16 RGB appearances with 20,480 occurrence references, full index/atlas and progression-area panel. All source/crop/tile reconstruction checks pass; visually inspected focus panel. Provided-map assistance explicit; room-number mapping inferred, passability unknown, static blanks/state differences retained. No neural training, live quest run, runtime asset integration or progression-harness changes. Next remains honest progression harness and live reference alignment, then continuous Tail Key/entry baseline.

## Staged execution started — 2026-09-11

User requested a full quantified action plan and to begin implementation. Wrote `docs/PROGRESSION_EXECUTION_PLAN.md` with stage 0–7 qualitative/quantitative gates, assistance disclosures, initial proof versus 18/20 fresh reliability, 10-pair inherited-memory ablation, bounded conditional training (3 candidates/blocker, 250k newly collected decisions/blocker, 1M initial total before review), post-sword 8192 decision/200k frame and house 12288/300k budgets, and single-worker-first M3 resource policy. `configs/progression_protocol_v1.json` is the status/protocol record; stage 1 complete, stage 2 next. Training remains paused.

Implemented new modules `progression.py`, `progression_env.py`, `progression_skills.py`, plus `tests/test_progression.py` and `scripts/validate_progression_interface.py`. Separate env preserves old TrainingEnv; no automatic powder grant/refill/duplicate cleanup, rejects legacy RAM-switch action, keeps read-only structured observations and physical movement/A/B compatibility, adds one-frame Start/Select pulses, inventory readiness, bounded frames/waits and fresh reset. Zero shaped reward. Equip skill uses physical cursor/buttons with observed inventory, supports active-slot transfers, excludes ocarina submenu. Frame journal tracks damage/healing separately, inventory/resource/trade changes, dialogue IDs (NOT decoded text or known speaker), stable room transitions and source-grounded quest milestone candidates. Initial key/open door/entry disqualifies fresh quest; successful entry requires episode acquisition+opening, alive+settled+no dialogue. No cause attribution or full memory planner yet.

Evidence `reports/progression-interface-v1.json`, `reports/progression-interface-v1-regression.json`, docs `PROGRESSION_INTERFACE_V1.md`. 13 interface tests pass including synthetic write-blocked 100-read purity, depleted powder/duplicate slots, raw Tail Key=1, death/false-entry, damage+healing, journal roundtrip, forbidden actions, physical shield equip/reset. Three physically obtained sword fixtures at `runs/progression-interface-v1-verified/`: house 412 sword actions +16 menu actions=428, beach268, approach83; all zero damage. House physically equips sword B then A,12 room transitions,2 dialogue-open events. Independent replay matches every action fingerprint/frame and final journal, including JSON journal roundtrip mid-prefix. Full suite79/79 in37.207s; source and selected policy hashes match. Initial incomplete `runs/progression-interface-v1/` retained after replay argument mismatch; complete evidence is verified directory. No runtime source changes after complete evidence capture.

Still pending: live toadstool/witch/cure/key/unlock/entry fixtures, physical full quest, persistent world memory/planner, exact NPC text decoding, all broader combat/item/trading skills. Historical navigation/70-case sword scores do not automatically transfer to new env; only three development sword starts revalidated. No optimizer updates or reserved evaluation. Next implement stage2 evidence-backed memory, then guided progression baseline. README and prior Tail Key plan link new execution plan.

## Persistent world memory implemented — 2026-09-11

User said “do it” to implementing stage 2 from existing verified traces, with directed connections, blocked/damage evidence, episode-state separation and deterministic saved-memory route queries. Added `src/gameboy_agent/world_memory.py`, `tests/test_world_memory.py`, `scripts/build_world_memory.py`, `docs/WORLD_MEMORY_V1.md`. No other runtime modules changed. Updated README and protocol/focus to stage2 complete (evidence/query scope), stage3 live planner integration next.

Build command: `.venv-ladx/bin/python scripts/build_world_memory.py --out runs/world-memory-next` (fresh output). Current evidence `reports/world-memory-v1.json`, artifacts `runs/world-memory-v1/`. Imported only house/beach/approach traces from `runs/progression-interface-v1-verified/`, checks all fixture manifest hashes, replay flag, contiguous rows and journal-event agreement. 1243 observations:779presence,442movement attempts,14connection observations (12distinct directed edges),8landmark observations across13rooms. All observations re-derived from source evidence. Every observation has source trace hash/path,line/decision,frame,eventID if applicable, historical pre-action context. No live possession/milestones inherited. Exact NPC text/speaker/cause/prerequisites remain unknown. Actual safe input traces have zero damage; damage capture and mixed stationary/moving outcomes tested on explicitly synthetic rows only.

Memory content-hashed JSON save/load, child generations deep-copy knowledge and record parent hash; imports idempotent and order independent on the same sources. Verify external source evidence via `verify_evidence()`; load alone validates content hashes/references. Directed BFS returns observed chain with evidence+historical conditions, execution_validated=false/conditions_checked=false. House→sword12legs; reverse and sword→TailKey correctlyunknown. All169 room-pair queries exactly identical before save, after reload and childgeneration. Generation1 has no new discoveries; inheritance benefit not evaluated. Movement failures not permanentwalls; contradictions retained. Positions on connections labeled action-boundary bracket, NOT exactexit controltarget. No unexplored-exit discovery yet.

Seven new tests pass; full regression result to follow below. No new emulator collection, optimizer updates, reserved evaluation, or live memory/navigation integration this turn. Next stage3 connects graph queries with goalmanager and localcontroller, uses separately labeled providedmap hints for the unknown quest route, verifies approach coordinates/transitions, then bounded post-sword attempt. Stage6 paired inheritance efficiency remains pending.

Stage2 regression completed: 86/86 tests pass in 36.343 seconds. `reports/world-memory-v1-regression.json`; implementation source hashes match build report.

## Stage 3 live integration and first crossing blocker — 2026-09-11

User said “do it” to connecting memory/planner/localcontroller and a bounded guided attempt. Added `progression_planner.py`, `run_progression_attempt.py`, guidance configs v1/v2, five planner tests and `docs/PROGRESSION_INTEGRATION_V1.md`. Memory route queried on every nav decision, multi-room chains yield observed intermediate arrival target with evidence; otherwise labeled provided-map guidance. Dialogue handling, 256/goal budget, 64-position loop detection, at most2 scripted three-action recovery probes. Full quest prerequisites/interactions not implemented; this is southern guidance prefix towardforest, explicitly labeled.

Two continuous physical house→sword→prefix attempts, all policyweights unchanged. v1:412sword+240post=652decisions,4rawdamage,goalshorepassed,cliffhandoffstalled. Source snapshot `runs/progression-attempt-v1/runner-source.py` preserves initial runner before adding --guidance/report-per-output CLI. v2 singleguidancechange restores original89,94approach between36,121shore and64,64cliff;412sword+515post=927decisions,20rawdamage. Reaches shoreline49actions,approach30,cliff87,western E1(12,54)154 with recovery; stallsapproachingD1(12,112). FinalE1(10,26),health4raw,alive. Do not claimcliff generalfix or safejourney. No furtherblindattempts after2. Needphysicallyvalidate proposednorthcrossing andsafeapproach, then correctmapguidanceor skill;noautomaticretraining.

Both exactreplayeveryaction/fingerprint/frame/plannerdecision with plannerJSONroundtripmatch. Artifacts runs/progression-attempt-v1 andv2; reports same names. Maincompare `reports/progression-integration-v1.json`. Fullsuite91/91pass38.746s. Live memory multi-room branch not exercised here because routeunknown; known-housechain intermediatebranchtestedseparately. No memory-efficiency claim.

Merged replay-verified observations fromboth into `runs/progression-integration-v1/memory-generation-2.json`,4157observations,4new distinctdirectedconnectionsF2→E2,E2→E1,E1→E2,E1→E0. All re-derivedvia sourcehashes. Repeatedprefixobservations notindependentnewskills. Runnerstillloadsgeneration1 for matchedcomparison; next frozen experiment mustexplicitlyselectnewmemory. Stage3statusin_progress withcrossingblocker;researchfocus updatedpath/report. Nooptimizerupdates,reservedtests,TailKey,witch/curelivefixture orfullquestsuccess. Next investigatecrossingphysicalgeometry/coordinatesanddamage,notblindcliffoptimization.

## Western route correction and zero-damage D0 prefix — 2026-09-11

User said “go” to diagnosing proposed E1→D1 crossing and correcting route. Physical probes from exactly reconstructed failed v2 arrival: north atx10 andx28 stationaryy26/0damage; westcrossE0oneaction. LiveE1objectgridtoprowall3A, physics01solid. Thus northwardhopinvalid, not a learned navigation deficit. Evidence `scripts/probe_progression_crossing.py`, `reports/progression-crossing-probe-v1.json`, correspondingruns.

Western scripted diagnostic initiallyreplayed depletedv2finalhealth4, diedonfirsthit (7actions) whilecrossingE0; preserved as runs/progression-west-passage-v1. Matched earlierfullhealtharrival reconstructprefix736decisions: movementonly12actions then2rawdamage stop (v2); holdingequippedshieldB20actions entersD0with0damage (shield-v1). Allindependentexactreplay; not generalshield/encounterreliabilityclaim. Scriptsverify_western_passage.py andverify_western_passage_early.py (--shield). EarlysourcebeforeCLI preservedruns/progression-west-passage-v2/diagnostic-source.py.

Added optional shielded_axis physicalskill in progression_planner: requireequippedshield, adjacentroomonly, lanealignmentbeforecrossing; targettolerance configurable. Learneddefaultunchanged. v3guidanceappliedittooearlyE2→E1, stalledx36y49with8rawdamage; preservedfailedrun. v4guidance retains oldlearnedE1(12,54)approach and originalgeneration1memoryfor matchedarrival, then shieldedE0(27,48)tol3 andD0(27,125)tol3. Freshcontinuousv4 succeededprefix:412sword+337post=749decisions,0damage,finalD0(26,124)health24. Subgoals49,30,87,154,13,4; E1learnedapproachincludesoneboundedrecovery. Exacteveryaction/fingerprint/frame/plannerdecisionreplay andJSONroundtrip. NoTailKey/fullquestclaim.

Currentguidanceconfigs/progression_guidance_v4.json. Driveracceptsguidance.memory_path optional; defaultgen1unchanged. Source snapshotspriorplanner/runnerinruns/progression-attempt-v2. Three newplannerunitcasesforlanealignment,equippedshield/adjacency,tighttolerance. Fullsuite94/94passes (see report). Mainreportreports/progression-crossing-resolution-v1.json, docsPROGRESSION_CROSSING_RESOLUTION.md. Merged allverifiedsuccessful/failed traces into runs/progression-crossing-resolution-v1/memory-generation-3.json with verify_evidence(). No memory-efficiencyclaim. Focus/protocolupdated:crossingblockerresolved,stage3stillinprogress. Next map/verifyfromD0towardforest/toadstool retainingzero-damageprefixasdevelopmentregression. Nooptimizerupdates/reservedtests/witchkeyfixtures.


## 2026-09-11 — Forest terrain progression checkpoint

Latest user authorization: “yes go.” Extended verified house-to-D0 prefix physically; no new optimizer or reserved evaluation. New `src/gameboy_agent/terrain_navigation.py` provides conservative ROM-physics grid navigation and distinct reachable-region bookkeeping. `scripts/extend_forest_route.py --cut-flora --out-name NEW_DIRECTORY` reconstructs the 749-action v4 prefix and runs a bounded 1,600-decision extension twice for exact replay. Existing artifacts required; do not overwrite run directories.

Five revised development runs are recorded in `runs/progression-forest-terrain-v1` through `v5`. Best v5: 2,349 total decisions, 14 extension rooms, 16 transitions, two dialogues opened/closed, zero damage or healing, final room 52 at (71,115), health24. Forest80 reached and traversed; no toadstool/powder/Tail Key. Threshold64 stationary three-frame decisions resolves premature forest-exit rejection, but is only bounded patience, not a general scripted-event detector. Centering alone (v4) did not resolve it. Cutting metadata records intent; dialogue IDs 0C0 and021 do not establish exact text or speaker.

All five traces replay exactly. Full suite101/101 passed37.874s; log in v5. Report `reports/progression-forest-progress-v1.json`, explanation `docs/PROGRESSION_FOREST_TERRAIN.md`, merged evidence memory `runs/progression-forest-progress-v1/memory-generation-4.json`. Source policy unchanged. Component cache/visit counts are episode-local, not inherited world-memory topology.

NEXT: verify explicit toadstool approach subgoals and any required indoor/cave transitions; current extension runner stops on unexpected indoors. Do not spend another outdoor-wandering budget or start broad training before identifying that route/interaction gap. Preserve forest entry at full health as regression. Stage3 is incomplete; no quest or generalization claim.
