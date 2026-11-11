from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .adapters import (fetch_arxiv, fetch_github_raw, fetch_html_article,
                       fetch_mediawiki, fetch_pdf_text, fetch_reddit,
                       fetch_speedrun, fetch_wayback_html)
from .check import check as run_check
from .config import load_sources
from .export import check_public_export, export_public
from .index import build_index
from .migrate import apply_audit, migrate_add_usage_class
from .report import build_report, print_summary
from .store import Store

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = Path(__file__).resolve().parents[4]
SOURCES_TOML = PROJECT_ROOT / "sources.toml"

ADAPTERS = {
    "github_raw": fetch_github_raw,
    "mediawiki": fetch_mediawiki,
    "wayback_html": fetch_wayback_html,
    "pdf_text": fetch_pdf_text,
    "arxiv": fetch_arxiv,
    "speedrun": fetch_speedrun,
    "html_article": fetch_html_article,
    "reddit": fetch_reddit,
}


def cmd_fetch(args) -> int:
    sources = load_sources(SOURCES_TOML)
    if args.source:
        sources = [s for s in sources if s.id == args.source]
    elif args.priority:
        sources = [s for s in sources if s.priority == args.priority]
    else:
        sources = [s for s in sources if s.priority == "P0"]
    if not sources:
        print("no matching sources", file=sys.stderr)
        return 2

    store = Store()
    failed = 0
    for src in sources:
        if src.get("enabled", True) is False:
            reason = src.get("blocked_reason", "disabled")
            store.record_failure(src.id, src.get("url") or src.get("repo") or src.get("api") or "",
                                 f"disabled: {reason}")
            print(f"[{src.id}] SKIP disabled: {reason}")
            continue
        fn = ADAPTERS.get(src.kind)
        if not fn:
            store.record_failure(src.id, "", f"no adapter for kind {src.kind}")
            print(f"[{src.id}] FAIL no adapter for {src.kind}")
            failed += 1
            continue
        try:
            docs = fn(src, args.limit) if src.kind == "github_raw" else fn(src)
        except Exception as exc:
            store.record_failure(src.id, src.get("url") or src.get("repo") or src.get("api") or "",
                                 f"{type(exc).__name__}: {exc}")
            print(f"[{src.id}] FAIL {type(exc).__name__}: {exc}")
            failed += 1
            continue
        saved = 0
        for doc in docs:
            try:
                if store.save(doc) is not None:
                    saved += 1
            except Exception as exc:
                store.record_failure(src.id, doc.url, f"save: {type(exc).__name__}: {exc}")
        print(f"[{src.id}] {saved} new / {len(docs)} fetched")
    print(f"fetch complete: {len(sources) - failed} sources ok, {failed} failed")
    return 1 if failed else 0


def cmd_check(args) -> int:
    store = Store()
    errors = run_check(store, REPO_ROOT)
    if getattr(args, "public_out", None):
        errors += check_public_export(Path(args.public_out), store=store)
    if errors:
        print(f"check FAILED ({len(errors)} problems)")
        for e in errors[:100]:
            print(" -", e)
        return 1
    print("check OK")
    return 0


def cmd_report(args) -> int:
    report = build_report(Store(), REPO_ROOT)
    print_summary(report)
    print(f"\nwrote {REPO_ROOT / 'reports' / 'corpus' / 'report.json'}")
    return 0


def cmd_index(args) -> int:
    n = build_index(Store())
    print(f"indexed {n} chunks")
    return 0


def cmd_migrate(args) -> int:
    if not args.add_usage_class:
        print("migrate requires --add-usage-class", file=sys.stderr)
        return 2
    store = Store()
    changed = migrate_add_usage_class(store)
    print(f"migrate --add-usage-class: {changed} rows changed")
    return 0


def cmd_audit(args) -> int:
    if not args.apply:
        print("audit requires --apply", file=sys.stderr)
        return 2
    store = Store()
    sources = load_sources(SOURCES_TOML)
    changed, warnings = apply_audit(store, sources)
    print(f"audit: {changed} rows updated from sources.toml")
    for warning in warnings:
        print(" -", warning)
    return 1 if warnings else 0


def cmd_export(args) -> int:
    if args.check:
        errors = check_public_export(Path(args.check), store=Store())
        if errors:
            print(f"export check FAILED ({len(errors)} problems)")
            for e in errors:
                print(" -", e)
            return 1
        print("export check OK")
        return 0

    if not args.public or not args.out:
        print("export requires --public --out <dir> (or --check <dir>)", file=sys.stderr)
        return 2
    try:
        result = export_public(Store(), args.out, load_sources(SOURCES_TOML))
    except Exception as exc:
        print(f"export FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"wrote public export to {result['out']}")
    print(f"sources: {result['sources']}; classes: "
          + ", ".join(f"{k}={v}" for k, v in result["counts"].items() if v))
    if result["guard_errors"]:
        for e in result["guard_errors"]:
            print(" -", e)
        return 1
    print("export guard OK: no restricted body text")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="gbg-corpus", description="GameBoyGhost reference corpus")
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("fetch")
    p.add_argument("--source")
    p.add_argument("--priority")
    p.add_argument("--limit", type=int)
    p.set_defaults(func=cmd_fetch)

    p = sub.add_parser("check")
    p.add_argument("--public-out", help="also validate a public export directory")
    p.set_defaults(func=cmd_check)

    for name, fn in (("report", cmd_report), ("index", cmd_index)):
        sp = sub.add_parser(name)
        sp.set_defaults(func=fn)

    p = sub.add_parser("migrate")
    p.add_argument("--add-usage-class", action="store_true")
    p.set_defaults(func=cmd_migrate)

    p = sub.add_parser("audit")
    p.add_argument("--apply", action="store_true")
    p.set_defaults(func=cmd_audit)

    p = sub.add_parser("export")
    p.add_argument("--public", action="store_true")
    p.add_argument("--out")
    p.add_argument("--check", metavar="DIR")
    p.set_defaults(func=cmd_export)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
