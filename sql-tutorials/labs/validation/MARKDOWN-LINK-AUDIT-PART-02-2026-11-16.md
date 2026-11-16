# Part 02 — scoped Markdown inline-link path audit (2026-11-16)

## Scope and source

- Repository: `sssamant21/data-platform-engineering-tutorials`, branch `main`.
- Source Git tree: `70579c5b92ea1c754077ecf07f35156d9038da56` (recursive, `truncated=false`; 1,687 tracked entries, including 324 under `sql-tutorials/`).
- Chapters: `sql-tutorials/part-02-filtering/011-*.md` through `020-*.md` (all ten existing files fetched from `main`).
- Method: inspect inline Markdown link destinations matching `[label](destination)` and `![label](destination)`; normalize relative paths against each chapter directory, resolve `.` and `..`, and compare with exact tracked Git tree paths. HTTP(S) destinations are inventoried, not contacted.

## Results

| Chapter | Local inline path links | External HTTP(S) links | Missing local tracked targets |
|---|---:|---:|---:|
| 011 | 7 | 5 | 0 |
| 012 | 10 | 4 | 0 |
| 013 | 9 | 4 | 0 |
| 014 | 9 | 4 | 0 |
| 015 | 10 | 4 | 0 |
| 016 | 10 | 4 | 0 |
| 017 | 10 | 4 | 0 |
| 018 | 10 | 5 | 0 |
| 019 | 10 | 4 | 0 |
| 020 | 13 | 4 | 0 |
| **Total** | **98** | **42** | **0** |

No local `#fragment` destinations or reference-style link definitions were found by this scoped pattern scan. Counts may differ from earlier provisional inventories because this audit uses an explicit inline-link extraction and normalization method.

## Limitations and acceptance

**PASS for scoped local inline path existence only.** This is not a complete CommonMark parser, reference-link resolution, generated heading-anchor verification, external URL availability check, or an assessment of whether linked content is semantically correct. Inline links containing unusual nested parentheses or multi-line destinations require a parser-based audit. No SQL was executed, no independent editorial review occurred, and no isolated PostgreSQL 18 runtime validation was performed.

## Next

Continue Parts 03–12 with parser-based Markdown path/anchor/reference checks, review SQL syntax and expected outputs, then run labs only on a confirmed disposable PostgreSQL 18 instance with reproducible execution evidence. Maintain authored/published 120/120, targeted SQL static review 120/120, independent editorial review 0/120, and actual PostgreSQL 18 runtime-validated 0/120 until independently supported evidence changes those counts.
