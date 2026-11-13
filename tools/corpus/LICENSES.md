# License audit — gbg-corpus sources

Audited 2026-11-05 against the file, footer, or terms page named in each row.
`may publish` means the public export may contain the body text under the stated
license (with attribution and the notice in `licenses/`). `must not publish`
means metadata and URL only; no body text or excerpts.

| id | source URL | license string | usage_class | license_evidence_url | publication rule |
|---|---|---|---|---|---|
| pandocs | https://github.com/gbdev/pandocs | CC0-1.0 | public-domain | https://raw.githubusercontent.com/gbdev/pandocs/89f82b2181dac4e335bbbdd1451534e6b3a716cf/LICENSE | may publish: CC0 dedication, no conditions |
| awesome_gbdev | https://github.com/gbdev/awesome-gbdev | GPL-3.0 | share-alike | https://raw.githubusercontent.com/gbdev/awesome-gbdev/7915a26a5e1e1814d823b90846e7519d5bda797c/LICENSE | may publish with GPL-3.0 notice and attribution; do not relicense |
| sameboy | https://github.com/LIJI32/SameBoy | MIT (Expat) | permissive | https://raw.githubusercontent.com/LIJI32/SameBoy/ea667ad79aa28409f034b1fd6da7304e1844750d/LICENSE | may publish with copyright and MIT notice |
| mooneye_gb | https://github.com/Gekkio/mooneye-gb | GPL-3.0 | share-alike | https://raw.githubusercontent.com/Gekkio/mooneye-gb/3856dcbca82a7d32bd438cc92fd9693f868e2e23/LICENSE | may publish with GPL-3.0 notice and attribution; do not relicense |
| gb_test_roms | https://github.com/retrio/gb-test-roms | none declared | copyrighted-local | https://github.com/retrio/gb-test-roms/tree/c240dd7d700e5c0b00a7bbba52b53e4ee67b5f15 | must not publish: no LICENSE/COPYING at the pinned commit; ROMs are copyrighted |
| mealybug | https://github.com/mattcurrie/mealybug-tearoom-tests | MIT | permissive | https://raw.githubusercontent.com/mattcurrie/mealybug-tearoom-tests/70e88fb90b59d19dfbb9c3ac36c64105202bb1f4/LICENSE | may publish with copyright and MIT notice |
| giibiiadvance | https://github.com/AntonioND/giibiiadvance | GPL-2.0 | share-alike | https://raw.githubusercontent.com/AntonioND/giibiiadvance/ccb40c3cf7d9efec538858a36d4ab69bb4d0ce5c/LICENSE.txt | may publish with GPL-2.0 notice and attribution; do not relicense |
| binjgb | https://github.com/binji/binjgb | MIT | permissive | https://raw.githubusercontent.com/binji/binjgb/16621111ed0ee73bcc45c912a823bcebedcffc0f/LICENSE | may publish with copyright and MIT notice |
| copetti_gb | https://www.copetti.org/writings/consoles/game-boy/ | CC-BY-4.0 | permissive | https://www.copetti.org/writings/consoles/game-boy/#referencing | may publish with attribution to Rodrigo Copetti and CC BY 4.0 notice |
| ladx_disassembly | https://github.com/zladx/LADX-Disassembly | none declared | copyrighted-local | https://github.com/zladx/LADX-Disassembly/tree/2a5c2c0d6df93a54df81ae9e1fe28b5c2fd60d03 | must not publish: no LICENSE at the pinned commit; derivative of a Nintendo game |
| ladx_randomizer | https://github.com/daid/LADXR | MIT | permissive | https://raw.githubusercontent.com/daid/LADXR/4325207e4e55076e05f209fbdf16b860a90e42ef/LICENSE | may publish with copyright and MIT notice |
| datacrystal_ladx | https://datacrystal.tcrf.net/wiki/The_Legend_of_Zelda:_Link%27s_Awakening_(Game_Boy) | GFDL-1.2 | share-alike | https://web.archive.org/web/20240303104212id_/https://datacrystal.tcrf.net/wiki/The_Legend_of_Zelda:_Link%27s_Awakening_(Game_Boy) | may publish with GFDL-1.2 notice and attribution; do not relicense |
| tcrf_ladx | https://tcrf.net/The_Legend_of_Zelda:_Link%27s_Awakening_DX | CC-BY-3.0 | permissive | https://web.archive.org/web/20131128111419id_/http://tcrf.net/The_Legend_of_Zelda:_Link%27s_Awakening_DX | may publish with attribution and CC BY 3.0 notice |
| zeldawiki_ladx | https://zeldawiki.wiki/wiki/The_Legend_of_Zelda:_Link%27s_Awakening_DX | GFDL-1.3 | share-alike | https://zeldawiki.wiki/wiki/Zelda_Wiki:GNU_Free_Documentation_License | may publish with GFDL-1.3 notice and attribution; do not relicense |
| speedrun_ladx | https://www.speedrun.com/pdvj2vdw | none declared | copyrighted-local | https://github.com/speedruncom/api | must not publish: API docs carry no reuse grant; terms page blocked and not archived; API data only |
| tasvideos_ladx | https://tasvideos.org/GameResources/GB/LinksAwakening | CC-BY-2.0 | permissive | https://tasvideos.org/SiteLicense | may publish with attribution and CC BY 2.0 notice |
| arxiv_dagger | https://arxiv.org/abs/1011.0686 | CC0-1.0 | public-domain | https://info.arxiv.org/help/license/index.html | may publish metadata and abstract only: arXiv CC0 dedication; PDF not mirrored |
| arxiv_il_survey | https://arxiv.org/abs/2106.12177 | CC0-1.0 | public-domain | https://info.arxiv.org/help/license/index.html | may publish metadata and abstract only: arXiv CC0 dedication; PDF not mirrored |
| sre_postmortem | https://sre.google/sre-book/postmortem-culture/ | CC-BY-NC-ND-4.0 | nc-nd | https://sre.google/sre-book/postmortem-culture/ | must not publish: footer is CC BY-NC-ND 4.0; local reference only |
| complexsystems | https://how.complexsystems.fail/ | all-rights-reserved | copyrighted-local | https://how.complexsystems.fail/ | must not publish: Copyright (c) R.I.Cook notice, no reuse grant |
| nist_800_61 | https://csrc.nist.gov/pubs/sp/800/61/r3/final | US-Government-work | public-domain | https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-61r3.pdf | may publish: PDF page 3 says not subject to copyright in the US |

