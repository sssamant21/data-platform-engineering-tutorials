\set ON_ERROR_STOP on
\timing on
\echo '1. Index inventory'
SELECT c.relname, x.indisprimary, x.indisunique, x.indisvalid, pg_relation_size(c.oid) AS bytes, pg_get_indexdef(c.oid)
FROM pg_index x JOIN pg_class c ON c.oid=x.indexrelid WHERE x.indrelid='ch034.events'::regclass ORDER BY c.relname;
\echo '2. Statistics baseline'
SELECT stats_reset FROM pg_stat_database WHERE datname=current_database();
SELECT indexrelname, idx_scan, idx_tup_read, idx_tup_fetch FROM pg_stat_user_indexes WHERE relid='ch034.events'::regclass ORDER BY indexrelname;
EXPLAIN (ANALYZE, BUFFERS) SELECT id FROM ch034.events WHERE customer_id=42 ORDER BY occurred_at DESC LIMIT 20;
\echo '3. Bounded update and delete workload'
UPDATE ch034.events SET status='reopened', payload=payload || 'x' WHERE id BETWEEN 1 AND 20000;
DELETE FROM ch034.events WHERE id BETWEEN 20001 AND 30000;
SELECT pg_stat_clear_snapshot();
SELECT relname, n_live_tup, n_dead_tup, n_tup_upd, n_tup_hot_upd FROM pg_stat_user_tables WHERE relid='ch034.events'::regclass;
\echo '4. Maintenance'
VACUUM (ANALYZE) ch034.events;
SELECT pg_stat_clear_snapshot();
SELECT c.relname, pg_relation_size(c.oid) AS bytes FROM pg_index x JOIN pg_class c ON c.oid=x.indexrelid WHERE x.indrelid='ch034.events'::regclass ORDER BY c.relname;
\echo '5. Plans and statistics after maintenance'
EXPLAIN (ANALYZE, BUFFERS) SELECT id FROM ch034.events WHERE customer_id=42 ORDER BY occurred_at DESC LIMIT 20;
SELECT indexrelname, idx_scan, idx_tup_read, idx_tup_fetch FROM pg_stat_user_indexes WHERE relid='ch034.events'::regclass ORDER BY indexrelname;
\echo '6. Disposable-lab index retirement and restoration'
SELECT pg_get_indexdef('ch034.events_status_idx'::regclass) AS saved_definition;
DROP INDEX CONCURRENTLY ch034.events_status_idx;
CREATE INDEX CONCURRENTLY events_status_idx ON ch034.events (status);
SELECT c.relname, x.indisvalid, x.indisready FROM pg_index x JOIN pg_class c ON c.oid=x.indexrelid WHERE x.indrelid='ch034.events'::regclass ORDER BY c.relname;
