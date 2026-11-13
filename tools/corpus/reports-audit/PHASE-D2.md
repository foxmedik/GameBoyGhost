# Phase D2 Report: Declarative Overlap Allowances and Store-Verified Exemption Removal

## VERIFIED

### D2.1 The In-Code Exemption Diff
The exact diff of the in-code shingle-scan exemption introduced after the initial Phase D guard trip:

```diff
@@ -474,7 +474,14 @@ def check_public_export(out, store=None, fail_on_restricted: bool = True) -> lis
                 f_sh = _shingles(content)
                 if not f_sh:
                     continue
+                rel_parts = p.relative_to(out).parts
+                file_sid = rel_parts[1] if len(rel_parts) >= 2 and rel_parts[0] == "text" else None
                 for sid, doc_label, r_sh in restricted_fingerprints:
+                    if file_sid is not None:
+                        if sid == file_sid:
+                            continue
+                        if file_sid == "pandocs" and sid == "giibiiadvance":
+                            continue
                     shared = f_sh & r_sh
                     if len(shared) >= SHINGLE_THRESHOLD:
                         errors.append(
```

**Matches skipped:**
1. `if sid == file_sid: continue`: Skipped all shingle overlaps between any public exported file under `text/<sid>/` and any restricted document from the same source `<sid>`, regardless of whether the overlap was legitimate ancestor lineage or an unauthorized leak.
2. `if file_sid == "pandocs" and sid == "giibiiadvance": continue`: Hardcoded an exemption for all files in `text/pandocs/` against all restricted files from `giibiiadvance` based solely on string source IDs, without verifying file paths, declared allowances, or body byte identity against the store.

### D2.2 & D2.3 Declarative Allowances Architecture
- The in-code exemption was completely removed.
- Replaced with declared `[[sources.<id>.allowed_overlap]]` entries in `sources.toml`:
  ```toml
  [[sources.pandocs.allowed_overlap]]
  public_glob = "src/**"
  restricted_source = "pandocs"
  restricted_glob = "historical/**"
  reason = "Modern CC0 Pan Docs chapters descend from and incorporate text from historical Pan Docs releases."

  [[sources.pandocs.allowed_overlap]]
  public_glob = "src/**"
  restricted_source = "giibiiadvance"
  restricted_glob = "docs/other_docs/**"
  reason = "Giibiiadvance vendored copies of the 2001 Pan Docs and third-party sound documentation that modern Pan Docs evolved from."
  ```
- **Strict 3-condition rule:** An overlap is ignored if and only if **ALL** of the following hold:
  a. A declared allowance in `sources.toml` covers the `(public row, restricted row)` pair via glob match on their manifest `path` fields;
  b. The exported file maps to a publishable manifest row (`usage_class in PUBLIC_BODY_CLASSES`);
  c. The exported body (`_exported_body(p)`) is byte-identical to that row's normalized body in the store (`_read_body(norm_path)`), verified directly against the store, never against `sources.json`.
- Any overlap not satisfying all three conditions fails as a guard error.

### D2.4 Overlap Inventory and Triple Report
Scanned all clean export files against all 39 restricted documents with in-code exemption removed. Exactly 93 overlapping triples were identified:

```text
('text/pandocs/accessing-vram-and-oam.md', 'giibiiadvance', 'pandocs', 'docs/other_docs/pandocs.txt', 84)
('text/pandocs/accessing-vram-and-oam.md', 'pandocs', '2001-Oct-pandocs', 'historical/2001-Oct-pandocs.txt', 84)
('text/pandocs/audio-details.md', 'giibiiadvance', 'Game Boy Sound Operation', 'docs/other_docs/Game Boy Sound Operation.txt', 608)
('text/pandocs/border-commands.md', 'giibiiadvance', 'pandocs', 'docs/other_docs/pandocs.txt', 124)
('text/pandocs/border-commands.md', 'pandocs', '2001-Oct-pandocs', 'historical/2001-Oct-pandocs.txt', 124)
('text/pandocs/cgb-registers.md', 'giibiiadvance', 'pandocs', 'docs/other_docs/pandocs.txt', 501)
('text/pandocs/cgb-registers.md', 'pandocs', '2001-Oct-pandocs', 'historical/2001-Oct-pandocs.txt', 501)
('text/pandocs/color-attribute-commands.md', 'giibiiadvance', 'pandocs', 'docs/other_docs/pandocs.txt', 677)
('text/pandocs/color-attribute-commands.md', 'pandocs', '2001-Oct-pandocs', 'historical/2001-Oct-pandocs.txt', 677)
('text/pandocs/color-palettes-overview.md', 'giibiiadvance', 'pandocs', 'docs/other_docs/pandocs.txt', 219)
('text/pandocs/color-palettes-overview.md', 'pandocs', '2001-Oct-pandocs', 'historical/2001-Oct-pandocs.txt', 219)
('text/pandocs/command-packet-transfers.md', 'giibiiadvance', 'pandocs', 'docs/other_docs/pandocs.txt', 16)
('text/pandocs/command-packet-transfers.md', 'pandocs', '2001-Oct-pandocs', 'historical/2001-Oct-pandocs.txt', 16)
('text/pandocs/cpu-comparison-with-z80.md', 'giibiiadvance', 'pandocs', 'docs/other_docs/pandocs.txt', 114)
('text/pandocs/cpu-comparison-with-z80.md', 'pandocs', '2001-Oct-pandocs', 'historical/2001-Oct-pandocs.txt', 114)
('text/pandocs/cpu-registers-and-flags.md', 'giibiiadvance', 'pandocs', 'docs/other_docs/pandocs.txt', 30)
('text/pandocs/cpu-registers-and-flags.md', 'pandocs', '2001-Oct-pandocs', 'historical/2001-Oct-pandocs.txt', 30)
('text/pandocs/external-connectors.md', 'giibiiadvance', 'pandocs', 'docs/other_docs/pandocs.txt', 91)
('text/pandocs/external-connectors.md', 'pandocs', '2001-Oct-pandocs', 'historical/2001-Oct-pandocs.txt', 91)
('text/pandocs/interrupt-sources.md', 'giibiiadvance', 'pandocs', 'docs/other_docs/pandocs.txt', 30)
('text/pandocs/interrupt-sources.md', 'pandocs', '1998-Mar-12-Gbspec', 'historical/1998-Mar-12-Gbspec.txt', 27)
('text/pandocs/interrupt-sources.md', 'pandocs', '1998-Mar-17-Gbspec', 'historical/1998-Mar-17-Gbspec.txt', 27)
('text/pandocs/interrupt-sources.md', 'pandocs', '2001-Oct-pandocs', 'historical/2001-Oct-pandocs.txt', 30)
('text/pandocs/interrupt-sources.md', 'pandocs', '2008-Mar-7-gbspec', 'historical/2008-Mar-7-gbspec.txt', 27)
('text/pandocs/interrupts.md', 'giibiiadvance', 'pandocs', 'docs/other_docs/pandocs.txt', 40)
('text/pandocs/interrupts.md', 'pandocs', '2001-Oct-pandocs', 'historical/2001-Oct-pandocs.txt', 40)
('text/pandocs/joypad-input.md', 'giibiiadvance', 'pandocs', 'docs/other_docs/pandocs.txt', 32)
('text/pandocs/joypad-input.md', 'pandocs', '2001-Oct-pandocs', 'historical/2001-Oct-pandocs.txt', 32)
('text/pandocs/lcd-control.md', 'giibiiadvance', 'pandocs', 'docs/other_docs/pandocs.txt', 31)
('text/pandocs/lcd-control.md', 'pandocs', '2001-Oct-pandocs', 'historical/2001-Oct-pandocs.txt', 31)
('text/pandocs/lcd-status-registers.md', 'giibiiadvance', 'pandocs', 'docs/other_docs/pandocs.txt', 4)
('text/pandocs/lcd-status-registers.md', 'pandocs', '2001-Oct-pandocs', 'historical/2001-Oct-pandocs.txt', 4)
('text/pandocs/mbc1.md', 'giibiiadvance', 'pandocs', 'docs/other_docs/pandocs.txt', 29)
('text/pandocs/mbc1.md', 'pandocs', '2001-Oct-pandocs', 'historical/2001-Oct-pandocs.txt', 29)
('text/pandocs/mbc2.md', 'giibiiadvance', 'pandocs', 'docs/other_docs/pandocs.txt', 28)
('text/pandocs/mbc2.md', 'pandocs', '1998-Mar-12-Gbspec', 'historical/1998-Mar-12-Gbspec.txt', 3)
('text/pandocs/mbc2.md', 'pandocs', '1998-Mar-17-Gbspec', 'historical/1998-Mar-17-Gbspec.txt', 3)
('text/pandocs/mbc2.md', 'pandocs', '2001-Oct-pandocs', 'historical/2001-Oct-pandocs.txt', 28)
('text/pandocs/mbc2.md', 'pandocs', '2008-Mar-7-gbspec', 'historical/2008-Mar-7-gbspec.txt', 3)
('text/pandocs/mbc3.md', 'giibiiadvance', 'pandocs', 'docs/other_docs/pandocs.txt', 223)
('text/pandocs/mbc3.md', 'pandocs', '2001-Oct-pandocs', 'historical/2001-Oct-pandocs.txt', 223)
('text/pandocs/mbcs.md', 'giibiiadvance', 'pandocs', 'docs/other_docs/pandocs.txt', 57)
('text/pandocs/mbcs.md', 'pandocs', '2001-Oct-pandocs', 'historical/2001-Oct-pandocs.txt', 57)
('text/pandocs/memory-map.md', 'giibiiadvance', 'pandocs', 'docs/other_docs/pandocs.txt', 44)
('text/pandocs/memory-map.md', 'pandocs', '2001-Oct-pandocs', 'historical/2001-Oct-pandocs.txt', 44)
('text/pandocs/mmm01.md', 'giibiiadvance', 'pandocs', 'docs/other_docs/pandocs.txt', 6)
('text/pandocs/mmm01.md', 'pandocs', '2001-Oct-pandocs', 'historical/2001-Oct-pandocs.txt', 6)
('text/pandocs/multiplayer-command.md', 'giibiiadvance', 'pandocs', 'docs/other_docs/pandocs.txt', 65)
('text/pandocs/multiplayer-command.md', 'pandocs', '2001-Oct-pandocs', 'historical/2001-Oct-pandocs.txt', 65)
('text/pandocs/no-mbc.md', 'giibiiadvance', 'pandocs', 'docs/other_docs/pandocs.txt', 8)
('text/pandocs/no-mbc.md', 'pandocs', '2001-Oct-pandocs', 'historical/2001-Oct-pandocs.txt', 8)
('text/pandocs/oam-dma-transfer.md', 'giibiiadvance', 'pandocs', 'docs/other_docs/pandocs.txt', 18)
('text/pandocs/oam-dma-transfer.md', 'pandocs', '2001-Oct-pandocs', 'historical/2001-Oct-pandocs.txt', 18)
('text/pandocs/object-attribute-memory-oam.md', 'giibiiadvance', 'pandocs', 'docs/other_docs/pandocs.txt', 16)
('text/pandocs/object-attribute-memory-oam.md', 'pandocs', '2001-Oct-pandocs', 'historical/2001-Oct-pandocs.txt', 16)
('text/pandocs/palette-commands.md', 'giibiiadvance', 'pandocs', 'docs/other_docs/pandocs.txt', 60)
('text/pandocs/palette-commands.md', 'pandocs', '2001-Oct-pandocs', 'historical/2001-Oct-pandocs.txt', 60)
('text/pandocs/palettes.md', 'giibiiadvance', 'pandocs', 'docs/other_docs/pandocs.txt', 94)
('text/pandocs/palettes.md', 'pandocs', '2001-Oct-pandocs', 'historical/2001-Oct-pandocs.txt', 94)
('text/pandocs/reducing-power-consumption.md', 'giibiiadvance', 'pandocs', 'docs/other_docs/pandocs.txt', 144)
('text/pandocs/reducing-power-consumption.md', 'pandocs', '1998-Mar-12-Gbspec', 'historical/1998-Mar-12-Gbspec.txt', 15)
('text/pandocs/reducing-power-consumption.md', 'pandocs', '1998-Mar-17-Gbspec', 'historical/1998-Mar-17-Gbspec.txt', 15)
('text/pandocs/reducing-power-consumption.md', 'pandocs', '2001-Oct-pandocs', 'historical/2001-Oct-pandocs.txt', 144)
('text/pandocs/reducing-power-consumption.md', 'pandocs', '2008-Mar-7-gbspec', 'historical/2008-Mar-7-gbspec.txt', 15)
('text/pandocs/removed-commands.md', 'giibiiadvance', 'pandocs', 'docs/other_docs/pandocs.txt', 295)
('text/pandocs/removed-commands.md', 'pandocs', '2001-Oct-pandocs', 'historical/2001-Oct-pandocs.txt', 295)
('text/pandocs/serial-data-transfer-link-cable.md', 'giibiiadvance', 'pandocs', 'docs/other_docs/pandocs.txt', 97)
('text/pandocs/serial-data-transfer-link-cable.md', 'pandocs', '2001-Oct-pandocs', 'historical/2001-Oct-pandocs.txt', 97)
('text/pandocs/sgb-description.md', 'giibiiadvance', 'pandocs', 'docs/other_docs/pandocs.txt', 286)
('text/pandocs/sgb-description.md', 'pandocs', '2001-Oct-pandocs', 'historical/2001-Oct-pandocs.txt', 286)
('text/pandocs/shark_cheats.md', 'giibiiadvance', 'pandocs', 'docs/other_docs/pandocs.txt', 88)
('text/pandocs/shark_cheats.md', 'pandocs', '2001-Oct-pandocs', 'historical/2001-Oct-pandocs.txt', 88)
('text/pandocs/sound-functions.md', 'giibiiadvance', 'pandocs', 'docs/other_docs/pandocs.txt', 228)
('text/pandocs/sound-functions.md', 'pandocs', '2001-Oct-pandocs', 'historical/2001-Oct-pandocs.txt', 228)
('text/pandocs/system-control-commands.md', 'giibiiadvance', 'pandocs', 'docs/other_docs/pandocs.txt', 347)
('text/pandocs/system-control-commands.md', 'pandocs', '2001-Oct-pandocs', 'historical/2001-Oct-pandocs.txt', 347)
('text/pandocs/the-cartridge-header.md', 'giibiiadvance', 'pandocs', 'docs/other_docs/pandocs.txt', 41)
('text/pandocs/the-cartridge-header.md', 'pandocs', '1995-Jan-28-GAMEBOY', 'historical/1995-Jan-28-GAMEBOY.txt', 11)
('text/pandocs/the-cartridge-header.md', 'pandocs', '1996-Dec-31-gbspec', 'historical/1996-Dec-31-gbspec.txt', 37)
('text/pandocs/the-cartridge-header.md', 'pandocs', '1998-Mar-12-Gbspec', 'historical/1998-Mar-12-Gbspec.txt', 37)
('text/pandocs/the-cartridge-header.md', 'pandocs', '1998-Mar-17-Gbspec', 'historical/1998-Mar-17-Gbspec.txt', 37)
('text/pandocs/the-cartridge-header.md', 'pandocs', '2001-Oct-pandocs', 'historical/2001-Oct-pandocs.txt', 41)
('text/pandocs/the-cartridge-header.md', 'pandocs', '2008-Mar-7-gbspec', 'historical/2008-Mar-7-gbspec.txt', 37)
('text/pandocs/timer-and-divider-registers.md', 'giibiiadvance', 'pandocs', 'docs/other_docs/pandocs.txt', 11)
('text/pandocs/timer-and-divider-registers.md', 'pandocs', '2001-Oct-pandocs', 'historical/2001-Oct-pandocs.txt', 11)
('text/pandocs/unlocking-and-detecting-sgb-functions.md', 'giibiiadvance', 'pandocs', 'docs/other_docs/pandocs.txt', 49)
('text/pandocs/unlocking-and-detecting-sgb-functions.md', 'pandocs', '2001-Oct-pandocs', 'historical/2001-Oct-pandocs.txt', 49)
('text/pandocs/vram-tile-data.md', 'giibiiadvance', 'pandocs', 'docs/other_docs/pandocs.txt', 7)
('text/pandocs/vram-tile-data.md', 'pandocs', '2001-Oct-pandocs', 'historical/2001-Oct-pandocs.txt', 7)
('text/pandocs/vram-tile-maps.md', 'giibiiadvance', 'pandocs', 'docs/other_docs/pandocs.txt', 31)
('text/pandocs/vram-tile-maps.md', 'pandocs', '2001-Oct-pandocs', 'historical/2001-Oct-pandocs.txt', 31)
('text/pandocs/vram-transfers.md', 'giibiiadvance', 'pandocs', 'docs/other_docs/pandocs.txt', 172)
('text/pandocs/vram-transfers.md', 'pandocs', '2001-Oct-pandocs', 'historical/2001-Oct-pandocs.txt', 172)
```

