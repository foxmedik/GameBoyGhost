# gbg-corpus — GameBoyGhost reference corpus

Reference material only. **This corpus is never training data** and is physically
separate from `data/train`, `data/eval`, and `reports/` (except the generated
`reports/corpus/`). The repo holds code, config, tests, a commit lock, the
license audit, and the report; raw bytes and normalized text live in
`$GBG_CORPUS_DIR` (default `~/.local/share/gbg-corpus`).

Every document carries a usage class and the evidence behind it. The public
export can only emit body text for `public-domain`, `permissive`, and
`share-alike` sources; everything else is a metadata-only link.

## Setup

Python 3.12 + uv, no system packages:

```bash
cd tools/corpus
uv sync --python 3.12
```

`GITHUB_TOKEN` is optional; if unset the tool falls back to `gh auth token`.
Without a token the GitHub API is limited to 60 requests/hour.

## Commands

```bash
uv run gbg-corpus fetch --priority P0      # fetch every enabled P0 source
uv run gbg-corpus fetch --source pandocs   # one source
uv run gbg-corpus migrate --add-usage-class # one-time schema backfill (idempotent)
uv run gbg-corpus audit --apply            # copy audited license metadata from sources.toml
uv run gbg-corpus check                    # manifests, hashes, governance fields, banned content
uv run gbg-corpus export --public --out public/  # guarded public export
uv run gbg-corpus export --check public/   # re-check an existing export
uv run gbg-corpus check --public-out public/     # check corpus + export together
uv run gbg-corpus report                   # writes reports/corpus/report.json
uv run gbg-corpus index                    # rebuild $GBG_CORPUS_DIR/index.sqlite
uv run pytest                              # offline tests
```

## Usage classes

| Class | Meaning | Public body text? |
|---|---|---|
| public-domain | Explicit public-domain dedication or US government work | yes |
| permissive | MIT/BSD/Apache/CC-BY; attribution and notice | yes |
| share-alike | GPL/AGPL/CC-BY-SA/GFDL; attribution, notice, no relicensing | yes, with notice |
| nc-nd | Non-commercial / no-derivatives | no |
| copyrighted-local | No reuse grant, or a derivative of copyrighted game code/assets | no |
| unknown | Not yet audited; treated as copyrighted-local | no |

The manifest row records `usage_class`, `license_evidence_url`, `usage_notes`,
`license`, `retrieved_via` (`direct`/`wayback`/`manual`), `snapshot_at`, and
`snapshot_url`. A source with no explicit grant is `copyrighted-local`, never
`unknown`. `unknown` means "not audited yet".

`LICENSES.md` is the human-readable audit: one row per source with the URL,
license string, class, evidence URL, and publish rule. `licenses/` holds the
license notices copied next to exported text.

## Storage layout

```
$GBG_CORPUS_DIR/                    # default ~/.local/share/gbg-corpus
  raw/<source_id>/<sha256>.<ext>
  raw/manual/                       # auditable manual browser saves (sidecar note)
  normalized/<source_id>/<slug>.md  # YAML front matter + verbatim text
  manifests/<source_id>.jsonl
  failures.jsonl
  index.sqlite                      # SQLite FTS5 over heading chunks
  report.json is written to <repo>/reports/corpus/report.json
```

Every normalized file repeats the governance fields in its front matter.
Chunks are one per heading section, split further at ~1000 tokens if a section
is oversized.

## Source status (P0)

