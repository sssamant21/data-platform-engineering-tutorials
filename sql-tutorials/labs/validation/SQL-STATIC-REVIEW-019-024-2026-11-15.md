# SQL targeted static review — Chapters 019–024 (2026-11-15)

**Scope:** Six published SQL labs on GitHub `main`. Source-based reasoning only; **no SQL executed**. This does not establish parser acceptance, runtime safety, independent editorial certification, or PostgreSQL 18 validation.

| Chapter | Lab | Targeted expected-result reasoning | Guardrail notes |
|---|---|---|---|
| 019 | `../019-case-coalesce-nullif.sql` | CASE priorities and COALESCE owners follow the six VALUES rows. Error rates: 5.00, NULL (zero denominator), 4.00, 0.00, NULL, NULL. Array assertions use NULL-safe `IS NOT DISTINCT FROM`. | Read-only transaction, 10s timeout, PostgreSQL 18/database check, ROLLBACK. |
| 020 | `../020-lab-02-filter-and-rank-operational-records.sql` | Filter keeps 401,402,403,405,407,408. Severity asc, latency desc NULLS LAST, ID tie-breaker gives 401,407,403,405,408,402; service counts api:2,billing:1,ingest:1,search:2. | Read-only transaction, 10s timeout, PostgreSQL 18/database check, ROLLBACK. |
| 021 | `../021-entity-relationships-conceptual-modeling.sql` | Customer C03 lacks an order; O100 has two lines (2×12.50 + 7.00 = 32.00); O101 has one line (2×7.50 = 15.00); orphan count zero. | Read-only transaction, 10s timeout, DO-based version/database guard, ROLLBACK. |
| 022 | `../022-create-schema-and-tables-isolated.sql` | Two customers, two orders, 32.00 + 15.50 = 47.50; orders table declares one foreign key. Rollback should remove newly created schema and tables. | **Transactional DDL and INSERT**, not read-only. Explicit disposable-primary prerequisite, version/database/schema-existence guard, lock/statement/idle timeouts, ROLLBACK and post-rollback schema assertion. |
| 023 | `../023-choosing-sql-data-types.sql` | 19.95+10.50+25.00+12.00+20.00+4.00 = 91.45; four non-NULL Boolean states; two NULLs. Nov 1 2026 14:30 UTC is 09:30 New York (EST). | Read-only transaction, 10s timeout, version/database/recovery guard, ROLLBACK. |
| 024 | `../024-primary-natural-surrogate-unique.sql` | Three orders, two tenants, three composite business keys; 19.95+10.50+25.00 = 55.45; two NULL emails permitted under default PostgreSQL UNIQUE semantics; duplicate T1/A-100 should raise unique_violation. | **Temporary-table DDL and INSERT**, not read-only. Explicit disposable-primary prerequisite, version/database/recovery guard, timeouts, ROLLBACK. |

## Findings and limitations

- No arithmetic or expected-row contradiction identified in the **targeted source-based review**.
- All six labs use synthetic values. Two labs (022, 024) execute writes/DDL **if run**; they must never be executed on production, regardless of database name. A matching `sql_tutorials` database name and version **cannot prove isolation**. Independently verify host, cluster identity, credentials, and disposable environment before execution.
- `psql -X -v ON_ERROR_STOP=1` is recommended by labs that document an invocation; use it for acceptance. SQL-only review does not verify client invocation or execution semantics.
- Chapter 022's post-rollback check is a catalog read outside the explicit transaction; it checks schema absence, not complete absence of all side effects in an arbitrary non-isolated environment.
- No comprehensive parser check, Markdown-aware anchor validation, independent editorial review, or external-link verification performed in this batch.
- Actual PostgreSQL 18 runtime validation: **0/120**, pending isolated execution and retained commands, logs, exact server version, cluster identity and results.

## Cumulative status and next action

Authored/published **120/120**; targeted structural QA **120/120** (previously reported); targeted SQL expected-output static review **24/120** (001–024); independent editorial review **0/120**; actual isolated PostgreSQL 18 runtime validation **0/120**.

**Next:** Chapters 025–030 targeted SQL semantic/expected-output review; comprehensive Markdown-aware local link/anchor checks; isolated PostgreSQL 18 acceptance with reproducible evidence.
