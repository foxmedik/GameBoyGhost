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

SHINGLE_THRESHOLD = 3


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


def _shingles(text: str, n: int = 12) -> set[str]:
    words = text.lower().split()
    if len(words) < n:
        return set()
    return {
        hashlib.sha256(" ".join(words[i:i + n]).encode("utf-8")).hexdigest()
        for i in range(len(words) - n + 1)
    }


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
    written_files: dict[str, str] = {}

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

        pub_rows = [r for r in rows if r.get("usage_class", "unknown") in PUBLIC_BODY_CLASSES]
        restricted_rows = [r for r in rows if r.get("usage_class", "unknown") in RESTRICTED_CLASSES]

        if restricted_rows:
            link_path = out / "links" / f"{sid}.md"
            link_path.write_text(
                _front_matter(meta) + _restricted_stub(meta, restricted_rows) + "\n"
            )
            written_files[link_path.relative_to(out).as_posix()] = hashlib.sha256(
                link_path.read_bytes()
            ).hexdigest()

        if pub_rows:
            dest = out / "text" / sid
            dest.mkdir(parents=True, exist_ok=True)
            for row in pub_rows:
                norm = store.root / row.get("normalized_path", "")
                if not norm.exists():
                    continue
                doc_meta = {**_doc_record(row), "license_evidence_url": row.get("license_evidence_url", "")}
                body = _read_body(norm)
                filename = f"{slugify(row.get('title') or row.get('sha256', 'document'))}.md"
                doc_path = dest / filename
                doc_path.write_text(
                    _front_matter(doc_meta) + _publish_notice(meta) + body.rstrip() + "\n"
                )
                written_files[doc_path.relative_to(out).as_posix()] = hashlib.sha256(
                    doc_path.read_bytes()
                ).hexdigest()
            lic_path = dest / "LICENSE.txt"
            lic_path.write_text(_license_notice(sid, meta))
            written_files[lic_path.relative_to(out).as_posix()] = hashlib.sha256(
                lic_path.read_bytes()
            ).hexdigest()

    readme_path = out / "README.md"
    readme_path.write_text(_readme(sources_json, counts))
    written_files["README.md"] = hashlib.sha256(readme_path.read_bytes()).hexdigest()

    sources_path = out / "sources.json"
    sources_data = {
        "generated_at": _now(),
        "usage_class_counts": counts,
        "restricted_classes": sorted(RESTRICTED_CLASSES),
        "files": dict(sorted(written_files.items())),
        "sources": sources_json,
    }
    sources_path.write_text(json.dumps(sources_data, indent=2, ensure_ascii=False) + "\n")

    errors = check_public_export(out, store=store)
    if errors and fail_on_restricted:
        if out.exists():
            shutil.rmtree(out)
        raise ExportGuardError("public export guard failed: " + "; ".join(errors))
    return {"out": str(out), "sources": len(sources_json), "counts": counts,
            "guard_errors": errors}


def _publish_notice(meta: dict) -> str:
    return (
        f"> **License:** {meta['license']} ({meta['usage_class']}). "
        f"**Attribution:** see `LICENSE.txt` in this directory. "
        f"**Evidence:** {meta.get('license_evidence_url', '')}\n\n"
    )


def _restricted_stub(meta: dict, restricted_rows: list[dict] | None = None) -> str:
    r_first = restricted_rows[0] if restricted_rows else {}
    title = r_first.get("title") or meta.get("title", "")
    url = r_first.get("canonical_url") or r_first.get("url") or meta.get("url", "")
    lic = r_first.get("license") or meta.get("license", "unknown")
    cls = r_first.get("usage_class") or meta.get("usage_class", "unknown")
    ev = r_first.get("license_evidence_url") or meta.get("license_evidence_url", "")
    retrieved = r_first.get("retrieved_at") or meta.get("retrieved_at", "")
    sha = r_first.get("sha256") or meta.get("sha256", "")

    lines = [
        "# Metadata only",
        "",
        f"- **Source:** {meta['id']}",
        f"- **Title:** {title}",
        f"- **URL:** {url}",
        f"- **License:** {lic}",
        f"- **Usage class:** {cls}",
        f"- **Evidence:** {ev}",
        f"- **Retrieved:** {retrieved}",
        f"- **SHA-256:** {sha}",
        "",
        "Body text and excerpts are intentionally withheld. This source is a",
        "local reference only and must not be republished from this corpus.",
    ]
    if restricted_rows and len(restricted_rows) > 1:
        lines.extend([
            "",
            "## Restricted documents",
            "",
        ])
        for r in restricted_rows:
            doc_title = r.get("title") or r.get("sha256", "document")
            doc_url = r.get("canonical_url") or r.get("url", "")
            doc_lic = r.get("license", "unknown")
            doc_cls = r.get("usage_class", "unknown")
            doc_ev = r.get("license_evidence_url", "")
            doc_sha = r.get("sha256", "")
            lines.extend([
                f"### {doc_title}",
                f"- **URL:** {doc_url}",
                f"- **License:** {doc_lic}",
                f"- **Usage class:** {doc_cls}",
                f"- **Evidence:** {doc_ev}",
                f"- **SHA-256:** {doc_sha}",
                "",
            ])
    return "\n".join(lines) + "\n"


