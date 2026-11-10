-- Chapter 054 — Conditional aggregation with CASE and FILTER
-- PostgreSQL 18.x only; synthetic data; disposable isolated sql_tutorials database.
-- Verify endpoint, port, user and isolation OUTSIDE this script.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';

DO $guard$
BEGIN
  IF current_setting('server_version_num')::integer NOT BETWEEN 180000 AND 189999 THEN
    RAISE EXCEPTION 'Requires PostgreSQL 18.x; got %', current_setting('server_version');
  END IF;
  IF current_database() <> 'sql_tutorials' THEN
    RAISE EXCEPTION 'Unexpected database: %', current_database();
  END IF;
END
$guard$;
SELECT version() AS runtime_version_for_evidence;

CREATE TEMP TABLE ch054_payment_events (
 event_id integer PRIMARY KEY,
 region text,
 status text NOT NULL CHECK (status IN ('captured','refunded','pending')),
 amount numeric(12,2)
) ON COMMIT DROP;

INSERT INTO ch054_payment_events VALUES
(1,'East','captured',20.00),
(2,'East','captured',30.00),
(3,'East','refunded',-5.00),
(4,'East','pending',NULL),
(5,'West','captured',40.00),
(6,'West','refunded',-10.00),
(7,'West','pending',15.00),
(8,'North','captured',25.00),
(9,'North','captured',NULL),
(10,'North','pending',NULL),
(11,NULL,'captured',10.00),
(12,'South','pending',NULL);

-- Portable CASE: expected 5 groups, including NULL region.
SELECT region, COUNT(*) AS all_events,
       SUM(CASE WHEN status = 'captured' THEN 1 ELSE 0 END) AS captured_events,
       COUNT(CASE WHEN status = 'captured' THEN amount END) AS captured_known,
       COALESCE(SUM(CASE WHEN status = 'captured' THEN amount END),0) AS captured_amount,
       COALESCE(SUM(CASE WHEN status = 'refunded' THEN amount END),0) AS refunds
FROM ch054_payment_events GROUP BY region ORDER BY region NULLS LAST;

-- PostgreSQL FILTER: must agree with CASE for each region.
SELECT region, COUNT(*) AS all_events,
       COUNT(*) FILTER (WHERE status = 'captured') AS captured_events,
       COUNT(amount) FILTER (WHERE status = 'captured') AS captured_known,
       COALESCE(SUM(amount) FILTER (WHERE status = 'captured'),0) AS captured_amount,
       COALESCE(SUM(amount) FILTER (WHERE status = 'refunded'),0) AS refunds
FROM ch054_payment_events GROUP BY region ORDER BY region NULLS LAST;

DO $checks$
DECLARE r record;
BEGIN
 SELECT COUNT(*) AS events, COUNT(amount) AS known,
        COUNT(*) FILTER (WHERE status = 'captured') AS captured,
        COUNT(*) FILTER (WHERE status = 'refunded') AS refunded,
        COUNT(*) FILTER (WHERE status = 'pending') AS pending,
        COUNT(*) FILTER (WHERE status = 'captured' AND amount IS NULL) AS missing_captured,
        SUM(amount) FILTER (WHERE status = 'captured') AS captured_total,
        SUM(amount) FILTER (WHERE status = 'refunded') AS refunded_total,
        SUM(amount) FILTER (WHERE status = 'pending') AS pending_total,
        SUM(amount) AS all_total
 INTO r FROM ch054_payment_events;
 IF r.events IS DISTINCT FROM 12 OR r.known IS DISTINCT FROM 8
    OR r.captured IS DISTINCT FROM 6 OR r.refunded IS DISTINCT FROM 2
    OR r.pending IS DISTINCT FROM 4 OR r.missing_captured IS DISTINCT FROM 1
    OR r.captured_total IS DISTINCT FROM 125.00
    OR r.refunded_total IS DISTINCT FROM -15.00
    OR r.pending_total IS DISTINCT FROM 15.00
    OR r.all_total IS DISTINCT FROM 125.00 THEN
    RAISE EXCEPTION 'Source KPI mismatch: %', row_to_json(r);
 END IF;

 IF (SELECT COUNT(*) FROM (
   SELECT region FROM ch054_payment_events GROUP BY region
 ) g) IS DISTINCT FROM 5 THEN
   RAISE EXCEPTION 'Expected five region groups';
 END IF;

 IF EXISTS (
   WITH case_metrics AS (
     SELECT region, COUNT(*) AS n,
       SUM(CASE WHEN status='captured' THEN 1 ELSE 0 END) AS captured,
       COUNT(CASE WHEN status='captured' THEN amount END) AS known,
       COALESCE(SUM(CASE WHEN status='captured' THEN amount END),0) AS total
     FROM ch054_payment_events GROUP BY region
   ), filter_metrics AS (
     SELECT region, COUNT(*) AS n,
       COUNT(*) FILTER (WHERE status='captured') AS captured,
       COUNT(amount) FILTER (WHERE status='captured') AS known,
       COALESCE(SUM(amount) FILTER (WHERE status='captured'),0) AS total
     FROM ch054_payment_events GROUP BY region
   )
   SELECT 1 FROM case_metrics c FULL JOIN filter_metrics f
      ON c.region IS NOT DISTINCT FROM f.region
   WHERE c.n IS DISTINCT FROM f.n OR c.captured IS DISTINCT FROM f.captured
      OR c.known IS DISTINCT FROM f.known OR c.total IS DISTINCT FROM f.total
      OR c.n IS NULL OR f.n IS NULL
 ) THEN
   RAISE EXCEPTION 'CASE/FILTER parity mismatch';
 END IF;

 IF NOT EXISTS (
   SELECT 1 FROM ch054_payment_events GROUP BY region
   HAVING region = 'North'
      AND COUNT(*) FILTER (WHERE status='captured') = 2
      AND COUNT(amount) FILTER (WHERE status='captured') = 1
      AND SUM(amount) FILTER (WHERE status='captured') = 25.00
 ) THEN
   RAISE EXCEPTION 'North NULL-amount behavior mismatch';
 END IF;
 RAISE NOTICE 'Chapter 054 assertions passed (only if executed; not a certification claim)';
END
$checks$;
ROLLBACK;
-- Record invocation, isolated instance identity, PostgreSQL version, output and exit code for acceptance.
