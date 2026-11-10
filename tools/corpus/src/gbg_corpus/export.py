from __future__ import annotations

import hashlib
import json
import re
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .model import PUBLIC_BODY_CLASSES, RESTRICTED_CLASSES, USAGE_CLASSES
from .normalize import slugify

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LICENSE_DIR = PROJECT_ROOT / "licenses"


class ExportGuardError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_body(normalized_path: Path) -> str:
    text = normalized_path.read_text(errors="replace")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            return parts[2].lstrip("\n")
    return text


def _source_class(rows: list[dict], cfg) -> str:
    classes = [r.get("usage_class", "unknown") for r in rows]
    if cfg is not None:
        classes.append(cfg.get("usage_class", "unknown"))
    if not classes:
        return "unknown"
    # Least reusable class wins if a source ever contains mixed rows or the
    # config is more restrictive than a stale manifest row.
    return max(classes, key=lambda c: USAGE_CLASSES.index(c) if c in USAGE_CLASSES else len(USAGE_CLASSES))


def _license_notice(sid: str, meta: dict) -> str:
    local = LICENSE_DIR / f"{sid}.txt"
    if local.exists():
        return local.read_text(errors="replace").rstrip() + "\n"
    lines = [
        f"License: {meta.get('license', 'unknown')}",
        f"Usage class: {meta.get('usage_class', 'unknown')}",
        f"License evidence: {meta.get('license_evidence_url', '')}",
        f"Terms: {meta.get('terms_url', '')}",
        "",
        "This notice travels with the exported text so attribution and reuse",
        "terms remain visible. See the evidence URL for the authoritative terms.",
    ]
    return "\n".join(lines) + "\n"


def _front_matter(meta: dict) -> str:
    import yaml
    return "---\n" + yaml.safe_dump(meta, sort_keys=False, allow_unicode=True).strip() + "\n---\n\n"


def _doc_record(row: dict) -> dict:
    return {
        "title": row.get("title", ""),
        "url": row.get("url", ""),
        "canonical_url": row.get("canonical_url", ""),
        "license": row.get("license", "unknown"),
        "usage_class": row.get("usage_class", "unknown"),
        "retrieved_at": row.get("retrieved_at", ""),
        "sha256": row.get("sha256", ""),
        "retrieved_via": row.get("retrieved_via", "direct"),
        "snapshot_at": row.get("snapshot_at"),
        "snapshot_url": row.get("snapshot_url"),
    }


