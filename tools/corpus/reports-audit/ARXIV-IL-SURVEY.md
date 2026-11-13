# arXiv Imitation Learning Survey Source Replacement Report

## VERIFIED

### Pre-Modification Store Mechanism Analysis
- **Behavior on different sha256 for existing source**: When fetching a single source (`gbg-corpus fetch --source <id>`), `Store.save(doc)` checks existing manifest rows for identical `(sha256, revision)` and `(canonical_url, revision)`. If neither matches, `save()` writes the raw document and normalized markdown and calls `self._append(row)`, which **appends** the new row to the source manifest (`manifests/<source_id>.jsonl`). It does not replace or skip.
- **Supported deletion command**: There is **no supported CLI command or Store method** in `gbg-corpus` to remove a manifest row together with its raw and normalized files.

### Backup Outside Git
Before modifying corpus files, the wrong paper files were backed up outside git to:
`/home/ben/.local/share/gbg-corpus/backups/arxiv_il_survey-20261113T194637Z/`

SHA-256 sums of backed-up files:
- `7d5eb4cc2118426cc768c05f40014b400cddd3b532c6f16024a94da6d715e944` `manifests/arxiv_il_survey.jsonl`
- `fc5c8d431c1365468c67259c44669afbbe6aa5fb500327355dcaab9354495482` `normalized/arxiv_il_survey/higher-dimensional-operators-in-2hdm.md`
- `be2c50d2b260123ff2e65ad79c983380638e1ad7aa6fa927c1a1d727d9eacc37` `raw/arxiv_il_survey/be2c50d2b260123ff2e65ad79c983380638e1ad7aa6fa927c1a1d727d9eacc37.xml`

### Step 2: Configuration Update
In `tools/corpus/sources.toml`, `[sources.arxiv_il_survey]` was updated:
- `arxiv_id = "2106.12177"`
- `enabled = true`
- Removed `blocked_reason`
- Added `expect_title_contains = "Imitation Learning"`
- `license = "CC0-1.0"`
- `usage_class = "public-domain"`
- `license_evidence_url = "https://info.arxiv.org/help/license/index.html"`
- `usage_notes = "Metadata and abstract only under the arXiv CC0 terms; the PDF is not mirrored."`

### Step 3: Network Fetch
Ran: `uv run gbg-corpus fetch --source arxiv_il_survey`
Output:
```text
[arxiv_il_survey] 1 new / 1 fetched
fetch complete: 1 sources ok, 0 failed
```
- Exactly one network request was made to arXiv API (`https://export.arxiv.org/api/query?id_list=2106.12177`).
- Returned title: `"Imitation Learning: Progress, Taxonomies and Challenges"`, matching the authorized title requirement.
- Authors: Boyuan Zheng, Sunny Verma, Jianlong Zhou, Ivor Tsang, Fang Chen.
- Published: `2021-06-23T05:55:33Z`, Revision: `v2`.
- Raw XML sha256: `a0212ae90a92d674c6c1682f00bd2be67337803326a15eb52f24fa73dde3a1ea`.

### Step 4: Retirement of Wrong Paper
Because no CLI removal command exists, the old row (`arxiv_id = 1707.00716`, sha256 `be2c50d2...`) was removed from `~/.local/share/gbg-corpus/manifests/arxiv_il_survey.jsonl`, and the two old files were deleted from the corpus store:
- Deleted: `~/.local/share/gbg-corpus/normalized/arxiv_il_survey/higher-dimensional-operators-in-2hdm.md`
- Deleted: `~/.local/share/gbg-corpus/raw/arxiv_il_survey/be2c50d2b260123ff2e65ad79c983380638e1ad7aa6fa927c1a1d727d9eacc37.xml`

Verification:
- Manifest row count: `wc -l ~/.local/share/gbg-corpus/manifests/arxiv_il_survey.jsonl` -> 1 row (for `2106.12177`).
- Files in normalized directory: `imitation-learning-progress-taxonomies-and-challenges.md` (1 file).
- Files in raw directory: `a0212ae90a92d674c6c1682f00bd2be67337803326a15eb52f24fa73dde3a1ea.xml` (1 file).

### Step 5: License Documentation Updates
- Updated `tools/corpus/licenses/arxiv_il_survey.txt` to CC0-1.0 public-domain attribution, pointing to `https://arxiv.org/abs/2106.12177` and `https://info.arxiv.org/help/license/index.html`.
- Updated `tools/corpus/LICENSES.md` audit table row and note for `arxiv_il_survey` matching `arxiv_dagger`'s treatment, removing the disabled note.

### Step 6: Acceptance Commands and Outputs

1. `uv run gbg-corpus audit --apply`
```text
audit: 0 rows updated from sources.toml
```

2. `uv run gbg-corpus check`
```text
check OK
```

3. `uv run gbg-corpus index`
```text
indexed 1218 chunks
```

