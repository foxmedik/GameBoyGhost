# Room 0x15 architectural decision

Decision: NO-GO on further training of the current flat action-imitation recovery branch. The bounded encounter-takeover experiment has now been stopped without qualification after a harness failure. The agreed fallback is the qualified deterministic teacher from room entry. No replacement takeover panel or paired integration panel will run.

Execution record: `runs/room15-takeover-local-v1/summary.json`. Three completed primary rollouts cleared the room, but their replay checks failed because the new verifier compared JSON-normalized state with unnormalized in-memory snapshot tuples. These are not qualified results and do not establish a controller failure. The process was stopped; any unfinished case is excluded. Preflight tests passed but missed this serialization path. The planned four actual half-heart takeover cases were never evaluated. The following option specifications are preserved as the original precommitment, not a queue of future research.

Fallback execution: the existing teacher and existing exact-replay harness were reused unchanged on five new room-entry timings, including four actual half-heart starts. Result: **4/5 clears, 3/4 half-heart zero-damage clears, 5/5 exact replays; supplemental gate failed**. The base13/idle313 death is a deterministic progression blocker, not a reason to reopen the learned-recovery branch. The successful full-health case is preserved as a continuous house-to-room15-clear continuation in `runs/room15-entry-fallback-check/continuation.json`. No reliability or autonomous gate was lowered, and no new learned controller was selected.

## Evidence audited

- V1 through V4 development panels report 13/20, 7/20, 14/20, and 15/20 autonomous clears. Their timing panels differ; this is historical evidence, not a controlled learning curve. V4 misses the unchanged 18/20 overall and 4/4 actual half-heart selection criteria.
- V5's 6/8 and elapsed-context 5/8 are diagnostic results on the same eight source episodes used for training. Neither evaluator independently replays its output or implements the promised 48-decision post-escape contract. They are not valid standalone promotion gates.
- The two first-trigger cases named `halfheart` have eight raw health units. The project's teacher and autonomous gates classify half-heart as four raw health units. The eight-case first-trigger collection has no actual half-heart cases. Earlier reports claiming 2/2 half-heart recovery are incorrect.
- The first-trigger teacher cleared 8/8 with exact replay. Terminal-state teacher recovery cleared 2/5. These are different, selected state sets; they support testing early encounter takeover but do not establish a controlled causal effect or terminal-state impossibility.
- The guided batch cleared 43/78. Among 54 episodes with a trigger, 29 eventually cleared, 22 timed out, and three died. These are episode outcomes, not measured local escape rates for 254 recovery activations. Four deaths occurred across the whole batch. There is no same-start unassisted baseline establishing the intervention helped.
- The deterministic teacher's separate reliability gate passed 43/43 exact clears, including 10/10 actual half-heart cases without damage. Source hashes in that gate still match the checked local code. This qualification covers its tested room-entry distribution, not every arbitrary student failure state.
- The current learned representation contains coordinates, health, entity state/velocity, and six action/displacement pairs. It does not encode collision topology, dialogue state, or explicit shield/combat phase. Its action vocabulary also lacks rightward movement. Adding an elapsed decision counter did not address these structural limitations.

Sources: `runs/room15-student-v4-gate-v2/summary.json`, `runs/room15-v5-recovery-skill-gate/summary.json`, `runs/room15-v5-recovery-skill-time-probe-v3/summary.json`, `runs/room15-v5-first-trigger-teacher-spans/summary.json`, `runs/room15-v5-terminal-stall-spans/summary.json`, `runs/room15-v5-guided-30m/summary.json`, `runs/room15-teacher-gate-v2/summary.json`, their evaluator code, and the selected teacher configuration. Sealed validation specifications and results were not opened or modified for this review.

## Option A: Deterministic encounter takeover (recommended)

Hypothesis: recovery fails because control returns to an unreliable nominal policy before the encounter is resolved. A state-aware controller owning the entire remaining encounter can remove that handoff failure.

Evidence: the teacher has a qualified entry gate and 8/8 exact first-trigger clears, while the repeated left-shield primitive and learned escape probes do not meet their objectives.

Minimum implementation: wrap the existing qualified `clear_compass_room` implementation as a persistent skill. Keep V4 and the existing first-trigger condition fixed. Validate room identity, life, and active encounter state before takeover. Preserve the teacher's projectile shielding, Zol phases, bounded dialogue handling, and collision bypass. Allow one takeover per encounter and retain control until the living room-clear contract, or a precise blocker. Record every model/primitive action. Do not return on a displacement threshold.

