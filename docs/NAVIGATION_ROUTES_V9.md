# Navigation routes v9 — rejected

V9 preserves all 135 selected-v7 safe local successes but loses all three west-return routes and still fails all three cliff loops. Route v7 remains selected. Sword reduction remains paused.

## Intervention

The entry audit found that v8 already chose the curated opening movement at all three v7 cliff handoffs. Physical exact-label lookup exposed uncovered states after shortest-suffix splices at house and beach; the approach lookup completed safely. This is evidence of a supervision coverage gap, not proof that a learned policy cannot generalize or needs memory.

Collected fresh features for three safe repaired approaches and three safe continuous returns: six canonical paths, 784 rows. Replaced the old 20 cliff paths while retaining 202 v7 preservation paths. The combined set has 208 paths, 7,557 rows and 5,447 curated states. Residual conflicting labels remain. See `docs/CLIFF_SUPERVISION_REPAIR.md` for collection and exclusion details.

Trained eight fixed epochs from v7 with the unchanged architecture and v8 training settings; evaluated only epoch 008. No checkpoint shopping. Teacher-row movement agreement rose from 42.6% to 74.7%; this did not transfer to cliff completion.

## Live results

| Check | Selected v7 | Candidate v9 |
| --- | ---: | ---: |
| Original local panel | 46/48 | 46/48 |
| Additional local panel | 43/48 | 43/48 |
| Fresh local panel | 46/48 | 46/48 |
| Complete routes | 6/9 | 3/9 |
| Route waypoints | 30/36 | 27/36 |
| Original continuous chains | 3/3 | 3/3 |
| Local/route damage and deaths | 0 | 0 |

No local successes were lost or gained. All three beach returns pass. All three west returns time out at the fourth goal; all three room loops time out at the cliff goal. The cliff endpoints are house/beach (64,90) and approach (62,90), below target (64,64). These observations do not establish the root cause.

The regression audit finds prolonged repeated positions on west returns: house/beach E1 (138,67), approach E1 (124,71). First action divergences from v7 are recorded in the portable audit. No runtime teacher or intermediate teacher waypoints were added.

## Verification and decision

All 192 local rollouts, nine routes and three original chains have independent exact final replays. Original v7 fingerprints match historical results and paired starts match. Route and chain pause/resume checks exactly match uninterrupted results. Fresh demonstration features were independently replayed and compared; return prefixes and origins connect exactly to repaired approach endpoints.

The route-preservation and more-complete-routes gates fail. All other frozen gates pass. Candidate **rejected for selection**; no rollback is required. All cases are known development data, and the 96 reserved evaluation specifications remain untouched. No ROMs or artifacts were uploaded or committed.

## Provenance

- Candidate: `runs/navigation-routes-v9/model/epoch-008.pt`
- Candidate SHA-256: `e8df35550b771f44b3b05039eaa62d1ed6f1d1c681538da30b024e6346bf9586`
- Immutable plan: `runs/navigation-routes-v9/plan.json`
- Plan SHA-256: `66a19406002139c6d1f62243c9e022ad51de9fd2f9d168bc8365331550db0652`
- Results: `reports/navigation-routes-v9.json`
- Regression audit: `reports/navigation-routes-v9-audit.json`
- Selection decision: `configs/navigation_v9_candidate.json`

Next investigation should diagnose the learned cliff stalls and west-return regressions before another candidate is frozen. The repaired scripted demonstrations establish safe teacher paths, not learned navigation completion.
