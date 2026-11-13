# Phase B Report: Front Matter in Sync with Manifests

## VERIFIED

### Acceptance Commands Output
```sh
$ cd tools/corpus

$ uv run gbg-corpus audit --apply
front matter: 130 files updated
audit: 0 rows updated from sources.toml

$ uv run gbg-corpus check
check OK

$ uv run gbg-corpus index
indexed 1218 chunks

$ uv run pytest -q
......................................                                   [100%]
38 passed in 0.52s
```

### B1 / B4 Normalized File Counts and Body Hash Comparison
- **Normalized files changed:** Exactly 130 files updated on the initial `audit --apply` pass (matching the expected 130 legacy files lacking `usage_class` in front matter; the remaining 5 files already carried valid governance front matter).
- **Idempotency:** A subsequent run of `uv run gbg-corpus audit --apply` resulted in `audit: 0 rows updated from sources.toml` and 0 normalized files updated.
- **Before / After Body Hash Verification:**
  - Evaluated all 135 normalized files comparing backup `/home/ben/.local/share/gbg-corpus-backup-20261110-1843/normalized` against active `~/.local/share/gbg-corpus/normalized`.
  - Body bytes extracted after the YAML front matter block (`parts[2]`).
  - Total files compared: 135
  - Matching body SHA-256 hashes: **135 / 135 (100%)**
  - Mismatches: **0**
  - No document body bytes were altered by the front matter synchronization.

### B2 Front Matter Validation in `check`
- Updated `check.py` to compare normalized file front matter against manifest rows for all 7 governance fields: `license`, `usage_class`, `license_evidence_url`, `usage_notes`, `retrieved_via`, `snapshot_at`, `snapshot_url`.
- Tested in `test_check_fails_on_front_matter_mismatch`: Hand-editing `license: MIT` to `license: GPL-3.0` in a normalized file causes `check` to fail with `front matter mismatch`.

### B3 SQLite Index `usage_class` Column
- Updated `SCHEMA` in `index.py` to add `usage_class TEXT NOT NULL` to the `docs` table.
- Updated `build_index()` to insert the manifest row's `usage_class`.
- Verified `~/.local/share/gbg-corpus/index.sqlite`:
  ```
  Columns in docs table: ['id', 'source_id', 'kind', 'url', 'title', 'heading_path', 'chunk_index', 'sha256', 'license', 'usage_class', 'text']
  Docs breakdown by usage_class:
    copyrighted-local: 82
    nc-nd: 10
    permissive: 219
    public-domain: 746
    share-alike: 161
  ```
- Tested in `test_index_includes_usage_class_column`.

## INFERRED

- Syncing front matter directly from manifest rows guarantees that any future license finding or class migration applied via `audit --apply` will propagate deterministically to the markdown file headers without modifying document content.

## Unknown / not established

- Whether external consumers of `$GBG_CORPUS_DIR/index.sqlite` expect the legacy 10-column table schema (FTS virtual table `docs_fts` structure remains unchanged and binary queries continue to function).

## Evidence limits

- Body hash equality proves that whitespace and text following the second `---` fence remained byte-identical for all 135 documents; it does not validate semantic correctness of the YAML metadata itself (which is validated against manifest rows).

## Files changed

- `tools/corpus/src/gbg_corpus/migrate.py`: Implement `sync_normalized_front_matter()` to update front matter from manifest rows while asserting body byte immutability; invoke from `apply_audit()`.
- `tools/corpus/src/gbg_corpus/check.py`: Validate that normalized files contain front matter agreeing with manifest rows across all 7 governance fields.
- `tools/corpus/src/gbg_corpus/index.py`: Add `usage_class TEXT NOT NULL` column to `docs` table in `index.sqlite` and insert manifest class.
- `tools/corpus/tests/test_governance.py`: Added tests for idempotent front-matter sync with body hash preservation, mismatch detection in `check`, and index `usage_class` column.
- `tools/corpus/reports-audit/PHASE-B.md`: Phase B audit report.

## Suggested commit message

```text
corpus: sync normalized front matter from manifests and add index usage_class (Phase B)
```

## Final status

```sh
$ git rev-parse HEAD
5f2dc0d9bfe24242ac3fbf2b6e605dff851e56e3

$ git status --short
 M tools/corpus/src/gbg_corpus/check.py
 M tools/corpus/src/gbg_corpus/index.py
 M tools/corpus/src/gbg_corpus/migrate.py
 M tools/corpus/tests/test_governance.py
?? brand/
?? tools/corpus/reports-audit/PHASE-B.md
```
