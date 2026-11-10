-- Chapter 055: Date-based grouping and time buckets (PostgreSQL 18)
-- Run ONLY in an isolated disposable database named sql_tutorials, via psql -X -v ON_ERROR_STOP=1.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';
DO $guard$
BEGIN
 IF current_setting('server_version_num')::integer NOT BETWEEN 180000 AND 189999
 THEN RAISE EXCEPTION 'PostgreSQL 18.x required: %', current_setting('server_version'); END IF;
 IF current_database() <> 'sql_tutorials'
 THEN RAISE EXCEPTION 'Wrong database: %', current_database(); END IF;
END
$guard$;
SELECT current_database() AS isolated_database, version() AS runtime_version;
CREATE TEMP TABLE ch055_events (
 event_id integer PRIMARY KEY,
 occurred_at timestamptz NOT NULL,
 amount numeric(12,2) NOT NULL
) ON COMMIT DROP;
-- Instants around midnight and month boundaries, with explicit UTC offsets.
INSERT INTO ch055_events VALUES
 (1,'2026-01-31 23:30:00+00',10.00),
 (2,'2026-02-01 00:15:00+00',20.00),
 (3,'2026-02-01 12:00:00+00',30.00),
 (4,'2026-02-28 23:59:00+00',40.00),
 (5,'2026-03-01 00:00:00+00',50.00),
 (6,'2026-03-01 01:00:00+00',60.00);
-- Set a deterministic display/session zone for subsequent queries.
SET LOCAL TIME ZONE 'UTC';
-- PostgreSQL-specific date_trunc; UTC session makes buckets reproducible.
SELECT date_trunc('month', occurred_at) AS month_utc,
       COUNT(*) AS events, SUM(amount) AS total
FROM ch055_events GROUP BY 1 ORDER BY 1;
-- Portable-ish date extraction, but dialect return types and timezone behavior differ.
SELECT EXTRACT(YEAR FROM occurred_at) AS yr,
       EXTRACT(MONTH FROM occurred_at) AS mon,
       COUNT(*) AS events, SUM(amount) AS total
FROM ch055_events GROUP BY 1,2 ORDER BY 1,2;
-- Half-open UTC interval; suitable for an indexed timestamp predicate.
SELECT COUNT(*) AS feb_events, SUM(amount) AS feb_total
FROM ch055_events
WHERE occurred_at >= TIMESTAMPTZ '2026-02-01 00:00:00+00'
  AND occurred_at <  TIMESTAMPTZ '2026-03-01 00:00:00+00';
-- Same instant can fall on a different local date in another reporting timezone.
SELECT event_id, (occurred_at AT TIME ZONE 'America/New_York')::date AS ny_date
FROM ch055_events WHERE event_id IN (1,2,5) ORDER BY event_id;
-- Fail-closed checks: counts, sums, month boundaries, and timezone conversion.
DO $checks$
DECLARE r record;
BEGIN
 SELECT COUNT(*) AS n, SUM(amount) AS total INTO r FROM ch055_events;
 IF r.n IS DISTINCT FROM 6 OR r.total IS DISTINCT FROM 210.00 THEN
   RAISE EXCEPTION 'Source mismatch: %', row_to_json(r);
 END IF;
 IF EXISTS (
  WITH actual AS (
    SELECT date_trunc('month',occurred_at)::date AS month_start,
           COUNT(*) AS n, SUM(amount) AS total
    FROM ch055_events GROUP BY 1
  ), expected(month_start,n,total) AS (
    VALUES (DATE '2026-01-01',1::bigint,10.00::numeric),
           (DATE '2026-02-01',3::bigint,90.00::numeric),
           (DATE '2026-03-01',2::bigint,110.00::numeric)
  )
  (SELECT * FROM actual EXCEPT SELECT * FROM expected)
  UNION ALL
  (SELECT * FROM expected EXCEPT SELECT * FROM actual)
 ) THEN RAISE EXCEPTION 'Monthly bucket mismatch'; END IF;
 IF (SELECT COUNT(*) FROM ch055_events
      WHERE occurred_at >= TIMESTAMPTZ '2026-02-01 00:00+00'
        AND occurred_at < TIMESTAMPTZ '2026-03-01 00:00+00') <> 3
 THEN RAISE EXCEPTION 'February half-open range mismatch'; END IF;
 IF (SELECT (occurred_at AT TIME ZONE 'America/New_York')::date
     FROM ch055_events WHERE event_id=2) IS DISTINCT FROM DATE '2026-01-31'
 THEN RAISE EXCEPTION 'Timezone boundary mismatch'; END IF;
 RAISE NOTICE 'Chapter 055 assertions passed in this execution';
END
$checks$;
ROLLBACK;
-- Capture server version, isolated instance identity, psql command/output/exit status as evidence.
