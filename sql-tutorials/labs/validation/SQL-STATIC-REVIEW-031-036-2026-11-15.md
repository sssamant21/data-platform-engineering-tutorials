# Targeted SQL static review — Chapters 031–036 (2026-11-15)

## Scope and method

Read current `main` MASTER-TOC.md, README.md, STATUS-TRACKER.md, all six chapter Markdown files (031–036), and their six SQL labs. Reviewed SQL statements textually for synthetic-data expected values, constraints, transaction boundaries, PostgreSQL-specific syntax, and dangerous operations. **No SQL was executed; no PostgreSQL 18 instance was provisioned.** This is not a complete parser-based syntax check, independent editorial review, runtime acceptance, or production safety certification.

## Per-chapter source-based checks

| Chapter | Targeted reasoning and expected output | Safety / portability |
|---|---|---|
| 031 INSERT | Three accepted rows, amounts 12.50 + 20.00 + 7.25 = **39.75**; statuses NEW, READY, HELD. Negative tests expect SQLSTATE 23505, 23514, 23502 and catch errors within nested exception blocks. | PostgreSQL PL/pgSQL DO, TEMP table, transactional rollback. |
| 032 INSERT SELECT | Five staged rows; three accepted (EV-101, EV-102, EV-104), two rejected (negative and NULL); accepted sum **39.75**. | Temporary staging/curated tables, INSERT SELECT, rollback. |
| 033 UPDATE | Four rows initially total **44.75**; only EV-102 qualifies for status change; pending IDs EV-101/EV-104, reviewed EV-102/EV-103; total unchanged. | Preview and exact-key assertion before UPDATE; PostgreSQL RETURNING in data-modifying CTE. |
| 034 DELETE | O-102 is the only cancelled candidate; remaining O-101/O-103, two customers, zero orphans. Removing C-01 while O-101 references it should raise SQLSTATE 23503. | PostgreSQL RETURNING, temporary FK tables, caught expected FK failure. |
| 035 DELETE/TRUNCATE/DROP | Three initial rows; DELETE removes EV-003 leaving two; TRUNCATE leaves zero but retains table; DROP makes temp table absent. | TRUNCATE and DROP explicitly scoped to `pg_temp`, no CASCADE, rollback. |
| 036 UPSERT/MERGE | Initial A:10/v1, B:5/v2. UPSERT yields A:12/v2, B:5/v2, C:7/v1; changed keys A/C. MERGE yields A:12/v2, B:8/v3, C:7/v1, D:4/v1; total **31**. Replay same MERGE should leave state unchanged. | PostgreSQL ON CONFLICT DO UPDATE WHERE, MERGE; version-aware replacement, not increment. |

## Findings and limitations

- **No contradictory arithmetic or expected row counts identified** in these six targeted source-based examples. Assertions are present in each SQL file, but their actual behavior is **unverified**.
- All six scripts use `BEGIN`, local lock/statement/idle timeouts, a PostgreSQL 18/database/standby check, temporary tables, and `ROLLBACK`. Chapter 036 also sets psql `ON_ERROR_STOP` internally; other files' documented invocation uses `-v ON_ERROR_STOP=1`. Without that invocation, a SQL error may allow later statements to continue. Prefer a trusted wrapper that verifies host/port/container identity and enforces fail-fast.
- **Important:** database name, server version, rollback and temporary tables do not prove isolation. Run only against an independently verified disposable PostgreSQL 18 instance with nonproduction credentials. The lab uses DML and Chapter 035 demonstrates destructive DDL. Do not run on production.
- The expected-error handling and MERGE semantics require real PostgreSQL 18 execution to certify. Concurrent writes, privilege differences, and environment-specific behavior are not tested. External URLs, all Markdown anchors, and complete SQL parsing were not checked.
- **Review state:** authored/published 120/120 (previously reported); targeted structural QA 120/120 (previously reported); cumulative targeted SQL expected-output static review **36/120**; independently editorially reviewed **0/120**; actually PostgreSQL 18 runtime-validated **0/120**.

## Next work

Review Chapters **037–042** and their SQL labs for source-based semantics, expected results, transaction safety, and dialect-specific behavior. Separately perform comprehensive Markdown-aware link/anchor and SQL syntax checks. Isolated PostgreSQL 18 execution with recorded image/version, connection isolation evidence, commands, outputs, errors and rollback/cleanup evidence is required before any runtime acceptance claim.
