from __future__ import annotations

import json
from pathlib import Path

import pytest

from gbg_corpus.adapters import parse_wayback_cdx, wayback_id_url
from gbg_corpus.check import check as run_check
from gbg_corpus.config import Source
from gbg_corpus.export import (ExportGuardError, _read_body,
                               check_public_export, export_public)
from gbg_corpus.index import build_index
from gbg_corpus.migrate import migrate_add_usage_class, sync_normalized_front_matter
from gbg_corpus.model import Document
from gbg_corpus.store import MAX_DOC_BYTES, Store

FIX = Path(__file__).parent / "fixtures"


def make_doc(**kw) -> Document:
    base = dict(
        source_id="test", kind="html_article", url="https://example.test/a",
        canonical_url="https://example.test/a", title="Test", text="# Test\n\nhello",
        raw=b"# Test\n\nhello", ext="md", license="MIT",
        usage_class="permissive",
        license_evidence_url="https://example.test/LICENSE",
        usage_notes="Test fixture.",
    )
    base.update(kw)
    return Document(**base)


def source(sid: str, **kw) -> Source:
    raw = {
        "id": sid, "kind": "html_article", "license": "MIT",
        "usage_class": "permissive",
        "license_evidence_url": "https://example.test/LICENSE",
        "usage_notes": "Test fixture.", "terms_url": "https://example.test/terms",
        "robots_hash": "0" * 64,
    }
    raw.update(kw)
    return Source(id=sid, kind=raw["kind"], raw=raw)


def test_usage_class_enum_validation(tmp_path):
    store = Store(tmp_path / "corpus")
    with pytest.raises(ValueError):
        store.save(make_doc(usage_class="open-ish"))
    assert store.save(make_doc(usage_class="copyrighted-local")) is not None


def test_manifest_migration_is_idempotent(tmp_path):
    store = Store(tmp_path / "corpus")
    manifest = store.root / "manifests" / "legacy.jsonl"
    manifest.write_text(json.dumps({
        "source_id": "legacy", "kind": "html_article", "url": "https://example.test/old",
        "sha256": "abc", "license": "unknown",
    }) + "\n")
    assert migrate_add_usage_class(store) == 1
    row = json.loads(manifest.read_text())
    assert row["usage_class"] == "unknown"
    assert row["license_evidence_url"] == ""
    assert row["usage_notes"] == ""
    assert row["retrieved_via"] == "direct"
    assert migrate_add_usage_class(store) == 0


def test_export_public_excludes_restricted_bodies(tmp_path):
    store = Store(tmp_path / "corpus")
    store.save(make_doc(source_id="pub", title="Public source",
                        text="# Public\n\npublic body", raw=b"# Public\n\npublic body"))
    store.save(make_doc(source_id="priv", title="Private source",
                        text="# Private\n\nsecret body", raw=b"# Private\n\nsecret body",
                        usage_class="nc-nd"))
    store.save(make_doc(source_id="unk", title="Unknown source",
                        text="# Unknown\n\nunknown body", raw=b"# Unknown\n\nunknown body",
                        usage_class="unknown", license="unknown"))
    out = tmp_path / "public"
    result = export_public(
        store, out, [source("pub"), source("priv", usage_class="nc-nd", license="CC-BY-NC-ND-4.0"),
                     source("unk", usage_class="unknown", license="unknown")]
    )
    assert result["guard_errors"] == []
    assert (out / "text" / "pub").is_dir()
    assert not (out / "text" / "priv").exists()
    assert not (out / "text" / "unk").exists()
    assert (out / "links" / "priv.md").exists()
    assert (out / "links" / "unk.md").exists()
    assert "secret body" not in (out / "links" / "priv.md").read_text()
    assert "unknown body" not in (out / "links" / "unk.md").read_text()
    assert check_public_export(out, store=store) == []


def test_clean_export_returns_no_errors(clean_leak_bench):
    store, out, sources, priv_doc = clean_leak_bench
    assert check_public_export(out, store=store) == []


