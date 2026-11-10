# 054 — Conditional Aggregation with CASE and FILTER

**Part 06 — Aggregation, Grouping & Reporting** · **60 minutes** · **Audience:** SQL beginners, data engineers, DBRE/SRE · **Primary lab:** PostgreSQL 18

[Master TOC](../MASTER-TOC.md) · [Index](../README.md) · [Previous: 053](053-having-versus-where.md) · [Lab 054](../labs/054-conditional-aggregation-case-filter.sql) · [Next: 055](../MASTER-TOC.md)

## 1. Objectives and prerequisites (5 minutes)

By the end, explain conditional aggregation; build multiple status-specific KPIs in one query; compare portable `CASE` to PostgreSQL `FILTER`; distinguish row counts from non-NULL value counts; handle zero qualifying rows and NULL amounts; reconcile report totals; and prevent duplicate-counting after joins. Prerequisites: [051](051-count-sum-avg-min-and-max.md), [052](052-group-by-and-aggregation-grain.md), and [053](053-having-versus-where.md).

**Agenda:** objectives 5; concepts 10; examples 15; isolated lab 20; troubleshooting 5; review 5 minutes.

## 2. Scenario and source grain

A synthetic retailer tracks **one row per payment event**. Amounts are in a fictional reporting currency. A refund is represented as a negative amount; pending records do not contribute to captured revenue.

| event_id | region | status | amount |
|---:|---|---|---:|
| 1 | East | captured | 20.00 |
| 2 | East | captured | 30.00 |
| 3 | East | refunded | -5.00 |
| 4 | East | pending | NULL |
| 5 | West | captured | 40.00 |
| 6 | West | refunded | -10.00 |
| 7 | West | pending | 15.00 |
| 8 | North | captured | 25.00 |
| 9 | North | captured | NULL |
| 10 | North | pending | NULL |
| 11 | NULL | captured | 10.00 |
| 12 | South | pending | NULL |

There are **12 events**: 6 captured, 2 refunded, 4 pending; **8 non-NULL amounts**; captured known amount **125.00**; refund amount **-15.00**; pending known amount **15.00**; all-status known net **125.00**. The matching captured and all-status totals are coincidental: pending +15.00 offsets refunds -15.00.

## 3. Portable CASE conditional aggregation (10 minutes)

The following query is broadly portable SQL (table name is supplied by the lab):

```sql
SELECT region,
       COUNT(*) AS all_events,
       SUM(CASE WHEN status = 'captured' THEN 1 ELSE 0 END) AS captured_events,
       SUM(CASE WHEN status = 'captured' THEN amount ELSE 0 END) AS captured_amount,
       SUM(CASE WHEN status = 'refunded' THEN amount ELSE 0 END) AS refund_amount
FROM payment_events
GROUP BY region
ORDER BY region;
```

`CASE` selects a value **for each input row**, then `SUM` aggregates those values. It does not remove rows from the input population. With `ELSE 0`, nonmatching rows contribute zero. However, a matching row with `amount IS NULL` still contributes NULL; `SUM` ignores that NULL. A group containing only matching NULL amounts can produce NULL, rather than zero.

For a guaranteed zero when there are no known matching values, use `COALESCE(SUM(CASE WHEN ... THEN amount END), 0)`. This **does not** mean the missing amount is actually zero: retain a separate missing-value count.

## 4. PostgreSQL FILTER versus CASE (10 minutes)

**PostgreSQL-specific / supported PostgreSQL 18:** `FILTER (WHERE condition)` attaches a predicate to one aggregate, while other aggregates retain the same group.

```sql
SELECT region,
       COUNT(*) AS all_events,
       COUNT(*) FILTER (WHERE status = 'captured') AS captured_events,
       COUNT(amount) FILTER (WHERE status = 'captured') AS captured_known_amounts,
       COALESCE(SUM(amount) FILTER (WHERE status = 'captured'), 0) AS captured_amount,
       COALESCE(SUM(amount) FILTER (WHERE status = 'refunded'), 0) AS refund_amount
FROM payment_events
GROUP BY region
ORDER BY region;
```

For this dataset, `COUNT(*) FILTER (WHERE status = 'captured')` equals `SUM(CASE WHEN status = 'captured' THEN 1 ELSE 0 END)`. `COUNT(amount) FILTER (...)` counts only captured rows **whose amount is not NULL**. PostgreSQL supports `FILTER`, but not all SQL engines accept the same syntax: use the `CASE` pattern when portability matters and test each target dialect.

| region | all events | captured events | captured known | captured amount | refunds |
|---|---:|---:|---:|---:|---:|
| East | 4 | 2 | 2 | 50.00 | -5.00 |
| North | 3 | 2 | 1 | 25.00 | 0.00 |
| South | 1 | 0 | 0 | 0.00 | 0.00 |
| West | 3 | 1 | 1 | 40.00 | -10.00 |
| NULL | 1 | 1 | 1 | 10.00 | 0.00 |

**Important:** SQL's default ascending NULL ordering differs among vendors. The displayed table puts the NULL region last for readability; in PostgreSQL `ORDER BY region NULLS LAST` makes this explicit.

## 5. Worked examples and reconciliation (5 minutes)

Count the captured rows with missing amounts, separately from captured event count:

```sql
SELECT COUNT(*) AS all_events,
       SUM(CASE WHEN status = 'captured' THEN 1 ELSE 0 END) AS captured_events,
       SUM(CASE WHEN status = 'captured' AND amount IS NULL THEN 1 ELSE 0 END) AS captured_missing_amounts,
       COALESCE(SUM(CASE WHEN status = 'captured' THEN amount END), 0) AS captured_known_total
FROM payment_events;
-- 12, 6, 1, 125.00
```

**Reconciliation:** captured 125.00 + refunded -15.00 + pending known 15.00 = all-status 125.00. Never treat equal totals as evidence that two datasets have equal rows. Group by region before applying presentation filters; otherwise unknown regions disappear silently.

**Anti-pattern:** `COUNT(CASE WHEN status='captured' THEN 1 ELSE 0 END)` counts **every row** because both 1 and 0 are non-NULL. Use `SUM(CASE ... THEN 1 ELSE 0 END)` or `COUNT(CASE WHEN ... THEN 1 END)`.

## 6. Data engineering and DBRE/SRE safeguards (5 minutes)

Document source grain, status mapping, refund sign convention, missing-value policy, and reporting time window. Joining payment events to multiple order items can multiply events and inflate KPIs: aggregate to one row per event/order before joining or use an explicitly tested semijoin. Check both `COUNT(*)` and `COUNT(DISTINCT event_id)` when diagnosing fan-out. Keep source totals, per-status totals, missing amount counts, and unknown-region counts in acceptance evidence. Prefer approved reporting databases for expensive production queries; this exercise is **isolated only**.

## 7. Hands-on lab (20 minutes)

Run only in an independently verified disposable PostgreSQL **18.x** instance and database `sql_tutorials`. The database/version guard is **not** proof that an endpoint is isolated. Verify host, port, user, database, and network environment before executing. The lab creates only a temporary table inside a transaction, sets local timeouts, asserts expected totals, and rolls back.

From repository root:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/054-conditional-aggregation-case-filter.sql
```

Exercises (4 minutes each): **A** predict captured/refunded/pending counts; **B** produce per-region metrics with portable `CASE`; **C** repeat using PostgreSQL `FILTER`; **D** explain North's 2 captured events but 1 known amount; **E** reconcile 125.00 across statuses and explain why South has a zero-filled captured sum.

**Expected acceptance (not executed evidence):** 12 source events; 6 captured, 2 refunded, 4 pending; 8 known amounts; captured amount 125.00; refund -15.00; pending known 15.00; 1 captured NULL amount; 5 region groups including NULL; CASE/FILTER parity. The lab raises an exception on discrepancies.

## 8. Troubleshooting and operational checks (5 minutes)

- **Counts unexpectedly equal all rows:** avoid `COUNT(CASE ... ELSE 0 END)`.
- **SUM returns NULL:** distinguish zero qualifying rows from qualifying rows with unknown amounts; use `COALESCE` for display and separately report missing values.
- **Unexpected total after join:** check event-key uniqueness and preaggregate before joining one-to-many dimensions.
- **Status totals do not reconcile:** verify sign conventions, unexpected statuses, NULL amounts, and filters.
- **Different vendor results:** validate `FILTER` support, NULL sorting, numeric types, and aggregate semantics; use `CASE` fallback.
- **Guard/timeout fails:** stop and inspect environment; never disable protections to force a pass.

## 9. Review questions and answers (5 minutes)

1. **What is conditional aggregation?** Applying a row-level condition inside an aggregate expression.
2. **Does CASE remove nonmatching rows from the group?** No; it changes their contribution to the aggregate.
3. **What is the portable count pattern?** `SUM(CASE WHEN condition THEN 1 ELSE 0 END)`.
4. **Why is COUNT(CASE ... ELSE 0 END) wrong for matching-row counts?** Zero is non-NULL and is counted.
5. **What does FILTER do?** Restricts rows seen by one aggregate, not the entire query.
6. **Why are captured events 6 but captured known amounts 5?** One captured event has NULL amount.
7. **What is the captured amount?** 125.00 in known values.
8. **What is the refund amount?** -15.00.
9. **Why can captured and all-status totals match?** Pending +15.00 cancels refunds -15.00.
10. **Is this lab runtime-certified?** No; PostgreSQL 18 execution plus retained evidence is required.

## 10. Portability and safety

`CASE`, `SUM`, `COUNT`, `COALESCE`, and `GROUP BY` are broadly portable; `FILTER` support varies by vendor. PostgreSQL-specific lab constructs include `DO $$`, `RAISE EXCEPTION`, `SET LOCAL`, `CREATE TEMP TABLE ... ON COMMIT DROP`, and `IS DISTINCT FROM` checks. The lab uses synthetic data, no production credentials, and no persistent changes.

## 11. References

- [PostgreSQL 18 aggregate functions and FILTER](https://www.postgresql.org/docs/18/sql-expressions.html#SYNTAX-AGGREGATES)
- [PostgreSQL 18 aggregate function reference](https://www.postgresql.org/docs/18/functions-aggregate.html)
- [PostgreSQL 18 conditional expressions](https://www.postgresql.org/docs/18/functions-conditional.html)
- [PostgreSQL 18 SELECT and grouping](https://www.postgresql.org/docs/18/sql-select.html)
- [PostgreSQL 18 psql](https://www.postgresql.org/docs/18/app-psql.html)

## 12. Completion and next chapter

Next: [055 — Date-based grouping and time buckets](../MASTER-TOC.md). Publication, targeted static reasoning, independent editorial review, comprehensive static QA, and **actual isolated PostgreSQL 18 runtime validation** are separate states. No runtime execution is claimed here.
