# Navigation recovery: behavior-preservation batch

This batch tests whether preserving the parent's predictions on original
training states prevents the regressions introduced by targeted correction.
All three candidates start from the selected 64-epoch parent and use the same
1,835 deduplicated recovery action examples and 346,536 original training
examples as the preceding correction experiment. No additional development
failures are converted to training examples in this batch.

## Results

No candidate passed the preregistered gate, so the selected parent is unchanged.
All candidates reach all three continuous destinations without damage, in
49/49/45 navigation actions for house/beach/approach. Sword actions are unchanged.

| Candidate | Original panel | Additional panel | Parent successes lost, original/additional | Health lost, original/additional |
|---|---:|---:|---:|---:|
| Parent | 42/48 | 37/48 | — | 0/0 |
| Previous unconstrained correction | 45/48 | 37/48 | 2/3 | 8/4 |
| Preservation weight 1 | 45/48 | 36/48 | 2/2 | 0/4 |
| Preservation weight 4 | 45/48 | 35/48 | 1/2 | 0/0 |
| Preservation weight 16 | 44/48 | 34/48 | 1/3 | 0/0 |

There are no learned-policy deaths in this batch. Health loss uses raw game
health units. Scores on the original panel include six correction-training
cases, so they cannot be interpreted as held-out success rates.

The constraint has the intended effect on original training states: movement
predictions differ from the parent on 7.77% of states for the previous
unconstrained correction, versus 5.14%, 3.42%, and 2.10% at weights 1, 4, and 16.
But stronger preservation does not improve live success on the additional
panel. Cached-state preservation alone is insufficient to protect these routes.

The batch completed 288 learned-policy local trials and nine continuous runs.
Cached baseline results were reused only after case/budget matching; initial
fingerprints match for every paired comparison. All 44 tests pass, including
two tests that check the new loss leaves the teacher frozen and moves the
candidate toward its predictions.

The next useful experiment is to collect corrective supervision along the
live trajectories where the candidate and parent diverge, with explicit
retirement of any development cohorts incorporated into training. Raising the
preservation weight further is not supported by these results.

Artifacts are under `runs/navigation-recovery-batch-v2`: `result.json` holds
all paired comparisons, `behavior-preservation.json` records training-state
changes, `anchor-*` contains checkpoints and training provenance, and `eval-*`
contains actions, outcomes, and continuous-run screenshots. The unpromoted
candidate registry is `configs/navigation_recovery_batch_v2.json`.

## Fixed experiment

Each candidate trains for 12 epochs with Adam at 0.00005. Its supervised loss
is augmented with KL divergence from the frozen parent on original training
states, weighted by 1, 4, or 16. Movement and button heads are separate, with
button divergence weighted by 0.25. The teacher probabilities are detached;
only the candidate receives gradients. Parent normalization and the previous
movement input mask remain fixed.

`runs/navigation-recovery-batch-v2/plan.json` was written before training.
Every candidate uses its fixed final epoch. Selection requires no lost parent
successes, zero damage and zero deaths on both 48-case development panels,
and all three continuous destinations reached without damage. If multiple
candidates pass, total successes and then action count break ties.

The original panel includes six correction-training cases. The additional
panel excludes their cohorts but its results are already known from the last
experiment. This is development model selection, not an independent test.
The 96 reserved evaluation specifications are untouched. The inherited
assisted harness remains privilege D; goals are externally supplied and
full-game completion is not evaluated.

## Reproduction

Use a new output directory for every run, from the project root:

```sh
.venv-ladx/bin/python scripts/navigation_recovery.py train \
  --data runs/navigation-recovery-data-v1 \
  --out runs/NEW_ANCHORED_MODEL --epochs 12 --anchor-weight 4
```

`scripts/evaluate_navigation_batch.py` reads the batch plan, runs both panels
and all three continuous starts for each candidate, verifies paired initial
fingerprints and unchanged sword actions, and applies the selection gate.
Training checkpoints include model, optimizer, RNG states, input mask,
normalization, hashes and a source snapshot. The bounded correction trainer
does not currently expose a resume CLI. Navigation-chain replay/resume is
available through the existing runner.

The weight-4 house run also passes exact pause/resume verification at total
action 420: all actions, the final fingerprint/state, and counters match the
uninterrupted 461-action run. See `verification.json` in the batch directory.

## Live-trajectory follow-up

The [expanded live-correction experiment](NAVIGATION_LIVE_CORRECTION_V3.md)
collects parent trajectories and off-route recovery paths. It removes two of
three regressions, but one original-panel regression still prevents promotion.
