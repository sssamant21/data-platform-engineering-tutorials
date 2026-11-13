-- Chapter 120: PostgreSQL 18 synthetic, read-only capstone.
-- Run ONLY against disposable database sql_tutorials. No production credentials.
-- Calculated expected results; NOT evidence of actual runtime validation.
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';

DO $guard$
BEGIN
 IF current_database() <> 'sql_tutorials'
    OR current_setting('server_version_num')::integer NOT BETWEEN 180000 AND 189999
 THEN RAISE EXCEPTION 'Chapter 120 requires disposable sql_tutorials on PostgreSQL 18';
 END IF;
END
$guard$;

-- Repeated event_id 2 represents a delivery retry, not a second business change.
WITH deliveries(event_id,order_id,event_ts,operation,region,amount) AS (
 VALUES
 (1,701,'2026-01-01 09:00'::timestamp,'U','East',40.00::numeric(10,2)),
 (2,702,'2026-01-01 09:05'::timestamp,'U','West',20.00::numeric(10,2)),
 (2,702,'2026-01-01 09:05'::timestamp,'U','West',20.00::numeric(10,2)),
 (3,701,'2026-01-02 10:00'::timestamp,'U','East',55.00::numeric(10,2)),
 (4,703,'2026-01-02 11:00'::timestamp,'U','West',30.00::numeric(10,2)),
 (5,702,'2026-01-03 08:00'::timestamp,'D','West',NULL::numeric(10,2)),
 (6,704,'2026-01-03 09:00'::timestamp,'U','East',15.00::numeric(10,2))
), delivery_ranked AS (
 SELECT *,ROW_NUMBER() OVER (
  PARTITION BY event_id ORDER BY event_ts DESC,order_id DESC
 ) AS delivery_rn FROM deliveries
), unique_events AS (
 SELECT * FROM delivery_ranked WHERE delivery_rn=1
), state_ranked AS (
 SELECT *,ROW_NUMBER() OVER (
  PARTITION BY order_id ORDER BY event_ts DESC,event_id DESC
 ) AS state_rn FROM unique_events
), latest AS (
 SELECT * FROM state_ranked WHERE state_rn=1
), active AS (
 SELECT * FROM latest WHERE operation='U'
)
SELECT region,COUNT(*) AS active_orders,SUM(amount) AS revenue
FROM active GROUP BY region ORDER BY region;
-- Calculated: East 2 / 70.00; West 1 / 30.00.

DO $assert$
DECLARE mismatch_count integer;
BEGIN
 WITH deliveries(event_id,order_id,event_ts,operation,region,amount) AS (
  VALUES
  (1,701,'2026-01-01 09:00'::timestamp,'U','East',40.00::numeric(10,2)),
  (2,702,'2026-01-01 09:05'::timestamp,'U','West',20.00::numeric(10,2)),
  (2,702,'2026-01-01 09:05'::timestamp,'U','West',20.00::numeric(10,2)),
  (3,701,'2026-01-02 10:00'::timestamp,'U','East',55.00::numeric(10,2)),
  (4,703,'2026-01-02 11:00'::timestamp,'U','West',30.00::numeric(10,2)),
  (5,702,'2026-01-03 08:00'::timestamp,'D','West',NULL::numeric(10,2)),
  (6,704,'2026-01-03 09:00'::timestamp,'U','East',15.00::numeric(10,2))
 ), delivery_ranked AS (
  SELECT *,ROW_NUMBER() OVER (
   PARTITION BY event_id ORDER BY event_ts DESC,order_id DESC
  ) AS delivery_rn FROM deliveries
 ), unique_events AS (
  SELECT * FROM delivery_ranked WHERE delivery_rn=1
 ), state_ranked AS (
  SELECT *,ROW_NUMBER() OVER (
   PARTITION BY order_id ORDER BY event_ts DESC,event_id DESC
  ) AS state_rn FROM unique_events
 ), latest AS (
  SELECT * FROM state_ranked WHERE state_rn=1
 ), active AS (
  SELECT * FROM latest WHERE operation='U'
 ), regional AS (
  SELECT region,COUNT(*)::numeric AS n,SUM(amount) AS revenue
  FROM active GROUP BY region
 ), observed(metric,n) AS (
  SELECT 'deliveries'::text,COUNT(*)::numeric FROM deliveries
  UNION ALL SELECT 'unique_events',COUNT(*)::numeric FROM unique_events
  UNION ALL SELECT 'latest_orders',COUNT(*)::numeric FROM latest
  UNION ALL SELECT 'active_orders',COUNT(*)::numeric FROM active
  UNION ALL SELECT 'tombstones',COUNT(*)::numeric FROM latest WHERE operation='D'
  UNION ALL SELECT 'deleted_702',COUNT(*)::numeric FROM active WHERE order_id=702
  UNION ALL SELECT 'total_revenue',SUM(amount) FROM active
  UNION ALL SELECT 'east_orders',n FROM regional WHERE region='East'
  UNION ALL SELECT 'east_revenue',revenue FROM regional WHERE region='East'
  UNION ALL SELECT 'west_orders',n FROM regional WHERE region='West'
  UNION ALL SELECT 'west_revenue',revenue FROM regional WHERE region='West'
 ), expected(metric,n) AS (
  VALUES ('deliveries',7::numeric),('unique_events',6::numeric),
  ('latest_orders',4::numeric),('active_orders',3::numeric),
  ('tombstones',1::numeric),('deleted_702',0::numeric),
  ('total_revenue',100::numeric),('east_orders',2::numeric),
  ('east_revenue',70::numeric),('west_orders',1::numeric),
  ('west_revenue',30::numeric)
 ), differences AS (
  (SELECT * FROM observed EXCEPT ALL SELECT * FROM expected)
  UNION ALL
  (SELECT * FROM expected EXCEPT ALL SELECT * FROM observed)
 )
 SELECT COUNT(*) INTO mismatch_count FROM differences;
 IF mismatch_count <> 0 THEN
  RAISE EXCEPTION 'Chapter 120 assertions failed: % mismatches',mismatch_count;
 END IF;
 RAISE NOTICE 'Chapter 120 exact-result assertions matched: zero mismatches';
END
$assert$;
ROLLBACK;
