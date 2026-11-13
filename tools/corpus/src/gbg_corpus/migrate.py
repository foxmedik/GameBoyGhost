from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath

import yaml

from .adapters import _glob_re
from .model import USAGE_CLASSES, validate_usage_class


def _rewrite(path: Path, rows: list[dict]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    tmp.replace(path)


def migrate_add_usage_class(store) -> int:
    """Add the governance fields to every manifest row.

    New rows get ``unknown`` and empty evidence/notes because the migration
    must not guess a license.  A later audit pass fills them from sources.toml.
    Idempotent: rows that already carry the fields are left untouched.
    """
    changed = 0
    for path in sorted((store.root / "manifests").glob("*.jsonl")):
        rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
        dirty = False
        for row in rows:
            if "usage_class" not in row:
                row["usage_class"] = "unknown"
                dirty = True
            if "license_evidence_url" not in row:
                row["license_evidence_url"] = ""
                dirty = True
            if "usage_notes" not in row:
                row["usage_notes"] = ""
                dirty = True
            if "retrieved_via" not in row:
                row["retrieved_via"] = "direct"
                dirty = True
            if "snapshot_at" not in row:
                row["snapshot_at"] = None
                dirty = True
            if "snapshot_url" not in row:
                row["snapshot_url"] = None
                dirty = True
            changed += int(dirty)
        if dirty:
            _rewrite(path, rows)
    store._rows.clear()
    store._simhashes.clear()
    return changed


SYNC_GOVERNANCE_FIELDS = (
    "license", "usage_class", "license_evidence_url", "usage_notes",
    "retrieved_via", "snapshot_at", "snapshot_url"
)


def sync_normalized_front_matter(store) -> tuple[int, dict[str, tuple[str, str]]]:
    """Sync front matter of normalized files with manifest rows.

    The body must be byte-identical before and after; prove it by hashing every
    body before and after.

    Returns (changed_count, body_hashes_map) where body_hashes_map is:
    {rel_path: (sha256_before, sha256_after)}
    """
    changed = 0
    body_hashes: dict[str, tuple[str, str]] = {}

    for row in store.all_rows():
        norm_rel = row.get("normalized_path")
        if not norm_rel:
            continue
        p = store.root / norm_rel
        if not p.exists():
            continue

        text = p.read_text(errors="replace")
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                fm = yaml.safe_load(parts[1]) or {}
                raw_body = parts[2]
            else:
                fm = {}
                raw_body = text
        else:
            fm = {}
            raw_body = text

        body_before = raw_body
        sha_before = hashlib.sha256(body_before.encode("utf-8")).hexdigest()

        dirty = False
        for f in SYNC_GOVERNANCE_FIELDS:
            target_val = row.get(f)
            if fm.get(f) != target_val:
                fm[f] = target_val
                dirty = True

        if dirty:
            new_fm = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True).strip()
            new_text = f"---\n{new_fm}\n---" + raw_body
            p.write_text(new_text)
            body_after = new_text.split("---", 2)[2] if new_text.startswith("---") else new_text
            sha_after = hashlib.sha256(body_after.encode("utf-8")).hexdigest()
            assert sha_before == sha_after, f"body bytes changed for {p}"
            changed += 1
        else:
            sha_after = sha_before

        body_hashes[norm_rel] = (sha_before, sha_after)

    return changed, body_hashes


def apply_audit(store, sources) -> tuple[int, list[str]]:
    """Apply license findings and per-path overrides from sources.toml to every manifest row.

    Returns (rows_changed, warnings). It is a straight copy of the audited source
    metadata from sources.toml (including class upgrades or downgrades), applying
    the first matching per-path override to rows by their 'path' field, otherwise
    the source-level values.
    """
    config = {}
    overrides_by_id: dict[str, list[dict]] = {}
    warnings: list[str] = []
    for src in sources:
        if src.get("enabled", True) is False:
            continue
        usage_class = src.get("usage_class")
        evidence = src.get("license_evidence_url", "")
        notes = src.get("usage_notes", "")
        if not usage_class:
            warnings.append(f"{src.id}: no usage_class in sources.toml")
            continue
        if usage_class not in USAGE_CLASSES:
            raise ValueError(f"{src.id}: invalid usage_class {usage_class!r}")
        if not evidence:
            warnings.append(f"{src.id}: no license_evidence_url")
        if not notes:
            warnings.append(f"{src.id}: no usage_notes")
        config[src.id] = {
            "usage_class": validate_usage_class(usage_class),
            "license": src.get("license"),
            "license_evidence_url": evidence,
            "usage_notes": notes,
        }
        ovs = src.get("overrides", [])
        validated_ovs = []
        for ov in ovs:
            ov_class = ov.get("usage_class")
            if not ov_class:
                raise ValueError(f"{src.id}: override missing usage_class")
            validated_ovs.append({
                "path_glob": ov.get("path_glob", ""),
                "usage_class": validate_usage_class(ov_class),
                "license": ov.get("license", src.get("license")),
                "license_evidence_url": ov.get("license_evidence_url", evidence),
                "usage_notes": ov.get("usage_notes", notes),
            })
        overrides_by_id[src.id] = validated_ovs

    changed = 0
    for path in sorted((store.root / "manifests").glob("*.jsonl")):
        rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
        dirty = False
        for row in rows:
            sid = row.get("source_id")
            meta = config.get(sid)
            if not meta:
                continue

            target_meta = meta
            row_path = row.get("path", "")
            if row_path and sid in overrides_by_id:
                for ov in overrides_by_id[sid]:
                    glob = ov["path_glob"]
                    if PurePosixPath(row_path).match(glob) or _glob_re(glob).match(row_path):
                        target_meta = ov
                        break

            row_dirty = False
            for key in ("usage_class", "license", "license_evidence_url", "usage_notes"):
                value = target_meta.get(key)
                if value is not None and row.get(key) != value:
                    row[key] = value
                    row_dirty = True
            if row_dirty:
                changed += 1
                dirty = True
        if dirty:
            _rewrite(path, rows)
    store._rows.clear()
    store._simhashes.clear()

    fm_changed, body_hashes = sync_normalized_front_matter(store)
    for path_str, (before, after) in body_hashes.items():
        if before != after:
            raise RuntimeError(f"body bytes changed for {path_str}")
    if fm_changed:
        print(f"front matter: {fm_changed} files updated")

    return changed, warnings
