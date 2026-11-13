# 118 — SQL Server/T-SQL and Oracle SQL: Key Differences

**Part 12 — Data Engineering, SQL Dialects & Final Projects · 60 minutes · Audience:** beginner SQL practitioners, data engineers, DBREs, and SREs.

**Validation:** Authored teaching material with calculated expectations. Independent editorial review, comprehensive static/link QA, PostgreSQL 18 runtime execution, and SQL Server/Oracle cross-engine execution are **pending**. SQL Server and Oracle snippets are illustrative and are **not** executed by the PostgreSQL companion lab.

## 1. Learning outcomes and prerequisites (0–5 minutes)

By the end, distinguish portable SELECT logic from T-SQL and Oracle extensions; translate pagination, NULL handling, date arithmetic, identity generation, and upsert concepts; design safe cross-engine regression tests; and identify operational hazards in migrations.

Prerequisites: [003 — isolated PostgreSQL lab setup](../part-01-fundamentals/003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md), [036 — UPSERT and MERGE](../part-04-data-modification/036-upsert-and-merge-patterns-across-sql-dialects.md), [115 — portability testing](115-portable-sql-versus-vendor-specific-syntax-and-testing.md), and [117 — MySQL/MariaDB comparison](117-mysql-and-mariadb-key-syntax-and-behavior-differences.md).

**Agenda:** outcomes 5 min; concepts 10; examples 15; lab 20; troubleshooting 5; review 5.

## 2. Concepts and comparison matrix (5–15 minutes)

SQL Server implements Transact-SQL (T-SQL). Oracle Database has its own SQL extensions and PL/SQL procedural language. Behavior depends on product version, database compatibility level, session settings, collation, and column types. ANSI/ISO-style constructs such as SELECT, JOIN, WHERE, CASE, COALESCE, and GROUP BY are a useful starting point, but portability is not guaranteed merely because syntax parses.

| Topic | PostgreSQL 18 | SQL Server / T-SQL | Oracle SQL | Migration concern |
|---|---|---|---|---|
| First N rows | `LIMIT 5` or `FETCH FIRST 5 ROWS ONLY` | `TOP (5)` or `OFFSET … FETCH NEXT` | `FETCH FIRST 5 ROWS ONLY` (supported releases) | Add a deterministic unique ORDER BY; TOP without ORDER BY is nondeterministic |
| Page 2, five rows | `ORDER BY id OFFSET 5 ROWS FETCH NEXT 5 ROWS ONLY` | `ORDER BY id OFFSET 5 ROWS FETCH NEXT 5 ROWS ONLY` | Same standard-style form | SQL Server OFFSET/FETCH requires ORDER BY |
| Null substitution | `COALESCE(x,0)` | `COALESCE(x,0)` or `ISNULL(x,0)` | `COALESCE(x,0)` or `NVL(x,0)` | Type precedence/conversion differs; COALESCE is the portable preference |
| Text concatenation | `a || b` | `CONCAT(a,b)` or `a + b` | `a || b` | NULL and implicit conversion behavior differ |
| Identity | `GENERATED ... AS IDENTITY` | `IDENTITY(seed,increment)` | Identity columns or sequences | Do not infer gapless keys or identical generated-key retrieval |
| Current time | `CURRENT_TIMESTAMP` | `SYSDATETIMEOFFSET()`, `SYSUTCDATETIME()` | `CURRENT_TIMESTAMP`, `SYSTIMESTAMP` | Timestamp precision and timezone types differ |
| Date arithmetic | `date + INTERVAL '1 day'` | `DATEADD(day,1,dt)` | `dt + INTERVAL '1' DAY` for compatible types | Test DST, date-vs-timestamp types, and month-end |
| Returning write results | `RETURNING` | `OUTPUT inserted.id` | `RETURNING ... INTO` (context-dependent) | Do not copy syntax verbatim |
| Conditional writes | `INSERT ... ON CONFLICT` | `UPDATE`/`INSERT` with explicit locking/isolation, or carefully designed `MERGE` | `MERGE` | Concurrency, duplicate source keys, and constraint handling require independent tests |
| Empty string | Distinct from NULL | Usually distinct from NULL | Zero-length character string treated as NULL in common character SQL semantics | Mandatory test for data-quality and migration pipelines |
| Identifier case | Unquoted folds to lower case | Case sensitivity depends on collation/configuration | Unquoted folds to upper case | Avoid accidental quoted-case dependencies |

