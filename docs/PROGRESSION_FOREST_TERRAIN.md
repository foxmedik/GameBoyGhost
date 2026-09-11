# Forest progression checkpoint

The continuous house prefix now reaches the forest and explores onward with all three hearts intact. The best development run uses 2,349 physical decisions: the verified 749-decision house-to-D0 prefix followed by 1,600 bounded exploration decisions. Independent fresh reconstruction reproduces the full action trace, fingerprints, journal and planner decisions exactly. Toadstool, powder, Tail Key and Tail Cave entry remain incomplete.

This adds scripted local navigation over read-only ROM object physics, with source-grounded room guidance. It does not train a new policy. The local grid admits known ground, stairs, shallow water and grass; unknown physics, pits and ledges are excluded. Known sword-cuttable objects receive a planning allowance and actual physical sword actions. Other removable objects are not treated as cuttable. Shielding uses the already equipped shield.

## Bounded development results

| Run | Extension decisions | Health lost, raw | Outcome |
| --- | ---: | ---: | --- |
| v1 | 303 | 4 | Coarse room visits; stopped at damage limit |
| v2 | 1,600 | 0 | Separate reachable regions; reached forest approach, lacked cutting |
| v3 | 427 | 0 | Physical cutting enabled; entered forest, rejected routes during stationary pause |
| v4 | 429 | 0 | Tighter lane centering; same pause remained |
| v5 | 1,600 | 0 | Longer bounded settling allowance; handled two dialogues and explored forest; budget exhausted |

The best extension visits 14 distinct overworld rooms, makes 16 observed transitions, opens and closes two dialogues, and issues 23 decisions with cutting intent. Cutting intent alone is not an attributed destruction event. Dialogue IDs are `0C0` in room `80` and `021` in room `51`; speaker and exact text are not decoded. The trace contains no health-loss or healing events. Final state is room `52`, position `(71,115)`, health `24/24`.

The stationary threshold increased from 24 to 192 emulated frames before rejecting an exit. This permits the observed scripted pause to lead into dialogue, but is not a general cutscene detector. Room component visit counts and cached grids are episode-local scratch state. Persistent world memory separately retains trace-backed observations and directed connections; inherited component planning and an efficiency benefit remain unproven.

## Evidence and continuation

Aggregate report: `reports/progression-forest-progress-v1.json`. Individual results, frozen plans, physical traces, journal, final state and image are in `runs/progression-forest-terrain-v1` through `v5`. The aggregate generation at `runs/progression-forest-progress-v1/memory-generation-4.json` preserves all five verified runs, including failures, on top of the previous crossing memory. Repeated prefix observations are evidence, not independent successful trials.

Reproduce the current implementation with a new output directory:

```sh
.venv-ladx/bin/python scripts/extend_forest_route.py --cut-flora --out-name progression-forest-reproduction
```

This requires the existing local v4 progression fixture, ROM and policy artifacts. It physically reconstructs the prefix from the initial house state; it does not load a forest checkpoint mid-episode. Output directories must be new.

Validation: 101 tests passed in 37.874 seconds, including seven local terrain tests. All five development runs passed independent exact replay. There were zero new optimizer updates and no reserved evaluation use. One deterministic trajectory does not establish varied-start reliability.

The next step is to replace outdoor room-distance exploration with explicit verified approach subgoals for the toadstool, including any required indoor transitions. The current runner stops on an unexpected indoor transition, so it cannot yet execute a cave route. Preserve zero-damage forest entry as a regression, and verify the next physical interaction before collecting training data. Stage 3 remains in progress.
