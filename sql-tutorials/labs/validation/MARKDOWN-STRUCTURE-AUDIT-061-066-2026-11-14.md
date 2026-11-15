# Chapters 061–066 — targeted Markdown structural audit (2026-11-14)

## Scope and method
Source: GitHub `main`, `sql-tutorials/part-07-subqueries/` Chapters 061–066 and corresponding `sql-tutorials/labs/06*.sql`. Six chapter Markdown files and six SQL labs were fetched and inspected textually. Counts use physical newline-separated lines, line-start ATX headings (`^#{1,6} `), line-start triple-backtick fence candidates (`^````), and inline Markdown link regexes. These heuristics are not a Markdown parser. They do not resolve anchors or test external URLs. All six chapters were already published; no new chapter was authored.

| Chapter | Lines | ATX headings | Fence candidates | Local inline links | External inline links | SQL lab |
|---|---:|---:|---:|---:|---:|---|
| 061 | 149 | 13 | 8 | 7 | 4 | `labs/061-scalar-subqueries-derived-tables.sql` |
| 062 | 165 | 12 | 10 | 7 | 3 | `labs/062-in-any-all-multi-row-subqueries.sql` |
| 063 | 170 | 13 | 10 | 6 | 3 | `labs/063-exists-versus-in-null-sensitive.sql` |
| 064 | 156 | 12 | 8 | 5 | 4 | `labs/064-correlated-subqueries-performance.sql` |
| 065 | 162 | 12 | 8 | 5 | 3 | `labs/065-common-table-expressions-with.sql` |
| 066 | 156 | 12 | 6 | 5 | 3 | `labs/066-recursive-ctes-hierarchical-queries.sql` |
| **Total** | **958** | **74** | **50** | **35** | **20** | **6 labs** |

All six files have even candidate fence counts; this does not establish proper nesting or valid Markdown. No fragment-only inline links were identified by the targeted pattern.

## Findings and actions
- Chapter 061 described the already-published Chapter 062 as "planned". Corrected to a direct relative chapter link in commit `0b0610985cec63d7118fcd11e24704f8b6a99fae`.
- All six SQL labs include textual PostgreSQL version references, `BEGIN READ ONLY`, `ROLLBACK`, and `statement_timeout`. Each lab explicitly requires independent verification of a disposable endpoint. The presence of these safeguards does **not** certify their effectiveness.
- No SQL executed, no PostgreSQL 18 server was connected, no expected result set was compared, and no independent editorial review was performed.

## Acceptance and next work
Targeted structural coverage after this batch: **66/120** chapters. Previously reported targeted local-file path smoke coverage: **120/120**. Independently reviewed: **0/120**. Actually PostgreSQL 18 runtime-validated: **0/120**.

Next: Chapters **067–072** targeted structural QA; perform Markdown-aware link/anchor resolution, SQL syntax/semantics and expected-output verification, safety checks, then execute isolated PostgreSQL 18 acceptance with reproducible environment and output evidence. External URLs remain unchecked.
