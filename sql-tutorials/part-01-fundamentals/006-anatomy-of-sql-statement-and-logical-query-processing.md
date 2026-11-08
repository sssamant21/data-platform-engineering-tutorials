# Chapter 006 — Anatomy of a SQL Statement and Logical Query Processing

> [Master TOC](../MASTER-TOC.md) · [SQL Tutorials](../README.md) · [Previous: Chapter 005](005-records-relationships-keys-and-relational-terminology.md)  
> **Audience:** Beginners, analysts, data engineers, application engineers, DBRE/SRE · **Duration:** 60 minutes · **Baseline:** PostgreSQL 18  
> **Status:** Published; independent editorial review and actual PostgreSQL 18 runtime validation pending.

## Learning objectives and 60-minute plan

| Minutes | Topic | Outcome |
|---:|---|---|
| 0–5 | Safety and context | Confirm the isolated lab and read-only scope |
| 5–15 | Statement anatomy | Recognize keywords, identifiers, literals, expressions, clauses |
| 15–25 | Logical processing order | Explain why WHERE cannot use a SELECT alias |
| 25–40 | Worked examples | Predict grouping, filtering, ordering and limiting |
| 40–55 | Hands-on lab | Execute and verify five read-only exercises |
| 55–60 | Troubleshooting and quiz | Explain results and common errors |

**Prerequisites:** [Chapter 003 — PostgreSQL 18 lab setup](003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md), [Chapter 004 — database objects](004-databases-schemas-tables-rows-columns.md), and [Chapter 005 — relationships and keys](005-records-relationships-keys-and-relational-terminology.md). The accompanying [SQL lab](../labs/006-statement-anatomy-logical-processing.sql) uses fictional, in-query data; it creates no permanent objects and must run only against the isolated `sql_tutorials` PostgreSQL 18 lab. You can study the examples without a database.

## 1. Anatomy of a SQL statement (10 minutes)

SQL is declarative: you describe the result; the database plans the physical execution. Consider:

```sql
SELECT customer_id, SUM(amount_usd) AS paid_total
FROM orders
WHERE status = 'paid'
GROUP BY customer_id
HAVING SUM(amount_usd) >= 50
ORDER BY paid_total DESC, customer_id ASC
LIMIT 2;
```

| Element | Example | Meaning |
|---|---|---|
| Keyword | `SELECT`, `FROM`, `WHERE` | Language instruction |
| Identifier | `customer_id`, `orders` | Column or table name |
| String literal | `'paid'` | Text value; single quotes delimit strings |
| Numeric literal | `50` | Number |
| Expression | `SUM(amount_usd)` | Computes a value |
| Alias | `AS paid_total` | Names an output expression |
| Predicate | `status = 'paid'` | Condition evaluated as true, false or unknown |
| Clause | `GROUP BY customer_id` | A logical step of the query |
| Terminator | `;` | Ends the SQL statement in typical clients |

Use **single quotes for string values**. PostgreSQL double quotes delimit identifiers, e.g., `"Order Total"`; unquoted identifiers are folded to lowercase in PostgreSQL. Avoid unnecessarily quoted mixed-case names in new schemas.

SQL comments use `--` for the rest of a line or `/* ... */` for a block. These examples use `WITH ... VALUES` as a temporary, read-only data source instead of creating a table.

## 2. Written syntax versus logical query order (10 minutes)

Although a query is usually **written** as `SELECT ... FROM ... WHERE ... GROUP BY ... HAVING ... ORDER BY ... LIMIT`, a useful *conceptual* logical evaluation order is:

| Conceptual order | Clause | Question |
|---:|---|---|
| 1 | `FROM` and joins | Which source rows are considered? |
| 2 | `WHERE` | Which individual rows qualify? |
| 3 | `GROUP BY` | Which rows form each group? |
| 4 | `HAVING` | Which groups qualify? |
| 5 | `SELECT` | Which output expressions are returned? |
| 6 | `DISTINCT` (if present) | Which duplicate result rows are removed? |
| 7 | `ORDER BY` | How is the result ordered? |
| 8 | `LIMIT` / `OFFSET` (if present) | Which slice is returned? |

