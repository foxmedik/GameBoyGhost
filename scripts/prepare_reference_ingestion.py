"""Prepare local guide and speedrun references for human-assisted ingestion.

The output is deliberately a research index, not an imitation-learning dataset:
it contains no guessed controller inputs or inferred game-state labels.
"""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "assets/guides/nintendo-players-guide"
SPEEDRUN = ROOT / "assets/videos/speedruns/link-awakening-speedrun.mp4"
SPEEDRUN_SAMPLES = ROOT / "runs/speedrun-review-v2"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(path):
    return str(path.relative_to(ROOT))


def contact_sheets(entries, output, columns=10, rows=6, thumbnail=(160, 90)):
    output.mkdir(parents=True)
    per_sheet = columns * rows
    result = []
    for offset in range(0, len(entries), per_sheet):
        group = entries[offset:offset + per_sheet]
        sheet = Image.new("RGB", (columns * thumbnail[0], rows * thumbnail[1]), "black")
        draw = ImageDraw.Draw(sheet)
        for index, entry in enumerate(group):
            with Image.open(ROOT / entry["file"]) as image:
                image = image.convert("RGB")
                image.thumbnail(thumbnail)
                x = (index % columns) * thumbnail[0]
                y = (index // columns) * thumbnail[1]
                sheet.paste(image, (x, y))
                draw.text((x + 3, y + 3), str(entry["index"]), fill="white", stroke_width=1,
                          stroke_fill="black")
        target = output / f"sheet-{offset // per_sheet + 1:03}.jpg"
        sheet.save(target, quality=88)
        result.append(relative(target))
    return result


def guide_index(output):
    pages = sorted((GUIDE / "pages-300dpi").glob("*.jpg"))
    if not pages:
        raise FileNotFoundError("Player's Guide page images are missing")
    text_path = GUIDE / "ocr.txt"
    text = text_path.read_text(errors="replace")
    page_entries = []
    for number, page in enumerate(pages, 1):
        with Image.open(page) as image:
            page_entries.append(dict(index=number, file=relative(page), width=image.width, height=image.height))
    (output / "guide-pages.jsonl").write_text("".join(json.dumps(row) + "\n" for row in page_entries))
    (output / "guide-ocr.txt").write_text(text)
    chunks = []
    width = 1200
    for start in range(0, len(text), width):
        chunk = text[start:start + width]
        chunks.append(dict(index=len(chunks) + 1, start_character=start, text=chunk))
    (output / "guide-ocr-chunks.jsonl").write_text("".join(json.dumps(row) + "\n" for row in chunks))
    # OCR has no page delimiters, so it is intentionally not claimed to align
    # with page images. The sheets support manual page lookup and annotation.
    sheets = contact_sheets(page_entries, output / "guide-contact-sheets", columns=4, rows=4,
                            thumbnail=(200, 256))
    return dict(page_images=len(page_entries), ocr_characters=len(text), ocr_chunks=len(chunks),
                ocr_page_aligned=False, contact_sheets=sheets,
                sources=dict(ocr=relative(text_path), ocr_sha256=sha256(text_path),
                             page_directory=relative(GUIDE / "pages-300dpi")))


def speedrun_index(output):
    source = json.loads((SPEEDRUN_SAMPLES / "manifest.json").read_text())
    frames = []
    for number, item in enumerate(source["samples"], 1):
        frame = ROOT / item["file"]
        if not frame.exists():
            raise FileNotFoundError(f"Missing speedrun sample: {frame}")
        frames.append(dict(index=number, file=relative(frame), timestamp_seconds=item["timestamp_seconds"]))
    (output / "speedrun-frames.jsonl").write_text("".join(json.dumps(row) + "\n" for row in frames))
    sheets = contact_sheets(frames, output / "speedrun-contact-sheets")
    return dict(frames=len(frames), sampling_seconds=source["sampling_seconds"],
                contact_sheets=sheets, source_video=relative(SPEEDRUN),
                source_video_sha256=sha256(SPEEDRUN), source_fps=source["source_fps"],
                source_resolution=source["source_resolution"])


def main():
    parser = argparse.ArgumentParser(description="Build searchable local-reference ingestion indexes")
    parser.add_argument("--output", type=Path, default=ROOT / "runs/reference-ingestion-v1")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"Output already exists: {output}")
    output.mkdir(parents=True)
    manifest = dict(schema="reference-ingestion-v1", training_data=False,
                    inference_labels=False, guide=guide_index(output), speedrun=speedrun_index(output),
                    next_step="Annotate route milestones, then recreate them in the emulator with recorded inputs and outcomes.")
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(dict(guide_pages=manifest["guide"]["page_images"],
                          speedrun_frames=manifest["speedrun"]["frames"],
                          output=relative(output)), indent=2))


if __name__ == "__main__":
    main()
