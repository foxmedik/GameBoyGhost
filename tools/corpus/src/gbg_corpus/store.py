from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from . import PARSER_VERSION
from .dedup import is_near_duplicate, simhash
from .model import Document, validate_usage_class
from .normalize import front_matter, slugify

BANNED_EXT = {
    ".gb", ".gbc", ".gba", ".rom", ".bin", ".iso", ".nes", ".sfc", ".smc",
    ".zip", ".7z", ".rar", ".tar", ".gz", ".pdf", ".mp3", ".wav", ".flac",
    ".ogg", ".m4a", ".mp4", ".mkv", ".avi", ".png", ".jpg", ".jpeg", ".gif",
    ".webp", ".exe", ".dll", ".so", ".dylib",
}

MAX_DOC_BYTES = 5 * 1024 * 1024  # 5 MB hard limit, never silently truncate.

# Magic bytes for content that must never be treated as text, even when the
# filename ends in .md.  This is deliberately a small, high-confidence list.
MAGIC_SIGNATURES: tuple[tuple[bytes, str], ...] = (
    (b"PK\x03\x04", "zip"),
    (b"PK\x05\x06", "zip"),
    (b"PK\x07\x08", "zip"),
    (b"7z\xbc\xaf\x27\x1c", "7z"),
    (b"Rar!\x1a\x07", "rar"),
    (b"\x1f\x8b", "gzip"),
    (b"%PDF-", "pdf"),
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"\xff\xd8\xff", "jpeg"),
    (b"GIF87a", "gif"),
    (b"GIF89a", "gif"),
    (b"RIFF", "riff-audio/image"),
    (b"ID3", "mp3"),
    (b"OggS", "ogg"),
    (b"fLaC", "flac"),
    (b"\x1aE\xdf\xa3", "matroska/webm"),
    (b"\x7fELF", "elf-binary"),
    (b"NES\x1a", "nes-rom"),
    (b"\x00asm", "wasm"),
)

# Game Boy / Game Boy Color cartridges carry the Nintendo logo at 0x0104.
_GB_LOGO = bytes.fromhex(
    "CEED6666CC0D000B03730083000C000D0008111F8889000EDCCC6EE6DD"
    "DDD999BBBB67636E0EECCCDDDC999FBBB9333E"
)


def sniff_binary(data: bytes) -> str | None:
    """Return a short kind when data is a known non-text/binary payload."""
    for prefix, kind in MAGIC_SIGNATURES:
        if data.startswith(prefix):
            return kind
    if len(data) >= 0x104 + len(_GB_LOGO) and data[0x104:0x104 + len(_GB_LOGO)] == _GB_LOGO:
        return "gameboy-rom"
    return None


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Store:
    def __init__(self, root: Path | None = None):
        self.root = Path(root or os.environ.get("GBG_CORPUS_DIR", "~/.local/share/gbg-corpus")).expanduser()
        for sub in ("raw", "normalized", "manifests", "raw/manual"):
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

        if len(doc.raw) > MAX_DOC_BYTES:
            self.record_failure(
                doc.source_id, doc.url,
                f"refused oversized document: {len(doc.raw)} bytes (max {MAX_DOC_BYTES})",
            )
            return None

        sniffed = sniff_binary(doc.raw)
        if sniffed:
            self.record_failure(
                doc.source_id, doc.url,
                f"refused binary content ({sniffed}) despite extension .{doc.ext.lstrip('.')}",
            )
            return None

        validate_usage_class(doc.usage_class)
        if doc.retrieved_via not in {"direct", "wayback", "manual"}:
            raise ValueError(f"invalid retrieved_via {doc.retrieved_via!r}")

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
            "usage_class": doc.usage_class,
            "license_evidence_url": doc.license_evidence_url,
            "usage_notes": doc.usage_notes,
            "retrieved_via": doc.retrieved_via,
            "snapshot_at": doc.snapshot_at,
            "snapshot_url": doc.snapshot_url,
            "retrieved_at": now_iso(), "revision": doc.revision,
            "heading_path": [doc.title],
        }
        norm_path.write_text(front_matter(fm) + doc.text.rstrip() + "\n")

        row = {
            "source_id": doc.source_id, "kind": doc.kind, "url": doc.url,
            "canonical_url": doc.canonical_url, "title": doc.title,
            "author": doc.author, "published_at": doc.published_at,
            "retrieved_at": now_iso(), "license": doc.license,
            "usage_class": doc.usage_class,
            "license_evidence_url": doc.license_evidence_url,
            "usage_notes": doc.usage_notes,
            "retrieved_via": doc.retrieved_via,
            "snapshot_at": doc.snapshot_at,
            "snapshot_url": doc.snapshot_url,
            "revision": doc.revision, "http_status": doc.http_status,
            "content_type": doc.content_type, "sha256": digest,
            "normalized_path": str(norm_path.relative_to(self.root)),
            "duplicate_of": duplicate_of, "parser_version": PARSER_VERSION,
            "simhash": str(shash), "raw_path": str(raw_path.relative_to(self.root)),
        }
        row.update(doc.extra)
        self._append(row)
        return row
