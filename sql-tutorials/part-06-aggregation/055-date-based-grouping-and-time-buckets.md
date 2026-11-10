# 055 — Date-based Grouping and Time Buckets

**Part 06 — Aggregation, Grouping & Reporting** · **60 minutes** · **Audience:** SQL beginners, data engineers, DBRE/SRE · **Lab:** PostgreSQL 18

[Master TOC](../MASTER-TOC.md) · [Tutorial index](../README.md) · [Previous: 054](054-conditional-aggregation-with-case-and-filter.md) · [SQL lab](../labs/055-date-based-grouping-time-buckets.sql) · [Next: 056 (planned)](../MASTER-TOC.md)

## 1. Learning outcomes and prerequisites (5 minutes)

After this chapter, you can explain event time versus processing time, group events into days and calendar months, write safe half-open timestamp filters, select a reporting timezone, reconcile time-bucket totals, and identify daylight-saving-time and index-usage pitfalls. Prerequisites: [051 — aggregates](051-count-sum-avg-min-and-max.md), [052 — GROUP BY](052-group-by-and-aggregation-grain.md), and [054 — conditional aggregation](054-conditional-aggregation-with-case-and-filter.md).

**Use case:** A data engineer creates monthly payment KPIs; a DBRE/SRE checks whether ingestion volumes changed across UTC month boundaries. All records below are fictional.

## 2. Concepts: event time, bucket grain, and timezone (10 minutes)

An **event timestamp** represents when something happened; an **ingestion timestamp** represents when the platform received it. Late arrivals can change historical event-time aggregates. Specify whether a KPI uses event time or ingestion time before writing SQL.

A **bucket** maps timestamps to a calendar interval. A UTC calendar month is not a fixed number of seconds: months have different lengths. An event at 2026-02-01 00:15 UTC is still January 31 in New York. Grouping by a bare date without agreeing on a timezone is a reporting defect.

For month reporting, choose **UTC** as the explicit lab policy. The month start is inclusive; the next month start is exclusive. Avoid `BETWEEN` with a guessed end-of-day timestamp, which can lose fractional-second events.

**Portability:** `EXTRACT(YEAR FROM ...)`, `EXTRACT(MONTH FROM ...)`, `GROUP BY`, and `SUM` are widely supported SQL constructs, but temporal types and session-timezone rules differ. PostgreSQL `date_trunc`, `timestamptz`, `AT TIME ZONE`, `SET LOCAL`, and `::date` are dialect-specific or have vendor-specific semantics. MySQL uses `DATE_FORMAT` for formatting; SQL Server has `DATEPART` and `DATETRUNC` (supported versions); BigQuery and Snowflake offer their own truncation/timezone signatures. Validate each target dialect separately.

## 3. Walkthrough: synthetic events and daily totals (15 minutes)

The lab creates a temporary table with six UTC events:

| Event | UTC timestamp | Amount |
|---|---|---:|
| 1 | Jan 31 23:30 | 10.00 |
| 2 | Feb 01 00:15 | 20.00 |
| 3 | Feb 01 12:00 | 30.00 |
| 4 | Feb 28 23:59 | 40.00 |
| 5 | Mar 01 00:00 | 50.00 |
| 6 | Mar 01 01:00 | 60.00 |

For a **PostgreSQL 18** connection with `SET LOCAL TIME ZONE 'UTC'`:

```sql
SELECT date_trunc('day', occurred_at)::date AS day_utc,
       COUNT(*) AS event_count, SUM(amount) AS total
FROM ch055_events
GROUP BY 1 ORDER BY 1;
```

Expected five day groups: January 31 = 10.00; February 1 = 50.00 (2 events); February 28 = 40.00; March 1 = 110.00 (2 events). The five groups reconcile to **6 events / 210.00**.

```sql
SELECT date_trunc('month', occurred_at)::date AS month_utc,
       COUNT(*) AS event_count, SUM(amount) AS total
FROM ch055_events GROUP BY 1 ORDER BY 1;
```

| Month start (UTC) | Events | Total |
|---|---:|---:|
| 2026-01-01 | 1 | 10.00 |
| 2026-02-01 | 3 | 90.00 |
| 2026-03-01 | 2 | 110.00 |

A broadly portable year/month grouping is:

```sql
SELECT EXTRACT(YEAR FROM occurred_at) AS report_year,
       EXTRACT(MONTH FROM occurred_at) AS report_month,
       COUNT(*) AS events, SUM(amount) AS total
FROM ch055_events
GROUP BY EXTRACT(YEAR FROM occurred_at), EXTRACT(MONTH FROM occurred_at)
ORDER BY report_year, report_month;
```

**Important:** This only gives the same UTC result if the database/session interprets `occurred_at` in UTC. In PostgreSQL, `timestamptz` is displayed and extracted in the session timezone unless you explicitly convert.

## 4. Half-open windows and index-aware filtering