def export_public(store, out, sources=None, fail_on_restricted: bool = True) -> dict:
    """Write a public export that contains no restricted body text.

    Restricted sources get a metadata-only stub under ``links/``.  Body text is
    written only for public-domain, permissive and share-alike sources, and a
    license notice is written next to the body.
    """
    out = Path(out)
    if out.exists():
        # Only clear a directory that looks like one of our exports.
        known = {"text", "links", "sources.json", "README.md"}
        leftovers = [p for p in out.iterdir() if p.name not in known]
        if leftovers:
            raise ValueError(f"refusing to overwrite non-export directory {out}: {leftovers[0].name}")
        for name in ("text", "links"):
            target = out / name
            if target.is_dir():
                shutil.rmtree(target)
        for name in ("sources.json", "README.md"):
            target = out / name
            if target.exists():
                target.unlink()
    (out / "text").mkdir(parents=True, exist_ok=True)
    (out / "links").mkdir(parents=True, exist_ok=True)

    cfg_by_id = {s.id: s for s in (sources or [])}
    rows_by_id: dict[str, list[dict]] = defaultdict(list)
    for row in store.all_rows():
        rows_by_id[row["source_id"]].append(row)

    all_ids = sorted(set(cfg_by_id) | set(rows_by_id))
    sources_json: dict[str, dict] = {}
    counts = {c: 0 for c in USAGE_CLASSES}

    for sid in all_ids:
        rows = rows_by_id.get(sid, [])
        cfg = cfg_by_id.get(sid)
        cls = _source_class(rows, cfg)
        counts[cls] = counts.get(cls, 0) + 1

        first = rows[0] if rows else {}
        title = (cfg.get("title") if cfg else None) or first.get("title") or sid
        url = (cfg.get("url") if cfg else None) or first.get("canonical_url") or first.get("url", "")
        meta = {
            "id": sid,
            "title": title,
            "url": url,
            "license": (rows[0].get("license") if rows else None)
                        or (cfg.get("license") if cfg else "unknown"),
            "usage_class": cls,
            "retrieved_at": max((r.get("retrieved_at", "") for r in rows), default=""),
            "sha256": first.get("sha256", ""),
            "license_evidence_url": (rows[0].get("license_evidence_url") if rows else None)
                                    or (cfg.get("license_evidence_url") if cfg else ""),
            "usage_notes": (rows[0].get("usage_notes") if rows else None)
                           or (cfg.get("usage_notes") if cfg else ""),
            "terms_url": (cfg.get("terms_url") if cfg else "") or "",
            "robots_hash": (cfg.get("robots_hash") if cfg else "") or "",
            "retrieved_via": first.get("retrieved_via", "direct") if rows else "direct",
            "snapshot_at": first.get("snapshot_at") if rows else None,
            "document_count": len(rows),
            "documents": [_doc_record(r) for r in rows],
        }
        sources_json[sid] = meta

        if cls in RESTRICTED_CLASSES:
            if rows:
                (out / "links" / f"{sid}.md").write_text(
                    _front_matter(meta) + _restricted_stub(meta) + "\n"
                )
            continue

        # Publishable source: write body text only for publishable rows.
        dest = out / "text" / sid
        dest.mkdir(parents=True, exist_ok=True)
        for row in rows:
            if row.get("usage_class", "unknown") not in PUBLIC_BODY_CLASSES:
                continue
            norm = store.root / row.get("normalized_path", "")
            if not norm.exists():
                continue
            doc_meta = {**_doc_record(row), "license_evidence_url": row.get("license_evidence_url", "")}
            body = _read_body(norm)
            filename = f"{slugify(row.get('title') or row.get('sha256', 'document'))}.md"
            (dest / filename).write_text(
                _front_matter(doc_meta) + _publish_notice(meta) + body.rstrip() + "\n"
            )
        (dest / "LICENSE.txt").write_text(_license_notice(sid, meta))

    (out / "sources.json").write_text(json.dumps({
        "generated_at": _now(),
        "usage_class_counts": counts,
        "restricted_classes": sorted(RESTRICTED_CLASSES),
        "sources": sources_json,
    }, indent=2, ensure_ascii=False) + "\n")

    (out / "README.md").write_text(_readme(sources_json, counts))

    errors = check_public_export(out, store=store)
    if errors and fail_on_restricted:
        raise ExportGuardError("public export guard failed: " + "; ".join(errors))
    return {"out": str(out), "sources": len(sources_json), "counts": counts,
            "guard_errors": errors}


def _publish_notice(meta: dict) -> str:
    return (
        f"> **License:** {meta['license']} ({meta['usage_class']}). "
        f"**Attribution:** see `LICENSE.txt` in this directory. "
        f"**Evidence:** {meta.get('license_evidence_url', '')}\n\n"
    )


def _restricted_stub(meta: dict) -> str:
    lines = [
        "# Metadata only",
        "",
        f"- **Source:** {meta['id']}",
        f"- **Title:** {meta['title']}",
        f"- **URL:** {meta['url']}",
        f"- **License:** {meta['license']}",
        f"- **Usage class:** {meta['usage_class']}",
        f"- **Evidence:** {meta.get('license_evidence_url', '')}",
        f"- **Retrieved:** {meta['retrieved_at']}",
        f"- **SHA-256:** {meta['sha256']}",
        "",
        "Body text and excerpts are intentionally withheld. This source is a",
        "local reference only and must not be republished from this corpus.",
    ]
    return "\n".join(lines) + "\n"


