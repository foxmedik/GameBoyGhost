from __future__ import annotations

import json
from pathlib import Path

import pytest

from gbg_corpus.adapters import parse_wayback_cdx, wayback_id_url
from gbg_corpus.config import Source
from gbg_corpus.export import ExportGuardError, check_public_export, export_public
from gbg_corpus.migrate import migrate_add_usage_class
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