def _readme(sources_json: dict, counts: dict) -> str:
    rows = []
    for sid, meta in sorted(sources_json.items()):
        docs = meta.get("documents", [])
        has_pub = any(d.get("usage_class") in PUBLIC_BODY_CLASSES for d in docs)
        has_priv = any(d.get("usage_class") in RESTRICTED_CLASSES for d in docs)
        if has_pub and has_priv:
            body_exported = "partial"
        elif has_pub:
            body_exported = "yes"
        else:
            body_exported = "no"
        rows.append(
            f"| {sid} | {meta['license']} | {meta['usage_class']} | "
            f"{meta['document_count']} | {body_exported} |"
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

    Checks:
    - sources.json structure and allowlist
    - Every file under out (except sources.json) is in the allowlist
    - Every allowlisted file exists and matches its sha256
    - When store is supplied: recomputes expected files from manifests and verifies
    - When store is supplied: builds 12-word shingles for all restricted docs and scans
      every file to verify no file shares >= 3 shingles
    - No restricted body files or restricted usage_class declarations under text/
    - Every restricted source has a links/<sid>.md stub
    """
    out = Path(out)
    errors: list[str] = []
    if not out.exists():
        return [f"export directory does not exist: {out}"]
    if not out.is_dir():
        return [f"export path is not a directory: {out}"]

    sources_path = out / "sources.json"
    if not sources_path.exists():
        return [f"missing {sources_path}"]
    try:
        data = json.loads(sources_path.read_text(errors="replace"))
    except json.JSONDecodeError as exc:
        return [f"invalid sources.json: {exc}"]
    if not isinstance(data, dict):
        return ["sources.json is not a JSON object"]

    sources = data.get("sources")
    if not isinstance(sources, dict):
        errors.append("sources.json 'sources' is not an object")
        sources = {}

    files = data.get("files")
    if not isinstance(files, dict):
        errors.append("sources.json 'files' allowlist is missing or not an object")
        files = {}

    # A4. File allowlist validation against disk
    for p in sorted(out.rglob("*")):
        if p.is_file():
            rel = p.relative_to(out).as_posix()
            if rel == "sources.json":
                continue
            if rel not in files:
                errors.append(f"file not in sources.json allowlist: {rel}")

    for rel_path, expected_hash in sorted(files.items()):
        p = out / rel_path
        if not p.is_file():
            errors.append(f"allowlisted file missing from export: {rel_path}")
        else:
            try:
                actual_hash = hashlib.sha256(p.read_bytes()).hexdigest()
                if actual_hash != expected_hash:
                    errors.append(
                        f"hash mismatch for {rel_path}: expected {expected_hash}, got {actual_hash}"
                    )
            except Exception as exc:
                errors.append(f"unable to read {rel_path}: {exc}")

    # A4. Store manifest recomputation
    if store is not None:
        expected_manifest_files: set[str] = {"README.md"}
        rows_by_id: dict[str, list[dict]] = defaultdict(list)
        for row in store.all_rows():
            rows_by_id[row["source_id"]].append(row)
        for sid, rows in rows_by_id.items():
            pub_rows = [r for r in rows if r.get("usage_class", "unknown") in PUBLIC_BODY_CLASSES]
            restricted_rows = [r for r in rows if r.get("usage_class", "unknown") in RESTRICTED_CLASSES]
            if pub_rows:
                expected_manifest_files.add(f"text/{sid}/LICENSE.txt")
                for r in pub_rows:
                    norm = store.root / r.get("normalized_path", "")
                    if norm.exists():
                        fn = f"{slugify(r.get('title') or r.get('sha256', 'document'))}.md"
                        expected_manifest_files.add(f"text/{sid}/{fn}")
            if restricted_rows:
                expected_manifest_files.add(f"links/{sid}.md")

        sources_files = set(files.keys())
        for m in sorted(expected_manifest_files - sources_files):
            errors.append(f"sources.json allowlist missing expected manifest file: {m}")
        for e in sorted(sources_files - expected_manifest_files):
            errors.append(f"sources.json allowlist contains unexpected file not in manifests: {e}")

    # A2/A3. Shingle fingerprints
    if store is not None:
        restricted_fingerprints: list[tuple[str, str, set[str]]] = []
        for row in store.all_rows():
            if row.get("usage_class") in RESTRICTED_CLASSES:
                norm = store.root / row.get("normalized_path", "")
                if norm.exists():
                    body = _read_body(norm)
                    sh = _shingles(body)
                    if sh:
                        doc_label = row.get("title") or row.get("sha256", "document")
                        restricted_fingerprints.append((row["source_id"], doc_label, sh))

        for p in sorted(out.rglob("*")):
            if p.is_file():
                try:
                    content = p.read_text(errors="replace")
                except Exception as exc:
                    errors.append(f"failed to read {p.relative_to(out)}: {exc}")
                    continue
                f_sh = _shingles(content)
                if not f_sh:
                    continue
                for sid, doc_label, r_sh in restricted_fingerprints:
                    shared = f_sh & r_sh
                    if len(shared) >= SHINGLE_THRESHOLD:
                        errors.append(
                            f"file {p.relative_to(out).as_posix()} shares {len(shared)} shingles "
                            f"with restricted document {doc_label!r} from source {sid!r}"
                        )

    # Check text/ directory
    store_fully_restricted: set[str] = set()
    if store is not None:
        rows_by_id = defaultdict(list)
        for row in store.all_rows():
            rows_by_id[row["source_id"]].append(row)
        for sid, rows in rows_by_id.items():
            if rows and all(r.get("usage_class") in RESTRICTED_CLASSES for r in rows):
                store_fully_restricted.add(sid)

    json_fully_restricted: set[str] = set()
    for sid, meta in sources.items():
        if isinstance(meta, dict):
            docs = meta.get("documents", [])
            if docs and all(d.get("usage_class") in RESTRICTED_CLASSES for d in docs):
                json_fully_restricted.add(sid)
            elif not docs and meta.get("usage_class") in RESTRICTED_CLASSES:
                json_fully_restricted.add(sid)

    fully_restricted = store_fully_restricted | json_fully_restricted

    text_root = out / "text"
    if text_root.exists():
        for child in sorted(text_root.iterdir()):
            if child.is_dir() and child.name in fully_restricted:
                errors.append(f"restricted source {child.name!r} has body text under text/")
            elif not child.is_dir():
                errors.append(f"non-directory found under text/: {child.name}")

        for md in sorted(text_root.rglob("*.md")):
            content = md.read_text(errors="replace")
            m = _FM_RE.match(content)
            if m and re.search(r"^usage_class:\s*['\"]?(nc-nd|copyrighted-local|unknown)['\"]?\s*$", m.group(1), re.M):
                errors.append(f"restricted body text found at {md.relative_to(out).as_posix()}")
            parts = md.relative_to(out).parts
            if len(parts) >= 2 and parts[1] in fully_restricted:
                errors.append(f"restricted source {parts[1]!r} has body file {md.relative_to(out).as_posix()}")

    # A5. Check links/ directory
    links_root = out / "links"
    should_have_stub: set[str] = set()
    if store is not None:
        should_have_stub |= {
            row["source_id"] for row in store.all_rows()
            if row.get("usage_class") in RESTRICTED_CLASSES
        }
    for sid, meta in sources.items():
        if isinstance(meta, dict):
            if meta.get("usage_class") in RESTRICTED_CLASSES:
                should_have_stub.add(sid)
            elif any(d.get("usage_class") in RESTRICTED_CLASSES for d in meta.get("documents", [])):
                should_have_stub.add(sid)

    for sid in sorted(should_have_stub):
        meta = sources.get(sid)
        if meta is None:
            errors.append(f"restricted source {sid!r} is missing from sources.json")
        elif not (links_root / f"{sid}.md").exists():
            errors.append(f"restricted source {sid!r} is missing its links/{sid}.md stub")

    return errors
