# Phase A2 Report: Shingle Hardening, No-Store Guard, and Independence

## VERIFIED

### A2.1 Independence Tests
- Tested planted leak in an allowlisted file with updated SHA-256 (`test_fingerprint_scan_catches_leak_when_allowlist_passes`):
  - Planted `PRIV_BODY` into existing `text/pub/public-guide.md` with valid front matter.
  - Recomputed SHA-256 and updated `sources.json["files"]["text/pub/public-guide.md"]`.
  - Verified: Allowlist checks pass (0 allowlist or hash mismatch errors). Store manifest check passes. Shingle fingerprint scan alone flags the leak (`shares N shingles with restricted document`).
- Tested mirror scenario (`test_allowlist_alone_catches_extra_file_when_fingerprint_scan_empty`):
  - Exported a store with an empty restricted set (no restricted documents).
  - Planted `extra.md` into the export.
  - Verified: Shingle fingerprint scan is clean (0 shared shingles). File allowlist alone flags the untracked file (`file not in sources.json allowlist: extra.md`).

### A2.2 No-Store Behaviour
- Previous behaviour: When `store=None`, `check_public_export` bypassed manifest cross-checks and shingle fingerprint scanning, returning `[]` on an otherwise intact export.
- Updated behaviour: When `store=None`, `check_public_export` immediately appends `"store not provided: content fingerprint scan and manifest verification could not run"` and never returns an empty list. Tested in `test_check_public_export_requires_store`.
- Call site audit:
  1. `tools/corpus/src/gbg_corpus/export.py:199` (`export_public`): passes `store=store` (Store instance).
  2. `tools/corpus/src/gbg_corpus/cli.py:86` (`cmd_check`): passes `store=store` (`Store()`).
  3. `tools/corpus/src/gbg_corpus/cli.py:134` (`cmd_export`): passes `store=Store()`.
  4. `tools/corpus/tests/test_governance.py`: all tests verifying export validity now supply `store=store`.

### A2.3 Tokenization Hardening
- Previous tokenizer: `text.lower().split()` (whitespace splitting; preserved punctuation, markdown formatting characters like `#`, `*`, `>`, and dashed divider lines like `- - -`).
- Updated tokenizer: `re.compile(r"\w+").findall(text.lower())` (extracts lowercase alphanumeric character runs; markdown symbols, punctuation, and divider dashes are ignored).
- Clean export re-measurement:
  - Scanned all clean export files against all 28 restricted documents (13,767 total 12-word shingles).
  - Previous max overlap: 1 shingle (due to `- - - - - - - - - - - -` divider lines).
  - **New max overlap: 0 shingles** across all 107 exported text documents and 5 metadata stubs.
- Tested altered formatting (`test_shingles_catch_leak_with_stripped_markdown_and_altered_punctuation`):
  - Stripped markdown markers, injected punctuation (`!`, `?`, `,`), and added asterisks around words.
  - Verified: Shingle fingerprint scan still matches alphanumeric runs and flags the leak.

### A2.4 Test Inventory (35 Total Tests)

`tests/test_corpus.py` (11 tests):
1. `test_hash_stability`
2. `test_manifest_schema`
3. `test_idempotent_same_sha_and_revision`
4. `test_mediawiki_raw_parsing`
5. `test_github_path_filtering`
6. `test_dedup_near_duplicates`
7. `test_banned_extension_refused`
8. `test_check_flags_banned_domain`
9. `test_prompt_injection_is_stored_not_executed`
10. `test_chunk_heading_path`
11. `test_html_extraction_drops_nav`

