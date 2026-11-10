# 053 — HAVING versus WHERE

**Part 06 — Aggregation, Grouping & Reporting** · **60 minutes** · **Audience:** SQL beginners, data engineers, DBRE/SRE · **Primary lab:** PostgreSQL 18

[Master TOC](../MASTER-TOC.md) · [Tutorial index](../README.md) · [Previous: 052](052-group-by-and-aggregation-grain.md) · [Lab 053](../labs/053-having-versus-where.sql) · [Next: 054](../MASTER-TOC.md)

## 1. Learning objectives and agenda (5 minutes)

After this chapter, you can (1) decide whether a predicate belongs in `WHERE` or `HAVING`; (2) describe how pre-group filtering changes aggregate denominators; (3) combine row and group predicates; (4) handle NULL and empty groups; (5) detect incorrect KPI reports caused by filters; and (6) reconcile source and grouped totals.

**Prerequisites:** Chapters [051](051-count-sum-avg-min-and-max.md) and [052](052-group-by-and-aggregation-grain.md), plus basic `SELECT` and `WHERE`.

**Agenda:** outcomes 5 min; concepts 10 min; worked examples 15 min; hands-on 20 min; troubleshooting 5 min; review 5 min.

## 2. Scenario: a synthetic payment operations feed (5 minutes)

A fictional retailer wants to find regions with at least two **captured** payment events and at least 40.00 in captured value. Each source row represents one payment event, not one order or one customer.

| event_id | region | status | amount |
|---:|---|---|---:|
| 1 | East | captured | 10.00 |
| 2 | East | captured | 20.00 |
| 3 | East | pending | NULL |
| 4 | West | captured | 30.00 |
| 5 | West | refunded | -5.00 |
| 6 | West | captured | 15.00 |
| 7 | NULL | captured | 8.00 |
| 8 | North | captured | 50.00 |
| 9 | North | pending | 5.00 |
| 10 | North | captured | 10.00 |

There are **10 events**, **9 known amounts**, and **143.00 net amount** across all statuses. Captured events alone total **7 events / 143.00**: East 2/30.00, West 2/45.00, North 2/60.00, and missing region 1/8.00. The equality of the two net totals is coincidental: the -5.00 refund and +5.00 pending event cancel. Never infer that two filtered datasets are equivalent from their sums alone.

## 3. The core distinction (10 minutes)

**Portable SQL:** `WHERE` filters **individual source rows before grouping**; `HAVING` filters **groups after aggregation**.

```sql
SELECT region,
       COUNT(*) AS captured_events,
       SUM(amount) AS captured_amount
FROM payment_events
WHERE status = 'captured'
GROUP BY region
HAVING COUNT(*) >= 2
   AND SUM(amount) >= 40.00
ORDER BY region;
```

Expected output (sorted by region):

| region | captured_events | captured_amount |
|---|---:|---:|
| North | 2 | 60.00 |
| West | 2 | 45.00 |

East fails the amount threshold (30.00); missing region fails the event-count threshold (1). The `WHERE` predicate means that `COUNT(*)` and `SUM(amount)` are calculated only from captured events.

A useful simplified logical order is `FROM/JOIN → WHERE → GROUP BY → aggregate calculation → HAVING → SELECT → ORDER BY`. The database optimizer may physically reorder operations while preserving SQL semantics.

**Common error:** `WHERE SUM(amount) >= 40` is invalid because a `WHERE` predicate cannot use a grouped aggregate from the same query level. Use `HAVING SUM(amount) >= 40`.

## 4. Worked examples: subtle differences (10 minutes)

### A. Filter rows first, then groups

```sql
SELECT region, COUNT(*) AS n, SUM(amount) AS captured_total
FROM payment_events
WHERE status = 'captured'
GROUP BY region
HAVING COUNT(*) >= 2
ORDER BY region;
```

Expected: East 2/30.00, North 2/60.00, West 2/45.00. The missing region is excluded because it has only one captured event.

### B. Filter groups but retain all statuses

```sql
SELECT region, COUNT(*) AS all_events, SUM(amount) AS all_status_net
FROM payment_events
GROUP BY region
HAVING COUNT(*) >= 2
ORDER BY region;
```

