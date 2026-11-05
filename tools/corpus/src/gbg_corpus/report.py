from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path


def build_report(store, repo_root: Path) -> dict:
    rows = store.all_rows()
    by_source: dict[str, dict] = defaultdict(lambda: {"documents": 0, "bytes": 0,
                                                      "licenses": Counter(), "kinds": Counter()})
    for row in rows:
        entry = by_source[row["source_id"]]
        entry["documents"] += 1
        raw = store.root / row.get("raw_path", "")
        if raw.exists():
            entry["bytes"] += raw.stat().st_size
        entry["licenses"][row.get("license", "unknown")] += 1
        entry["kinds"][row.get("kind", "?")] += 1

    failures = []
    if store.failures_path.exists():
        failures = [json.loads(l) for l in store.failures_path.read_text().splitlines() if l.strip()]

    clusters: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        if row.get("duplicate_of"):
            clusters[row["duplicate_of"]].append(row.get("canonical_url", row.get("url", "")))

    unresolved = [f for f in failures
                  if by_source.get(f.get("source_id"), {}).get("documents", 0) == 0]

    report = {
        "generated_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc).isoformat(),
        "corpus_root": str(store.root),
        "totals": {
            "documents": len(rows),
            "bytes": sum(v["bytes"] for v in by_source.values()),
            "failures": len(failures),
            "failures_unresolved": len(unresolved),
            "duplicates": sum(len(v) for v in clusters.values()),
        },
        "by_source": {
            sid: {
                "documents": v["documents"], "bytes": v["bytes"],
                "licenses": dict(v["licenses"]), "kinds": dict(v["kinds"]),
            } for sid, v in sorted(by_source.items())
        },
        "failures": failures,
        "duplicate_clusters": [{"canonical_sha256": k, "members": v} for k, v in clusters.items()],
    }

    out = repo_root / "reports" / "corpus"
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps(report, indent=2))
    return report


def print_summary(report: dict):
    print(f"{'source':28s} {'docs':>6s} {'bytes':>12s}  licenses")
    print("-" * 78)
    for sid, v in report["by_source"].items():
        lic = ", ".join(f"{k}:{n}" for k, n in v["licenses"].items())
        print(f"{sid:28s} {v['documents']:6d} {v['bytes']:12d}  {lic}")
    print("-" * 78)
    t = report["totals"]
    print(f"{'TOTAL':28s} {t['documents']:6d} {t['bytes']:12d}  "
          f"failures:{t['failures']} (unresolved:{t['failures_unresolved']}) "
          f"duplicates:{t['duplicates']}")
