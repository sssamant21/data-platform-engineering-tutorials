# 078 — Gaps-and-Islands Patterns

**Part 08 — Window Functions & Advanced Analytics | 60 minutes | PostgreSQL 18 baseline**

[Curriculum](../MASTER-TOC.md) · [Part 08 navigation](../README.md) · [SQL lab](../labs/078-gaps-and-islands-patterns.sql) · [Previous: 077](077-ntile-percentiles-and-distribution-analysis.md)

## Objectives and schedule

After this lesson you can distinguish missing sequence values (**gaps**) from contiguous runs (**islands**), identify runs using `ROW_NUMBER()` and `LAG()`, avoid duplicate and ordering pitfalls, and apply the patterns to data-pipeline continuity and DBRE/SRE telemetry.

| Minutes | Activity |
|---|---|
| 0–10 | Define sequence grain, gaps, and islands |
| 10–25 | Work through row-number island keys |
| 25–35 | Find missing values with LAG |
| 35–45 | Run the synthetic PostgreSQL 18 lab |
| 45–55 | Practice and troubleshoot |
| 55–60 | Review answers and operational safeguards |

## 1. What is a gap? What is an island?

Suppose a service successfully ingested batches numbered **1, 2, 3, 5, 6, 9**. The contiguous islands are **1–3**, **5–6**, and **9–9**. The missing batch numbers are **4, 7, 8**. Never assume batch IDs are supposed to be consecutive without a documented contract: sequences, sharding, retries, and cancellations may legitimately create holes. An absent event is a candidate for investigation, not proof of data loss.

**Grain:** one distinct, accepted batch number *per service*. A duplicate retry must not create another sequence position. We will use fictional `api` and `file` services.

## 2. Portable island detection with ROW_NUMBER

The following query uses inline synthetic data and broadly portable window-function syntax. `ROW_NUMBER()` requires a deterministic order; after deduplicating, the difference `batch_no - row_number` stays constant inside a consecutive run.

```sql
WITH events(service, batch_no) AS (
  VALUES ('api',1),('api',2),('api',3),('api',5),
         ('api',6),('api',9),('file',10),('file',11),
         ('file',13),('file',14)
), unique_batches AS (
  SELECT DISTINCT service, batch_no FROM events
), numbered AS (
  SELECT service, batch_no,
         ROW_NUMBER() OVER (PARTITION BY service ORDER BY batch_no) AS rn
  FROM unique_batches
), islands AS (
  SELECT service, MIN(batch_no) AS start_batch,
         MAX(batch_no) AS end_batch, COUNT(*) AS batch_count
  FROM (
    SELECT service, batch_no, batch_no - rn AS island_key
    FROM numbered
  ) x
  GROUP BY service, island_key
)
SELECT * FROM islands ORDER BY service, start_batch;
```

Expected:

| service | start_batch | end_batch | batch_count |
|---|---:|---:|---:|
| api | 1 | 3 | 3 |
| api | 5 | 6 | 2 |
| api | 9 | 9 | 1 |
| file | 10 | 11 | 2 |
| file | 13 | 14 | 2 |

Why it works: for API batches 1, 2, 3, the row numbers are 1, 2, 3, so `batch_no - rn = 0` throughout. At batch 5, the row number is 4, giving key 1. At batch 9, the row number is 6, giving key 3. **Do not group only by the computed key:** include `service`, or unrelated streams can merge.

## 3. Find missing ranges with LAG

`LAG(batch_no)` retrieves the previous *existing* batch in each ordered service stream. If `batch_no > previous_batch + 1`, the missing inclusive interval starts at `previous_batch + 1` and ends at `batch_no - 1`.

```sql
WITH events(service, batch_no) AS (
  VALUES ('api',1),('api',2),('api',3),('api',5),
         ('api',6),('api',9),('file',10),('file',11),
         ('file',13),('file',14)
), unique_batches AS (
  SELECT DISTINCT service, batch_no FROM events
), neighbors AS (
  SELECT service, batch_no,
         LAG(batch_no) OVER (PARTITION BY service ORDER BY batch_no) AS prev_batch
  FROM unique_batches
)
SELECT service, prev_batch + 1 AS missing_from,
       batch_no - 1 AS missing_through,
       batch_no - prev_batch - 1 AS missing_count
FROM neighbors
WHERE prev_batch IS NOT NULL AND batch_no > prev_batch + 1
ORDER BY service, missing_from;
```

Expected gaps: **api 4–4 (1), api 7–8 (2), file 12–12 (1)**. Total missing positions: **4**. The query detects *internal* gaps only; it cannot detect missing values before the first observed batch or after the last without an external expected range or watermark.

## 4. Alternative LAG-based island identifiers (PostgreSQL 18)

