#!/usr/bin/env python3
"""Print a compact integrity report for locally recorded human demonstrations."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


RUNS = Path.home() / "Library/Application Support/GameBoyGhost Demo Recorder" / "runs"


def line_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open() as handle:
        return sum(1 for _ in handle)


def tag_counts(path: Path) -> Counter:
    tags: Counter = Counter()
    if not path.exists():
        return tags
    for line in path.read_text().splitlines():
        try:
            tags[json.loads(line).get("tag", "unknown")] += 1
        except json.JSONDecodeError:
            tags["invalid"] += 1
    return tags


def inspect(session: Path) -> tuple[bool, str]:
    manifest = session / "manifest.json"
    actions = line_count(session / "actions.jsonl")
    segments = line_count(session / "input_segments.jsonl")
    frames = len(list((session / "frames").glob("*.png")))
    tags = tag_counts(session / "tags.jsonl")
    complete = manifest.exists() and actions > 0 and segments > 0 and frames > 0
    tag_text = ", ".join(f"{name}={count}" for name, count in sorted(tags.items())) or "none"
    return complete, f"frames={frames} actions={actions} segments={segments} tags[{tag_text}] manifest={'yes' if manifest.exists() else 'no'}"


def main() -> None:
    if not RUNS.exists():
        print(f"No recorder data directory: {RUNS}")
        return
    sessions = sorted(path for path in RUNS.iterdir() if path.is_dir())
    complete = 0
    print(f"Recorder data: {RUNS}")
    for session in sessions:
        valid, details = inspect(session)
        complete += valid
        print(f"{'READY' if valid else 'INCOMPLETE'}  {session.name}  {details}")
    archives = sorted(RUNS.glob("*.tar.gz"))
    print(f"Completed sessions: {complete}; local archives: {len(archives)}")


if __name__ == "__main__":
    main()