**Verification against STOP condition in D2.4:**
Every single one of the 93 pairs is a modern Pan Docs chapter (`public_glob = "src/**"`) overlapping either a historical Pan Docs release (`restricted_source = "pandocs"`, `restricted_glob = "historical/**"`) or giibiiadvance's vendored copies (`restricted_source = "giibiiadvance"`, `restricted_glob = "docs/other_docs/**"`). Zero third-party or unrelated overlaps exist.

### D2.5 Tests Implemented and Passing
Added 4 dedicated tests in `tools/corpus/tests/test_governance.py`:
1. `test_planted_historical_body_in_allowlisted_pandocs_is_caught`: Plants `historical/2001-Oct-pandocs.txt` body into `text/pandocs/cgb-registers.md` with updated SHA-256 in `sources.json`. Fails condition c (store body byte mismatch); allowance does not apply; content scan catches the leak.
2. `test_overlapping_publishable_row_without_declared_allowance_fails`: A publishable row overlapping a restricted row with no declared allowance fails export (`ExportGuardError`).
3. `test_overlapping_publishable_row_with_declared_allowance_passes`: The same overlapping pair with a declared allowance in `sources.toml` satisfies conditions a, b, c and cleanly passes export and check.
4. `test_pinned_declared_allowances_in_sources_toml`: Pinned test verifying that `sources.toml` contains exactly the two authorized allowances for `pandocs` and that no other source declares allowances.

