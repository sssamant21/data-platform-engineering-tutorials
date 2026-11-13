# 117 — MySQL and MariaDB: Key Syntax and Behavior Differences

**Part 12 — Data Engineering, SQL Dialects & Final Projects · 60 minutes · Audience:** beginner data engineers, analysts, DBREs and SREs.

**Validation:** Authored tutorial; calculated expectations only. Independent editorial review, comprehensive static QA, MySQL/MariaDB execution and isolated PostgreSQL 18 runtime validation are **pending**. The companion SQL lab exercises portable comparisons on PostgreSQL 18; it does **not** execute MySQL or MariaDB syntax.

## 1. Outcomes and prerequisites (0–5 minutes)

By the end, explain important MySQL/MariaDB versus PostgreSQL SQL differences; predict NULL, collation, pagination and upsert behavior; identify transactional and operational hazards; and design dialect-specific acceptance tests.

Prerequisites: [003 — PostgreSQL 18 lab setup](../part-01-fundamentals/003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md), [036 — UPSERT and MERGE](../part-04-data-modification/036-upsert-and-merge-patterns-across-sql-dialects.md), [115 — portability testing](115-portable-sql-versus-vendor-specific-syntax-and-testing.md), and [116 — PostgreSQL 18 baseline](116-postgresql-18-sql-lab-baseline-and-advanced-features.md).

**Agenda:** outcomes 5 min; concepts 10; walkthrough 15; lab 20; troubleshooting 5; review 5.

## 2. SQL dialects and operational behavior (5–15 minutes)

MySQL and MariaDB share historical syntax, but they are **different products** with diverging features and release schedules. Always record the exact server family, version, storage engine, SQL mode and connection character set/collation. Do not assume a query tested on one is certified on the other.

| Concern | PostgreSQL 18 | MySQL / MariaDB | Risk and action |
|---|---|---|---|
| Pagination | `LIMIT 10 OFFSET 20`, or standard `OFFSET … FETCH` | `LIMIT 10 OFFSET 20` or `LIMIT 20,10` | Always specify unique `ORDER BY`; offsets can skip/duplicate under concurrent writes |
| Identifier quotes | `"mixedCase"` | Backticks by default; double quotes with `ANSI_QUOTES` SQL mode | Avoid quoted mixed-case identifiers; inspect SQL mode |
| Concatenation | `a || b` | `CONCAT(a,b)` is conventional; `||` normally means logical OR unless `PIPES_AS_CONCAT` | Prefer explicit dialect adapter; `CONCAT` NULL behavior matters |
| Case-insensitive matching | `ILIKE` extension or `LOWER` | Depends on selected collation; `LOWER` plus compatible collation is not always identical | Explicitly test Unicode, accents, case and indexes |
| Boolean | Native `boolean` | `BOOLEAN` commonly aliases `TINYINT(1)`; values beyond 0/1 may be stored unless constrained | Add explicit integrity checks |
| JSON | `jsonb` and PostgreSQL operators | MySQL JSON type and functions; MariaDB JSON alias is generally text-based | Test storage, validation, paths, indexing and null semantics per engine |
| UPSERT | `INSERT … ON CONFLICT … DO UPDATE` | `INSERT … ON DUPLICATE KEY UPDATE` | Multiple unique indexes and affected-row counts require separate review |
| Ignore conflicts | `ON CONFLICT DO NOTHING` | `INSERT IGNORE` can suppress or downgrade more than duplicate-key errors depending on mode | Do not treat as interchangeable |
| Date arithmetic | `date + INTERVAL '1 day'` | `DATE_ADD(date, INTERVAL 1 DAY)` | Parameterize timezone and test boundaries |
| Auto-generated keys | Identity/sequence, `RETURNING` | `AUTO_INCREMENT`, `LAST_INSERT_ID()` | Identity allocation and retrieval are connection-specific |
| Transactions | Transactional DDL depends on operation | Many DDL operations implicitly commit; engine-specific atomic DDL is not general transactional rollback | Never promise rollback of DDL without verifying exact statement/engine |