4. `uv run gbg-corpus report`
```text
source                         docs        bytes  usage_class
----------------------------------------------------------------------------------------
arxiv_dagger                      1         2755  public-domain:1
arxiv_il_survey                   1         2562  public-domain:1
awesome_gbdev                     1        52651  share-alike:1
binjgb                            1         7755  permissive:1
complexsystems                    1        23713  copyrighted-local:1
copetti_gb                        1       153023  permissive:1
datacrystal_ladx                  3        90772  share-alike:3
gb_test_roms                      7        30329  copyrighted-local:7
giibiiadvance                     5       219374  copyrighted-local:5
ladx_disassembly                  7        20338  copyrighted-local:7
ladx_randomizer                   1         1292  permissive:1
mealybug                          1         5582  permissive:1
mooneye_gb                        1         9618  share-alike:1
nist_800_61                       1       108379  public-domain:1
pandocs                          82       837879  copyrighted-local:6, public-domain:76
sameboy                           5        35546  permissive:5
speedrun_ladx                    12       136478  copyrighted-local:12
sre_postmortem                    1        55113  nc-nd:1
tasvideos_ladx                    1        26779  permissive:1
tcrf_ladx                         1       103763  permissive:1
zeldawiki_ladx                    1         9593  share-alike:1
----------------------------------------------------------------------------------------
TOTAL                           135      1933294  failures:4 (unresolved:0) duplicates:1

usage_class breakdown
  public-domain         79
  permissive            11
  share-alike            6
  nc-nd                  1
  copyrighted-local     38
  unknown                0
  restricted            39  (nc-nd + copyrighted-local + unknown)

freshness: 7 docs older than 180 days (oldest 10543 days)

wrote /var/home/ben/Developer/GameBoyGhost/reports/corpus/report.json
```

5. `uv run pytest`
```text
...............................................                          [100%]
47 passed in 1.64s
```

6. `rm -rf /tmp/gbg-public && uv run gbg-corpus export --public --out /tmp/gbg-public`
```text
wrote public export to /tmp/gbg-public
sources: 21; documents: public-domain=79, permissive=11, share-alike=6, nc-nd=1, copyrighted-local=38
export guard OK: no restricted body text
```

7. `uv run gbg-corpus export --check /tmp/gbg-public`
```text
export check OK
```

8. `uv run gbg-corpus check --public-out /tmp/gbg-public`
```text
check OK
```

### Arithmetic
- Manifest rows:
  - Total: 135 rows (unchanged: 1 row retired, 1 row added).
  - `public-domain`: 79 (was 78; +1 `arxiv_il_survey`).
  - `permissive`: 11 (was 12; -1 retired `arxiv_il_survey`).
  - `share-alike`: 6 (unchanged).
  - `nc-nd`: 1 (unchanged).
  - `copyrighted-local`: 38 (unchanged).
- Clean export (`/tmp/gbg-public`):
  - Sources in `sources.json`: 21 (was 20; `arxiv_il_survey` re-enabled).
  - Bodies in `text/`: 96 markdown files (was 95; +1 `arxiv_il_survey` public-domain body).
  - Stubs in `links/`: 7 markdown files (unchanged).
  - Disabled sources in `sources.json["disabled"]`: 0 (was 1; `disabled = {}`).

## INFERRED

- Enabling `arxiv_il_survey` as CC0-1.0 / `public-domain` allows it to export cleanly to `text/arxiv_il_survey/imitation-learning-progress-taxonomies-and-challenges.md` alongside its `LICENSE.txt` without tripping any restricted shingle overlap or leak checks.

## Unknown / not established

- Whether the author-written abstract text changed between arXiv versions v1 and v2 for paper 2106.12177 (arXiv API returned v2 metadata).

## Evidence limits

- Verification confirmed that the metadata and abstract match paper 2106.12177; full PDF contents are intentionally not retrieved or mirrored under CC0-1.0 metadata-only scope.

## Files changed

- `reports/corpus/report.json`: Updated corpus report with 79 public-domain / 11 permissive documents and updated `arxiv_il_survey` metadata.
- `tools/corpus/LICENSES.md`: Updated `arxiv_il_survey` audit table row and note to CC0-1.0 public-domain metadata grant.
- `tools/corpus/licenses/arxiv_il_survey.txt`: Updated license notice to CC0-1.0 public-domain attribution for arXiv 2106.12177.
- `tools/corpus/sources.toml`: Updated `arxiv_il_survey` to arXiv ID 2106.12177, enabled, CC0-1.0 public-domain, and added title check.
- `tools/corpus/reports-audit/ARXIV-IL-SURVEY.md`: Audit report for source replacement and verification.

## Suggested commit message

```text
corpus: replace arxiv_il_survey with 2106.12177 (CC0-1.0 metadata)
```

## Final status

```sh
$ git rev-parse HEAD
5b3f9046d531e8fe538da63d51c3df3e55c070a2

$ git status --short
 M reports/corpus/report.json
 M tools/corpus/LICENSES.md
 M tools/corpus/licenses/arxiv_il_survey.txt
 M tools/corpus/sources.toml
?? brand/
?? tools/corpus/reports-audit/ARXIV-IL-SURVEY.md
```
