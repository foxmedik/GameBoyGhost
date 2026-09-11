# Multi-goal navigation experiment v1

The fixed eight-epoch candidate improves complete scripted routes from 0/9 to 2/9, but fails the preservation gate. The selected navigator remains focused v4. The candidate and its correction data are retained locally for diagnosis.

## Results

| Check | Selected v4 | Route candidate |
| --- | ---: | ---: |
| Complete four-goal routes | 0/9 | 2/9 |
| Ordered waypoints reached | 19/36 | 22/36 |
| Route navigation damage (raw health units) | 20 | 16 |
| Route deaths | 1 | 1 |
| Original local panel | 46/48 | 46/48 |
| Additional local panel | 39/48 | 43/48 |
| Fresh local panel | 46/48 | 45/48 |
| Original sword-to-goal chains | 3/3 | 3/3 |

The two completed routes are beach_return from beach and approach, both without navigation damage. The room_loop route stalls at its third goal from all starts. west_return reaches three goals from house, but regresses from two to one completed goals from beach and approach; the beach run dies. Aggregate gains therefore do not justify replacement.

Local comparisons verify matching physical replay fingerprints for all 144 starts. Four additional-panel failures improve and no original-panel successes are lost. Fresh case `d5f00d7e9f023bd1bb87305aefd12456734ef575a04390ba3dba2e409ee972bf` regresses from an 18-action success to death at action 19, with four health units lost. Its first action disagreement is index 3. This is a cross-room goal from E0 (25,34) to D0 (20,115), suitable for the next focused diagnosis. If its demonstration becomes training data, retire that cohort from validation claims.

## Protocol and data

`configs/navigation_routes_v1.json` fixes three four-goal routes and three prepared starts before baseline execution and training. Each goal has a 256-action budget and the existing Manhattan tolerance of eight pixels. The sword controller is fixed. Waypoints advance within one continuous episode without resetting state, health, enemies, or time. Goals come from observed development endpoints; their presence does not prove every ordered connection feasible.

Correction collection replays each baseline fingerprint, then searches from actual handoffs and damage-free stalled endpoints. Successful earlier legs form the physical prefix of subsequent legs. The bounded teacher uses the parent policy plus deterministic greedy/detour attempts, rejecting paths on any health loss. Every accepted path is replayed to check all model inputs, goal arrival, and final fingerprint. Shortest successful handoff continuations extend collection routes.

Collection produced 69 verified paths, 3,671 action examples, and complete repaired prefixes for six starts. None of the three room_loop third-goal searches succeeded within the collection budget. This is a search limitation, not evidence that the goal is unreachable. Unresolved routes remain in the evaluation.

Training selects shortest observed remaining continuations for identical masked model inputs, with deterministic tie handling and per-label path/row/hash provenance. It yields 2,802 unique states and 136 states with conflicting observed actions; no optimal-path claim is made. One candidate starts from selected v4 and trains for eight epochs at learning rate 1e-5, retention KL weight eight, with the existing architecture, normalization, and previous-movement mask. Retention covers 346,536 original cache rows plus 6,206 prior verified demonstration rows, including the focused v4 correction. The fixed final epoch is evaluated without checkpoint shopping.

This is a privileged D-harness development experiment on known starts and goals, not a general planner or held-out game-completion benchmark. The reserved evaluation set remains unused. ROMs, emulator states, datasets, and weights remain ignored local artifacts.

## Verification and reproduction

All 48 unit tests pass, including ordered waypoint handling, budget boundaries, and death precedence. The original three continuous chains still succeed without damage in 49, 49, and 45 navigation actions. A route paused at action 470 after its first waypoint resumes with exactly the uninterrupted actions, fingerprint, progress counters, damage, and final status.

Use a new output directory to reproduce; artifact directories intentionally refuse overwrite:

```sh
.venv-ladx/bin/python scripts/navigation_route_experiment.py prepare --out runs/navigation-routes-reproduction
.venv-ladx/bin/python scripts/navigation_route_experiment.py collect --out runs/navigation-routes-reproduction
.venv-ladx/bin/python scripts/train_navigation_routes.py --out runs/navigation-routes-reproduction
.venv-ladx/bin/python scripts/navigation_route_experiment.py evaluate --out runs/navigation-routes-reproduction --checkpoint runs/navigation-routes-reproduction/model/epoch-008.pt --label candidate
```

The local run `runs/navigation-routes-v1` contains source snapshots, curriculum, baseline and candidate traces, collection manifests, training provenance, and all evaluation outputs. `reports/navigation-routes-v1.json` is the portable result; `configs/navigation_route_candidate.json` records the rejected candidate without changing selection. `scripts/report_navigation_routes.py` checks route and panel comparisons, original chains, and pause/resume outputs before producing the report.

The next experiment should diagnose the fresh-panel death and westbound handoff regressions, preserve the newly successful beach loops, and expand the unresolved room-loop teacher search before training another candidate.
