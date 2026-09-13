# Project audit — 11 September 2026

Audited revision: `6ae99a8`, initially clean working tree. This is an audit and proposed recovery sequence; it does not change runtime behavior or authorize a new training experiment.

## Assessment

There is real workflow drift, but the project does not need a restart. The strongest work remains the physical environment, replay/resume checks, selected early controller, and evidence-backed forest prefix. Recent work shifted from integrating the next quest milestone to producing demonstration tooling. That is a legitimate supporting capability, but its acceptance criterion became “a file was saved and delivered,” while the UI and collection counter call that success. There is no implemented path from these app captures into the current learner.

The documentation also lost a consistent account of progress. The toadstool route has more evidence than the main status admits, and less instrumentation than the route write-up implies. Both errors can send the next session in the wrong direction.

Twenty-five commits after `9b82c81` (physical toadstool route) concern the recorder and its handoff. This is a scope observation, not evidence that the user did not authorize that work. The missing connection is a declared progression blocker, a usable training-data contract, and an exit criterion for the tooling detour. The proposed 80–100-take playlist should not become the next default merely because the recorder exists.

## Actual capability boundary

| Area | Evidence and current limit |
| --- | --- |
| Environment | Neutral physical-button surface and a separate structured progression environment exist. The older training environment deliberately retains RAM assistance; these are different benchmark conditions. |
| Learned control | Sword and selected navigation artifacts exist. Selected navigation policy SHA-256 matches the focus file. Historical route scores are development results, not arbitrary-goal or whole-game competence. This audit did not rerun those full panels. |
| Forest progression | The v5 fixture has eight matching artifact hashes. Historical evidence reports 2,349 decisions, zero damage/healing, and exact replay. The current audit suite also exercises physical environment/replay behavior. |
| Toadstool | A local video manifest records final state `[0,0,80,36,49,1]`, and the route script physically asserts the acquisition latch. This is a scripted demonstration, not yet a complete independently replay-checked progression fixture. |
| Tail Key / Tail Cave | No qualifying completed quest run established by the reviewed evidence. Witch exchange, cure, key, unlock and entry remain the progression work. |
| Memory | Hashed generations, directed evidence and trace validation exist. Demonstrated benefit to quest completion or action efficiency is still a separate unmet gate. |
| Human demos | Local save/archive/transport checkout exists. The only Studio intake archive inspected is an idle smoke capture, not a successful house-to-sword demonstration. |
| Training ingestion | Existing Parquet curation and structured-controller training exist. Human app captures are a separate schema with no implemented conversion/ingestion path. |
| General architecture | No integrated large planner/teacher, full completion detector in the neutral environment, cross-game result, or completed formal PufferLib/vision/teacher-student comparison was established. These are roadmap gaps, not reasons to build all of them before finishing the current milestone. |

## Findings, ordered by impact

### 1. High: recorder completion is incorrectly treated as task success

`apps/human_demo_app.py:103–106` calls `end()` on timeout and on SAVE. That method unconditionally writes a completed manifest, increments progress, displays “Success saved,” and queues another run. It does not distinguish user assertion, timeout, death, or detected sword acquisition. `task_count()` also accepts archive names and persistent counts without validating their contents.

Reproduction: executing the real `end()` and `task_count()` methods with mocked I/O resources and no successful outcome produced `count=1` and “Success saved — 1/5.” Source inspection confirms timeout uses this same method.

Actual intake: `recorder-checkout-house-to-sword-20260911-100553.tar.gz` contains 447 actions and 447 PNGs, all actions with no buttons, no tags, and `sword_level=0` at the beginning and end. It is useful transport evidence. The handoff explicitly counts it as 1/5, incorrectly reducing the real demonstration target to four remaining examples.

Required correction: distinguish capture finalized, human-asserted success, automatic outcome, integrity accepted, and delivered. Timeout must not assert success. Preserve the smoke capture but classify it separately from gameplay quota.

### 2. High: app captures do not preserve the canonical replay/provenance contract

The v4 manifest at `apps/human_demo_app.py:106` contains format, task ID, frame/tag counts and completion time only. It omits ROM/state hashes, initial state identity or snapshot, code/config version, emulator version, producer/session identity, and initial/final outcome metadata. `load_preview()` advances an unrecorded frame before capture. The older CLI recorder retained ROM/state hashes; the app lost that provenance while advancing its format version.

