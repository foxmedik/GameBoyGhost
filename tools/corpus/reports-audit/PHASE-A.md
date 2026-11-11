# Phase A Report: Content-Based Export Guard

## VERIFIED

- Preflight Step 2:
  ```
  $ git rev-parse HEAD ; git status --short ; git branch --show-current
  c7f5ed3a240bd38a1e6548d0b48639aa610d9176
  ?? brand/
  corpus-governance
  ```
- Preflight Step 3:
  ```
  $ uv run gbg-corpus check && uv run pytest -q
  check OK
  ..................                                                       [100%]
  ```
- Preflight Step 5 Backup:
  - Backup path: `/home/ben/.local/share/gbg-corpus-backup-20261110-1843`
  - `manifests` tar sha256: `a96c955397724710ecd13be381bc65831277788cdfaa3dae05a30d5e6e92c1f0`
  - `normalized` tar sha256: `8c90f06aa97fe87e869a893c40dad1cb3cae15b4f23fef9b60b41afa7f46c10a`
  - Normalized files verified byte-identical before and after Phase A.
- Shingle Overlap Measurement (A3):
  - Clean export (107 text documents, 5 link stubs, `README.md`, `sources.json`) measured against all 28 restricted documents (13,767 total 12-word shingles).
  - 106 exported files had 0 shared shingles with any restricted document.
  - 1 exported file (`text/giibiiadvance/game-boy-sound-operation.md`) had 1 shared shingle with `gb_test_roms` due to repeated ASCII markdown divider lines (`- - - - - - - - - - - -`).
  - Max overlap across all files: 1 shingle.
  - Selected threshold: `SHINGLE_THRESHOLD = 3` (minimum threshold passing a clean export with a margin of 2; a 300-word leak produces ~289 shared shingles).
- Leak variants tested (A7 / EXAMPLES Section 1):
  1. `text/pub/leak.md`, no front matter -> caught (allowlist + shingle fingerprint).
  2. `text/pub/leak.md`, front matter claiming `usage_class: public-domain` -> caught (allowlist + shingle fingerprint).
  3. `text/pub/leak.md`, restricted document's own normalized file -> caught (allowlist + shingle fingerprint + front matter).
  4. `text/pub/leak.md`, front matter `usage_class: 'nc-nd'` (quoted) -> caught (allowlist + shingle fingerprint + front matter regex).
  5. `text/pub/leak.md`, front matter block larger than 4096 bytes -> caught (allowlist + shingle fingerprint + front matter).
  6. Appended to `links/priv.md` -> caught (sha256 mismatch + shingle fingerprint).
  7. `extra.md` at export root -> caught (allowlist).
  8. `text/misc/leak.md` (directory not a source id) -> caught (allowlist + shingle fingerprint).
  9. `text/priv.txt` (file under text/) -> caught (allowlist + non-directory check + shingle fingerprint).
  10. `text/PRIV/leak.md` (case variant) -> caught (allowlist + shingle fingerprint).
  11. `sources.json` with "priv" entry removed -> caught cleanly without raising; returns errors list.
- A6 Guard failure directory cleanup:
  - Output directory is removed via `shutil.rmtree` before raising `ExportGuardError`.
- Acceptance Commands:
  ```
  $ uv run pytest -q
  .............................                                            [100%]
  29 passed in 0.47s

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

- Threshold of 3 shingles leaves sufficient margin for clean exports while offering robust detection of multi-word excerpts and whole-body leaks.
- Recomputing the expected file set from the store manifests closes any gap where an adversary or bug could add unauthorized files to `sources.json` allowlist.

## Unknown / not established

- Whether future sources added to the corpus might introduce novel formatting constructs with 3 or more consecutive common 12-word sequences (e.g. large identical tables or ASCII art).

## Evidence limits

- Shingle checking detects exact sequence matches of 12-word shingles; it is not designed to detect semantic paraphrasing or lossy summarization.
- Fingerprints are generated from local normalized files in the store; untracked or unmanifested files outside the store cannot be fingerprinted.

## Files changed

- `tools/corpus/src/gbg_corpus/export.py`: Per-document export decision, 12-word shingle hashing, file allowlist in `sources.json`, safe sources lookup, and directory cleanup on failure.
- `tools/corpus/src/gbg_corpus/cli.py`: Remove `--fail-on-restricted` option and handle guard errors cleanly.
- `tools/corpus/tests/test_governance.py`: Add 11 leak variant tests covering EXAMPLES Section 1 and test cleanup on guard failure.
- `tools/corpus/reports-audit/PHASE-A.md`: Audit report for Phase A.

## Suggested commit message

```text
corpus: content-based export guard and file allowlist (Phase A)
```

## Final status

```
$ git rev-parse HEAD
c7f5ed3a240bd38a1e6548d0b48639aa610d9176

$ git status --short
 M tools/corpus/src/gbg_corpus/cli.py
 M tools/corpus/src/gbg_corpus/export.py
 M tools/corpus/tests/test_governance.py
?? brand/
?? tools/corpus/reports-audit/
```
