# Reference assets

Versioned artwork and text references live under `docs/reference/`:

- `gamefaqs-walkthrough.txt` is the local walkthrough used to locate route
  descriptions.
- `tilesets/` contains the supplied map, sprite, background, and tileset art.

Large local inputs are intentionally excluded from Git and live in
`assets/`. The current useful sources are the Nintendo Player's Guide page
images and OCR under `assets/guides/nintendo-players-guide/`, plus the
speedrun video under `assets/videos/speedruns/`.

Derived media and analyses belong in `runs/`. A source video or guide scan is
not a training example by itself: training records must include the emulator
observation, physical input, and observed outcome.