**Version note:** Oracle legacy `ROWNUM` and SQL Server `TOP` are vendor-specific; do not substitute one for the other mechanically. Oracle `ROWNUM` filtering before ordering can select different rows from an ordered top-N query. SQL Server `NOLOCK` / `READ UNCOMMITTED` is not a safe general performance fix: it permits inconsistent reads. Oracle implicit commits around DDL and SQL Server DDL/transaction behavior must be assessed statement by statement; do not assume PostgreSQL rollback guarantees apply.

## 3. Worked examples: synthetic service orders (15–30 minutes)

Assume the logical data below (no production data):

| order_id | region | amount |
|---:|---|---:|
| 201 | East | 25.00 |
| 202 | East | NULL |
| 203 | West | 40.00 |
| 204 | West | 15.00 |
| 205 | East | 20.00 |

### 3.1 Portable aggregate and NULL semantics

```sql
SELECT region, COUNT(*) AS orders,
       COUNT(amount) AS priced_orders,
       SUM(amount) AS revenue
FROM orders
GROUP BY region
ORDER BY region;
```

Calculated results: East / 3 / 2 / 45.00; West / 2 / 2 / 55.00. Overall revenue is 100.00. `COUNT(amount)` excludes NULL; `COUNT(*)` includes all rows. `SUM` ignores NULL but an all-NULL group returns NULL. For a deliberate zero substitute, use `COALESCE(SUM(amount),0)` and document whether missing prices represent zero or unknown.

### 3.2 Deterministic pagination

Portable-style SQL supported by the relevant modern versions:

```sql
SELECT order_id, region
FROM orders
ORDER BY order_id
OFFSET 2 ROWS FETCH NEXT 2 ROWS ONLY;
```

Calculated rows: 203/West and 204/West. SQL Server also supports `SELECT TOP (2) ... ORDER BY order_id` for the first page; Oracle supports `FETCH FIRST 2 ROWS ONLY`; PostgreSQL also supports `LIMIT 2 OFFSET 2`. A stable unique sort key is necessary but does not alone guarantee consistent pages across concurrent updates; use snapshot/keyset strategies when required.

### 3.3 Oracle empty-string trap

```sql
-- Conceptual comparison: evaluate on each target engine, not in this PG lab.
SELECT CASE WHEN '' IS NULL THEN 'null' ELSE 'not null' END AS classification;
```

Oracle commonly classifies a zero-length character string as NULL, unlike PostgreSQL and SQL Server. This matters when migrating optional identifiers, external keys, CSV blanks, and audit fields. Explicitly define the source-to-target contract for empty versus missing values. Oracle's future behavior should not be assumed unchanged across all releases.

### 3.4 DML syntax differs: illustrative only

SQL Server:
```sql
-- Disposable test table only; syntax example, not a production instruction.
UPDATE dbo.orders SET amount = 30.00
OUTPUT inserted.order_id, inserted.amount
WHERE order_id = 201;
```

PostgreSQL:
```sql
UPDATE orders SET amount = 30.00
WHERE order_id = 201
RETURNING order_id, amount;
```

Oracle SQL / PL/SQL contexts use `RETURNING ... INTO` rather than copying either form. These are **not executed** in the read-only lab. For production change requests, require an exact row-count preview, approval, transaction plan, backup/restore assessment, lock and log-growth estimates, and verified rollback/forward-fix.

### 3.5 DBRE/SRE incident case: inconsistent KPI after migration

A pipeline reports 100.00 in the source but 80.00 in the target. Investigate missing row 205, duplicate join fan-out, NULL handling, collation, and cutoff/watermark semantics before changing the query. Compare at the **same grain** (one order_id per row), then reconcile key sets and amount values. A matching aggregate alone cannot prove row-level equality.

## 4. Hands-on isolated PostgreSQL 18 lab (30–50 minutes)

Run [Chapter 118 SQL lab](../labs/118-sql-server-oracle-portability-comparison.sql) only on a **disposable PostgreSQL 18** instance with database `sql_tutorials`. It uses CTE `VALUES` rows, a read-only transaction, transaction-local timeouts, database/version guards, duplicate-aware bidirectional `EXCEPT ALL` assertions, and `ROLLBACK`. Database-name/version guards are defense in depth, **not** proof of isolation.

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials \
  -f sql-tutorials/labs/118-sql-server-oracle-portability-comparison.sql
