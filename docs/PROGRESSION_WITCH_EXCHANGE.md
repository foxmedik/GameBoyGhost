# Physical witch exchange verified

> Subsequent scripted milestone: [Tarin cure verified](PROGRESSION_TARIN_CURE.md). Tail Key acquisition is now next.

`runs/progression-witch-exchange-v12` completes house → sword → toadstool → cave return → witch exchange alive, with the receipt dialogue closed. The independent action replay matches every command fingerprint, game-state snapshot, frame count and journal event.

| Result | Value |
| --- | --- |
| Physical decisions | 3,696 |
| Emulator frames | 23,053 |
| Total health loss / healing | 16 / 0 raw units |
| Final health | 8 raw units |
| Mushroom | Consumed, DB4B = 0 |
| Powder | 32, with item 0C physically equipped |
| Final location | Indoor map 0E, room A2, at (72,86) |
| Receipt dialogue | Closed |
| Independent action replay | Exact |
| Optimizer updates / runtime human interventions | 0 / 0 |

This remains a scripted teacher baseline with supplied route knowledge and read-only ROM senses. It is not a newly learned quest policy or a full-game completion result. The selected learned policy hashes are unchanged. The complete house prefix is physically replayed; no intermediate state loads or inventory writes occur in the episode.

## Changes that enabled the interaction

The local navigator now aligns across a corridor before entering the adjacent path cell, allowing a four-pixel lateral tolerance rather than insisting on exact centering after displacement. Observed dialogue can be dismissed through bounded physical A pulses with movement released. The controller recognizes both stationary stalls and repeated pushback in a small area, allowing up to three short move-and-sword responses within a local approach. Travel otherwise retains the equipped shield.

The route reaches the witch via rooms 62 → 52 → 42 → 43 → 44 → 54 → 64 → 65, then verifies the actual hut transition to 0E:A2. It physically equips the mushroom on A, stands below the witch, faces up, and uses A. The journal observes mushroom consumption and powder availability. The final receipt dialogue is advanced and gameplay is settled before success is accepted.

The earlier route investigation described this hut as a rejected side-scrolling branch. The new physical run and matched `IndoorsBA2Entities` / `MAP_SHOP` source establish that this is the witch's hut; use the current verified evidence rather than that historical interpretation.

## Retained development outcomes

All attempts v3–v12 are retained and independently replay exactly, including failures. The compact ledger is `reports/progression-witch-exchange-summary-v1.json`.

- V3–v5 exposed entrance pinning, displacement/corner handling and an insufficient short approach budget; v5 reached room 43 alive.
- V6's broad nearby-enemy attack rule caused a death before room 42 and was rejected. It is absent from the current implementation.
- V7–v9 tested bounded stall responses and alignment; they did not complete the approach.
- V10 reached the hut and physically equipped the mushroom, but targeted a position inside the witch's collision area.
- V11 completed the actual exchange, while the receipt dialogue remained open.
- V12 completed the exchange and returned to settled gameplay with the dialogue closed.

The final approach budget was frozen at 2,048 new decisions, with 256-iteration local approaches and bounded dialogue/combat responses. The initial 512-decision extension limit was increased after traces showed continued physical progress; the overall 12,288-decision / 300,000-frame house-run limits were preserved. These are development attempts under changing implementations, not repeated trials establishing reliability. No reserved evaluation or new training was used.

## Reproduce

With the existing local artifacts and verified ROM, choose a fresh output directory:

```sh
.venv-ladx/bin/python scripts/run_toadstool_progression.py \
  --stage witch-exchange --out runs/witch-exchange-new
```

The runner verifies and replays `progression-witch-approach-v4` from its house initial state, executes the extension, records failures as well as success, and independently replays the resulting actions. It stores hashes, the journal, skill evidence, snapshots and a result manifest. Historical run directories must not be overwritten.

All 114 repository tests pass with no skips using the pinned optional data dependencies. New tests cover corridor alignment after displacement and the finite dialogue-dismissal budget; the live run verifies the full exchange. The suite log is `runs/progression-witch-validation-20260911/tests.log`.

## Next milestone

Return from the hut with powder, physically cure Tarin, then acquire the Tail Key and unlock/enter Tail Cave. Those events have not yet been demonstrated. The verified prefix finishes with eight raw health units, so preserve explicit health accounting in the return attempt. No additional human recordings or optimizer work is required by this result.
