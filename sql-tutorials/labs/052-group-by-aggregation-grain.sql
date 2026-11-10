-- Chapter 052: GROUP BY and aggregation grain
-- PostgreSQL 18 only. Synthetic fixture. Disposable isolated sql_tutorials DB ONLY.
-- Confirm host, port, user, database, and isolation independently before running.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/052-group-by-aggregation-grain.sql
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

CREATE TEMP TABLE ch052_payment_events (
  payment_id integer PRIMARY KEY,
  region text,
  status text NOT NULL,
  amount numeric(12,2)
) ON COMMIT DROP;

INSERT INTO ch052_payment_events (payment_id,region,status,amount) VALUES
  (1,'East','captured',10.00),
  (2,'East','captured',20.00),
  (3,'East','pending',NULL),
  (4,'West','captured',30.00),
  (5,'West','refunded',-5.00),
  (6,'West','captured',15.00),
  (7,NULL,'captured',8.00);

-- Five groups; use NULLS LAST to make the display order explicit in PostgreSQL.
SELECT region, status, COUNT(*) AS event_count,
       COUNT(amount) AS known_amount_count, SUM(amount) AS net_amount
FROM ch052_payment_events
GROUP BY region, status
ORDER BY region NULLS LAST, status;

-- Three groups: East 3/30, West 3/40, NULL 1/8.
SELECT region, COUNT(*) AS event_count, SUM(amount) AS net_amount
FROM ch052_payment_events
GROUP BY region
ORDER BY region NULLS LAST;

-- Reconcile grouped output to raw source: 7 rows / 78.00.
SELECT SUM(group_events) AS reconciled_events,
       SUM(group_net) AS reconciled_net
FROM (
  SELECT region, status, COUNT(*) AS group_events, SUM(amount) AS group_net
  FROM ch052_payment_events
  GROUP BY region, status
) AS groups_by_key;

DO $checks$
DECLARE
  src record;
  grouped record;
  east_pending record;
  regions record;
BEGIN
  SELECT COUNT(*) AS n, COUNT(amount) AS known,
         COUNT(*) - COUNT(amount) AS missing,
         SUM(amount) AS net,
         COUNT(*) FILTER (WHERE region IS NULL) AS missing_region
  INTO src FROM ch052_payment_events;
  IF src.n <> 7 OR src.known <> 6 OR src.missing <> 1
     OR src.net <> 78.00 OR src.missing_region <> 1 THEN
    RAISE EXCEPTION 'Source assertions failed: %', row_to_json(src);
  END IF;

  SELECT COUNT(*) AS groups_count,
         SUM(event_count) AS n, SUM(net_amount) AS net
  INTO grouped
  FROM (
    SELECT region, status, COUNT(*) AS event_count, SUM(amount) AS net_amount
    FROM ch052_payment_events GROUP BY region, status
  ) AS g;
  IF grouped.groups_count <> 5 OR grouped.n <> 7 OR grouped.net <> 78.00 THEN
    RAISE EXCEPTION 'Grouped reconciliation failed: %', row_to_json(grouped);
  END IF;

  SELECT COUNT(*) AS n, COUNT(amount) AS known, SUM(amount) AS net
  INTO east_pending FROM ch052_payment_events
  WHERE region = 'East' AND status = 'pending';
  IF east_pending.n <> 1 OR east_pending.known <> 0 OR east_pending.net IS NOT NULL THEN
    RAISE EXCEPTION 'East pending NULL behavior failed: %', row_to_json(east_pending);
  END IF;

  SELECT COUNT(*) AS groups_count,
         SUM(n) AS n, SUM(net) AS net,
         MAX(net) FILTER (WHERE region = 'East') AS east_net,
         MAX(net) FILTER (WHERE region = 'West') AS west_net,
         MAX(net) FILTER (WHERE region IS NULL) AS unassigned_net
  INTO regions
  FROM (
    SELECT region, COUNT(*) AS n, SUM(amount) AS net
    FROM ch052_payment_events GROUP BY region
  ) AS r;
  IF regions.groups_count <> 3 OR regions.n <> 7 OR regions.net <> 78.00
     OR regions.east_net <> 30.00 OR regions.west_net <> 40.00
     OR regions.unassigned_net <> 8.00 THEN
    RAISE EXCEPTION 'Region-grain assertions failed: %', row_to_json(regions);
  END IF;

  RAISE NOTICE 'Chapter 052 deterministic assertions passed';
END
$checks$;

ROLLBACK;
-- Expected exit status 0 only if all assertions pass; no persistent table remains.
