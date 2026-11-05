from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from . import PARSER_VERSION
from .dedup import is_near_duplicate, simhash
from .model import Document
from .normalize import front_matter, slugify

BANNED_EXT = {
    ".gb", ".gbc", ".gba", ".rom", ".bin", ".iso", ".nes", ".sfc", ".smc",
    ".zip", ".7z", ".rar", ".tar", ".gz", ".pdf", ".mp3", ".wav", ".flac",
    ".ogg", ".m4a", ".mp4", ".mkv", ".avi", ".png", ".jpg", ".jpeg", ".gif",
    ".webp", ".exe", ".dll", ".so", ".dylib",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Store:
    def __init__(self, root: Path | None = None):
        self.root = Path(root or os.environ.get("GBG_CORPUS_DIR", "~/.local/share/gbg-corpus")).expanduser()
        for sub in ("raw", "normalized", "manifests"):
            (self.root / sub).mkdir(parents=True, exist_ok=True)
        self.failures_path = self.root / "failures.jsonl"
        self._rows: dict[str, list[dict]] = {}
        self._simhashes: dict[str, int] = {}

    # ---------------------------------------------------------------- manifests
    def rows(self, source_id: str) -> list[dict]:
        if source_id not in self._rows:
            path = self.root / "manifests" / f"{source_id}.jsonl"
            rows = []
            if path.exists():
                rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
            self._rows[source_id] = rows
            for r in rows:
                if r.get("simhash"):
                    self._simhashes[r["sha256"]] = int(r["simhash"])
        return self._rows[source_id]

    def all_rows(self) -> list[dict]:
        out = []
        for path in sorted((self.root / "manifests").glob("*.jsonl")):
            out += [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
        return out

    def _append(self, row: dict):
        path = self.root / "manifests" / f"{row['source_id']}.jsonl"
        with path.open("a") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        self._rows.setdefault(row["source_id"], []).append(row)
        if row.get("simhash"):
            self._simhashes[row["sha256"]] = int(row["simhash"])

    # ---------------------------------------------------------------- failure log
    def record_failure(self, source_id: str, url: str, error: str, attempts: int = 1):
        with self.failures_path.open("a") as f:
            f.write(json.dumps({
                "source_id": source_id, "url": url, "error": error,
                "attempts": attempts, "retrieved_at": now_iso(),
            }) + "\n")

    # ---------------------------------------------------------------- save
    def save(self, doc: Document) -> dict | None:
        digest = sha256_bytes(doc.raw)
        existing = self.rows(doc.source_id)
        for r in existing:
            if r["sha256"] == digest and r.get("revision") == doc.revision:
                return None
            if r.get("canonical_url") == doc.canonical_url and r.get("revision") == doc.revision:
                return None

        ext = doc.ext.lstrip(".")
        if f".{ext.lower()}" in BANNED_EXT or ext.lower() in BANNED_EXT:
            self.record_failure(doc.source_id, doc.url, f"refused banned extension .{ext}")
            return None

        raw_path = self.root / "raw" / doc.source_id / f"{digest}.{ext}"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        if not raw_path.exists():
            raw_path.write_bytes(doc.raw)

        slug = slugify(doc.title or doc.url)
        norm_path = self.root / "normalized" / doc.source_id / f"{slug}.md"
        if norm_path.exists() and norm_path.read_text(errors="replace").find(digest) == -1:
            norm_path = self.root / "normalized" / doc.source_id / f"{slug}-{digest[:8]}.md"
        norm_path.parent.mkdir(parents=True, exist_ok=True)

        shash = simhash(doc.text)
        duplicate_of = None
        for other_sha, other_hash in self._simhashes.items():
            if other_sha != digest and is_near_duplicate(shash, other_hash):
                duplicate_of = other_sha
                break

        fm = {
            "source_id": doc.source_id, "url": doc.url, "canonical_url": doc.canonical_url,
            "title": doc.title, "license": doc.license, "sha256": digest,
            "retrieved_at": now_iso(), "revision": doc.revision,
            "heading_path": [doc.title],
        }
        norm_path.write_text(front_matter(fm) + doc.text.rstrip() + "\n")

        row = {
            "source_id": doc.source_id, "kind": doc.kind, "url": doc.url,
            "canonical_url": doc.canonical_url, "title": doc.title,
            "author": doc.author, "published_at": doc.published_at,
            "retrieved_at": now_iso(), "license": doc.license,
            "revision": doc.revision, "http_status": doc.http_status,
            "content_type": doc.content_type, "sha256": digest,
            "normalized_path": str(norm_path.relative_to(self.root)),
            "duplicate_of": duplicate_of, "parser_version": PARSER_VERSION,
            "simhash": str(shash), "raw_path": str(raw_path.relative_to(self.root)),
        }
        row.update(doc.extra)
        self._append(row)
        return row
