-- Chapter 119: synthetic, read-only PostgreSQL 18 comparison lab.
-- Not a Snowflake or BigQuery execution/cost test.
-- Requires disposable PostgreSQL 18 database named sql_tutorials.
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';

DO $guard$
BEGIN
 IF current_database() <> 'sql_tutorials'
    OR current_setting('server_version_num')::integer NOT BETWEEN 180000 AND 189999
 THEN RAISE EXCEPTION 'Chapter 119 requires disposable sql_tutorials on PostgreSQL 18';
 END IF;
END
$guard$;

-- Latest event per order; rank deletes as well as updates.
WITH events(event_id,order_id,event_ts,operation,amount) AS (
 VALUES (1,501,'2026-01-01 09:00'::timestamp,'U',40.00::numeric(10,2)),
        (2,502,'2026-01-01 09:05'::timestamp,'U',20.00::numeric(10,2)),
        (3,501,'2026-01-01 10:00'::timestamp,'U',55.00::numeric(10,2)),
        (4,503,'2026-01-02 08:00'::timestamp,'U',30.00::numeric(10,2)),
        (5,502,'2026-01-02 09:00'::timestamp,'D',NULL::numeric(10,2)),
        (6,503,'2026-01-02 10:00'::timestamp,'U',35.00::numeric(10,2))
), ranked AS (
 SELECT *,ROW_NUMBER() OVER (
   PARTITION BY order_id ORDER BY event_ts DESC,event_id DESC
 ) AS rn FROM events
)
SELECT order_id,amount FROM ranked
WHERE rn=1 AND operation='U' ORDER BY order_id;
-- Calculated: 501/55.00; 503/35.00.

-- A deliberately wrong approach: filtering tombstones BEFORE ranking.
-- Demonstrates the resurrected order 502; never use as production CDC logic.
WITH events(event_id,order_id,event_ts,operation,amount) AS (
 VALUES (1,501,'2026-01-01 09:00'::timestamp,'U',40.00::numeric),
        (2,502,'2026-01-01 09:05'::timestamp,'U',20.00::numeric),
        (3,501,'2026-01-01 10:00'::timestamp,'U',55.00::numeric),
        (4,503,'2026-01-02 08:00'::timestamp,'U',30.00::numeric),
        (5,502,'2026-01-02 09:00'::timestamp,'D',NULL::numeric),
        (6,503,'2026-01-02 10:00'::timestamp,'U',35.00::numeric)
), ranked_wrong AS (
 SELECT *,ROW_NUMBER() OVER (
  PARTITION BY order_id ORDER BY event_ts DESC,event_id DESC
 ) AS rn FROM events WHERE operation='U'
)
SELECT order_id,amount FROM ranked_wrong WHERE rn=1 ORDER BY order_id;
-- Calculated WRONG result: 501/55.00, 502/20.00, 503/35.00.

-- Exact assertions compare multisets in both directions (EXCEPT ALL).
DO $assert$
DECLARE mismatch_count integer;
BEGIN
 WITH events(event_id,order_id,event_ts,operation,amount) AS (
  VALUES (1,501,'2026-01-01 09:00'::timestamp,'U',40.00::numeric(10,2)),
         (2,502,'2026-01-01 09:05'::timestamp,'U',20.00::numeric(10,2)),
         (3,501,'2026-01-01 10:00'::timestamp,'U',55.00::numeric(10,2)),
         (4,503,'2026-01-02 08:00'::timestamp,'U',30.00::numeric(10,2)),
         (5,502,'2026-01-02 09:00'::timestamp,'D',NULL::numeric(10,2)),
         (6,503,'2026-01-02 10:00'::timestamp,'U',35.00::numeric(10,2))
 ), ranked AS (
  SELECT *,ROW_NUMBER() OVER (
    PARTITION BY order_id ORDER BY event_ts DESC,event_id DESC
  ) AS rn FROM events
 ), latest AS (SELECT * FROM ranked WHERE rn=1),
 active AS (SELECT * FROM latest WHERE operation='U'),
 observed(metric,n) AS (
  SELECT 'delivered'::text,COUNT(*)::numeric FROM events
  UNION ALL SELECT 'keys',COUNT(DISTINCT order_id)::numeric FROM events
  UNION ALL SELECT 'latest',COUNT(*)::numeric FROM latest
  UNION ALL SELECT 'active',COUNT(*)::numeric FROM active
  UNION ALL SELECT 'active_total',SUM(amount) FROM active
  UNION ALL SELECT 'tombstones',COUNT(*)::numeric FROM latest WHERE operation='D'
  UNION ALL SELECT 'first_day',COUNT(*)::numeric FROM events
    WHERE event_ts >= '2026-01-01'::timestamp
      AND event_ts < '2026-01-02'::timestamp
  UNION ALL SELECT 'active_501',MAX(amount) FROM active WHERE order_id=501
  UNION ALL SELECT 'active_503',MAX(amount) FROM active WHERE order_id=503
  UNION ALL SELECT 'deleted_502',COUNT(*)::numeric FROM active WHERE order_id=502
 ), expected(metric,n) AS (
  VALUES ('delivered',6::numeric),('keys',3::numeric),
         ('latest',3::numeric),('active',2::numeric),
         ('active_total',90::numeric),('tombstones',1::numeric),
         ('first_day',3::numeric),('active_501',55::numeric),
         ('active_503',35::numeric),('deleted_502',0::numeric)
 ), differences AS (
  (SELECT * FROM observed EXCEPT ALL SELECT * FROM expected)
  UNION ALL
  (SELECT * FROM expected EXCEPT ALL SELECT * FROM observed)
 )
 SELECT COUNT(*) INTO mismatch_count FROM differences;
 IF mismatch_count <> 0 THEN
  RAISE EXCEPTION 'Chapter 119 assertions failed: % differences',mismatch_count;
 END IF;
 RAISE NOTICE 'Chapter 119 exact-result assertions matched: zero mismatches';
END
$assert$;
ROLLBACK;
