from __future__ import annotations

import json
from pathlib import Path

import pytest

from gbg_corpus.adapters import parse_wayback_cdx, wayback_id_url
from gbg_corpus.config import Source
from gbg_corpus.export import check_public_export, export_public
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
    assert check_public_export(out) == []


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
