# Reference resolution audit — PostgreSQL enterprise learning path

**Checkpoint:** 2026-11-09  
**Branch:** `main`  
**Scope:** Independent 20-chapter learning path only  
**Documentation baseline:** PostgreSQL 18  
**Validation type:** GitHub source/tree inspection only; no executable or live HTTP tests.

## Evidence and method

Read the track's `README.md`, `MASTER-TOC.md`, `STATUS-TRACKER.md`, `POSTGRESQL-18-BASELINE.md`, `STATIC-AUDIT-2026-11-03.md`, and existing `validation/semantic-review-progress.md` before resuming the unfinished link gate. The GitHub recursive `main` tree was reported as **not truncated**.

Fetched the eight Markdown sources for **Chapters 01–04 and their four labs**. Extracted ordinary inline Markdown links, resolved relative paths against each source directory (including cross-curriculum links), and compared targets against exact blob paths in the GitHub tree. Counts below represent link occurrences, not unique URLs.

| File | Inline link occurrences | Missing relative-file targets |
| --- | ---: | ---: |
| Chapter 01 lesson | 12 | 0 |
| Chapter 01 lab | 1 | 0 |
| Chapter 02 lesson | 12 | 0 |
| Chapter 02 lab | 7 | 0 |
| Chapter 03 lesson | 12 | 0 |
| Chapter 03 lab | 6 | 0 |
| Chapter 04 lesson | 12 | 0 |
| Chapter 04 lab | 7 | 0 |
| **Total** | **69** | **0** |

**Result:** 69 ordinary inline Markdown link occurrences inventoried across eight files; no broken relative-file targets found by exact tree-path resolution. The chapters also contain intentional links to the separate 100-chapter curriculum. These targets were *read-only verified as file paths*, not edited.

## Limits and outstanding checks

- This parser covers ordinary `[label](destination)` links with simple destinations. It does **not** establish exhaustive coverage of reference-style definitions, multiline/escaped destinations, raw HTML links, or autolinks.
- No fragment/anchor links were found by this extraction in the eight files; heading-slug/fragment resolution remains untested.
- The PostgreSQL 18 documentation URLs were **inventoried but not HTTP-fetched or semantically checked**. No claim is made about HTTP status, redirects, page sections, or version correctness.
- Chapters 05–20 and their labs, plus supporting Markdown files, still need this deeper reference pass.
- Historical PostgreSQL 17 runtime assumptions are unchanged. **0/20 labs runtime validated**; **0/20 PostgreSQL 18 runtime validated**. Independent technical approval and production certification remain pending.

## Next safe action

Continue the same source-tree reference check for Chapters 05–08 and their labs, then subsequent batches. Verify reference-style links, fragments and official PostgreSQL 18 destinations separately. Record only confirmed errors and make scoped fixes. Do not advance runtime statuses without isolated execution, version/image/volume identity, sanitized outputs, and cleanup proof.
