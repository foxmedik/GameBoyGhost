# Westbound safety correction: route v4 and v5

The two harmful westbound runs now execute without damage, and the approach westbound route completes. Neither candidate is promoted: route v4 introduces local damage; route v5 fixes it but loses two previous successes through timeouts. Selected focused v4 (the earlier local navigator, distinct from route v4) remains unchanged.

| Check | Route v3 | Route v4 | Route v5 |
| --- | ---: | ---: | ---: |
| Complete routes | 3/9 | 4/9 | 3/9 |
| Ordered waypoints reached | 25/36 | 28/36 | 27/36 |
| Route navigation damage | 12 | 0 | 0 |
| Route deaths | 0 | 0 | 0 |
| Original local successes | 46/48 | 46/48 | 46/48 |
| Additional local successes | 43/48 | 43/48 | 43/48 |
| Fresh local successes | 46/48 | 46/48 | 45/48 |
| Total local damage | 0 | 12 | 0 |

Route v4 completes all three beach loops plus west_return from approach. House and beach west_return reach three goals before timing out. All room_loop starts reach two goals and time out. Route v5 preserves the westbound behavior but loses the house beach loop at its final goal. All remaining route failures are damage-free timeouts.

## What changed

The route-v3 beach westbound run first loses health at action index 353, then at 374 and 375. Approach first loses health at 190. All losses occur while targeting the second waypoint. V4's collector uses the handoff, four actions later, and states one, two, three, four, eight, and sixteen actions before the first collision. All 16 recovery origins produce three safe paths each. Two successful local traces and the twelve completed beach-loop legs are also replayed as supervised preservation examples.

A training-state audit identified an entry decision missed by route v3: at beach prefix 350, the verified 25-action path starts up, while the model chooses left. The model agrees with the remaining 24 actions on that teacher path. Route v4 learns the first up action. Across 48 westbound teacher paths, first-movement agreement improves from 0/48 to 21/48; exact movement-plus-button agreement improves from 0/48 to 6/48. These are alternative training demonstrations, not held-out live scores; some later teacher disagreements also change.

Route v4 initializes from route v3 and uses 62 verified paths, 2,447 actions, and 2,112 distinct masked-input states, including 60 conflicting states. Half of each supervised batch is westbound, with eightfold sampling weight on states appearing in the first four recovery actions (124 states). The other half preserves local fixes and beach loops. Eight fixed epochs use learning rate 1e-5 and KL-retention weight eight; retention covers 346,536 original rows and 8,578 demonstration rows. Shortest-observed-suffix selection preserves label provenance and does not claim optimality.

The full gate then detects 12 health units of damage in fresh case `89dad7a34f0e26a1a4a01c96b22d087cff6c9433765e5a96398ee9acf4aaab50`, despite successful completion. Its first disagreement with the prior safe trace is action index 1.

Route v5 targets that collateral regression. It replays the safe local trace and searches candidate prefixes around the first disagreement. Explicit anchors cover both previously repaired local cases and every completed beach and westbound leg from route v4. All 28 collection origins succeed, producing 34 verified paths, 1,197 actions, 983 distinct states, and six conflicting states. A fixed eight-epoch run at learning rate 5e-6 balances the new repair, prior local fixes, beach routes, and westbound routes equally; KL retention uses 346,536 original rows and 8,653 prior demonstration rows.

The targeted local case now succeeds in nine actions without damage. However, fresh case `f49bda234a90275504d0a788f3ed896810299bca814d35a880e2da18d8b37087` changes from success to timeout, and the house beach loop times out on its final goal. The no-lost-success conditions therefore reject route v5 even though all route and local damage is zero.

## Validation and artifacts

All 48 tests pass and new scripts compile. Both candidates preserve the three original sword-to-goal chains, succeeding without damage in 49, 49, and 45 navigation actions. For both, pausing the house beach route at action 470 and resuming yields exactly the uninterrupted actions, fingerprint, counters, damage, and final status. All local comparisons use matching physical replay fingerprints. Sword behavior, supplied goals, model architecture, normalization, and previous-movement masking remain unchanged.

The newly trained fresh cohort is recorded in `configs/navigation_retired_cohorts.json`, bringing the registry to 80 cohorts. Future untouched validation panels must exclude them. These are development/training regression scores under the privileged D harness; reserved evaluation is unused and game completion is not evaluated.

- `scripts/navigation_west_fix_v4.py`: collision-origin collection and fixed entry-weighted training plan.
- `scripts/audit_navigation_entries.py`: teacher-path entry diagnostics.
- `scripts/navigation_route_safety_v5.py`: collateral-damage repair and route preservation examples.
- `reports/navigation-routes-v4.json` and `reports/navigation-routes-v5.json`: complete gate results.
- `runs/navigation-routes-v4` and `runs/navigation-routes-v5`: ignored source snapshots, verification manifests, models, traces, and evaluation drivers.

The next step should strengthen preservation with successful live-trace action supervision and explicit coverage of the two newly failing continuations. Probability retention on the existing cache plus a small anchor set has repeatedly failed to preserve live behavior. Any additional development cohorts used for that supervision must also be retired from validation claims. ROMs and runtime assets remain excluded from Git.
