-- Chapter 113: ELT, incremental loads and CDC patterns
-- Synthetic, read-only simulation. No source connection, DDL, writes or checkpoint updates.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/113-elt-incremental-loads-cdc-patterns.sql
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';
DO $guard$
BEGIN
 IF current_database() <> 'sql_tutorials' THEN
   RAISE EXCEPTION 'Disposable sql_tutorials database required, got %', current_database();
 END IF;
 IF current_setting('server_version_num')::integer NOT BETWEEN 180000 AND 189999 THEN
   RAISE EXCEPTION 'PostgreSQL 18 required, got %', current_setting('server_version');
 END IF;
END
$guard$;

-- Observe the latest unique event per key, including the delete.
WITH events(cursor_no,event_id,order_id,op,amount) AS (
 VALUES (101,'e101',10,'U',55.00::numeric),
        (102,'e102',30,'I',20.00::numeric),
        (103,'e103',20,'D',NULL::numeric),
        (104,'e104',10,'U',60.00::numeric),
        (104,'e104',10,'U',60.00::numeric)
), dedup AS (
 SELECT DISTINCT * FROM events
), ranked AS (
 SELECT *,row_number() OVER(PARTITION BY order_id ORDER BY cursor_no DESC,event_id DESC) AS rn
 FROM dedup
)
SELECT order_id,op,amount,cursor_no FROM ranked WHERE rn=1 ORDER BY order_id;

-- Fail closed on wrong totals, missing tombstones or mismatched key-level result.
DO $assert$
DECLARE delivered integer; unique_events integer; latest_keys integer;
        active_keys integer; active_total numeric; deletes integer; diffs integer;
BEGIN
 WITH events(cursor_no,event_id,order_id,op,amount) AS (
  VALUES (101,'e101',10,'U',55.00::numeric),
         (102,'e102',30,'I',20.00::numeric),
         (103,'e103',20,'D',NULL::numeric),
         (104,'e104',10,'U',60.00::numeric),
         (104,'e104',10,'U',60.00::numeric)
 ), dedup AS (SELECT DISTINCT * FROM events),
 ranked AS (
   SELECT *,row_number() OVER(PARTITION BY order_id ORDER BY cursor_no DESC,event_id DESC) AS rn
   FROM dedup
 ), latest AS (SELECT order_id,op,amount FROM ranked WHERE rn=1),
 active AS (SELECT order_id,amount FROM latest WHERE op <> 'D'),
 expected(order_id,amount) AS (VALUES (10,60.00::numeric),(30,20.00::numeric)),
 mismatch AS (
  (SELECT * FROM active EXCEPT ALL SELECT * FROM expected)
  UNION ALL
  (SELECT * FROM expected EXCEPT ALL SELECT * FROM active)
 )
 SELECT (SELECT count(*) FROM events),
        (SELECT count(*) FROM dedup),
        (SELECT count(*) FROM latest),
        (SELECT count(*) FROM active),
        (SELECT sum(amount) FROM active),
        (SELECT count(*) FROM latest WHERE op='D'),
        (SELECT count(*) FROM mismatch)
 INTO delivered,unique_events,latest_keys,active_keys,active_total,deletes,diffs;
 IF (delivered,unique_events,latest_keys,active_keys,active_total,deletes,diffs)
   IS DISTINCT FROM (5,4,3,2,80.00::numeric,1,0) THEN
   RAISE EXCEPTION 'Chapter 113 assertion failed: delivered %, unique %, latest %, active %, total %, deletes %, diffs %',
     delivered,unique_events,latest_keys,active_keys,active_total,deletes,diffs;
 END IF;
 RAISE NOTICE 'Chapter 113 synthetic assertions passed: 5 deliveries, 4 unique events, 3 latest keys, 2 active orders, 80.00 total, 1 tombstone, 0 mismatches';
END
$assert$;
ROLLBACK;