def test_guard_failure_deletes_output_directory(tmp_path):
    bad_out = tmp_path / "bad_export"
    bad_store = Store(tmp_path / "bad_corpus")
    bad_store.save(make_doc(source_id="pub", title="Leaked Doc", text=f"# Leak\n\n{PRIV_BODY}"))
    bad_store.save(make_doc(source_id="priv", title="Secret", text=f"# Secret\n\n{PRIV_BODY}", usage_class="nc-nd"))
    with pytest.raises(ExportGuardError):
        export_public(bad_store, bad_out, [source("pub", usage_class="public-domain"), source("priv", usage_class="nc-nd")])
    assert not bad_out.exists()


def test_check_fails_when_restricted_body_under_text(tmp_path):
    store = Store(tmp_path / "corpus")
    store.save(make_doc(source_id="priv", title="Private source",
                        text="# Private\n\nsecret body", raw=b"# Private\n\nsecret body",
                        usage_class="copyrighted-local"))
    out = tmp_path / "public"
    export_public(store, out, [source("priv", usage_class="copyrighted-local")])
    evil = out / "text" / "priv"
    evil.mkdir(parents=True)
    (evil / "leak.md").write_text(
        "---\nsource_id: priv\nusage_class: copyrighted-local\n---\n\nsecret body\n"
    )
    errors = check_public_export(out)
    assert any("restricted source 'priv'" in e for e in errors)
    assert any("restricted body text" in e for e in errors)


def test_magic_byte_sniff_rejects_fake_markdown_zip(tmp_path):
    store = Store(tmp_path / "corpus")
    row = store.save(make_doc(ext="md", raw=b"PK\x03\x04fake zip payload"))
    assert row is None
    log = store.failures_path.read_text()
    assert "refused binary content (zip)" in log


def test_max_size_rejection(tmp_path):
    store = Store(tmp_path / "corpus")
    row = store.save(make_doc(raw=b"x" * (MAX_DOC_BYTES + 1)))
    assert row is None
    log = store.failures_path.read_text()
    assert "refused oversized document" in log
    assert not (store.root / "raw" / "test").exists()


def test_wayback_cdx_fixture_builds_id_url():
    captures = parse_wayback_cdx((FIX / "wayback_cdx.json").read_text())
    assert len(captures) == 2
    assert captures[0]["timestamp"] == "20131128111419"
    assert captures[0]["statuscode"] == "200"
    url = wayback_id_url(captures[0]["timestamp"], captures[0]["original_url"])
    assert url == ("https://web.archive.org/web/20131128111419id_/"
                   "http://tcrf.net/The_Legend_of_Zelda:_Link%27s_Awakening_DX")
    assert "20131128111419id_/" in url


PRIV_BODY_WORDS = [
    "link", "awakening", "zelda", "dungeon", "compass", "instrument", "sword",
    "shield", "koholint", "nightmare", "tail", "cave", "bottle", "grotto",
    "key", "cavern", "angler", "tunnel", "catfish", "maw", "face", "shrine",
    "eagle", "tower", "turtle", "rock", "wind", "fish", "egg", "marin",
] * 12  # 30 * 12 = 360 words (> 300 words)
PRIV_BODY = " ".join(PRIV_BODY_WORDS)


@pytest.fixture
def clean_leak_bench(tmp_path):
    store = Store(tmp_path / "corpus")
    pub_doc = make_doc(
        source_id="pub", title="Public Guide", url="https://example.test/pub",
        text="# Public Guide\n\nThis is a fully public guide to hardware.",
        raw=b"# Public Guide\n\nThis is a fully public guide to hardware.",
        usage_class="public-domain", license="CC0-1.0",
        license_evidence_url="https://example.test/cc0",
    )
    priv_doc = make_doc(
        source_id="priv", title="Private Research", url="https://example.test/priv",
        text=f"# Private Research\n\n{PRIV_BODY}",
        raw=f"# Private Research\n\n{PRIV_BODY}".encode("utf-8"),
        usage_class="nc-nd", license="CC-BY-NC-ND-4.0",
        license_evidence_url="https://example.test/nc-nd",
    )
    store.save(pub_doc)
    store.save(priv_doc)
    sources = [
        source("pub", usage_class="public-domain", license="CC0-1.0"),
        source("priv", usage_class="nc-nd", license="CC-BY-NC-ND-4.0"),
    ]
    out = tmp_path / "public_export"
    res = export_public(store, out, sources)
    assert res["guard_errors"] == []
    assert check_public_export(out, store=store) == []
    return store, out, sources, priv_doc


