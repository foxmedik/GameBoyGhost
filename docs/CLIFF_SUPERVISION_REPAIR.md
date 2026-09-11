# Cliff handoff and supervision repair

This investigation found a concrete difference between replayable demonstrations and the per-state targets used to train v8. It generated three repaired approach paths with safe continuous returns, then trained and evaluated one fixed v9 candidate. V9 was rejected: local preservation passed, but route completion fell from 6/9 to 3/9. See `docs/NAVIGATION_ROUTES_V9.md`. Sword-reduction work remains paused.

## Exact entry audit

Six full historical room-loop runs (v7/v8, house/beach/approach) were physically replayed, checking the exact final fingerprint and capturing the third-goal handoff. House and beach have identical v7/v8 handoff fingerprints and match their demonstration origins. The v8 approach handoff has the same (90,99) coordinates but different encoded state and no exact training-row match.

At all three v7 entry states, v8 already chooses the **curated movement**: up for house/beach, left for approach. The earlier raw-label audit compared several valid alternate demonstrations. It did not imply all opening movements were incorrectly supervised. The first button differs from the selected demonstration for house and approach.

There are 87 raw cliff states with differing movement labels, 71 within at least one individual path. These can reflect successful alternatives, stalled movements later abandoned by the teacher, or unobserved state. This count alone does not prove bad data or a need for memory. Reconstructing the trainer's exact sorted shortest-suffix traversal produces the same 7,017 curated states as its saved training plan.

## Physical test of curated labels

A frozen diagnostic followed the exact curated state/action lookup, with no nearest neighbor, fallback controller or intermediate waypoints. It stopped on a missing key. Each result was independently replayed.

| Handoff | Result | Actions before completion/miss |
| --- | --- | ---: |
| v7 house | Coverage miss | 2 |
| v7 beach | Coverage miss | 54 |
| v7 approach | Safe goal success | 136 |
| v8 house | Coverage miss | 2 |
| v8 beach | Coverage miss | 54 |
| v8 approach | Entry not represented | 0 |

The house lookup executes demonstration row 0, then row 3, skipping two intervening actions. Its next physical state has no exact label. This establishes an actual coverage gap after a shortest-suffix splice, not that a learned model can never generalize there. The approach lookup successfully shortens its demonstrated path from 146 to 136 actions, showing that some splices are valid.

## Fresh feature collection and continuous returns

A single predetermined continuation was tested per origin: keep the lookup prefix, then append the remaining actions from the last selected source demonstration; if the first state is missing, try the shortest same-start demonstration. Original goals and 256-action budgets remain unchanged. There is no adaptive recovery. Features are freshly encoded from each actual trajectory and checked in an independent physical replay.

All v7 starts reach the cliff goal safely: house 197 actions, beach 191, approach 136. Duplicate v8 house/beach origins also pass. The different v8 approach origin reaches the goal in 146 actions but takes four raw damage units, so it is excluded. Five accepted runs represent only **three unique safe origins**.

For each repaired v7 endpoint, three shortest distinct existing same-start return action templates were frozen and tried in the same physical episode. Seven of nine return trials succeed without damage; two house templates exhaust their actions short of the goal. Selected shortest safe returns are house 87, beach 86, approach 87 actions. Every accepted return origin fingerprint equals its repaired approach final fingerprint, and its physical prefix includes that approach's complete actions.

The canonical training set is six paths / 784 rows. It still contains 22 exact masked states with differing movement labels. These are repaired and verified trajectories, not a claim of eliminating every alias or of learned completion.

## Fixed v9 intervention

V9 replaces v8's 20 cliff paths with these six canonical paths and retains all 202 v7 preservation paths. It uses the unchanged architecture, 250-feature contract, shortest-suffix selection, learning rate 1e-5, eight epochs, retention and action-margin losses, sampling groups and entry weighting from v8. Only the final epoch is evaluated. The frozen plan explicitly records the residual 22-state ambiguity.

Combined training: 208 verified paths, 7,557 rows, 5,447 selected states and 84 conflicting-label states before selection. On the new 784 teacher rows, movement agreement improves from v7's 42.6% to v9's 74.7%; this is training fit, not live success.

Promotion still requires more than six complete routes, no loss of any selected v7 route or waypoint, all 135 safe local successes, zero local/route damage and deaths, all three original chains and exact replay/resume. Sword counts are diagnostic only. See the separate v9 result report for the completed gate decision.

## Artifacts

- `reports/cliff-entry-audit-v2.json`: entry matches, curated targets and raw conflicting occurrences.
- `reports/cliff-label-replay-v1.json`: exact-label executability probe.
- `reports/cliff-splice-repair-v1.json`: fixed continuation outcomes.
- `reports/cliff-splice-returns-v1.json`: continuous return trials.
- Corresponding ignored run directories contain frozen plans, fresh arrays, exact fingerprints and source snapshots.
- `runs/navigation-routes-v9/plan.json`: immutable next-candidate protocol.

All work uses known development data. No reserved evaluation, runtime teacher waypoints, ROM uploads or history deletion occurs.

The subsequent specialist investigation completes all nine known routes while preserving every safe local success. See `docs/NAVIGATION_CLIFF_SPECIALISTS.md`; the v9 rejection above remains unchanged.
