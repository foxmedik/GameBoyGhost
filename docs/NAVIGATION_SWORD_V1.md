# Learned selective sword candidate v1 — rejected

The designated epoch-008 candidate fails the frozen promotion gate. **Selected route v7 remains unchanged.** The terrain+motion collection teacher still has its separately verified 66.5% swing reduction; that result did not transfer reliably to this trained controller.

| Measure | Selected v7 | Candidate |
| --- | ---: | ---: |
| Original local panel | 46/48 | 42/48 |
| Additional local panel | 43/48 | 42/48 |
| Fresh local panel | 46/48 | 47/48 |
| Local damage, raw units | 0 | 4 |
| Complete routes | 6/9 | 4/9 |
| Route waypoints | 30/36 | 28/36 |
| Original continuous chains | 3/3 | 3/3 |
| Route damage / deaths | 0 / 0 | 0 / 0 |
| Actual swings on original 48 | 582 | 568 |
| Actions on original 48 | 1,155 | 1,427 |
| Frames on original 48 | 12,670 | 15,390 |

Swing reduction is only **2.4%**, below the frozen 25% requirement. Five previously successful local cases are lost, one is gained, and a separate still-successful case incurs damage. The fresh-panel gain cannot offset these regressions. Two previously successful west-return routes fail. No deaths occur.

## Training and evaluation

The existing frozen plan was checked against its hash, selected parent, trainer source, and baseline hashes before execution. Training used all eight fixed epochs, learning rate 5e-6, balanced new/preservation supervision, retention and action-margin losses. Only epoch 008 was evaluated. No checkpoint shopping or retraining occurred.

The 244 verified paths supply 7,063 rows: 42 new teacher demonstrations (290 rows) and 202 preservation paths (6,773 rows). Shortest-observed-suffix selection leaves 4,882 distinct normalized-input keys and 144 conflicting-label states. Retention includes 346,536 original rows and 12,979 prior-demonstration rows. All shared network layers and movement/button outputs are trainable under this frozen method; no teacher terrain or motion rule is inserted into learned runtime.

Evaluation runs 192 local rollouts: both v7 and the candidate on the original 48 cases, plus the candidate on each additional 48-case panel. Every final trajectory has an independent exact physical replay. Rerun v7 original fingerprints match the historical results. Candidate results use matching initial fingerprints against all three v7 panels. Nine continuous routes and three original chains also receive independent final replay. Separate route and chain pause/resume tests reproduce the uninterrupted actions, final fingerprint, counters, status, state, and route progress exactly. All checks completed; no reserved evaluation or full-game benchmark was used.

## Regression audit

All five lost local successes and the damage-increase case were inspected with first action divergence, repeated positions, damage windows, and final states:

- Original 794f8293... first changes both movement and button, then spends 119 actions at F0 (108,67).
- Original 4b4081e2... first suppresses a sword press with the same movement, then spends 111 actions at E2 (32,87).
- Original 2881dd94... first changes both movement and button, then oscillates between E0 (35,89) and (35,99), 62 actions each.
- Original c2d33e5c... first suppresses a sword press with the same movement, then spends 110 actions at E1 (18,112).
- Additional e4a3a8a5... first changes movement at action 31 and times out near the east edge of E1.
- Additional 49ee820f... still succeeds but takes four extra raw health units from a sand-crab encounter. Its first action changes movement from right to up while retaining the sword press. Damage begins at action 8 near F3 (12,64).

Both lost west-return routes (beach and approach starts) time out before the final goal, spending 227 navigation actions at E1 (145,64). The beach route first changes movement at action 356; approach first changes its sword button at action 176. These observations locate divergence and stalling; they do not establish a single causal mechanism.

On the 290 new training rows only, button-label agreement increases from 36.2% to 59.0%, and no-button predictions rise from 52 to 122. This demonstrates some fitting of the new labels, not live competence. Inherited movement-label agreement changes from 85.47% to 85.29%; a small average change does not prevent large live trajectory regressions.

## Decision and next hypothesis

Reject this candidate and preserve selected v7. The original frozen training plan remains immutable; `configs/navigation_sword_candidate.json` and the result report record the completed/rejected status.

A useful next bounded experiment would freeze the shared representation and movement outputs, training only button outputs with selective-sword supervision. This would isolate direct movement-function drift, but changing buttons can still change timing, terrain and subsequent states. It would require a new frozen plan and the same complete preservation gates. No such candidate has been trained or claimed successful.

Artifacts: `reports/navigation-sword-v1.json`, `reports/navigation-sword-v1-audit.json`, and ignored run directory `runs/navigation-sword-v1`. Evaluation and audit scripts are `scripts/evaluate_sword_candidate.py` and `scripts/audit_sword_candidate.py`. ROMs, checkpoints and raw traces remain local; no commit or upload occurred.
