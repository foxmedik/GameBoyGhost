# Tail Key → Tail Cave: next success story

The user confirmed Tail Key acquisition and Tail Cave entry as the immediate milestone. Further navigation optimizer work stays paused while the progression contract and baseline are established. This document is the implementation sequence; it does not claim the quest has run or the new harness has been validated.

## Success contract

First demonstrate a continuous run from a physically obtained post-sword state that acquires the Tail Key, opens Tail Cave and reaches its entrance room alive after the room transition settles. Then reproduce the entire run from the supplied house start, including sword acquisition, without loading intermediate savestates or using runtime human rescue. The supplied house state already has a shield; this is not a power-on/new-game claim.

Track and latch intermediate events so acquisition, unlocking and entry are distinguishable. Reject initial states that already satisfy the terminal milestone. Retain action/frame counts, damage, deaths, resets, goal changes, assistance and wall time. A single completed run is the first story; reliability requires a subsequent frozen varied-start panel. Do not silently replace that first achievement criterion with perfection on every optional route.

## Source-grounded prerequisites

The intended quest sequence is sword → toadstool → witch/powder exchange → powder interaction with raccoon/Tarin → Tail Key chest → Tail Cave unlock and entry. These are explicit high-level progression hints for the first guided baseline. They are not a zero-shot game-knowledge claim. Do not encode a fixed button tape or silently call a teacher route an autonomous learned policy.

The matched disassembly supplies these detector candidates:

| Event/state | Matched source evidence | Implementation requirement |
| --- | --- | --- |
| Toadstool acquired | `wHasToadstool`, DB4B | Observe its acquisition and later consumption |
| Powder available | Inventory slot plus `wMagicPowderCount`, DB4C | Distinguish toadstool representation from actual powder; verify witch exchange |
| Raccoon cured | `wTarinFlag`, DB48, changes to 1 | Validate the live interaction and event transition |
| Tail Key acquired | `wHasTailKey`, DB11 | Record raw value; source chest handling increments the flag and keyhole handling checks nonzero |
| Tail Cave opened | Overworld room D3, room-status event bit 0x10 | Verify against physical keyhole interaction; do not infer entry from this alone |
| Tail Cave entered | Indoor A, map 00, entrance room 17 | Require living player and settled gameplay transition; verify a physical entrance trace |

Addresses come from `references/LADX-Disassembly/azle-r1.sym`, whose hash is recorded in `configs/ladx-rom-verification.json`. Source evidence is not a substitute for live fixtures. In particular, the inherited inventory feature tests `wHasTailKey == 0xFF`, while the chest/keyhole code supports nonzero possession. The new detector must not trust that feature uncritically. Verify the actual 0→1 pickup transition before finalizing the fixture.

Sources: `src/code/entities/bank3.asm` (`EntityInitChestWithItem`, `ChestGiveNoneInventoryItem`), `src/code/bank2.asm` (keyhole handling), `src/code/entities/05_witch.asm`, `src/code/entities/05_tarin.asm`, `src/constants/rooms.asm`, and `src/constants/memory/wram.asm` in the local matched disassembly. Upstream behavior is in `references/LADXExperiments/experiments/gym_env/link_awake_env.py`.

## First implementation block: honest progression harness

Create a separate versioned progression mode, preserving the current reproduction experiments and selected checkpoints. Keep structured read-only senses and existing physical-control timing where possible, but remove automatic item/progression assistance from this mode:

- `TrainingEnv` currently calls `script_give_magic_powder`, which can grant powder in the witch's hut and alter duplicate inventory items.
- `get_inventory_progress` currently refills powder during observation generation.
- The inherited inventory-switch action writes item slots directly. The progression mode needs physical menu/equip actions instead.

These are material to the quest, not cosmetic benchmark differences. Add fixtures for observation-read purity, absence of grants/refills, physical item equipping, and milestone transitions. Revalidate the selected sword/navigation handoff under the changed mode instead of assuming all old scores transfer. Do not modify historical snapshots or retrain models merely to hide a harness mismatch.

Deliverable: trustworthy progress events and a control surface that can complete the real interactions, with replay/resume evidence. No large training run.

## Second block: connect the skills and attempt the quest

Reuse sword acquisition and useful local navigation. Add the minimal reusable physical skills needed to talk, equip/use an item, open a chest and enter a doorway. Keep a small goal manager above them, with explicit budgets, observed transition/blocked-edge memory and a generic stall/replan response. The goal manager chooses the next quest objective; a motor controller does not have to infer the entire quest from a final pixel coordinate.

Run one bounded guided progression attempt from the post-sword state. Log the first unmet prerequisite or failed skill and preserve the continuous state/action trace. Optional loops and zero-swing optimization are outside scope. A scripted teacher may diagnose one missing skill as a separately labeled comparator; it must not silently finish an evaluated learner run.

Deliverable: the first verified Tail Key + entry run, or one precisely identified blocker along that chain.

## Third block: train only a necessary blocker

Use a cheap physical skill or planning/recovery fix when that addresses the demonstrated cause. If a reliable teacher can complete the skill across relevant arrival states but the learner cannot, collect a bounded batch of verified learner-state corrections and train that skill. Evaluate its following interaction/leg continuously. Avoid a new neural specialist for each named coordinate.

Before collecting or training, freeze the task distribution, comparison, resource limits and stop rule. The audit's example thresholds/caps remain proposals; they are not active training authorization. Navigation and sword-reduction optimizer experiments remain paused until this evidence exists.

## Final proof

After the post-sword proof, run the whole house → sword → key → entrance sequence continuously and produce a replay-verified recording. Then freeze fresh physical startup/timing variations and report progression success, survival, health cost and interventions. Existing 144 local cases/nine routes remain regression data; the 96 reserved navigation specifications stay untouched until their separate release protocol is appropriate.

The immediate next action is the progression-mode and milestone-fixture implementation—not another cliff dataset or full PPO sweep.

## Provided tilesets and maps

The user's assets are processed into `runs/progression-assets-v2/index.html` and a machine-readable manifest: 31 image references, 256 indexed overworld rooms and 451 unique tile appearances. See `docs/PROGRESSION_ASSETS.md` for reproducibility, verification and limitations. Use them in the guided baseline with explicit `provided_full_map_and_artwork` assistance. Live room/coordinate alignment and physical passability still need validation; the static references are not integrated into a controller yet. Standalone tilesets and interior maps remain intact reference images because their layouts differ from the overworld grid.

## Execution protocol now active

`docs/PROGRESSION_EXECUTION_PLAN.md` and `configs/progression_protocol_v1.json` define the staged quantitative gates and budgets. The separate interface and event foundation is implemented; see `docs/PROGRESSION_INTERFACE_V1.md` and its evidence report. Source-grounded terminal milestones still await physical quest fixtures. World-memory integration is the next implementation stage.
