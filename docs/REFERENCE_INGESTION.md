# Reference ingestion

Run `scripts/prepare_reference_ingestion.py` after placing the local Player's
Guide and speedrun in the paths described by [reference assets](REFERENCE_ASSETS.md).
It creates an ignored `runs/reference-ingestion-v1/` directory with:

- page-image metadata, OCR text, OCR search chunks, and guide contact sheets;
- a 3-second timestamped speedrun-frame index and contact sheets.

These outputs support human route annotation. They are not training examples:
the guide OCR is not page-aligned, and the speedrun does not contain verified
controller inputs. To create trainable examples, reproduce selected annotated
segments in the emulator and record observations, physical inputs, and verified
outcomes together.
