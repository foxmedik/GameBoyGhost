# Navigation correction from live trajectories

This experiment collects the states visited during live regressions, preserves
successful parent trajectories, and trains one candidate on the expanded data.
The parent remains the starting checkpoint. The previous weight-4 candidate
supplies the off-route prefixes; it is not the training initialization.

## Results

The expanded data fixes two of the three regressions seen with the prior
weight-4 candidate. One original-panel regression remains, so this candidate
does not replace the selected parent.

| Panel | Parent | Prior weight-4 candidate | Expanded-data candidate | Expanded candidate's lost parent successes |
|---|---:|---:|---:|---:|
| Original regression panel | 42/48 | 45/48 | 45/48 | 1 |
| Additional regression panel | 37/48 | 35/48 | 37/48 | 0 |
| Fresh development panel | 46/48 | Not evaluated | 46/48 | 0 |

The expanded candidate has zero damage and zero deaths across all 144 local
trials. Its additional/fresh successes are exactly the parent's successes,
not offsetting gains and losses. On the original panel it gains four goals and
loses one. Both older panels now substantially contain training examples.

All three continuous destinations are reached without damage: house and beach
require 49 navigation actions, approach 45. Sword actions are exactly unchanged.
The goal-aware greedy baseline reaches 48/48 on the fresh panel, so learned
navigation still trails that simple diagnostic on these selected local goals.

Collection produced 48 new recovery demonstrations and 79 verified parent
trajectories. Together with the 96 earlier demonstrations, this is 223 paths
and 5,678 action examples before deduplication; training uses 182 unique
feature/action sequences with 4,741 examples. Every accepted path passes
physical replay and artifact verification. All 44 tests pass.

The remaining regression is the beach goal in room F2 at (118, 90), starting
from the approach episode represented by case `7ca8327a...`. Its full case
specification and candidate trace are in `remaining-regressions.json`.
Successful recovery examples exist for this route, but the candidate still
does not reproduce reliable goal-reaching behavior from its evaluated start.
That distinction is the focus for further diagnosis; collecting a successful
teacher path does not itself guarantee that behavior cloning learns it.

The candidate is recorded in `configs/navigation_live_correction_v3.json` as
not promoted. `configs/navigation_experiment.json` remains unchanged. The
reserved evaluation set has not been consumed.

## Data and separation

Three previously successful routes regressed under the weight-4 candidate.
Their first recorded action differences occur at navigation steps 1, 1, and 7.
These are first policy divergences, not proof that an individual action alone
caused the eventual timeout. Collection replays each shared source episode and
then its candidate actions up to that divergence, eight actions later, and
step 96. It also targets the original local correction route still missed by
both parent and candidate, for 12 recovery origins in total.

The branching checks show that the parent succeeds immediately before each
of the three first divergences, but fails at all six later sampled positions.
The parent also fails at all three positions on the remaining original route.
The searched teacher produces safe successful paths from all 12 origins.

At each origin, the parent is tried as a recovery teacher, followed by bounded
physical goal-directed search with directional detours. Up to four paths are
accepted per origin, only after actual success with zero health loss. Every
accepted feature/action sequence and final fingerprint is reproduced through
fresh physical replay. Source Parquet observations must match at the original
handoff. Images and action prefixes are retained for inspection.

The data also preserves all 79 successful, damage-free parent trajectories
from the two prior 48-case panels. Their recorded actions are replayed and
verified, with one demonstration per route. The previous 96 recovery
demonstrations are referenced unchanged through links to their immutable run
directories.

All cohorts containing preservation or correction episodes are retired from
validation: 78 cohorts in total. Before collection and training, a new balanced
48-case development panel was frozen, excluding these cohorts and every episode
in either old live panel. The old panels now serve substantially as training
regressions, not independent validation. The new panel remains development
evaluation, and the 96 reserved evaluation specifications are untouched.

## Training and checks

The experiment plan fixes a single candidate: 12 epochs, Adam at 0.00005,
1,536 original training samples plus 512 expanded correction/preservation
samples per batch, and parent-preservation KL weight 4. Parent normalization
and the previous-movement mask stay fixed. Exact duplicate feature/action
sequences are removed before sampling. Final-epoch selection is fixed before
live evaluation.

The gate requires no lost parent successes, damage, or deaths on all three
panels, plus all three continuous sword-to-destination runs without navigation
damage. Sword action sequences and paired evaluation-start fingerprints are
checked. This is still the inherited privilege-D harness with externally
supplied goals; full-game completion is not evaluated.

## Reproduction and artifacts

From the project root, using a new experiment directory:

```sh
.venv-ladx/bin/python scripts/navigation_live_correction.py prepare \
  --out runs/NEW_LIVE_CORRECTION
.venv-ladx/bin/python scripts/navigation_live_correction.py collect \
  --out runs/NEW_LIVE_CORRECTION
.venv-ladx/bin/python scripts/verify_live_correction.py runs/NEW_LIVE_CORRECTION
.venv-ladx/bin/python scripts/navigation_recovery.py train \
  --data runs/NEW_LIVE_CORRECTION/data --out runs/NEW_LIVE_CORRECTION/model \
  --epochs 12 --anchor-weight 4
```

Before `evaluate_live_correction.py`, evaluate the parent against the new
`fresh-panel` with `evaluate_navigation.py`, writing `fresh-parent` in the
experiment directory. The evaluator then compares the candidate across all
three panels and runs the continuous routes.

The concrete experiment is `runs/navigation-live-correction-v3`. Its plan,
source snapshots, immutable demonstration references, collection logs,
`audit.json`, model checkpoints and per-action evaluation traces preserve
provenance. The correction trainer saves optimizer/RNG state but does not
currently expose a resume CLI; the existing navigation-chain runner supports
verified pause/resume.

The candidate also passes exact house pause/resume at total action 420: all
actions, final state/fingerprint and counters match the uninterrupted 461-action
run. See `resume-verification.json`.

## Follow-up

The [focused suffix-label correction](NAVIGATION_FOCUSED_FIX_V4.md) resolves
this regression and passes the broader gate; that checkpoint supersedes v3
and the original parent as the selected experimental navigator.
