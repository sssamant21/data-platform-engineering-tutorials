\set ON_ERROR_STOP on
\timing on
SELECT pg_relation_size('ch037.orders'::regclass) AS heap_bytes,
 pg_indexes_size('ch037.orders'::regclass) AS index_bytes;
SELECT relname,n_live_tup,n_dead_tup,last_vacuum,last_autovacuum
 FROM pg_stat_user_tables WHERE relid='ch037.orders'::regclass;
EXPLAIN (ANALYZE, BUFFERS)
 SELECT id FROM ch037.orders WHERE customer_id=42 ORDER BY created_at DESC LIMIT 10;
UPDATE ch037.orders SET status='updated' WHERE id BETWEEN 1 AND 20000;
DELETE FROM ch037.orders WHERE id BETWEEN 20001 AND 30000;
SELECT pg_stat_clear_snapshot();
SELECT n_live_tup,n_dead_tup FROM pg_stat_user_tables WHERE relid='ch037.orders'::regclass;
ANALYZE ch037.orders;
VACUUM (ANALYZE) ch037.orders;
SELECT pg_stat_clear_snapshot();
SELECT n_live_tup,n_dead_tup,last_vacuum FROM pg_stat_user_tables WHERE relid='ch037.orders'::regclass;
SELECT pg_relation_size('ch037.orders'::regclass) AS heap_bytes,
 pg_indexes_size('ch037.orders'::regclass) AS index_bytes;
SELECT datname,age(datfrozenxid) AS xid_age FROM pg_database WHERE datname=current_database();
