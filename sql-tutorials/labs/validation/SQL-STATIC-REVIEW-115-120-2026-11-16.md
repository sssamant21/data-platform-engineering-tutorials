# SQL static and expected-output review — Chapters 115–120 (2026-11-16)

**Scope:** Six published 60-minute chapter Markdown files (115–120) and their six companion SQL labs, read from `main`. Source-based targeted inspection only. This is **not** SQL parser validation, independent editorial approval, comprehensive link/anchor checking, cross-engine execution, or actual PostgreSQL 18 runtime validation.

## Targeted results

| Chapter | Source-based checks and calculated expected result | Remaining limits |
|---|---|---|
| 115 — portability | Four synthetic orders; known amounts 3, NULLs 1, sum 120; East 2/1/40, West 2/2/80; both pagination styles return 101–103. Bidirectional `EXCEPT ALL` comparison and scalar guard examined. | PostgreSQL only; no cross-vendor syntax/semantic execution |
| 116 — PostgreSQL features | Five event rows, three latest keys; active 101=30 and 103=40, deleted 102; active total 70; `DISTINCT ON` and `ROW_NUMBER` expected to agree. | No PostgreSQL 18 execution or actual query-plan evidence |
| 117 — MySQL/MariaDB comparison | Four rows, 3 non-NULL amounts, 1 NULL, total 120; lowercased East/West each 60; page 102/103; `NOT IN` with NULL excludes all, `NOT EXISTS` returns 104. | PostgreSQL SQL only; MySQL/MariaDB differences untested |
| 118 — SQL Server/Oracle comparison | Five rows, 4 priced, total 100; East 3/2/45, West 2/2/55; page 203/204; `NOT IN` returns no rows and `NOT EXISTS` returns 205. | T-SQL and Oracle snippets not executed |
| 119 — cloud analytics | Six events, 3 keys, 2 active latest keys (501=55, 503=35), one tombstone (502), active total 90; filtering deletes before ranking incorrectly resurrects 502. | No Snowflake/BigQuery execution or cost measurements |
| 120 — final capstone | Seven deliveries including replayed event 2; six unique events; four latest orders, three active, one tombstone; East 2/70, West 1/30, total 100. | No actual pipeline, CDC durability, or database runtime execution |

## Findings and corrections

- **NAV-117 and NAV-118 — resolved:** Both chapters described already-published successors as “planned”. Updated direct relative links to published Chapters 118 and 119, respectively. Commits: `5c928c7378239d38e99fb64dd5abd2a96757ee27` and `9d63468af6ec555349cc0a7154cc8bb085bf80ed`.
- **QA-115-120-RUNTIME — open:** SQL assertions are authored and calculated, not observed. Database-name and major-version guards alone cannot establish an isolated host; verify container identity and credentials out of band.
- **QA-117-120-PSQL — open operational safeguard:** Labs 117–120 do not embed `\\set ON_ERROR_STOP on`; execute with `psql -X -v ON_ERROR_STOP=1` to fail on SQL errors, after independent disposable-instance verification. No SQL was executed here.
- **QA-115-119-DIALECT — open:** PostgreSQL comparison labs do not validate the named vendor engines. Retain version-scoped cross-engine evidence before certifying portability.

## Coverage and next acceptance gates

**Cumulative targeted SQL static/expected-output review: 120/120** (this six-chapter batch closes the previously reported 114/120). Previously reported targeted structural QA: **120/120**; authored/published: **120/120**. Independent editorial review: **0/120**. Actual isolated PostgreSQL 18 runtime validation: **0/120**.

Next: comprehensive Markdown link/anchor audit for the complete `sql-tutorials/` tree; parser-based PostgreSQL SQL syntax checks (with `psql` metacommands handled separately); independent editorial review; isolated PostgreSQL 18 runtime acceptance with immutable version, container identity, exact commands, logs, expected/observed results and cleanup evidence. Separately test cross-engine dialect examples on disposable vendor instances. Do not modify production systems or use production credentials.
