# Chapter 020 — Lab 02: Filter and Rank Operational Records

> [Master TOC](../MASTER-TOC.md) · [Learning path](../README.md) · [Previous: 019](019-case-coalesce-and-nullif.md) · [Next: 021](../MASTER-TOC.md)
>
> **Part 02 capstone · 60 minutes · PostgreSQL 18 target**
>
> **Validation:** Authored; publication and targeted static reasoning only. Independent editorial review, comprehensive SQL syntax validation, and isolated PostgreSQL 18 execution pending.

## Objectives and prerequisites (0–5 minutes)

By the end, you can filter synthetic service telemetry, handle NULLs correctly, assign operational priority with CASE, sort deterministically, paginate safely, detect duplicates, and reconcile selected rows against an expected answer. Prerequisites: [WHERE (011)](011-where-and-comparison-operators.md), [NULL (013)](013-null-handling-and-sql-three-valued-logic.md), [DISTINCT (016)](016-distinct-and-duplicate-handling.md), [ORDER BY (017)](017-order-by-and-deterministic-sorting.md), [pagination (018)](018-limit-offset-fetch-and-top-across-dialects.md), [CASE (019)](019-case-coalesce-and-nullif.md), and [lab setup (003)](../part-01-fundamentals/003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md).

| Minutes | Activity |
|---|---|
| 0–5 | Outcomes, safety, prerequisites |
| 5–15 | Dataset, SQL predicate and ranking review |
| 15–30 | Guided queries and expected results |
| 30–50 | Independent hands-on lab |
| 50–55 | Troubleshooting and operational guardrails |
| 55–60 | Review questions and answers |

## Synthetic incident dataset and concepts (5–15 minutes)

The data represents eight **fictional** operational events. The event grain is one row per event_id, not one row per service. A NULL latency is **unknown**, not zero. A NULL owner indicates an unassigned event. The table is presented for reasoning only; the companion SQL uses inline VALUES and creates no permanent tables.

| event_id | service | severity | latency_ms | owner_team | event_date |
|---:|---|---:|---:|---|---|
| 401 | api | 1 | 900 | sre | 2026-11-01 |
| 402 | billing | 2 | 300 | NULL | 2026-11-01 |
| 403 | ingest | 1 | NULL | data | 2026-11-02 |
| 404 | api | 3 | 120 | app | 2026-11-02 |
| 405 | search | 2 | 750 | sre | 2026-11-03 |
| 406 | billing | NULL | 600 | NULL | 2026-11-03 |
| 407 | api | 1 | 900 | platform | 2026-11-04 |
| 408 | search | 2 | 750 | data | 2026-11-04 |

**Business rule:** Include severity 1 or 2 events in the inclusive November 1–4 window; exclude unknown severity. Classify severity 1 as P1 and severity 2 as P2. Rank by severity ascending (P1 first), latency descending with NULLs last, then event_id ascending. event_id is the unique tie-breaker; without it, tied rows can swap between runs. NULL handling and collation defaults differ by database.

Portable SQL patterns: WHERE, AND/OR with parentheses, IS NULL, CASE, COALESCE, DISTINCT, ORDER BY, and standard FETCH FIRST. PostgreSQL-specific examples: `DATE '2026-11-01'` is standard, `NULLS LAST` is supported by PostgreSQL but not universally, `LIMIT` is not standard, `::type` casts and `current_setting` are PostgreSQL-specific. SQL Server uses TOP or OFFSET/FETCH; do not copy PostgreSQL syntax blindly.

## Guided examples (15–30 minutes)

### 1. Filter the operational scope

```sql
WITH events(event_id,service,severity,latency_ms,owner_team,event_date) AS (
 VALUES
 (401,'api',1,900,'sre',DATE '2026-11-01'),
 (402,'billing',2,300,NULL::text,DATE '2026-11-01'),
 (403,'ingest',1,NULL::integer,'data',DATE '2026-11-02'),
 (404,'api',3,120,'app',DATE '2026-11-02'),
 (405,'search',2,750,'sre',DATE '2026-11-03'),
 (406,'billing',NULL::integer,600,NULL::text,DATE '2026-11-03'),
 (407,'api',1,900,'platform',DATE '2026-11-04'),
 (408,'search',2,750,'data',DATE '2026-11-04')
)
SELECT event_id, service, severity
FROM events
WHERE severity IN (1,2)
  AND event_date >= DATE '2026-11-01'
  AND event_date < DATE '2026-11-05'
ORDER BY event_id;
```

**Expected IDs:** 401, 402, 403, 405, 407, 408 (6 rows). Event 404 has severity 3; 406 has unknown severity. For timestamp columns, prefer a half-open range using the appropriate time zone and a next-day exclusive boundary.

### 2. Classify and rank without losing unknown latency

```sql
-- Using the same events CTE above:
SELECT event_id,
 CASE WHEN severity=1 THEN 'P1'
      WHEN severity=2 THEN 'P2' ELSE 'other' END AS priority,
 COALESCE(owner_team,'unassigned') AS display_owner,
 latency_ms
FROM events
WHERE severity IN (1,2)
ORDER BY severity ASC, latency_ms DESC NULLS LAST, event_id ASC;
```

