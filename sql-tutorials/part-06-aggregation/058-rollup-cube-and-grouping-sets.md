# 058 — ROLLUP, CUBE, and GROUPING SETS

**Part 06 — Aggregation, Grouping & Reporting | Duration: 60 minutes | Audience: SQL beginners, data engineers, DBRE/SRE**

**Prerequisites:** [051 — Aggregate functions](051-count-sum-avg-min-and-max.md), [052 — GROUP BY and aggregation grain](052-group-by-and-aggregation-grain.md), and [054 — Conditional aggregation](054-conditional-aggregation-with-case-and-filter.md).

## 1. Learning outcomes and agenda (5 minutes)

By the end, you can (1) distinguish detail groups from subtotals and grand totals, (2) use `ROLLUP`, `CUBE`, and `GROUPING SETS`, (3) label synthetic subtotal rows without confusing them with genuine NULL dimension values, (4) reconcile report totals without double counting, and (5) choose a bounded query for operational reporting.

Time plan: outcomes 5m; concepts 10m; guided examples 15m; hands-on 20m; troubleshooting 5m; review 5m.

## 2. Concepts, SQL semantics, and portability (10 minutes)

A normal `GROUP BY region, channel` returns only existing region/channel combinations. `ROLLUP(region, channel)` adds a subtotal for each region and one grand total: it is **hierarchical** and sensitive to column order. `CUBE(region, channel)` adds every grouping combination: detail, region subtotal, channel subtotal, and grand total. `GROUPING SETS ((region, channel), (region), ())` explicitly requests only those levels; the empty grouping set `()` means grand total.

| Construct | Grouping sets for two dimensions | Typical use |
|---|---|---|
| `GROUP BY region, channel` | (region, channel) | Detail |
| `ROLLUP(region, channel)` | (region, channel), (region), () | Hierarchical subtotals |
| `CUBE(region, channel)` | (region, channel), (region), (channel), () | All subtotal directions |
| `GROUPING SETS ((region),(channel),())` | (region), (channel), () | Selected summary levels |

`GROUPING(region)` is **0** when region participates in that row's grouping set and **1** when it is rolled up. It distinguishes a real NULL region from a subtotal placeholder NULL. PostgreSQL supports `GROUPING` with grouping sets; cross-vendor syntax and grouping identifiers vary. SQL `ROLLUP`/`CUBE`/`GROUPING SETS` are standardized concepts but not universally implemented (for example SQLite has no native equivalents). Portable fallback: write separate `GROUP BY` queries combined using `UNION ALL`, with explicit level tags and compatible types. Do not treat `GROUPING` or `ROLLUP` as supported in every SQL engine without checking its documentation.

## 3. Guided walkthrough with synthetic events (15 minutes)

Our six fictional payment records have two dimensions and an exact numeric amount:

| Event | Region | Channel | Amount |
|---|---|---|---:|
| 1 | East | web | 10.00 |
| 2 | East | web | 20.00 |
| 3 | East | store | 30.00 |
| 4 | West | web | 40.00 |
| 5 | West | store | 50.00 |
| 6 | NULL | web | 5.00 |

Source grand total = **155.00**, six rows. `NULL` means the source region is unknown; it must not be confused with the region placeholder for a rolled-up row.

**A. Hierarchical totals:**

```sql
SELECT region, channel, GROUPING(region) AS region_rolled_up,
       GROUPING(channel) AS channel_rolled_up,
       COUNT(*) AS events, SUM(amount) AS total
FROM ch058_events
GROUP BY ROLLUP (region, channel)
ORDER BY GROUPING(region), region NULLS LAST,
         GROUPING(channel), channel NULLS LAST;
```

Expected **9 rows**: five detail combinations (including one with unknown region), three region subtotals (East 60.00, West 90.00, unknown region 5.00), and one grand total. The source contains five distinct dimension pairs. A subtotal for unknown region has `region_rolled_up=0`, while the grand total has `region_rolled_up=1`.

**B. All combinations:**

```sql
SELECT region, channel, GROUPING(region) AS region_rolled_up,
       GROUPING(channel) AS channel_rolled_up,
       SUM(amount) AS total
FROM ch058_events
GROUP BY CUBE (region, channel);
```

Expected **11 rows**: 5 detail + 3 region subtotals + 2 channel subtotals (web 75.00, store 80.00) + 1 grand total = 11. Notice that the web total is 10 + 20 + 40 + 5 = **75.00**.

**C. Choose only the required levels:**

```sql
SELECT region, channel, GROUPING(region) AS gr,
       GROUPING(channel) AS gc, COUNT(*) AS events, SUM(amount) AS total
FROM ch058_events
GROUP BY GROUPING SETS ((region, channel), (region), ())
ORDER BY gr, region NULLS LAST, gc, channel NULLS LAST;
```

This produces the same nine grouping rows as the two-column `ROLLUP`, but makes the requested reporting grain explicit. For a KPI report requiring only region totals and grand total, use `GROUPING SETS ((region),())` to avoid computing detail rows.

**D. Label rows safely:**

