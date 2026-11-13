from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

from .config import load_sources
from .model import RETRIEVAL_METHODS, USAGE_CLASSES
from .store import BANNED_EXT

SYNC_GOVERNANCE_FIELDS = (
    "license", "usage_class", "license_evidence_url", "usage_notes",
    "retrieved_via", "snapshot_at", "snapshot_url"
)

REQUIRED = {
    "source_id", "kind", "url", "canonical_url", "title", "retrieved_at",
    "license", "usage_class", "license_evidence_url", "usage_notes",
    "retrieved_via", "snapshot_at", "revision", "http_status", "content_type",
    "sha256", "normalized_path", "duplicate_of", "parser_version",
}

BANNED_DOMAINS = ("discord.com", "discord.gg", "spotify.com", "music.apple.com",
                  "open.spotify.com", "podcasts.apple.com")


def check(store, repo_root: Path, sources_path: Path | None = None) -> list[str]:
    errors: list[str] = []
    seen_canonical: dict[tuple, str] = {}
    repo_root = repo_root.resolve()
    sources_file = sources_path or (repo_root / "tools" / "corpus" / "sources.toml")
    expected_titles: dict[str, str] = {}
    if sources_file.exists():
        try:
            sources_list = load_sources(sources_file)
            expected_titles = {
                s.id: s.get("expect_title_contains")
                for s in sources_list
                if s.get("expect_title_contains")
            }
        except Exception as exc:
            errors.append(f"failed to load sources config {sources_file}: {exc}")

    for row in store.all_rows():
        sid = row.get("source_id", "?")
        url = row.get("url", "")
        for key in REQUIRED:
            if key not in row:
                errors.append(f"{sid}: missing field {key} ({url})")

        exp_title = expected_titles.get(sid)
        if exp_title:
            row_title = row.get("title") or ""
            if exp_title.lower() not in row_title.lower():
                errors.append(
                    f"{sid}: title {row_title!r} does not contain expected substring {exp_title!r}"
                )

        usage_class = row.get("usage_class")
        if usage_class is not None and usage_class not in USAGE_CLASSES:
            errors.append(f"{sid}: invalid usage_class {usage_class!r} ({url})")
        if usage_class is None:
            errors.append(f"{sid}: missing usage_class ({url})")
        if not (row.get("license_evidence_url") or "").strip():
            errors.append(f"{sid}: blank license_evidence_url ({url})")
        if not (row.get("usage_notes") or "").strip():
            errors.append(f"{sid}: blank usage_notes ({url})")
        if row.get("retrieved_via") not in RETRIEVAL_METHODS:
            errors.append(f"{sid}: invalid retrieved_via {row.get('retrieved_via')!r} ({url})")
        if row.get("retrieved_via") == "wayback" and not row.get("snapshot_at"):
            errors.append(f"{sid}: wayback row lacks snapshot_at ({url})")

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
        else:
            norm_text = norm.read_text(errors="replace")
            if not norm_text.startswith("---"):
                errors.append(f"{sid}: normalized file missing front matter: {norm.name}")
            else:
                parts = norm_text.split("---", 2)
                if len(parts) < 3:
                    errors.append(f"{sid}: malformed front matter in {norm.name}")
                else:
                    try:
                        fm = yaml.safe_load(parts[1]) or {}
                    except Exception as exc:
                        errors.append(f"{sid}: invalid YAML front matter in {norm.name}: {exc}")
                        fm = {}
                    for f in SYNC_GOVERNANCE_FIELDS:
                        mf_val = row.get(f)
                        fm_val = fm.get(f)
                        if fm_val != mf_val:
                            errors.append(
                                f"{sid}: front matter mismatch in {norm.name} for {f}: "
                                f"manifest={mf_val!r} != front_matter={fm_val!r}"
                            )

        key = (row.get("canonical_url"), row.get("revision"))
        if key in seen_canonical and not row.get("duplicate_of"):
            errors.append(f"{sid}: duplicate canonical URL without duplicate_of: {key[0]}")
        seen_canonical.setdefault(key, row.get("sha256", ""))
    return errors
