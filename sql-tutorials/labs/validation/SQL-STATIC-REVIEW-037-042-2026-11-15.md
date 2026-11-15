# SQL targeted static review — Chapters 037–042 (2026-11-15)

**Scope:** GitHub `main`, exclusively `sql-tutorials/`. Reviewed the current `MASTER-TOC.md`, `README.md`, `STATUS-TRACKER.md`, six published chapter Markdown files (037–042), and six corresponding lab SQL files. The six chapter/lab mappings were checked against the README. Chapter authoring is frozen at **120/120**.

**Method and limits:** Source inspection and manual deterministic arithmetic/cardinality reasoning. No PostgreSQL server was connected, no SQL executed, no parser-based syntax certification, no external links checked, and no independent editorial approval obtained. Assertions in SQL files are *proposed executable checks*, not actual runtime evidence. Host, port, role and isolation must be verified independently before any execution. Database-name and version checks do not prove a disposable environment.

| Chapter | Lab | Targeted reasoning and expected outcomes | Safety / limits |
|---|---|---|---|
| 037 RETURNING / OUTPUT | `../037-returning-output-write-verification.sql` | Seed 101=12.50 pending, 102=18.00 pending, 103=9.25 settled. UPDATE 101 to reviewed; INSERT 104=20.00; DELETE 102=18.00. Final keys 101,103,104, count 3, sum 41.75, reviewed 1. Expected DML RETURNING count one each. | TEMP table; explicit transaction and ROLLBACK; fail-closed checks; PostgreSQL RETURNING is not universal SQL. |
| 038 Transaction and savepoint | `../038-begin-commit-rollback-savepoint.sql` | Initial balances 100.00+50.00=150.00; transfer 20 gives 80.00+70.00; optional transfer 5 gives 75.00+75.00; rollback to savepoint restores 80.00+70.00. | TEMP table, guarded UPDATE row counts, final ROLLBACK; no durable COMMIT is tested. |
| 039 Isolation | `../039-isolation-levels-transaction-anomalies.sql` | Inline inventory A=10 B=5, total=15; hypothetical reservation of 2 leaves A=8. Three transaction modes checked: read committed, repeatable read, serializable. | READ ONLY transaction for each mode, each rolled back. **Single session cannot reproduce nonrepeatable reads, phantoms, write skew or serialization failures.** The examples explain these conceptually only. |
| 040 Transaction capstone | `../040-lab-04-safe-auditable-transaction.sql` | Orders 40+35+25=100; savepoint rollback preserves order 1002 pending. Final in-transaction state: 3 orders, 1 paid, 2 pending, 1 payment of 40, 1 audit row, order total 100. | TEMP tables, FK and unique constraints, guarded update count, final ROLLBACK. Audit row is synthetic and not durable. |
| 041 Join cardinality | `../041-join-fundamentals-cardinality.sql` | Customers 3; orders 3; inner rows 3; LEFT rows 4 (Ada twice, Ben once, Cy unmatched); order-item rows 4; distinct ordering customers 2; order revenue 20+30+15=65. | TEMP tables; fan-out warning: summing order amount after joining items would overcount. Final ROLLBACK. |
| 042 INNER JOIN | `../042-inner-join-matched-records.sql` | Staged orders 4/74.00; matched 3/65.00; unmatched 1/9.00; distinct matched customers 2; matched amount >=25: 1 row (order 102). Conservation 65+9=74. | Staging intentionally includes unmatched customer 99; audit via NOT EXISTS. TEMP tables, final ROLLBACK. |

## Targeted checks

- Six chapter numbers and corresponding SQL lab names match the published README entries and the Master TOC order.
- No contradictions found in the **specific** expected numeric results and cardinalities above. This does **not** prove full SQL semantics or expected output across every statement.
- All six SQL scripts include PostgreSQL version/database guard text, transaction boundaries, timeouts and explicit ROLLBACK. Chapters 037, 038, 040, 041, 042 include TEMP DDL/DML and **must only be run on an independently verified disposable PostgreSQL 18 instance**. Chapter 039 is read-only.
- Chapter 039's isolation examples must not be described as demonstrated concurrent anomalies. Chapter 038's COMMIT discussion is conceptual, not executed.
- Version checks in 041 and 042 allow versions above 18, unlike 037–040; the course's PostgreSQL **18** runtime acceptance still requires recording `server_version_num` within 180000–189999 on the isolated target. This is a portability/scope follow-up, not a claim of tested incompatibility.
- No chapter edits were necessary based on this targeted review. No production system was accessed.

## Validation state and next steps

**Published:** 120/120 chapters. **Targeted structural QA:** previously reported 120/120. **Targeted SQL expected-output static review:** 42/120 after this batch. **Independent editorial review:** 0/120. **Actually executed on isolated PostgreSQL 18 with retained evidence:** 0/120.

Next: static SQL review Chapters **043–048**; then comprehensive Markdown-aware local path and anchor checks, semantic/syntax review and expected-output QA; isolated PostgreSQL 18 execution only after independent environment verification. Retain command, server identity/version, exit code, stdout/stderr, assertions and cleanup evidence for every actual runtime acceptance.
