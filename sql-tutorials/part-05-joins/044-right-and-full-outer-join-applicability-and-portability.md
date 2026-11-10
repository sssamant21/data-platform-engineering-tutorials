# 044 — RIGHT and FULL OUTER JOIN: Applicability and Portability

**Part 05 — Joins & Relational Query Patterns** · **60 minutes** · **Audience:** SQL beginners, data engineers, DBRE/SRE.

**Prerequisite:** [043 — LEFT OUTER JOIN](043-left-outer-join-preserve-unmatched-left-rows.md). **Lab:** [044 PostgreSQL 18 SQL](../labs/044-right-full-outer-join.sql). **Next:** 045 — CROSS JOIN and SELF JOIN (planned in [Master TOC](../MASTER-TOC.md)).

## 1. Objectives and 60-minute agenda (5 minutes)

By the end, you can (1) explain preserved sides in RIGHT and FULL OUTER JOIN, (2) distinguish missing matches from nullable values, (3) reconcile two staging feeds without accidentally dropping records, (4) rewrite RIGHT JOIN as LEFT JOIN, and (5) identify dialect portability limits.

Time budget: outcomes 5m; concepts 10m; examples 15m; isolated lab 20m; troubleshooting 5m; review 5m.

## 2. Concepts and portable syntax (10 minutes)

An INNER JOIN keeps matching pairs only. A LEFT JOIN keeps every left row. A RIGHT JOIN keeps every right row. A FULL OUTER JOIN keeps all rows from **both** inputs: matched pairs plus left-only and right-only rows. When multiple rows share a join key, each matching pair is returned: FULL JOIN is **not** an automatic deduplication or one-to-one reconciliation operation.

```sql
-- Standard-style SQL; supported by PostgreSQL 18.
SELECT a.order_id AS left_id, b.order_id AS right_id
FROM staging_a AS a
FULL OUTER JOIN staging_b AS b ON a.order_id = b.order_id;
```

Unmatched columns from the absent side are NULL. Test a **non-nullable key** to classify missing matches; do not assume a nullable description being NULL proves absence. Standard equality does not match NULL to NULL. A join condition must represent business identity (e.g., order_id), not a mutable amount or a display name.

**RIGHT as LEFT:** `A RIGHT JOIN B ON ...` is equivalent in matched-row semantics to `B LEFT JOIN A ON ...` with the same predicate, but output column order and `SELECT *` layout can differ. Explicitly select columns.

**Dialect notes:** PostgreSQL, SQL Server, Oracle, and Snowflake support RIGHT and FULL OUTER JOIN. BigQuery Standard SQL supports them. MySQL does not provide a native FULL OUTER JOIN; use a tested LEFT JOIN plus right-only anti-join with `UNION ALL`. SQLite supports RIGHT and FULL OUTER JOIN starting with SQLite 3.39.0; older SQLite versions do not. Confirm actual target engine/version. `IS NOT DISTINCT FROM`, `FILTER`, `DO` blocks and temporary-table syntax used in the lab are PostgreSQL-specific; do not copy the lab unchanged to other engines.

## 3. Worked reconciliation (15 minutes)

Two fictional order feeds contain:

| Feed A | Amount | Feed B | Amount |
|---|---:|---|---:|
| 101 | 20.00 | 102 | 30.00 |
| 102 | 30.00 | 103 | 15.00 |
| 104 | 9.00 | 104 | 9.00 |

```sql
WITH a(order_id, amount) AS (
 VALUES (101,20.00),(102,30.00),(104,9.00)
), b(order_id, amount) AS (
 VALUES (102,30.00),(103,15.00),(104,9.00)
)
SELECT a.order_id AS a_id, b.order_id AS b_id,
       CASE WHEN a.order_id IS NULL THEN 'B_ONLY'
            WHEN b.order_id IS NULL THEN 'A_ONLY'
            ELSE 'MATCHED' END AS status
FROM a FULL OUTER JOIN b ON a.order_id=b.order_id
ORDER BY COALESCE(a.order_id,b.order_id);
```

Expected:

| a_id | b_id | status |
|---:|---:|---|
| 101 | NULL | A_ONLY |
| 102 | 102 | MATCHED |
| NULL | 103 | B_ONLY |
| 104 | 104 | MATCHED |

Four result rows: 2 matched, 1 A-only, 1 B-only. Feed A has 3 rows/59.00; feed B has 3 rows/54.00. **Never sum both feed amounts across matched rows as if they were unique sales**; matched records represent the same business entity.