This is a **teaching model**, not a promise about PostgreSQL's physical execution sequence. Optimizers can reorder operations while preserving semantics; window functions, set operations, and expression evaluation add nuances.

**Key consequences:**

- `WHERE` filters **rows before grouping**. `HAVING` filters **groups after aggregation**.
- An aggregate such as `SUM(amount_usd)` belongs in `SELECT` or `HAVING` for this example, not `WHERE`.
- A `SELECT` output alias such as `paid_total` generally **cannot be used in WHERE or HAVING** in PostgreSQL; `ORDER BY paid_total` is supported.
- Without `ORDER BY`, the output row order is **not guaranteed**, even if it appears stable in a small lab.
- `LIMIT` without a deterministic `ORDER BY` is unsafe for reproducible reporting or pagination.

## 3. Guided examples (15 minutes)

Use this fictional dataset throughout:

| order_id | customer_id | amount_usd | status |
|---:|---:|---:|---|
| 5001 | 101 | 40.00 | paid |
| 5002 | 101 | 25.00 | paid |
| 5003 | 102 | 70.00 | pending |
| 5004 | 102 | 90.00 | paid |
| 5005 | 103 | 15.00 | paid |
| 5006 | 103 | 10.00 | paid |

### Example A — Filter rows before aggregation

```sql
WITH orders(order_id, customer_id, amount_usd, status) AS (
  VALUES
    (5001,101,40.00::numeric(10,2),'paid'),
    (5002,101,25.00::numeric(10,2),'paid'),
    (5003,102,70.00::numeric(10,2),'pending'),
    (5004,102,90.00::numeric(10,2),'paid'),
    (5005,103,15.00::numeric(10,2),'paid'),
    (5006,103,10.00::numeric(10,2),'paid')
)
SELECT customer_id, COUNT(*) AS paid_orders,
       SUM(amount_usd) AS paid_total
FROM orders
WHERE status = 'paid'
GROUP BY customer_id
ORDER BY customer_id;
```

Expected: customer 101 → 2 orders / 65.00; 102 → 1 / 90.00; 103 → 2 / 25.00. The pending 70.00 order is excluded *before* aggregation.

### Example B — Filter groups with HAVING

Take Example A and insert `HAVING SUM(amount_usd) >= 50` between `GROUP BY` and `ORDER BY`. Expected: only customers 101 (65.00) and 102 (90.00). The group for customer 103 is filtered out.

### Example C — Order by a SELECT alias

Take Example B and replace the final line with:

```sql
ORDER BY paid_total DESC, customer_id ASC
LIMIT 1;
```

Expected: customer 102, paid_orders 1, paid_total 90.00. The secondary sort key ensures stable tie handling if totals match.

### Example D — WHERE versus HAVING

This is **not valid** PostgreSQL SQL:

```sql
-- Demonstration only: do NOT run this invalid statement.
-- SELECT customer_id, SUM(amount_usd) AS paid_total
-- FROM orders
-- WHERE paid_total >= 50
-- GROUP BY customer_id;
```

`paid_total` is defined in the `SELECT` output, too late to be referenced by `WHERE`. Use `HAVING SUM(amount_usd) >= 50`, or put the aggregation into a subquery/CTE and filter the outer query. A CTE is a named intermediate query, not necessarily a materialized table.

### Example E — Inspect the plan safely

On the same small read-only query, use `EXPLAIN` without `ANALYZE` to inspect the estimated plan. The plan's shape, estimates, and node order are version- and optimizer-dependent; do not assert an exact plan. `EXPLAIN ANALYZE` actually executes a statement, so it requires extra care for write queries and is not needed in this beginner lab.

## 4. Hands-on Lab 006 (15 minutes)

**Goal:** Run the [standalone SQL script](../labs/006-statement-anatomy-logical-processing.sql) and verify its output.

