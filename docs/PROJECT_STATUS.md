# Project status — Tail Key and Tail Cave

## Where we are

The active goal is a continuous, physical run from the supplied house state through sword acquisition, Tail Key acquisition, Tail Cave unlock, and settled entry alive. We are in stage 3: guided quest integration.

The project has a trustworthy starting foundation and a verified route into the forest. It does **not** yet have a verified toadstool, powder, Tail Key, unlocked Tail Cave, or cave-entry run. We should treat the forest checkpoint as a strong development regression, not as quest completion or proof of general gameplay ability.

## What is established

| Area | Current evidence | What it gives us |
| --- | --- | --- |
| House-to-sword and early navigation | Selected learned navigation controller, physical sword acquisition, and a continuous house-to-D0 prefix | A repeatable starting segment without granting inventory or loading an intermediate state |
| Western crossing | Corrected route plus physical shielding through the corridor | The prefix reaches D0 with zero damage and exact replay |
| Honest progression interface | Separate environment with physical buttons/equipping, read-only state sensing, milestone latches, and a frame-level journal | Quest progress can be observed without inventory writes, powder grants/refills, or hidden recovery |
| Evidence-backed memory | Immutable, hashed world-memory generations reconstructed from verified traces | Directed room connections and observations can be retained across generations without inheriting episode inventory or quest state |
| Forest exploration | v5 reconstructs the 749-decision house-to-D0 prefix, then explores for 1,600 more decisions | Reaches the forest, visits 14 extension rooms, makes 16 transitions, handles two dialogue pauses, and ends at full health |

The current best run is `runs/progression-forest-terrain-v5`. It uses 2,349 total physical decisions, has an independent exact replay, and records no health-loss or healing event. The 101-test suite passed. The learned navigation policy has not changed during this progression work, and no reserved evaluation has been used.

## What the agent currently does

The system combines a learned early-game controller with a bounded, scripted local terrain planner. The planner reads actual ROM object physics without writing game state, uses supplied map/quest guidance explicitly, chooses locally reachable exits, holds the already equipped shield, and can physically cut only source-verified vegetation. It records room transitions, health changes, inventory/quest changes, and dialogue IDs.

This is deliberately guided play. It is not a claim that the learned policy independently understands the map, dialogue, combat, or the entire quest. The local reachable-region cache is scratch state for one episode; persistent memory currently stores only trace-backed observations and directed connections.

## What we learned from the forest work

The first terrain attempt took damage. Separating reachable regions removed that damage but initially could not pass a cuttable obstacle. Adding physical sword cutting reached the forest, where a scripted pause was misread as a blocked route. A bounded 192-frame settling allowance allowed the dialogue to complete and the run to continue.

That fix is intentionally narrow. It gives interactions time to start; it is not a general cutscene or NPC-understanding system. The two observed dialogue IDs have not been decoded into speaker or text, and a cutting decision is not automatically evidence that vegetation was destroyed.

## The next plan

1. Completed mapping pass: ordinary screen-edge traversal from the forest checkpoint cannot reach room `50`; see [TOADSTOOL_ROUTE_AUDIT.md](TOADSTOOL_ROUTE_AUDIT.md). The remaining route is a non-edge transition in the reached forest component.
2. Add the smallest physical skill needed for that transition: enter the known cave, identify and push only the ROM-designated movable rock tiles, then validate the settled exit into the toadstool area from relevant arrival states before relying on it in a full run.
3. Run a new bounded continuous attempt from the house state. Preserve the full-health forest entry as a regression and record the first unmet quest milestone if the run stops.
4. Continue the same evidence chain through witch/powder exchange, Tarin/raccoon interaction, Tail Key chest, keyhole, and settled cave entry. Each terminal event must be physically observed and independently replayed.
5. Only train a new policy if a measured skill blocker remains after a reliable teacher/planner can perform the skill. Freeze the task panel, budget, and acceptance gate first. Broad combat, spin attacks, bombs, arrows, and trading work stay deferred until a next milestone requires them.

The first successful post-sword run is the immediate success mark. After that, reproduce the whole route from the house start and then evaluate reliability on frozen varied starts. Memory inheritance is a later, separate claim: it must show no lower completion count and at least a 20% median action reduction on matched successful pairs.

## Guardrails

- No mid-episode state loads, inventory writes, powder grants/refills, or human rescue in qualifying episodes.
- No optimizer updates unless a concrete blocker has been measured and an experiment has been frozen.
- Keep failed traces and rejected route hypotheses as evidence; do not overwrite historical artifacts.
- Keep supplied maps, ROM-object physics, and source quest hints labeled as assistance.
- Do not use the historical reserved navigation evaluation as progression data.

## Evidence to open next

The detailed forest checkpoint is in [PROGRESSION_FOREST_TERRAIN.md](PROGRESSION_FOREST_TERRAIN.md). The complete acceptance gates are in [PROGRESSION_EXECUTION_PLAN.md](PROGRESSION_EXECUTION_PLAN.md). The immediate quest sequence and source-backed milestone definitions are in [TAIL_KEY_ENTRY_PLAN.md](TAIL_KEY_ENTRY_PLAN.md). The machine-readable current focus is `configs/research_focus.json`.
