# gbg-corpus — GameBoyGhost reference corpus

Reference material only. **This corpus is never training data** and is physically
separate from `data/train`, `data/eval`, and `reports/` (except the generated
`reports/corpus/`). The repo holds code, config, tests, a commit lock, and the
report; raw bytes and normalized text live in `$GBG_CORPUS_DIR`
(default `~/.local/share/gbg-corpus`).

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
uv run gbg-corpus fetch --priority P0      # fetch every P0 source
uv run gbg-corpus fetch --source pandocs   # one source
uv run gbg-corpus fetch --source pandocs --limit 10
uv run gbg-corpus check                    # manifests, hashes, banned content
uv run gbg-corpus report                   # writes reports/corpus/report.json
uv run gbg-corpus index                    # rebuild $GBG_CORPUS_DIR/index.sqlite
uv run pytest                              # offline tests
```

## Storage layout

```
$GBG_CORPUS_DIR/                    # default ~/.local/share/gbg-corpus
  raw/<source_id>/<sha256>.<ext>
  normalized/<source_id>/<slug>.md  # YAML front matter + verbatim text
  manifests/<source_id>.jsonl
  failures.jsonl
  index.sqlite                      # SQLite FTS5 over heading chunks
  report.json is written to <repo>/reports/corpus/report.json
```

Every normalized file repeats `source_id`, `url`, `license`, `sha256`,
`retrieved_at`, and the top heading path in its front matter. Chunks are one
per heading section, split further at ~1000 tokens if a section is oversized.

## Source status (P0)

| Source | Docs | Bytes | License | Notes |
|---|---:|---:|---|---|
| pandocs | 82 | 837,879 | CC0-1.0 | pinned commit |
| awesome_gbdev | 1 | 52,651 | GPL-3.0 | README |
| sameboy | 5 | 35,546 | MIT | README + root docs |
| mooneye_gb | 1 | 9,618 | GPL-3.0 | `README.markdown` |
| gb_test_roms | 7 | 30,329 | unknown | no LICENSE in repo; no binaries fetched |
| mealybug | 1 | 5,582 | MIT | README |
| giibiiadvance | 5 | 219,374 | GPL-2.0 | docs (includes a near-dup of pandocs) |
| binjgb | 1 | 7,755 | MIT | README |
| copetti_gb | 1 | 153,023 | unknown | no explicit reuse license |
| ladx_disassembly | 7 | 20,338 | unknown | README + docs; no LICENSE in repo |
| ladx_randomizer | 1 | 1,292 | MIT | substituted `daid/LADXR` (see below) |
| zeldawiki_ladx | 1 | 9,593 | unknown | wikitext, revid recorded |
| speedrun_ladx | 12 | 136,478 | unknown | game, categories, leaderboards, recent runs |
| tasvideos_ladx | 1 | 26,779 | unknown | corrected URL |
| arxiv_dagger | 1 | 2,755 | arXiv metadata only | abstract + metadata |
| arxiv_il_survey | 1 | 2,555 | arXiv metadata only | abstract + metadata |
| sre_postmortem | 1 | 55,113 | CC-BY-NC-ND-4.0 | online edition |
| complexsystems | 1 | 23,713 | unknown | no explicit reuse license |
| datacrystal_ladx | 0 | 0 | unknown | **blocked: 403** |
| tcrf_ladx | 0 | 0 | unknown | **blocked: 403** |

Totals: 130 documents, 1,630,373 raw bytes, 1,105 indexed chunks.

## Assumptions and substitutions

- **`zladx/LADX-Randomizer` does not exist.** The maintained randomizer is
  `daid/LADXR` (MIT), used instead. Recorded here rather than silently swapped.
- **TASVideos path**: the DX-specific path 404s (it redirects to
  `Wiki/PageDoesNotExist`). The game-resources page is
  `https://tasvideos.org/GameResources/GB/LinksAwakening`.
- **mooneye-gb** uses `README.markdown`, not `README.md`.
- **GitHub refs are pinned** to the resolved commit SHA in `sources.lock.json`.
  Re-running fetch uses the pinned SHA; delete the lock entry to re-pin.
- **Licenses** are detected from `LICENSE`/`COPYING` files. Where a site has no
  explicit reuse grant, `license` is `unknown` and the text is local-only.
- **gb-test-roms**: only README/docs; ROM binaries are filtered by extension and
  never requested.
- **P1 and P2 were not attempted** in this pass. The handoff says P1 only if P0
  is clean and time remains; P0 is clean except the two blocked wikis. Reddit P2
  needs OAuth credentials that are not present, so it is skipped rather than
  HTML-scraped.

## Blocked sources

| Source | Result | Action |
|---|---|---|
| datacrystal.tcrf.net | HTTP 403 (Cloudflare) on `api.php` | 3 attempts with backoff, recorded, moved on |
| tcrf.net | HTTP 403 (Cloudflare) on `api.php` | same |

No UA rotation, no bypass attempts. Both are recorded in `failures.jsonl` and in
`reports/corpus/report.json`.

## Safety rules encoded in the tool

- Files with banned extensions (`.gb`, `.gbc`, `.pdf`, audio/video, archives) are
  refused at save time and logged.
- `check` fails on banned domains (Discord, Spotify, Apple Music), missing raw or
  normalized files, hash mismatches, raw content inside the git repo, and
  duplicate canonical URLs without `duplicate_of`.
- Scraped text is stored verbatim. A test feeds a document containing
  "ignore previous instructions" and asserts it is stored, not acted on.
- No LLM summarization. Any future derived note must be a separate, labelled file.

## Tests

Offline only; fixtures in `tests/fixtures/`. Covers manifest schema, hash
stability, idempotent re-fetch, MediaWiki raw parsing, GitHub path filtering,
near-duplicate detection, banned extension/domain refusal, heading-path chunking,
HTML extraction, and the prompt-injection-as-text rule.

## Next command

```bash
cd tools/corpus && uv run gbg-corpus fetch --priority P1
```

P1 is not configured yet; add entries to `sources.toml` first. Or run `check`
and `report` after any new fetch.
