# First continuous house → Nightmare boss door proof

The guided physical route completed and exact-replayed on 2026-09-12. Link opens the Nightmare boss door and stops outside in room `0x0B`, `(80,26)`, at frame **53,700**, with **24/24 health**, sword A, Feather B, grounded, movement released, no dialogue, no door animation, and no pending healing or damage. Boss room `0x06` was never entered. Moldorm and the Cello remain out of scope.

The proof contains **15,896 commands**, executed continuously from the supplied house state, which already has the shield. Every command fingerprint, snapshot, event list and frame count matched an independent replay. No intermediate savestate was loaded. This is guided development, not autonomous completion or teacher qualification.

Proof: `runs/house-nightmare-door-proof-v1/continuation.json`. Endpoint: `endpoint-result.json` in that directory. Restore every ordered replay segment and hashed dependency named by the continuation. A screenshot or final state alone is insufficient.

## Development evidence and failures

The new route acquires the next Small Key at full health, recovers into room `0x08` at frame 48,163, obtains the Nightmare Key at frame 49,500, and reaches Rolling Bones at frame 51,097 with full health. The observed-spacing combat defeats Rolling Bones without damage. Its first clear detector returned as the shutters started opening; that settled-state subcriterion was rejected and the following bounded stage physically waited for the shutters to finish.

The complete history preserves: the room-`0x0E` approach stopped by a Spark; a receipt-escape budget failure and airborne recovery; room-`0x10` Stalfos contact; a separate inner-Spark contact; an east-door alignment budget failure and recovery; an initial miniboss entry budget failure during closing shutters; and the upper-trap synchronization failure caused by an unobserved cooldown. Failed candidates are not promoted by a later recovery. The successful route includes its own failed assumptions and physical recoveries; alternate failed branches remain separate artifacts.

`reports/house-door-resumed-development-v1/progress.json` lists completed attempts and replay results. Raw requests, observations, plans, hashes, source snapshots and trajectories remain in their named run directories. One initial process lost stdin before any new gameplay and is recorded separately.

The new source modules contain development controller implementations for the Nightmare Key return, Rolling Bones spacing and post-miniboss route. Follow-up code fixes for shutter settlement and east-door alignment are not retroactively the source of the original proof. The per-attempt source snapshots and hashes preserve that distinction.

## Qualification is not complete

`configs/house_boss_door_teacher_panel_v1.json` freezes **20 fresh house cases and 4 actual half-heart recovery cases**, their input schedules, 30,000-decision/150,000-frame/900-second per-case budgets, full-health endpoint and exact-replay requirements. Its SHA-256 is recorded in the adjacent `.sha256` file. No qualification cases have run.

The recovery prerequisite is actual health 4 with no pending health processing at the first Feather trap approach in the same continuous house episode. A case that does not reach that condition fails the prerequisite; a higher-health arrival cannot substitute. No health writes or midroute loads are allowed.

A reusable full-route teacher must still be assembled and bound by source/config/model hashes before this panel executes. In particular, the historical manual item progression between room-`0x15` and Feather is preserved replay evidence, not a qualified controller. Do not replay a recorded prefix and call it varied-start teacher qualification. Current traces remain ineligible for learner labels.

## Verification and restoration limits

173 regression tests passed with no failures, errors or skips. `test_progression_longrun.py` was excluded because it regenerates sealed definitions. Existing isolated optimizer/resume software fixtures ran; no route learner campaign or labels were created. All 149 sealed artifacts still match the closeout hashes; their contents were not parsed or evaluated.

For endpoint-specific verification from the repository root:

```sh
.venv-ladx/bin/python scripts/verify_house_boss_door_proof.py --output runs/unused-house-door-proof-verification.json
```

The first additional verifier run matched all commands but rejected the final Python tuple/JSON list representation. Its failure report is preserved; the verifier now normalizes the final snapshot exactly as it does each command snapshot. Gameplay checks and fingerprints were not weakened.

**wipe_ready=false.** Teacher qualification, a pinned externally backed-up release, complete private artifact backup, and clean uv reconstruction are outstanding. No qualified release or training-data release has been published. **The Mac has not been erased.**
