from __future__ import annotations

import json
from pathlib import Path

from gbg_corpus.adapters import _matches, parse_mediawiki
from gbg_corpus.check import check
from gbg_corpus.dedup import is_near_duplicate, simhash
from gbg_corpus.model import Document
from gbg_corpus.normalize import chunk_markdown, html_to_markdown
from gbg_corpus.store import Store, sha256_bytes

FIX = Path(__file__).parent / "fixtures"


def make_doc(**kw) -> Document:
    base = dict(
        source_id="test", kind="html_article", url="https://example.test/a",
        canonical_url="https://example.test/a", title="Test", text="# Test\n\nhello",
        raw=b"# Test\n\nhello", ext="md", license="unknown", revision="r1",
    )
    base.update(kw)
    return Document(**base)


def test_hash_stability():
    assert sha256_bytes(b"abc") == sha256_bytes(b"abc")
    assert sha256_bytes(b"abc") != sha256_bytes(b"abd")


def test_manifest_schema(tmp_path):
    store = Store(tmp_path / "corpus")
    row = store.save(make_doc())
    assert row is not None
    required = {"source_id", "kind", "url", "canonical_url", "title", "retrieved_at",
                "license", "revision", "http_status", "content_type", "sha256",
                "normalized_path", "duplicate_of", "parser_version"}
    assert required <= set(row)
    assert (store.root / row["normalized_path"]).exists()
    assert (store.root / row["raw_path"]).read_bytes() == b"# Test\n\nhello"


def test_idempotent_same_sha_and_revision(tmp_path):
    store = Store(tmp_path / "corpus")
    assert store.save(make_doc()) is not None
    assert store.save(make_doc()) is None
    # different revision is a new document
    assert store.save(make_doc(revision="r2")) is not None


def test_mediawiki_raw_parsing():
    data = json.loads((FIX / "mediawiki.json").read_text())
    doc = parse_mediawiki(data, "https://tcrf.net/api.php",
                          "The Legend of Zelda: Link's Awakening DX", "wikitext",
                          "tcrf_ladx", "mediawiki", "unknown")
    assert doc.revision == "987654"
    assert "RAM map" in doc.text
    assert doc.canonical_url.startswith("https://tcrf.net/wiki/")


def test_github_path_filtering():
    include = ["**/*.md", "README.md"]
    exclude = ["**/.github/**"]
    assert _matches("docs/a.md", include, exclude)
    assert _matches("README.md", include, exclude)
    assert not _matches("src/main.c", include, exclude)
    assert not _matches(".github/workflows/ci.md", include, exclude)
    assert not _matches("roms/game.gb", include, exclude)


def test_dedup_near_duplicates():
    a = "the game boy has a sharp lr35902 cpu running at four point one nine mhz"
    b = "the game boy has a sharp lr35902 cpu running at four point one nine mhz today"
    c = "completely different text about postmortems and incident review culture"
    assert is_near_duplicate(simhash(a), simhash(b))
    assert not is_near_duplicate(simhash(a), simhash(c))


def test_banned_extension_refused(tmp_path):
    store = Store(tmp_path / "corpus")
    row = store.save(make_doc(ext="gb", raw=b"\x00\x01"))
    assert row is None
    assert "banned extension" in store.failures_path.read_text()


def test_check_flags_banned_domain(tmp_path):
    store = Store(tmp_path / "corpus")
    store.save(make_doc(url="https://discord.com/channels/1/2",
                        canonical_url="https://discord.com/channels/1/2"))
    errors = check(store, tmp_path / "repo")
    assert any("banned domain" in e for e in errors)


def test_prompt_injection_is_stored_not_executed(tmp_path):
    text = (FIX / "prompt_injection.txt").read_text()
    store = Store(tmp_path / "corpus")
    row = store.save(make_doc(title="Injection", text=text, raw=text.encode()))
    assert row is not None
    stored = (store.root / row["normalized_path"]).read_text()
    assert "ignore previous instructions" in stored
    assert "rm -rf /" in stored  # stored, not run


def test_chunk_heading_path():
    md = "# A\n\nalpha text\n\n## B\n\nbeta text\n"
    chunks = chunk_markdown(md, target_tokens=50)
    paths = [c["heading_path"] for c in chunks]
    assert ["A"] in paths
    assert ["A", "B"] in paths


def test_html_extraction_drops_nav():
    html = (FIX / "article.html").read_text()
    text, meta = html_to_markdown(html, "https://example.test/game-boy")
    assert "LR35902" in text
    assert "ignore me" not in text
