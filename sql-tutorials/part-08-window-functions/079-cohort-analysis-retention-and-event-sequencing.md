# 079 — Cohort Analysis, Retention, and Event Sequencing

**Part 08 — Window Functions & Advanced Analytics | 60 minutes | PostgreSQL 18 lab baseline**

[Master TOC](../MASTER-TOC.md) · [SQL Tutorials](../README.md) · [Companion SQL lab](../labs/079-cohort-retention-event-sequencing.sql) · [Previous: 078](078-gaps-and-islands-patterns.md) · [Next: 080 — Lab 08](../MASTER-TOC.md#part-08--window-functions--advanced-analytics)

## Learning objectives and 60-minute agenda

By the end, you can define an acquisition cohort, calculate weekly distinct-user retention, sequence events using window functions, recognize denominator and late-arrival errors, and explain how data engineering and DBRE/SRE teams validate activity metrics.

| Time | Activity |
|---|---|
| 0–5 min | Outcomes, prerequisites, and grain |
| 5–15 min | Cohort, activity, retention, and event definitions |
| 15–30 min | Worked examples and sequencing |
| 30–50 min | Isolated read-only PostgreSQL 18 lab |
| 50–55 min | Troubleshooting, reconciliation, and guardrails |
| 55–60 min | Questions, answers, and next steps |

**Prerequisites:** Chapters [071](071-window-function-anatomy-over-partition-by-order-by.md), [073](073-lag-and-lead-for-change-analysis.md), and [078](078-gaps-and-islands-patterns.md). You need a disposable PostgreSQL 18 instance and `psql` for the companion lab. Do not use a production connection.

## 1. Define the business question before SQL

A **cohort** is a group of entities sharing a starting period, such as the calendar week of a user's first qualifying event. **Retention at week N** means the number of distinct members of that original cohort with at least one qualifying event in week N, divided by the **original cohort size**. Week 0 is the acquisition week; week 1 is the following calendar week. This is **calendar-week retention**, not a rolling seven-day window.

**Grain:** one row per distinct `(user_id, cohort_week, activity_week)` before aggregation. A user may emit multiple events in a week; counting events instead of distinct users inflates retention. Choose the timezone, event eligibility rules, user identity mapping, and whether acquisition is based on all history or the available observation window. Here, synthetic events are dates already normalized to one agreed reporting timezone. Production timestamps require explicit timezone conversion before truncation.

The dataset contains six fictional users. Cohorts start Monday **2026-01-05** (users 1–3), **2026-01-12** (users 4–5), and **2026-01-19** (user 6). User 1 returns in weeks 1 and 2; user 2 returns in week 1; user 3 does not return. User 4 returns in week 1; user 5 does not return. User 6 has no subsequent observed week.

## 2. Portable SQL concepts and a PostgreSQL 18 example

The general pattern is widely portable: `MIN(event_date) OVER (PARTITION BY user_id)` identifies each user's first event; `ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY event_date, event_id)` sequences events; `COUNT(DISTINCT user_id)` counts active members. **Calendar-week truncation and week arithmetic below are PostgreSQL-specific**. For portability, use an approved calendar dimension with a stable `week_start` and `week_index`, then calculate `activity_week_index - cohort_week_index` instead of relying on vendor date functions.

The following complete example is PostgreSQL 18 SQL, with synthetic inline data only:

```sql
WITH events(user_id, event_id, event_day) AS (
  VALUES
    (1,101,DATE '2026-01-05'),(1,102,DATE '2026-01-12'),
    (1,103,DATE '2026-01-19'),(2,201,DATE '2026-01-06'),
    (2,202,DATE '2026-01-13'),(3,301,DATE '2026-01-07'),
    (4,401,DATE '2026-01-12'),(4,402,DATE '2026-01-20'),
    (5,501,DATE '2026-01-13'),(6,601,DATE '2026-01-19')
), annotated AS (
  SELECT *,
         MIN(event_day) OVER (PARTITION BY user_id) AS first_day,
         ROW_NUMBER() OVER (
           PARTITION BY user_id ORDER BY event_day, event_id
         ) AS event_number
  FROM events
), weekly_users AS (
  SELECT DISTINCT user_id,
         date_trunc('week', first_day)::date AS cohort_week,
         date_trunc('week', event_day)::date AS activity_week
  FROM annotated
), cohort_sizes AS (
  SELECT cohort_week, COUNT(*) AS cohort_size
  FROM weekly_users WHERE activity_week = cohort_week
  GROUP BY cohort_week
), retention AS (
  SELECT cohort_week,
         ((activity_week - cohort_week) / 7) AS week_number,
         COUNT(*) AS active_users
  FROM weekly_users
  GROUP BY cohort_week, activity_week
)
SELECT r.cohort_week, r.week_number, c.cohort_size,
       r.active_users,
       ROUND(100.0 * r.active_users / NULLIF(c.cohort_size,0), 2)
         AS retention_pct
FROM retention r JOIN cohort_sizes c USING (cohort_week)
ORDER BY r.cohort_week, r.week_number;
```

**Expected results (calculated from the synthetic input, not runtime-verified):**

| cohort_week | week_number | cohort_size | active_users | retention_pct |
|---|---:|---:|---:|---:|
| 2026-01-05 | 0 | 3 | 3 | 100.00 |
| 2026-01-05 | 1 | 3 | 2 | 66.67 |
| 2026-01-05 | 2 | 3 | 1 | 33.33 |
| 2026-01-12 | 0 | 2 | 2 | 100.00 |
| 2026-01-12 | 1 | 2 | 1 | 50.00 |
| 2026-01-19 | 0 | 1 | 1 | 100.00 |

A missing week row is **not** automatically 0%: it might be unobserved, not yet elapsed, or truly inactive. For a complete retention matrix, join cohorts to an explicit calendar of eligible observed weeks and left-join activity; never fill future weeks with zero. Cohort denominators remain fixed across weeks.

## 3. Event sequencing and repeat activity

`ROW_NUMBER()` establishes a stable ordinal per user when `event_id` breaks same-day ties. `LAG(event_day)` returns the previous event date. The difference `event_day - LAG(event_day)` gives days between successive events in PostgreSQL; the first event yields NULL. This answers operational questions such as “how long between successful pipeline runs?” or “did a client return after onboarding?”

```sql
WITH events(user_id, event_id, event_day) AS (
  VALUES (1,101,DATE '2026-01-05'),
         (1,102,DATE '2026-01-12'),
         (1,103,DATE '2026-01-19')
)
SELECT user_id, event_id, event_day,
       ROW_NUMBER() OVER (
         PARTITION BY user_id ORDER BY event_day, event_id
       ) AS event_number,
       event_day - LAG(event_day) OVER (
         PARTITION BY user_id ORDER BY event_day, event_id
       ) AS days_since_previous
FROM events
ORDER BY user_id, event_number;
```

Expected user 1 event numbers: **1, 2, 3**; intervals: **NULL, 7, 7**. If `event_id` is not unique within a user, add a genuine stable event key; arbitrary ties make sequencing nondeterministic. A `LAG` interval measures observed-event separation, not proof of continuous engagement.

## 4. Hands-on lab — 20 minutes

Run from the repository root against a disposable local PostgreSQL 18 database named `sql_tutorials`:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials \
  -f sql-tutorials/labs/079-cohort-retention-event-sequencing.sql
```

Before running, verify the target host, port, user, and database. The SQL script prints connection identity, checks PostgreSQL major version and database name, uses `BEGIN READ ONLY`, sets transaction-local timeouts, and ends with `ROLLBACK`. Its final assertion compares the **entire expected retention multiset in both directions** using `EXCEPT ALL`, checks sequencing, and fails closed on discrepancies. The expected final acceptance column is **1**. This expectation is derived statically; it is **not** evidence of PostgreSQL 18 execution.

**Exercises:** (1) Calculate week-1 retention for the first cohort: `2/3 = 66.67%`. (2) Add a second event for user 2 in the same week; the retention numerator must remain 2 because of `DISTINCT`. (3) Add a qualifying event for user 3 on January 20; first-cohort week-2 retention rises from 1/3 to 2/3. (4) Explain why a newly acquired cohort cannot yet have a meaningful week-4 retention rate.

## 5. Troubleshooting, safety, and interpretation

| Symptom | Likely cause / corrective action |
|---|---|
| Retention exceeds 100% | Counted events rather than distinct cohort members, or denominator changed |
| Cohort assignment shifts | First-ever qualifying event missing due to truncated history or late arrival |
| Different week boundaries | Timezone or calendar-week convention inconsistent across pipelines |
| Duplicate active users | Event retries not deduplicated at user-week grain |
| Missing rows mistaken for zero | No eligible observation week; use an explicit calendar and data watermark |
| Event sequence changes between runs | Missing unique tie-breaker in window `ORDER BY` |
| Lab guard fails | Wrong database or PostgreSQL version; stop and inspect connection, never bypass guard |

**Data engineering:** reconcile event volume, distinct users, duplicate event IDs, ingestion watermark, and late-arriving corrections before publishing cohort dashboards. **DBRE/SRE:** bound query runtime, assess window-sort costs and data volume, avoid unrestricted scans on production, and keep dashboard definitions version-controlled. No production credentials, customer records, patient data, DDL, or DML belong in this exercise.

## 6. Review questions and answers

**Q1. What is the denominator of week-2 retention?** The original number of members in the acquisition cohort, not week-1 active users.

**Q2. Why deduplicate by user and activity week?** A user with multiple events should count once toward that week's retention.

**Q3. Why does week 0 normally show 100%?** Each member qualifies by having their first event in that week under this cohort definition.

**Q4. Is an absent week-3 row 0% retention?** Not necessarily; verify the observation horizon and calendar before labeling inactivity.

**Q5. What makes `ROW_NUMBER` deterministic?** An `ORDER BY` whose keys uniquely determine event order, such as event date plus stable event ID.

**Q6. What changes between SQL engines?** Week truncation, date arithmetic, interval and casting syntax, and potentially default week definitions. The window/aggregation concepts are broadly portable.

## References and next chapter

- [PostgreSQL 18 — Window Functions](https://www.postgresql.org/docs/18/functions-window.html)
- [PostgreSQL 18 — Date/Time Functions](https://www.postgresql.org/docs/18/functions-datetime.html)
- [PostgreSQL 18 — SELECT](https://www.postgresql.org/docs/18/sql-select.html)
- [PostgreSQL 18 — Aggregate Functions](https://www.postgresql.org/docs/18/functions-aggregate.html)
- [Chapter 080 — Analytical Customer Activity Report](../MASTER-TOC.md#part-08--window-functions--advanced-analytics)

**Validation state:** authored lesson; publication is separate from independent editorial review, comprehensive automated syntax/link QA, and actual isolated PostgreSQL 18 runtime acceptance. No runtime certification is asserted.
