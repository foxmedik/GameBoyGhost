# One-hour run: reproducible proof, failed varied-start reliability

The frozen mixed recorded-prefix/scripted-suffix baseline failed the full-quest reliability gate: **0/20 development and 0/20 separate validation starts completed**, while the unperturbed control succeeded. This measures the scripted baseline, not a learned AI-model policy. The result does not invalidate the original exact-start proof; it shows that proof is timing-sensitive.

The batch ran from 2026-09-11 18:26:17 UTC to 19:26:27 UTC: **60 minutes 10 seconds**, including the last case finishing after the admission deadline. It completed235 cases, with896,813 recorded decisions and5,768,627 emulator frames, plus896,813 decisions independently replayed. All235 case manifests verify and all235 replay results pass. Source snapshots/current source and selected model hashes match. All116 regression tests pass (37.019s); logs are preserved.

The data totals include repeated house prefixes and are not unique learning samples. The194 conditional development probes add **81,347 post-prefix decisions**, including their physical perturbation setup. No training, RAM perturbation, intermediate state loading, runtime rescue, historical reserved navigation evaluation or validation-driven tuning occurred.

## Separate panels and health accounting

| Panel / stage | Successes | Deaths | Final health min–max | Total damage / healing |
| --- | ---: | ---: | ---: | ---: |
| control/house | 1/1 | 0 | 20–20 | 20 / 16 |
| development/house | 0/20 | 6 | 0–20 | 264 / 0 |
| validation/house | 0/20 | 5 | 0–20 | 276 / 0 |
| development_probe/witch-approach | 28/28 | 0 | 8–12 | 344 / 0 |
| development_probe/witch-exchange | 21/33 | 5 | 0–12 | 552 / 16 |
| development_probe/tarin | 29/40 | 9 | 0–24 | 784 / 136 |
| development_probe/tail-key | 24/24 | 0 | 4–20 | 480 / 16 |
| development_probe/tail-cave | 31/34 | 3 | 0–20 | 692 / 56 |
| development_probe/toadstool | 2/35 | 22 | 0–17 | 709 / 0 |

Health values are raw units. Damage and healing totals include each case’s physically reconstructed prefix; they are not suffix-only costs. Deaths are a subset of failures. The six stage-probe groups are conditional on reaching their exact supplied prefix, and are development diagnostics; they cannot be pooled with the20 house validation cases or used to claim end-to-end reliability. The720 planned probes were sampled in frozen shuffled order until the hour deadline;194 completed.

## What failed

Of40 varied house cases,11 died during the recorded prefix. The other29 reached the live suffix in an unsuitable state:28 raised a route delta KeyError (23 at delta−48,4 at−64,1 at−97), and1 failed terrain approach. These are failed handoffs, not successful prefix completion. Final failure locations are preserved separately for development and validation in the report; the development set most often stopped in overworld81 (11 cases), with other outcomes inD1,C1,90,91 and indoor12:B2. Validation outcomes must remain excluded from tuning.

Mushroom collection is the weakest conditional stage (2/35). Failures concentrate in overworld52,62,42,50 and indoor0A:BD;22 die, including3 during the physical perturbation itself. The raw route and its cave-mouth approach do not recover reliably from timing/position changes.

All12 witch-exchange failures stop in overworld42:5 deaths and7 approach stalls/budget failures. Tarin has11 failures:7 in42,2 in54,1 in52 and1 in61, with9 deaths. Tail Cave has3 deaths:1 in70 and2 inC3. Cave return (28/28) and Tail Key pickup (24/24) are the strongest conditional stages on this sampled development set. Tail Cave succeeds31/34, but this does not meet or replace a frozen end-to-end validation panel.

## Next work

Use development evidence to replace the timing-sensitive recorded-prefix handoff with state-checked progression and explicit recovery, starting at the earliest divergence. Validate stage preconditions before invoking route traversal so a wrong room yields a precise blocker rather than a KeyError. Then address the mushroom approach and room42 movement/combat bottleneck. Establish a reliable teacher and freeze a new experiment before training. Preserve the existing20 validation specifications/results as evaluation evidence; do not tune on them or relabel them as development data.

## Evidence and completion

Portable report: `reports/progression-longrun-hour-v1.json`. Frozen plan, source snapshots, results.jsonl, completion.json and verification.json: `runs/progression-longrun-hour-v1/`. Each case has a hash manifest, trace, journal, final image/state and replay result. Test evidence: regression-tests.log and regression-tests.json.

The job stopped at its requested deadline and was not restarted or extended. Follow-up monitoring is being paused after this report; no deeper dungeon work or training has begun.