def test_leak_variant_01_no_front_matter(clean_leak_bench):
    store, out, sources, priv_doc = clean_leak_bench
    (out / "text" / "pub" / "leak.md").write_text(PRIV_BODY + "\n")
    errors = check_public_export(out, store=store)
    assert len(errors) > 0


def test_leak_variant_02_front_matter_public_domain(clean_leak_bench):
    store, out, sources, priv_doc = clean_leak_bench
    (out / "text" / "pub" / "leak.md").write_text(
        f"---\nusage_class: public-domain\n---\n\n{PRIV_BODY}\n"
    )
    errors = check_public_export(out, store=store)
    assert len(errors) > 0


def test_leak_variant_03_own_normalized_file(clean_leak_bench):
    store, out, sources, priv_doc = clean_leak_bench
    norm = store.root / store.rows("priv")[0]["normalized_path"]
    (out / "text" / "pub" / "leak.md").write_text(norm.read_text())
    errors = check_public_export(out, store=store)
    assert len(errors) > 0


def test_leak_variant_04_quoted_usage_class(clean_leak_bench):
    store, out, sources, priv_doc = clean_leak_bench
    (out / "text" / "pub" / "leak.md").write_text(
        f"---\nusage_class: 'nc-nd'\n---\n\n{PRIV_BODY}\n"
    )
    errors = check_public_export(out, store=store)
    assert len(errors) > 0


def test_leak_variant_05_oversized_front_matter(clean_leak_bench):
    store, out, sources, priv_doc = clean_leak_bench
    padding = "note: " + ("x" * 4500) + "\n"
    (out / "text" / "pub" / "leak.md").write_text(
        f"---\nusage_class: 'nc-nd'\n{padding}---\n\n{PRIV_BODY}\n"
    )
    errors = check_public_export(out, store=store)
    assert len(errors) > 0


def test_leak_variant_06_appended_to_links(clean_leak_bench):
    store, out, sources, priv_doc = clean_leak_bench
    priv_link = out / "links" / "priv.md"
    with priv_link.open("a") as f:
        f.write("\n\n" + PRIV_BODY + "\n")
    errors = check_public_export(out, store=store)
    assert len(errors) > 0


def test_leak_variant_07_extra_file_at_root(clean_leak_bench):
    store, out, sources, priv_doc = clean_leak_bench
    (out / "extra.md").write_text("extra root file\n")
    errors = check_public_export(out, store=store)
    assert len(errors) > 0


def test_leak_variant_08_invalid_directory(clean_leak_bench):
    store, out, sources, priv_doc = clean_leak_bench
    (out / "text" / "misc").mkdir(parents=True, exist_ok=True)
    (out / "text" / "misc" / "leak.md").write_text(
        f"---\nusage_class: public-domain\n---\n\n{PRIV_BODY}\n"
    )
    errors = check_public_export(out, store=store)
    assert len(errors) > 0


def test_leak_variant_09_file_under_text(clean_leak_bench):
    store, out, sources, priv_doc = clean_leak_bench
    (out / "text" / "priv.txt").write_text(PRIV_BODY + "\n")
    errors = check_public_export(out, store=store)
    assert len(errors) > 0


def test_leak_variant_10_case_variant_directory(clean_leak_bench):
    store, out, sources, priv_doc = clean_leak_bench
    (out / "text" / "PRIV").mkdir(parents=True, exist_ok=True)
    (out / "text" / "PRIV" / "leak.md").write_text(PRIV_BODY + "\n")
    errors = check_public_export(out, store=store)
    assert len(errors) > 0


