# Targeted SQL static review — Chapters 085–090 (2026-11-15)

**Scope:** Existing Chapters 085–090 in Part 09 and corresponding `labs/085-*.sql` through `labs/090-*.sql`, read from GitHub `main`. No new chapters were authored. This is manual/source-based reasoning, **not** PostgreSQL execution, parser-based syntax validation, independent editorial review, or comprehensive link/anchor QA.

| Chapter | Reviewed contract and synthetic expected results | Assessment |
|---|---|---|
| 085 — Views | Paid-order customer totals: Ada 50.00 (2), Ben 15.00 (1), Cy 0.00 (0), Dee 7.50 (1); four paid orders, 72.50 total. Adding pending 99.00 produces 171.50. | Arithmetic consistent; lab models a view-shaped CTE, not a created view or real access-control test. |
| 086 — Materialized views | Cutoff snapshot: api 2 / 50.00, file 1 / 15.00; live: api 3 / 60.00, file 1 / 15.00; lag 10.00, live total 75.00. | Arithmetic consistent; lab simulates refresh, not materialized-view creation or concurrent refresh. |
| 087 — Temporary tables | Customer 101: 3 paid / 30.00; 102: 1 paid / 20.00; four paid source rows, total 50.00. | Arithmetic consistent; CTE demonstration does not create a temporary table. |
| 088 — Stored routines | Invoice fees 5.00, 4.00, 0.00; total fees 9.00 and invoice totals 105.00, 44.00, 20.00 (sum 169.00). | Arithmetic consistent; built-in `abs(numeric)` catalog metadata assertion and syntax still need PostgreSQL 18 execution. No stored routine created. |
| 089 — Triggers and dynamic SQL | Four changed rows (101, 103, 104, 105), one unchanged (102); paid transition only 101; NULL-to-pending transition preserved. | Logic consistent; parameter-like CTE is not driver parameter binding; no actual trigger or dynamic SQL executed. |
| 090 — Reporting capstone | Four customers, six orders, four paid; Aster 50.00, Birch 25.00, Cedar 10.00, Dune 0.00; live 85.00, snapshot 75.00, gap 10.00. | Arithmetic consistent; synthetic read-only report contract, not deployed reporting objects. |

## Validation and safety boundaries

All six canonical SQL labs begin read-only transactions, apply transaction-local timeouts, check `sql_tutorials` and PostgreSQL major version 18, use inline synthetic data, and end with `ROLLBACK`. The database-name/version guard does **not** establish isolation. Execute only after independently verifying a disposable PostgreSQL 18 instance and non-production credentials. Use `psql -X -v ON_ERROR_STOP=1`, retain command, server version, database identity, stdout/stderr, exit code, and results. No SQL was executed during this review.

The examples use PostgreSQL-specific features including `::numeric`, `jsonb`, `FILTER`, `IS DISTINCT FROM`, `EXCEPT ALL`, and `pg_catalog.regprocedure`; portability must not be assumed. Bidirectional `EXCEPT ALL` checks and fail-closed arithmetic guards were inspected, not executed.

**Open coverage gaps:** real view privileges/RLS, materialized-view locking and refresh, temporary-table lifecycle, routine creation and privileges, trigger side effects, actual bound driver parameters, and deployed reporting objects are conceptual-only in these read-only labs. A disposable write-enabled integration suite is required to validate those behaviors. These are limitations, not claims that the current read-only labs performed those operations.

**Result:** No arithmetic contradiction found in the targeted synthetic expectations. No edits to chapters/labs made. Independent editorial review: 0/120; actual isolated PostgreSQL 18 runtime acceptance: 0/120. Cumulative targeted SQL expected-output static review: **90/120**. Previously reported targeted structural QA: 120/120 (not re-audited here).

**Next:** Chapters 091–096 targeted semantic/expected-output review; repository-wide Markdown path and anchor verification; parser-based SQL syntax checks; isolated PostgreSQL 18 runtime evidence and separately scoped disposable integration tests for stateful features.
