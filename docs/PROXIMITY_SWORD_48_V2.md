# Terrain-aware sword teacher v2: frozen protocol

This experiment changes only the collection teacher's sword suppression. It does not train or select a learned controller. The selected navigator remains route v7. All 48 cases are known development cases; reserved evaluation remains untouched.

## Source-grounded terrain model

Addresses below identify source comment annotations; actual revision-1 addresses are resolved by `azle-r1.sym`. The rebuilt `azle-r1.gbc` and runtime ROM have identical SHA-256 `6285ba6201f17bc8595c600ebc2477d52561f0aff29b11f7fc3343bacb2e230b`. The revision-1 sword tables are at 158E and 159A (one byte before the source annotations); the physics table remains at bank 8:4AD4.

The matching disassembly's `bank0.asm` at 158F–15A6 supplies ordinary swing offsets; 15D6–15F4 computes column `floor((x + offsetX - 8)/16)` and row `floor((y + offsetY - 16)/16)`, then indexes `D711 + row*16 + col`. The visible room is ten columns by eight rows. We reject out-of-room samples rather than treating padding as terrain. Tile screen origins are `(16*col, 16*row)` after those hardware-coordinate adjustments. Overworld world-grid coordinates are `(room_col*10+col, room_row*8+row)`; indoor layout is mapped separately by the baseline. No full-map assets enter this predicate.

At 1624–1635 the cutting handler recognizes outdoor IDs 0A (grass), 5C (bush), D3 (bush covering stairs), and indoor DD. The physics filter at 1606–1617 excludes flags >=90 and flag 01. ROM bank 8 at 4AD4 contains overworld physics; map group selects the subsequent 256-byte table, with the color-dungeon adjustment from 2A12–2A25. Physics is read through bank-indexed PyBoy memory without switching the emulated bank. Handler entry guards C1C4 / C16A / boots are retained. `UseSword` calls `func_157C` at 1553, turning to the held d-pad direction before cutting. The predicate therefore uses the proposed movement's facing. It tests the immediate ordinary-swing sample in the movement direction, not arbitrary nearby vegetation. No spin, beam, or future movement reach is claimed.

Baseline `get_room_object_int` reads eight 16-byte rows and drops six padding columns. `minimap_object` is remembered terrain centered on the world tile position; `minimap_info` currently populates seen-position, seen-map, and not-current-map channels, not cutting metadata. Current live room objects avoid stale history and require no new learner input.

## Damage diagnosis and hypotheses

Exact physical replays of both v1 damage increases are stored separately in `runs/proximity-sword-v2-diagnosis`, preserving v1. In case a45a26..., sand crab C6 approaches from Link's right while he faces left and remains at (36,42). RAM X speed F0 means -16/16 = -1 pixel/frame, matching ten-pixel movement per action in the trace. Cadence takes four raw health units; proximity takes eight across two encounters. Linear approach can start defense earlier but does not solve wrong-facing combat or a stuck movement rule.

In case ad8190..., proximity suppresses the step-1 sword press with no entities in the starting room. The action crosses into a room with urchins C5; damage begins at step 2, before the next proposed press. Cadence takes no damage. Predicting only existing entities cannot cover an unseen destination. Both experimental arms conservatively preserve proposed sword presses when moving toward an exit within a 24-pixel edge guard (left x<=24, right x>=136, up y<=40, down y>=120). This is explicitly teacher uncertainty handling, not a claim that a threat was observed. The guard may retain unnecessary swings at blocked boundaries.

Entity C240/C250 speeds are signed sixteenths of pixels/frame (`wram.asm` comments), independently observed in the crab replay. Motion prediction computes closest linear approach to a 32-pixel neighborhood over 20 frames: the current ten-ready-frame action plus the non-sword cadence interval before the next proposed press. It considers both stationary Link and nominal intended movement at one pixel/frame, an observed ordinary-motion approximation. Acceleration, direction changes, collision, and longer transition waits are not predicted.

## Frozen comparison

Three arms, 48 identical cases each: **144 rollouts**, each independently replayed to its complete final fingerprint. Each case also verifies its full starting fingerprint against v1 and the rerun cadence final fingerprint against historical cadence. All arms use `navigation_recovery.teacher` attempt 0, a 128-action budget, and the same eight-pixel Manhattan goal tolerance.

- Cadence: original alternating sword rule.
- Terrain: v1 near-threat rule plus reachable foliage and conservative exit handling.
- Terrain motion: identical to Terrain plus closest-approach prediction.

Thus motion is separately ablated. Terrain versus cadence jointly measures terrain/exit handling and suppression; it does not isolate foliage from the exit guard. Dialogue, other item inputs, and movement are preserved. Redundant proposed presses during sword states 1–4 are suppressed in experimental arms.

Before execution, freeze all cases, source snapshots/hashes, reference hashes, ROM/state hashes, navigation selection hash, and this protocol under the new `runs/proximity-sword-48-v2`. Keep ROMs and run artifacts local. Record full per-action structured states, allowed/suppressed reasons, terrain targets, frame timing, frame-level animation starts/health changes, successes, raw damage, deaths, actions, emulator frames, and exact replay fingerprints.

Adoption requires at least 25% fewer actual swings, no lost cadence successes, no per-case damage increases, and no new per-case deaths. Inspect every regression even if aggregate metrics improve. A failed arm is rejected, not used for training. Passing this teacher gate is not learned-policy promotion; verified data collection and a separately frozen preservation-supervised training candidate would follow.
