# Part 08 — scoped Markdown link-path audit (2026-11-16)

## Scope and source
- Repository: `sssamant21/data-platform-engineering-tutorials`, branch `main`
- Pinned complete recursive Git tree: `6321622cff338547c3c21f1627dab4414c7bc035` (`truncated=false`; 1,693 entries)
- Chapters: `sql-tutorials/part-08-window-functions/071-*.md` through `080-*.md` (ten Markdown chapter files)
- Method: fetched all ten files from `main`, extracted inline Markdown `[label](target)` links with a scoped regular expression, normalized local relative paths and checked existence against the pinned tree. This is not a Markdown parser.

## Results

| Chapter | Local path targets checked | External HTTP(S) URLs inventoried |
|---|---:|---:|
| 071 | 7 | 4 |
| 072 | 5 | 4 |
| 073 | 7 | 3 |
| 074 | 7 | 3 |
| 075 | 7 | 3 |
| 076 | 5 | 3 |
| 077 | 6 | 3 |
| 078 | 4 | 4 |
| 079 | 9 | 4 |
| 080 | 11 | 4 |
| **Total** | **68** | **35** |

**Missing tracked local path targets: 0.** Fourteen local fragment-link occurrences point to `MASTER-TOC.md`: twelve to `#part-08--window-functions--advanced-analytics` and two to `#part-09--sql-objects-functions--semi-structured-data`. The corresponding section headings appear in the Master TOC, but GitHub-rendered anchor resolution was **not** verified. No reference-style link definitions were detected by the scoped line pattern.

## Limitations and next work
- No HTTP(S) URL availability check; no comprehensive Markdown parsing, code-fence-aware extraction, reference-style use resolution, image links, encoded-link edge cases, or GitHub-rendered fragment verification.
- No SQL parser checks, SQL execution, independent editorial review, or PostgreSQL 18 runtime acceptance. No production environment accessed.
- Cumulative scoped chapter link-path audits after this evidence: **80/120** (Parts 01–08); remaining: Parts 09–12 (081–120).
- Continue Part 09 (081–090), then Parts 10–12; follow with comprehensive Markdown/parser QA and isolated PostgreSQL 18 runtime acceptance with retained evidence.
