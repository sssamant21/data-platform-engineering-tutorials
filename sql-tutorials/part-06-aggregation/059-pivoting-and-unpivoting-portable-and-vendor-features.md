# 059 — Pivoting and Unpivoting: Portable and Vendor Features

**Part 06 — Aggregation, Grouping & Reporting** · **60 minutes** · **Audience:** beginner SQL, data engineers, DBRE/SRE · **Prerequisites:** [051 aggregates](051-count-sum-avg-min-and-max.md), [052 GROUP BY](052-group-by-and-aggregation-grain.md), [054 conditional aggregation](054-conditional-aggregation-with-case-and-filter.md).

> **Safety:** All data here are synthetic. Run the companion SQL only on an independently verified disposable PostgreSQL 18 instance named `sql_tutorials`. Never run lab DDL against production or with production credentials. The SQL version/database guard cannot prove isolation.

## 1. Objectives and agenda (5 minutes)

By the end you can: (1) distinguish long (tidy) versus wide report shapes; (2) pivot with portable conditional aggregation; (3) unpivot with `UNION ALL`; (4) explain `NULL` versus zero and report grain; (5) recognize vendor-specific `PIVOT`/`UNPIVOT` implementations; (6) reconcile row counts and monetary totals. Agenda: objectives 5, concepts 10, walkthrough 15, lab 20, troubleshooting 5, review 5 minutes.

**Scenario:** A synthetic payment-event feed contains `region`, `channel`, and `amount`. The analytics team needs one row per region with columns `web_amount` and `store_amount`; DBREs must verify that reshaping does not lose or multiply values.

## 2. Concepts and portability (10 minutes)

A **long** table has one row per region/channel event (event grain). A **wide** pivot report has one row per region and a separate column for each selected channel (region grain). Pivoting aggregates; it is **not** a simple transpose when several source rows share a region/channel. Before pivoting, define the grouping key, measure, category values, and whether absent categories mean zero or unknown.

**Portable SQL approach:** `SUM(CASE WHEN channel = 'web' THEN amount ELSE 0 END)` and `SUM(CASE WHEN channel = 'store' THEN amount ELSE 0 END)` with `GROUP BY region`. `CASE` + `SUM` is broadly portable, but casting, identifier quoting, and exact numeric types vary. The `ELSE 0` rule means **no matching events contributes zero**; a genuine unknown amount may require a separate missing-data count.

**PostgreSQL:** `SUM(amount) FILTER (WHERE channel='web')` is concise but returns `NULL` if there are no matching non-NULL values. Use `COALESCE(...,0)` only if that is the agreed business rule. PostgreSQL has `tablefunc.crosstab` via an extension, but it requires permissions, explicit output columns and careful ordering; this chapter deliberately does not install extensions.

**Vendor differences:** SQL Server and Oracle offer dialect-specific `PIVOT` and `UNPIVOT` operators with differing syntax and NULL behavior. Snowflake also supports `PIVOT`/`UNPIVOT`, with its own rules; BigQuery supports `PIVOT`/`UNPIVOT` in GoogleSQL. Do not paste a vendor's syntax into PostgreSQL without adaptation. Dynamic pivot columns generally require generated SQL and a fixed, reviewed category allowlist.

## 3. Worked examples (15 minutes)

Synthetic source events:

| id | region | channel | amount |
|---:|---|---|---:|
| 1 | East | web | 10.00 |
| 2 | East | web | 20.00 |
| 3 | East | store | 30.00 |
| 4 | West | web | 40.00 |
| 5 | West | store | 50.00 |
| 6 | West | store | 5.00 |
| 7 | North | web | 15.00 |
| 8 | North | store | 10.00 |

**A. Source-level baseline** (the lab creates `ch059_events`):

```sql
SELECT COUNT(*) AS event_count, SUM(amount) AS source_total
FROM ch059_events;
-- 8 events, 180.00
```

**B. Portable static pivot:**

```sql
SELECT region,
       SUM(CASE WHEN channel='web' THEN amount ELSE 0 END) AS web_amount,
       SUM(CASE WHEN channel='store' THEN amount ELSE 0 END) AS store_amount,
       SUM(amount) AS region_total
FROM ch059_events
GROUP BY region
ORDER BY region;
```

| region | web_amount | store_amount | region_total |
|---|---:|---:|---:|
| East | 30.00 | 30.00 | 60.00 |
| North | 15.00 | 10.00 | 25.00 |
| West | 40.00 | 55.00 | 95.00 |

Each row represents **one region**, not one payment. Column sums: web 85.00, store 95.00, grand total 180.00. For a category not present in a region, the `ELSE 0` returns zero. Adding an unlisted channel such as `mobile` would make `region_total` exceed `web_amount + store_amount`—a valuable fail-closed reconciliation signal.

**C. PostgreSQL FILTER alternative:**

```sql
SELECT region,
       COALESCE(SUM(amount) FILTER (WHERE channel='web'),0) AS web_amount,
       COALESCE(SUM(amount) FILTER (WHERE channel='store'),0) AS store_amount
FROM ch059_events
GROUP BY region
ORDER BY region;
```

This is equivalent **for this non-NULL fixture**. With NULL amounts, `SUM` ignores them; decide whether that is acceptable rather than silently interpreting unknown as zero.

**D. Portable unpivot with UNION ALL:** Start with the wide report, then turn each measure column into a row. `UNION ALL` retains rows even when amounts coincide; `UNION` might deduplicate and is inappropriate for preserving event-like records.