def test_leak_variant_11_sources_json_priv_removed(clean_leak_bench):
    store, out, sources, priv_doc = clean_leak_bench
    sources_json = out / "sources.json"
    data = json.loads(sources_json.read_text())
    data["sources"].pop("priv", None)
    sources_json.write_text(json.dumps(data, indent=2))
    errors = check_public_export(out, store=store)
    assert isinstance(errors, list)
    assert len(errors) > 0


def test_fingerprint_scan_catches_leak_when_allowlist_passes(clean_leak_bench):
    """A2.1: Plant restricted body in allowlisted file with updated hash; fingerprint scan catches it."""
    import hashlib
    store, out, sources, priv_doc = clean_leak_bench
    pub_file = out / "text" / "pub" / "public-guide.md"
    assert pub_file.exists()
    pub_file.write_text(f"---\nusage_class: public-domain\n---\n\n{PRIV_BODY}\n")

    rel = "text/pub/public-guide.md"
    new_sha = hashlib.sha256(pub_file.read_bytes()).hexdigest()
    sources_json = out / "sources.json"
    data = json.loads(sources_json.read_text())
    data["files"][rel] = new_sha
    sources_json.write_text(json.dumps(data, indent=2))

    errors = check_public_export(out, store=store)
    assert not any("sources.json allowlist" in e for e in errors)
    assert not any("hash mismatch" in e for e in errors)
    assert any("shares" in e and "shingles" in e for e in errors)


def test_allowlist_alone_catches_extra_file_when_fingerprint_scan_empty(tmp_path):
    """A2.1 mirror: Empty restricted set, planted extra file; allowlist alone catches it."""
    store = Store(tmp_path / "pub_only_corpus")
    store.save(make_doc(source_id="pub", title="Public Only Doc"))
    out = tmp_path / "pub_export"
    export_public(store, out, [source("pub", usage_class="public-domain")])

    (out / "extra.md").write_text("untracked extra file\n")
    errors = check_public_export(out, store=store)
    assert any("file not in sources.json allowlist: extra.md" in e for e in errors)
    assert not any("shares" in e and "shingles" in e for e in errors)


def test_check_public_export_requires_store(clean_leak_bench):
    """A2.2: check_public_export(out, store=None) returns error saying content scan could not run."""
    store, out, sources, priv_doc = clean_leak_bench
    errors = check_public_export(out, store=None)
    assert len(errors) > 0
    assert any("store not provided: content fingerprint scan and manifest verification could not run" in e for e in errors)


def test_shingles_catch_leak_with_stripped_markdown_and_altered_punctuation(clean_leak_bench):
    r"""A2.3: Restricted body with stripped markdown and altered punctuation is still caught by \w+ shingles."""
    store, out, sources, priv_doc = clean_leak_bench
    words = PRIV_BODY.split()
    altered_tokens = [
        f"**{w.upper()}**," if i % 3 == 0 else (f"#{w}?!" if i % 3 == 1 else f"--- {w} ---")
        for i, w in enumerate(words)
    ]
    altered_body = " ".join(altered_tokens)

    (out / "text" / "pub" / "leak.md").write_text(
        f"---\nusage_class: public-domain\n---\n\n{altered_body}\n"
    )
    errors = check_public_export(out, store=store)
    assert any("shares" in e and "shingles" in e for e in errors)


