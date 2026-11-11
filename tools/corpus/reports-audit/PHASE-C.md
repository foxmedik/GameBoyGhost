# Phase C Report: arXiv Sources Reclassification, Exclusion, and Title Integrity

## VERIFIED

### C1 / C2 Configuration and Audit Updates
- `arxiv_dagger` updated:
  - `sources.toml`: `license = "CC0-1.0"`, `usage_class = "public-domain"`, `license_evidence_url = "https://info.arxiv.org/help/license/index.html"`, `usage_notes = "Metadata and abstract only under the arXiv CC0 terms; the PDF is not mirrored."`, `expect_title_contains = "Imitation Learning"`.
  - `licenses/arxiv_dagger.txt`: Updated to CC0-1.0 public-domain attribution and terms evidence.
  - `LICENSES.md`: Row and notes updated to CC0-1.0 public-domain metadata grant.
- `arxiv_il_survey` disabled:
  - `sources.toml`: `enabled = false`, `blocked_reason = "wrong arXiv id (1707.00716 is 'Higher dimensional operators in 2HDM'); correct id pending"`.
  - `LICENSES.md`: Marked disabled with reason.
- `apply_audit`:
  - Updated to skip sources where `enabled = false`.
  - On `uv run gbg-corpus audit --apply`, updated `arxiv_dagger` manifest row from `permissive` to `public-domain` and synced its normalized markdown front matter.

### C3 Disabled Source Export Exclusion
- `export_public`:
  - Excludes disabled sources from `text/` (no directory or files written).
  - Excludes disabled sources from `links/` (no metadata stub written).
  - Excludes disabled sources from `sources.json["sources"]`.
  - Records disabled sources under `sources.json["disabled"]` with `id`, `title`, and `blocked_reason`.
- `check_public_export`:
  - Fails if any disabled source exists under `text/`, has a link stub in `links/`, or is listed in `sources.json["sources"]`.
  - Excludes disabled sources from manifest recomputation when `store` is provided.

### C4 `expect_title_contains` Guard
- Added optional `expect_title_contains` checking in `check.py` against `sources.toml` entries (case-insensitive).
- Configured:
  - `arxiv_dagger`: `"Imitation Learning"` (matches `"A Reduction of Imitation Learning and Structured Prediction to No-Regret Online Learning"`).
  - `nist_800_61`: `"Incident Response"` (matches `"Incident Response Recommendations and Considerations for Cybersecurity Risk Management: A CSF 2.0 Community Profile"`).
- `gbg-corpus check` passes.
- Tested: `check` fails if a row's title does not contain the expected substring.

### C5 Acceptance Commands Output
```sh
$ cd tools/corpus

$ uv run gbg-corpus audit --apply
front matter: 1 files updated
audit: 1 rows updated from sources.toml

$ uv run gbg-corpus check
check OK

$ uv run pytest -q
.........................................                                [100%]
41 passed in 0.73s

$ uv run gbg-corpus export --public --out /tmp/gbg-public
wrote public export to /tmp/gbg-public
sources: 20; classes: public-domain=3, permissive=7, share-alike=5, nc-nd=1, copyrighted-local=4
export guard OK: no restricted body text

$ uv run gbg-corpus export --check /tmp/gbg-public
export check OK
```

Export metrics verification:
- Active exported sources: 20 (was 21; `arxiv_il_survey` excluded from `sources` and written to `disabled`).
- Usage class breakdown: `public-domain=3` (added `arxiv_dagger`), `permissive=7` (`arxiv_dagger` moved to public-domain; `arxiv_il_survey` disabled), `share-alike=5`, `nc-nd=1`, `copyrighted-local=4`.
- `/tmp/gbg-public/sources.json` contains:
  ```json
  "disabled": {
    "arxiv_il_survey": {
      "id": "arxiv_il_survey",
      "title": "arxiv_il_survey",
      "blocked_reason": "wrong arXiv id (1707.00716 is 'Higher dimensional operators in 2HDM'); correct id pending"
    }
  }
  ```
- Neither `text/arxiv_il_survey` nor `links/arxiv_il_survey.md` exists.

## INFERRED

- Using `expect_title_contains` prevents accidental ingestion of unrelated papers or mismatched IDs across upstream repos/APIs before files are processed.

## Unknown / not established

- The correct arXiv ID for the intended imitation learning survey (intentionally unselected per instruction C2).

## Evidence limits

- `expect_title_contains` tests substring presence in document titles; it does not evaluate the paper's full topic or abstract contents.

## Files changed

- `tools/corpus/sources.toml`: Reclassify `arxiv_dagger` to CC0-1.0 / public-domain, disable `arxiv_il_survey` with blocked reason, and add `expect_title_contains` to `arxiv_dagger` and `nist_800_61`.
- `tools/corpus/licenses/arxiv_dagger.txt`: Update license notice to CC0-1.0 public domain.
- `tools/corpus/LICENSES.md`: Update audit rows and explanatory notes for `arxiv_dagger` and `arxiv_il_survey`.
- `tools/corpus/src/gbg_corpus/check.py`: Add `expect_title_contains` validation against `sources.toml`.
- `tools/corpus/src/gbg_corpus/export.py`: Exclude disabled sources from public exports and validate in `check_public_export`.
- `tools/corpus/src/gbg_corpus/migrate.py`: Skip disabled sources during `apply_audit()`.
- `tools/corpus/tests/test_governance.py`: Add tests for disabled source exclusion and `expect_title_contains` validation.
- `tools/corpus/reports-audit/PHASE-C.md`: Phase C audit report.

## Suggested commit message

```text
corpus: reclassify arxiv_dagger, disable arxiv_il_survey, add title checks (Phase C)
```

## Final status

```sh
$ git rev-parse HEAD
30b421180f4d6b2b45ff727efbcc3c2686e3f392

$ git status --short
 M tools/corpus/LICENSES.md
 M tools/corpus/licenses/arxiv_dagger.txt
 M tools/corpus/sources.toml
 M tools/corpus/src/gbg_corpus/check.py
 M tools/corpus/src/gbg_corpus/export.py
 M tools/corpus/src/gbg_corpus/migrate.py
 M tools/corpus/tests/test_governance.py
?? brand/
?? tools/corpus/reports-audit/PHASE-C.md
```