**Important:** MySQL 8.x and MariaDB 10.x/11.x/12.x behavior is not uniform. Check the target release's official manual before deployment. `ONLY_FULL_GROUP_BY` is SQL-mode dependent; PostgreSQL's strict grouping rules are not a universal substitute for MySQL/MariaDB testing. `REPLACE` is not a safe generic UPSERT: it may delete and reinsert, affecting foreign keys, triggers and identity values.

## 3. Walkthrough: synthetic orders (15–30 minutes)

Assume the following logical rows:

| order_id | region | amount |
|---:|---|---:|
| 101 | East | 40.00 |
| 102 | east | 20.00 |
| 103 | West | NULL |
| 104 | West | 60.00 |

### 3.1 Portable-style aggregation and NULL

```sql
SELECT region, COUNT(*) AS order_count,
       COUNT(amount) AS known_amount_count,
       SUM(amount) AS amount_total
FROM orders
GROUP BY region
ORDER BY region;
```

Expected **under case-sensitive region grouping**: East 1/1/40.00; West 2/1/60.00; east 1/1/20.00. But MySQL/MariaDB grouping can combine `East` and `east` under case-insensitive collations; the exact behavior must be tested against the configured collation. `COUNT(*)` includes NULL amounts; `COUNT(amount)` does not. `SUM` ignores NULL, and an all-NULL group sums to NULL, not zero.

A deliberate normalized grouping key:

```sql
SELECT LOWER(region) AS region_key, COUNT(*) AS orders,
       SUM(COALESCE(amount, 0)) AS total
FROM orders
GROUP BY LOWER(region)
ORDER BY region_key;
```

Calculated expected results for this ASCII-only dataset: east / 2 / 60.00; west / 2 / 60.00. For international text, lowercase and collation equivalence require cross-engine tests.

### 3.2 Deterministic pagination

```sql
SELECT order_id, region FROM orders ORDER BY order_id LIMIT 2 OFFSET 1;
```

Calculated rows: (102, east), (103, West). MySQL/MariaDB's `LIMIT 1, 2` is a dialect alternative; PostgreSQL does not support that comma form. For large mutable datasets, consider keyset pagination (`WHERE order_id > :last_seen_id ORDER BY order_id LIMIT 2`) with an appropriate index, but confirm snapshot and business requirements.

### 3.3 Different upsert syntax — illustrative, **do not execute in production**

PostgreSQL:
```sql
INSERT INTO orders(order_id, region, amount)
VALUES (101, 'East', 45.00)
ON CONFLICT (order_id) DO UPDATE SET amount = EXCLUDED.amount;
```

MySQL/MariaDB pattern:
```sql
INSERT INTO orders(order_id, region, amount)
VALUES (101, 'East', 45.00)
ON DUPLICATE KEY UPDATE amount = 45.00;
```

Both snippets assume an isolated table with a unique order_id. Their conflict targeting and handling of additional unique constraints are **not equivalent**. Avoid relying on MySQL's older `VALUES(column)` update-reference syntax without checking version/deprecation status; choose a supported syntax for the actual target. For ingestion, test duplicate delivery, conflicting unique keys, row counts, concurrency and replay before production approval.

### 3.4 Transactions and schema change safety

A transactional InnoDB DML sequence can use `START TRANSACTION`, `UPDATE`, and `ROLLBACK`; however, DDL can implicitly commit and nontransactional storage engines behave differently. MySQL/MariaDB do not share PostgreSQL's transactional DDL guarantees. A DBRE change plan must specify engine, exact DDL, online/locking behavior, backup/restore, rollback or forward-fix strategy, and application compatibility. Never infer production safety from a read-only tutorial.

## 4. Hands-on lab: PostgreSQL 18 portable behavior (30–50 minutes)

Run [117 — portable comparison SQL lab](../labs/117-mysql-mariadb-portability-comparison.sql) **only** in a separate disposable PostgreSQL 18 instance, database `sql_tutorials`. The lab uses CTEs containing synthetic rows; no persistent objects, writes or credentials are involved. Database-name and version checks are defense in depth, not proof of isolation.

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials \
  -f sql-tutorials/labs/117-mysql-mariadb-portability-comparison.sql