def test_front_matter_sync_idempotent_and_preserves_body_bytes(tmp_path):
    """B4: front-matter sync is idempotent and preserves exact body bytes."""
    import hashlib
    store = Store(tmp_path / "corpus")
    doc = make_doc(
        source_id="test", title="Sync Test", text="# Heading\n\nBody paragraph line 1.\nLine 2.\n",
        license="MIT", usage_class="permissive",
    )
    row = store.save(doc)
    assert row is not None

    norm_path = store.root / row["normalized_path"]
    # Hand-alter front matter to simulate a legacy file missing usage_class and with stale license
    text = norm_path.read_text()
    parts = text.split("---", 2)
    stale_fm = (
        "---\nsource_id: test\ntitle: Sync Test\nlicense: old-lic\n"
        f"sha256: {row['sha256']}\n---"
    )
    norm_path.write_text(stale_fm + parts[2])

    body_before = parts[2]
    hash_before = hashlib.sha256(body_before.encode("utf-8")).hexdigest()

    changed, hashes = sync_normalized_front_matter(store)
    assert changed == 1
    rel = row["normalized_path"]
    assert rel in hashes
    b_before, b_after = hashes[rel]
    assert b_before == hash_before
    assert b_after == hash_before

    # Verify body bytes on disk are identical
    text_after = norm_path.read_text()
    body_after = text_after.split("---", 2)[2]
    assert hashlib.sha256(body_after.encode("utf-8")).hexdigest() == hash_before
    assert body_after == body_before

    # Verify front matter now has manifest fields
    import yaml
    fm_updated = yaml.safe_load(text_after.split("---", 2)[1])
    assert fm_updated["license"] == "MIT"
    assert fm_updated["usage_class"] == "permissive"

    # Idempotent second pass
    changed2, hashes2 = sync_normalized_front_matter(store)
    assert changed2 == 0
    assert hashes2[rel][0] == hash_before
    assert hashes2[rel][1] == hash_before


def test_check_fails_on_front_matter_mismatch(tmp_path):
    """B4: check fails when normalized front matter disagrees with manifest row."""
    store = Store(tmp_path / "corpus")
    doc = make_doc(source_id="test", title="Mismatch Test", license="MIT", usage_class="permissive")
    row = store.save(doc)
    assert row is not None

    # Front matter initially in sync
    errors = run_check(store, tmp_path)
    assert not any("front matter mismatch" in e for e in errors)

    # Hand-edit front matter to create mismatch
    norm_path = store.root / row["normalized_path"]
    text = norm_path.read_text()
    parts = text.split("---", 2)
    tampered_fm = parts[1].replace("license: MIT", "license: GPL-3.0")
    norm_path.write_text(f"---{tampered_fm}---" + parts[2])

    errors = run_check(store, tmp_path)
    assert any("front matter mismatch" in e and "license" in e for e in errors)


def test_index_includes_usage_class_column(tmp_path):
    """B3: index.py docs table includes usage_class column filled from manifest row."""
    import sqlite3
    store = Store(tmp_path / "corpus")
    doc = make_doc(source_id="test", title="Index Test", text="# Head\n\nChunk text.", usage_class="share-alike")
    store.save(doc)

    db_path = tmp_path / "index.sqlite"
    count = build_index(store, db_path)
    assert count > 0

    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT source_id, license, usage_class, text FROM docs").fetchall()
    conn.close()
    assert len(rows) > 0
    assert rows[0][2] == "share-alike"


def test_export_excludes_disabled_sources(tmp_path):
    """C3: sources with enabled = false have no text/, no links/ stub, and are in sources.json['disabled']."""
    import json
    store = Store(tmp_path / "corpus")
    store.save(make_doc(source_id="pub", title="Active Public"))
    store.save(make_doc(source_id="dis", title="Disabled Source", usage_class="copyrighted-local"))

    sources = [
        source("pub", usage_class="public-domain"),
        source("dis", enabled=False, blocked_reason="wrong id (test)", usage_class="copyrighted-local"),
    ]
    out = tmp_path / "public_export"
    res = export_public(store, out, sources)
    assert res["guard_errors"] == []

    # Assert no text/ or links/ for disabled source
    assert (out / "text" / "pub").is_dir()
    assert not (out / "text" / "dis").exists()
    assert not (out / "links" / "dis.md").exists()

    # Assert listed in sources.json under 'disabled' and not 'sources'
    sources_data = json.loads((out / "sources.json").read_text())
    assert "dis" in sources_data["disabled"]
    assert sources_data["disabled"]["dis"]["blocked_reason"] == "wrong id (test)"
    assert "dis" not in sources_data["sources"]
    assert "pub" in sources_data["sources"]

    assert check_public_export(out, store=store) == []


