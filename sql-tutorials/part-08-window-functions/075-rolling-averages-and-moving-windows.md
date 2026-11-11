# 075 — Rolling Averages and Moving Windows

**Part 08 — Window Functions & Advanced Analytics** · **60 minutes** · **Audience:** SQL beginners, data engineers, analysts, DBRE/SRE.

**Prerequisites:** [071 — Window-function anatomy](071-window-function-anatomy-over-partition-by-order-by.md), [074 — Running totals](074-running-totals-and-cumulative-measures.md). **Next:** [076 — FIRST_VALUE, LAST_VALUE, and window frames](../MASTER-TOC.md#part-08--window-functions--advanced-analytics).

**Safety:** Fictional inline telemetry only. The [PostgreSQL 18 lab](../labs/075-rolling-averages-moving-windows.sql) is read-only and requires a separately verified, disposable PostgreSQL 18 instance, a non-production connection and least-privilege credentials. Database-name/version guards are not proof of isolation.

## 1. Learning outcomes and schedule (5 minutes)

After this lesson, you can: calculate trailing three-row averages, distinguish ROWS from time-based RANGE, handle NULL and partial windows, explain stable ordering, and evaluate operational moving metrics without mistaking synthetic examples for production capacity evidence.

| Activity | Minutes |
|---|---:|
| Outcomes, prerequisites and safety | 5 |
| Concepts and portable SQL | 10 |
| Worked examples and expected output | 15 |
| Isolated read-only hands-on lab | 20 |
| Troubleshooting and acceptance | 5 |
| Review questions and answers | 5 |

## 2. Concepts (10 minutes)

A **moving average** summarizes a subset of observations around a row. A *trailing three-row window* contains the current observation and at most two preceding rows, reset per service:

```sql
AVG(latency_ms) OVER (
  PARTITION BY service
  ORDER BY sample_time, sample_id
  ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
) AS trailing_avg_ms
```

This is broadly portable SQL window syntax. `PARTITION BY` separates services; the unique `sample_id` tie-breaker makes the order deterministic. `ROWS` counts physical observations, **not minutes**. The first and second rows have partial windows; `AVG` excludes NULL values. If all values in a frame are NULL, AVG returns NULL. `COUNT(*)` counts observations, while `COUNT(latency_ms)` counts non-NULL measurements.

A three-row average is **not** necessarily a three-minute average. Irregular sampling, duplicate timestamps, gaps, or late arrivals change which observations enter the frame. A time-based `RANGE` frame can express an interval on PostgreSQL timestamps, but syntax/support differ by database. In PostgreSQL 18, `ORDER BY sample_time RANGE BETWEEN INTERVAL '10 minutes' PRECEDING AND CURRENT ROW` uses one timestamp ordering expression and includes all timestamp peers. It is **PostgreSQL-specific in this lesson**, not a promised cross-dialect equivalent.

Do not treat a NULL latency as zero. For a strict complete three-measurement average, return NULL unless `COUNT(latency_ms)` equals 3; this also prevents treating early partial windows as fully comparable.

## 3. Guided walkthrough (15 minutes)

**Grain:** one synthetic latency observation per `(service, sample_id)`. Two services deliberately have different numbers of rows; API contains a tied timestamp and a missing measurement.

| service | ID | time | latency_ms |
|---|---:|---|---:|
| api | 1 | 09:00 | 100 |
| api | 2 | 09:05 | 200 |
| api | 3 | 09:05 | 300 |
| api | 4 | 09:10 | NULL |
| api | 5 | 09:20 | 500 |
| file | 6 | 09:00 | 40 |
| file | 7 | 09:10 | 80 |
| file | 8 | 09:20 | 120 |

**Portable window calculation** (the inline timestamp literals and cast syntax here follow PostgreSQL 18):

```sql
WITH samples(service,sample_id,sample_time,latency_ms) AS (
 VALUES
 ('api',1,TIMESTAMP '2026-01-01 09:00',100),
 ('api',2,TIMESTAMP '2026-01-01 09:05',200),
 ('api',3,TIMESTAMP '2026-01-01 09:05',300),
 ('api',4,TIMESTAMP '2026-01-01 09:10',NULL::integer),
 ('api',5,TIMESTAMP '2026-01-01 09:20',500),
 ('file',6,TIMESTAMP '2026-01-01 09:00',40),
 ('file',7,TIMESTAMP '2026-01-01 09:10',80),
 ('file',8,TIMESTAMP '2026-01-01 09:20',120)
), moving AS (
 SELECT service,sample_id,sample_time,latency_ms,
   ROUND(AVG(latency_ms) OVER w,2) AS avg_3_rows,
   COUNT(*) OVER w AS window_rows,
   COUNT(latency_ms) OVER w AS measured_rows
 FROM samples
 WINDOW w AS (
   PARTITION BY service ORDER BY sample_time,sample_id
   ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
 )
)
SELECT service,sample_id,latency_ms,avg_3_rows,window_rows,measured_rows,
 CASE WHEN measured_rows=3 THEN avg_3_rows END AS complete_avg_3
FROM moving ORDER BY service,sample_time,sample_id;
```

**Expected output — manually derived, not PostgreSQL runtime-tested:**

| service | ID | latency | avg_3_rows | window_rows | measured_rows | complete_avg_3 |
|---|---:|---:|---:|---:|---:|---:|
| api | 1 | 100 | 100.00 | 1 | 1 | NULL |
| api | 2 | 200 | 150.00 | 2 | 2 | NULL |
| api | 3 | 300 | 200.00 | 3 | 3 | 200.00 |
| api | 4 | NULL | 250.00 | 3 | 2 | NULL |
| api | 5 | 500 | 400.00 | 3 | 2 | NULL |
| file | 6 | 40 | 40.00 | 1 | 1 | NULL |
| file | 7 | 80 | 60.00 | 2 | 2 | NULL |
| file | 8 | 120 | 80.00 | 3 | 3 | 80.00 |

API ID 4 averages 200 and 300 (NULL excluded). API ID 5 averages 300 and 500. This is not the same as filling missing values with zero. The only complete three-measurement windows are API ID 3 and FILE ID 8.

**PostgreSQL-specific time-window contrast:**

```sql
-- Substitute the same samples CTE above.
SELECT service,sample_id,
 ROUND(AVG(latency_ms) OVER (
   PARTITION BY service ORDER BY sample_time
   RANGE BETWEEN INTERVAL '10 minutes' PRECEDING AND CURRENT ROW
 ),2) AS trailing_10min_avg
FROM samples
ORDER BY service,sample_time,sample_id;
```

For API ID 3, the 10-minute window includes IDs 1, 2 and 3, averaging 200.00; for API ID 4, it includes IDs 1–4 and averages 200.00 (NULL ignored). For API ID 5, only ID 5 falls within 09:10–09:20 with a non-NULL value, averaging 500.00. **Time windows count timestamps, not a fixed number of rows.**

## 4. Hands-on lab (20 minutes)

Open [075-rolling-averages-moving-windows.sql](../labs/075-rolling-averages-moving-windows.sql). Verify the host, role, network endpoint and database independently before running. From `sql-tutorials/labs/`:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f 075-rolling-averages-moving-windows.sql
```

1. Predict API ID 3's trailing average before running (200.00).
2. Run the eight-row detailed output; verify the exact result table.
3. Compare `window_rows` to `measured_rows` for API IDs 4 and 5.
4. Check that the strict complete-window average appears only at IDs 3 and 8.
5. Run the lab's bidirectional `EXCEPT ALL` assertion. Any mismatch causes a fail-closed SQL error with `ON_ERROR_STOP`.
6. **Exercise:** Change `2 PRECEDING` to `1 PRECEDING` in a *copy* of the query; predict API ID 3 average 250.00 (IDs 2 and 3).
7. **Exercise:** Compare the PostgreSQL time-based window to the three-row window. Why is API ID 5's time-window result 500.00 rather than 400.00?
8. Confirm `ROLLBACK` and that no persistent objects were created.

## 5. Validation, troubleshooting and operational guardrails (5 minutes)

| Symptom | Likely cause | Safe response |
|---|---|---|
| Averages change between executions | Tied ordering keys or mutable event order | Add a unique stable tie-breaker; define late-arrival policy |
| Missing latency appears as zero | Incorrect COALESCE policy | Preserve NULL and report measured versus total rows |
| First rows look artificially low/high | Partial frames | Require a minimum number of valid measurements |
| Three-row result differs from last ten minutes | Irregular samples | Choose a row- or time-based definition explicitly |
| Unexpected spikes after joining dimensions | Join fan-out | Reconcile input grain before the window |
| Slow window calculation | Large partitions or sort pressure | Examine approved staging plans and temporary-file metrics; no production load testing |
| Lab guard fails | Wrong PostgreSQL version/database | Stop; independently verify disposable endpoint; never bypass checks to target production |

For DBRE/SRE alerting, define whether an SLO is based on per-request latency, per-batch average, a rolling percentile, or a weighted average. An average of averages is generally **not** the weighted mean when batch sizes differ. Window averages on eight synthetic rows do not certify alert thresholds or production performance.

## 6. Review questions and answers (5 minutes)

**Q1. What does `ROWS BETWEEN 2 PRECEDING AND CURRENT ROW` mean?** At most the current row and two earlier rows within the ordered partition.

**Q2. Does a three-row window mean three minutes?** No; row-count windows do not represent elapsed time.

**Q3. Why order by both timestamp and ID?** The ID breaks timestamp ties and ensures deterministic row membership.

**Q4. How does AVG handle NULL?** It excludes NULL; a frame with no non-NULL values returns NULL.

**Q5. Why track COUNT(*) and COUNT(latency_ms)?** They distinguish total observations from actual measured values.

**Q6. Which API row has a complete three-measurement window?** ID 3 only.

**Q7. What is the difference between ROWS and timestamp RANGE?** ROWS counts positions; a timestamp RANGE selects values in a time interval and includes peers.

**Q8. What must be verified before using this lab?** Independent disposable PostgreSQL 18 endpoint identity, least-privilege account, synthetic inputs and safe execution scope.

## 7. References and validation status

- [PostgreSQL 18 — Window functions](https://www.postgresql.org/docs/18/functions-window.html)
- [PostgreSQL 18 — Window-function tutorial](https://www.postgresql.org/docs/18/tutorial-window.html)
- [PostgreSQL 18 — Window frame syntax](https://www.postgresql.org/docs/18/sql-expressions.html#SYNTAX-WINDOW-FUNCTIONS)
- [Master TOC](../MASTER-TOC.md) · [Status tracker](../STATUS-TRACKER.md)

**Validation status:** Authored; targeted static reasoning of eight expected rows and safety checks. Independent editorial review, comprehensive automated SQL syntax/link QA, and actual isolated PostgreSQL 18 execution with reproducible evidence **pending**.