1. Verify that you are connected to the isolated `sql_tutorials` database on PostgreSQL major version 18.
2. Run the script with `psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f labs/006-statement-anatomy-logical-processing.sql` from the `sql-tutorials/` directory. Adjust connection parameters to the **local lab only**; follow Chapter 003 for Docker execution.
3. Inspect the base rows (6 total), paid-only rows (5), grouped totals (101: 65.00, 102: 90.00, 103: 25.00), HAVING output (2 groups), and top customer (102: 90.00).
4. Confirm the assertion query returns `PASS`. The script uses a guarded division to fail when expected values differ.
5. Explain in your own words why the pending order does not contribute to the paid totals and why the top customer is 102.

**Acceptance checklist:**

- [ ] The connection guard verifies PostgreSQL 18 and the isolated `sql_tutorials` database.
- [ ] Six fictional input rows, five paid rows, and three paid customer groups are accounted for.
- [ ] Paid revenue totals 180.00 (65 + 90 + 25).
- [ ] HAVING retains two customers; ORDER BY and LIMIT return customer 102.
- [ ] All assertions pass and the read-only transaction ends with `ROLLBACK`.
- [ ] No persistent objects or records are created.

## 5. Troubleshooting, DBRE/SRE considerations, and portability (5 minutes)

| Symptom | Likely cause | Safe action |
|---|---|---|
| `column "paid_total" does not exist` in WHERE | Output alias used before SELECT projection | Filter with HAVING or an outer query |
| `aggregate functions are not allowed in WHERE` | Aggregate evaluated after row filtering | Move aggregate condition to HAVING |
| Unexpected group totals | WHERE predicate omitted or pending rows included | Compare paid-only rows before grouping |
| Different order across runs | Missing or incomplete ORDER BY | Specify deterministic sort keys |
| `relation "orders" does not exist` | Ran fragment without the CTE | Run the complete statement |
| Guard fails | Wrong server major version or database | Stop; reconnect to the isolated Chapter 003 lab |

**Production perspective:** The optimizer's physical order can differ from the logical teaching model. For incident analysis, capture sanitized SQL, execution plan, row estimates, and workload context; avoid running costly exploratory queries on production without review. In data engineering, write down the *grain* (one row per order versus one row per customer) before aggregation to avoid incorrect KPIs.

**Dialect note:** The `::numeric(10,2)` casts are PostgreSQL-specific shorthand; portable-style SQL uses `CAST(40.00 AS DECIMAL(10,2))`. `LIMIT` is common but not universal: SQL Server often uses `TOP` or `OFFSET ... FETCH`; standard-style `FETCH FIRST 1 ROW ONLY` is supported by PostgreSQL. Do not assume vendor equivalence without testing.

## 6. Knowledge check and answers

1. **Why is FROM conceptually before SELECT?** The source rows must be identified before producing the output columns.
2. **Can WHERE reference a SUM result directly?** No. Use HAVING or a subquery.
3. **Which customer has the highest paid total?** Customer 102 (90.00).
4. **How much revenue is excluded by filtering to paid?** 70.00 (the pending order).
5. **Does the logical order describe the actual physical plan?** No. The optimizer can choose different execution strategies.
6. **Why use ORDER BY with LIMIT?** To choose a reproducible top row rather than an arbitrary row.

**Next:** Chapter 007 — SELECT Fundamentals: Retrieve Rows and Columns (planned; see [Master TOC](../MASTER-TOC.md)).

## References

- [PostgreSQL 18 — SELECT](https://www.postgresql.org/docs/18/sql-select.html)
- [PostgreSQL 18 — Table Expressions](https://www.postgresql.org/docs/18/queries-table-expressions.html)
- [PostgreSQL 18 — Sorting Rows](https://www.postgresql.org/docs/18/queries-order.html)
- [PostgreSQL 18 — EXPLAIN](https://www.postgresql.org/docs/18/sql-explain.html)

**Validation note:** Expected results were manually checked against the synthetic dataset. GitHub publication and static safety checks are separate from independent editorial review and PostgreSQL 18 execution; both remain pending until independently evidenced.
