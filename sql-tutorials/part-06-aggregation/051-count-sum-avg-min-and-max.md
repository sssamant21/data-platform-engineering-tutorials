# 051 — COUNT, SUM, AVG, MIN, and MAX

**Part 06 — Aggregation, Grouping & Reporting** · **60 minutes** · **Audience:** SQL beginners, data engineers, DBRE/SRE · **Target:** PostgreSQL 18

[Master TOC](../MASTER-TOC.md) · [Tutorial index](../README.md) · [Previous: 050](../part-05-joins/050-lab-05-consolidate-customers-orders-and-payments.md) · [Executable lab 051](../labs/051-count-sum-avg-min-max.sql) · [Next: 052](../MASTER-TOC.md)

## 1. Learning outcomes and agenda (5 minutes)

After this chapter you can: (1) explain how five common aggregates summarize rows; (2) distinguish `COUNT(*)`, `COUNT(column)`, and `COUNT(DISTINCT column)`; (3) predict how NULL affects aggregates; (4) use `COALESCE` safely on empty inputs; (5) verify source-to-report reconciliation; (6) recognize duplicate-join inflation and integer/decimal precision issues.

**Agenda:** objectives 5 min; definitions 10; worked queries 15; isolated lab 20; troubleshooting 5; review 5. Prerequisites: Chapters 007–009, 041–050; SELECT, NULL, and joins. Chapter 052 introduces GROUP BY; this chapter deliberately aggregates **the entire input** into a single result row.

## 2. Synthetic data engineering scenario (5 minutes)

A fictional retailer ingests five payment events. The team needs daily operational checks: total events, non-NULL amounts, distinct orders, total captured value, average value, smallest and largest value. The data is illustrative and contains no real customers.

| payment_id | order_id | amount | Meaning |
|---:|---:|---:|---|
| 1 | 101 | 10.00 | Captured |
| 2 | 101 | 30.00 | Captured |
| 3 | 102 | 20.00 | Captured |
| 4 | 103 | NULL | Pending amount, unknown |
| 5 | 104 | 40.00 | Captured |

The **source grain** is one row per payment event, not one row per order. There are five events, four known amounts, four distinct order IDs, and a known-amount total of 100.00.

## 3. Five aggregate functions (10 minutes)

| Expression | Meaning | NULL behavior | Expected on fixture |
|---|---|---|---:|
| `COUNT(*)` | Number of input rows | Counts rows even with NULL values | 5 |
| `COUNT(amount)` | Non-NULL amount count | Ignores NULL | 4 |
| `SUM(amount)` | Sum of known values | Ignores NULL | 100.00 |
| `AVG(amount)` | Average of known values | Ignores NULL; divides by 4, not 5 | 25.00 |
| `MIN(amount)` | Smallest known amount | Ignores NULL | 10.00 |
| `MAX(amount)` | Largest known amount | Ignores NULL | 40.00 |

`COUNT(DISTINCT order_id)` is 4; `COUNT(DISTINCT amount)` is also 4 in this fixture, but the two concepts differ. A NULL amount is **unknown**, not zero. Converting it to zero before averaging changes the metric to 20.00; do that only if the business definition explicitly requires treating missing amounts as zero.

## 4. Portable SQL: worked examples (10 minutes)

Assume a table `payment_events(payment_id, order_id, amount)`:

```sql
SELECT COUNT(*) AS event_count,
       COUNT(amount) AS known_amount_count,
       COUNT(DISTINCT order_id) AS distinct_orders,
       SUM(amount) AS total_amount,
       AVG(amount) AS mean_known_amount,
       MIN(amount) AS minimum_amount,
       MAX(amount) AS maximum_amount
FROM payment_events;
```

**Expected:** one result row with `5, 4, 4, 100.00, 25.00, 10.00, 40.00`. Aggregate functions without `GROUP BY` produce a single group, even if the input has zero rows.

```sql
SELECT COUNT(*) AS missing_amount_count
FROM payment_events
WHERE amount IS NULL;
-- Expected: 1
```

```sql
SELECT COUNT(*) AS event_count,
       COUNT(amount) AS known_count,
       AVG(amount) AS average_known,
       AVG(COALESCE(amount, 0)) AS average_if_missing_means_zero
FROM payment_events;
-- Expected: 5, 4, 25.00, 20.00
```

**Critical difference:** `COALESCE(SUM(amount), 0)` replaces a NULL *result* when no non-NULL values exist. `SUM(COALESCE(amount,0))` replaces NULL *inputs*. These can agree for sums but have different meaning, particularly for AVG. Document the intended null policy before choosing.

## 5. Empty inputs, precision, and reproducibility (5 minutes)

```sql
SELECT COUNT(*) AS rows_seen,
       SUM(amount) AS amount_total,
       AVG(amount) AS amount_average
FROM payment_events
WHERE order_id = -999;
-- Expected: 0, NULL, NULL (one aggregate result row).
```

`COUNT(*)` returns 0 on empty input, while `SUM`, `AVG`, `MIN`, and `MAX` return NULL. If an operational dashboard needs an explicit zero for an empty sum, use `COALESCE(SUM(amount), 0)` and label that policy. Use exact `DECIMAL`/`NUMERIC` for currency-like samples; floating-point arithmetic may not be exact. PostgreSQL `AVG(integer)` yields a numeric result, but return types differ by vendor. Always validate types and rounding requirements.