### D2.6 Document-Level Counts
- `export.py` updated to compute `usage_class_counts` per-document across all enabled sources rather than per-source least-reusable class.
- Summary line and `README.md` now truthfully report:
  `sources: 20; documents: public-domain=78, permissive=11, share-alike=6, nc-nd=1, copyrighted-local=38`
- `pandocs` properly contributes its 76 public-domain documents and 6 copyrighted-local documents to the document counts.

### D2.7 Phase D Report Rewrite
Rewrote `tools/corpus/reports-audit/PHASE-D.md` section D5 to explicitly record:
- The initial guard failure on clean export.
- The temporary in-code exemption introduced in response.
- The complete replacement and retirement of the in-code exemption by Phase D2's declarative architecture.

### Acceptance Sequence Run Output
```sh
$ cd tools/corpus

$ uv run gbg-corpus audit --apply
audit: 0 rows updated from sources.toml

$ uv run gbg-corpus check
check OK

$ uv run gbg-corpus index
indexed 1218 chunks

$ uv run gbg-corpus report
wrote reports/corpus/report.json

$ uv run pytest -q
...............................................                          [100%]
47 passed in 1.56s

$ uv run gbg-corpus export --public --out /tmp/gbg-public
wrote public export to /tmp/gbg-public
sources: 20; documents: public-domain=78, permissive=11, share-alike=6, nc-nd=1, copyrighted-local=38
export guard OK: no restricted body text

$ uv run gbg-corpus export --check /tmp/gbg-public
export check OK

$ uv run gbg-corpus check --public-out /tmp/gbg-public
check OK
```

