# ROM revision and gameplay fixture verification

Follow-up: `docs/TRAINING_AND_RESUME.md` records implemented phase-aware controls, live sword/push coverage, complete current-baseline checkpoint/resume, and the longer pilot. The initial open items below are retained as audit history and superseded where that report provides newer evidence.

The local ROM is English 1.1. Rebuilding that revision from the [LADX disassembly](https://github.com/zladx/LADX-Disassembly) produced a byte-for-byte identical ROM. This verified a serious problem in the upstream environment: all four hook addresses target the wrong locations for this revision.

The project adapter now checks the ROM hash and hook opcode signatures before starting, uses corrected addresses, and propagates registration failures. Earlier smoke runs established execution and weight updates; their upstream combat/collision instrumentation should not be treated as validated reward evidence.

## Hook corrections

| Hook | Upstream address | English 1.1 address | Evidence |
| --- | --- | --- | --- |
| Urchin push | `15:7413` | `15:7415` | Urchin push-jingle instruction, signature `3e 3e e0 f2` |
| Solid collision | `02:7277` | `02:729f` | `ApplyCollisionWithSolid`, signature `f0 af fe 69` |
| Projectile shield | `03:6c50` | `03:6c45` | Shield-ting instruction immediately before `CheckLinkCollisionWithProjectile.jr_003_6C54`, signature `3e 16 e0 f2` |
| Sword damage | `03:719d` | `03:7190` | `ApplySwordDamagesToEnemy`, signature `79 3c ea ac c1` |

The old collision address points into an instruction operand containing byte `db`. PyBoy interprets that byte as an existing breakpoint and raises “Hook already registered.” Upstream suppresses this error and marks the hook registered anyway. The old sword address also falls inside an instruction operand. The old shield address is the `shieldEnd` branch, not the shield-ting instruction.

`src/gameboy_agent/rom_profile.py` owns the checked profile and strict hook lifecycle. It does not change the shared upstream enum. Unknown ROMs are rejected by the structured adapter; the generic neutral emulator remains independent of this profile.

The disassembly commit, symbol hash, toolchain version, and matched symbols are recorded in `configs/ladx-rom-verification.json`. The repository is pinned in `configs/references.lock.json`. RGBDS 1.0.3 and its libpng dependency were installed through Homebrew for this build. Rebuild locally with:

```bash
make -C references/LADX-Disassembly -j4 azle-r1.gbc PYTHON="$PWD/.venv-ladx/bin/python"
```

Built ROMs remain under ignored `references/`; no ROM contents are added to project source.

## Real gameplay fixture

`configs/fixtures/house_to_projectile_combat.json` contains 3,075 frames of physical-button input from the supplied house savestate. The initial state already has the shield. The scripted route exits the house, traverses outdoor rooms, encounters obstacles, and reaches Octorok projectiles. This is regression data selected by the developer, not an autonomous run or evaluation success.

Captured evidence:

- House exit: indoor room `a3` changes to outdoor room `a2` at frame 99.
- Seven outdoor screen changes, including horizontal and vertical transitions, plus the initial house exit.
- 1,504 solid-collision hook executions. These are raw invocations, not 1,504 separate gameplay events or reward points.
- Two shield-jingle hook executions at frames 2,308 and 2,533. The first event framebuffer was inspected.
- Two damage sequences reduce health from 24 to 20, then 20 to 16. Health decrements over several frames; individual decrements should not be counted as separate hits.
- No sword-damage or urchin-push execution in this fixture. Those addresses are verified statically against the byte-identical build, but their live behavior remains untested.

Artifacts are under `runs/validated-fixtures/{hooked,replay,unhooked}/`, including per-frame trace JSONL, controls, summaries, and screenshots. Captures use temporary ROM copies and never write gameplay RAM. Hooked captures temporarily patch emulator ROM instructions using PyBoy's breakpoint API; an unhooked comparison checks their effect.

Every row in two independently initialized hooked replays matched exactly. With hooks disabled, every framebuffer hash, work-RAM hash, decoded state, inventory, and health sample still matched. This verifies non-interference for the captured sequence, not all possible gameplay or all memory banks. Expected trace hashes and event frames are stored with the fixture.

## Transition semantics

The rebuilt symbols confirm `wRoomTransitionState` at `c124` and `wTransitionSequenceCounter` at `c16b`. The latter is not simply a universal “warp active” boolean.

Observed outdoor nonzero room-transition spans lasted **50, 44, 42, 38, 43, 42, and 38 frames**, cycling through states 1–5. Thus the upstream fixed 40-frame advancement can leave a transition unfinished or advance beyond its end, depending on when called.

During the house exit, the sequence counter differs from 4 over frames 80–98 and 105–141, with an intermediate 4-valued gap. The indoor/room identity changes at frame 99, before the second phase ends. A single “counter equals 4” sample or room-ID change is insufficient evidence that the entire transition has finished.

The neutral surface advances a fixed number of frames without skipping based on these bytes. Reproduction retains upstream timing pending a separately tested transition controller. A robust controller must track phases and validate completion across consecutive frames; the captured trace now supplies a real regression case. Indoor entry, dungeon stairs, side-scrolling transitions, and full death animations need additional fixtures.

## Validation

All **13 integration tests pass**, including exact gameplay replay, hooked/unhooked equivalence, ROM mismatch rejection, and registration-error propagation. The full fixture runs in fresh temporary outputs each time; capture refuses to overwrite an existing directory.

The corrected-hook PPO run `ff9dee53-04c4-49a9-8bba-3f5aab9ab196` also passed environment checks, fixed-start replay, 256 training steps, finite/updated weights, model reload, and inference. Run metadata now hashes the ROM-profile implementation too.

```bash
.venv-ladx/bin/python -m unittest discover -s tests -v
.venv-ladx/bin/python scripts/run_ladx_baseline.py
# Supply a new output directory for every capture:
.venv-ladx/bin/python scripts/capture_ladx_fixtures.py configs/fixtures/house_to_projectile_combat.json runs/my-new-fixture
```

Next: use these cases to implement phase-aware transition handling, then add live sword/push and remaining transition fixtures. Full experiment replay/resume and independent completion detection remain separate requirements.