## Notes and evidence changes

- **copetti_gb** was proposed as `copyrighted-local`. The article's
  "Copyright and permissions" section explicitly grants CC BY 4.0, so it is
  `permissive`. Evidence is the live page section, not a repository badge.
- **tasvideos_ladx** was proposed as `copyrighted-local`. The site's
  `SiteLicense` page says all content is CC BY 2.0, so it is `permissive`.
- **zeldawiki_ladx** was proposed for possible CC BY-SA. The footer and license
  page say GNU Free Documentation License 1.3, a copyleft documentation
  license; it is `share-alike`, not CC BY-SA.
- **datacrystal_ladx**: direct `index.php?action=raw` returned Cloudflare 403.
  Wayback has no capture of a DX-specific page, so the archived
  "Link's Awakening (Game Boy)" page and its RAM/ROM maps were ingested
  (`retrieved_via=wayback`). The archived footer says GFDL 1.2.
- **tcrf_ladx**: direct `index.php?action=raw` returned Cloudflare 403. The
  archived DX URL is a redirect to the Link's Awakening page, which covers DX.
  The archived footer says CC BY 3.0; `retrieved_via=wayback`.
- **arxiv_dagger**: arXiv grants CC0 on metadata and author abstracts (per
  https://info.arxiv.org/help/license/index.html); it is `public-domain`.
  The PDF is not mirrored.
- **arxiv_il_survey**: arXiv grants CC0 on metadata and author abstracts (per
  https://info.arxiv.org/help/license/index.html); it is `public-domain`.
  The PDF is not mirrored.
- **speedrun_ladx** stays `copyrighted-local`: no reuse grant was found, the
  terms page is Cloudflare-blocked, and Wayback has no capture of it.
- **gb_test_roms** and **ladx_disassembly** stay `copyrighted-local`: no
  LICENSE/COPYING file exists at the pinned commits.
- **pandocs (historical/)**: the 6 legacy files under `historical/**` credit third
  parties in their headers; repo-level CC0 is not shown to cover them, so they
  are overridden to `copyrighted-local`.
- **giibiiadvance (**/*.txt)**: third-party hardware notes and a vendored copy of
  the 2001 Pan Docs under `**/*.txt` are overridden to `copyrighted-local` rather
  than inheriting repository-level GPL-2.0.

## Local no-license sources

For rows with `none declared`, the evidence URL is the pinned repository tree
that was inspected and found to contain no license file. Absence of a license
is not permission; these are treated as `copyrighted-local` and are never
exported as body text.