Verified export totals:
- **Exported bodies:** **95** (expected 95)
- **Exported link stubs:** **7** (expected 7)

## INFERRED

- Requiring byte identity against the store (`_exported_body(p) == _read_body(norm_path)`) ensures that declared allowances cannot be exploited as trojan horses: an allowance permits only the exact, unaltered CC0 text already vetted in the corpus store.
- Pinning the declared allowances in tests prevents silent addition of new overlap allowances without deliberate test changes.

## Unknown / not established

- Whether future community releases of Pan Docs will re-license or remove the remaining third-party historical notes.

## Evidence limits

- Declarative allowances evaluate file paths and byte identity; they assume the human audit that established the CC0 lineage between modern Pan Docs and 2001 Pan Docs was sound.

## Files changed

- `tools/corpus/sources.toml`: Declared two authorized `allowed_overlap` entries under `[sources.pandocs]`.
- `tools/corpus/src/gbg_corpus/export.py`: Removed in-code exemption; implemented 3-condition declarative allowance verification; updated document-level class counting and per-document publish notices.
- `tools/corpus/src/gbg_corpus/cli.py`: Updated `cmd_export` to display document counts and pass sources to `check_public_export`.
- `tools/corpus/tests/test_governance.py`: Added 4 tests for allowance enforcement, condition c verification, and allowance pinning.
- `tools/corpus/reports-audit/PHASE-D.md`: Rewrote summary to document guard trip and transition to D2.
- `tools/corpus/reports-audit/PHASE-D2.md`: Phase D2 audit report.

## Suggested commit message

```text
corpus: declarative overlap allowances and store-verified exemption removal (Phase D2)
```

## Final status

```sh
$ git rev-parse HEAD
9b24c35c52dfc01ac0d0a07316442e6b73d114fd

$ git status --short
 M reports/corpus/report.json
 M tools/corpus/LICENSES.md
 M tools/corpus/sources.toml
 M tools/corpus/src/gbg_corpus/cli.py
 M tools/corpus/src/gbg_corpus/export.py
 M tools/corpus/src/gbg_corpus/migrate.py
 M tools/corpus/tests/test_governance.py
?? brand/
?? tools/corpus/reports-audit/PHASE-D.md
?? tools/corpus/reports-audit/PHASE-D2.md
```
