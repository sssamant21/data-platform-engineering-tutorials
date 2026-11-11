# 082 — Dates, Intervals, Timestamps, and Time Zones

**Part 09 — SQL Objects, Functions & Semi-Structured Data | 60 minutes | PostgreSQL 18 lab**

[Master TOC](../MASTER-TOC.md) · [Index](../README.md) · [SQL lab](../labs/082-dates-intervals-timestamps-time-zones.sql) · [Previous: 081](081-string-functions-and-regular-expressions.md) · [Next: 083](../MASTER-TOC.md#part-09--sql-objects-functions--semi-structured-data)

## 1. Outcomes and plan (0–5 minutes)

Explain DATE, TIME, TIMESTAMP WITHOUT TIME ZONE, TIMESTAMP WITH TIME ZONE (`timestamptz`), INTERVAL, half-open ranges, daylight-saving changes, and UTC-based event ingestion. Write and verify time-zone-safe reports without modifying source data. Prerequisites: [009 — data types](../part-01-fundamentals/009-data-types-null-and-explicit-type-conversion.md), [055 — date grouping](../part-06-aggregation/055-date-based-grouping-and-time-buckets.md), isolated PostgreSQL 18 database `sql_tutorials`.

| Time | Activity |
|---|---|
| 0–5 | Objectives and environment |
| 5–15 | Temporal types and semantics |
| 15–30 | Worked examples and DST |
| 30–50 | Synthetic lab and exercises |
| 50–55 | Troubleshooting and safety |
| 55–60 | Review and answers |

## 2. Temporal types and storage (5–15 minutes)

| Type | Meaning | Example |
|---|---|---|
| `DATE` | Calendar date, no clock or zone | `DATE '2026-03-08'` |
| `TIME` | Clock time without date | `TIME '09:30:00'` |
| `TIMESTAMP` | Local date and clock time; **no zone** | `TIMESTAMP '2026-03-08 09:30:00'` |
| `TIMESTAMPTZ` | Instant; PostgreSQL normalizes internally and displays using session TimeZone | `TIMESTAMPTZ '2026-03-08 09:30:00+00'` |
| `INTERVAL` | Calendar/time duration; months and days are not always fixed seconds | `INTERVAL '1 day'` |

SQL-standard DATE, TIMESTAMP, INTERVAL, EXTRACT, and arithmetic are broadly portable; `timestamptz`, `AT TIME ZONE` behavior, `date_trunc`, `make_interval`, and timezone database names are PostgreSQL-specific or vary by vendor. PostgreSQL does **not** retain the original named zone in a `timestamptz` value. Keep the source zone identifier separately when required for audit or customer-local scheduling. Prefer UTC instants for event occurrence and explicit IANA zone identifiers (e.g. `America/New_York`) for presentation.

## 3. Worked examples (15–30 minutes)

### A. UTC instants and local display

```sql
SELECT event_id,
       occurred_at AT TIME ZONE 'America/New_York' AS new_york_wall_time
FROM (VALUES
 (1, TIMESTAMPTZ '2026-03-08 06:30:00+00'),
 (2, TIMESTAMPTZ '2026-03-08 07:30:00+00')
) AS events(event_id, occurred_at)
ORDER BY event_id;
```

Expected New York wall times: event 1 = `2026-03-08 01:30:00`, event 2 = `2026-03-08 03:30:00`. The clock skips 02:00–02:59 on spring-forward day, even though the instants are exactly 60 minutes apart. These synthetic 2026 dates use PostgreSQL's named-zone rules.

### B. Half-open time windows

```sql
WITH events(id, occurred_at) AS (
 VALUES (1, TIMESTAMPTZ '2026-03-08 06:30:00+00'),
        (2, TIMESTAMPTZ '2026-03-08 07:30:00+00'),
        (3, TIMESTAMPTZ '2026-03-09 00:00:00+00')
)
SELECT id FROM events
WHERE occurred_at >= TIMESTAMPTZ '2026-03-08 00:00:00+00'
  AND occurred_at <  TIMESTAMPTZ '2026-03-09 00:00:00+00'
ORDER BY id;
```

Expected IDs: 1, 2. The end is excluded, preventing double-counting across adjacent windows. Avoid `BETWEEN` for adjacent timestamp windows because its upper bound is inclusive. Avoid `occurred_at::date` in predicates on large indexed event tables: converting the column can interfere with normal index access and session zone can change the result.

### C. Elapsed versus calendar arithmetic

```sql
SELECT TIMESTAMPTZ '2026-03-08 07:30:00+00'
     - TIMESTAMPTZ '2026-03-08 06:30:00+00' AS elapsed;
```

Expected: `01:00:00`. `INTERVAL '1 day'` and `INTERVAL '24 hours'` can yield different instants across DST boundaries when applied to `timestamptz` in a named-zone session. For SLAs use elapsed instants; for recurring local schedules use explicit calendar rules and a named zone. Do not assume every day has 86,400 elapsed seconds.

### D. Deterministic grouping

```sql
SELECT (occurred_at AT TIME ZONE 'America/New_York')::date AS local_day,
       COUNT(*) AS event_count
FROM (VALUES
 (TIMESTAMPTZ '2026-03-08 06:30:00+00'),
 (TIMESTAMPTZ '2026-03-08 07:30:00+00')
) AS e(occurred_at)
GROUP BY 1;
```

Expected: local day `2026-03-08`, count 2. Use the **business reporting zone** consistently, not whichever zone the connection happens to use.

## 4. Hands-on lab (30–50 minutes)

Run in a disposable PostgreSQL 18 instance, not production:

```bash
psql -X -d sql_tutorials -c "SELECT current_database(), current_setting('server_version'), current_setting('TimeZone');"
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/082-dates-intervals-timestamps-time-zones.sql
```

The read-only transaction checks the database and PostgreSQL major version, fixes the session zone to UTC, and uses only synthetic `VALUES` rows. It asserts exact local wall times, window membership, durations, and day counts using bidirectional `EXCEPT ALL` and fail-closed checks, then rolls back.

Exercises: (1) Change the reporting zone to `America/Los_Angeles` in a **copy of the SELECT**, and explain the different local day boundaries. (2) Count the records in `[2026-03-08 07:00+00, 2026-03-09 00:00+00)`; expected IDs 2 and 3? **No**: the exclusive upper bound excludes ID 3, so only ID 2. (3) Explain why `2026-11-01 01:30` in New York is ambiguous without an offset: the wall time occurs twice during fall-back.

## 5. Troubleshooting and guardrails (50–55 minutes)

- Unexpected displayed hour: inspect `SHOW TimeZone`; display settings do not change the stored instant.
- Ambiguous or nonexistent wall times: require an explicit offset or a documented disambiguation policy at ingestion; never silently guess.
- Off-by-one reporting: compare UTC half-open boundaries and named-zone conversions; record the intended reporting zone.
- Wrong duration: subtract two `timestamptz` instants; distinguish elapsed time from calendar arithmetic.
- Invalid parsing: require ISO-8601-like typed literals or parameterized input; avoid `DateStyle`-dependent ambiguous strings.
- DBRE/SRE: no production credentials, no writes, no session-global setting changes, bounded execution time, preserve raw timestamps and original zone metadata, and reconcile counts across boundaries. Database tzdata updates may change historical named-zone conversions; record version/environment for reproducible audits.

## 6. Review questions and answers (55–60 minutes)

1. **Does PostgreSQL `timestamptz` store a timezone name?** No; it represents an instant and formats using the session zone.
2. **Why use `>= start AND < end`?** Adjacent windows cannot overlap at their shared boundary.
3. **What is the difference between `timestamp` and `timestamptz`?** The former is a wall-clock value without zone; the latter identifies an instant.
4. **Does a DST spring-forward hour change elapsed UTC time?** No; the example has 60 minutes elapsed despite a two-hour wall-clock jump.
5. **Why not group by `occurred_at::date` without a policy?** Session zone can alter which local day receives an event.

## References

- [PostgreSQL 18 — Date/Time Types](https://www.postgresql.org/docs/18/datatype-datetime.html)
- [PostgreSQL 18 — Date/Time Functions and Operators](https://www.postgresql.org/docs/18/functions-datetime.html)
- [PostgreSQL 18 — Date/Time Input](https://www.postgresql.org/docs/18/datatype-datetime.html#DATATYPE-DATETIME-INPUT)
- [PostgreSQL 18 — Runtime TimeZone Configuration](https://www.postgresql.org/docs/18/runtime-config-client.html)
- [Chapter 083 — Numeric expressions and precision](../MASTER-TOC.md#part-09--sql-objects-functions--semi-structured-data)

**Validation status:** Authored; targeted static reasoning only. Independent editorial review, comprehensive static QA, and actual isolated PostgreSQL 18 execution remain pending.
