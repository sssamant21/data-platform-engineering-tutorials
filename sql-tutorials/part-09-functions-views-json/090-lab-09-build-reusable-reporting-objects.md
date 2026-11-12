# 090 — Lab 09: Build Reusable Reporting Objects

**Part 09 — SQL Objects, Functions & Semi-Structured Data** · **60 minutes** · **PostgreSQL 18 baseline** · **Audience:** analysts, data engineers, DBRE/SRE

[Master TOC](../MASTER-TOC.md) · [Tutorial index](../README.md) · [Canonical read-only SQL lab](../labs/090-lab-09-reusable-reporting-objects.sql) · [Previous: 089](089-triggers-dynamic-sql-and-parameterization-safeguards.md) · [Next: 091 — EXPLAIN](../part-10-performance/091-read-execution-plans-with-explain.md) (planned)

## 1. Outcomes and prerequisites (0–5 minutes)

Build a reusable, one-row-per-customer reporting interface; separate raw records from reporting contracts; extract and validate JSON attributes; compare a live report with a stale materialized snapshot; and reconcile exact expected results. Understand how a view, materialized view, and SQL function would expose the same report while imposing different operational costs.

Review [084 — JSON](084-json-and-semi-structured-sql-queries.md), [085 — Views](085-views-and-secure-abstraction.md), [086 — Materialized views](086-materialized-views-and-refresh-strategies.md), [087 — Intermediate results](087-temporary-tables-and-intermediate-result-sets.md), and [088 — Functions](088-stored-functions-and-procedures-dialect-specific-syntax.md).

**Scenario:** a fictional commerce data team needs a stable customer spend report. DBRE/SRE must verify correctness, access boundaries, refresh freshness and performance before approving a reusable object. This capstone models the interface with read-only CTEs, rather than creating persistent objects.

## 2. Design and SQL portability (5–15 minutes)

**Reporting grain:** exactly one row per customer, including customers with no paid orders. **Metric:** sum of paid order amounts only. **Contract:** customer_id, customer_name, region, paid_order_count, paid_total, tier. Missing JSON region defaults to `unassigned` for display, not to a false physical value. Currency uses exact `NUMERIC`, not floating point. Never sum joined order-item and payment rows without first controlling fan-out.

| Construct | Purpose | Operational caution |
|---|---|---|
| CTE / derived table | Read-only prototype, query-local | Not a persisted API |
| `CREATE VIEW` | Reusable logical interface | Permissions, ownership and dependency management |
| `CREATE MATERIALIZED VIEW` (PostgreSQL) | Persist query results | Staleness, refresh I/O and lock behavior |
| SQL-language function | Parameterized reporting interface | Privileges, volatility and execution plans |
| Temporary table | Session-local intermediate data | Pooling and cleanup concerns |

`WITH`, `JOIN`, `GROUP BY`, `CASE`, `COALESCE` and `SUM` are broadly portable SQL constructs. PostgreSQL `jsonb`, `->>`, `CREATE MATERIALIZED VIEW`, `security_invoker` and `REFRESH MATERIALIZED VIEW CONCURRENTLY` are dialect-specific; translate and test equivalents before moving to Snowflake, BigQuery, SQL Server or MySQL.

## 3. Guided walkthrough (15–30 minutes)

Use a two-stage design: aggregate paid orders *before* joining customers; then publish a stable projection. The canonical lab includes the full synthetic dataset and exact assertions. The core report query is:

```sql
WITH customers(customer_id, customer_name, attributes) AS (
  VALUES (1,'Aster', '{"region":"east"}'::jsonb),
         (2,'Birch', '{"region":"west"}'::jsonb),
         (3,'Cedar', '{}'::jsonb),
         (4,'Dune', '{"region":"east"}'::jsonb)
),
orders(order_id, customer_id, status, amount) AS (
  VALUES (101,1,'paid',30.00::numeric(10,2)),
         (102,1,'paid',20.00), (103,1,'pending',90.00),
         (104,2,'paid',25.00), (105,2,'refunded',40.00),
         (106,3,'paid',10.00)
),
paid AS (
  SELECT customer_id, COUNT(*) AS paid_order_count,
         SUM(amount) AS paid_total
  FROM orders WHERE status = 'paid' GROUP BY customer_id
)
SELECT c.customer_id, c.customer_name,
       COALESCE(c.attributes->>'region','unassigned') AS region,
       COALESCE(p.paid_order_count,0) AS paid_order_count,
       COALESCE(p.paid_total,0::numeric) AS paid_total,
       CASE WHEN COALESCE(p.paid_total,0) >= 40 THEN 'high' ELSE 'standard' END AS tier
FROM customers c LEFT JOIN paid p USING (customer_id)
ORDER BY c.customer_id;
```

**Expected (calculated, not runtime-observed):**

| ID | Customer | Region | Paid orders | Paid total | Tier |
|---:|---|---|---:|---:|---|
| 1 | Aster | east | 2 | 50.00 | high |
| 2 | Birch | west | 1 | 25.00 | standard |
| 3 | Cedar | unassigned | 1 | 10.00 | standard |
| 4 | Dune | east | 0 | 0.00 | standard |

