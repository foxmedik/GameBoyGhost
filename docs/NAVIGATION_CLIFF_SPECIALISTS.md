# Learned cliff specialists

The second specialist candidate completes all nine known four-goal development routes, including all three cliff loops, with zero navigation damage. All local preservation, exact replay and three pause/resume checks pass. It is now the selected experimental navigator, replacing v7.

## What the stall diagnosis established

Physical replay of v9 shows the house controller moving left from (89,99), then turning upward at (64,90), directly below goal (64,64). Beach behaves similarly. The approach run also converges below the cliff. At the house stall there is no exact curated input match; nearby teacher rows continue the detour. The first prior action mismatch is at (68,90), where the demonstration briefly reverses right while v9 continues left. Thus a deviation is not automatically a bad physical move, and higher training agreement alone is insufficient.

The existing v7 controller also fails all three 256-action returns when started from verified cliff endpoints. All three probes have zero damage and exact independent final replays. The return behavior needs attention alongside the cliff approach.

These observations motivated two scoped feed-forward specialists, with the original v7 fallback frozen. They do not establish one universal cause for navigation failures.

## Architecture and scope

`NavigationController` optionally loads self-contained `goal_experts` from a checkpoint. Each expert has the same 250-input, two-hidden-layer network as the existing navigator. Dispatch matches the complete supplied final goal: room tuple, x and y. The two goals are derived from the verified cliff data: E2 (64,64) and E2 (36,121). All other final goals use the unchanged v7 network.

The experts consume the existing structured observation and original final goal. Previous movement remains masked. Runtime has no intermediate teacher waypoints, route index, demonstration cursor, action replay, search or new emulator privileges. Checkpoints include the fallback and both experts, so ordinary route/chain loading and replay resume remain self-contained.

This is **known-goal specialization**, not a general detour planner. The return goal is shared by working routes and chains, so isolating the fallback does not remove the need for their live preservation checks. Goals and harness remain privilege level D; full-game completion is unevaluated.

## First specialist experiment

V1 trains two separate networks from v7 on shortest-suffix labels for their respective goals in the verified v9 dataset. Both use 256 fixed epochs, Adam at 1e-4, seed 2027, movement cross-entropy plus 0.25 button cross-entropy, and balanced cliff/preservation sampling. Only the final checkpoint is evaluated. V7 fallback weights and normalization are unchanged.

Results: **7/9 routes, 32/36 waypoints**, zero navigation damage or deaths. The beach cliff loop succeeds. House reaches the upper E2 corridor but oscillates near x12–17, y58. Approach oscillates in E1 near x110, y65. All six v7 successful routes survive. Local panels remain 46/48, 43/48, 46/48; all 135 safe successes survive. Original chains remain 3/3. All 192 local rollouts and 12 route/chain runs replay exactly; route and chain resume checks pass.

V1 passes its frozen improvement gate. Its checkpoint remains available as a verified intermediate candidate.

## Cleaner teacher probe and exclusions

A separate bounded teacher probe tries three E1 corridor lanes (126,124,122), with a three-pixel waypoint tolerance and one deterministic attempt per start/lane. All nine approaches reach the original cliff goal safely in 99–103 actions. Only one continuous return succeeds: four take damage and four time out. A second frozen nine-trial return probe from lane-124 endpoints produces one safe success; the other eight fail through damage, timeout or exhausted recorded actions.

These faster paths are preserved as diagnostic artifacts but **are not used in v2 training**. Safe arrival alone is insufficient evidence of a safe continuous route.

## Corrections from actual learned states

A fixed collector follows v1 at its original handoffs, then switches only at predetermined observed failure regions:

- House: first return to E2 at y≤64 after visiting E1; teacher targets the original cliff goal directly.
- Approach: first reach E1 at y≤64; teacher rises to y54, crosses the established upper corridor, then targets the original cliff goal.
- Beach: retain the successful learned path throughout.

Two fixed button phases are tested for each failing start. Features are freshly encoded for the original goal, including the learned prefix. All returns use unchanged learned specialist v1. Every attempt is independently replayed, comparing every feature row and the final fingerprint.

| Start / phase | Cliff actions | Learned return | Outcome |
| --- | ---: | ---: | --- |
| House / 0 | 196 | 73 | Safe continuous success; selected |
| House / 1 | 199 | 10 | Return takes 3 damage; excluded |
| Approach / 0 | 92 | 81 | Safe continuous success; selected |
| Approach / 1 | 95 | 74 | Safe continuous success; retained alternative |
| Beach / 0 | 159 | 83 | Safe learned preservation; selected |

The three canonical cliff paths total 447 rows. Together with the 14-row existing local-goal anchor, v2 has 461 raw rows / 418 curated inputs and **zero conflicting action labels**. Continuous return prefixes and origin fingerprints match the corresponding approach endpoints exactly.

## Second specialist experiment

V2 initializes from v1 and updates only the E2 (64,64) expert. It replaces the older cliff approach supervision with the three canonical paths, preserving the local goal anchor. Training uses 256 fixed epochs, Adam 1e-4, seed 2027, the same button weighting and balanced sampling, with 8× weight on the first eight teacher-correction rows. No checkpoint shopping. Final training agreement is 99.5% movement and 100% buttons; live evaluation remains the acceptance test.

The v7 fallback, v1 return expert, mean, scale and input mask are asserted unchanged. Both new dispatch tests and the existing suite pass: 66 tests total.

All nine route rollouts succeed with zero navigation damage. Cliff/return leg actions are house 194/73, beach 157/81, approach 92/81. The frozen v2 gate additionally requires preserving all seven v1 routes and improving beyond seven. It includes a pause/resume inside the cliff goal, alongside the return-route and original-chain resume checks.

## Artifacts

- `reports/cliff-stall-diagnostic-v1.json`
- `reports/navigation-cliff-specialists-v1.json`
- `reports/cliff-clean-teacher-v1.json`
- `reports/cliff-clean-returns-v1.json`
- `reports/cliff-live-corrections-v1.json`
- `runs/navigation-cliff-specialists-v1/plan.json` and `runs/navigation-cliff-specialists-v2/plan.json`
- `runs/navigation-cliff-specialists-v2/model/epoch-256.pt`

All experiments use known development data. The 96 reserved evaluation specifications remain untouched. Sword reduction stays paused. Historical runs, rejected candidates, uncommitted work and ROM exclusions are preserved; nothing is committed or uploaded.

## Final v2 acceptance

Selected after **9/9 routes and 36/36 waypoints**, all 135 safe local successes preserved (46/48, 43/48, 46/48), and 3/3 original continuous chains. Zero local/route damage or deaths. All 192 local rollouts and 12 route/chain runs replay exactly; original v7 reruns match historical fingerprints. Paired starts match. All three pause/resume checks match uninterrupted outputs, including a pause inside the cliff goal. All frozen gates pass; 66 tests pass.

Result: `reports/navigation-cliff-specialists-v2.json`. Selection: `configs/navigation_experiment.json` and `configs/navigation_cliff_specialists_v2_candidate.json`. V7 and eligible specialist v1 remain available. The selected checkpoint SHA-256 is `9d2b24b28be5289fc3d32d85d46faa1835ca2068d73a1e8790630d77dbaf85ec`.

A 64-second silent MP4 of the learned house loop is at `runs/videos/learned-cliff-loop-v2/cliff-loop.mp4`. It renders actual emulator frames at native speed, verifies the exact completed-run fingerprint, and adds a two-second final presentation hold. It is a learned policy replay, not a teacher demonstration. Representative frames were visually inspected.
