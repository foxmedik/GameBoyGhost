# GameBoyGhost demonstration app

Build the Apple-silicon app on the Studio:

```sh
./.venv-ladx/bin/python -m pip install pyinstaller
./.venv-ladx/bin/python scripts/build_human_demo_app.py
```

Copy `dist/GameBoyGhost Demo Recorder.app` to the other Mac and open it. It
contains the local ROM and house state required for the demonstration; do not
distribute it outside your own machines.

Click **Start Run** to load the house state. The window displays Link's live
screen, a feature-free 16×16 room grid with the current room panel highlighted,
and map/room, Link-pixel, and Link-cell coordinates. Every frame is recorded.
`input_segments.jsonl` records each controller hold with its exact start frame,
end frame, and length.

The Start/End flow is deliberately gated: **End Run** unlocks only after the
game's Toadstool latch is set. It writes a manifest, all image/action/tag data,
and sends a compressed run archive to the Studio over SSH/rsync.

The delivery defaults are `studio@192.168.50.27` and
`/Users/studio/Developer/GameBoyAgent/runs/human-demos/incoming`. Use
**Delivery settings** once on the recording Mac if either value differs. The
recording Mac needs an SSH key authorized for that Studio account; the app uses
noninteractive SSH and reports a failed transfer while keeping the local run.

Tag buttons add timestamped annotations for combat, shield use, spin slashes,
terrain cutting, items, recovery, dialogue, and landmarks.