| Source | Docs | Bytes | License | Usage class | Notes |
|---|---:|---:|---|---|---|
| pandocs | 82 | 837,879 | CC0-1.0 | public-domain | pinned commit |
| awesome_gbdev | 1 | 52,651 | GPL-3.0 | share-alike | README |
| sameboy | 5 | 35,546 | MIT | permissive | README + root docs |
| mooneye_gb | 1 | 9,618 | GPL-3.0 | share-alike | `README.markdown` |
| gb_test_roms | 7 | 30,329 | none declared | copyrighted-local | no LICENSE; binaries not fetched |
| mealybug | 1 | 5,582 | MIT | permissive | README |
| giibiiadvance | 5 | 219,374 | GPL-2.0 | share-alike | docs (includes a near-dup of pandocs) |
| binjgb | 1 | 7,755 | MIT | permissive | README |
| copetti_gb | 1 | 153,023 | CC-BY-4.0 | permissive | article grants CC BY 4.0 |
| ladx_disassembly | 7 | 20,338 | none declared | copyrighted-local | no LICENSE; Nintendo derivative |
| ladx_randomizer | 1 | 1,292 | MIT | permissive | `daid/LADXR` substitution |
| datacrystal_ladx | 3 | 90,772 | GFDL-1.2 | share-alike | Wayback, 2024-2025 snapshots |
| tcrf_ladx | 1 | 103,763 | CC-BY-3.0 | permissive | Wayback, 2013 snapshot |
| zeldawiki_ladx | 1 | 9,593 | GFDL-1.3 | share-alike | wikitext, revid recorded |
| speedrun_ladx | 12 | 136,478 | none declared | copyrighted-local | API data; terms blocked |
| tasvideos_ladx | 1 | 26,779 | CC-BY-2.0 | permissive | SiteLicense page |
| arxiv_dagger | 1 | 2,755 | arXiv-non-exclusive-1.0 | permissive | metadata + abstract only |
| arxiv_il_survey | 1 | 2,555 | arXiv-non-exclusive-1.0 | permissive | metadata + abstract only |
| sre_postmortem | 1 | 55,113 | CC-BY-NC-ND-4.0 | nc-nd | local-only inspiration |
| complexsystems | 1 | 23,713 | all-rights-reserved | copyrighted-local | no reuse grant |
| nist_800_61 | 1 | 108,379 | US-Government-work | public-domain | SP 800-61 Rev. 3, April 2025 |

Totals: 135 documents, 1,933,287 raw bytes, 1,218 indexed chunks.
Class breakdown: public-domain 83, permissive 13, share-alike 11, nc-nd 1,
copyrighted-local 27, unknown 0. Restricted (nc-nd + copyrighted-local +
unknown): 28.

## Recovered blocked sources

Direct `api.php` and `index.php?action=raw` requests to both wikis still return
Cloudflare 403. No UA rotation, proxies, or bypass was used. The recovery used
the Internet Archive's CDX API and `id_` raw snapshots at 1 request/second:

- **datacrystal_ladx**: the DX-specific page has no Wayback capture, so the
  archived "The Legend of Zelda: Link's Awakening (Game Boy)" page, RAM map, and
  ROM map were ingested (2024-03-03, 2024-11-03, 2025-05-30). `retrieved_via =
  wayback`; the original URL and snapshot URL are separate fields.
- **tcrf_ladx**: the archived DX URL (2013-11-28) redirects to the Link's
  Awakening page, which covers DX. `retrieved_via = wayback`.

See `LICENSES.md` for the archived footer evidence. If a future Wayback request
fails, set `enabled = false` with `blocked_reason` in `sources.toml`; do not fake
a document.

## NIST SP 800-61

The current revision was resolved from the CSRC landing page at audit time:
**NIST SP 800-61 Rev. 3**, *Incident Response Recommendations and Considerations
for Cybersecurity Risk Management: A CSF 2.0 Community Profile*, April 2025,
DOI `10.6028/NIST.SP.800-61r3`. The PDF was fetched from NVL Publications and
its text extracted with PyMuPDF (a uv dependency). The manifest records the PDF
URL and SHA-256; the binary PDF is not stored in the corpus or git. Usage class
is `public-domain`: page 3 states the publication is not subject to copyright in
the United States. This is the citable incident-response backbone; the SRE
chapter stays `nc-nd` local-only inspiration.

