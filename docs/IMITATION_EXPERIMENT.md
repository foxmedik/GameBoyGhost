# Demonstration-assisted sword experiments

This experiment diagnoses the deterministic stall, tests behavior cloning from the scripted route, then fine-tunes PPO from progressively earlier starts. All variants remain privilege D. A sword pickup is a task milestone, not full-game completion.

## Diagnosis and data

The previous close-start PPO policy selected right+A for all 2,048 deterministic actions, moved from x=65 to x=108, and stayed against an obstacle at y=79. Full traces and final images are under `runs/imitation-experiment-v1`.

The full scripted route yields 1,769 observation/action pairs. It is reproduced with physical buttons; the metadata records source savestate, route, and data hashes. Its original per-frame labels do not exactly match the ten-ready-frame deployment action clock. That timing mismatch is explicitly a limitation of this first behavior-cloning comparison. Label accuracy on these training pairs is not a held-out evaluation.

A separate feedback-scripted teacher creates 1,008 pairs in 12 successful close-start demonstrations. There are four physical left-movement perturbations, repeated three times; these are not 12 independent start distributions. The teacher uses precise position and dialogue reads, sends ordinary policy actions, and neither edits RAM nor runs during learned-policy evaluation.

The original observation has conflicting action labels for identical observations: 16 conflicting groups in the route data; 12 in the close teacher data. The latter has only 30 unique observations, and its exact-observation classification upper bound is about 67.9%. Alternating press/release labels and timing matter. This motivates an explicitly separate context variant.

## Variants

- `runs/imitation-experiment-v1`: original route behavior cloning, then staged PPO. Behavior cloning fits approximately 88.8% of training actions after 60 epochs.
- `runs/imitation-teacher-v1`: feedback teacher with matching action clock, original observation interface.
- `runs/imitation-context-v1`: the same feedback demonstrations with precise x/y, dialogue-state byte, and previous movement/button added as five normalized controller inputs. This wrapper only reads state and preserves action timing. It is a changed sensing contract, not an apples-to-apples policy-only comparison.
- `runs/imitation-context-refinement`: corrective teacher labels at states visited by a learned controller (DAgger-style dataset aggregation). Half the collection actions come from the teacher; evaluation uses only the learned policy. Round evaluations guide development and are not a held-out benchmark.

## PPO fine-tuning and provenance

The route policy is fine-tuned sequentially for 8,192 close-start steps, 16,384 beach-start steps, and 32,768 house-start steps. Each stage transfers policy weights, starts a fresh optimizer and horizon, and records its source policy path/hash. These transfers are new experiments, not exact continuation claims. Within each stage, the existing full checkpoint/resume contract is retained, with immutable raw shards and checkpoints every 8,192 steps.

`--warm-start` is deliberately distinct from `--resume`; resume rejects an initial-state/curriculum/weight-transfer override. Existing environment source files are unchanged by this experiment, so their current checkpoints remain compatible.

The context variant is currently a supervised controller experiment, not integrated into the full PPO checkpoint/restore contract. Supervised artifacts include policy weights, data, and training metrics; mid-epoch behavior-cloning resume is not implemented. Do not claim these weights alone are full experiment checkpoints.

## Evaluation rules

The fixed comparison uses one deterministic episode and three stochastic seeds (10000–10003) from each of the close, beach, and original house starts. The house already contains a shield in the supplied savestate. No teacher is active during evaluations, but learned policies remain demonstration-assisted by provenance. Reports distinguish each start and control randomness. These small samples and training-related starts do not establish generalization or reliability. Every final-stage evaluation retains action traces; earlier comparison models/seeds are preserved for replay.

The untrained baseline failed all beach/house episodes. The original route cloning model succeeded in two of three stochastic beach episodes and one of three stochastic house episodes, but failed deterministic play at every start. This establishes an observed autonomous policy-driven house-to-sword episode under the assisted harness, not a reliable house-start controller.

## Final findings

The staged PPO comparison completed 57,344 total steps. Close-stage training recorded 49 sword successes in 51 completed episodes; beach recorded 7 in 26; house recorded 0 in 16. All trajectory shard hashes, contiguous indices, and success counts validate. Replaying the final 8,192 house-stage steps reproduced the environment, policy tensors, and optimizer exactly.

Final fixed evaluation (three stochastic episodes per start, alongside one deterministic episode):

| Variant | Close stochastic | Beach stochastic | House stochastic | Deterministic |
| --- | --- | --- | --- | --- |
| Untrained baseline | 3/3 | 0/3 | 0/3 | 0/3 starts |
| Route imitation | 2/3 | 2/3 | 1/3 | 0/3 starts |
| Route imitation + staged PPO | 1/3 | 0/3 | 0/3 | 0/3 starts |

The staged PPO policy is not promoted. The route-imitation policy and its successful house episode seed remain preserved. Replaying that known seed is verification, not an additional independent success sample.

After two rounds of corrective context training, `runs/imitation-context-refinement/round-1/imitation-policy.zip` succeeds deterministically on all four training-related close starts (82–85 policy steps). A separate physical perturbation check succeeded on two of four additional setups; overall 6/8 deterministic close-start cases. This resolves the original close-start constant-action failure in those cases, but is not a reliable house-route policy.

A compact five-input controller ablation also solves the four training-related starts, but only one of four additional perturbations. It is retained as an experiment, not selected over the more robust contextual model. No teacher or action override is active in these learned-policy evaluations.

All 21 existing regressions pass; the additional controller-context purity, action-clock, and reset test also passes. The new wrapper does not alter gameplay RAM or action timing.

Next work should extend corrective, action-timed demonstrations along the earlier route while preserving the solved close-start behavior. Broadening the evaluation starts and seeds is necessary before claiming reliable house-to-sword performance. No unattended training batch is left running.
