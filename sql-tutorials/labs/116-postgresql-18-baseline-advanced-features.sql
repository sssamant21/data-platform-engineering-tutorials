-- Chapter 116: PostgreSQL 18 lab baseline and advanced SQL
-- Synthetic CTEs only. Disposable PostgreSQL 18 database named sql_tutorials.
-- Run: psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/116-postgresql-18-baseline-advanced-features.sql
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';

DO $guard$
BEGIN
 IF current_database() <> 'sql_tutorials' THEN
   RAISE EXCEPTION 'Disposable database sql_tutorials required; got %', current_database();
 END IF;
 IF current_setting('server_version_num')::integer NOT BETWEEN 180000 AND 189999 THEN
   RAISE EXCEPTION 'PostgreSQL 18 required; got %', current_setting('server_version');
 END IF;
END
$guard$;

-- Latest events: (101,U,30), (102,D,NULL), (103,U,40).
WITH events(order_id,event_seq,event_id,operation,payload) AS (
 VALUES (101,1,1001,'U','{"amount":20}'::jsonb),
        (102,1,1002,'U','{"amount":50}'::jsonb),
        (101,2,1003,'U','{"amount":30}'::jsonb),
        (103,1,1004,'U','{"amount":40}'::jsonb),
        (102,2,1005,'D','{}'::jsonb)
)
SELECT DISTINCT ON (order_id) order_id, event_seq, operation,
       payload ->> 'amount' AS amount_text
FROM events ORDER BY order_id,event_seq DESC,event_id DESC;

-- PostgreSQL set-returning function: 1, 2, 3.
SELECT generate_series(1,3) AS synthetic_day;

-- Fail closed: compare DISTINCT ON, ROW_NUMBER and exact expected rows, including multiplicity.
DO $assert$
DECLARE
  delivered integer; latest_keys integer; active_keys integer;
  tombstones integer; active_total numeric; generated integer;
  mismatch_count integer;
BEGIN
 WITH events(order_id,event_seq,event_id,operation,payload) AS (
   VALUES (101,1,1001,'U','{"amount":20}'::jsonb),
          (102,1,1002,'U','{"amount":50}'::jsonb),
          (101,2,1003,'U','{"amount":30}'::jsonb),
          (103,1,1004,'U','{"amount":40}'::jsonb),
          (102,2,1005,'D','{}'::jsonb)
 ), latest AS (
   SELECT DISTINCT ON (order_id) order_id,event_seq,operation,payload
   FROM events ORDER BY order_id,event_seq DESC,event_id DESC
 ), ranked AS (
   SELECT order_id,event_seq,operation,payload,
          ROW_NUMBER() OVER (PARTITION BY order_id
                             ORDER BY event_seq DESC,event_id DESC) AS rn
   FROM events
 ), expected(order_id,event_seq,operation,amount_text) AS (
   VALUES (101,2,'U','30'),(102,2,'D',NULL::text),(103,1,'U','40')
 ), actual AS (
   SELECT order_id,event_seq,operation,payload ->> 'amount' AS amount_text FROM latest
 ), window_actual AS (
   SELECT order_id,event_seq,operation,payload ->> 'amount' AS amount_text
   FROM ranked WHERE rn=1
 ), differences AS (
   (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected)
   UNION ALL (SELECT * FROM expected EXCEPT ALL SELECT * FROM actual)
   UNION ALL (SELECT * FROM window_actual EXCEPT ALL SELECT * FROM expected)
   UNION ALL (SELECT * FROM expected EXCEPT ALL SELECT * FROM window_actual)
 )
 SELECT (SELECT COUNT(*) FROM events),
        (SELECT COUNT(*) FROM latest),
        (SELECT COUNT(*) FILTER (WHERE operation='U') FROM latest),
        (SELECT COUNT(*) FILTER (WHERE operation='D') FROM latest),
        (SELECT SUM((payload ->> 'amount')::numeric)
           FROM latest WHERE operation='U'),
        (SELECT COUNT(*) FROM generate_series(1,3)),
        (SELECT COUNT(*) FROM differences)
 INTO delivered,latest_keys,active_keys,tombstones,active_total,generated,mismatch_count;
 IF (delivered,latest_keys,active_keys,tombstones,active_total,generated,mismatch_count)
    IS DISTINCT FROM (5,3,2,1,70::numeric,3,0) THEN
   RAISE EXCEPTION 'Chapter 116 failed: events %, keys %, active %, tombstones %, total %, series %, mismatches %',
     delivered,latest_keys,active_keys,tombstones,active_total,generated,mismatch_count;
 END IF;
 RAISE NOTICE 'Chapter 116 assertions passed: 5 events, 3 keys, 2 active, 1 tombstone, total 70, series 3, mismatches 0';
END
$assert$;
ROLLBACK;
