# Part 07 — scoped Markdown link-path audit (2026-11-16)

## Scope and pinned source
- Repository: `sssamant21/data-platform-engineering-tutorials`, branch `main`.
- Recursive Git tree commit: `5346e668b582c5e4a8bea45515ac0775fbdad306`; `truncated=false`, 1,692 tree entries.
- Chapter Markdown files: `sql-tutorials/part-07-subqueries/061-*.md` through `070-*.md` (ten files).
- Method: retrieve each chapter from `main`, match inline Markdown links with a regular expression, classify HTTP(S) versus local destinations, URL-decode local paths, normalize relative segments, and compare each target path to the pinned recursive tree. This is a **scoped path-existence check**, not a full Markdown parser.

## Results

| Chapter | Local inline links | External HTTP(S) links |
|---|---:|---:|
| 061 | 8 | 4 |
| 062 | 7 | 3 |
| 063 | 6 | 3 |
| 064 | 5 | 4 |
| 065 | 5 | 3 |
| 066 | 5 | 3 |
| 067 | 5 | 4 |
| 068 | 6 | 4 |
| 069 | 5 | 4 |
| 070 | 6 | 4 |
| **Total** | **58** | **36** |

- **Missing tracked local target paths: 0/58.**
- Five fragment-bearing local links reference `../MASTER-TOC.md`: four reference `#part-07--subqueries-ctes--set-operations` and one references `#part-08--window-functions--advanced-analytics`. The corresponding Part 07 and Part 08 headings were confirmed present in the current `MASTER-TOC.md`; GitHub-rendered anchor resolution was not independently tested.
- Reference-style link definitions detected by the scoped pattern: 0.
- External HTTP(S) links: 36 inventoried, **not tested**.

## Limits and validation classification
- Authored/published: **120/120** (per status tracker).
- Targeted SQL static review: **120/120** (per status tracker); **not** parser-based syntax verification.
- Cumulative scoped chapter link-path audit: **70/120** (Parts 01–07).
- Independent editorial review: **0/120**.
- Actual isolated PostgreSQL 18 runtime validation: **0/120**.
- No SQL executed, no production environment accessed, and no new chapters authored in this audit.
- The regular expression may miss reference-style, autolinks, nested Markdown, or dynamically constructed destinations. Complete Markdown parsing, external URL testing, SQL parser validation, and runtime evidence remain pending.

## Next
Audit Part 08 (071–080), then Parts 09–12. Perform comprehensive link/anchor and SQL parser QA; execute PostgreSQL 18 labs only on a verified isolated instance with reproducible evidence. Track defects before certifying readiness.
