# Part 10 — scoped Markdown link-path audit (2026-11-16)

## Scope and provenance
- Branch: `main`; repository: `sssamant21/data-platform-engineering-tutorials`.
- Complete recursive Git tree: `e2cf4279fae5ef9d7ff281e11b16ed3f2437122b`; `truncated=false`.
- Ten chapter Markdown files under `sql-tutorials/part-10-performance/`, chapters 091–100.
- Method: scan inline Markdown links with a regular expression, normalize relative paths against each chapter directory, resolve `..` and `.`, and compare paths with tracked tree entries. This is a scoped path-existence check, not a Markdown parser.

## Findings

| Chapter | Local inline links |
|---|---:|
| 091 | 7 |
| 092 | 8 |
| 093 | 8 |
| 094 | 9 |
| 095 | 9 |
| 096 | 9 |
| 097 | 11 |
| 098 | 10 |
| 099 | 10 |
| 100 | 11 |
| **Total** | **92** |

- Missing tracked local targets: **0**.
- External HTTP(S) link occurrences inventoried: **51**, not tested.
- Local fragment occurrences: **0**.
- Reference-style link definitions matched by the scoped pattern: **0**.
- No files or SQL statements were executed or modified as part of this audit.

## Limitations and follow-up
This does not establish complete Markdown correctness, rendered-anchor resolution, reference-style link usage correctness, external URL reachability, SQL parser correctness, independent editorial review, or PostgreSQL 18 runtime validation. Continue scoped audits for Parts 11–12, then full Markdown/parser checks and isolated PostgreSQL 18 execution with reproducible evidence. Keep published chapters at 120/120 and do not claim runtime acceptance without execution.