**Expected order:** 401, 407, 403, 405, 408, 402. The P1 900ms tie is resolved by event_id; unknown P1 latency is last within P1, ahead of all P2 rows. Display fallback does not repair missing source ownership.

### 3. Paginate deterministically

Append `LIMIT 3 OFFSET 0` to the ranked query for page 1: **401, 407, 403**. Append `LIMIT 3 OFFSET 3` for page 2: **405, 408, 402**. PostgreSQL `LIMIT/OFFSET` is vendor-specific; standard SQL uses `OFFSET 3 ROWS FETCH NEXT 3 ROWS ONLY`. Offset pagination can drift under concurrent writes; production pipelines should use stable snapshots or keyset pagination with the full sort key.

### 4. Reconcile and identify duplicates

```sql
-- Using the same events CTE:
SELECT service, COUNT(*) AS selected_events
FROM events WHERE severity IN (1,2)
GROUP BY service ORDER BY service;
-- Expected: api=2, billing=1, ingest=1, search=2.
```

The count of grouped events is 6, matching the filtered row count. `SELECT DISTINCT service` returns four service names, **not** six event records. Deduplicating by service would discard valid incidents.

## Hands-on lab (30–50 minutes)

Run [020 SQL lab](../labs/020-lab-02-filter-and-rank-operational-records.sql) only on an independently verified disposable PostgreSQL 18 database named `sql_tutorials`. The database name/version guard is necessary but **not sufficient** to establish isolation. Never use production credentials.

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/020-lab-02-filter-and-rank-operational-records.sql
```

The script begins `BEGIN READ ONLY`, uses inline VALUES, sets a local statement timeout, checks database/version, prints ordered results and aggregate counts, asserts exact expected arrays and counts, and ends with `ROLLBACK`. Expected **but not observed**: `environment_assertion=1`, `acceptance_assertion=1`, ranked IDs `{401,407,403,405,408,402}`, six selected events and four distinct services. Any failed assertion causes a SQL error; `ON_ERROR_STOP=1` exits nonzero.

**Practice:** (1) Show P1 events only; expected IDs 401,403,407. (2) Find events with unknown latency; expected 403. (3) Find unassigned owners across *all* events; expected 402,406. (4) Filter latency >=750 and known severity 1/2; expected 401,405,407,408. (5) Show the second three ranked rows; expected 405,408,402. (6) Explain why `NOT IN (1,2)` does not return 406: NULL yields UNKNOWN. (7) Count selected rows per service; expected 2,1,1,2 as above. (8) Check distinct selected service names; expected 4.

## Troubleshooting and safety (50–55 minutes)

| Symptom | Likely cause | Safe remedy |
|---|---|---|
| Event 406 appears unexpectedly | NULL severity was treated as a numeric value | Require `severity IN (1,2)`; explicitly report unknowns separately |
| Order changes across runs | No unique tie-breaker | Add event_id to ORDER BY |
| Unknown latency ranks first | Dialect-dependent NULL defaults | Use explicit NULL ordering or a CASE sort expression |
| Counts differ from six | Missing parentheses, altered range, or duplicated join rows | Verify predicate and event grain; reconcile before reporting |
| Page 2 repeats rows | Missing stable ordering or concurrent changes | Include unique tie-breaker and use stable snapshot/keyset |
| psql exits on assertion | Wrong database/version or incorrect result | Inspect environment; do not bypass guard or change expected answers to hide errors |

**DBRE/SRE controls:** Read-only queries are not free of operational impact. Limit scope, use a short statement timeout, avoid unbounded scans on shared infrastructure, and review EXPLAIN on isolated data before using large tables. Do not mutate operational incidents or change production roles. Do not infer a missing metric is healthy. If a guard fails, stop and diagnose rather than weakening it.

## Review questions and answers (55–60 minutes)

1. Why is event_id the last sort key? **To make ties deterministic.**
2. Why exclude event 406? **Its severity is NULL and the IN predicate is UNKNOWN.**
3. Does `COALESCE(owner_team,'unassigned')` update the source? **No.**
4. How many selected rows? **Six.**
5. How many distinct selected services? **Four.**
6. Which P1 event has unknown latency? **403.**
7. What is page 2 under the prescribed order? **405,408,402.**
8. Does DISTINCT service deduplicate events safely? **No; different events may share a service.**
9. Why prefer a half-open timestamp window? **It avoids losing fractional-second events near the end boundary.**
10. Does a passing static inspection establish PostgreSQL 18 runtime acceptance? **No; execution and retained evidence are required.**

## References and next chapter

- [PostgreSQL 18 SELECT](https://www.postgresql.org/docs/18/sql-select.html)
- [PostgreSQL 18 comparison and NULL semantics](https://www.postgresql.org/docs/18/functions-comparison.html)
- [PostgreSQL 18 conditional expressions](https://www.postgresql.org/docs/18/functions-conditional.html)
- [PostgreSQL 18 psql](https://www.postgresql.org/docs/18/app-psql.html)
- [Next: Chapter 021 — Entity relationships and conceptual data modeling](../MASTER-TOC.md)
