# 086 — Materialized Views and Refresh Strategies

**Part 09 — SQL Objects, Functions & Semi-Structured Data | 60 minutes | PostgreSQL 18**

[Master TOC](../MASTER-TOC.md) · [Tutorial index](../README.md) · [Read-only lab](../labs/086-materialized-views-refresh-strategies.sql) · [Previous: 085](085-views-and-secure-abstraction.md) · [Next: 087](../MASTER-TOC.md#part-09--sql-objects-functions--semi-structured-data)

## 1. Learning objectives and schedule (0–5 minutes)

After this lesson, explain ordinary versus materialized views, freshness versus query cost, refresh locking, PostgreSQL concurrent-refresh prerequisites, and safe refresh runbooks. You will calculate a synthetic report, compare snapshots with live aggregates, and reconcile a proposed refresh. Prerequisites: [views](085-views-and-secure-abstraction.md), [aggregates](../part-06-aggregation/051-count-sum-avg-min-and-max.md), and an isolated PostgreSQL 18 `sql_tutorials` database.

| Minutes | Activity |
|---|---|
| 0–5 | Outcomes, prerequisites and safety |
| 5–15 | Materialization and refresh concepts |
| 15–30 | Worked SQL examples and tradeoffs |
| 30–50 | Read-only lab and exercises |
| 50–55 | Troubleshooting and operational safeguards |
| 55–60 | Review and answers |

## 2. Concepts and SQL portability (5–15 minutes)

A **regular view** stores a query definition; a **materialized view** stores the result of a query at its last successful population/refresh. A materialized view can reduce repeated aggregation cost but consumes storage, can be stale, and adds refresh operations. A snapshot is not a source of truth: the underlying tables remain authoritative.

**Portable concepts:** precomputed reporting data, refresh cadence, stale-read tolerance, reconciliation and ownership are cross-platform design principles. **PostgreSQL-specific syntax:** `CREATE MATERIALIZED VIEW`, `WITH NO DATA`, `REFRESH MATERIALIZED VIEW`, and `REFRESH MATERIALIZED VIEW CONCURRENTLY`. Other platforms implement materialized views, indexed views, dynamic tables, or managed refresh differently. Do not assume identical SQL or transactional guarantees.

In PostgreSQL 18:
- `CREATE MATERIALIZED VIEW ... AS SELECT ... WITH DATA` populates immediately; `WITH NO DATA` leaves it unscannable until populated.
- `REFRESH MATERIALIZED VIEW` replaces its contents from the defining query; it is **not** a built-in incremental refresh. Ordinary refresh blocks concurrent reads of that materialized view while refresh runs.
- `REFRESH MATERIALIZED VIEW CONCURRENTLY` can avoid blocking ordinary `SELECT` readers, but requires an already populated materialized view and at least one qualifying `UNIQUE` index using only column names, covering all rows (no expression or partial index). Only one refresh at a time can run against a given materialized view. It can still consume significant CPU, I/O, WAL and storage.
- Concurrent refresh is not always faster; benchmark both strategies on staging. Refresh ownership/privilege requirements, availability, dependencies and lock behavior should be checked against the exact PostgreSQL version.
- PostgreSQL does not automatically schedule materialized-view refreshes; orchestration is an operational responsibility.

## 3. Walkthrough (15–30 minutes)

Imagine a source orders table and a daily report grouped by reporting date and service. The source receives a late order after the last refresh.

**Illustrative isolated-only DDL (not executed in the canonical lab):**

```sql
CREATE MATERIALIZED VIEW demo_daily_revenue AS
SELECT order_day, service,
       COUNT(*)::bigint AS paid_orders,
       SUM(amount)::numeric(12,2) AS paid_revenue
FROM demo_orders
WHERE status = 'paid'
GROUP BY order_day, service
WITH DATA;

-- Required for PostgreSQL CONCURRENTLY: all rows covered by a simple-column UNIQUE index.
CREATE UNIQUE INDEX demo_daily_revenue_key
ON demo_daily_revenue (order_day, service);

-- After population and index creation, a controlled refresh:
REFRESH MATERIALIZED VIEW CONCURRENTLY demo_daily_revenue;
```

These statements require an approved disposable database and a preexisting synthetic `demo_orders` table; **do not run in production**. Unlike a regular view, a materialized view does not reflect new rows until a refresh succeeds. It also needs a deployment and index lifecycle. The index example assumes one output row per non-NULL `(order_day, service)` group; in real deployments define NOT NULL source keys and verify uniqueness. `CONCURRENTLY` does not mean zero resource impact or guaranteed completion.

**Read-only snapshot simulation with inline values:**

```sql
WITH orders(order_id, order_day, service, status, amount, arrived_at) AS (
 VALUES
 (1,DATE '2026-11-01','api','paid',20.00::numeric,TIMESTAMP '2026-11-01 10:00'),
 (2,DATE '2026-11-01','api','paid',30.00::numeric,TIMESTAMP '2026-11-01 11:00'),
 (3,DATE '2026-11-01','api','paid',10.00::numeric,TIMESTAMP '2026-11-02 08:00'),
 (4,DATE '2026-11-01','file','paid',15.00::numeric,TIMESTAMP '2026-11-01 12:00'),
 (5,DATE '2026-11-02','api','pending',99.00::numeric,TIMESTAMP '2026-11-02 09:00')
)
SELECT service, COUNT(*) AS orders, SUM(amount) AS revenue
FROM orders
WHERE status='paid' AND arrived_at <= TIMESTAMP '2026-11-01 23:59:59'
GROUP BY service ORDER BY service;
```

Expected at the first cutoff: API 2 orders / 50.00, FILE 1 / 15.00. A subsequent source query after the late API arrival returns API 3 / 60.00, FILE 1 / 15.00. **Freshness lag:** 10.00 in API revenue; no evidence of lost data. The next successful refresh would include that late order if the defining query covers its reporting date.

For real systems, distinguish **source event time**, **arrival time**, **refresh completion time**, and **report as-of time**. A refresh timestamp is useful but does not alone prove source completeness or data accuracy.

## 4. Hands-on lab (30–50 minutes)

Run only against an isolated PostgreSQL 18 database named `sql_tutorials`, using non-production credentials:

```bash
psql -X -d sql_tutorials -c "SELECT current_database(), current_setting('server_version');"
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/086-materialized-views-refresh-strategies.sql
```

The [canonical lab](../labs/086-materialized-views-refresh-strategies.sql) uses inline synthetic orders, a read-only transaction, database/version guards, transaction-local timeouts, two-way `EXCEPT ALL` assertions and rollback. It **simulates** materialized snapshot versus live results using CTEs; it does not create or refresh a real materialized view. Expected: snapshot API 2 / 50.00, FILE 1 / 15.00; live API 3 / 60.00, FILE 1 / 15.00; stale API revenue 10.00, total live paid revenue 75.00, and one late-arriving paid order.

Exercises: (1) Predict results if the refresh cutoff moves to `2026-11-02 23:59:59`. (2) Explain why grouping by `arrived_at::date` instead of `order_day` changes business meaning. (3) Draft a freshness SLO such as 30 minutes and identify required monitoring signals. (4) Explain why `CONCURRENTLY` requires an appropriate unique index and populated view. (5) Compare hourly full refresh against a daily refresh in terms of staleness, WAL, I/O and reader availability.

## 5. Validation, troubleshooting and safety (50–55 minutes)

- **Stale data:** compare report snapshot and source aggregates at the same business grain and cutoff. Late events may require a wider recomputation window.
- **Refresh fails:** preserve the error, check owner/MAINTAIN privileges as appropriate for PostgreSQL 18, storage, dependencies, locks, and unique-index prerequisites. Do not repeatedly retry a resource-intensive refresh during an incident.
- **Blocked readers:** standard refresh can block queries; evaluate concurrent refresh after testing its unique-index requirements and resource cost.
- **Duplicate reporting rows:** validate the grouping grain and source joins; a unique index is not a substitute for business-key correctness.
- **Resource pressure:** record refresh duration, source row counts, materialized size, WAL growth, lock waits, query latency, and replication lag; define cancellation and rollback procedures.
- **Deployment:** require data-team approval of grain and freshness SLO, application-team sign-off for consumer compatibility, and DBRE/SRE approval of capacity, schedule, monitoring, and recovery. Prefer a controlled staging rehearsal before production change.
- **Runtime evidence:** retain server version, database identity, exact SQL file SHA, command, exit code, stdout/stderr, expected-result comparisons and cleanup evidence. **This lesson has not been PostgreSQL 18 runtime-certified.**

## 6. Review questions and answers (55–60 minutes)

1. **How does a materialized view differ from a regular view?** It stores query results and requires refresh to see source changes.
2. **Does PostgreSQL automatically incrementally update a materialized view?** No; ordinary `REFRESH` recomputes its defining query.
3. **What does concurrent refresh improve?** Reader availability; it does not eliminate load or guarantee faster refresh.
4. **What is required for concurrent refresh?** Populated view and a qualifying all-rows simple-column unique index, among other operational prerequisites.
5. **Why might revenue differ after refresh?** New or late-arriving paid orders, corrections, or changed source records.
6. **What validates correctness?** Source-to-snapshot reconciliation, freshness evidence and actual isolated runtime execution, not just reading SQL.

## References

- [PostgreSQL 18 — CREATE MATERIALIZED VIEW](https://www.postgresql.org/docs/18/sql-creatematerializedview.html)
- [PostgreSQL 18 — REFRESH MATERIALIZED VIEW](https://www.postgresql.org/docs/18/sql-refreshmaterializedview.html)
- [PostgreSQL 18 — Materialized Views](https://www.postgresql.org/docs/18/rules-materializedviews.html)
- [PostgreSQL 18 — CREATE INDEX](https://www.postgresql.org/docs/18/sql-createindex.html)
- [PostgreSQL 18 — Monitoring Database Activity](https://www.postgresql.org/docs/18/monitoring-stats.html)

**Status:** Authored/published; targeted static reasoning only. Independent editorial review, comprehensive automated syntax/link QA, and actual isolated PostgreSQL 18 runtime validation pending.
