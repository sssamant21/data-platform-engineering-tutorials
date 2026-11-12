-- Chapter 097: index-friendly predicates and safe rewrites
-- Synthetic read-only PostgreSQL 18 lab. No tables, indexes or DML.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/097-index-friendly-predicates-rewrites.sql
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '15s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';

DO $guard$
BEGIN
 IF current_database() <> 'sql_tutorials' THEN
  RAISE EXCEPTION 'Expected isolated sql_tutorials database; got %', current_database();
 END IF;
 IF current_setting('server_version_num')::integer / 10000 <> 18 THEN
  RAISE EXCEPTION 'Expected PostgreSQL 18; got %', current_setting('server_version');
 END IF;
END
$guard$;

-- Estimated plan only. Inline VALUES have no persistent index.
EXPLAIN (COSTS ON)
SELECT event_id
FROM (VALUES
 (1,TIMESTAMP '2026-11-09 23:59:59'),
 (2,TIMESTAMP '2026-11-10 00:00:00'),
 (3,TIMESTAMP '2026-11-10 12:00:00'),
 (4,TIMESTAMP '2026-11-10 23:59:59'),
 (5,TIMESTAMP '2026-11-11 00:00:00')
) AS e(event_id,event_at)
WHERE event_at >= TIMESTAMP '2026-11-10 00:00:00'
  AND event_at < TIMESTAMP '2026-11-11 00:00:00';

-- Expected: IDs 2,3,4; total 90.
WITH events(event_id,event_at,amount) AS (
 VALUES (1,TIMESTAMP '2026-11-09 23:59:59',10::numeric),
 (2,TIMESTAMP '2026-11-10 00:00:00',20::numeric),
 (3,TIMESTAMP '2026-11-10 12:00:00',30::numeric),
 (4,TIMESTAMP '2026-11-10 23:59:59',40::numeric),
 (5,TIMESTAMP '2026-11-11 00:00:00',50::numeric)
)
SELECT event_id,amount FROM events
WHERE event_at >= TIMESTAMP '2026-11-10 00:00:00'
AND event_at < TIMESTAMP '2026-11-11 00:00:00'
ORDER BY event_id;

DO $assert$
DECLARE n bigint;
BEGIN
 WITH events(event_id,event_at,amount) AS (
  VALUES (1,TIMESTAMP '2026-11-09 23:59:59',10::numeric),
  (2,TIMESTAMP '2026-11-10 00:00:00',20::numeric),
  (3,TIMESTAMP '2026-11-10 12:00:00',30::numeric),
  (4,TIMESTAMP '2026-11-10 23:59:59',40::numeric),
  (5,TIMESTAMP '2026-11-11 00:00:00',50::numeric)
 ), original AS (
  SELECT event_id,amount FROM events WHERE event_at::date = DATE '2026-11-10'
 ), rewritten AS (
  SELECT event_id,amount FROM events
  WHERE event_at >= TIMESTAMP '2026-11-10 00:00:00'
    AND event_at < TIMESTAMP '2026-11-11 00:00:00'
 ), expected(event_id,amount) AS (
  VALUES (2,20::numeric),(3,30::numeric),(4,40::numeric)
 ), differences AS (
  (SELECT * FROM original EXCEPT ALL SELECT * FROM rewritten)
  UNION ALL (SELECT * FROM rewritten EXCEPT ALL SELECT * FROM original)
  UNION ALL (SELECT * FROM rewritten EXCEPT ALL SELECT * FROM expected)
  UNION ALL (SELECT * FROM expected EXCEPT ALL SELECT * FROM rewritten)
 )
 SELECT count(*) INTO n FROM differences;
 IF n <> 0 THEN RAISE EXCEPTION '097 date rewrite mismatch: %',n; END IF;

 WITH emails(customer_id,email) AS (
  VALUES (1,'ALICE@example.test'),(2,'alice@example.test'),(3,'bob@example.test')
 ), actual AS (
  SELECT customer_id FROM emails WHERE lower(email) = 'alice@example.test'
 ), expected(customer_id) AS (VALUES (1),(2)),
 differences AS (
  (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected)
  UNION ALL (SELECT * FROM expected EXCEPT ALL SELECT * FROM actual)
 )
 SELECT count(*) INTO n FROM differences;
 IF n <> 0 THEN RAISE EXCEPTION '097 email mismatch: %',n; END IF;

 WITH amounts(event_id,amount) AS (
  VALUES (1,10::numeric),(2,20::numeric),(3,30::numeric),
         (4,40::numeric),(5,50::numeric),(6,NULL::numeric)
 ), original AS (
  SELECT event_id FROM amounts WHERE amount + 5 > 25
 ), rewritten AS (
  SELECT event_id FROM amounts WHERE amount > 20
 ), expected(event_id) AS (VALUES (3),(4),(5)),
 differences AS (
  (SELECT * FROM original EXCEPT ALL SELECT * FROM rewritten)
  UNION ALL (SELECT * FROM rewritten EXCEPT ALL SELECT * FROM original)
  UNION ALL (SELECT * FROM rewritten EXCEPT ALL SELECT * FROM expected)
  UNION ALL (SELECT * FROM expected EXCEPT ALL SELECT * FROM rewritten)
 )
 SELECT count(*) INTO n FROM differences;
 IF n <> 0 THEN RAISE EXCEPTION '097 numeric rewrite mismatch: %',n; END IF;
 RAISE NOTICE '097 synthetic equivalence and expected-result assertions passed';
END
$assert$;
ROLLBACK;