def test_check_public_export_flags_disabled_sources_leak(tmp_path):
    """C3: check_public_export fails if disabled source has files under text/, stub in links/, or is in 'sources'."""
    import json
    store = Store(tmp_path / "corpus")
    store.save(make_doc(source_id="pub", title="Active Public"))
    store.save(make_doc(source_id="dis", title="Disabled Source", usage_class="copyrighted-local"))

    sources = [
        source("pub", usage_class="public-domain"),
        source("dis", enabled=False, blocked_reason="wrong id", usage_class="copyrighted-local"),
    ]
    out = tmp_path / "public_export"
    export_public(store, out, sources)

    # 1. Leaked dir under text/
    (out / "text" / "dis").mkdir(parents=True)
    (out / "text" / "dis" / "leak.md").write_text("leak")
    errors = check_public_export(out, store=store)
    assert any("disabled source 'dis' has content under text/" in e for e in errors)
    import shutil
    shutil.rmtree(out / "text" / "dis")

    # 2. Leaked stub under links/
    (out / "links" / "dis.md").write_text("stub")
    errors = check_public_export(out, store=store)
    assert any("disabled source 'dis' has link stub links/dis.md" in e for e in errors)
    (out / "links" / "dis.md").unlink()

    # 3. Listed under 'sources' in sources.json
    sources_json_path = out / "sources.json"
    data = json.loads(sources_json_path.read_text())
    data["sources"]["dis"] = {"id": "dis", "title": "Disabled"}
    sources_json_path.write_text(json.dumps(data, indent=2))
    errors = check_public_export(out, store=store)
    assert any("disabled source 'dis' is listed in sources.json under 'sources'" in e for e in errors)


def test_check_enforces_expect_title_contains(tmp_path):
    """C4: check fails if row title does not contain expect_title_contains (case-insensitive)."""
    store = Store(tmp_path / "corpus")
    doc = make_doc(
        source_id="arxiv_dagger",
        title="A Reduction of Imitation Learning and Structured Prediction to No-Regret Online Learning"
    )
    store.save(doc)

    cfg_file = tmp_path / "sources.toml"
    cfg_file.write_text("""
version = 1
[sources.arxiv_dagger]
id = "arxiv_dagger"
kind = "arxiv"
expect_title_contains = "Imitation Learning"
""")
    # Matches case-insensitively -> passes
    errors = run_check(store, repo_root=tmp_path, sources_path=cfg_file)
    assert not any("does not contain expected substring" in e for e in errors)

    # Substring mismatch -> fails
    cfg_file.write_text("""
version = 1
[sources.arxiv_dagger]
id = "arxiv_dagger"
kind = "arxiv"
expect_title_contains = "Reinforcement Learning"
""")
    errors = run_check(store, repo_root=tmp_path, sources_path=cfg_file)
    assert any("title 'A Reduction of Imitation Learning" in e and "Reinforcement Learning" in e for e in errors)