`tick()` records the image/state **after** applying the row's action. That is a valid transition outcome if documented, but is not the preceding observation that caused the human action. A future imitation importer must shift observations appropriately, preserve an initial observation, and handle episode boundaries explicitly. Pairing each stored screenshot with its same-row action would expose the consequence of that action to the learner.

Required correction: define a versioned initial-observation/action/next-observation contract and immutable replay metadata before asking for a large collection. Add a small independent replay acceptance check. Do not assume a PNG plus a button list is already a training sample.

### 3. High: the integrity inspector accepts corrupt captures as READY

`scripts/inspect_human_demos.py:32–40` checks only manifest existence and positive file/line counts. It does not parse the manifest/actions/segments, compare their counts, decode PNGs, check frame continuity, validate segment coverage or tag bounds, or compare manifest totals.

Reproduction in a temporary directory: invalid JSON manifest, two invalid action lines, one invalid segment line, and one fake PNG returned `True` / READY with `frames=1 actions=2`. This is a confirmed false acceptance, independent of gameplay success.

Required correction: make integrity a fail-closed validator with explicit reasons; keep data integrity and task outcome separate. Include corrupt/truncated files and count/segment mismatches in focused tests.

### 4. High: the successful toadstool script bypasses progression accounting

`scripts/record_toadstool_route.py:50–58` advances PyBoy directly. Much of the cave route, both timed pushes and pickup dialogue use this `raw()` function rather than `ProgressionEnv.step_buttons()`. Those frames do not advance the environment frame budget or journal and are not appended to its action history. Health losses or transitions during those intervals are not recorded at frame granularity; later observations cannot reconstruct intermediate events.

The final artifact is a video manifest with a latch assertion. The script does not write a complete extension trajectory/journal, hash the full replay dependencies, or independently compare a second full replay. It also does not call the cave block-change verifier after the two pushes, despite the route documentation describing that verification as required. The helper unit tests do not exercise the actual video runner.

This does **not** imply that acquisition was fake: the script uses physical controls and the local manifest reports the latch. It means this evidence cannot yet meet the project's stronger progression acceptance contract or seed the existing verified-memory importer.

Required correction: integrate this known route through a recorded physical-action interface, including sustained pushes and diagonal controls as needed. Capture every frame, verify each intended push result and acquisition, preserve damage/healing, and independently replay the full trace before promoting it.

### 5. Medium: current status and entry-point documentation contradict the code

`docs/PROJECT_STATUS.md`, `configs/research_focus.json`, and `configs/progression_protocol_v1.json` still stop at forest exploration and recommend discovering the cave route. `docs/TOADSTOOL_ROUTE_AUDIT.md` opens with successful acquisition but retains earlier “next” instructions and even “this audit did not touch the item.” Its current conclusion and chronological notes are not clearly separated.

`docs/HUMAN_DEMO_APP.md` describes an end button gated on toadstool acquisition, configurable delivery settings, and rich tags that the present app does not provide. The README links the older CLI instructions, while the latest handoff describes the app's different storage and labels. Relative links in the latest handoff use `../apps` and `../configs` from within `docs/`, resolving into nonexistent `docs/apps` and `docs/configs`.

Required correction: one current status entry with explicit evidence levels: independently verified fixture, scripted demonstration, pending integration, and future work. Retain historical notes under dated history. Document the actual launcher, mappings, schema, and outcome rules.

### 6. Medium: upload worker reads mutable active-session state

`end()` starts `self.send` as a daemon thread; `send()` repeatedly reads `self.session` while building the archive. Starting the next run changes that field, including when Y skips the wait. A delayed worker can select the next session or use a mismatched archive path and directory. This is a code-level race; occurrence in the inspected smoke upload was not demonstrated.

Daemon workers can also be interrupted by app exit, and failed deliveries have no persistent retry queue. Delivery messages are global rather than bound to a session.

Required correction: pass an immutable completed-session path/ID into the worker, publish archives atomically, and persist per-session delivery state with retry. Test starting another run while an upload is delayed.

### 7. Medium: documented packaged-app build no longer matches app requirements

`scripts/build_human_demo_app.py:20–25` bundles ROM/state assets but not `configs/human_demo_tasks.json`, which `App.__init__` reads unconditionally. The app expects bundled ROM name `assets/ladx.gbc`, while PyInstaller receives the ROM under its original filename. `state_path()` always resolves the configured `runs/.../initial.state`, ignoring the bundled `STATE` constant. Even repairing the missing config would leave these path mismatches.

