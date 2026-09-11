# Route regression correction v2

The second route candidate fixes the fresh-panel death but fails promotion. Selected focused v4 remains unchanged. The fresh target now succeeds in 14 actions without damage, versus death after 19 actions for route v1 and an 18-action success for v4.

| Check | Selected v4 | Route v1 | Route v2 |
| --- | ---: | ---: | ---: |
| Complete scripted routes | 0/9 | 2/9 | 2/9 |
| Ordered waypoints reached | 19/36 | 22/36 | 22/36 |
| Route navigation damage | 20 | 16 | 16 |
| Route deaths | 1 | 1 | 1 |
| Original local successes | 46/48 | 46/48 | 46/48 |
| Additional local successes | 39/48 | 43/48 | 43/48 |
| Fresh local successes | 46/48 | 45/48 | 46/48 |
| Local damage / deaths | 0 / 0 | 4 / 1 | 4 / 0 |

All v4 local successes survive with matching physical start fingerprints. However, original case `2b70007c69c8e7a7faa9399a6eea7e76e799e097862a30690fafdf1f90fa4f51` now takes four health units of damage before succeeding. The house beach_return becomes successful, while beach_return from beach loses its v1 success; approach still succeeds. The westbound beach death and approach timeout remain. No room_loop completes.

## Correction and training

The fresh regression's first disagreement with v4 occurs at action index 3. Thirteen damage-free, independently replayed local paths were collected from the original start and v1 prefixes of three and seven actions, including v4's exact successful continuation. Its cohort `65f5d71af81a8e9d9f6499ca135b7353edcf29c635034db1fc66487b72e88675` is retired from validation claims. `configs/navigation_retired_cohorts.json` records this and the prior retired cohorts (79 total) for future panel construction. The existing fresh panel is now partly a training regression panel; scores do not measure untouched generalization.

Route collection starts from route v1's actual rollouts using the unchanged three-route curriculum. It supplies 41 verified route paths, including complete repaired prefixes for the beach and approach westbound starts. The room-loop third goal and house westbound return remain unresolved by the bounded collector. All accepted paths are verified through physical action replay and feature/fingerprint equality; a searched success does not imply the learned policy will reproduce it.

The combined 54 paths contain 2,462 actions, reduced to 1,707 distinct masked-input states using shortest observed remaining continuations. Fifty-four states have conflicting observed actions. One candidate initializes from route v1, trains eight epochs at learning rate 1e-5 and retention KL weight eight, and uses half of each 256-example correction batch for the fresh regression. Retention includes 346,536 original cache rows and 9,877 demonstration rows from earlier local corrections and route v1. Architecture, normalization, and previous-movement masking remain unchanged.

The report compares against selected v4 and additionally requires preserving both route v1 successes without damage. It rejects v2 for local damage, route damage/death, and the lost beach-start route. No checkpoint shopping or deployment exception is used.

## Verification and artifacts

All 48 unit tests pass. The three original sword-to-goal chains succeed without damage in 49, 49, and 45 navigation actions. A route paused at action 470 after the first waypoint resumes identically to the uninterrupted run, including actions, state fingerprint, damage, progress counters, and final status.

- `scripts/navigation_route_fix_v2.py`: collection protocol and frozen training plan.
- `scripts/train_navigation_routes.py`: shared trainer with optional route retention and focused sampling.
- `scripts/report_navigation_routes.py`: paired checks and promotion gate.
- `reports/navigation-routes-v2.json`: portable results.
- `runs/navigation-routes-v2`: ignored local data, source snapshots, checkpoint, traces, and evaluation driver.

The reserved evaluation set is unused. The sword controller remains fixed; supplied goals and the privileged D harness are unchanged. This is a development navigation experiment, not game completion. ROMs and runtime artifacts remain excluded from Git.

The next correction should preserve the newly repaired fresh target while directly anchoring the damage-free original case and successful beach-start loop. Westbound failures need diagnosis at the first harmful action, since successful searched continuations have not yet transferred into reliable policy behavior. The room-loop cliff detour also still needs a verified demonstration.
