# Environment assistance and correctness audit

Follow-up: `docs/ROM_TRANSITION_AUDIT.md` resolves the ROM identity and hook-address questions below, records real outdoor/house-exit/projectile fixtures, and expands the suite to 13 passing tests. The initial findings below are retained as audit history; its earlier statements about unverified hook addresses are superseded by that report.

The first audit separates an upstream reproduction harness from an unassisted emulator surface. Both are runnable. Reproduction still trains successfully; neutral mode passes physical-control and reset checks. Neither is a validated completion benchmark.

The canonical handoffs remain unchanged. All integration changes live outside `references/`; the LADX upstream checkout is clean.

## Modes

| Property | Reproduction | Neutral |
| --- | --- | --- |
| Implementation | `src/gameboy_agent/ladx_baseline.py` | `src/gameboy_agent/neutral_env.py` |
| Start | Fixed upstream savestate | Power-on, or explicit savestate |
| Observations | Upstream screen, entities, map and progress vector | RGB framebuffer only |
| Controls | Upstream movement/A/B plus RAM inventory switching | Eight physical buttons, including Start/Select and combinations |
| Timing | Upstream variable frame skips | Exactly 10 frames per step by default |
| Item assistance | Preserved and labeled | None |
| Reward | Upstream shaped reward | Zero |
| Death | Upstream health-zero condition | No death detector; gameplay continues |
| Completion | Not evaluated | Not evaluated |
| Privilege | D | A-style surface; required completion detector still missing |

Neutral mode deliberately has its own observation and action spaces. The reproduction policy cannot be loaded directly into it. This establishes an unassisted control surface, not the handoff's matched-tools vision/senses A/B experiment.

## Confirmed findings

1. `run_action_on_emulator` calls `script_give_magic_powder` every step. It grants powder in the witch's hut and removes duplicate inventory items. A fixture confirms the grant.
2. `get_inventory_progress` refills powder to its maximum. Observation generation calls it, so reading an observation can change gameplay RAM. A fixture confirms that an observation changes a count of 1 to 20. Neutral framebuffer reads preserve work RAM in the equivalent fixture.
3. `switch_inventory` writes inventory RAM directly. Neutral mode offers physical Start/Select controls instead and imports no LADX environment code.
4. Upstream `get_net_reward` returns a scalar based on weighted differences, but its component dictionary contains weighted cumulative values. The project adapter now returns per-step components under `reward` and retains original totals under `reward_cumulative`. The scalar training reward is unchanged; a regression checks that per-step components sum to it.
5. The progress vector deliberately encodes the toadstool as -0.5, outside its declared 0–1 bounds. The adapter now permits -0.5 at that specific field; it does not clip observations.
6. Upstream catches all step exceptions and reports an episode ending; the adapter propagates errors. Time limits are truncations and health-zero is termination. Both modes reject steps after an episode ends until reset.
7. Reusing a PyBoy 2.0 instance across neutral savestate resets produced different early framebuffer observations even when work RAM matched. `load_state` only delegates to motherboard state loading in the installed source. Creating a fresh emulator on each neutral reset makes the regression pass, including simultaneous physical-button inputs. The precise renderer/host-state cause has not been isolated. This trades reset speed for episode isolation and must be considered during later scaling work.

## ROM assumptions

The local ROM has title `ZELDA`, header revision 1, cartridge type 27, and size 1,048,576 bytes. Both the header and global checksums validate. Its SHA-256 is `6285ba6201f17bc8595c600ebc2477d52561f0aff29b11f7fc3343bacb2e230b`.

This establishes file identity and checksum consistency, not correctness of game-specific memory decoding. Upstream provides no ROM-hash assertion in the inspected environment. Its combat hooks use bank/address pairs: push `(0x15, 0x7413)`, collision `(0x02, 0x7277)`, shield `(0x03, 0x6C50)`, and sword damage `(0x03, 0x719D)`. Its register helper suppresses hook-registration `ValueError` and deregistration exceptions. Successful training does not prove those hooks mean what their names claim for this ROM revision. A disassembly/symbol match and known combat fixtures are still required.

## Transitions and reward risks still open

- Upstream tests room-transition byte `0xC124 != 0` and warp byte `0xC16B != 4`, then advances fixed 40/60-frame chunks. It also waits on movement and advances extra frames after pushing. There is no verified transition state machine. Neutral mode never reads these flags and keeps a fixed frame budget; a synthetic flag fixture confirms this. Real overworld, indoor, warp, side-scrolling, and death-animation transition fixtures are not yet captured.
- Health reward divides by the maximum-heart byte without a zero guard. The reproduction baseline is suitable only for its gameplay savestate until title/death/transition cases are audited. Neutral mode avoids these RAM assumptions.
- `get_game_progress_reward` mutates exploration memory, clearing seen sets when progress rises. Several reward getters also consume event flags or increment counters. Calling these getters for a dashboard could change subsequent rewards. They need a single event/update phase and pure readout before instrumentation expands.
- Configured `dialog_steps`, `max_health`, `deaths`, and `total_rupees` do not appear in upstream `get_reward_dict`, so those configured terms currently have no effect.
- Upstream's rupee formula uses a multiplier of 255, and the maximum-heart feature is divided by 16 in two places. Dungeon item offsets also need independent verification. These are audit leads, not silently corrected game semantics.
- Completion detection, true new-game-to-credits evaluation, whole-experiment resume, and immutable canonical trajectory recording remain unimplemented. Neutral smoke output is a diagnostic action log, not the final dataset schema.

## Validation and artifacts

Ten integration tests passed using temporary ROM copies. Fixture RAM edits are isolated test setup and are not training data. They cover assistance side effects, signed observations, reward totals, invalid/error paths, timeouts, synthetic zero-health termination, neutral read purity, physical-button replay, and fixed transition timing.

The updated reproduction run `7c8a58df-8f34-4737-8e13-c7b360a62348` passed Gym/SB3 checks, fixed-start replay, 256 training steps, parameter-update checks, saved-model reload, and 16 inference steps.

The neutral power-on run `0e9e6d97-f475-41f1-9b48-a7dd539bb609` passed Gym/SB3 checks and 256 random physical-button steps. It records actions, framebuffer hashes, start conditions, ROM checksums, and explicit unknown completion status. It is not a learning or progress claim.

Commands from the project root:

```bash
.venv-ladx/bin/python -m unittest discover -s tests -v
.venv-ladx/bin/python scripts/run_ladx_baseline.py
.venv-ladx/bin/python scripts/run_neutral_smoke.py
.venv-ladx/bin/python scripts/run_neutral_smoke.py --state references/LADXExperiments/ladx.gbc.state
```

The next correctness milestone is capturing real transition/combat fixtures and validating RAM/hook semantics against this ROM revision. The full replay/resume design can then preserve both emulator and harness state explicitly.
