# Western crossing resolved

Live terrain showed the proposed E1→D1 northward crossing was invalid: all ten objects in E1's top row were object 3A, mapped to solid physics flag 01. Independent physical north probes at x=10 and x=28 stopped at y=26 with zero additional damage. A west press crossed into E0. This is evidence about this observed room state, not a universal rule inferred from a single failed movement.

The alternative is E1→E0, align near x=27, then north to D0. A diagnostic from the depleted failed arrival died on its first hit; that failure is retained. A separate pair reconstructed the exact earlier full-health arrival at decision 736. With movement alone it lost two raw units after 12 actions and stopped. Holding the already-equipped shield completed the corridor in 20 actions with zero damage. Both branches independently replayed exactly. This one comparison supports a tactical choice for this passage, not a broad combat claim.

The first integration of a scripted shielded lane skill was too broad: applied from upper E2, it ran into terrain and stopped with eight raw units lost. The corrected integration preserves the previously successful learned approach through E1, then uses the physical shielded lane skill only for the verified corridor. No model weights changed.

## Fresh continuous verification

`runs/progression-attempt-v4` physically starts in the supplied house and completes:

- Sword acquisition: 412 actions.
- Shore goal: 49 actions; established approach: 30; cliff: 87.
- Learned western E1 approach: 154 actions, including one bounded recovery probe.
- Shielded E0 approach: 13 actions; crossing to D0: four.

Total: **749 decisions, 337 after sword acquisition, zero damage, final health 24 raw units in D0 at (26,124)**. Every action/fingerprint/frame and planner decision matched independent replay; planner JSON continuation matched. This is a successful navigation prefix, not Tail Key acquisition or Tail Cave entry.

The successful comparison uses the original memory snapshot to preserve the learned arrival behavior. Updated knowledge is separately merged in `runs/progression-crossing-resolution-v1/memory-generation-3.json`, with trace evidence from successful and failed diagnostics/attempts. No inherited-memory efficiency claim is made. Current guidance is `configs/progression_guidance_v4.json`.

## Implementation and evidence

The planner's optional `shielded_axis` skill requires an already-equipped shield, aligns a crossing lane and accepts only adjacent room transitions. It is explicitly scripted and restricted to tagged guidance goals; it is not a general obstacle planner. Goals can specify a tighter completion tolerance for narrow crossing lanes. Existing learned navigation remains the default.

Diagnostics: `scripts/probe_progression_crossing.py`, `scripts/verify_western_passage.py`, and `scripts/verify_western_passage_early.py --shield`. The pre-CLI early diagnostic source is preserved under its run directory. Results and frozen diagnostic plans are in the corresponding `runs/progression-*` directories. Main report: `reports/progression-crossing-resolution-v1.json`.

No optimizer updates or reserved evaluation occurred. Next map/verify the onward route from D0 toward the forest and toadstool, retaining this continuous prefix as development regression evidence. All later quest interactions and terminal milestone live fixtures remain pending.

Regression: 94/94 tests passed in 37.897 seconds, including three new shielded-lane boundary tests.