Expected: East 3/30.00, North 3/65.00, West 3/40.00. This is **not** a captured-only report. The missing-region group has one row and is excluded.

### C. Count captured events while retaining all rows

```sql
SELECT region,
       COUNT(*) AS all_events,
       SUM(CASE WHEN status = 'captured' THEN 1 ELSE 0 END) AS captured_events,
       SUM(CASE WHEN status = 'captured' THEN amount ELSE 0 END) AS captured_amount
FROM payment_events
GROUP BY region
HAVING SUM(CASE WHEN status = 'captured' THEN 1 ELSE 0 END) >= 2
ORDER BY region;
```

Expected: East all=3/captured=2/amount=30.00; North 3/2/60.00; West 3/2/45.00. This retains the all-status denominator while computing captured-only metrics. The `CASE` expression is broadly portable; PostgreSQL's `FILTER (WHERE ...)` aggregate syntax is covered in Chapter 054.

### D. A group-level condition is not a row-level condition

```sql
SELECT region, COUNT(*) AS n, SUM(amount) AS net
FROM payment_events
WHERE amount >= 20
GROUP BY region
HAVING COUNT(*) >= 2;
```

Expected: **no rows**. Only East/20, West/30, and North/50 satisfy the row-level amount predicate, each in a different group. In contrast, `HAVING SUM(amount) >= 20` on unfiltered input returns multiple regions. Do not move predicates between clauses without rechecking business meaning.

### E. NULL and aggregate behavior

`WHERE status = 'pending'` retains East/NULL and North/5.00. Grouping by region gives East `COUNT(*)=1`, `COUNT(amount)=0`, `SUM(amount)=NULL`; North 1/1/5.00. `HAVING SUM(amount) > 0` excludes East because `NULL > 0` is UNKNOWN, not TRUE. Use `COALESCE` only when the business explicitly defines missing amounts as zero.

## 5. Grouping without GROUP BY and aliases (5 minutes)

```sql
SELECT COUNT(*) AS event_count, SUM(amount) AS net
FROM payment_events
HAVING COUNT(*) >= 10;
-- One row: 10, 143.00
```

Without explicit grouping columns, a whole-input aggregate forms one implicit group. Some dialects restrict `HAVING` without `GROUP BY`; test portability. Prefer repeating aggregate expressions in `HAVING` rather than relying on a `SELECT` alias being visible there. In PostgreSQL, `HAVING captured_amount > 40` generally fails if `captured_amount` is an output alias.

## 6. Data engineering and DBRE/SRE correctness checks (5 minutes)

A report should record both the *source population* and the *filtered population*. Run these checks before publishing KPI totals:

```sql
SELECT COUNT(*) AS source_rows, COUNT(amount) AS known_amounts,
       SUM(amount) AS all_status_net
FROM payment_events;
-- 10, 9, 143.00

SELECT COUNT(*) AS captured_rows, SUM(amount) AS captured_net
FROM payment_events WHERE status = 'captured';
-- 7, 143.00
```

The final report contains only North and West, so its **captured amount sums to 105.00**, not 143.00. The difference **38.00** is intentionally excluded: East 30.00 plus missing-region 8.00. Reconcile these populations explicitly rather than expecting the post-`HAVING` total to equal the unfiltered source total.

**Operational controls:** document metric grain, status filter, amount sign convention, NULL policy, thresholds, time window, and data freshness. Beware one-to-many join fan-out before aggregation (Chapter 049); preaggregate to the event key when necessary. Apply bounded read queries to a replica or approved reporting database when production access is unavoidable; the lab below must **never** run against production.

## 7. Hands-on PostgreSQL 18 lab (20 minutes)

Use a **disposable isolated PostgreSQL 18 instance**, database `sql_tutorials`, and synthetic records only. Verify the endpoint, host, port, user, and isolation independently before running. The lab's database/version guard is not proof of isolation. It creates a temporary table inside a transaction, sets local timeouts, runs reporting queries and fail-closed assertions, and finishes with `ROLLBACK`.

