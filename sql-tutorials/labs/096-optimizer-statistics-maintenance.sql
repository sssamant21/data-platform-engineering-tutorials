-- Chapter 096: optimizer statistics and PostgreSQL maintenance basics
-- Synthetic, read-only demonstration. PostgreSQL 18 isolated database sql_tutorials only.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/096-optimizer-statistics-maintenance.sql
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '15s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';

DO $guard$
BEGIN
 IF current_database() <> 'sql_tutorials' THEN
  RAISE EXCEPTION 'Expected isolated sql_tutorials database, got %', current_database();
 END IF;
 IF current_setting('server_version_num')::integer / 10000 <> 18 THEN
  RAISE EXCEPTION 'Expected PostgreSQL 18, got %', current_setting('server_version');
 END IF;
END
$guard$;

-- Inline data have no physical indexes or stored table statistics.
EXPLAIN (COSTS ON)
SELECT order_id
FROM (VALUES
 (1,10,'paid'),(2,10,'paid'),(3,10,'paid'),(4,10,'pending'),
 (5,20,'pending'),(6,20,'pending'),(7,20,'pending'),(8,20,'paid')
) AS o(order_id,tenant_id,status)
WHERE tenant_id = 10 AND status = 'paid';

WITH orders(order_id,tenant_id,status) AS (
 VALUES (1,10,'paid'),(2,10,'paid'),(3,10,'paid'),(4,10,'pending'),
        (5,20,'pending'),(6,20,'pending'),(7,20,'pending'),(8,20,'paid')
)
SELECT COUNT(*)::bigint AS total_rows,
 COUNT(*) FILTER (WHERE tenant_id=10)::bigint AS tenant_10,
 COUNT(*) FILTER (WHERE status='paid')::bigint AS paid,
 COUNT(*) FILTER (WHERE tenant_id=10 AND status='paid')::bigint AS tenant_10_paid,
 COUNT(*) FILTER (WHERE tenant_id=20 AND status='pending')::bigint AS tenant_20_pending,
 ROUND(100.0 * COUNT(*) FILTER (WHERE tenant_id=10 AND status='paid') / COUNT(*),1) AS joint_pct
FROM orders;

-- Existing catalog visibility depends on local database state; zero rows is normal.
SELECT schemaname, tablename, attname, null_frac, n_distinct
FROM pg_catalog.pg_stats
WHERE schemaname='public'
ORDER BY tablename,attname LIMIT 20;

SELECT schemaname, relname, n_live_tup, n_dead_tup,
 last_analyze, last_autoanalyze, last_autovacuum
FROM pg_catalog.pg_stat_all_tables
WHERE schemaname='public'
ORDER BY relname LIMIT 20;

-- Compare actual multiset with fixed expected values in BOTH directions.
DO $assert$
DECLARE discrepancy_count bigint;
BEGIN
 WITH orders(order_id,tenant_id,status) AS (
  VALUES (1,10,'paid'),(2,10,'paid'),(3,10,'paid'),(4,10,'pending'),
         (5,20,'pending'),(6,20,'pending'),(7,20,'pending'),(8,20,'paid')
 ), actual AS (
  SELECT COUNT(*)::bigint AS total_rows,
   COUNT(*) FILTER (WHERE tenant_id=10)::bigint AS tenant_10,
   COUNT(*) FILTER (WHERE status='paid')::bigint AS paid,
   COUNT(*) FILTER (WHERE tenant_id=10 AND status='paid')::bigint AS tenant_10_paid,
   COUNT(*) FILTER (WHERE tenant_id=20 AND status='pending')::bigint AS tenant_20_pending,
   ROUND(100.0 * COUNT(*) FILTER (WHERE tenant_id=10 AND status='paid') / COUNT(*),1) AS joint_pct
  FROM orders
 ), expected(total_rows,tenant_10,paid,tenant_10_paid,tenant_20_pending,joint_pct) AS (
  VALUES (8::bigint,4::bigint,4::bigint,3::bigint,3::bigint,37.5::numeric)
 ), differences AS (
  (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected)
  UNION ALL
  (SELECT * FROM expected EXCEPT ALL SELECT * FROM actual)
 )
 SELECT COUNT(*) INTO discrepancy_count FROM differences;
 IF discrepancy_count <> 0 THEN
  RAISE EXCEPTION '096 synthetic result mismatch: % differing rows', discrepancy_count;
 END IF;
 RAISE NOTICE '096 synthetic assertions passed in this execution';
END
$assert$;
ROLLBACK;
