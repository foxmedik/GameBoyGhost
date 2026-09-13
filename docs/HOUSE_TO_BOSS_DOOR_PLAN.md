# House → Boss Door: version-1 alive endpoint

> Superseded by [the full-health endpoint and checkpoint plan](HOUSE_TO_BOSS_DOOR_FULL_HEALTH.md). Earlier results retain their original meaning.

This was the active session plan, established at the user's request on 2026-09-12. The endpoint is **opening Tail Cave's boss door alive from the supplied house start**. Stop outside the boss room. The final boss fight and Full Moon Cello belong to a later phase. Required encounters on the approach, including the miniboss if the established route uses it, remain in scope.

This supersedes the Tail Key / cave-entry scope as the current objective, without changing its frozen protocols, acceptance criteria, or results. Machine-readable phase state: `configs/house_to_boss_door_v1.json`. Current pointers: `configs/research_focus.json`.

## What counts as success

A route success requires one continuous physical episode from the original supplied house state to a newly opened boss door, alive, with the opening finished and controls released. Standing near the door, obtaining the Nightmare Key, opening Tail Cave's exterior entrance, or starting with the boss door already open do not satisfy it. No intermediate state loads, inventory writes, or hidden human rescue are allowed in a gate episode. The supplied house start already has the shield; this is not a power-on claim.

There are three distinct deliverables:

1. **Route established:** one complete guided house-to-open-door proof with independent exact replay and a verified endpoint detector.
2. **Training ready:** the full state-checked teacher passes its own frozen reliability panel; then a separate demonstration collection and a frozen learning experiment are prepared.
3. **Training accomplished:** the declared trained system completes its precommitted end-to-end gate. Report guided/hybrid completion and model-only completion separately. A guided pass cannot promote an autonomous model, and finishing an optimizer job cannot finish this phase.

The operational fallback is the best qualified deterministic/hybrid route. Model failures do not reopen the closed room-15 recovery branch. If a trained candidate fails, preserve it as rejected evidence and retain the qualified operational controller; report model acceptance as outstanding rather than silently changing the objective.

## Current evidence and immediate next step

The Nightmare Key is now acquired and the guided continuous route reaches Rolling Bones in room `0x11`. The boss door remains unopened. See [current route evidence and handoffs](HOUSE_BOSS_DOOR_ROUTE_PROGRESS.md).

The Nightmare Key controller's nominal check passed, but its two fresh timing checks scored **1/2**. A room-`0x0E` enemy can enter the early jump landing. The room-`0x10` state-checked crossing has one nominal success. Full-route teacher qualification is still false.

Next progression is the required miniboss, then the final antechamber and door. The bounded 3,000-frame lower-lane miniboss test survived at half a heart but failed to clear; it is stopped. Before training, repair the earliest route reliability failure and pass a fresh frozen full-route teacher gate. Reconstructed recorded prefixes remain development/replay artifacts, not the varied-start route controller.

## Session sequence

| Stage | Work | Exit evidence |
| --- | --- | --- |
| 1. Finish the route | Nightmare Key, necessary approach encounters, boss-door opening; stop before entering room `0x06` | Living continuous house proof, exact independent replay, opening screenshot and state transition |
| 2. Make the route repeatable | State-checked stage controller; explicit prerequisites and bounded recovery; qualify endpoint detection against the physical opening | Versioned controller, endpoint tests, no timing-sensitive recorded-prefix control; replay fingerprints retained |
| 3. Qualify the full teacher | Freeze controller/hash, fresh development case IDs, timing variations, budgets, endpoint and metrics before running | Full-route teacher gate passes; historical room-local qualification is insufficient |
| 4. Prepare training | Collect fresh demonstrations only after gate pass; preserve action ownership and episode provenance; split by source episode/start, not individual rows | Separate approved training manifest, untouched evaluation panels, frozen learning experiment |
| 5. Train and evaluate | Train the frozen candidate; evaluate a fresh frozen full-route panel; compare with qualified guided baseline | End-to-end result, intervention metrics, exact replay, explicit accepted/rejected decision |

Each session advances the earliest incomplete stage. Do not launch another generic data batch to work around an unfinished route, unreliable teacher, or ambiguous endpoint.

