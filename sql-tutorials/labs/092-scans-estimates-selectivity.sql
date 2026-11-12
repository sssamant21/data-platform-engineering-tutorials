-- 092: Table scans, index scans, row estimates, and selectivity
-- Isolated PostgreSQL 18 only. Synthetic data; no persistent objects.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '15s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';

DO $guard$
BEGIN
 IF current_database() <> 'sql_tutorials' THEN
   RAISE EXCEPTION 'Expected isolated sql_tutorials database, found %', current_database();
 END IF;
 IF current_setting('server_version_num')::integer / 10000 <> 18 THEN
   RAISE EXCEPTION 'Expected PostgreSQL 18, found %', current_setting('server_version');
 END IF;
END
$guard$;

-- Estimated plan only; no ANALYZE and no table/index changes.
EXPLAIN (FORMAT TEXT, COSTS ON)
SELECT event_id, status
FROM (VALUES (1,'paid'),(2,'paid'),(3,'paid'),(4,'paid'),
             (5,'paid'),(6,'paid'),(7,'paid'),(8,'pending'),
             (9,'failed'),(10,'failed')) AS e(event_id,status)
WHERE status = 'pending';

-- Read-only practice: inspect deterministic status frequencies.
WITH events(event_id,status) AS (
 VALUES (1,'paid'),(2,'paid'),(3,'paid'),(4,'paid'),
        (5,'paid'),(6,'paid'),(7,'paid'),(8,'pending'),
        (9,'failed'),(10,'failed')
)
SELECT status, COUNT(*) AS matching_rows,
       COUNT(*)::numeric / (SELECT COUNT(*) FROM events) AS selectivity
FROM events GROUP BY status ORDER BY status;

-- Fail closed if the complete multiset differs (both directions).
DO $assert$
DECLARE discrepancy_count integer;
BEGIN
 WITH events(event_id,status) AS (
  VALUES (1,'paid'),(2,'paid'),(3,'paid'),(4,'paid'),
         (5,'paid'),(6,'paid'),(7,'paid'),(8,'pending'),
         (9,'failed'),(10,'failed')
 ), actual AS (
  SELECT status, COUNT(*)::bigint AS matching_rows,
         COUNT(*)::numeric / (SELECT COUNT(*) FROM events) AS selectivity
  FROM events GROUP BY status
 ), expected(status,matching_rows,selectivity) AS (
  VALUES ('failed',2::bigint,0.20::numeric),
         ('paid',7::bigint,0.70::numeric),
         ('pending',1::bigint,0.10::numeric)
 ), differences AS (
  (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected)
  UNION ALL
  (SELECT * FROM expected EXCEPT ALL SELECT * FROM actual)
 )
 SELECT COUNT(*) INTO discrepancy_count FROM differences;
 IF discrepancy_count <> 0 THEN
   RAISE EXCEPTION '092 selectivity assertion failed: % differences', discrepancy_count;
 END IF;
END
$assert$;
ROLLBACK;
