# Focused beach-route regression fix

This experiment targets the remaining room-F2 goal at (118, 90), case
`7ca8327a...`, from the approach source episode. The v3 candidate followed the
parent for its first two actions, then took a different route and eventually
held left against an obstacle at (132, 77). The original parent succeeded;
v3 timed out after 128 actions.

## Results and selection

The regression is resolved: the candidate reaches the target in 18 actions
without damage, versus v3's 128-action timeout and the original parent's
20-action success. It passes the full gate and is now the selected experimental
navigator in `configs/navigation_experiment.json`.

| Panel | Original parent | v3 | Focused candidate |
|---|---:|---:|---:|
| Original regression | 42/48 | 45/48 | 46/48 |
| Additional regression | 37/48 | 37/48 | 39/48 |
| Latest development | 46/48 | 46/48 | 46/48 |

There are no lost successes relative to either comparison model and no damage
or deaths across all 144 local trials. All three continuous destinations
succeed without navigation damage in 49/49/45 actions for house/beach/approach.
Sword actions remain unchanged. All 45 tests pass, including the new test for
conflicting-label selection and checksum rejection.

This is development-based selection; the results do not establish independent
generalization. The default scripted explorer is unchanged. The selected
checkpoint remains a local artifact, with a compact versioned comparison in
`reports/navigation-focused-v4.json`.

## Diagnosis and correction

The earlier search retained every action in successful paths, including
exploratory detours and stationary loops. At some identical model-visible
inputs, those paths supply conflicting action labels. A successful complete
trajectory does not make every action within it equally useful for imitation.

Sixteen new damage-free demonstrations were collected from the initial handoff
and after 2, 10 and 96 actions of v3. Every accepted feature sequence and final
fingerprint passed fresh physical replay. Together with previous demonstrations
for this target, the data has 297 distinct model-visible states, including 68
with conflicting action labels.

The focused training view chooses the action associated with the shortest
observed remaining successful suffix for each identical masked input. It
retains source path, checksum, row, and observed remaining action count for
every label. These are observed costs, not a claim of globally optimal routes.
The underlying demonstrations remain unchanged.

Training starts from v3. A fixed eight-epoch pass at learning rate 0.00001
learns these labels while applying KL weight 8 to preserve v3's outputs on
original training states and the other verified demonstration states. Each
update uses 1,536 original states, 512 other demonstration states and 256
focused target states. Normalization and the previous-movement mask stay fixed;
there is no runtime coordinate exception or scripted override.

No new cohort is used: this target was already retired for correction training.
All three evaluation panels are now known development/regression panels. The
96 reserved evaluation specifications remain untouched. The assisted harness
is privilege D, goals are externally supplied, and full-game completion is
not evaluated.

## Validation and artifacts

The fixed candidate is evaluated against all three 48-case panels and the three
continuous starts. The gate requires no lost successes relative to either the
original parent or v3, zero damage/deaths, and all continuous goals reached
without navigation damage.

The experiment lives in `runs/navigation-focused-v4`. `training-plan.json`
contains the exact selected-label provenance, `data` contains new verified
paths, `target-check` records the focused replay, and `result.json` records the
broader comparisons. The model is `model/epoch-008.pt`.

Run from the project root, using a new output directory:

```sh
.venv-ladx/bin/python scripts/fix_navigation_regression.py collect \
  --out runs/NEW_FOCUSED_FIX
.venv-ladx/bin/python scripts/fix_navigation_regression.py train \
  --out runs/NEW_FOCUSED_FIX
.venv-ladx/bin/python scripts/evaluate_focused_navigation.py \
  --out runs/NEW_FOCUSED_FIX
```

The bounded trainer saves optimizer/RNG state each epoch but has no resume CLI.
The existing navigation-chain runner retains verified replay-based pause/resume.

House pause/resume at total action 420 reproduces the uninterrupted 461-action
run exactly, including all actions, final fingerprint/state and counters.
