# 077 — NTILE, Percentiles, and Distribution Analysis

**Part 08 — Window Functions & Advanced Analytics** · **60 minutes** · **Audience:** SQL beginners, data engineers, analysts, DBRE/SRE.

**Prerequisites:** [071 — Window-function anatomy](071-window-function-anatomy-over-partition-by-order-by.md), [072 — Ranking functions](072-row-number-rank-and-dense-rank.md). **Next:** [078 — Gaps-and-islands patterns](../MASTER-TOC.md#part-08--window-functions--advanced-analytics).

**Safety:** Use only synthetic observations and a separately verified disposable PostgreSQL 18 instance. [Run the read-only lab](../labs/077-ntile-percentiles-distribution.sql) with nonproduction credentials. Database/version assertions cannot prove an endpoint is isolated.

## 1. Outcomes and schedule (5 minutes)

After this lesson you can (1) distinguish equal-row buckets from value thresholds, (2) calculate exact and continuous percentiles, (3) interpret percentile ranks and ties, (4) avoid misleading latency SLO claims, and (5) check SQL results safely.

| Activity | Minutes |
|---|---:|
| Outcomes, setup, safety | 5 |
| Concepts, dialects, semantics | 10 |
| Worked examples | 15 |
| Hands-on SQL lab | 20 |
| Validation and troubleshooting | 5 |
| Review with answers | 5 |

## 2. Concepts and portability (10 minutes)

**Distribution** describes how observations are spread. An average can hide tail latency: five requests at 10 ms and one at 1,000 ms may produce an acceptable-looking mean while one request is very slow.

- `NTILE(n) OVER (PARTITION BY service ORDER BY latency_ms, event_id)` divides *rows* into up to `n` ordered groups as evenly as possible. Earlier buckets get the extra rows. It does **not** divide the numerical latency range into equal-width intervals. A unique tie-breaker makes assignments reproducible; equal latencies can still land in different buckets.
- `PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY latency_ms)` interpolates between ordered values; `PERCENTILE_DISC(0.5)` selects an observed value. In PostgreSQL these are ordered-set aggregates, not `OVER` window functions. Compute per-service percentiles using `GROUP BY` and join them to row-level results when needed.
- `PERCENT_RANK()` is `(RANK()-1)/(N-1)` for partitions with more than one row (0 for one row). `CUME_DIST()` is the fraction of rows at or below the current ordered value. Both respect ties; they answer different questions from a percentile threshold.
- `NULL` latency is unknown, **not zero**. Ordered-set percentile aggregates ignore NULL inputs; explicitly filter or report missing observations. Define the time interval, sampling grain, and population before interpreting p95/p99. Small samples make extreme percentiles unstable.

**Portability:** `NTILE`, `PERCENT_RANK`, and `CUME_DIST` are widely supported SQL window patterns; ordered-set percentile syntax and support differ across PostgreSQL, SQL Server, Oracle, Snowflake, BigQuery, MySQL, and SQLite. PostgreSQL 18 supports `PERCENTILE_CONT` and `PERCENTILE_DISC` as ordered-set aggregates; PostgreSQL `percentile_cont` returns a `double precision` result for numeric input. BigQuery commonly uses analytic `PERCENTILE_CONT` and `APPROX_QUANTILES`; do not assume identical syntax or approximation behavior across systems.

## 3. Walkthrough with synthetic telemetry (15 minutes)

Each row is one synthetic completed request. The **grain** is `(service,event_id)`. The API service has five observations: 10, 20, 20, 40, 100 ms; FILE has four: 5, 15, 25, 35 ms. An extra API row with NULL latency is deliberately excluded from numerical calculations but included in missing-data reporting.

```sql
WITH samples(service,event_id,latency_ms) AS (
 VALUES ('api',1,10),('api',2,20),('api',3,20),
        ('api',4,40),('api',5,100),('api',6,NULL::integer),
        ('file',7,5),('file',8,15),('file',9,25),('file',10,35)
), measured AS (
 SELECT * FROM samples WHERE latency_ms IS NOT NULL
)
SELECT service,event_id,latency_ms,
       NTILE(4) OVER (PARTITION BY service ORDER BY latency_ms,event_id) AS quartile
FROM measured
ORDER BY service,latency_ms,event_id;
```

**Expected quartiles (reasoned, not runtime-executed):**

| service | event_id | latency_ms | quartile |
|---|---:|---:|---:|
| api | 1 | 10 | 1 |
| api | 2 | 20 | 1 |
| api | 3 | 20 | 2 |
| api | 4 | 40 | 3 |
| api | 5 | 100 | 4 |
| file | 7 | 5 | 1 |
| file | 8 | 15 | 2 |
| file | 9 | 25 | 3 |
| file | 10 | 35 | 4 |

The API has five measured rows across four buckets, so bucket 1 gets two rows. Identical 20 ms values fall into different buckets because the ordering also uses event ID.

```sql
WITH samples(service,latency_ms) AS (
 VALUES ('api',10),('api',20),('api',20),('api',40),('api',100),
        ('file',5),('file',15),('file',25),('file',35)
)
SELECT service,COUNT(*) AS n,
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY latency_ms) AS p50_cont,
       PERCENTILE_DISC(0.5) WITHIN GROUP (ORDER BY latency_ms) AS p50_disc,
       PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) AS p95_cont
FROM samples GROUP BY service ORDER BY service;
```

**Expected results:** API `n=5, p50_cont=20, p50_disc=20, p95_cont=88`; FILE `n=4, p50_cont=20, p50_disc=15, p95_cont=33.5`. Continuous percentile interpolation uses ordered zero-based position `(n-1)*fraction`; for API p95, position 3.8 interpolates between 40 and 100, giving 88. For FILE p50, position 1.5 gives 20, while discrete p50 returns 15.

**DBRE/SRE interpretation:** These are toy values, not evidence of an actual SLO breach. A real p95 report must specify sampling, time window, success/error inclusion, and missing telemetry. For ingestion batches, a p95 duration can flag a heavy tail hidden by the average.

## 4. Hands-on lab (20 minutes)

1. Independently confirm PostgreSQL **18.x**, the disposable `sql_tutorials` database, nonproduction credentials, and endpoint isolation. No production endpoint or real telemetry is permitted.
2. From the repository root run `psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/077-ntile-percentiles-distribution.sql` against that verified endpoint.
3. Inspect the four `NTILE` buckets, including the tied API 20 ms rows; explain why they split.
4. Compare p50 continuous and discrete results, then explain why FILE's median is 20 vs 15.
5. Check the missing API measurement count, exact-result acceptance output, and `ROLLBACK`. A successful assertion must show all `*_ok` values true and `fail_closed_acceptance=1`.
6. Practice: change `NTILE(4)` to `NTILE(3)` in a scratch copy, predict the API bucket sizes **2,2,1**; restore the original file. Practice: calculate API p75 continuous: **40**. Do not modify production objects.

The lab repeats its tiny inline dataset for a deterministic two-way `EXCEPT ALL` comparison and fails closed on mismatches. It creates no persistent tables.

## 5. Troubleshooting and validation (5 minutes)

| Symptom | Cause | Safe response |
|---|---|---|
| Bucket membership changes | Nonunique sort keys | Add stable event ID as tie-breaker |
| Continuous p50 differs from observed values | Interpolation | Compare with `PERCENTILE_DISC` |
| p95 unexpectedly NULL or low | Missing values or wrong filter | Count missing and measured rows separately |
| Percentiles differ across warehouses | Approximate function or different NULL/type semantics | Document dialect, method, and test on same input |
| `NTILE(4)` yields fewer than four buckets | Partition has fewer than four rows | Interpret as row buckets, not fixed numeric ranges |
| SQL fails environment guard | Wrong database/version | Stop; do not bypass the guard |

**Validation states:** Examples and expected values are manually reasoned; targeted static checks can inspect the SQL text. This is **not** independent editorial approval, comprehensive SQL parser/link validation, or PostgreSQL 18 runtime certification. Record server version, lab SHA, exact command, stdout/stderr, exit status, and reviewer when an isolated runtime test is actually executed.

## 6. Review questions and answers (5 minutes)

1. **Does `NTILE(4)` guarantee four equal-sized latency ranges?** No; it balances row counts and may split ties.
2. **Why is FILE's continuous median 20 but discrete median 15?** Even-sized sample interpolation averages the middle 15 and 25; discrete p50 selects the first value meeting the cumulative 50% threshold.
3. **Does `PERCENT_RANK()` return the same result as `PERCENTILE_CONT`?** No. The former ranks each row relative to the partition; the latter estimates a value threshold.
4. **How should NULL telemetry be treated?** Count and report it as missing; do not silently replace it with zero.
5. **Can five observations establish reliable production p99?** No; the sample is too small and must not be represented as production evidence.

## References and next steps

- [PostgreSQL 18 — Window Functions](https://www.postgresql.org/docs/18/functions-window.html)
- [PostgreSQL 18 — Aggregate Functions / Ordered-set aggregates](https://www.postgresql.org/docs/18/functions-aggregate.html)
- [PostgreSQL 18 — SELECT](https://www.postgresql.org/docs/18/sql-select.html)
- [Master TOC — Part 08](../MASTER-TOC.md#part-08--window-functions--advanced-analytics)
- [Next: 078 — Gaps-and-islands patterns](../MASTER-TOC.md#part-08--window-functions--advanced-analytics) (planned)