The report total is **85.00**, four paid orders, and four customers. A hypothetical cached snapshot taken before order 106 would show Cedar at zero and a total of 75.00. The snapshot therefore lags the live source by **10.00**; freshness cannot be inferred from the fact that a materialized view exists.

**Illustrative DDL only; do not run on shared/production databases:**

```sql
-- In an approved disposable schema, after replacing report_query
-- with the reviewed SELECT above:
CREATE VIEW demo_customer_report WITH (security_invoker = true)
AS SELECT * FROM report_source; -- report_source is intentionally undefined
-- A materialized view would require CREATE MATERIALIZED VIEW ... AS SELECT ...
-- and a documented refresh plan; this snippet is NOT executable as-is.
```

A view is not automatically a security boundary. In PostgreSQL, review view ownership, `security_invoker`, underlying grants and row-level security. A materialized view stores data separately; refresh and SELECT privileges need independent review. Do not expose customer identifiers or sensitive JSON attributes without an approved data-access design.

## 4. Hands-on lab (30–50 minutes)

Run only against an **isolated, disposable PostgreSQL 18** database called `sql_tutorials` using nonproduction credentials. The canonical lab is read-only, has a version/database guard, local timeouts, synthetic CTEs, exact multiset assertions and rollback:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -c "SELECT current_database(), current_setting('server_version');"
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/090-lab-09-reusable-reporting-objects.sql
```

Tasks: (1) identify the report grain; (2) explain why pending/refunded orders do not contribute; (3) confirm Dune remains in the report; (4) compare live and stale snapshot totals; (5) inspect the exact multiset assertions and the fail-closed acceptance expression; (6) design an approval checklist for a production view/materialized view without executing DDL.

**Stretch exercises:** Add a synthetic paid order for Dune in your own copy of the CTE and update expected assertions. Change the tier threshold from 40 to 25; identify which customers change tier. Add two order items per order and demonstrate how a naive join can double-count amounts.

## 5. Troubleshooting and operational acceptance (50–55 minutes)

- **Missing customers:** aggregation plus INNER JOIN removes zero-activity customers; use LEFT JOIN and zero-fill deliberately.
- **Inflated totals:** inspect join cardinality and aggregate at the order grain before joining.
- **Incorrect JSON region:** distinguish missing key, JSON null, SQL NULL and blank string; define a documented policy.
- **Stale materialized data:** compare snapshot generation time, source watermark and reconciliation totals; a refresh may lock or consume substantial I/O. PostgreSQL concurrent refresh has a qualifying unique-index prerequisite and other restrictions.
- **Access denied:** check invoker/owner privileges, RLS behavior and underlying object grants in a disposable environment.
- **Slow report:** collect `EXPLAIN` evidence in staging; do not add indexes or trigger refreshes blindly.
- **Safety:** no production credentials, real customer/healthcare data, persistent DDL or unapproved maintenance. The lab proves *modeled report logic only* when executed; it does not test actual CREATE VIEW, materialized refresh, access controls or concurrent workload behavior.

For runtime evidence retain the PostgreSQL server version, database identity, exact Git commit, invocation, exit status, complete output, assertion results and cleanup. Without this evidence runtime status remains **pending**.

## 6. Review questions with answers (55–60 minutes)

1. **What is the report grain?** One row per customer.
2. **Why aggregate orders first?** To prevent fan-out and make the join contract explicit.
3. **Why does Dune appear?** LEFT JOIN preserves customers with no matching paid orders.
4. **What does a regular view store?** The definition, not a separately refreshed result set.
5. **What is the stale snapshot delta?** Live 85.00 minus snapshot 75.00 = 10.00.
6. **Does a read-only CTE prove materialized refresh works?** No; only a separate isolated DDL/refresh test can prove that.
7. **Is PostgreSQL `->>` portable SQL?** No; JSON operators vary by vendor.
8. **What must DBRE/SRE approve before rollout?** Ownership, access/RLS, dependencies, load impact, refresh/freshness SLO, rollback and monitoring.

## References

- [PostgreSQL 18 — WITH queries](https://www.postgresql.org/docs/18/queries-with.html)
- [PostgreSQL 18 — JSON functions and operators](https://www.postgresql.org/docs/18/functions-json.html)
- [PostgreSQL 18 — CREATE VIEW](https://www.postgresql.org/docs/18/sql-createview.html)
- [PostgreSQL 18 — CREATE MATERIALIZED VIEW](https://www.postgresql.org/docs/18/sql-creatematerializedview.html)
- [PostgreSQL 18 — REFRESH MATERIALIZED VIEW](https://www.postgresql.org/docs/18/sql-refreshmaterializedview.html)
- [PostgreSQL 18 — EXPLAIN](https://www.postgresql.org/docs/18/sql-explain.html)

**Validation state:** authored; targeted static/manual reasoning only. Independent editorial review, comprehensive syntax/link QA and actual isolated PostgreSQL 18 runtime execution remain pending.
