# 074 — Running Totals and Cumulative Measures

**Part 08 — Window Functions & Advanced Analytics** · **60 minutes** · **Audience:** SQL beginners, data engineers, analysts, DBRE/SRE.

**Prerequisites:** [071 — Window-function anatomy](071-window-function-anatomy-over-partition-by-order-by.md), [073 — LAG and LEAD](073-lag-and-lead-for-change-analysis.md). **Next:** [075 — Rolling averages and moving windows](../MASTER-TOC.md#part-08--window-functions--advanced-analytics).

**Safety:** All records are fictional and defined inline. The [PostgreSQL 18 read-only lab](../labs/074-running-totals-cumulative-measures.sql) requires an independently verified disposable instance and least-privilege account. Its name/version checks are defense in depth, not proof of isolation. No persistent objects or production credentials are used.

## 1. Outcomes and schedule (5 minutes)

By the end you can calculate a running sum, cumulative count, cumulative share and service-specific cumulative measure; explain window frames and ties; reconcile the final cumulative value to the group total; and identify data-quality traps.

| Activity | Minutes |
|---|---:|
| Objectives and safety | 5 |
| Concepts and SQL syntax | 10 |
| Guided walkthrough | 15 |
| Hands-on lab | 20 |
| Troubleshooting and validation | 5 |
| Review with answers | 5 |

## 2. Concepts: what is cumulative? (10 minutes)

A **running total** sums values from the beginning of a chosen ordered sequence through the current row. Unlike `GROUP BY`, a window aggregate preserves one output row per input row. `PARTITION BY service` resets the running sum for each service. `ORDER BY event_time, event_id` defines a stable sequence.

**Portable SQL pattern:**

```sql
SUM(records) OVER (
  PARTITION BY service
  ORDER BY event_time, event_id
  ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
) AS running_records
```

Specify `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` explicitly. In PostgreSQL, the default ordered aggregate frame is `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`, which includes **peers** with equal window ordering values; that can produce a jump across tied timestamps. `ROWS` advances by physical row position within the deterministic window ordering. `RANGE` is not inherently wrong: choose it when tied ordering values should share a cumulative value.

`SUM` ignores NULL measurements. That does **not** establish that missing records are zero. If all rows in a frame are NULL, `SUM` returns NULL; `COUNT(records)` counts only known measurements. For accurate operational reports, track missing observations separately and agree on how incomplete data affects KPIs.

The total for a partition can be computed using `SUM(records) OVER (PARTITION BY service)` with **no window ORDER BY**. A cumulative percentage is `100.0 * running_records / NULLIF(service_total, 0)`; protect division by zero and consider whether negative corrections make a percentage meaningful.

## 3. Guided example (15 minutes)

Synthetic ingestion batches have the grain **one row per batch**. The two API rows at 09:05 intentionally tie on timestamp; `batch_id` breaks the tie.

| service | batch_id | time | records |
|---|---:|---|---:|
| api | 1 | 09:00 | 20 |
| api | 2 | 09:05 | 30 |
| api | 3 | 09:05 | 10 |
| api | 4 | 09:10 | 40 |
| file | 5 | 09:00 | 15 |
| file | 6 | 09:05 | NULL |
| file | 7 | 09:10 | 25 |

```sql
WITH batches(service,batch_id,event_time,records) AS (
 VALUES
 ('api',1,TIMESTAMP '2026-01-01 09:00',20),
 ('api',2,TIMESTAMP '2026-01-01 09:05',30),
 ('api',3,TIMESTAMP '2026-01-01 09:05',10),
 ('api',4,TIMESTAMP '2026-01-01 09:10',40),
 ('file',5,TIMESTAMP '2026-01-01 09:00',15),
 ('file',6,TIMESTAMP '2026-01-01 09:05',NULL::integer),
 ('file',7,TIMESTAMP '2026-01-01 09:10',25)
), calculated AS (
 SELECT service,batch_id,event_time,records,
        SUM(records) OVER (
          PARTITION BY service ORDER BY event_time,batch_id
          ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS running_records,
        COUNT(records) OVER (
          PARTITION BY service ORDER BY event_time,batch_id
          ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS known_measurements,
        SUM(records) OVER (PARTITION BY service) AS service_total
 FROM batches
)
SELECT service,batch_id,records,running_records,known_measurements,
       service_total,
       ROUND(100.0 * running_records / NULLIF(service_total,0),2) AS cumulative_pct
FROM calculated ORDER BY service,event_time,batch_id;
```

**Expected results (manually reasoned; not runtime-validated):**

| service | ID | records | running | known | total | cumulative % |
|---|---:|---:|---:|---:|---:|---:|
| api | 1 | 20 | 20 | 1 | 100 | 20.00 |
| api | 2 | 30 | 50 | 2 | 100 | 50.00 |
| api | 3 | 10 | 60 | 3 | 100 | 60.00 |
| api | 4 | 40 | 100 | 4 | 100 | 100.00 |
| file | 5 | 15 | 15 | 1 | 40 | 37.50 |
| file | 6 | NULL | 15 | 1 | 40 | 37.50 |
| file | 7 | 25 | 40 | 2 | 40 | 100.00 |

**Contrast:** With `ORDER BY event_time` and PostgreSQL's default `RANGE` frame, both API 09:05 rows can show 60 at once, rather than 50 then 60. A deterministic `ROWS` ordering avoids this ambiguity. A final `ORDER BY` controls display only; it does not change window calculations.

## 4. Hands-on lab (20 minutes)

Open [074-running-totals-cumulative-measures.sql](../labs/074-running-totals-cumulative-measures.sql). Verify the endpoint, account, and database are disposable *before* execution. From `sql-tutorials/labs/`:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f 074-running-totals-cumulative-measures.sql
```

1. Predict the running API totals (20, 50, 60, 100) before executing.
2. Execute the lab's detailed query and compare all seven rows to the expected table.
3. Verify FILE's missing batch does not increase `known_measurements`; distinguish missing from zero.
4. Verify API total 100 and FILE total 40; check that each final running total equals its partition total.
5. Execute the fail-closed acceptance query, which compares the complete result set in both directions using `EXCEPT ALL`. Under `ON_ERROR_STOP=1`, a failed assertion must stop the run.
6. **Stretch:** Remove `batch_id` from the window ordering and omit the `ROWS` frame. Predict the 09:05 peer behavior, then restore the deterministic version.
7. **Stretch:** Add `COUNT(*) OVER (PARTITION BY service ORDER BY event_time,batch_id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)` and compare rows observed versus non-NULL measurements.

Expected: seven rows, API total 100, FILE total 40, one missing measurement, cumulative percentages ending at 100% for both services. The script finishes with `ROLLBACK`.

## 5. Troubleshooting and DBRE/SRE controls (5 minutes)

| Symptom | Explanation | Safe action |
|---|---|---|
| Running total jumps on tied timestamps | Default RANGE frame includes peers | Explicitly choose ROWS and a stable unique tie-breaker |
| Total resets unexpectedly | Incorrect PARTITION BY key | Confirm the intended service/customer/business grain |
| Cumulative total appears too high | Join fan-out or duplicated events | Reconcile unique event keys before computing the window |
| NULL batch seems silently counted as zero | SUM skips NULL | Report missing measurements with COUNT(*) - COUNT(records) |
| Percentage division fails or is undefined | Zero/NULL denominator | Use NULLIF and an explicit incomplete-data policy |
| Report differs after late-arriving records | Event-time ordering changed | Recompute affected partitions; document watermarks and corrections |
| Large partitions spill to disk | Window sorting and memory pressure | Inspect approved staging EXPLAIN and temp metrics, not unapproved production benchmarks |

For ingestion dashboards, cumulative counts of *events* and cumulative *record quantities* answer different questions. If events can be retried or corrected, deduplicate by an approved business key before summing. Never infer production throughput from this seven-row synthetic exercise.

## 6. Review questions and answers (5 minutes)

**Q1. Why use a window SUM instead of GROUP BY?** It preserves each batch row while attaching a cumulative value.

**Q2. What does PARTITION BY do?** Restarts the accumulation for each service.

**Q3. Why explicitly use ROWS?** It defines row-by-row accumulation and avoids the default RANGE peer grouping.

**Q4. Why include batch_id after event_time?** It creates a deterministic order when timestamps tie.

**Q5. Why does FILE batch 6 leave the running total at 15?** Its measurement is NULL and SUM ignores NULL, although the missing measurement must still be reported.

**Q6. How do you verify a running sum?** Compare the final cumulative value per partition with an independently computed partition aggregate, and reconcile full expected rows.

**Q7. What can invalidate a cumulative report after publication?** Late arrivals, duplicate events, corrections, changing partitions, or incomplete source data.

## 7. References and status

- [PostgreSQL 18 — Window functions](https://www.postgresql.org/docs/18/functions-window.html)
- [PostgreSQL 18 — Window tutorial](https://www.postgresql.org/docs/18/tutorial-window.html)
- [PostgreSQL 18 — Window frames](https://www.postgresql.org/docs/18/sql-expressions.html#SYNTAX-WINDOW-FUNCTIONS)
- [Master TOC](../MASTER-TOC.md) · [Status tracker](../STATUS-TRACKER.md)

**Status:** Authored for publication; manually reasoned expected results and targeted static safety inspection. Independent editorial review and comprehensive automated link/syntax QA pending. **No isolated PostgreSQL 18 runtime execution or retained evidence; runtime validation pending.**