`tests/test_governance.py` (24 tests):
12. `test_usage_class_enum_validation`
13. `test_manifest_migration_is_idempotent`
14. `test_export_public_excludes_restricted_bodies`
15. `test_clean_export_returns_no_errors` -> **explicitly asserts that a clean export returns no errors**
16. `test_guard_failure_deletes_output_directory` -> **explicitly covers output-directory cleanup on guard failure**
17. `test_check_fails_when_restricted_body_under_text`
18. `test_magic_byte_sniff_rejects_fake_markdown_zip`
19. `test_max_size_rejection`
20. `test_wayback_cdx_fixture_builds_id_url`
21. `test_leak_variant_01_no_front_matter`
22. `test_leak_variant_02_front_matter_public_domain`
23. `test_leak_variant_03_own_normalized_file`
24. `test_leak_variant_04_quoted_usage_class`
25. `test_leak_variant_05_oversized_front_matter`
26. `test_leak_variant_06_appended_to_links`
27. `test_leak_variant_07_extra_file_at_root`
28. `test_leak_variant_08_invalid_directory`
29. `test_leak_variant_09_file_under_text`
30. `test_leak_variant_10_case_variant_directory`
31. `test_leak_variant_11_sources_json_priv_removed`
32. `test_fingerprint_scan_catches_leak_when_allowlist_passes` (A2.1)
33. `test_allowlist_alone_catches_extra_file_when_fingerprint_scan_empty` (A2.1 mirror)
34. `test_check_public_export_requires_store` (A2.2)
35. `test_shingles_catch_leak_with_stripped_markdown_and_altered_punctuation` (A2.3)

### A2.5 Acceptance Commands Output
```sh
$ uv run pytest -q
...................................                                      [100%]
35 passed in 0.55s

$ uv run gbg-corpus export --public --out /tmp/gbg-public
wrote public export to /tmp/gbg-public
sources: 21; classes: public-domain=2, permissive=9, share-alike=5, nc-nd=1, copyrighted-local=4
export guard OK: no restricted body text

$ uv run gbg-corpus export --check /tmp/gbg-public
export check OK

$ uv run gbg-corpus check --public-out /tmp/gbg-public
check OK
```

## INFERRED

- Extracting `\w+` alphanumeric runs decouples shingle computation from source markdown formatting variants, making the scan resilient against punctuation modification, line breaking, and markdown reformatting.
- Enforcing `store is not None` ensures that public export verification cannot be executed in a degraded bypass mode without content scanning.

## Unknown / not established

- Whether non-English or Unicode-segmented documents in future expansion would require specialized locale-aware word boundary tokenization (current sources are ASCII / English).

## Evidence limits

- **Detection window:** With threshold 3 and 12-word shingles, a verbatim excerpt of 13 words or fewer produces at most 2 shingles and is not detected (12 words = 1 shingle, 13 words = 2 shingles, 14 words = 3 shingles). Restricted documents shorter than 14 words cannot trigger the scan.
- **Corpus document lengths:**
  - Shortest restricted document: `ladx_disassembly: Photo pictures` with **101 words** (produces 90 shingles).
  - Second shortest restricted document: `ladx_disassembly: Notes on entities` with **201 words** (produces 190 shingles).
  - Longest restricted document: `speedrun_ladx: Speedrun.com game pdvj2vdw` with **4,220 words**.
  - All 28 restricted documents in the current corpus exceed 100 words, well above the 14-word detection threshold.

## Files changed

- `tools/corpus/src/gbg_corpus/export.py`: Alphanumeric `\w+` shingle tokenizer and enforcement of `store` requirement in `check_public_export`.
- `tools/corpus/tests/test_governance.py`: Added independence tests, no-store test, tokenizer resilience test, explicit clean export test, and explicit guard failure cleanup test.
- `tools/corpus/reports-audit/PHASE-A2.md`: Phase A2 audit report.

## Suggested commit message

```text
corpus: shingle tokenization hardening, no-store guard, and independence tests (Phase A2)
```

## Final status

```sh
$ git rev-parse HEAD
ddd1c71730f9ec129f6757cc68898dec51b6abe7

$ git status --short
 M tools/corpus/src/gbg_corpus/export.py
 M tools/corpus/tests/test_governance.py
?? brand/
?? tools/corpus/reports-audit/PHASE-A2.md
```
