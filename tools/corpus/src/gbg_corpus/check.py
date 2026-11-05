from __future__ import annotations

import hashlib
from pathlib import Path

from .store import BANNED_EXT

REQUIRED = {
    "source_id", "kind", "url", "canonical_url", "title", "retrieved_at",
    "license", "revision", "http_status", "content_type", "sha256",
    "normalized_path", "duplicate_of", "parser_version",
}

BANNED_DOMAINS = ("discord.com", "discord.gg", "spotify.com", "music.apple.com",
                  "open.spotify.com", "podcasts.apple.com")


def check(store, repo_root: Path) -> list[str]:
    errors: list[str] = []
    seen_canonical: dict[tuple, str] = {}
    repo_root = repo_root.resolve()

    for row in store.all_rows():
        sid = row.get("source_id", "?")
        url = row.get("url", "")
        for key in REQUIRED:
            if key not in row:
                errors.append(f"{sid}: missing field {key} ({url})")
        if row.get("duplicate_of") and row.get("duplicate_of") == row.get("sha256"):
            errors.append(f"{sid}: self-referential duplicate_of ({url})")
        for domain in BANNED_DOMAINS:
            if domain in (row.get("url") or "") or domain in (row.get("canonical_url") or ""):
                errors.append(f"{sid}: banned domain {domain} ({url})")

        raw = store.root / row.get("raw_path", "")
        norm = store.root / row.get("normalized_path", "")
        if not raw.exists():
            errors.append(f"{sid}: missing raw file {raw}")
        else:
            digest = hashlib.sha256(raw.read_bytes()).hexdigest()
            if digest != row.get("sha256"):
                errors.append(f"{sid}: sha256 mismatch for {raw.name}")
            if raw.suffix.lower() in BANNED_EXT:
                errors.append(f"{sid}: banned raw extension {raw.suffix}")
            try:
                raw.resolve().relative_to(repo_root)
                errors.append(f"{sid}: raw content is inside the git repo: {raw}")
            except ValueError:
                pass
        if not norm.exists():
            errors.append(f"{sid}: missing normalized file {norm}")

        key = (row.get("canonical_url"), row.get("revision"))
        if key in seen_canonical and not row.get("duplicate_of"):
            errors.append(f"{sid}: duplicate canonical URL without duplicate_of: {key[0]}")
        seen_canonical.setdefault(key, row.get("sha256", ""))
    return errors
