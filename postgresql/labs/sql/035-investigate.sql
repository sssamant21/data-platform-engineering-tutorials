\set ON_ERROR_STOP on
\timing on
\echo '1. Baseline'
SELECT current_database(), now() AS observed_at;
SELECT stats_reset FROM pg_stat_database WHERE datname=current_database();
SELECT relname, n_live_tup, n_dead_tup, last_vacuum, last_autovacuum FROM pg_stat_user_tables WHERE relid='ch035.events'::regclass;
SELECT pg_relation_size('ch035.events'::regclass) AS heap_bytes, pg_indexes_size('ch035.events'::regclass) AS indexes_bytes;
\echo '2. Autovacuum settings and lab-only per-table override'
SELECT name,setting,unit,source FROM pg_settings WHERE name IN ('autovacuum','autovacuum_vacuum_threshold','autovacuum_vacuum_scale_factor','autovacuum_freeze_max_age') ORDER BY name;
ALTER TABLE ch035.events SET (autovacuum_vacuum_scale_factor=0.02, autovacuum_vacuum_threshold=1000);
SELECT reloptions FROM pg_class WHERE oid='ch035.events'::regclass;
\echo '3. Bounded churn'
UPDATE ch035.events SET status='updated', payload=payload || 'x' WHERE id BETWEEN 1 AND 20000;
DELETE FROM ch035.events WHERE id BETWEEN 20001 AND 30000;
SELECT pg_stat_clear_snapshot();
SELECT relname,n_live_tup,n_dead_tup,n_tup_upd,n_tup_hot_upd FROM pg_stat_user_tables WHERE relid='ch035.events'::regclass;
\echo '4. VACUUM progress snapshot (may be empty)'
SELECT pid, phase, heap_blks_total, heap_blks_scanned, index_vacuum_count FROM pg_stat_progress_vacuum WHERE relid='ch035.events'::regclass;
\echo '5. Targeted maintenance'
VACUUM (VERBOSE, ANALYZE, INDEX_CLEANUP AUTO) ch035.events;
SELECT pg_stat_clear_snapshot();
SELECT relname,n_live_tup,n_dead_tup,last_vacuum,last_autovacuum FROM pg_stat_user_tables WHERE relid='ch035.events'::regclass;
SELECT pg_relation_size('ch035.events'::regclass) AS heap_bytes, pg_indexes_size('ch035.events'::regclass) AS indexes_bytes;
\echo '6. Transaction age and lab setting rollback'
SELECT datname,age(datfrozenxid) AS xid_age,mxid_age(datminmxid) AS multixact_age FROM pg_database WHERE datname=current_database();
SELECT age(relfrozenxid) AS table_xid_age,mxid_age(relminmxid) AS table_multixact_age FROM pg_class WHERE oid='ch035.events'::regclass;
ALTER TABLE ch035.events RESET (autovacuum_vacuum_scale_factor, autovacuum_vacuum_threshold);
SELECT reloptions FROM pg_class WHERE oid='ch035.events'::regclass;