## Public export guard

`gbg-corpus export --public --out <dir>` writes:

```
public/
  README.md                 # attribution and license rules
  sources.json              # per source: id, title, URL, license, class,
                            # evidence, retrieved_at, sha256, documents
  text/<source_id>/*.md     # only public-domain, permissive, share-alike
  text/<source_id>/LICENSE.txt
  links/<source_id>.md      # metadata-only stub for nc-nd/copyrighted-local/unknown
```

Restricted classes never get a `text/` directory and never get an excerpt. The
guard has two layers:

1. The exporter evaluates the source class before writing; the least reusable
   class wins if a source ever contains mixed rows.
2. After writing, `check_public_export` fails if a restricted source id appears
   under `text/`, if an exported body declares a restricted `usage_class` in its
   front matter, or if a restricted source with documents lacks its `links/`
   stub. It also cross-checks the live manifests, so a tampered `sources.json`
   cannot hide a restricted source. Tests place a synthetic restricted document
   under `public/text/` and assert the check fails.

`--fail-on-restricted` defaults to true. `gbg-corpus check --public-out DIR`
runs the same guard as part of the normal check.

## Safety guards

- Magic-byte sniff rejects ZIP, PDF, 7z/RAR/gzip, PNG/JPEG/GIF, RIFF/MP3/OGG/
  FLAC, Matroska, ELF, NES, WebAssembly, and Game Boy ROM headers even when the
  extension is `.md`.
- Documents larger than 5 MB are logged in `failures.jsonl` and skipped; they
  are never silently truncated.
- Files with banned extensions (`.gb`, `.gbc`, `.pdf`, audio/video, archives)
  are refused at save time.
- `check` fails on banned domains (Discord, Spotify, Apple Music), missing raw or
  normalized files, hash mismatches, raw content inside the git repo, missing
  governance fields, invalid usage classes, and duplicate canonical URLs
  without `duplicate_of`.
- Scraped text is stored verbatim. A test feeds a document containing
  "ignore previous instructions" and asserts it is stored, not acted on.
- No LLM summarization. Any future derived note must be a separate, labelled file.

## Tests

Offline only; fixtures in `tests/fixtures/`. The suite covers manifest schema,
hash stability, idempotent re-fetch, MediaWiki raw parsing, GitHub path
filtering, near-duplicate detection, banned extension/domain refusal,
heading-path chunking, HTML extraction, the prompt-injection-as-text rule, plus
the governance layer: idempotent usage-class migration, enum validation,
restricted-body export exclusion, export guard failure on a planted restricted
document, ZIP magic bytes in a fake `.md`, the 5 MB limit, and CDX parsing /
`id_` URL construction. No test touches the network.

## Assumptions and substitutions

- **`zladx/LADX-Randomizer` does not exist.** The maintained randomizer is
  `daid/LADXR` (MIT), used instead and documented here.
- **TASVideos path**: the DX-specific path 404s. The game-resources page is
  `https://tasvideos.org/GameResources/GB/LinksAwakening`.
- **mooneye-gb** uses `README.markdown`, not `README.md`.
- **GitHub refs are pinned** to the resolved commit SHA in `sources.lock.json`.
  Re-running fetch uses the pinned SHA; delete the lock entry to re-pin.
- **gb-test-roms**: only README/docs; ROM binaries are filtered by extension and
  never requested.
- **Copetti and TASVideos** were upgraded from the proposed conservative class
  after reading explicit license grants. GitHub badges were not used as
  evidence; every row cites the file or footer that was read.
- **P1 and P2 were not attempted** in this pass. Reddit P2 needs OAuth
  credentials that are not present, so it is skipped rather than HTML-scraped.

## Next command

```bash
cd tools/corpus && uv run gbg-corpus check && uv run gbg-corpus export --public --out /tmp/gbg-public
```

Then review `LICENSES.md` and `public/sources.json` before publishing anything.
