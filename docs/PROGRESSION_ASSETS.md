# Provided artwork for Tail Key progression

Run `.venv-ladx/bin/python scripts/process_progression_assets.py` to rebuild `runs/progression-assets-v2/`. Open `index.html` for the room selector, forest/southern reference panel, complete labeled overworld map, tile atlas and preserved source artwork. The manifest is the machine-readable interface for future progression integration; no controller consumes it yet.

Processed 31 image assets, preserving original files, annotations and credits. The overworld grid yields 256 native 160×128 room images, 20,480 tile occurrences and 451 unique RGB 16×16 appearances. Each appearance has a pixel hash and all room/cell occurrences. Every source has a SHA-256 and image metadata. The irregular standalone tilesets, sprites and interior maps are normalized reference images, not falsely assigned ROM tile IDs.

The Koholint sheet uses origin (1,1), strides (161,129), 16 columns and 16 rows. All 34 separator lines were checked; the vertical separator at x=644 includes a second green color. Footer/alternate scenery is retained in the full source but excluded from room extraction. Room numbers follow the inferred row-major overworld convention. Visual inspection of 41 (forest chest), D3 (Tail Cave exterior) and E2 agrees with the expected areas; live alignment remains required.

`reports/progression-assets-v1.json` records exact source hash checks, all 256 crop comparisons and reconstruction of all 20,480 tile occurrences from the appearance catalog. This is extraction verification, not emulator validation.

## How this helps now

Use room images to inspect the required journey and identify candidate landmarks, ledges, doors and interaction locations. Use the indexed appearances as references when interpreting observed room terrain. Validate room identity, screen/player coordinate offsets, quest-state differences and physical transitions in the honest progression harness before deriving movement targets. Store observed directed transitions and blocked edges separately from the static artwork. Never promote visual similarity into a collision guarantee.

The first progression baseline must record `provided_full_map_and_artwork` assistance if these references influence its planning or skills. Static maps can show open/closed doors or other quest states unlike the live game, and include blank placeholders. Some references are monochrome GB imagery. All catalog semantics and passability are initially unknown; hashes identify appearance, not game object codes. The assets do not replace physical menu control, honest inventory handling or live milestone detectors.

No training, reserved evaluation, collision labeling or runtime integration was performed by asset processing. Next: implement the progression harness and compare its live observations with these references while establishing the first continuous quest attempt.
