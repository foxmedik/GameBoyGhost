# Human demonstration recorder

Run this from the project root with the Bluetooth controller already connected:

```sh
./.venv-ladx/bin/python scripts/record_human_demo.py
```

It opens PyBoy's native 4× Game Boy window from the house save state at
`runs/navigation-chain-house-v1/initial.state`. Controller input is captured
through PyBoy's SDL integration: D-pad moves Link; controller `B` is Game Boy
`A`, controller `A` is Game Boy `B`, Back is Select, and Start is Start.
Keyboard fallback is arrows, `A`, `S`, Return, and Backspace. This deliberately
uses the same SDL runtime as PyBoy, avoiding the duplicate-framework warning
that can occur when pygame and PyBoy run together on macOS.

Press `R` to reload the house state and begin another attempt in the same
session. Press Escape or close the window to finish. The recorder never grants
items or writes gameplay RAM.

While playing, use the number keys to add a timestamped label:

| Key | Label |
| --- | --- |
| 1 | combat |
| 2 | shield |
| 3 | spin slash |
| 4 | cut terrain |
| 5 | item use |
| 6 | recovery |
| 7 | NPC or dialogue |
| 8 | route landmark |

Each session is written to a new ignored directory beneath `runs/human-demos/`.
It contains a 160×144 PNG for every emulated frame, `actions.jsonl` with the
exact buttons held and read-only game state for each frame, `tags.jsonl`, and a
manifest with ROM/state hashes. This makes combat examples usable for training:
the frame, human action, health change, inventory change, room, and manual tag
can all be aligned exactly.

Use a custom starting state or output folder when needed:

```sh
./.venv-ladx/bin/python scripts/record_human_demo.py \
  --state runs/navigation-chain-house-v1/initial.state \
  --out runs/human-demos/sword-beach-01
```