```sql
SELECT COUNT(*), SUM(amount)
FROM ch055_events
WHERE occurred_at >= TIMESTAMPTZ '2026-02-01 00:00:00+00'
  AND occurred_at <  TIMESTAMPTZ '2026-03-01 00:00:00+00';
-- Expected: 3, 90.00
```

This pattern is preferable to `WHERE date_trunc('month', occurred_at) = ...` when an ordinary B-tree index on `occurred_at` exists: the raw-column range is usually more index-friendly. It does **not** guarantee an index scan; verify with `EXPLAIN` and production-representative statistics later in Part 10. Do not create an index on production just for this tutorial.

## 5. Reporting timezone and DST

```sql
SELECT event_id,
       (occurred_at AT TIME ZONE 'America/New_York')::date AS ny_local_date
FROM ch055_events
WHERE event_id IN (1,2,5)
ORDER BY event_id;
```

Expected New York local dates: event 1 = January 31; event 2 = January 31; event 5 = February 28. The source timestamp represents the same instant, but its local calendar date changes. For daily/monthly **local** KPIs, first convert to the agreed business timezone and then truncate; do not mix UTC and local date boundaries. DST days can have 23 or 25 hours, so do not model local days as always 86,400 seconds.

## 6. Hands-on PostgreSQL 18 lab (20 minutes)

**Preflight:** use a disposable isolated PostgreSQL **18.x** instance and database named `sql_tutorials`. Check host, port, database, username, and environment with your lab owner; never use production credentials. The script rejects a different major version or database, sets transaction-local timeouts, uses only temporary data, and ends in `ROLLBACK`. A matching database name alone does not prove isolation—verify the endpoint independently.

From a terminal with `psql` configured for the isolated instance:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/055-date-based-grouping-time-buckets.sql
```

Run from the repository root or adjust the path. The script prints UTC monthly totals, a February range check, local New York dates, and raises an exception if expected values differ. Exit code zero and a passing notice are **necessary but not sufficient** for acceptance: retain the actual command, connection identity, PostgreSQL version, captured output, exit code, and rollback evidence.

Practice: (a) add a daily grouping query; (b) compare UTC and New York month attribution; (c) compute February's share of 210.00, approximately 42.86%; (d) explain how a late-arriving January event would change a historical January KPI. Make changes only to your local disposable copy of the lab.

## 7. Validation, reconciliation, and troubleshooting (5 minutes)

| Symptom | Likely cause | Safe investigation |
|---|---|---|
| February has 2 instead of 3 events | Wrong boundary or timezone | Inspect UTC instants and exclusive upper bound |
| Totals differ by timezone | Local versus UTC bucket definition | Document report timezone and compare boundary events |
| Day totals duplicate | Join fan-out | Aggregate at event grain before joining dimension tables |
| Slow timestamp filter | Function applied to indexed column | Compare half-open raw-column predicate and `EXPLAIN` |
| Unexpected empty month | No events in source | A calendar dimension/series is needed for zero-filled months |

Validate `SUM(month_total)=SUM(source_amount)=210.00` and `SUM(month_count)=6`. Calendar gaps require a date spine; ordinary `GROUP BY` does not generate missing periods. A daily ingestion dashboard may differ from an event-time dashboard because of late arrivals and replayed events.

**Operational guardrails:** run only on synthetic data, avoid permanent DDL and production endpoints, bound exploratory scans, use explicit timezone and date-range parameters, and confirm the report grain before joins. `ROLLBACK` cleans up the temporary fixture, but cannot protect against connecting to the wrong system; the preflight is mandatory.

## 8. Review questions and answers (5 minutes)

1. **Why use a half-open range?** It includes every timestamp before the next boundary without inventing the last fractional second.
2. **Why can UTC and local monthly totals differ?** An instant near midnight UTC may belong to a different local calendar day or month.
3. **Does `GROUP BY` generate zero-event months?** No; use a calendar table or generated series with an outer join.
4. **Why group by both year and month?** Grouping only by month number merges different years.
5. **Can an event-time January total change in February?** Yes, late-arriving January events or corrections can update historical buckets.
6. **Is `date_trunc` portable to every SQL engine?** No; syntax and timezone behavior require dialect-specific verification.

## 9. References and next chapter

- [PostgreSQL 18 — Date/Time Functions and Operators](https://www.postgresql.org/docs/18/functions-datetime.html)
- [PostgreSQL 18 — Date/Time Types](https://www.postgresql.org/docs/18/datatype-datetime.html)
- [PostgreSQL 18 — Aggregate Functions](https://www.postgresql.org/docs/18/functions-aggregate.html)
- [Chapter 056 — Text transformations for reporting (Master TOC)](../MASTER-TOC.md)

**Validation state at authorship:** tutorial and lab authored for publication; targeted static review only. Independent editorial review, comprehensive automated syntax/link checks, and actual isolated PostgreSQL 18 execution/evidence remain pending.