## Gate design and reporting

These are new **full-route** gates, not reinterpretations of historical room-local scores. Allocate fresh case IDs and freeze manifests before execution; no panel exists or has passed yet.

- Teacher: **20/20** continuous house-to-open-door development cases, all exact replays. Also **4/4** explicitly recorded actual half-heart arrival challenges must reach the endpoint alive, all exact replays. Produce these through continuous house episodes with physical setup, never RAM edits or a mid-encounter reload. Record the challenge arrival milestone, setup actions, damage/healing, and initial raw health 4. If these states cannot be produced, the gate is incomplete; do not substitute mislabeled cases.
- Model-only full-route claim: **at least 18/20** new continuous house cases and **4/4** fresh actual half-heart challenges; exact replay for every case and zero teacher fallback. Freeze the learned-control scope before evaluation. A learned local segment inside a guided route is reported as such and cannot satisfy this model-only gate.
- Guided/hybrid deployment: report its own full-route panel and exact control ownership. Its acceptance must not be reported as the model-only gate passing.
- Preserve the existing **18/20 and 4/4** room-15 autonomous bar and all rejected historical candidates unchanged. The room-15 research branch remains closed.

Every run records completion, furthest milestone, first blocker, deaths, damage/healing, final health, decisions, frames, wall time, replay result, model actions, deterministic actions, teacher takeover count, and teacher-controlled frames. For a hybrid route with always-guided stages, report the guided share even when there is no takeover event. Track guided completion, autonomous completion, and teacher intervention separately.

The current continuation harness permits 24,000 decisions / 400,000 emulated frames. These are development ceilings, not yet a frozen full-route gate budget. Freeze per-episode ceilings, total cases, worker count, wall-time/compute cap, and candidate count in each experiment manifest before dispatch. Do not change a running gate or expand a failed candidate into a sweep. Training remains disabled until the prerequisites above are met.

## Endpoint contract to implement and validate

Local matched-ROM source locates the boss door at the north side of indoor-A room `0x0B`, leading toward boss room `0x06`. `src/data/rooms/indoors_a.asm:IndoorsA0B` places object `$F8`; `src/code/bank0.asm:LoadObject_BossDoor` uses `ROOM_STATUS_DOOR_OPEN_UP` (`0x04`). `src/code/bank2.asm:.checkBossDoor` checks `wHasDungeonBossKey` and starts the door animation. These files are under `references/LADX-Disassembly`.

The candidate observation contract is: observe the closed door in room `[1,0,11]` with the Nightmare Key, then its room-status up-door bit changing to open, followed by settled playable state, closed dialogue and `wDoorsOpeningOrClosing == 0`, while alive and still outside the boss room. Candidate addresses are `wIndoorARoomStatus + 0x0B = 0xD90B`, boss key `0xDBCF`, and door animation `0xC188`. Validate the rendered passage and these signals on a real physical opening before making a completion claim. Source inspection alone is not a live detector qualification.

Implement this as versioned endpoint evidence so historical snapshots, journals, and replay hashes remain compatible. Wrong room, missing key, already-open start, death, unresolved animation, or entering the boss room must never be mistaken for this endpoint. The final controller must release movement when opening starts and stop after the contract settles.

## Evidence boundaries and session handoff

The existing 20 sealed validation specifications/results remain sealed evaluation evidence, including `runs/progression-longrun-hour-v1/plan.json` and `reports/progression-longrun-hour-v1.json`. Do not use them for development, teacher repair, label generation, or checkpoint selection. Existing historical frozen experiment files stay unchanged. New challenge and training panels must have independently allocated identities and provenance.

The historical room-15 teacher's 43/43 result covers its recorded scope, not this new full route. The later supplemental 4/5 result remains a failure. Current onward traces are development-only and ineligible for training labels. Whole-route teacher qualification is false and new-phase training has not started.

End each session by updating `configs/research_focus.json` and `docs/PROJECT_STATUS.md` with: active stage, verified furthest milestone, living continuation plus full-health alternative, control ownership, exact replay evidence, first unresolved blocker, next bounded action, teacher qualification scope, and training readiness. Link the new result; preserve failed attempts. Never describe route discovery or a recorded replay as autonomous learning.