Another approach flags the start of each run with `CASE WHEN prev_batch IS NULL OR batch_no <> prev_batch + 1 THEN 1 ELSE 0 END`. A running `SUM` over an explicit `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` frame assigns an island number. This is often easier to extend for temporal islands, where continuity means a time difference no larger than a defined threshold. Timestamp-based islands require explicit timezone and late-arrival policies; do not assume adjacent rows represent adjacent calendar days.

**Portability:** `ROW_NUMBER`, `LAG`, `SUM() OVER`, `GROUP BY`, and `CASE` are widely implemented SQL constructs. `VALUES` as a table expression, timestamp arithmetic, interval syntax, date series generation, and exact casting rules vary by engine. The companion lab is explicitly PostgreSQL 18 SQL, including `psql` meta-commands and PostgreSQL settings. Oracle's and SQL Server's date arithmetic differ; adapt and test rather than copying PostgreSQL-only syntax.

## 5. Data engineering and DBRE/SRE applications

- **CDC/ingestion:** identify missing expected sequence positions per connector or partition; reconcile with source offsets and replay logs before declaring data loss.
- **Monitoring:** group consecutive failed health-check intervals, but normalize timestamps to agreed buckets first.
- **Incident response:** report a compact range (`7–8`) rather than generating every missing value across potentially huge gaps.
- **Capacity and performance:** deduplicate and filter early; window sorting can be expensive on large streams. Inspect `EXPLAIN` in an isolated environment and consider suitable `(service, batch_no)` indexing in a real schema only after review.

## 6. Hands-on lab

Use only the disposable `sql_tutorials` PostgreSQL 18 database. From the repository root:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/078-gaps-and-islands-patterns.sql
```

The lab runs `BEGIN READ ONLY`, transaction-local timeouts, a PostgreSQL 18 version guard, a database-name guard, synthetic inline rows, island and gap queries, and fail-closed exact-result assertions. It ends with `ROLLBACK`. The database name alone is not a substitute for checking host, user, and isolation: **do not run on production**. Expected acceptance: five islands, three gap ranges, four missing positions, and an assertion result of **1**.

## 7. Practice

1. Add a duplicate `('api',5)` to the input. Explain why the `DISTINCT` step keeps island boundaries unchanged.
2. Add API batch 7. Recalculate the gaps: the API 7–8 gap becomes 8–8, leaving API gaps 4 and 8.
3. Remove FILE batch 11. Expected FILE islands become 10–10 and 13–14; its internal gap becomes 11–12.
4. Design a query for missing *daily* snapshots. Specify whether missing weekends count, the timezone, and how late-arriving snapshots are treated before writing SQL.

## 8. Troubleshooting and safety

| Symptom | Likely cause / remedy |
|---|---|
| Islands split unexpectedly | Duplicate sequence numbers were not deduplicated; check grain and `DISTINCT`. |
| Islands from different sources combine | `service` omitted from partition or grouping. |
| Missing initial or trailing numbers | `LAG` only sees internal gaps; join to an authoritative expected range. |
| Huge missing-value expansion | Report ranges first; avoid unbounded `generate_series`. |
| Different results between runs | Missing deterministic `ORDER BY` or inconsistent type normalization. |
| SQL lab guard fails | Wrong PostgreSQL major version or database; stop, verify environment, never bypass guard. |

Do not create objects, update offsets, replay production events, or run heavy scans on production for this tutorial. For real incidents, investigate ingestion logs, retention, expected sequence semantics, and late-arrival windows before remediation.

## 9. Review questions with answers

**Q1. What defines an island?** A contiguous sequence of expected positions at the chosen grain.

**Q2. Why use `DISTINCT` before `ROW_NUMBER`?** Duplicate retries would otherwise change row numbers and break the constant-key method.

**Q3. Why partition by service?** Independent streams have independent sequences; mixing them produces false runs.

**Q4. What does `LAG` fail to detect by itself?** Leading and trailing gaps outside the observed range.

**Q5. Does a missing sequence number prove lost data?** No. Confirm the source's numbering and retention contract.

**Q6. Why report gap ranges rather than expand each missing value?** It bounds work and keeps incident reports concise even for very large gaps.

## 10. References

- [PostgreSQL 18 — Window Functions](https://www.postgresql.org/docs/18/tutorial-window.html)
- [PostgreSQL 18 — Window Function Calls](https://www.postgresql.org/docs/18/sql-expressions.html#SYNTAX-WINDOW-FUNCTIONS)
- [PostgreSQL 18 — Window Functions Reference](https://www.postgresql.org/docs/18/functions-window.html)
- [PostgreSQL 18 — SELECT](https://www.postgresql.org/docs/18/sql-select.html)

**Publication state:** Authored for the SQL learning path. Independent editorial review, comprehensive automated syntax/link QA, and actual isolated PostgreSQL 18 runtime acceptance are separate pending activities.
