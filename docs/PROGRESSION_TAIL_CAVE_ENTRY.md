# Tail Cave entered — complete scripted quest proof

`runs/progression-tail-cave-v12` completes the continuous supplied-house → sword → mushroom → witch/powder → Tarin cure → Tail Key → Tail Cave unlock → settled entrance sequence alive. This is a **scripted teacher baseline**, not a newly learned AI-model accomplishment. The independent full action replay matches exactly.

| Result | Value |
| --- | --- |
| Total decisions / emulator frames | 5,192 / 33,991 |
| Extension after Tail Key | 788 decisions / 3,762 frames |
| Total damage / healing | 20 / 16 raw units |
| Additional damage after Tail Key | 0 |
| Final health / powder | 20 / 24 |
| Tail Cave exterior status | D8D3 = 90 hex, including opened bit 10 hex |
| Final room | Indoor A, map 00, room 17 |
| Final position | (80,124) |
| Entry | Alive, settled gameplay, dialogue closed |
| Full quest success | True |
| Independent action/state/frame/journal replay | Exact |
| New optimizer updates / human interventions | 0 / 0 |

The supplied house state already includes a shield; this is not a power-on claim. No intermediate state loads, game-RAM assignments, inventory grants, runtime human rescue or reserved evaluation were used. Every prefix action is reconstructed physically and checked against its saved fingerprint.

## Route and interactions

The guided extension follows room order 41 → 51 → 61 → 60 → 70 → 80 → 90 → A0 → B0 → C0 → C1 → C2 → C3 → C2 → D2 → D3. The second C2 visit enters a different connected area through C3's lower western exit, physically checked at each transition. Non-corner exits avoid accidentally crossing the perpendicular boundary while centering. B0 uses a passage between its two children.

In room90 the script cuts the blocking bush using the equipped sword and verifies object5C becomes floor04. Health subsequently rises from4 to20 during physical movement. The journal records all16 raw healing units separately; it does not assign an unverified pickup cause. No additional damage occurs on the selected extension.

The matched disassembly places D3's keyhole at cell(6,5) and entrance at(6,1). The script approaches below the keyhole, moves upward until the game's opened bit changes, releases controls for600 animation frames, then enters through the doorway. The journal requires prior key acquisition and opening, living health, closed dialogue and a settled indoor entrance. The harness now accepts successful environment termination while retaining errors for death and budget termination; a regression test covers both outcomes.

## Retained development attempts

All12 attempts and their exact replays are preserved. V1 identifies an inaccessible southern exit in71; V2 accidentally crosses north while centering a corner. V3 and V4 die in70. V5's route through60 avoids that encounter and stops at the village bush. V6 and V7 find blocked southern village routes. V8 and V9 stall at children inB0. V10 reaches C2's upper component but cannot go south; V11 confirms C3's direct southern edge is also blocked. V12 returns into lower C2 and completes the quest. These are iterative development runs, not a frozen reliability panel.

## Reproduction and evidence

Use the verified local ROM and prefix artifacts with a new directory:

```sh
.venv-ladx/bin/python scripts/run_toadstool_progression.py \
  --stage tail-cave --out runs/tail-cave-new
```

The runner starts from the supplied house state, reconstructs the verified `progression-tail-key-v2` prefix, records the bounded extension, then independently replays the entire trace in a fresh environment. The extension cap remains2,048 decisions; the house caps remain12,288 decisions and300,000 frames.

Per-run reports are `reports/progression-tail-cave-v1.json` through `v12.json`. The aggregate ledger is `reports/progression-tail-cave-summary-v1.json`; complete trajectories, journals, source-hash plans, final images and manifests remain in their ignored run directories. Latest imported evidence memory is `runs/progression-tail-cave-v12/memory-generation-5.json`.

## What this establishes

The initial continuous quest proof is complete, including physical terminal-milestone fixtures and exact replay. A varied-start reliability panel, learned quest control and useful inherited-memory improvement remain unverified. The next research decision is to freeze the baseline and define those evaluations; further dungeon progression, recorder collection and optimizer work have not been started.

Validation: all12 run manifests and independent replays verify; the successful run’s source hashes match current code. All115 tests pass with no skips in36.727 seconds, including successful terminal-trace handling. An earlier suite run overlapped a source edit and correctly detected a checkpoint source mismatch; the frozen-source rerun passes. Selected model weights are unchanged.