def test_pinned_restrictions_in_sources_toml():
    """D3: reads the real sources.toml and asserts restricted sources and overrides."""
    from gbg_corpus.cli import SOURCES_TOML
    from gbg_corpus.config import load_sources
    from gbg_corpus.model import RESTRICTED_CLASSES

    sources = load_sources(SOURCES_TOML)
    src_by_id = {s.id: s for s in sources}

    # 1. Pinned restricted sources
    pinned_restricted_ids = (
        "gb_test_roms", "ladx_disassembly", "speedrun_ladx",
        "sre_postmortem", "complexsystems"
    )
    for sid in pinned_restricted_ids:
        assert sid in src_by_id, f"pinned restricted source {sid} missing from sources.toml"
        src = src_by_id[sid]
        u_class = src.get("usage_class")
        assert u_class in RESTRICTED_CLASSES, (
            f"pinned source {sid} must be in a restricted class, got {u_class!r}"
        )

    # 2. Both D2 overrides exist and are restricted
    # pandocs: historical/** -> copyrighted-local
    assert "pandocs" in src_by_id
    pandocs = src_by_id["pandocs"]
    pandocs_overrides = pandocs.get("overrides", [])
    hist_ov = [ov for ov in pandocs_overrides if ov.get("path_glob") == "historical/**"]
    assert len(hist_ov) >= 1, "pandocs missing override for historical/**"
    assert hist_ov[0].get("usage_class") == "copyrighted-local"
    assert hist_ov[0].get("usage_class") in RESTRICTED_CLASSES
    assert "89f82b2181dac4e335bbbdd1451534e6b3a716cf/historical" in hist_ov[0].get("license_evidence_url", "")

    # giibiiadvance: **/*.txt -> copyrighted-local
    assert "giibiiadvance" in src_by_id
    gbadv = src_by_id["giibiiadvance"]
    gbadv_overrides = gbadv.get("overrides", [])
    txt_ov = [ov for ov in gbadv_overrides if ov.get("path_glob") == "**/*.txt"]
    assert len(txt_ov) >= 1, "giibiiadvance missing override for **/*.txt"
    assert txt_ov[0].get("usage_class") == "copyrighted-local"
    assert txt_ov[0].get("usage_class") in RESTRICTED_CLASSES
    assert "ccb40c3cf7d9efec538858a36d4ab69bb4d0ce5c" in txt_ov[0].get("license_evidence_url", "")


def test_apply_audit_per_path_overrides(tmp_path):
    """D1: apply_audit applies first matching override by path field, else source-level values."""
    from gbg_corpus.migrate import apply_audit

    store = Store(tmp_path / "corpus")
    doc_main = make_doc(source_id="pandocs", url="https://example.test/main", canonical_url="https://example.test/main",
                        title="Main Doc", text="main text", raw=b"main text",
                        usage_class="unknown", extra={"path": "docs/main.md"})
    doc_hist = make_doc(source_id="pandocs", url="https://example.test/hist", canonical_url="https://example.test/hist",
                        title="Old Doc", text="old text", raw=b"old text",
                        usage_class="unknown", extra={"path": "historical/old.txt"})
    store.save(doc_main)
    store.save(doc_hist)

    src = source(
        "pandocs",
        usage_class="public-domain",
        license="CC0-1.0",
        overrides=[{
            "path_glob": "historical/**",
            "usage_class": "copyrighted-local",
            "license": "none-declared",
            "license_evidence_url": "https://example.test/hist",
            "usage_notes": "Hist notes",
        }],
    )
    changed, warnings = apply_audit(store, [src])
    assert changed == 2

    rows = store.rows("pandocs")
    rows_by_title = {r["title"]: r for r in rows}
    assert rows_by_title["Main Doc"]["usage_class"] == "public-domain"
    assert rows_by_title["Old Doc"]["usage_class"] == "copyrighted-local"


def test_planted_historical_body_in_allowlisted_pandocs_is_caught(tmp_path):
    """D2.5: restricted historical body planted in an allowlisted text/pandocs file with updated sha256 is caught."""
    import hashlib
    import json
    store = Store()
    out = tmp_path / "export"
    from gbg_corpus.cli import SOURCES_TOML
    from gbg_corpus.config import load_sources
    sources = load_sources(SOURCES_TOML)
    res = export_public(store, out, sources)
    assert res["guard_errors"] == []

    # Plant historical/2001-Oct-pandocs.txt body into text/pandocs/cgb-registers.md
    hist_row = [r for r in store.rows("pandocs") if r.get("path") == "historical/2001-Oct-pandocs.txt"][0]
    hist_body = _read_body(store.root / hist_row["normalized_path"])

    target_file = out / "text" / "pandocs" / "cgb-registers.md"
    assert target_file.exists()
    target_file.write_text(f"---\nusage_class: public-domain\nlicense: CC0-1.0\n---\n\n> **License:** CC0-1.0 (public-domain).\n\n{hist_body}\n")

    # Update sha256 in sources.json so allowlist check passes
    sources_json_path = out / "sources.json"
    data = json.loads(sources_json_path.read_text())
    rel = "text/pandocs/cgb-registers.md"
    data["files"][rel] = hashlib.sha256(target_file.read_bytes()).hexdigest()
    sources_json_path.write_text(json.dumps(data, indent=2))

    # Because condition c fails (exported body does not match normalized body in store),
    # the allowance does not apply and the fingerprint scan catches it
    errors = check_public_export(out, store=store, sources=sources)
    assert any("shares" in e and "2001-Oct-pandocs" in e for e in errors)


