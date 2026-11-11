# 080 — Lab 08: Produce an Analytical Customer Activity Report

**Part 08 — Window Functions & Advanced Analytics | 60 minutes | PostgreSQL 18 capstone**

[Master TOC](../MASTER-TOC.md) · [Tutorial index](../README.md) · [SQL lab](../labs/080-lab-08-analytical-customer-activity-report.sql) · [Previous: 079](079-cohort-analysis-retention-and-event-sequencing.md) · [Next: 081](../MASTER-TOC.md#part-09--sql-objects-functions--semi-structured-data)

## Outcomes and schedule

At the end you can specify the reporting grain, combine customer dimensions with activity facts without dropping inactive customers, use deterministic `ROW_NUMBER`, `DENSE_RANK`, `LAG` and running `SUM`, reconcile an analytical report against source facts, and explain operational safeguards.

| Minutes | Activity |
|---|---|
| 0–5 | Prerequisites, safety, business requirements |
| 5–15 | Grain, dimensions, facts, metric definitions |
| 15–30 | Worked SQL and expected outputs |
| 30–50 | Execute the isolated read-only capstone and exercises |
| 50–55 | Acceptance, troubleshooting and DBRE/SRE checks |
| 55–60 | Review answers and next steps |

**Prerequisites:** [071](071-window-function-anatomy-over-partition-by-order-by.md), [072](072-row-number-rank-and-dense-rank.md), [073](073-lag-and-lead-for-change-analysis.md), [074](074-running-totals-and-cumulative-measures.md), [079](079-cohort-analysis-retention-and-event-sequencing.md); disposable PostgreSQL 18 instance and `psql`. Never connect with production credentials.

## Business case and metric contract

A fictional retail platform wants **one row per customer**, including customers with no activity. The synthetic `customers` dimension has four customers (Aster, Birch, Cedar, Dune). The synthetic `events` fact set has seven events across three active customers, spanning 2026-02-02 to 2026-02-16. Each event has a unique `event_id`, a customer key, a UTC-normalized calendar date, activity type (`purchase` or `visit`), and nonnegative amount. Visits have zero amount. There are no real names, payments or identifiers.

**Metric definitions:** `event_count` counts every recorded event; `purchases` counts purchase events; `lifetime_spend` sums event amounts; `first_activity` and `last_activity` are observed dates or NULL for inactive customers. `spend_position` uses `ROW_NUMBER` sorted by spend descending and customer ID ascending, so ties have deterministic unique positions. `spend_rank` uses `DENSE_RANK` on spend only, so equal spend shares a rank. This report is a **full synthetic observation-window** report, not proof of complete real-world lifetime history.

**Grain contract:** the source event table has one row per event; the final report has exactly one row per customer. Never join a customer to a separate one-to-many payment table before summing event amounts without pre-aggregating both facts: doing so multiplies rows and corrupts totals. Customer ID is the stable key; customer names are presentation labels.

## Portable SQL pattern and PostgreSQL-specific details

The relational pattern—`LEFT JOIN`, `GROUP BY`, `COALESCE`, window `OVER (PARTITION BY ... ORDER BY ...)`, `ROW_NUMBER`, `DENSE_RANK`, `LAG`—is broadly supported in modern SQL engines. The lab's inline `VALUES` CTEs, PostgreSQL `FILTER` aggregate syntax, date subtraction yielding integer days, `SET LOCAL`, `BEGIN READ ONLY`, `current_setting`, and `EXCEPT ALL` acceptance harness are PostgreSQL-specific or not uniformly portable. To port the purchase count, replace `COUNT(event_id) FILTER (WHERE activity_type='purchase')` with `SUM(CASE WHEN activity_type='purchase' THEN 1 ELSE 0 END)` after accounting for the outer-join NULL row.

The companion script first defines two inline datasets, then sequences events:

```sql
WITH events(event_id, customer_id, event_day, amount) AS (
  VALUES (101,1,DATE '2026-02-02',20::numeric),
         (102,1,DATE '2026-02-09',30::numeric),
         (103,1,DATE '2026-02-16',0::numeric)
)
SELECT event_id, customer_id,
       ROW_NUMBER() OVER (
         PARTITION BY customer_id ORDER BY event_day,event_id
       ) AS event_number,
       LAG(event_day) OVER (
         PARTITION BY customer_id ORDER BY event_day,event_id
       ) AS previous_day,
       SUM(amount) OVER (
         PARTITION BY customer_id ORDER BY event_day,event_id
         ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
       ) AS running_spend
FROM events ORDER BY event_id;
```

**Expected, manually calculated (not runtime evidence):**

| event_id | event_number | previous_day | running_spend |
|---|---:|---|---:|
| 101 | 1 | NULL | 20 |
| 102 | 2 | 2026-02-02 | 50 |
| 103 | 3 | 2026-02-09 | 50 |

Aster's observed inter-event gaps are seven days each. The explicit `ROWS` frame and unique event-ID tie breaker avoid accidental peer grouping and nondeterministic order. A date alone does not determine a stable order for multiple same-day events.

## Final analytical report

The full SQL lab joins customer dimensions to sequenced events, aggregates to customer grain, then ranks the **aggregated customer rows** (not the raw events). In simplified form:

```sql
SELECT c.customer_id, c.customer_name,
       COUNT(e.event_id) AS event_count,
       COALESCE(SUM(e.amount),0) AS lifetime_spend
FROM customers c
LEFT JOIN events e ON e.customer_id = c.customer_id
GROUP BY c.customer_id,c.customer_name;
```

This abbreviated example assumes `customers` and `events` are CTEs or tables already defined. The executable companion script includes the full inline definitions and all window metrics.

**Expected report (manually calculated, not executed):**

| ID | Customer | Events | Purchases | Spend | First | Last | Position | Dense rank |
|---:|---|---:|---:|---:|---|---|---:|---:|
| 1 | Aster | 3 | 2 | 50 | 2026-02-02 | 2026-02-16 | 1 | 1 |
| 2 | Birch | 2 | 2 | 50 | 2026-02-03 | 2026-02-10 | 2 | 1 |
| 3 | Cedar | 2 | 1 | 15 | 2026-02-09 | 2026-02-16 | 3 | 2 |
| 4 | Dune | 0 | 0 | 0 | NULL | NULL | 4 | 3 |

**Cross-checks:** four report rows; three active customers; seven events; five purchases; total spend 115; Aster/Birch tie at spend 50 but have different positions. `COUNT(e.event_id)` rather than `COUNT(*)` ensures Dune has zero events under the left join. `COALESCE` converts Dune's NULL sum to zero without fabricating activity dates.

## Hands-on lab — 20 minutes

Verify the PostgreSQL target is a disposable local `sql_tutorials` database, and inspect `PGHOST`, `PGPORT`, `PGUSER` and connection settings before proceeding. Run from the repository root:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials \
  -f sql-tutorials/labs/080-lab-08-analytical-customer-activity-report.sql
```

The lab prints connection identity, fails closed unless database name is `sql_tutorials` and PostgreSQL major version is 18, uses a read-only transaction with transaction-local timeouts, and ends with `ROLLBACK`. All data is synthetic `VALUES` rows; no schema or persistent data is created. The final acceptance query compares the complete actual and expected report **in both directions** with `EXCEPT ALL`, checks event/customer/purchase/spend counts and event sequencing, and returns `fail_closed_acceptance = 1` only if every check succeeds. A guard or assertion failure should terminate the script because `ON_ERROR_STOP` is enabled.

**Practice tasks:** (1) Explain why Dune appears and why `COUNT(*)` would be wrong. (2) Change Birch's second purchase from 10 to 20 in **a separate disposable copy** of the lab; recompute spend, positions and ranks, and update the expected assertions before executing. (3) Add a same-day visit for Aster with a new unique event ID and demonstrate deterministic sequencing. (4) Replace the `FILTER` expression with a conditional `CASE` aggregate; verify identical purchase counts. (5) Explain why summing a customer-level lifetime amount after joining to another multirow fact can double-count it.

## Validation, troubleshooting and safety

| Symptom | Cause and response |
|---|---|
| Four customers become three | An event predicate in `WHERE` turns the left join into an effective inner join; filter inside the join or aggregate |
| Inactive customer shows one event | `COUNT(*)` counts the outer-join placeholder; count a non-NULL event key |
| Spend exceeds 115 | Fan-out or duplicate events; inspect event IDs, join cardinality, and source-to-report reconciliation |
| Aster and Birch have different dense ranks | Incorrect ranking `ORDER BY` includes customer ID; rank by spend only |
| Ranking changes across runs | `ROW_NUMBER` lacks a stable tie-breaker |
| Final acceptance fails | Inspect the expected multiset and all source counts; do not suppress assertion or bypass guards |
| Wrong database/version | Stop; inspect host, port, role, version and database; never bypass the guards |

**Data engineering controls:** define event eligibility, deduplication keys, observation window, late-arrival policy, currency semantics, and customer identity mapping before productionizing. **DBRE/SRE controls:** verify execution identity, limit query duration and result cardinality, evaluate scan/sort costs, use least privilege, and benchmark only against approved nonproduction data. Read-only SQL is not automatically low-cost on a large real table. This capstone intentionally performs no DML, DDL, privilege changes, or external reads.

## Review questions with answers

**Q1. What is the report grain?** One row per customer, including inactive customers.

**Q2. Why are `ROW_NUMBER` and `DENSE_RANK` different for Aster and Birch?** Equal spend gives the same dense rank; the stable customer-ID tie breaker gives unique positions.

**Q3. Why specify `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`?** It defines an explicit row-based cumulative frame and avoids unintended peer-group behavior.

**Q4. What is the expected source-to-report spend reconciliation?** 20 + 30 + 40 + 10 + 15 = 115, and the customer totals 50 + 50 + 15 + 0 = 115.

**Q5. What does `LAG` return for the first event?** NULL unless an explicit default is provided.

**Q6. Does a successful static check establish PostgreSQL 18 runtime validity?** No. Only execution on an isolated PostgreSQL 18 instance with retained evidence establishes that state.

## References and next chapter

- [PostgreSQL 18 — Window Functions](https://www.postgresql.org/docs/18/functions-window.html)
- [PostgreSQL 18 — SELECT](https://www.postgresql.org/docs/18/sql-select.html)
- [PostgreSQL 18 — Aggregate Functions](https://www.postgresql.org/docs/18/functions-aggregate.html)
- [PostgreSQL 18 — WITH Queries](https://www.postgresql.org/docs/18/queries-with.html)
- [Chapter 081 — String Functions and Regular Expressions](../MASTER-TOC.md#part-09--sql-objects-functions--semi-structured-data)

**Validation state:** Authored content and companion SQL require independent editorial review and comprehensive syntax/link QA. Expected results were manually derived; **actual isolated PostgreSQL 18 runtime execution and reproducible evidence are pending**.