```

Tasks: (1) inspect the guards and timeouts; (2) count NULL versus non-NULL amounts; (3) compare exact-case and normalized-case grouping; (4) retrieve the deterministic two-row page; (5) compare `NOT IN` with a NULL-bearing subquery to `NOT EXISTS`; (6) inspect bidirectional `EXCEPT ALL` assertions; (7) explain which observations **cannot** establish MySQL/MariaDB behavior.

**Calculated expectations:** four orders; three non-NULL amounts; one NULL; overall known total 120.00; two normalized regions each totaling 60.00; page IDs 102 and 103; `NOT IN` with a NULL-bearing set returns zero rows; equivalent NULL-safe `NOT EXISTS` returns ID 104; zero assertion differences. These values have **not** been observed in PostgreSQL 18.

**Additional dialect acceptance exercise (design only):** For a disposable MySQL and a separate disposable MariaDB instance, draft a matrix recording server version, `SELECT @@sql_mode`, `SELECT @@collation_connection`, table collation, storage engine, expected and observed case grouping, NULL behavior, duplicate-key handling, and transaction rollback. Do not copy PostgreSQL's `DO`, `jsonb`, `ILIKE`, or `EXCEPT ALL` lab assertions directly: rewrite using supported target syntax.

## 5. Troubleshooting and DBRE/SRE guardrails (50–55 minutes)

- **Unexpected group totals:** inspect column/table collation and SQL mode; check duplicate keys and join fan-out before changing queries.
- **Unexpected boolean values:** `BOOLEAN` may be a tiny integer; enforce an explicit 0/1 constraint compatible with your release.
- **Incorrect pagination:** add unique tie-breaker; verify concurrent write behavior and stable snapshot assumptions.
- **Rollback failed after DDL:** check implicit commits, storage engine and exact statement; use preapproved migration/restore procedures.
- **Upsert changed unexpected rows:** review every unique index, conflict precedence and affected-row semantics; replay only in isolation.
- **Long-running queries:** record `EXPLAIN`, rows examined, indexes, transaction isolation, lock waits and resource limits; do not issue production `KILL`, DDL or mass DML from a tutorial.

## 6. Review and answers (55–60 minutes)

1. **Are MySQL and MariaDB interchangeable?** No; test against each specific version and configuration.
2. **Why can `GROUP BY region` differ?** Collation determines comparison/equality; case-insensitive collations may merge case variants.
3. **Does `COUNT(amount)` include NULL?** No; `COUNT(*)` counts rows.
4. **Why avoid `NOT IN` when the subquery can contain NULL?** Three-valued logic can make the predicate UNKNOWN for every unmatched row; prefer a correctly correlated `NOT EXISTS`.
5. **Is `INSERT IGNORE` the same as PostgreSQL `ON CONFLICT DO NOTHING`?** No; its warning/error behavior is broader and mode-dependent.
6. **Can MySQL DDL always be rolled back?** No; many DDL statements implicitly commit.
7. **Does the PostgreSQL lab certify MySQL/MariaDB?** No; cross-engine execution and evidence remain separate.

**Next:** Chapter 118 — SQL Server/T-SQL and Oracle SQL: key differences (planned; see [Master TOC](../MASTER-TOC.md)).

## References

- [MySQL 8.4 Reference Manual — SQL statements](https://dev.mysql.com/doc/refman/8.4/en/sql-statements.html)
- [MySQL — SQL modes](https://dev.mysql.com/doc/refman/8.4/en/sql-mode.html)
- [MySQL — INSERT ON DUPLICATE KEY UPDATE](https://dev.mysql.com/doc/refman/8.4/en/insert-on-duplicate.html)
- [MariaDB — SQL statements](https://mariadb.com/kb/en/sql-statements/)
- [MariaDB — SQL_MODE](https://mariadb.com/kb/en/sql-mode/)
- [PostgreSQL 18 — SELECT](https://www.postgresql.org/docs/18/sql-select.html)
- [PostgreSQL 18 — INSERT](https://www.postgresql.org/docs/18/sql-insert.html)

**Acceptance note:** Publication and targeted static reasoning are not independent editorial approval, comprehensive parser QA, cross-engine verification or PostgreSQL 18 runtime certification.