```sql
SELECT CASE WHEN GROUPING(region)=1 THEN 'ALL REGIONS'
            WHEN region IS NULL THEN 'UNKNOWN REGION' ELSE region END AS region_label,
       CASE WHEN GROUPING(channel)=1 THEN 'ALL CHANNELS' ELSE channel END AS channel_label,
       SUM(amount) AS total
FROM ch058_events
GROUP BY ROLLUP(region,channel);
```

Do not use `COALESCE(region, 'ALL REGIONS')` to label subtotals: it incorrectly merges unknown source values with rollup placeholders.

**E. Portable alternative:** A union of region totals and the grand total uses standard `GROUP BY` and `UNION ALL` with explicit `level` labels. When unioning detail and summary levels, use consistent typed NULL placeholders, and do not sum across all levels.

## 4. DBRE/SRE and data engineering safeguards (5 minutes)

- Report **one grain at a time**. Summing every output row from `ROLLUP` double counts source measures; filter the desired grouping flags before reconciling.
- For a `CUBE` of N dimensions, the theoretical number of grouping sets is `2^N`; avoid unbounded cubes on high-cardinality dimensions or production clusters.
- Join fan-out inflates all grouping levels. Verify uniqueness and preaggregate one-to-many sources before reporting.
- `COUNT(*)` counts records, while `COUNT(amount)` excludes NULL amounts. State the business rule for missing amounts.
- Use exact `NUMERIC` amounts for monetary totals. Define timezone, refresh window, late arrivals, and dimensions in operational KPI contracts.
- Prefer read-only production reporting, query timeouts, resource budgets, and EXPLAIN review; **this lab must run only on a disposable PostgreSQL 18 database**.

## 5. Hands-on lab (20 minutes)

**Preflight:** Verify independently that the endpoint is isolated/disposable PostgreSQL 18 and the database is named `sql_tutorials`. The SQL guard checks version and database name, **not actual isolation**. From the repository root:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/058-rollup-cube-grouping-sets.sql
```

The [rollback-only PostgreSQL 18 lab](../labs/058-rollup-cube-grouping-sets.sql) creates a temporary synthetic fixture inside a transaction, sets local timeouts, displays each grouping pattern, checks expected results using fail-closed assertions, and rolls back.

Practice:
1. Explain the difference between detail, subtotal, and grand-total rows using `GROUPING` flags.
2. Reconcile the source 6 events / 155.00 against **only** the grand-total row.
3. Compare 9 rows from `ROLLUP` with 11 from `CUBE`; identify the extra channel subtotals.
4. Modify a **disposable copy** to add a new channel; predict the number of CUBE grouping rows before running.
5. Write `GROUPING SETS ((channel),())` and compare web 75.00, store 80.00, total 155.00.
6. Explain why `GROUPING(region)=0` can coexist with `region IS NULL`.

**Expected:** source 6/155.00; ROLLUP 9 rows; CUBE 11 rows; region totals East 60.00, West 90.00, unknown 5.00; channel totals web 75.00, store 80.00; one grand total 155.00 in each result. The script's success NOTICE is only a source assertion until actually executed and retained in evidence.

## 6. Troubleshooting (5 minutes)

| Symptom | Cause | Safe resolution |
|---|---|---|
| Total appears too large | Summed detail and subtotal rows together | Filter `GROUPING` flags to one reporting level |
| NULL region labeled grand total | `COALESCE` applied to rollup placeholder | Use `GROUPING(region)` |
| Missing channel subtotals | Used `ROLLUP` rather than `CUBE` | Request explicit `GROUPING SETS` |
| Too many groups / slow query | High-cardinality CUBE or join fan-out | Reduce grouping sets; verify join cardinality |
| Wrong number of rows | Confused source row count with distinct dimension combinations | Count distinct combinations and grouping levels |
| SQL dialect error | Engine lacks feature or differs in syntax | Use documented dialect equivalent or `UNION ALL` |
| Guard fails | Wrong version/database | Stop; inspect isolated lab endpoint |

## 7. Review questions with answers (5 minutes)

1. **Does ROLLUP(region,channel) include channel-only subtotals?** No, only detail, region totals, and grand total.
2. **What extra levels does CUBE add here?** Channel-only subtotals.
3. **Why is `GROUPING(region)` needed?** It separates a rolled-up NULL placeholder from a real NULL region.
4. **Why must we not sum all ROLLUP output totals?** The same source amount appears at multiple grouping levels.
5. **How can we limit work to region totals and a grand total?** `GROUPING SETS ((region),())`.
6. **Is CUBE universally portable?** No; verify the target SQL dialect or use a `UNION ALL` fallback.

**Next:** [059 — Pivoting and unpivoting — portable and vendor features (planned)](../MASTER-TOC.md).

## References

- [PostgreSQL 18 — SELECT, GROUP BY, grouping sets](https://www.postgresql.org/docs/18/sql-select.html)
- [PostgreSQL 18 — GROUPING function](https://www.postgresql.org/docs/18/functions-aggregate.html)
- [PostgreSQL 18 — Table expressions and grouping sets](https://www.postgresql.org/docs/18/queries-table-expressions.html)
