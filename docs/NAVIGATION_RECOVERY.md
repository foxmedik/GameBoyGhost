# Targeted navigation recovery

This experiment uses the six missed local goals and two stalled continuous
sword-to-navigation runs from the first navigation experiment to collect
corrective demonstrations. These are development corrections, not independent
validation cases. The 96 reserved evaluation specifications remain unused.

The inherited assisted harness has privilege D. Goals are supplied externally.
No full-game completion is evaluated.

## Results and selection

The corrected candidate repairs all three continuous sword-to-destination runs
without damage. It does not replace the selected general navigator because
local regressions and new health loss offset the broader benefits.

| Evaluation | Parent | Corrected candidate |
|---|---:|---:|
| Six local correction cases (now training regressions) | 0/6 | 5/6 |
| Other original regression cases | 42/42 | 40/42 |
| Original panel total | 42/48 | 45/48 |
| Additional development panel | 37/48 | 37/48 |
| Continuous exact destination | 1/3 | 3/3 |

The additional panel has three gained and three lost goals. Corrected policy
health loss totals eight raw health units on the original panel and four on
the additional panel, versus zero for the parent on both. Neither learned
policy dies on these panels. The goal-aware greedy baseline reaches 45/48
additional development goals without damage, so learned navigation still has
clear room for improvement.

| Continuous start | Parent navigation actions | Corrected navigation actions |
|---|---:|---:|
| House | 66, success | 49, success |
| Beach | 384, timeout | 49, success |
| Approach | 384, timeout | 45, success |

Sword actions are exactly unchanged. Corrected house pause/resume at total
action 420 reproduces the uninterrupted 461-action run, including every action,
final fingerprint, final state and counters.

Collection produced 96 demonstrations from 106 attempts across 24 origins,
covering all eight source cases. All accepted traces passed fresh physical
replay. There are 73 unique origin/action sequences; exact feature/action
sequence deduplication leaves 59 training sequences and 1,835 action examples
from 2,539 accepted rows. These are targeted examples, not independent episodes.

All 42 existing tests pass. The separate recovery audit checks all accepted
artifacts and labels, physical action ranges, feature finiteness, and the
additional panel's episode/cohort exclusions.

Artifacts:

- `runs/navigation-recovery-data-v1`: demonstrations, attempt logs and screenshots.
- `runs/navigation-recovery-model-v1/epoch-012.pt`: fixed final-epoch candidate.
- `runs/navigation-recovery-comparison-v1.json`: paired outcomes and resume check.
- `runs/navigation-recovery-verification-v1.json`: data and split audit.
- `runs/navigation-recovery-remaining-cases-v1.json`: failures and damage for follow-up.
- `configs/navigation_recovery_candidate.json`: candidate record, explicitly not promoted.

The selected experimental parent in `configs/navigation_experiment.json` is
unchanged. The next experiment should constrain changes away from corrected
states (for example, preserve the parent's outputs on existing training
states) and address the remaining route failure before another general
promotion decision. Additional-panel results are now known development results.

## Method

`navigation_recovery.py freeze` selected 48 additional development cases before
collection or corrective training. It excludes all original live-test episodes
and every curated cohort containing one of the six correction episodes. The
panel is balanced over house/beach/approach and same-room/cross-room goals.
It still comes from the development data pool and is not a held-out benchmark.

Collection starts at the original skill handoff and after 32 or 96 actions of
the previous policy. Each of the 24 origins receives up to 24 bounded physical
rollouts, with a goal-directed teacher and deterministic directional detours.
The teacher can use the original successful source segment at its original
start as a fallback. Only actual successes with zero observed health loss are
accepted, up to four per origin. This is searched assisted supervision, not a
claim of optimal or human expert behavior.

Every attempt reconstructs the source episode by physical action replay.
Original dataset observations must match exactly at the handoff. Each accepted
path is replayed again in a fresh environment: all 250-feature observations and
the final emulator fingerprint must match. PNGs, physical actions, source
hashes, attempt outcomes and the collector source are retained with the data.
The search teacher is not part of the deployed controller.

Corrective training starts from the previous 64-epoch no-movement-history
network. Normalization and the input mask stay fixed. Twelve epochs use Adam
at 0.00005, with 1,536 original training examples and 512 sampled correction
examples per batch. Identical feature/action sequences are deduplicated.
The final epoch is fixed before evaluation; development action accuracy does
not select a checkpoint. The old cached development examples are not used in
this fine-tuning pass because correction episodes have been retired.

The new policy is compared with its parent on the additional 48 cases, the
original 48 as a regression panel, and all three continuous starts. Regression
success on the six training corrections does not establish generalization.

## Commands

Run from the project root; outputs must be new directories.

```sh
.venv-ladx/bin/python scripts/navigation_recovery.py freeze \
  --out runs/NEW_RECOVERY_PANEL
.venv-ladx/bin/python scripts/navigation_recovery.py collect \
  --out runs/NEW_RECOVERY_DATA --workers 8
.venv-ladx/bin/python scripts/verify_navigation_recovery.py \
  --data runs/NEW_RECOVERY_DATA --panel runs/NEW_RECOVERY_PANEL \
  --out runs/NEW_RECOVERY_VERIFICATION.json
.venv-ladx/bin/python scripts/navigation_recovery.py train \
  --data runs/NEW_RECOVERY_DATA --out runs/NEW_RECOVERY_MODEL --epochs 12
```

The bounded correction trainer writes model, optimizer, normalization and RNG
state every epoch, but does not currently expose a resume command. Existing
navigation-chain replay/resume behavior is unchanged.

## Second batch

The [behavior-preservation batch](NAVIGATION_RECOVERY_BATCH_V2.md) tests three
constraint strengths. It reduces damage but does not pass the full regression
gate; the selected general parent remains unchanged.