def test_overlapping_publishable_row_without_declared_allowance_fails(tmp_path):
    """D2.5: publishable row whose body overlaps a restricted row with no declared allowance fails export."""
    store = Store(tmp_path / "corpus")
    shared_text = " ".join([f"common_word_{i}" for i in range(50)])
    doc_pub = make_doc(source_id="pub", title="Pub Doc", text=f"# Pub\n\n{shared_text}", raw=f"# Pub\n\n{shared_text}".encode(),
                       usage_class="public-domain", extra={"path": "src/pub.md"})
    doc_priv = make_doc(source_id="priv", title="Priv Doc", text=f"# Priv\n\n{shared_text}", raw=f"# Priv\n\n{shared_text}".encode(),
                        usage_class="nc-nd", extra={"path": "historical/priv.txt"})
    store.save(doc_pub)
    store.save(doc_priv)

    sources = [
        source("pub", usage_class="public-domain"),
        source("priv", usage_class="nc-nd"),
    ]
    out = tmp_path / "export"
    with pytest.raises(ExportGuardError):
        export_public(store, out, sources)


def test_overlapping_publishable_row_with_declared_allowance_passes(tmp_path):
    """D2.5: publishable row whose body overlaps a restricted row with a declared allowance passes export."""
    store = Store(tmp_path / "corpus")
    shared_text = " ".join([f"common_word_{i}" for i in range(50)])
    doc_pub = make_doc(source_id="pub", title="Pub Doc", text=f"# Pub\n\n{shared_text}", raw=f"# Pub\n\n{shared_text}".encode(),
                       usage_class="public-domain", extra={"path": "src/pub.md"})
    doc_priv = make_doc(source_id="priv", title="Priv Doc", text=f"# Priv\n\n{shared_text}", raw=f"# Priv\n\n{shared_text}".encode(),
                        usage_class="nc-nd", extra={"path": "historical/priv.txt"})
    store.save(doc_pub)
    store.save(doc_priv)

    sources = [
        source("pub", usage_class="public-domain", allowed_overlap=[{
            "public_glob": "src/**",
            "restricted_source": "priv",
            "restricted_glob": "historical/**",
            "reason": "Test allowed overlap.",
        }]),
        source("priv", usage_class="nc-nd"),
    ]
    out = tmp_path / "export"
    res = export_public(store, out, sources)
    assert res["guard_errors"] == []
    assert check_public_export(out, store=store, sources=sources) == []


def test_pinned_declared_allowances_in_sources_toml():
    """D2.5: pinned test listing declared allowances from real sources.toml."""
    from gbg_corpus.cli import SOURCES_TOML
    from gbg_corpus.config import load_sources

    sources = load_sources(SOURCES_TOML)
    src_by_id = {s.id: s for s in sources}

    # Only pandocs has declared allowances
    for sid, s in src_by_id.items():
        allowances = s.get("allowed_overlap", [])
        if sid == "pandocs":
            assert len(allowances) == 2, f"pandocs must have exactly 2 declared allowances, got {len(allowances)}"
            pairs = {(a["public_glob"], a["restricted_source"], a["restricted_glob"]) for a in allowances}
            expected_pairs = {
                ("src/**", "pandocs", "historical/**"),
                ("src/**", "giibiiadvance", "docs/other_docs/**"),
            }
            assert pairs == expected_pairs
            for a in allowances:
                assert a.get("reason"), "allowance must have a non-empty reason"
        else:
            assert len(allowances) == 0, f"source {sid} must not declare allowances"