From repository root:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/053-having-versus-where.sql
```

Exercises (4 minutes each): **A** predict captured-only groups before and after `HAVING`; **B** compare captured-only and all-status West totals; **C** explain why East pending has a NULL sum; **D** write the conditional captured-event count using `CASE`; **E** reconcile the final 105.00 against the captured 143.00.

**Expected acceptance, not a runtime claim:** source 10/143.00, captured 7/143.00, qualifying North 2/60.00 and West 2/45.00, report 2 groups/105.00, excluded captured 38.00, pending East NULL sum. The lab raises an exception on mismatches. For runtime certification, retain `SELECT version()`, exact invocation, terminal output, exit code, and isolated environment identification.

## 8. Troubleshooting and safety (5 minutes)

- **Aggregate in WHERE:** move the aggregate predicate to `HAVING` or use an outer query over a grouped subquery.
- **Unexpected totals:** compare pre-`WHERE` and post-`WHERE` populations, then inspect group-level exclusions and duplicate joins.
- **Too few groups:** review `HAVING` thresholds and NULL/UNKNOWN behavior; do not silently weaken conditions.
- **Incorrect denominators:** use conditional aggregation when reporting all-event and subset-event measures together.
- **Alias not found in HAVING:** repeat the aggregate expression or use a derived table.
- **Slow report:** inspect predicate selectivity, grouping cardinality, and plans on an approved nonproduction environment; filtering earlier may reduce work but must not change the intended population.
- **Guard or timeout failure:** stop, verify the target and environment; never remove safeguards merely to make the script pass.

## 9. Review questions with answers (5 minutes)

1. **When does WHERE apply?** Before grouping, to individual rows.
2. **When does HAVING apply?** After aggregation, to grouped results.
3. **Can WHERE use SUM(amount) at the same query level?** No.
4. **Which regions pass captured count >=2 and captured sum >=40?** North and West.
5. **What is the final report total?** 105.00.
6. **Why does 105.00 differ from captured 143.00?** East 30.00 and unassigned 8.00 are excluded by HAVING.
7. **Why is West all-status net 40.00 but captured total 45.00?** The -5.00 refund is present only in the all-status calculation.
8. **Does NULL > 0 pass HAVING?** No; the comparison is UNKNOWN.
9. **How can you count captured events while keeping all rows?** Conditional aggregation with `SUM(CASE WHEN ... THEN 1 ELSE 0 END)`.
10. **Does a deterministic expected result prove PostgreSQL 18 runtime acceptance?** No; execution and retained evidence are required.

## 10. Portability notes

`WHERE`, `GROUP BY`, `HAVING`, `CASE`, `COUNT`, `SUM`, and `COALESCE` are broadly portable. Dialects differ in output-alias visibility, boolean expressions, and `HAVING` without explicit `GROUP BY`. The lab's `DO $$`, `RAISE EXCEPTION`, `CREATE TEMP TABLE ... ON COMMIT DROP`, `SET LOCAL`, `FILTER`, and `current_setting` are **PostgreSQL-specific harness constructs**, not portable tutorial SQL. No cross-vendor execution is claimed.

## 11. References

- [PostgreSQL 18 — SELECT, WHERE, GROUP BY, HAVING](https://www.postgresql.org/docs/18/sql-select.html)
- [PostgreSQL 18 — Table expressions and HAVING](https://www.postgresql.org/docs/18/queries-table-expressions.html)
- [PostgreSQL 18 — Aggregate functions](https://www.postgresql.org/docs/18/functions-aggregate.html)
- [PostgreSQL 18 — Conditional expressions](https://www.postgresql.org/docs/18/functions-conditional.html)
- [PostgreSQL 18 — psql](https://www.postgresql.org/docs/18/app-psql.html)

## 12. Completion and next chapter

[Chapter 054 — Conditional aggregation with CASE and FILTER](../MASTER-TOC.md) builds multiple KPI measures from a shared input population. **Authored/published**, **independently editorially reviewed**, **targeted statically inspected**, **comprehensively static-QA checked**, and **actually PostgreSQL 18 runtime-validated** are separate states. This chapter does not claim runtime validation.
