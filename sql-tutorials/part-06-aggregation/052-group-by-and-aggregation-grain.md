# 052 — GROUP BY and Aggregation Grain

**Part 06 — Aggregation, Grouping & Reporting** · **60 minutes** · **Audience:** SQL beginners, data engineers, DBRE/SRE · **Lab target:** PostgreSQL 18

[Master TOC](../MASTER-TOC.md) · [Tutorial index](../README.md) · [Previous: 051](051-count-sum-avg-min-and-max.md) · [SQL lab 052](../labs/052-group-by-aggregation-grain.sql) · [Next: 053](../MASTER-TOC.md)

## 1. Learning outcomes and agenda (5 minutes)

After this lesson, you can define the **grain** of a table and a report; group records using one or several keys; distinguish row-level fields from grouped fields; explain NULL grouping; prevent inflated totals from one-to-many joins; and reconcile grouped totals against the raw source.

**Prerequisites:** Chapters 007–009, 041–051, especially aggregate functions and join fan-out. **Agenda:** objectives 5 min, concepts 10 min, worked examples 15 min, lab 20 min, troubleshooting 5 min, review 5 min.

## 2. Business question and synthetic fixture (5 minutes)

A fictional retailer ingests payment events. The business asks for a **one-row-per-region-and-status** report. Each input row represents **one payment event** (source grain); each output row represents **one (region, status) pair** (report grain). There are no real customer records.

| payment_id | region | status | amount |
|---:|---|---|---:|
| 1 | East | captured | 10.00 |
| 2 | East | captured | 20.00 |
| 3 | East | pending | NULL |
| 4 | West | captured | 30.00 |
| 5 | West | refunded | -5.00 |
| 6 | West | captured | 15.00 |
| 7 | NULL | captured | 8.00 |

There are **7 events**, **6 known amounts**, and **78.00 net known amount**. A refund is negative here by explicit synthetic business convention. A NULL amount means unknown, not zero. The NULL region represents missing attribution, not a named geographic region.

## 3. What GROUP BY actually does (10 minutes)

`GROUP BY` partitions rows into groups with matching grouping expressions; each aggregate operates on rows *within its group*. Without `GROUP BY`, a whole-input aggregate produces one row. With `GROUP BY region, status`, the fixture produces **5 groups**: East/captured, East/pending, West/captured, West/refunded, NULL/captured.

**Portable SQL:**

```sql
SELECT region, status,
       COUNT(*) AS event_count,
       COUNT(amount) AS known_amount_count,
       SUM(amount) AS net_amount
FROM payment_events
GROUP BY region, status
ORDER BY region, status;
```