Smallest falsification stage: replay the eight existing first-trigger development states plus four continuously reconstructed first-trigger states whose actual trigger health is four. Freeze all case identities and prefix hashes before controller execution; select cases by state/health coverage, not outcome. Do not write health memory or synthesize favorable resets. If four such states cannot be constructed within the experiment budget, qualification is incomplete and the branch stops.

Local pass: 12/12 living room clears, 12/12 independent exact replays, zero damage on all four actual half-heart cases, at most one takeover, and no execution-contract errors. Cap takeover at 512 controller decisions and 8,192 emulated frames including nested dialogue/animation commands; exceeding either cap is failure. These bounds are fixed safety/termination contracts, not tuning variables.

If local qualification passes, freeze 20 unused development timings across the established starts, including four actual half-heart room entries. Run unchanged V4 and the hybrid on identical continuously reconstructed starts. Hybrid operational pass: at least 18/20 living room clears, 4/4 half-heart clears, 20/20 exact replays, and no unplanned fallback. Preserve the existing 700-decision total room budget, counting nested primitive commands. Record deaths, damage, frame costs, and intervention share for both arms. The comparison diagnoses benefit; the absolute criteria determine adoption.

Classification: hybrid/guided. Passing this operational gate does NOT pass the learned-autonomous gate. That gate remains at least 18/20 autonomous clears, 4/4 half-heart clears, 20/20 exact replays, and no teacher/deterministic recovery fallback. No autonomy claim is earned by relabeling the primitive.

Maximum budget: four wall-clock hours total, at most 30 minutes of emulator execution, zero optimizer updates, one fixed controller version, 12 local cases plus 20 paired cases (52 primary rollouts), and independent replays. Smoke-test shape/dtype/action execution, case reconstruction, budgets, and replay failure detection before spending the panel. Any unmet criterion or budget expiry stops this branch; do not sweep thresholds, extend budgets, or replace failed cases.

## Option B: Geometry and interaction-state policy (deferred alternative)

Hypothesis: state aliasing and an incomplete action vocabulary prevent the learned controller from distinguishing solid geometry, pickup/dialogue lock, protected waiting, and an actionable enemy.

Evidence: y80/y83 clustering, omitted collision/dialogue/guard context, and missing rightward movement make the current coordinate-and-history representation incomplete. The current probes do not prove these omissions are the cause.

Minimum implementation: one shared training/inference encoder for local collision topology, reachable directions, dialogue/animation state, Link facing/guard state, and target/projectile relationships; a complete directional action vocabulary; and one standalone recovery candidate using existing provenance-preserved development sources. Audit the information and action availability before training. Do not add generic label volume.

Smallest falsification stage: the same 12-case challenge, with four actual half-heart states. The frozen teacher must first pass 12/12 exact living clears with zero damage on the four half-heart states before any new labels are generated. Freeze a separate episode-disjoint recovery test set before training; cases used as labels are training regressions, not held-out evidence.

Learned pass: all 12 development challenge cases and all eight episode-disjoint recovery test cases escape alive within 128 recovery decisions, leave the original blocked region, and survive a full 48-decision V4 continuation without a 12-decision stationary return within eight Manhattan pixels of the trigger. Room clear alive also qualifies. Require all exact replays and zero damage in actual half-heart recoveries. Then require the unchanged fresh 20-case autonomous gate (18/20, 4/4, 20/20, no fallback).

Maximum budget: one eight-hour work session, one encoder, one training candidate, at most 30 CPU-minutes training and 45 emulator-minutes including teacher qualification and replay. Failure of teacher qualification, either learned gate, or the budget stops the branch. This is an alternative for a later research allocation, not the next experiment after Option A fails.

## Stop and fallback

Run Option A only as the final bounded attempt to preserve model control before recovery. If it fails any precommitted gate or its resource cap, abandon mid-room recovery research for this milestone. Use the hash-verified selected deterministic teacher from its qualified room-entry boundary, replay-check the integrated handoff, and move development effort to the next Tail Cave room. A failure at that boundary is a deterministic progression blocker to repair, not a reason to restart the learning loop.

No new training labels are required for Option A. No unqualified teacher may generate imitation labels. Sealed validation stays untouched. Existing raw artifacts remain preserved; the corrections above supersede earlier narrative claims without rewriting experimental results.
