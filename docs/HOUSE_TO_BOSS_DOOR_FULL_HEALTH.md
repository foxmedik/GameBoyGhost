# House → opened boss door, full health and ready to fight

This is the active phase definition. The user strengthened the endpoint from arriving alive to **opening the boss door at full health, equipped for battle, and stopping outside the boss room**. The final boss and cello remain a separate phase. Version 1 protocols and all historical results remain evidence under their original definitions.

## Exact endpoint

Start at the supplied original house state. Finish in Tail Cave room `0x0B` after observing the boss door change from closed to open, with the animation finished. Health must equal **8 × current heart capacity** (currently 24/24), with both healing and damage buffers empty. Link must be grounded, playable, free of dialogue, with sword on A and Roc's Feather on B. Release all movement. Do not enter room `0x06`.

The software contract is `src/gameboy_agent/battle_ready_endpoint.py`; it wraps the preserved version-1 opening detector. Its tests do not substitute for a live opening proof. Arriving with half a heart is now a failed endpoint even if the door opens.

Physical healing along the route is allowed. The requirement is full health **at the finish**, not a flawless no-hit run throughout. Health cannot be written into RAM, restored through a mid-episode state load, or credited while its animation is still applying. A future checkpoint must document its actual capacity, equipment, and consumed resources.

## Route to establish and optimize

| Stage | Controller contract | Health/resource objective |
| --- | --- | --- |
| House through Tail Key and cave entry | Existing state-driven progression; verify each inventory/event transition | Preserve the known start and existing regression evidence |
| First keys, compass, map, Roc's Feather | Room-specific movement/combat and pickup contracts | Reach the physically verified refill and wait for 24/24 |
| Feather return to next key | Underground return; direct room-`0x04` jump; guarded room-`0x0D` encounter | Preserve full health rather than carry development mistakes into the teacher |
| Small Key and Nightmare Key | Control room-`0x0E` hazards, key-receipt exit, upper room-`0x0F` entry, staircase and chest | No unobserved landing assumption; key accounting exact |
| Rolling Bones and onward approach | Explicit safe attack/disengagement phases, then verified recovery if needed | End with full health; no assumed healing drop before physical verification |
| Antechamber and boss door | Final approach, physical loadout, full-health check, version-2 opening endpoint | Stop outside the boss room, ready for a separately scoped battle |

Optimization is ordered: **reliable full-health completion → no hidden intervention/exact replay → less damage and fewer recovery detours → fewer frames and decisions**. Faster failing routes are rejected. Once a teacher passes, compare route changes on paired development starts; report completion, final health, damage/healing, interventions, frames and decisions. Do not select on sealed validation.

Current concrete improvement: the new feather return reaches room `0x0E` with **24 health rather than 8**, and **578 fewer emulated frames** from the same full-health refill. This is a developmental comparison, not a reliability gate. The next room-`0x0E` guarded attempt timed out at its 600-decision limit without losing health; it is not a completed encounter. Details: `reports/full-health-route-development-v1.json`.

## Training setup

Teach complete sequences, preserving episode provenance and temporal state. The planned scope includes stage selection, transitions, movement/combat, equipping and health recovery. A candidate may use a learned stage selector with local policies, but its card must disclose any deterministic skills or teacher fallback. A recorded prefix cannot stand in for learned route planning.

Before any new training:

1. Finish one continuous house-to-full-health-open-door proof and independently replay it.
2. Freeze and pass the full-route teacher gate: 20/20 fresh house cases, plus 4/4 actual half-heart arrival challenges that recover and satisfy the full-health endpoint. All cases replay exactly. Historical room-15 gates stay unchanged; no reopening that research branch.
3. Collect separate approved demonstrations only after teacher qualification. Diagnostic and gate episodes remain excluded. Split by source episode/start family so related trajectories cannot cross train/held-out boundaries.
4. Freeze one learning experiment: observation/state schema, stage/action vocabulary, source hashes, dataset split, candidate count, optimizer/compute limits and evaluation case IDs.
5. Train and evaluate. The full-route model-only bar remains at least 18/20 plus 4/4 challenges, now with the full-health endpoint, all exact replays and zero teacher fallback. Guided/hybrid completion is a separate metric and claim.

Current status: route incomplete, teacher unqualified, dataset not approved, training not started. The existing 20 sealed validation cases and the other historical reserved evaluations remain untouched.

## GitHub and Hugging Face checkpoint

The checkpoint plan is `configs/house_boss_door_checkpoint_v1.json`. GitHub repository: `foxmedik/GameBoyGhost`. Existing Hugging Face dataset: `foxmedik/GameBoyGhost-LADX`. Use a separate `releases/house-boss-door-full-health-v1` namespace; preserve the old pinned dataset revision. A future model repository is not yet selected.

Two distinct publishable claims are possible:

- **Development snapshot:** source, active protocol, current result summaries, blocked readiness manifest and an honest card. No trained-route or full-health-door success claim.
- **Qualified route/training release:** a pinned source commit, full-health endpoint proof, teacher gate, approved sequence-data manifest and checksums, reproduction instructions, then frozen training configuration, actual model weights and evaluation evidence when those exist.

The currently modified working tree is not a pinned release commit. The existing `upload_hf_release.py` has an old collection-specific commit message and row assumptions; do not use it unchanged for this checkpoint. Publishing must use the new manifest/namespace, verify hashes against the returned remote revision, and record the actual Git commit. Model weights must not be implied by the presence of a dataset release.

Keep ROMs, emulator savestates, reference copies, secrets, and sealed evaluation specifications/trajectories out of the upload. Local save states may support later user gameplay, but reproducibility evidence remains continuous physical replay. No upload is performed merely by preparing the local snapshot.

## Session handoff

Prefer the new full-health development continuation in `configs/research_focus.json` for route optimization; retain the furthest Nightmare-Key/miniboss handoff separately. Finish the room-`0x0E` safety/pickup stage, then connect the qualified segments, clear Rolling Bones, verify recovery and the final approach, and prove the full-health door endpoint. Update actual progress and blockers before each checkpoint. Do not mark the route optimized, training ready, or release qualified until the relevant gate passes.