def _readme(sources_json: dict, counts: dict) -> str:
    rows = []
    for sid, meta in sorted(sources_json.items()):
        rows.append(
            f"| {sid} | {meta['license']} | {meta['usage_class']} | "
            f"{meta['document_count']} | {'yes' if meta['usage_class'] in PUBLIC_BODY_CLASSES else 'no'} |"
        )
    return f"""# Public corpus export

Generated by `gbg-corpus export --public` on {_now()}.

This directory contains only material whose usage class permits public reuse.
Documents in `text/` are verbatim reference text with a license notice; documents
in `links/` are metadata-only stubs for local-reference sources.

## Usage class rules

| Class | Body text in export? | Rule |
|---|---|---|
| public-domain | yes | Explicit public-domain dedication or US government work. |
| permissive | yes | MIT/BSD/Apache/CC-BY. Keep the copyright and license notice. |
| share-alike | yes, with notice | GPL/AGPL/CC-BY-SA/GFDL. Attribution and license notice required; do not relicense. |
| nc-nd | no | Local reference only. No body text, excerpts, or derived prose. |
| copyrighted-local | no | Local reference only. Never export text. |
| unknown | no | Treated as copyrighted-local until a human upgrades it with evidence. |

`share-alike` text may be redistributed under its own license with the notice in
`LICENSE.txt`; it must not be pasted wholesale into unrelated project prose.

## Attribution

Every `text/<source>/` directory contains a `LICENSE.txt` with the license,
usage class, and evidence URL. Keep it alongside the text. `sources.json` records
the source id, title, URL, license, usage class, retrieval time, and SHA-256 for
every document.

## Source summary

| Source | License | Usage class | Docs | Body exported |
|---|---|---|---|---|
{chr(10).join(rows)}

Class counts: {", ".join(f"{k}={v}" for k, v in counts.items() if v)}.
"""


_FM_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def check_public_export(out, store=None, fail_on_restricted: bool = True) -> list[str]:
    """Validate an already-written public export directory.

    The invariant is simple: no restricted source id may appear under
    ``text/`` and no exported body may declare a restricted usage class.
    When a Store is supplied, manifest classes are cross-checked as well so a
    tampered sources.json cannot hide a restricted source.
    """
    out = Path(out)
    errors: list[str] = []
    sources_path = out / "sources.json"
    if not sources_path.exists():
        return [f"missing {sources_path}"]
    try:
        data = json.loads(sources_path.read_text())
    except json.JSONDecodeError as exc:
        return [f"invalid sources.json: {exc}"]

    sources = data.get("sources", {})
    restricted = {sid for sid, meta in sources.items()
                  if meta.get("usage_class") in RESTRICTED_CLASSES}
    if store is not None:
        restricted |= {row["source_id"] for row in store.all_rows()
                       if row.get("usage_class") in RESTRICTED_CLASSES}

    text_root = out / "text"
    if text_root.exists():
        for child in sorted(text_root.iterdir()):
            if child.is_dir() and child.name in restricted:
                errors.append(f"restricted source {child.name!r} has body text under text/")
        for md in sorted(text_root.rglob("*.md")):
            head = md.read_text(errors="replace")[:4096]
            m = _FM_RE.match(head)
            if m and re.search(r"^usage_class:\s*(nc-nd|copyrighted-local|unknown)\s*$", m.group(1), re.M):
                errors.append(f"restricted body text found at {md.relative_to(out)}")
            parts = md.relative_to(out).parts
            if len(parts) >= 2 and parts[1] in restricted:
                errors.append(f"restricted source {parts[1]!r} has body file {md.relative_to(out)}")

    links_root = out / "links"
    for sid in sorted(restricted):
        if sources[sid].get("document_count", 0) and not (links_root / f"{sid}.md").exists():
            errors.append(f"restricted source {sid!r} is missing its links/{sid}.md stub")

    return errors
