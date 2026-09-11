# Cliff starting-position stress test

A frozen development stress test evaluates the selected cliff-specialists-v2 navigator without retraining or changing selection. **34/48 perturbed starts finish safely**; nine finish with damage and five time out. All 12 controls match their original safe runs exactly. The strict stress gate fails.

## Frozen scope

Three historical starts (house, beach, approach) each supply four deterministic anchors on the successful learned cliff loop:

- Start of the cliff goal.
- First entry into the western room during the cliff goal.
- First re-entry into the upper side of the original room.
- Start of the return goal.

At each anchor, test an unchanged control and four perturbations: up, down, left or right for four physical actions. The setup alternates the equipped sword from the previous button state. It advances the real episode; there are no coordinate writes, teleports, retries or selected replacement cases. These actions alter position, facing, timing and potentially enemy state, so this is not a position-only causal experiment.

The 12 controls must reproduce the original action suffix and final fingerprint exactly. The 48 perturbed cases use the same original final goals and unchanged policy. Each remaining goal has a 256-action budget starting at the stress handoff; historical prefix and setup actions are excluded from that budget. Thus this measures continuation from perturbed states, not the original full-route budget with extra actions charged to it.

## Safety accounting

If setup causes damage, death or environment termination, stop setup and classify the case separately without running learned navigation. Every such case remains in the frozen 48-case denominator. Damage during setup is not attributed to the learned controller.

All other cases remain eligible, including room transitions and movements blocked by walls. Report actual position changes and unique initial fingerprints. Learned navigation continues until success, death, environment termination or budget exhaustion, allowing separate counts for completion, damage-free completion and damage/deaths.

The strict stress gate requires all 48 perturbations to have safe setup and safe learned completion, alongside exact control matches. Valid-setup completion is also reported separately; it must not silently hide setup exclusions.

## Verification and limits

Every prefix, physical setup and recorded learned continuation is independently replayed. Every learned feature row and the final fingerprint must match. Selected policy, selection configuration, fixed sword configuration, retired-cohort registry and runtime source hashes are checked before and after the run.

An input-match diagnostic compares initial masked inputs with the latest active expert's supervised examples. It does not establish absence from inherited pretraining. These are new perturbations of known development routes with unchanged final goals, not held-out maps, new goals or reserved evaluation.

No training, correction collection or policy selection occurs in this experiment. Observed rollout arrays are diagnostic records, not curated training demonstrations. Sword reduction stays paused; the 96 reserved evaluation specifications remain untouched.

## Artifacts

- Immutable plan: `runs/navigation-cliff-stress-v1/plan.json`
- Plan SHA-256: `d615beb326b12a7888f3e413f611108ce682ea3bcbae59f1b3c4e03d78d2f3eb`
- Policy: `runs/navigation-cliff-specialists-v2/model/epoch-256.pt`
- Policy SHA-256: `9d2b24b28be5289fc3d32d85d46faa1835ca2068d73a1e8790630d77dbaf85ec`
- Portable result: `reports/navigation-cliff-stress-v1.json`
- Source: `scripts/evaluate_cliff_stress.py`

## Completed results

All 48 perturbations have valid, zero-damage setup. There are 48 distinct perturbed initial fingerprints; 45 cases change position and three are wall-blocked. Only one initial masked input matches the latest expert supervision (this is not a claim about all inherited pretraining).

| Perturbation anchor | Cases | Completed | Safe completion | Damage cases | Timeouts |
| --- | ---: | ---: | ---: | ---: | ---: |
| Cliff entry | 12 | 9 | 8 | 1 | 3 |
| Western corridor | 12 | 11 | 9 | 2 | 1 |
| Upper-room re-entry | 12 | 12 | 8 | 4 | 0 |
| Return entry | 12 | 11 | 9 | 2 | 1 |
| **Total** | **48** | **43** | **34** | **9** | **5** |

Overall safe completion is 70.8%; completion regardless of damage is 89.6%. Nine cases each take four raw damage units, for 36 total. No deaths occur. All five timeouts are damage-free. The 12 unperturbed controls pass safely and match both historical action sequences and final fingerprints. All 60 independent replays and all recorded input-feature comparisons pass.

## Observed failure phases

Eight of the nine first-damage events occur during the return goal; one occurs during the cliff approach. Three of the five timeouts are on the return goal, and two on the cliff approach. In particular, downward perturbations at cliff entry fail safe completion for all three starts: house reaches the cliff but stalls on return, while beach and approach stall in the western room before reaching the cliff goal.

All four house upper-entry perturbations finish with damage. One of them is blocked from changing position during setup, illustrating why these results cannot isolate position from timing, facing and combat-state effects. Another position-unchanged western-corridor case also takes damage.

The immediate research priority is return safety/recovery under changed arrival states, plus the lower western-corridor failure after downward entry shifts. The current 9/9 result remains valid on its known original routes; this stress panel establishes that broader robustness is unfinished. No rollback, retraining or selection change was made.

Detailed phase classification and repeated terminal positions are in `reports/navigation-cliff-stress-v1-audit.json`. If these cases are used for corrections later, treat them as development regression cases thereafter and freeze separate stress cases before new generalization claims.
