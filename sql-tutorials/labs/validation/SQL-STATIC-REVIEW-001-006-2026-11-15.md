# SQL Tutorials — SQL static semantic review, Chapters 001–006 (2026-11-15)

## Scope and method

Reviewed the six published SQL lab files on GitHub `main` (001-first-queries.sql, 002-relational-architecture.sql, 003-lab-smoke-test.sql, 004-databases-schemas-tables-rows-columns.sql, 005-records-relationships-keys.sql, 006-statement-anatomy-logical-processing.sql), their associated chapter Markdown, and the current MASTER-TOC.md, README.md, and STATUS-TRACKER.md. This is **human static reasoning from source**, not SQL parser certification, an independent editorial review, or runtime execution. No database was connected to and no SQL was executed.

## Source review and expected-output reasoning

| Chapter | Key manually reasoned result | Findings and limitations |
|---|---|---|
| 001 | Four orders, three paid (1001, 1003, 1004); paid sum 120 + 40 + 60 = 220.00 | CTE-scoped synthetic data; PostgreSQL numeric cast is vendor-specific. No environment assertion or explicit read-only transaction, although statements are SELECT-only. |
| 002 | INNER JOIN returns three rows (101, 102, 103); LEFT JOIN counts Ava=2, Noah=1, Mia=0 | Correct use of COUNT(o.order_id) rather than COUNT(*). Session metadata and pg_stat_activity are PostgreSQL-specific and environment-dependent. No explicit lab database/version assertion or read-only transaction. |
| 003 | Four synthetic orders; paid count=3, revenue=220.00; PASS when assertions succeed | Version range 180000–189999 and lab database/role checks included. Uses SELECT-only queries but no BEGIN READ ONLY; runtime behavior of assertion/error handling unverified. |
| 004 | Four rows, paid=3, paid total 45.50+24.50+10.00=80.00, distinct customers=3 | BEGIN READ ONLY, version/database assertions and ROLLBACK. Catalog inventory is environment-dependent; final PASS literal alone is not evidence of runtime success. |
| 005 | Three customers, three orders, four LEFT JOIN rows; one unmatched customer; total=95.00; one staged orphan (5004,999); zero duplicate order/product pairs | BEGIN READ ONLY, version/database assertions and ROLLBACK. Expected results consistent with VALUES data. |
| 006 | Six orders, five paid, three customer groups, paid total=180.00; two groups >=50; top customer 102 at 90.00 | BEGIN READ ONLY, version/database assertions and ROLLBACK. Expected results consistent with VALUES data. |

## Static safety observations

- All six files use SELECT/CTE-based synthetic records and no persistent data modification. Chapters 004–006 additionally bracket queries in explicit read-only transactions.
- Chapters 001–003 lack an explicit `BEGIN READ ONLY` / `ROLLBACK` envelope. They remain SELECT-only in their present form, but this is a guardrail-consistency improvement opportunity, **not** evidence that writes occurred.
- The `1 / CASE ... THEN 1 ELSE 0 END` assertion technique requires a client that stops on SQL errors, such as `psql -v ON_ERROR_STOP=1`. Verify error propagation during runtime acceptance.
- Some outputs depend on environment: current role, database, schema, PostgreSQL version, backend PID, catalog tables, and pg_stat_activity visibility.
- The Chapter 003 smoke test explicitly requires role `sql_lab` and database `sql_tutorials`; it should only be run against the isolated lab.
- The Chapter 001–006 Markdown link inventory identifies relative targets but **does not** constitute a complete Markdown-aware anchor, reference-style link, HTML link, or external URL check.

## Validation state

- **Authored/published:** 120/120 chapters (per current tracker).
- **Targeted structural QA:** 120/120 chapters (per current tracker).
- **Targeted manual SQL expected-output reasoning:** 6/120 labs in this report.
- **Independent editorial review:** 0/120.
- **Actually executed on isolated PostgreSQL 18 with retained logs:** 0/120.
- **Full syntax/semantic certification:** pending. Static reasoning cannot substitute for PostgreSQL 18 execution.

## Next milestone

Review Chapters 007–012 SQL files and expected outputs, then expand to complete lab-wide SQL semantic/safety checks. Independently perform a Markdown-aware link/anchor audit. Run PostgreSQL 18 acceptance only in an isolated disposable instance, with reproducible commands, version/role/database proof, stdout/stderr, exit status, and expected-output comparisons. Do not mark runtime validated before evidence exists.