```sql
-- RIGHT JOIN preserves all B records: 102, 103, 104.
SELECT b.order_id, a.order_id AS a_match
FROM a RIGHT JOIN b ON a.order_id=b.order_id;

-- Same logical result with a reversed LEFT JOIN.
SELECT b.order_id, a.order_id AS a_match
FROM b LEFT JOIN a ON a.order_id=b.order_id;
```

For MySQL, emulate FULL JOIN for a **non-nullable unique join key**:

```sql
SELECT a.order_id AS a_id, b.order_id AS b_id
FROM a LEFT JOIN b ON a.order_id=b.order_id
UNION ALL
SELECT a.order_id AS a_id, b.order_id AS b_id
FROM b LEFT JOIN a ON a.order_id=b.order_id
WHERE a.order_id IS NULL;
```

The second branch adds only B-only rows. This assumes `a.order_id` is non-nullable; nullable keys and duplicate keys require explicit rules. Do not use `UNION` as a substitute for reconciliation: deduplication can hide legitimate multiplicity.

## 4. Hands-on PostgreSQL 18 lab (20 minutes)

Use a **disposable, isolated** PostgreSQL 18 database named `sql_tutorials`. Never connect with production credentials. From the repository root:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/044-right-full-outer-join.sql
```

The lab checks server version, database name and writable primary, sets transaction-local timeouts, creates only temporary synthetic tables, and ends with `ROLLBACK`. It demonstrates RIGHT JOIN, the reversed LEFT JOIN, FULL JOIN, classifications and assertions. Expected: A=3/59.00, B=3/54.00, FULL=4 rows (2 matched, 1 A-only, 1 B-only), RIGHT=3, reversed LEFT=3, no duplicate keys. Final output includes a `PASS` notice and `ROLLBACK`; no persistent data is written.

Practice: (a) change the projection to include both amounts; (b) filter only A-only rows using `b.order_id IS NULL`; (c) explain why a filter on `b.amount` in `WHERE` can discard A-only rows; (d) add a duplicate ID in a scratch copy and predict fan-out before running it. Restore original fixture before checking assertions.

## 5. Validation, troubleshooting, and safety (5 minutes)

- Missing rows? Check join direction, `ON` vs `WHERE` filters, NULL join keys, and whether the business keys are normalized.
- More rows than expected? Count duplicates per join key **before** joining; unique source keys are required for one-to-one comparisons.
- Amount mismatch? Reconcile each source independently; do not treat FULL JOIN row count or summed matched amounts as a deduplicated fact table.
- Syntax error? Verify dialect/version; MySQL lacks native FULL OUTER JOIN. For SQLite, check version 3.39+.
- Permission or guard failure? Stop. Use a separate disposable lab instance; do not weaken guard checks or point to production.
- For DBRE/SRE incident investigations, run read-only comparisons against approved replicas or snapshots, cap query scope, and review plans on large tables. The included script itself is isolated and rollback-only, **not** a production diagnostic script.

**Validation status:** Authored for PostgreSQL 18; expected outputs are reasoned from the fixture. Independent editorial review, comprehensive static QA, and actual isolated PostgreSQL 18 runtime execution/evidence are pending until separately recorded.

## 6. Review questions and answers (5 minutes)

1. **Which rows survive FULL JOIN?** All matched pairs plus unmatched rows from each side.
2. **What does RIGHT JOIN preserve?** Every right-side row, with NULLs for missing left-side values.
3. **How can you express RIGHT JOIN with LEFT JOIN?** Swap the inputs and retain the equivalent `ON` predicate.
4. **Why might a FULL JOIN produce more rows than either input?** Duplicate matching keys cause pairwise fan-out.
5. **How should missing matches be tested?** Use a non-nullable key from the missing side, not a nullable attribute.
6. **Is FULL OUTER JOIN native in MySQL?** No; emulate with LEFT JOIN plus right-only anti-join and UNION ALL, validating key assumptions.

## References

- [PostgreSQL 18 — Joined Tables](https://www.postgresql.org/docs/18/queries-table-expressions.html#QUERIES-JOIN)
- [PostgreSQL 18 — SELECT](https://www.postgresql.org/docs/18/sql-select.html)
- [SQLite 3.39.0 release notes](https://www.sqlite.org/releaselog/3_39_0.html)
- [MySQL 8.4 JOIN clause](https://dev.mysql.com/doc/refman/8.4/en/join.html)
- [Master TOC](../MASTER-TOC.md) · [Status tracker](../STATUS-TRACKER.md)