```sql
WITH wide AS (
 SELECT region,
        SUM(CASE WHEN channel='web' THEN amount ELSE 0 END) AS web_amount,
        SUM(CASE WHEN channel='store' THEN amount ELSE 0 END) AS store_amount
 FROM ch059_events GROUP BY region
)
SELECT region, 'web' AS channel, web_amount AS amount FROM wide
UNION ALL
SELECT region, 'store' AS channel, store_amount AS amount FROM wide
ORDER BY region, channel;
```

Expected **6 rows**, one per region/channel, with total 180.00. **This does not recover the original eight event rows:** aggregation has discarded event IDs and per-event granularity. A pivot/unpivot round trip can preserve **aggregated measures**, not source records.

**E. Zero versus NULL:** If a wide row has `NULL` in `store_amount`, `UNION ALL` preserves the row with NULL, while some vendor `UNPIVOT` implementations omit NULL cells by default. Explicitly document whether missing categories, missing amounts, and real zeros have different meanings.

## 4. Data engineering and DBRE/SRE safeguards

- Agree on the source grain and uniqueness keys; join fan-out before pivoting multiplies measures.
- Maintain a controlled category list; detect new/unknown channel values instead of silently dropping them.
- Reconcile `SUM(source.amount)` to `SUM(pivoted columns)` and to `SUM(unpivoted.amount)`; check row grain separately.
- Use exact `NUMERIC` for financial amounts; do not round each source event before aggregation unless the contract requires it.
- Large pivots can consume memory and produce wide result sets. Bound date ranges and report cardinality, inspect `EXPLAIN` in staging, and use read-only permissions for production reporting.
- Never interpret a successful SQL assertion as a substitute for independent editorial review or an actual PostgreSQL 18 execution log.

## 5. Hands-on isolated PostgreSQL 18 lab (20 minutes)

**Preflight:** Independently confirm a disposable PostgreSQL 18 endpoint, database `sql_tutorials`, and non-production credentials. From the repository root:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/059-pivoting-unpivoting-portable-vendor.sql
```

The [companion rollback-only SQL lab](../labs/059-pivoting-unpivoting-portable-vendor.sql) creates a temporary fixture, displays the portable pivot and unpivot, checks both shapes and totals, and rolls back. Transaction-local statement/lock/idle timeouts are set.

Practice: (1) predict the three pivot rows before running; (2) reconcile 85.00 web + 95.00 store = 180.00; (3) explain why the unpivot returns 6, not 8, rows; (4) add an isolated ninth `mobile` event in a **disposable copy** and observe the category-reconciliation assertion fail; (5) extend the pivot with a mobile column and update expected totals; (6) explain the difference between absent and NULL category measures.

**Expected baseline:** source 8 events / 180.00; pivot 3 region rows / 180.00; unpivot 6 rows / 180.00; East 60.00, North 25.00, West 95.00. The script's NOTICE is a runtime assertion only **if actually executed** and its exit code/output retained.

## 6. Troubleshooting (5 minutes)

| Symptom | Likely cause | Safe check/fix |
|---|---|---|
| Pivot total smaller than source | New channel omitted from static columns | Compare source channels to allowlist; add approved column |
| Pivot total larger than source | Join fan-out or duplicated input | Validate keys and preaggregate at the correct grain |
| Unpivot returns fewer rows than expected | Confused aggregate grain with event grain | Compare region/channel combinations, not event IDs |
| Missing measure appears as zero | `ELSE 0` or `COALESCE` | Define missing-data policy and audit NULLs |
| SQL syntax error on `PIVOT` | Vendor-specific syntax | Use portable CASE/UNION ALL pattern |
| Guard aborts | Wrong database/version | Stop; inspect connection; do not bypass guard |

## 7. Review questions with answers (5 minutes)

1. **What changes during a pivot?** Rows of category values become measure columns, usually after aggregation.
2. **Is a pivot reversible to original event rows?** Not after aggregation removes event-level detail.
3. **Why use `UNION ALL` for portable unpivot?** It preserves all selected column rows without deduplication.
4. **How does `FILTER` differ from `CASE ELSE 0`?** FILTER may return NULL for an empty matching set; CASE contributes zeros.
5. **What detects an unexpected channel?** Compare source total with the sum of all explicitly pivoted category columns and inspect distinct categories.
6. **Should dynamic SQL accept arbitrary category strings as identifiers?** No; use allowlists, safe identifier quoting, and reviewed queries.

**Next:** [060 — Lab 06: build a monthly KPI report (planned)](../MASTER-TOC.md).

## References

- [PostgreSQL 18 — Aggregate Functions](https://www.postgresql.org/docs/18/functions-aggregate.html)
- [PostgreSQL 18 — Conditional Expressions (CASE)](https://www.postgresql.org/docs/18/functions-conditional.html)
- [PostgreSQL 18 — SELECT and UNION](https://www.postgresql.org/docs/18/sql-select.html)
- [PostgreSQL 18 — Tablefunc](https://www.postgresql.org/docs/18/tablefunc.html) (optional extension; not used in lab)
- [Microsoft SQL Server — FROM: PIVOT and UNPIVOT](https://learn.microsoft.com/en-us/sql/t-sql/queries/from-using-pivot-and-unpivot)
- [Snowflake — PIVOT](https://docs.snowflake.com/en/sql-reference/constructs/pivot)
- [GoogleSQL — PIVOT operator](https://cloud.google.com/bigquery/docs/reference/standard-sql/query-syntax#pivot_operator)

**Validation state at authoring:** targeted static reasoning only. Independent editorial review, comprehensive automated syntax/link checks, and actual isolated PostgreSQL 18 runtime validation remain pending.
