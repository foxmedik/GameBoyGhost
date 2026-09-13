# Tail Key — scripted physical baseline

Subsequent milestone: [Tail Cave unlocked and entered](PROGRESSION_TAIL_CAVE_ENTRY.md).

The house-start run `runs/progression-tail-key-v2` physically obtains the Tail Key after the verified Tarin cure. This is a scripted teacher baseline using supplied route knowledge and read-only game observations; no new AI-model learning occurred.

| Result | Value |
| --- | --- |
| Total decisions / frames | 4,404 / 30,229 |
| Extension decisions / frames after Tarin | 102 / 1,824 |
| Total damage / healing | 20 / 0 raw units |
| Additional damage after Tarin | 0 |
| Final health / powder | 4 / 24 |
| Tail Key possession | DB11 changed from 0 to 1 |
| Final room / position | Overworld 41, (72,74) |
| Chest | A0 closed → A1 open at cell (4,3) |
| Dialogue | Closed after pickup and 240 additional settling frames |

The supplied house state is the only initial state load. All prefix and extension actions use physical inputs; no inventory assignments, intermediate state loads, human rescue, optimizer updates or reserved evaluation use occurred. Tail Cave remains locked and unentered, so the overall quest success field stays false.

## Route and bounded interaction

The matched disassembly identifies room 41's chest as `CHEST_TAIL_KEY` (`src/data/chests/overworld.asm`) and places it at cell (4,3) (`src/data/rooms/overworld_a.asm`). The script travels north from Tarin's room 51, verifies the actual room transition and the closed chest, then approaches from below.

V1 safely stopped because the southern chest stance was blocked by a bush. V2 approaches cell (4,5), physically equips the sword, and checks that bounded sword inputs change the blocking object from 5C to ordinary floor 04. It then approaches the chest, faces up, and uses bounded A pulses and dialogue handling. The game journal records possession, and the script independently checks the chest is open. Both development runs are retained.

## Reproduction

Use the verified local ROM and prefix artifacts with a new output directory:

```sh
.venv-ladx/bin/python scripts/run_toadstool_progression.py \
  --stage tail-key --out runs/tail-key-new
```

The runner reconstructs the entire `progression-tarin-v3` prefix from the house, checking every fingerprint. It records the extension and independently replays the full trace in a fresh environment, comparing fingerprints, snapshots, frames and journals. The extension remains capped at 2,048 decisions; house caps remain 12,288 decisions and 300,000 frames.

Portable reports are `reports/progression-tail-key-v1.json` and `reports/progression-tail-key-v2.json`; aggregate validation is recorded in `reports/progression-tail-key-summary-v1.json`. Complete traces, manifests, final images and states remain in their ignored run directories.

Validation: both runs replay exactly and all manifest hashes verify. V2 source hashes match the current implementation. All 114 tests pass with no skips (36.828 seconds); selected model weights remain unchanged.

## Next

Physically reach the Tail Cave keyhole, unlock it, and enter alive with a settled transition. Preserve the four-unit health state and explicit damage/healing accounting. Reliability testing and learned-policy capability remain unverified.