**Expected logical result** (the lab uses PostgreSQL's default ascending NULL placement; portability of NULL sort order varies):

| region | status | event_count | known_amount_count | net_amount |
|---|---|---:|---:|---:|
| East | captured | 2 | 2 | 30.00 |
| East | pending | 1 | 0 | NULL |
| West | captured | 2 | 2 | 45.00 |
| West | refunded | 1 | 1 | -5.00 |
| NULL | captured | 1 | 1 | 8.00 |

**Important:** `COUNT(*)` counts rows even if amount is NULL; `COUNT(amount)` does not. `SUM(amount)` ignores NULL, but returns NULL for a group with no non-NULL amount. A group with a NULL key is a valid group: NULL grouping values are treated together for grouping, even though `NULL = NULL` is not TRUE in a `WHERE` predicate.

## 4. Choose and document the report grain (5 minutes)

```sql
-- One row per region: 3 output groups, including missing region.
SELECT region, COUNT(*) AS events, SUM(amount) AS net_amount
FROM payment_events
GROUP BY region
ORDER BY region;
```

Expected: East **3 / 30.00**, West **3 / 40.00**, NULL **1 / 8.00**. Different grouping keys answer different questions: region-only loses status detail; region/status preserves it. Never compare row counts from reports at different grains without accounting for the grouping.

```sql
-- One row per status: captured 5 / 83.00;
-- pending 1 / NULL; refunded 1 / -5.00.
SELECT status, COUNT(*) AS events, SUM(amount) AS net_amount
FROM payment_events
GROUP BY status
ORDER BY status;
```

A nonaggregated selected column generally must be in the `GROUP BY` (or be functionally dependent where supported). This is invalid in the ordinary case:

```sql
SELECT region, status, SUM(amount)
FROM payment_events
GROUP BY region; -- status is neither grouped nor aggregated
```

PostgreSQL rejects this with a grouping error. Avoid relying on engines that permit arbitrary non-grouped values: such queries are not portable or trustworthy.

## 5. Multiple keys, expressions, and NULL policy (5 minutes)

```sql
-- Portable grouping by an expression, not an alias.
SELECT COALESCE(region, 'Unassigned') AS region_label,
       COUNT(*) AS event_count
FROM payment_events
GROUP BY COALESCE(region, 'Unassigned')
ORDER BY region_label;
```

Expected: East 3, Unassigned 1, West 3. `COALESCE` is an explicit presentation rule; do not silently replace missing data. Choose a label that cannot collide with a real region, or retain an additional missingness indicator. PostgreSQL allows some alias/ordinal grouping conveniences, but repeating expressions is easier to port and audit.

**Logical processing, simplified:** `FROM` / `JOIN` → `WHERE` → `GROUP BY` → aggregate calculation → `HAVING` → `SELECT` → `ORDER BY`. `WHERE` filters source rows before grouping; `HAVING` filters groups afterward (Chapter 053).

## 6. Reconciliation and join fan-out (5 minutes)

Check the source **before** trusting the report:

```sql
SELECT COUNT(*) AS source_events, SUM(amount) AS source_net
FROM payment_events;
-- Expected: 7, 78.00
```

```sql
SELECT SUM(group_events) AS reconciled_events,
       SUM(group_net) AS reconciled_net
FROM (
    SELECT region, status,
           COUNT(*) AS group_events, SUM(amount) AS group_net
    FROM payment_events
    GROUP BY region, status
) AS grouped;
-- Expected: 7, 78.00
```

**Why not simply join first?** If each payment joins to several line items, `SUM(payment.amount)` counts the same payment multiple times. Preaggregate each source at its own business key, then join; check unique keys, input/output row counts, missing keys, and totals. `SUM(DISTINCT amount)` is not a valid generic fix because two real events can share the same amount. A source-to-report reconciliation should also account for intentionally excluded rows and filters.

## 7. Hands-on PostgreSQL 18 lab (20 minutes)

**Safety:** Use only a disposable, independently verified PostgreSQL 18 instance and database `sql_tutorials`. Never use production credentials. The database-name/version checks in the lab are safeguards, **not proof** that the endpoint is isolated.

Run from the repository root:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/052-group-by-aggregation-grain.sql
```

The lab starts a transaction, sets local timeouts, creates a temporary fixture, inserts only synthetic values, displays grouped reports, executes deterministic fail-closed assertions, and ends with `ROLLBACK`. An assertion failure must produce a nonzero psql exit code with `ON_ERROR_STOP`.

**Exercise A (4 min):** Predict region/status groups and event counts. **B (4 min):** Explain the difference between `COUNT(*)` and `COUNT(amount)` for East/pending. **C (4 min):** Group by region alone and reconcile 3+3+1 to seven events. **D (4 min):** Identify the invalid non-grouped column in the example above. **E (4 min):** Explain why a one-to-many join could inflate `SUM(amount)` and propose preaggregation.

**Acceptance (expected, not runtime-certified):** 7 events, 6 known amounts, 5 region/status groups, source net 78.00, region nets East 30.00 / West 40.00 / missing 8.00, and grouped reconciliation 7 / 78.00. Preserve `SELECT version()`, invocation, exit status, and terminal output before claiming real runtime validation.

## 8. Troubleshooting and operational guardrails (5 minutes)

- **`column must appear in GROUP BY`:** select only grouped expressions or aggregates; revisit the intended grain.
- **Too many groups:** inspect trailing whitespace, inconsistent case, NULL values, and unexpected grouping columns; normalize upstream only with an approved business rule.
- **Totals inflated:** check one-to-many joins and duplicate business keys; preaggregate at source grain.
- **Missing rows:** inspect `WHERE`, inner joins, and NULL predicates before grouping.
- **NULL aggregate:** a group has no known values; distinguish unknown from zero.
- **Slow aggregation:** inspect row volume, filters, memory and query plan in a safe environment; avoid assuming an index automatically improves all GROUP BY queries.
- **Version, database, or timeout guard fails:** stop and verify endpoint; never remove guards to force success.

DBRE/SRE reporting should capture source row count, grouping keys, distinct group count, source sum, reconciled sum, NULL-key count, run timestamp, and version of the SQL. For healthcare or financial reporting, obtain sign-off on metric definitions before using aggregate output operationally.

## 9. Review questions with answers (5 minutes)

1. **What is source grain?** One row per payment event in this fixture.
2. **What is report grain?** One row per unique region/status pair.
3. **How many region/status groups exist?** Five.
4. **How does GROUP BY handle NULL region?** The NULL region values form a group.
5. **Why is East/pending SUM NULL?** Its only amount is NULL.
6. **What is the region-only East count?** Three events.
7. **Why must status be grouped in a region/status report?** It is a nonaggregated output dimension.
8. **What is the reconciled net amount?** 78.00, matching the source.
9. **Why not SUM(DISTINCT amount) to fix fan-out?** It can discard legitimate equal-valued events.
10. **Is a reviewed expected result a runtime pass?** No; execute on isolated PostgreSQL 18 and retain evidence.

## 10. SQL portability

`GROUP BY`, `COUNT`, `SUM`, `COALESCE`, derived tables, and multiple grouping keys are widely supported. NULL sort placement and alias grouping rules vary; specify ordering policy when presenting output. `DO $$`, `RAISE EXCEPTION`, `CREATE TEMP TABLE ... ON COMMIT DROP`, `SET LOCAL`, and `current_setting` in the lab harness are **PostgreSQL-specific**. SQL Server, MySQL, Oracle, Snowflake, and BigQuery need their own validation harnesses. `GROUPING SETS` and `ROLLUP` are deferred to Chapter 058.

## 11. References

- [PostgreSQL 18 — SELECT / GROUP BY](https://www.postgresql.org/docs/18/sql-select.html)
- [PostgreSQL 18 — Aggregate functions](https://www.postgresql.org/docs/18/functions-aggregate.html)
- [PostgreSQL 18 — Aggregate expressions](https://www.postgresql.org/docs/18/sql-expressions.html#SYNTAX-AGGREGATES)
- [PostgreSQL 18 — Table expressions](https://www.postgresql.org/docs/18/queries-table-expressions.html)
- [PostgreSQL 18 — psql](https://www.postgresql.org/docs/18/app-psql.html)

## 12. Completion and next chapter

[Chapter 053 — HAVING versus WHERE](../MASTER-TOC.md) will distinguish filtering individual source rows from filtering aggregated groups. **Authored/published, editorially reviewed, targeted statically inspected, comprehensive static QA, and actual PostgreSQL 18 runtime-validated are separate states.** No PostgreSQL 18 execution is claimed by this manuscript.
