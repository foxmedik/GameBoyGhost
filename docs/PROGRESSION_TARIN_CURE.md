# Tarin cured — scripted physical baseline

Subsequent milestone: [Tail Key acquired](PROGRESSION_TAIL_KEY.md).

`runs/progression-tarin-v3` completes the continuous house → sword → mushroom → witch/powder → Tarin cure sequence alive. This is a **scripted baseline**, not an AI-model accomplishment or a training result. It uses physical controller inputs and read-only game-state observations.

| Result | Value |
| --- | --- |
| Decisions from the house | 4,302 |
| Emulator frames | 28,405 |
| Total damage / healing | 20 / 0 raw units |
| Final health | 4 raw units |
| Final powder | 24 |
| Tarin flag | DB48 = 1, observed changing from 0 |
| Final room | Overworld 51 |
| Dialogue | Closed, with 240 additional frames allowed after the cure |
| Independent physical action replay | Exact |
| Learned-model updates | None |

The full house-to-witch prefix matches its saved fingerprints. No intermediate state load, inventory assignment, runtime human rescue or reserved evaluation use occurred. The final state has no Tail Key; key acquisition and Tail Cave entry remain future milestones.

## Route and interaction

The script physically equips the sword for the return, exits the hut and traverses 65 → 64 → 54 → 44 → 43 → 42 → 52 → 62 → 61 → 51. The direct attempted westward path from the arrival region in 52 did not exist; that failed attempt is retained as `progression-tarin-v1`.

In room 51 the script approaches below Tarin, physically equips powder on A, faces upward, and uses bounded A pulses and waiting. The event journal observes the game's own Tarin flag changing from 0 to 1. The matched `05_tarin.asm` handler sets this flag when the raccoon becomes human. Dialogue is advanced using physical inputs; no flag or item count is assigned by the harness.

V2 established the cure with exact independent replay. V3 adds a final 240-frame settling interval and closed-dialogue check. The return adds one four-unit hit to the witch prefix; no healing occurred. The run is a single development proof, not a reliability or learned generalization claim.

## Reproduction and evidence

With the verified ROM and existing local prefix artifacts, use a fresh output directory:

```sh
.venv-ladx/bin/python scripts/run_toadstool_progression.py \
  --stage tarin --out runs/tarin-new
```

The runner starts from the house state and replays the verified `progression-witch-exchange-v12` commands before the Tarin extension. It retains the 2,048-decision extension cap and the 12,288-decision / 300,000-frame house-run limits. The independent second pass compares command fingerprints, snapshots, frame counts and event journals.

Per-run reports: `reports/progression-tarin-v1.json`, `reports/progression-tarin-v2.json`, and `reports/progression-tarin-v3.json`. Full action traces, manifests, final snapshots and journals remain in the corresponding ignored run directories. The aggregate validation ledger is `reports/progression-tarin-summary-v1.json`.

## Next

Continue the scripted baseline to the Tail Key chest, then the Tail Cave keyhole and settled entry. Preserve the current four-unit health state and record any physical healing or damage. The AI model has not learned these later quest stages; that distinction remains explicit in project status.

Validation: all three run manifests match their artifact hashes; 114 tests pass with no skips. The selected learned-policy hash is unchanged. After capture, only the runner module docstring and prefix-failure message were clarified; the saved plan preserves capture-time hashes.
