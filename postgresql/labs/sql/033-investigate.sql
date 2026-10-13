\set ON_ERROR_STOP on
\timing on
\echo '1. Baseline and initial query'
SELECT current_database() AS database_name, current_user AS operator;
EXPLAIN (ANALYZE, BUFFERS) SELECT id, amount FROM ch033.orders WHERE customer_id = 42 ORDER BY created_at DESC LIMIT 20;
\echo '2. Ordinary index build (write blocking risk)'
CREATE INDEX orders_customer_idx ON ch033.orders (customer_id);
\echo '3. Concurrent index build (standalone)'
CREATE INDEX CONCURRENTLY orders_created_idx ON ch033.orders (created_at);
\echo '4. Concurrent reindex (standalone)'
REINDEX INDEX CONCURRENTLY ch033.orders_created_idx;
\echo '5. Intentional UNIQUE concurrent failure: duplicate status values'
\set ON_ERROR_STOP off
CREATE UNIQUE INDEX CONCURRENTLY orders_status_unique_failure_idx ON ch033.orders (status);
\set ON_ERROR_STOP on
\echo '6. Inspect catalog after expected failure'
SELECT c.relname, x.indisvalid, x.indisready, x.indislive,
       pg_size_pretty(pg_relation_size(c.oid)) AS index_size
FROM pg_index x JOIN pg_class c ON c.oid = x.indexrelid
JOIN pg_class t ON t.oid = x.indrelid
WHERE t.oid = 'ch033.orders'::regclass ORDER BY c.relname;
\echo '7. Guarded cleanup: exact invalid lab index only'
SELECT CASE WHEN EXISTS (
  SELECT 1 FROM pg_index x
  JOIN pg_class c ON c.oid = x.indexrelid
  JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE n.nspname='ch033' AND c.relname='orders_status_unique_failure_idx'
    AND NOT x.indisvalid
) THEN 'DROP INDEX CONCURRENTLY ch033.orders_status_unique_failure_idx;'
ELSE 'SELECT ''No invalid failure index to remove'' AS cleanup;'
END AS cleanup_sql
\gexec
\echo '8. Verify remaining indexes and plan'
SELECT c.relname, x.indisvalid, x.indisready,
       pg_size_pretty(pg_relation_size(c.oid)) AS index_size
FROM pg_index x JOIN pg_class c ON c.oid=x.indexrelid
WHERE x.indrelid='ch033.orders'::regclass ORDER BY c.relname;
EXPLAIN (ANALYZE, BUFFERS) SELECT id, amount FROM ch033.orders WHERE customer_id=42 ORDER BY created_at DESC LIMIT 20;
