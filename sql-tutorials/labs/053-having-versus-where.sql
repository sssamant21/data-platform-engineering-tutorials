-- Chapter 053: HAVING versus WHERE
-- PostgreSQL 18 only; synthetic fixture; disposable isolated sql_tutorials database ONLY.
-- Independently verify host, port, credentials, database and isolation before running.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/053-having-versus-where.sql
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';

DO $guard$
BEGIN
  IF current_setting('server_version_num')::integer NOT BETWEEN 180000 AND 189999 THEN
    RAISE EXCEPTION 'Requires PostgreSQL 18.x; found %', current_setting('server_version');
  END IF;
  IF current_database() <> 'sql_tutorials' THEN
    RAISE EXCEPTION 'Unexpected database: %', current_database();
  END IF;
END
$guard$;

SELECT version() AS runtime_version_for_evidence;

CREATE TEMP TABLE ch053_payment_events (
  event_id integer PRIMARY KEY,
  region text,
  status text NOT NULL,
  amount numeric(12,2)
) ON COMMIT DROP;

INSERT INTO ch053_payment_events (event_id, region, status, amount) VALUES
  (1,'East','captured',10.00),
  (2,'East','captured',20.00),
  (3,'East','pending',NULL),
  (4,'West','captured',30.00),
  (5,'West','refunded',-5.00),
  (6,'West','captured',15.00),
  (7,NULL,'captured',8.00),
  (8,'North','captured',50.00),
  (9,'North','pending',5.00),
  (10,'North','captured',10.00);

-- WHERE selects rows before GROUP BY; HAVING filters resulting groups.
-- Expected: North 2 / 60.00, West 2 / 45.00.
SELECT region, COUNT(*) AS captured_events, SUM(amount) AS captured_amount
FROM ch053_payment_events
WHERE status = 'captured'
GROUP BY region
HAVING COUNT(*) >= 2 AND SUM(amount) >= 40.00
ORDER BY region;

-- Without WHERE, the group sums include pending and refunded rows.
-- Expected: East 3/30, North 3/65, West 3/40.
SELECT region, COUNT(*) AS all_events, SUM(amount) AS all_status_net
FROM ch053_payment_events
GROUP BY region
HAVING COUNT(*) >= 2
ORDER BY region;

-- Conditional aggregation retains all-status denominator.
SELECT region, COUNT(*) AS all_events,
       SUM(CASE WHEN status = 'captured' THEN 1 ELSE 0 END) AS captured_events,
       SUM(CASE WHEN status = 'captured' THEN amount ELSE 0 END) AS captured_amount
FROM ch053_payment_events
GROUP BY region
HAVING SUM(CASE WHEN status = 'captured' THEN 1 ELSE 0 END) >= 2
ORDER BY region;

-- Pending East sum must be NULL; North pending sum is 5.00.
SELECT region, COUNT(*) AS events, COUNT(amount) AS known_amounts,
       SUM(amount) AS pending_amount
FROM ch053_payment_events
WHERE status = 'pending'
GROUP BY region
ORDER BY region;

DO $checks$
DECLARE
  src record;
  captured record;
  final_report record;
  pending_east record;
  all_status record;
BEGIN
  SELECT COUNT(*) AS n, COUNT(amount) AS known, SUM(amount) AS net
  INTO src FROM ch053_payment_events;
  IF src.n IS DISTINCT FROM 10 OR src.known IS DISTINCT FROM 9
     OR src.net IS DISTINCT FROM 143.00 THEN
    RAISE EXCEPTION 'Source assertion failed: %', row_to_json(src);
  END IF;

  SELECT COUNT(*) AS n, SUM(amount) AS net,
         COUNT(DISTINCT region) AS named_regions,
         COUNT(*) FILTER (WHERE region IS NULL) AS missing_region_events
  INTO captured FROM ch053_payment_events WHERE status = 'captured';
  IF captured.n IS DISTINCT FROM 7 OR captured.net IS DISTINCT FROM 143.00
     OR captured.named_regions IS DISTINCT FROM 3
     OR captured.missing_region_events IS DISTINCT FROM 1 THEN
    RAISE EXCEPTION 'Captured population assertion failed: %', row_to_json(captured);
  END IF;

  SELECT COUNT(*) AS groups_count,
         SUM(n) AS events,
         SUM(net) AS amount,
         MAX(net) FILTER (WHERE region = 'North') AS north_net,
         MAX(net) FILTER (WHERE region = 'West') AS west_net,
         MAX(n) FILTER (WHERE region = 'North') AS north_n,
         MAX(n) FILTER (WHERE region = 'West') AS west_n
  INTO final_report
  FROM (
    SELECT region, COUNT(*) AS n, SUM(amount) AS net
    FROM ch053_payment_events
    WHERE status = 'captured'
    GROUP BY region
    HAVING COUNT(*) >= 2 AND SUM(amount) >= 40.00
  ) AS qualifying;
  IF final_report.groups_count IS DISTINCT FROM 2
     OR final_report.events IS DISTINCT FROM 4
     OR final_report.amount IS DISTINCT FROM 105.00
     OR final_report.north_net IS DISTINCT FROM 60.00
     OR final_report.west_net IS DISTINCT FROM 45.00
     OR final_report.north_n IS DISTINCT FROM 2
     OR final_report.west_n IS DISTINCT FROM 2
     OR (captured.net - final_report.amount) IS DISTINCT FROM 38.00 THEN
    RAISE EXCEPTION 'HAVING report assertion failed: %', row_to_json(final_report);
  END IF;

  SELECT COUNT(*) AS n, COUNT(amount) AS known, SUM(amount) AS net
  INTO pending_east FROM ch053_payment_events
  WHERE region = 'East' AND status = 'pending';
  IF pending_east.n IS DISTINCT FROM 1
     OR pending_east.known IS DISTINCT FROM 0
     OR pending_east.net IS NOT NULL THEN
    RAISE EXCEPTION 'Pending NULL assertion failed: %', row_to_json(pending_east);
  END IF;

  SELECT COUNT(*) AS groups_count,
         MAX(net) FILTER (WHERE region = 'East') AS east_net,
         MAX(net) FILTER (WHERE region = 'North') AS north_net,
         MAX(net) FILTER (WHERE region = 'West') AS west_net
  INTO all_status
  FROM (
    SELECT region, COUNT(*) AS n, SUM(amount) AS net
    FROM ch053_payment_events GROUP BY region HAVING COUNT(*) >= 2
  ) AS g;
  IF all_status.groups_count IS DISTINCT FROM 3
     OR all_status.east_net IS DISTINCT FROM 30.00
     OR all_status.north_net IS DISTINCT FROM 65.00
     OR all_status.west_net IS DISTINCT FROM 40.00 THEN
    RAISE EXCEPTION 'All-status grouping assertion failed: %', row_to_json(all_status);
  END IF;

  RAISE NOTICE 'Chapter 053 deterministic assertions passed (expected, not independently runtime-certified)';
END
$checks$;

ROLLBACK;
-- psql exit code 0 is expected only when all checks pass. No persistent tables created.
