from __future__ import annotations

import json
from pathlib import Path

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


def apply_audit(store, sources) -> tuple[int, list[str]]:
    """Apply source-level license findings to every manifest row.

    Returns (rows_changed, warnings).  Only sources with a non-unknown
    ``usage_class`` in sources.toml are applied.  Existing rows are never
    rewritten with a weaker class by this function; it is a straight copy of
    the audited source metadata.
    """
    config = {}
    warnings: list[str] = []
    for src in sources:
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

    changed = 0
    for path in sorted((store.root / "manifests").glob("*.jsonl")):
        rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
        dirty = False
        for row in rows:
            meta = config.get(row.get("source_id"))
            if not meta:
                continue
            row_dirty = False
            for key, value in meta.items():
                if value is None:
                    continue
                if row.get(key) != value:
                    row[key] = value
                    row_dirty = True
            if row_dirty:
                changed += 1
                dirty = True
        if dirty:
            _rewrite(path, rows)
    store._rows.clear()
    store._simhashes.clear()
    return changed, warnings
