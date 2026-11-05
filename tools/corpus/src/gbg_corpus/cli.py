from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .adapters import (fetch_arxiv, fetch_github_raw, fetch_html_article,
                       fetch_mediawiki, fetch_reddit, fetch_speedrun)
from .check import check as run_check
from .config import load_sources
from .index import build_index
from .report import build_report, print_summary
from .store import Store

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = Path(__file__).resolve().parents[4]
SOURCES_TOML = PROJECT_ROOT / "sources.toml"

ADAPTERS = {
    "github_raw": fetch_github_raw,
    "mediawiki": fetch_mediawiki,
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
    errors = run_check(Store(), REPO_ROOT)
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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="gbg-corpus", description="GameBoyGhost reference corpus")
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("fetch")
    p.add_argument("--source")
    p.add_argument("--priority")
    p.add_argument("--limit", type=int)
    p.set_defaults(func=cmd_fetch)

    for name, fn in (("check", cmd_check), ("report", cmd_report), ("index", cmd_index)):
        sp = sub.add_parser(name)
        sp.set_defaults(func=fn)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
