# 076 — FIRST_VALUE, LAST_VALUE, and Window Frames

**Part 08 — Window Functions & Advanced Analytics** · **60 minutes** · **Audience:** SQL beginners, data engineers, analysts, DBRE/SRE.

**Prerequisites:** [071 — Window-function anatomy](071-window-function-anatomy-over-partition-by-order-by.md), [075 — Rolling averages](075-rolling-averages-and-moving-windows.md). **Next:** [077 — NTILE, percentiles, and distribution analysis](../MASTER-TOC.md#part-08--window-functions--advanced-analytics).

**Safety:** All data below are fictional. Execute the [076 PostgreSQL 18 read-only lab](../labs/076-first-last-value-window-frames.sql) only on an independently verified disposable PostgreSQL 18 endpoint with nonproduction credentials. Database-name and version checks alone cannot establish isolation.

## 1. Learning objectives and timing (5 minutes)

After this chapter you can explain the difference between the first row, the last row *so far*, and the final row of a partition; specify explicit frames; handle ties and NULLs; and safely use first/last event comparisons for ingestion or incident telemetry.

| Activity | Minutes |
|---|---:|
| Objectives, prerequisites and safety | 5 |
| Window frames and portability | 10 |
| Worked examples and expected output | 15 |
| Isolated read-only SQL lab | 20 |
| Troubleshooting and validation | 5 |
| Review questions and answers | 5 |

## 2. Concepts: what is the frame? (10 minutes)

A **partition** groups rows for a window calculation without collapsing them. An **order** arranges rows inside the partition. A **frame** selects the subset of ordered rows visible to a frame-sensitive function.

`FIRST_VALUE(expression)` returns the expression from the first row in the current frame. `LAST_VALUE(expression)` returns it from the last row **in the current frame**, not automatically the last row in the entire partition.

**Broadly portable SQL pattern:**

```sql
LAST_VALUE(event_id) OVER (
  PARTITION BY service
  ORDER BY event_time, event_id
  ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
) AS final_event_id
```

Use `ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING` when the business question is *which row is last across the whole service?* For a running view use `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`.

In PostgreSQL 18, with `ORDER BY` but no explicit frame, the default is `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` (including peers tied on the ordering expressions). Therefore `LAST_VALUE` with the default frame can return the last peer of the current row, not the final event. Add a unique tie-breaker, such as `event_id`, and write the frame explicitly. SQL engines may differ in defaults, frame support and NULL-handling extensions; verify each target dialect. PostgreSQL 18 implements the standard RESPECT NULLS behavior for these functions and does not implement `IGNORE NULLS` for them. **A NULL final value remains NULL**; it does not mean the last non-NULL measurement.

## 3. Worked walkthrough (15 minutes)

**Grain:** one event per `(service,event_id)`. Timestamp ties are intentional; `event_id` is unique and resolves order.

| service | event_id | time | latency_ms |
|---|---:|---|---:|
| api | 1 | 09:00 | 100 |
| api | 2 | 09:05 | 200 |
| api | 3 | 09:10 | 300 |
| api | 4 | 09:10 | 400 |
| api | 5 | 09:20 | NULL |
| file | 6 | 09:00 | 50 |
| file | 7 | 09:15 | 70 |
| file | 8 | 09:30 | 90 |

**PostgreSQL 18 inline dataset with broadly portable window clauses:**

```sql
WITH events(service,event_id,event_time,latency_ms) AS (
 VALUES
 ('api',1,TIMESTAMP '2026-01-01 09:00',100),
 ('api',2,TIMESTAMP '2026-01-01 09:05',200),
 ('api',3,TIMESTAMP '2026-01-01 09:10',300),
 ('api',4,TIMESTAMP '2026-01-01 09:10',400),
 ('api',5,TIMESTAMP '2026-01-01 09:20',NULL::integer),
 ('file',6,TIMESTAMP '2026-01-01 09:00',50),
 ('file',7,TIMESTAMP '2026-01-01 09:15',70),
 ('file',8,TIMESTAMP '2026-01-01 09:30',90)
)
SELECT service,event_id,latency_ms,
 FIRST_VALUE(event_id) OVER (
  PARTITION BY service ORDER BY event_time,event_id
  ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
 ) AS first_id,
 LAST_VALUE(event_id) OVER (
  PARTITION BY service ORDER BY event_time,event_id
  ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
 ) AS last_so_far_id,
 LAST_VALUE(event_id) OVER (
  PARTITION BY service ORDER BY event_time,event_id
  ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
 ) AS final_id
FROM events ORDER BY service,event_id;
```

**Expected results (manually reasoned; not runtime-tested):**

| service | event_id | first_id | last_so_far_id | final_id |
|---|---:|---:|---:|---:|
| api | 1 | 1 | 1 | 5 |
| api | 2 | 1 | 2 | 5 |
| api | 3 | 1 | 3 | 5 |
| api | 4 | 1 | 4 | 5 |
| api | 5 | 1 | 5 | 5 |
| file | 6 | 6 | 6 | 8 |
| file | 7 | 6 | 7 | 8 |
| file | 8 | 6 | 8 | 8 |

The lab also calculates first and final latency. For `api`, the first is 100 and the final is **NULL** (ID 5 has no latency). For `file`, they are 50 and 90. This is valuable for DBRE/SRE change analysis: do not silently convert missing end-of-window telemetry to zero or to the previous value.

**Contrast:** Replace the full frame of `LAST_VALUE(event_id)` with `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`; the result becomes each current `event_id` (the last observed event *so far*). If you omit the frame entirely, tied timestamps may make the default `RANGE` frame return a peer row; do not rely on that for deterministic last-event analysis.

## 4. Hands-on lab (20 minutes)

1. Verify the connection out-of-band: disposable instance, PostgreSQL **18.x**, database `sql_tutorials`, least-privilege account, no production access. Do not copy real event records.
2. Run `psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/076-first-last-value-window-frames.sql` against the verified isolated endpoint. The file contains `BEGIN READ ONLY`, transaction-local timeouts, version/database checks, inline synthetic `VALUES`, exact two-way `EXCEPT ALL` comparisons, fail-closed assertions, and `ROLLBACK`.
3. Confirm eight result rows, API first/final IDs 1/5, FILE 6/8, API final latency NULL and FILE final latency 90. Acceptance flags must all be true and `fail_closed_acceptance` must be 1.
4. Experiment *only in the disposable lab*: change the running frame to the full frame and predict which rows change. Then restore the original query and repeat the checks.
5. Optional: compare `ORDER BY event_time` without `event_id` against deterministic ordering. Explain why the 09:10 API peer order is not guaranteed.

**Expected results are static predictions.** A successful lab run requires a real PostgreSQL 18 execution log and exit status; merely reading the assertions is not evidence of execution.

## 5. Troubleshooting, safety and acceptance (5 minutes)

| Symptom | Likely cause | Safe response |
|---|---|---|
| `LAST_VALUE` equals current event | Running/default frame, not full partition | Explicitly add `UNBOUNDED FOLLOWING` |
| Different results for tied timestamps | Nonunique `ORDER BY` | Add stable unique event ID |
| Final latency unexpectedly NULL | Final event has NULL metric | Preserve NULL; separately define any last-non-NULL business rule |
| Version/database guard fails | Wrong endpoint or database | Stop; verify isolated connection; never bypass guard |
| Timeout | Environment/load or accidental broad query | Stop and inspect lab endpoint; do not raise limits in production |
| Assertion fails | SQL or expected-result mismatch | Keep evidence, debug in disposable instance, do not mark validated |

The inline data and read-only transaction avoid persistent objects. Read-only SQL can still consume CPU/memory or hold snapshots, so use a dedicated disposable database and bounded execution. The file uses `psql` meta-command `\\set`, which is a **client command**, not portable SQL. The `::integer` cast and transaction-local `SET LOCAL` are PostgreSQL-specific.

## 6. Review questions with answers (5 minutes)

1. **Why can `LAST_VALUE` return the current row?** Its frame may end at the current row (or last peer), rather than the partition end.
2. **What frame finds the final event across a partition?** `ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING` with a deterministic order.
3. **Why add `event_id` to `ORDER BY event_time`?** It breaks timestamp ties reproducibly.
4. **Does `LAST_VALUE(latency_ms)` skip NULL in PostgreSQL 18?** No; a NULL final row returns NULL.
5. **What is the data-engineering risk of treating final NULL as zero?** It turns missing telemetry into an invented measurement and distorts change or incident reports.
6. **Is publishing this file proof of runtime validation?** No. Execute it on isolated PostgreSQL 18 and retain version, commands, outputs, exit code and acceptance evidence.

## References and next step

- [PostgreSQL 18 — Window Functions](https://www.postgresql.org/docs/18/functions-window.html)
- [PostgreSQL 18 — Window Function Calls](https://www.postgresql.org/docs/18/sql-expressions.html#SYNTAX-WINDOW-FUNCTIONS)
- [PostgreSQL 18 — SELECT](https://www.postgresql.org/docs/18/sql-select.html)
- [Chapter 077 in the Master TOC](../MASTER-TOC.md#part-08--window-functions--advanced-analytics)

**Publication state:** authored; runtime acceptance pending until actual isolated PostgreSQL 18 execution with reproducible evidence.
