# First live memory/planner integration

The goal manager now queries persistent memory, selects intermediate observed rooms when a multi-room chain exists, and otherwise uses explicitly labeled map-guidance goals. It delegates movement to the selected navigator, advances physical dialogue, records goal completion and stops after bounded stall recovery. It is a southern navigation prefix toward the forest, not yet a full prerequisite-aware quest planner.

Implementation: `src/gameboy_agent/progression_planner.py`, `scripts/run_progression_attempt.py`, and `configs/progression_guidance_v1.json` / `configs/progression_guidance_v2.json`. Tests: `tests/test_progression_planner.py`. Main evidence: `reports/progression-integration-v1.json`.

## Physical attempts

Both attempts physically reacquired the sword from the supplied house state, then continued without a reset, inventory edits or human rescue. Policies were unchanged. The plan and guidance were saved before each attempt, with 256 decisions per guidance goal and two short recovery probes after repeated local-position loops. Each run independently reproduced every action, state/observation fingerprint, frame count and planner decision. Planner JSON roundtrip continuation also matched.

| Attempt | Sword actions | Post-sword actions | Raw health lost | Result |
| --- | ---: | ---: | ---: | --- |
| v1 | 412 | 240 | 4 | Shore reached; stalled on direct handoff to cliff goal |
| v2 | 412 | 515 | 20 | Shore, existing approach, cliff and western passage goals reached; stalled approaching proposed northward crossing |

The one guidance change restored the existing E2 (89,94) approach goal between (36,121) and (64,64), matching the earlier developed route sequence. In v2, those three goals required 49, 30 and 87 actions respectively. This demonstrates a useful handoff correction in this attempt, not a general robustness or safety claim. Later western passage movement used a recovery probe and cost substantial health.

The second attempt stopped alive at E1 (10,26), health 4 raw units, while targeting D1 (12,112). Whether the proposed crossing is physically usable at those coordinates or the navigator simply cannot execute it remains unverified. The first next diagnostic is a bounded physical crossing/terrain check, not a neural retraining sweep. No further blind attempts were run.

## Memory contribution

Live decisions queried the inherited memory. The post-sword prefix had no usable multi-room known route; the intermediate-memory branch is covered by a separate test on the known house-to-sword chain. This is not yet evidence that inheritance improves gameplay efficiency.

After replay verification, observations from both attempts were merged into `runs/progression-integration-v1/memory-generation-2.json`. It contains 4,157 evidence-backed observations and four newly observed distinct directed connections: F2→E2, E2→E1, E1→E2 and E1→E0. Repeated sword prefixes count as additional trace observations, not new independent skills. Failed movement and damage observations are retained with circumstances; no permanent wall or damage-cause claim is inferred.

Full regression: 91/91 tests passed in 38.746 seconds, including five new planner tests. No optimizer updates, reserved evaluation or Tail Key acquisition occurred. Stage 3 remains in progress with an identified blocker. Exact NPC text, witch exchange and the rest of the quest manager remain future integration work.

Run a frozen guidance version into a fresh directory:

```bash
.venv-ladx/bin/python scripts/run_progression_attempt.py --out runs/progression-attempt-next --guidance configs/progression_guidance_v2.json
```

The runner currently defaults to the generation-1 input memory so the two comparisons share the same starting knowledge. Select the new cumulative memory explicitly in the next frozen experiment before claiming use of the newly learned connections.
