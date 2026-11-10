from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .model import RESTRICTED_CLASSES, USAGE_CLASSES

FRESHNESS_DAYS = 180


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        try:
            dt = datetime.fromisoformat(text[:10])
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _age_days(row: dict, now: datetime) -> int | None:
    dt = _parse_date(row.get("published_at")) or _parse_date(row.get("retrieved_at"))
    if dt is None:
        return None
    return max(0, (now - dt).days)


def build_report(store, repo_root: Path) -> dict:
    now = datetime.now(timezone.utc)
    rows = store.all_rows()
    by_source: dict[str, dict] = defaultdict(lambda: {
        "documents": 0, "bytes": 0, "licenses": Counter(),
        "usage_classes": Counter(), "kinds": Counter(), "age_days": [],
    })
    class_counts: Counter = Counter({c: 0 for c in USAGE_CLASSES})
    stale_documents: list[dict] = []
    ages: list[int] = []

    for row in rows:
        entry = by_source[row["source_id"]]
        entry["documents"] += 1
        raw = store.root / row.get("raw_path", "")
        if raw.exists():
            entry["bytes"] += raw.stat().st_size
        entry["licenses"][row.get("license", "unknown")] += 1
        cls = row.get("usage_class", "unknown")
        entry["usage_classes"][cls] += 1
        class_counts[cls] += 1
        entry["kinds"][row.get("kind", "?")] += 1
        age = _age_days(row, now)
        if age is not None:
            ages.append(age)
            entry["age_days"].append(age)
            if age > FRESHNESS_DAYS:
                stale_documents.append({
                    "source_id": row["source_id"], "title": row.get("title", ""),
                    "url": row.get("url", ""), "age_days": age,
                    "dated_by": "published_at" if row.get("published_at") else "retrieved_at",
                })

    failures = []
    if store.failures_path.exists():
        failures = [json.loads(l) for l in store.failures_path.read_text().splitlines() if l.strip()]

    clusters: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        if row.get("duplicate_of"):
            clusters[row["duplicate_of"]].append(row.get("canonical_url", row.get("url", "")))

    unresolved = [f for f in failures
                  if by_source.get(f.get("source_id"), {}).get("documents", 0) == 0]
    restricted = sum(v for k, v in class_counts.items() if k in RESTRICTED_CLASSES)

    report = {
        "generated_at": now.isoformat(),
        "corpus_root": str(store.root),
        "totals": {
            "documents": len(rows),
            "bytes": sum(v["bytes"] for v in by_source.values()),
            "failures": len(failures),
            "failures_unresolved": len(unresolved),
            "duplicates": sum(len(v) for v in clusters.values()),
            "restricted_documents": restricted,
            "unknown_documents": class_counts.get("unknown", 0),
            "usage_classes": dict(class_counts),
        },
        "freshness": {
            "threshold_days": FRESHNESS_DAYS,
            "evaluated_documents": len(ages),
            "stale_documents": len(stale_documents),
            "oldest_age_days": max(ages) if ages else None,
            "stale": sorted(stale_documents, key=lambda d: d["age_days"], reverse=True),
        },
        "by_source": {
            sid: {
                "documents": v["documents"], "bytes": v["bytes"],
                "licenses": dict(v["licenses"]),
                "usage_classes": dict(v["usage_classes"]),
                "kinds": dict(v["kinds"]),
                "age_days": max(v["age_days"]) if v["age_days"] else None,
                "max_age_days": max(v["age_days"]) if v["age_days"] else None,
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
    print(f"{'source':28s} {'docs':>6s} {'bytes':>12s}  usage_class")
    print("-" * 88)
    for sid, v in report["by_source"].items():
        cls = ", ".join(f"{k}:{n}" for k, n in v["usage_classes"].items())
        print(f"{sid:28s} {v['documents']:6d} {v['bytes']:12d}  {cls}")
    print("-" * 88)
    t = report["totals"]
    print(f"{'TOTAL':28s} {t['documents']:6d} {t['bytes']:12d}  "
          f"failures:{t['failures']} (unresolved:{t['failures_unresolved']}) "
          f"duplicates:{t['duplicates']}")
    print("\nusage_class breakdown")
    for cls in USAGE_CLASSES:
        print(f"  {cls:18s} {t['usage_classes'].get(cls, 0):5d}")
    print(f"  {'restricted':18s} {t['restricted_documents']:5d}  "
          f"(nc-nd + copyrighted-local + unknown)")
    f = report["freshness"]
    print(f"\nfreshness: {f['stale_documents']} docs older than {f['threshold_days']} days "
          f"(oldest {f['oldest_age_days']} days)")