```

Tasks: (1) inspect the safety guard; (2) calculate regional counts and revenue; (3) retrieve page two using `OFFSET/FETCH`; (4) compare `COUNT(*)` and `COUNT(amount)`; (5) examine `NOT IN` with NULL versus `NOT EXISTS`; (6) verify assertion logic; (7) document why PostgreSQL results **do not certify** SQL Server or Oracle.

**Calculated, not observed expectations:** five orders, four priced orders, one NULL, revenue 100.00, East 45.00, West 55.00, page IDs 203/204, one unmatched order ID (205) with `NOT EXISTS`, zero rows for `NOT IN` with a NULL-bearing exclusion set, and zero assertion differences.

**Cross-engine acceptance design (not executed):** in separate disposable SQL Server and Oracle instances, record product/version, database compatibility level, session collation and settings, execution SQL, result rows, data types, query plans where appropriate, and error messages. Test empty string, nulls, pagination, identity, timestamp conversion, and concurrent upsert separately. Store reproducible evidence and mark each engine pass/fail; do not label this PostgreSQL lab a SQL Server or Oracle test.

## 5. Troubleshooting and safety (50–55 minutes)

- **Different row pages:** require ORDER BY with unique tie-breaker; compare isolation level and data snapshot.
- **Missing blanks after migration:** test Oracle empty-string-as-NULL semantics and upstream normalization; do not silently convert unknown to zero.
- **Unexpected duplicate updates:** check unique constraints, MERGE source cardinality and concurrency; never retry blind mass DML.
- **Date shifts:** capture source/target time zones and type mappings; test daylight-saving transitions and precision.
- **Unexpected locks/log growth:** capture engine-specific blocking, plans, transaction log/redo/undo metrics; avoid production DDL, `NOLOCK` shortcuts or unapproved hints.
- **Lab guard fails:** stop; verify isolated PostgreSQL 18 and `sql_tutorials`; do not bypass the guard or point it at production.
- **Assertion fails:** compare both sides of `EXCEPT ALL`, then inspect type casts, NULL semantics and dataset literals; do not claim validation.

## 6. Review questions with answers (55–60 minutes)

1. **Is `TOP` portable SQL?** No; it is T-SQL syntax. Use an engine-supported FETCH form with deterministic ordering.
2. **What does `COUNT(amount)` return here?** Four, because one amount is NULL.
3. **What is the regional revenue?** East 45.00, West 55.00, total 100.00.
4. **Why is Oracle empty string important?** Empty character strings may be treated as NULL, affecting filters, uniqueness and ingestion reconciliation.
5. **Can a matching total certify migration accuracy?** No; reconcile keys, duplicates and row-level values.
6. **Does the PostgreSQL lab prove T-SQL/Oracle behavior?** No; those require separate isolated engine execution.
7. **Why not use SQL Server NOLOCK as a universal fix?** It can return inconsistent or uncommitted data.
8. **What is the safe way to validate an upsert migration?** Isolated concurrency, duplicate-key, constraint and replay tests with observed evidence.

**Next:** Chapter 119 — Snowflake and BigQuery: cloud analytical SQL patterns (planned; [Master TOC](../MASTER-TOC.md)).

## Authoritative references

- [Microsoft Learn — SELECT ORDER BY / OFFSET FETCH](https://learn.microsoft.com/en-us/sql/t-sql/queries/select-order-by-clause-transact-sql)
- [Microsoft Learn — TOP](https://learn.microsoft.com/en-us/sql/t-sql/queries/top-transact-sql)
- [Microsoft Learn — OUTPUT clause](https://learn.microsoft.com/en-us/sql/t-sql/queries/output-clause-transact-sql)
- [Microsoft Learn — transaction isolation levels](https://learn.microsoft.com/en-us/sql/t-sql/statements/set-transaction-isolation-level-transact-sql)
- [Oracle Database SQL Language Reference](https://docs.oracle.com/en/database/oracle/oracle-database/23/sqlrf/)
- [Oracle — row limiting clause](https://docs.oracle.com/en/database/oracle/oracle-database/23/sqlrf/SELECT.html)
- [PostgreSQL 18 — SELECT](https://www.postgresql.org/docs/18/sql-select.html)
- [PostgreSQL 18 — transaction control](https://www.postgresql.org/docs/18/tutorial-transactions.html)

**Acceptance:** Authored/published is not independent review, comprehensive parser QA, SQL Server/Oracle validation or PostgreSQL 18 runtime certification.
