# 085 — Views and Secure Abstraction

**Part 09 — SQL Objects, Functions & Semi-Structured Data | 60 minutes | PostgreSQL 18**

[Master TOC](../MASTER-TOC.md) · [Tutorial index](../README.md) · [Read-only SQL lab](../labs/085-views-secure-abstraction.sql) · [Previous: 084](084-json-and-semi-structured-sql-queries.md) · [Next: 086](../MASTER-TOC.md#part-09--sql-objects-functions--semi-structured-data)

## 1. Outcomes and schedule (0–5 minutes)

You will define a view, distinguish logical abstraction from access control, query a view without creating database objects, recognize PostgreSQL ownership and security behavior, and validate a safe reporting contract. Prerequisites: [SELECT](../part-01-fundamentals/007-select-fundamentals-retrieve-rows-and-columns.md), [joins](../part-05-joins/041-join-fundamentals-and-relationship-cardinality.md), [aggregates](../part-06-aggregation/051-count-sum-avg-min-and-max.md), and an isolated PostgreSQL 18 `sql_tutorials` database.

| Minutes | Activity |
|---|---|
| 0–5 | Objectives and safety |
| 5–15 | View concepts and privilege boundaries |
| 15–30 | Worked SQL examples |
| 30–50 | Read-only lab and practice |
| 50–55 | Validation and troubleshooting |
| 55–60 | Review and answers |

## 2. Key concepts (5–15 minutes)

A **view** is a named stored query; ordinary PostgreSQL views do **not** persist a separate snapshot of query results. The underlying tables are queried when the view is used. Views can stabilize a reporting interface, centralize transformations, hide columns from the view's result, and support least-privilege access **when underlying privileges, ownership, row security and grants are configured correctly**. Merely omitting a sensitive column from a view is not security if a consumer can still SELECT the base table.

**Portable SQL concept:** `CREATE VIEW name AS SELECT ...` is widely supported, but replacement, security options, updatability, dependencies and grants vary by database.

**PostgreSQL 18 specifics:**
- By default, base-relation permission checks and row-level-security policies are evaluated in the context of the view owner; a `security_invoker=true` view instead uses the invoking user's permissions and applicable RLS policies. The invoking user must have suitable access to the underlying relations for a security-invoker view.
- `security_barrier=true` can constrain predicate reordering across a view boundary for security-sensitive filtering, with possible performance costs. It is not a replacement for RLS, careful privileges, or leakage testing.
- `WITH LOCAL CHECK OPTION` / `WITH CASCADED CHECK OPTION` apply to certain automatically updatable views; a reporting aggregation view is not automatically updatable.
- `CREATE OR REPLACE VIEW` has compatibility restrictions on existing columns; treat changes as API migrations. A view does not automatically make a query fast: measure its expanded plan using `EXPLAIN`.
- A materialized view stores results and has a separate refresh lifecycle; see Chapter 086.

## 3. Worked examples (15–30 minutes)

These examples illustrate DDL **only**; do not run them on production. They require preexisting isolated demo tables and an approved role model. The canonical lab below is entirely read-only and creates no view or role.

```sql
-- Illustrative isolated-environment DDL, NOT part of the read-only lab.
CREATE VIEW reporting_order_totals AS
SELECT customer_id, COUNT(*) AS order_count,
       SUM(amount)::numeric(12,2) AS total_amount
FROM demo_orders
WHERE status = 'paid'
GROUP BY customer_id;
```

The view presents one row per customer with paid orders; it does not include raw payment identifiers. A user with direct access to `demo_orders` could still query those identifiers. A real deployment requires explicit base-table privilege design, view ownership and grants; avoid `GRANT SELECT ON ALL TABLES` as a shortcut.

**Synthetic query using the same logical contract without DDL:**

```sql
WITH orders(order_id, customer_id, status, amount) AS (
 VALUES (101,1,'paid',20.00::numeric),
        (102,1,'paid',30.00::numeric),
        (103,1,'pending',99.00::numeric),
        (104,2,'paid',15.00::numeric)
), reporting_order_totals AS (
 SELECT customer_id, COUNT(*) AS order_count, SUM(amount) AS total_amount
 FROM orders WHERE status = 'paid' GROUP BY customer_id
)
SELECT * FROM reporting_order_totals ORDER BY customer_id;
```

Expected:

| customer_id | order_count | total_amount |
|---:|---:|---:|
| 1 | 2 | 50.00 |
| 2 | 1 | 15.00 |

A second consumer can join this interface to a customer dimension without repeating the payment-status filter. Define and document the **grain** (one row per customer), the status semantics, decimal precision, NULL handling, and what happens when no paid orders exist. If you need all customers including zero-order customers, start from the customer dimension and LEFT JOIN an aggregate, using `COALESCE` only when zero is the correct business meaning.

**Illustrative privilege pattern (do not execute in the read-only lab):** use a dedicated view owner with only the necessary base-table access; grant consumers `USAGE` on the reporting schema and `SELECT` on explicitly approved views. Verify the consumer cannot query base tables directly. For security-invoker views, consumers also need underlying access, so choose the security model deliberately. Check RLS interactions and owner bypass rules in the target deployment.

## 4. Hands-on lab (30–50 minutes)

The [canonical PostgreSQL 18 lab](../labs/085-views-secure-abstraction.sql) uses synthetic inline data and a CTE named `reporting_order_totals` as a **view-shaped SELECT contract**, not an actual persisted view. This avoids DDL and permissions changes. It validates both customer-level reporting rows and reconciliation totals using bidirectional `EXCEPT ALL` assertions.

```bash
psql -X -d sql_tutorials -c "SELECT current_database(), current_setting('server_version');"
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/085-views-secure-abstraction.sql
```

Use a disposable PostgreSQL 18 database named `sql_tutorials` and non-production credentials. The script begins `READ ONLY`, applies local timeouts, checks the database name and major version, and ends with `ROLLBACK`. It contains no persistent writes. Expected customer rows: Ada (2 paid, 50.00), Ben (1 paid, 15.00), Cy (0 paid, 0.00), Dee (1 paid, 7.50). Expected: 4 customers, 4 paid orders, total paid amount 72.50. A pending order and a cancelled order are excluded.

Practice:
1. Explain why a view that omits `payment_token` does not protect it if the reporting role can SELECT the base table.
2. Remove the `COALESCE` from the view-shaped CTE; explain why Cy's total becomes SQL NULL instead of zero.
3. Change the status predicate to include `pending` in a scratch copy; predict the new total (171.50) and explain why this violates the original reporting contract.
4. Sketch a deployment checklist: dedicated owner, explicit grants, base-table denial test, RLS tests, `EXPLAIN`, rollback plan and contract versioning.

For later runtime acceptance, retain PostgreSQL server version, database identity, exact command, stdout/stderr, exit code and comparison results. **No runtime execution is asserted by this chapter.**

## 5. Troubleshooting and DBRE/SRE safeguards (50–55 minutes)

- **Permission denied:** check schema `USAGE`, view `SELECT`, owner/base-table access, `security_invoker`, and RLS policy context. Do not disable RLS to make a demo pass.
- **Unexpected missing customers:** aggregating orders alone excludes customers with no qualifying orders; use a customer-driven LEFT JOIN.
- **Incorrect totals:** verify grain and join cardinality before aggregating; fan-out can double-count payments.
- **Slow view:** inspect the underlying query plan, filtering and indexes; a regular view is not a cached result.
- **Unsafe deployment:** changing a view can break downstream column contracts. Use versioned migrations, pre-production tests, explicit approvals, least privilege, rollback and monitoring. Never run unapproved DDL on production.
- **Portability:** PostgreSQL `security_invoker` and `security_barrier` are vendor-specific; SQL Server, Oracle, Snowflake and BigQuery have different view and authorization semantics.

## 6. Review questions and answers (55–60 minutes)

1. **Does a normal view store its own result rows?** No; PostgreSQL evaluates its underlying query when referenced.
2. **Is hiding a column sufficient to secure it?** No; restrict base-table access and test the actual consumer role.
3. **What does `security_invoker=true` change?** It uses invoking-user permissions and applicable row-security policies for underlying relations.
4. **Why include a customer dimension in a zero-order report?** It preserves customers without matching paid orders.
5. **Can an aggregate view be assumed writable?** No; aggregated reporting views are not automatically updatable.
6. **What is required to certify the lab?** Successful isolated PostgreSQL 18 execution with reproducible evidence, not static reasoning.

## References

- [PostgreSQL 18 — CREATE VIEW](https://www.postgresql.org/docs/18/sql-createview.html)
- [PostgreSQL 18 — Rules and views](https://www.postgresql.org/docs/18/rules-views.html)
- [PostgreSQL 18 — Privileges](https://www.postgresql.org/docs/18/ddl-priv.html)
- [PostgreSQL 18 — Row security policies](https://www.postgresql.org/docs/18/ddl-rowsecurity.html)
- [PostgreSQL 18 — EXPLAIN](https://www.postgresql.org/docs/18/sql-explain.html)

**Status:** Authored and published. Targeted static inspection only; independent editorial review, comprehensive syntax/link QA and isolated PostgreSQL 18 runtime validation pending.
