# 073 — LAG and LEAD for Change Analysis

**Part 08 — Window Functions & Advanced Analytics** · **60 minutes** · **Audience:** SQL beginners, data engineers, analysts, DBRE/SRE.

**Prerequisites:** [071 — Window-function anatomy](071-window-function-anatomy-over-partition-by-order-by.md), [072 — Ranking functions](072-row-number-rank-and-dense-rank.md). **Next:** [074 — Running totals and cumulative measures](../MASTER-TOC.md#part-08--window-functions--advanced-analytics).

**Safety:** All data are synthetic inline rows. Run the [PostgreSQL 18 read-only lab](../labs/073-lag-lead-change-analysis.sql) only on an independently verified disposable PostgreSQL 18 instance with a least-privilege account. Database-name/version guards are additional checks, not proof of isolation. The lab uses `BEGIN READ ONLY`, transaction-local timeouts, fail-closed assertions, and `ROLLBACK`.

## 1. Learning objectives and agenda (5 minutes)

After this lesson, you can explain previous/next-row navigation, calculate changes between successive observations, distinguish missing measurements from zero, make ordering deterministic, and identify missing-time-interval pitfalls.

| Activity | Time |
|---|---:|
| Outcomes, prerequisites, safeguards | 5 min |
| Concepts and portable syntax | 10 min |
| Guided examples and expected results | 15 min |
| Hands-on PostgreSQL 18 lab | 20 min |
| Troubleshooting and operational controls | 5 min |
| Review questions with answers | 5 min |

## 2. Core concepts (10 minutes)

`LAG(expression [, offset [, default]]) OVER (...)` retrieves a value from an earlier **row in the ordered partition**. `LEAD` retrieves a later row. Offset defaults to 1. The optional default is used when the requested row **does not exist**; it does **not** replace a NULL value stored in an existing row. Both functions retain input row grain.

**Portable SQL:** `LAG`, `LEAD`, `OVER`, `PARTITION BY`, and `ORDER BY` are broadly supported across major analytical SQL engines; availability and syntax should be checked for each vendor/version. PostgreSQL 18 follows the SQL standard-style navigation syntax. PostgreSQL does not implement the standard `IGNORE NULLS` option for these functions; its behavior is equivalent to `RESPECT NULLS`. Other engines may offer additional NULL-handling syntax.

Always define an ordering key that uniquely identifies event sequence: `ORDER BY observed_at, event_id`. Ordering only by a nonunique timestamp makes the chosen predecessor ambiguous. `PARTITION BY service` prevents cross-service comparisons. Window `ORDER BY` does not guarantee output display order, so include a final `ORDER BY`.

**Important distinction:** `LAG` returns the previous *row*, not necessarily the previous minute or previous calendar day. A missing observation or delayed event can create a time gap. For strict interval comparison, first validate cadence or construct a calendar/time spine and join observations to it.

## 3. Guided example (15 minutes)

Scenario: two fictional ingestion services report a sequence of processed-record counts. Each row is a distinct observation; counts are point-in-time measurements, not cumulative counters. NULL means the measurement was unavailable, not zero.

| service | event_id | minute | records |
|---|---:|---:|---:|
| api | 1 | 09:00 | 100 |
| api | 2 | 09:05 | 130 |
| api | 3 | 09:10 | NULL |
| api | 4 | 09:15 | 125 |
| file | 5 | 09:00 | 50 |
| file | 6 | 09:05 | 50 |
| file | 7 | 09:10 | 80 |
| file | 8 | 09:20 | 70 |

The FILE service has no 09:15 observation. This is intentional: row-to-row navigation must not be mistaken for five-minute cadence validation.

```sql
WITH observations(service,event_id,observed_at,records) AS (
 VALUES
 ('api',1,TIMESTAMP '2026-01-01 09:00:00',100),
 ('api',2,TIMESTAMP '2026-01-01 09:05:00',130),
 ('api',3,TIMESTAMP '2026-01-01 09:10:00',NULL),
 ('api',4,TIMESTAMP '2026-01-01 09:15:00',125),
 ('file',5,TIMESTAMP '2026-01-01 09:00:00',50),
 ('file',6,TIMESTAMP '2026-01-01 09:05:00',50),
 ('file',7,TIMESTAMP '2026-01-01 09:10:00',80),
 ('file',8,TIMESTAMP '2026-01-01 09:20:00',70)
), neighbors AS (
 SELECT service,event_id,observed_at,records,
        LAG(records) OVER w AS previous_records,
        LEAD(records) OVER w AS next_records,
        LAG(observed_at) OVER w AS previous_at
 FROM observations
 WINDOW w AS (PARTITION BY service ORDER BY observed_at,event_id)
)
SELECT service,event_id,records,previous_records,next_records,
       records - previous_records AS change_from_previous,
       CASE WHEN previous_at IS NULL THEN NULL
            ELSE EXTRACT(EPOCH FROM (observed_at - previous_at))/60
       END AS minutes_since_previous
FROM neighbors
ORDER BY service,observed_at,event_id;
```

`WINDOW w AS (...)` is supported by PostgreSQL and several other platforms; for maximum portability, repeat the identical `OVER (PARTITION BY ... ORDER BY ...)` clause.

**Expected results (reasoned, not executed):**

| service | event_id | records | previous | next | change | minutes since previous |
|---|---:|---:|---:|---:|---:|---:|
| api | 1 | 100 | NULL | 130 | NULL | NULL |
| api | 2 | 130 | 100 | NULL | +30 | 5 |
| api | 3 | NULL | 130 | 125 | NULL | 5 |
| api | 4 | 125 | NULL | NULL | NULL | 5 |
| file | 5 | 50 | NULL | 50 | NULL | NULL |
| file | 6 | 50 | 50 | 80 | 0 | 5 |
| file | 7 | 80 | 50 | 70 | +30 | 5 |
| file | 8 | 70 | 80 | NULL | -10 | 10 |

A missing neighbor and an existing NULL neighbor can look identical when only the value is selected. To distinguish them, also navigate a non-nullable event ID: `LAG(event_id) OVER w` is NULL only when there is no previous row (assuming event_id itself is NOT NULL).

**Operational example:** An SRE investigating ingestion degradation might flag `change_from_previous < 0` *and* `minutes_since_previous = 5`. Here FILE event 8 has a decrease of 10 but a 10-minute gap, so it needs separate treatment. A count decrease alone is not evidence of dropped data.

## 4. Hands-on lab (20 minutes)

Open [073-lag-lead-change-analysis.sql](../labs/073-lag-lead-change-analysis.sql) and inspect the endpoint, role, database and SQL before execution. From the `sql-tutorials/labs` directory:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f 073-lag-lead-change-analysis.sql
```

1. Predict the previous/next record count for API events 2, 3, and 4; explain why event 4's previous count is NULL.
2. Execute the first result query and compare all eight rows to the table above.
3. Verify the only negative non-NULL delta is FILE event 8 (-10), and that its gap is 10 minutes.
4. Verify FILE event 6 has a zero delta, which is different from NULL.
5. Inspect the explicit acceptance query: it compares all eight rows in both directions using `EXCEPT ALL`, checks row counts, and fails closed on mismatch.
6. **Stretch:** Replace `LAG(records)` with `LAG(records,2)`. Predict API event 3's two-row predecessor (100), then restore the original expression.
7. **Stretch:** Add `LAG(event_id)` and distinguish first-row missing predecessors from existing NULL measurements.

The lab ends with `ROLLBACK` and does not create or modify tables. A failed assertion under `ON_ERROR_STOP=1` should cause a nonzero `psql` exit; record any failure without claiming success.

## 5. Troubleshooting and DBRE/SRE safeguards (5 minutes)

| Symptom | Likely cause | Safe response |
|---|---|---|
| Predecessor changes between runs | Nonunique ordering | Add a stable event ID tie-breaker |
| Delta unexpectedly NULL | First row or NULL current/previous measurement | Inspect both values and predecessor event ID |
| Unexpected cross-service comparison | Missing `PARTITION BY` | Partition by the correct business key |
| A ten-minute gap is treated as five | Previous row mistaken for previous interval | Compute timestamp difference; use a time spine if necessary |
| Wrong change direction | Subtracting current from previous | Define delta as current minus previous |
| Large window query sorts/spills | High cardinality or poor ordering/index support | Inspect approved staging plans and temp metrics; do not benchmark production without approval |

For change-data-capture, do not assume arrival order equals business event order. Agree on event-time, sequence-number, duplicate, and late-arrival rules. For counter resets or rollovers, negative deltas may be legitimate and require domain-specific handling. Querying `pg_stat_activity` or modifying production settings is **not** part of this exercise.

## 6. Review questions with answers (5 minutes)

**Q1. Does LAG return the previous minute?** No; it returns the previous row in the specified window ordering.

**Q2. Why is `PARTITION BY service` essential?** It prevents the last API observation from becoming the predecessor of the first FILE observation.

**Q3. What is the delta for API event 4?** NULL, because its existing predecessor (event 3) has an unknown record count.

**Q4. What is the delta for FILE event 6?** Zero: 50 minus 50.

**Q5. Why should a timestamp have an event-ID tie-breaker?** Equal timestamps otherwise make predecessor selection nondeterministic.

**Q6. Does the optional default argument replace a NULL in a previous row?** No; it is used for an out-of-range offset.

**Q7. How do you detect irregular cadence?** Compare current and previous timestamps and validate the expected interval.

## 7. References and validation

- [PostgreSQL 18 — Window functions](https://www.postgresql.org/docs/18/functions-window.html)
- [PostgreSQL 18 — SELECT and WINDOW clause](https://www.postgresql.org/docs/18/sql-select.html)
- [PostgreSQL 18 — Date/time functions and EXTRACT](https://www.postgresql.org/docs/18/functions-datetime.html)
- [Master TOC](../MASTER-TOC.md) · [Status tracker](../STATUS-TRACKER.md)

**Publication:** Chapter and lab authored for this learning path. **Editorial review:** pending independent review. **Static validation:** targeted manual reasoning of expected results and safety patterns; comprehensive automated SQL syntax and Markdown-link QA pending. **PostgreSQL 18 runtime validation:** pending; no SQL execution evidence has been collected. These are not interchangeable states.
