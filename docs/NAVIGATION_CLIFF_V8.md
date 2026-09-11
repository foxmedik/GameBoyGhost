# Cliff detour demonstration and route v8

A complete damage-free room loop is now physically demonstrated from all three starts, including both the approach above the cliff and the return below it. The first trained candidate does not reproduce the cliff detour and fails promotion. Selected route v7 remains unchanged.

## Demonstration search

The initial probe compares four bounded teacher detours. Only the western-neighbor approach finds safe paths: two from house, two from beach, and one from approach. They take 199/206, 206/199, and 146 actions respectively, within the unchanged 256-action goal budget. The path leaves E2's lower area through E1, uses a narrow passage near x=126 to reach the upper area, then re-enters E2 above the cliff. The policy training inputs always encode the original goal, not the teacher's intermediate waypoints.

The first return search (64 attempts per approach, 128 actions per attempt) finds no successes. Two subsequent full-budget waypoint searches also fail. Their failure states and the successful approach traces locate the narrow passage and reveal poorly placed intermediate waypoints. The third full-budget return search uses the western passage with a tighter three-pixel teacher-waypoint tolerance. It produces three safe returns for each of the five approaches: 15 verified return paths. The evaluated final-goal tolerance remains eight pixels.

Every accepted action sequence is replayed to check its encoded model inputs, final goal, and exact emulator fingerprint. Return prefixes equal the complete approach action prefixes, and return origin fingerprints equal approach final fingerprints. No reset or health restoration occurs between legs. Failed searches remain in local manifests. Intermediate waypoints assist collection only; the learned runtime has no new planner or hard-coded detour.

## Candidate result

Route v8 inherits v7's preservation examples and adds 20 cliff paths. The combined set contains 222 verified paths, 9,326 actions, 7,017 distinct masked-input states, and 148 conflicting states. One fixed eight-epoch candidate trains at learning rate 1e-5 with the inherited margin and KL terms; retention covers 346,536 original rows and 12,979 demonstration rows.

It completes 4/9 routes versus selected v7's 6/9. All room-loop starts still time out at the third goal. All three beach loops and the beach-start westbound route succeed; house and approach westbound returns regress to timeouts after three goals. All nine runs remain damage-free with no deaths. Local results are 46/48 original, 44/48 additional, and 46/48 fresh, with all earlier safe local successes preserved and zero damage/deaths. These gains do not override the two lost route successes.

All 50 tests pass. The original three continuous chains remain successful without damage, and exact post-waypoint pause/resume passes. The curriculum, budgets, fixed sword policy, model architecture, and feature contract remain unchanged. Cohorts remain retired under the existing registry; reserved evaluation is unused. These are development/training regression results, not held-out generalization or game completion.

## Video

`runs/videos/cliff-loop-demonstration/cliff-loop.mp4` records a verified house-start demonstration, beginning after sword acquisition. It contains 3,892 gameplay frames at 59.72750057 fps plus a two-second completion hold, approximately 67 seconds total. It is silent, uses nearest-neighbor scaling, and labels the current waypoint. The four goals complete at approximately 8.9, 13.9, 48.9, and 65.2 seconds.

The video is a teacher-demonstration replay, not an autonomous trained-policy success. The recording captures every emulator frame through the normal readiness/transition loop and verifies the final fingerprint and zero damage. Its manifest records provenance and the video hash. Full MP4 decoding passes.

Artifacts include `reports/navigation-routes-v8.json`, `scripts/collect_cliff_detour.py`, `scripts/collect_cliff_returns.py`, `scripts/navigation_cliff_training_v8.py`, `scripts/finalize_cliff_returns.py`, and `scripts/record_cliff_loop.py`. Source snapshots and all failed/successful searches are retained under ignored run directories. ROMs and emulator runtime artifacts remain excluded from Git. Recording requires the optional `imageio-ffmpeg` package.
