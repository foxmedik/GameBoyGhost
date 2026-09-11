# Live behavior preservation and return-leg correction

## Route v6: broader preservation

Route v6 restores both v5 timeouts and preserves all 135 known safe local successes across the three development panels (46/48 original, 43/48 additional, 46/48 fresh). All local and route damage is zero, with no deaths. It completes all three beach loops, but the approach westbound route now times out after three goals. That lost prior route success blocks promotion.

The change adds 135 replay-verified successful local traces as explicit action supervision. For each case, the most recent safe successful trace among route v5, v4, v3, and selected focused v4 supplies actions. The failing fresh case `f49bda234a90275504d0a788f3ed896810299bca814d35a880e2da18d8b37087` receives recovery searches around its first disagreement at action index 3. The house beach-return failure receives searches from its actual final-goal handoff and later failed-policy prefixes; its third waypoint ends at (114,87), while the earlier successful path ended at (113,88), illustrating how a small endpoint change can move the following leg outside a demonstrated path.

All 166 collection origins produce verified successes, totaling 182 paths and 4,965 action examples. Shortest-observed-suffix selection produces 4,065 distinct masked-input states and 24 conflicting states. Every label retains provenance; the selector does not claim optimality. The fixed eight-epoch run initializes from route v5, uses learning rate 5e-6, KL-retention weight eight, and a margin penalty requiring the demonstrated action's score to exceed alternatives by 0.25. Margin loss weight is two, with button loss weighted one-quarter relative to movement. Supervised batches allocate 64 examples to repairs, 96 to local preservation, and 48 each to beach and westbound paths. Retention covers 346,536 original rows and 7,403 demonstration rows.

The promotion gate now includes the union of safe local successes from all prior route candidates, not only the original selected model's successes. It still requires preserving all previous complete routes, zero local/route damage and deaths, and all original sword-to-goal chains. All conditions except prior complete-route preservation pass for v6.

## Evaluation boundaries and verification

These panels are now heavily used for training and regression checks. The retirement registry expands from 80 to 126 cohorts. Both development-panel builders now automatically exclude the registry when constructing future panels. The reserved evaluation set remains unused. These results establish behavior on known starts and goals, not held-out generalization or game completion. The fixed sword controller, scripted goals, privileged D harness, architecture, and normalization remain unchanged.

All 50 tests pass, including two tests checking the margin penalty and its gradient direction. Exact route pause/resume is checked after a waypoint handoff, alongside all 144 local cases, nine routes, and three original continuous chains.

The experiment scripts and portable reports are versioned source artifacts; raw data, emulator states, ROM copies, and model weights remain ignored local artifacts. Historical run source snapshots preserve earlier protocols.

- `scripts/navigation_live_preservation_v6.py`: successful local-trace selection and timeout recovery.
- `scripts/train_navigation_routes.py`: shared trainer, group sampling, and action-margin penalty.
- `scripts/report_navigation_routes.py`: paired gate including all prior safe local successes.
- `scripts/navigation_return_fix_v7.py`: focused approach westbound return-leg search with inherited v6 supervision.
- `reports/navigation-routes-v6.json`: v6 metrics and rejection gate.

## Route v7: promotion gate passed

Route v7 completes all three beach-return routes and all three westbound-return routes: 6/9 complete routes and 30/36 ordered waypoints, with zero navigation damage or deaths. The remaining three failures are the room-loop third-goal timeouts. All 135 known safe local successes survive (46/48 original, 43/48 additional, 46/48 fresh), also without damage or deaths. Every earlier completed route survives. All eight promotion conditions pass, and v7 replaces focused v4 as the selected experimental navigator; it does not change the default runtime or fixed sword controller.

The return collector starts from the actual v6 approach westbound handoff at total action 292 and prefixes 294, 296, 300, 308, 340, and 388. All seven origins yield damage-free verified paths, 20 in total. The handoff requires 102 search attempts to find three successes; prefix 294 produces two successes within the 128-attempt limit. Later stalled states yield three successes within 19 attempts. This records observed bounded-search outcomes, not shortest-path optimality.

V7 inherits the v6 dataset through verified local references and adds these return corrections, producing 202 total paths, 6,773 actions, 4,719 distinct masked-input states, and 61 conflicting states. Collection-policy hashes explicitly allow the two contributing collection parents, without relabeling inherited provenance. A fixed eight-epoch run at learning rate 2e-6 keeps the margin and KL terms. Supervised batches use 16 previous-repair examples, 80 local examples, 48 beach examples, 48 westbound examples, and 64 new return examples. States in the first four new recovery actions receive eightfold sampling weight. Retention uses 346,536 original rows and 11,171 demonstration rows.

All three original sword-to-goal chains remain successful without damage in 49, 49, and 45 navigation actions. The post-waypoint pause at action 470 resumes identically to the uninterrupted run, including actions, fingerprint, progress, damage, and final status. The local cohorts used are already retired; the registry remains at 126 cohorts.

`reports/navigation-routes-v7.json` records the passing gate. `configs/navigation_experiment.json` records the selected checkpoint and its SHA-256, preserving the prior selected checkpoint for rollback. `configs/navigation_route_candidate.json` records promotion. Full local artifacts remain under `runs/navigation-routes-v7`.

The next unresolved navigation problem is the room-loop cliff detour: every start reaches its first two goals safely, then times out at goal three. That needs a verified route demonstration before another correction experiment. A genuinely untouched evaluation panel must exclude all 126 retired cohorts; the reserved evaluation set remains unused.