The latest operational handoff uses a source-checkout launcher, which avoids this particular packaging path. The documented self-contained build is still broken by inspection; no new bundle was built in this audit.

Required correction: declare and support one distribution path now. Either repair/test the bundle's assets and config resolution or clearly retire that build recipe in favor of the local launcher.

### 8. Medium: documented test environment does not run the full suite

The README's baseline environment lacks `pyarrow`. The documented discovery command returned 98 tests, one import error (`test_navigation_margin`) and five skips. Other data tests intentionally skip the same dependency, so the suite treats its optional status inconsistently.

For this audit the pinned data dependencies were installed in `/tmp/gameboy-audit-deps` and supplied via `PYTHONPATH`, without changing `.venv-ladx`. The complete rerun is recorded below. No tests currently target the app recorder, its archive delivery, or its inspector.

Complete rerun: **109 tests passed in 39.861 seconds, no skips**. Command: `PYTHONPATH=/tmp/gameboy-audit-deps .venv-ladx/bin/python -m unittest discover -s tests -v`. Logs are retained locally at `runs/project-audit-2026-09-11/baseline-tests.log` and `runs/project-audit-2026-09-11/full-tests.log`.

Required correction: document a complete development/test dependency set and add the small recorder acceptance tests above. A green historical suite is not coverage of the newest subsystem.

## Other maintenance observations

- All 154 Python files under source/scripts/apps/tests parse successfully. Fifteen local reference repositories match the recorded lock revisions.
- The collection plan still emits `git_commit=None` with “project has no git history” (`scripts/data_workset.py:288`). Its runtime hash snapshot preserves useful source identity, but that explanation is stale for new runs.
- Session folder names use task plus second-resolution wall time, without producer identity. This is weaker than the canonical append-only, multi-producer ID requirement and can collide in centralized intake.
- Recorder code compresses state changes, I/O, rendering and delivery into long statements. Extracting a small capture/validation core is justified by the identified bugs; rewriting the whole research repository is not.

## Recovery sequence

User clarification during this audit: the earlier session asked for cave gameplay while controller-input recording was still being established. Treat that as the process failure to correct: prove one end-to-end recording first, and explain the specific learning need before requesting another gameplay task. A working input recorder does not imply that human cave demonstrations are already consumable by the learner.

1. Reconcile current status: preserve the verified forest fixture and label the toadstool video as a physical scripted demonstration awaiting full trace integration. Keep Tail Key/Tail Cave as the active milestone.
2. Make existing recorder outputs trustworthy: fix completion semantics, provenance, integrity acceptance and per-session delivery. Classify the existing smoke capture as transport-only. Demonstrate one captured, independently replayed and correctly indexed sample before requesting more takes.
3. Return to progression: instrument the already discovered toadstool route, verify it continuously from the house, then report the first blocker toward witch/powder, Tarin, key and cave entry. Use the existing bounded protocol and preserve the forest regression.
4. Collect human examples only for a measured control/interaction gap with an agreed observation/action interface. A human-assisted teacher route and an autonomous agent result remain distinct.
5. Train only after the existing protocol's teacher, data, budget and evaluation gates are frozen. Keep broad combat/spin playlists and further arbitrary-coordinate tuning deferred unless the progression evidence makes them necessary.

The next useful success is a trustworthy, reusable milestone trace. More UI polish, raw take counts, or another local navigation score will not establish that by themselves.

## Validation and limits

This audit reviewed the canonical and session handoffs, current focus/protocol, implementation boundaries, recent changes, capture/packaging code, curation/checkpoint/memory code and local milestone artifacts. It ran the repository test suite, syntax checks, selected hash/lock checks, inspected the incoming archive without extracting it, and reproduced recorder false acceptance with temporary fixtures/mocked resources.

It did not launch training, inspect reserved evaluation specifications, alter selected policies, contact the Mini, revalidate remote deployment/Hugging Face, rebuild the app, or rerun the full historical navigation panels/toadstool video. Historical outcome statements above remain attributed to their saved evidence. This is a broad project audit with targeted reproductions, not proof that every experimental script is defect-free.


## Subsequent user decision

The user chose to shelve recorder development and collection, preserving its code/data. The earlier proposed recorder-fix step is therefore deferred. Active work resumed physical quest progression; current results and the next blocker are recorded in `docs/PROJECT_STATUS.md` and `docs/PROGRESSION_TOADSTOOL_AND_RETURN.md`.