## 6. Join fan-out: why aggregation can lie (5 minutes)

A report joining orders to payments duplicates an order row when it has multiple payments. `SUM(o.order_amount)` after a one-to-many join can inflate the order total. To report order-level totals, aggregate payments by order first, then join; or aggregate each source at its native grain and reconcile separately. **Never repair fan-out with `SUM(DISTINCT amount)`**: two legitimate events may have identical amounts. Use explicit join keys, row-count checks, uniqueness checks, and independent source totals.

## 7. Hands-on PostgreSQL 18 lab (20 minutes)

Use a disposable PostgreSQL **18** database named `sql_tutorials` and a nonproduction account. Verify the endpoint independently; the database-name guard is not proof of isolation. The [lab file](../labs/051-count-sum-avg-min-max.sql) creates a transaction-scoped temporary table, uses only synthetic rows, sets timeouts, performs deterministic assertions, and rolls back.

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/051-count-sum-avg-min-max.sql
```

**Exercise A:** Predict the seven columns in the main aggregate query. **B:** Explain why `COUNT(*) - COUNT(amount)` equals 1. **C:** Predict `AVG(COALESCE(amount,0))`. **D:** Predict aggregate results for an impossible order ID. **E:** In a disposable copy, insert a second 10.00 event and explain why `SUM(DISTINCT amount)` would undercount.

**Acceptance criteria (predicted, not executed here):** 5 events, 4 known amounts, 1 missing amount, 4 distinct orders, sum 100.00, average 25.00, min 10.00, max 40.00, zero-filled average 20.00, and an empty-input count of 0 with NULL sum/average. The script fails closed on mismatches.

## 8. Troubleshooting and safety (5 minutes)

- **Average is 20 rather than 25:** NULL amounts were converted to zero before AVG; confirm the business definition.
- **Count differs between expressions:** `COUNT(column)` skips NULL; `COUNT(*)` does not.
- **Unexpected NULL total:** the filtered input is empty or every amount is NULL; inspect row counts first.
- **Inflated totals:** inspect join cardinality and duplicate keys before adding DISTINCT.
- **Unexpected decimal result:** verify source column types, implicit casts, precision, and rounding.
- **Guard or timeout failure:** stop, verify PostgreSQL version/database/endpoint, and rerun only in an isolated environment; never remove safeguards for convenience.

DBRE/SRE checks should record the query version, expected source grain, source row count, missing-value count, distinct-key count, source sum, and acceptance status. Never run the mutation-based fixture in production or against sensitive records.

## 9. Review questions with answers (5 minutes)

1. **What does `COUNT(*)` count?** All input rows, including rows containing NULL.
2. **What does `COUNT(amount)` count?** Only rows with non-NULL amount.
3. **Why is AVG 25.00?** The known values total 100.00 across four non-NULL amounts.
4. **What does `SUM(amount)` return on zero input rows?** NULL, not zero.
5. **Why is `COUNT(DISTINCT order_id)` four?** Orders 101, 102, 103, and 104 occur.
6. **Can `SUM(DISTINCT amount)` fix duplicate joins?** No; it removes legitimately repeated amounts.
7. **What is the safe aggregation grain?** The grain required by the metric, checked against source keys.
8. **Does reading expected output certify runtime success?** No; isolated PostgreSQL 18 execution and retained evidence are required.

## 10. Portability notes

`COUNT`, `SUM`, `AVG`, `MIN`, `MAX`, `DISTINCT`, `COALESCE`, and `WHERE` are widely supported SQL features. PostgreSQL-specific harness features include `DO $$`, `RAISE EXCEPTION`, `CREATE TEMP TABLE ... ON COMMIT DROP`, `SET LOCAL`, `current_setting`, and psql error-stop settings. SQL Server, Oracle, MySQL, Snowflake, and BigQuery have different procedural scripting and temporary-table semantics; do not paste the lab harness into them unchanged. Exact aggregate return types and numeric precision can vary by engine.

## 11. Authoritative references

- [PostgreSQL 18 — Aggregate functions](https://www.postgresql.org/docs/18/functions-aggregate.html)
- [PostgreSQL 18 — Aggregate expressions](https://www.postgresql.org/docs/18/sql-expressions.html#SYNTAX-AGGREGATES)
- [PostgreSQL 18 — SELECT](https://www.postgresql.org/docs/18/sql-select.html)
- [PostgreSQL 18 — Numeric types](https://www.postgresql.org/docs/18/datatype-numeric.html)
- [PostgreSQL 18 — psql](https://www.postgresql.org/docs/18/app-psql.html)

## 12. Completion and next milestone

This chapter introduces whole-input aggregation; [Chapter 052 — GROUP BY and aggregation grain](../MASTER-TOC.md) will split aggregates into multiple groups. **Authored/published ≠ independently editorially reviewed ≠ comprehensive static QA ≠ PostgreSQL 18 runtime-validated.** Preserve execution logs and exact server version before claiming runtime acceptance.
