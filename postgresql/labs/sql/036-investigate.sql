\set ON_ERROR_STOP on
\timing on
\echo '1. Baseline settings and XID ages'
SELECT name,setting,unit FROM pg_settings WHERE name IN ('autovacuum_vacuum_threshold','autovacuum_vacuum_scale_factor','autovacuum_freeze_max_age','autovacuum_multixact_freeze_max_age') ORDER BY name;
SELECT datname, age(datfrozenxid) AS xid_age, mxid_age(datminmxid) AS multixact_age FROM pg_database WHERE datname=current_database();
SELECT relname,n_live_tup,n_dead_tup,last_autovacuum FROM pg_stat_user_tables WHERE relid='ch036.events'::regclass;
\echo '2. Calculate illustrative thresholds'
SELECT 50 + 0.2 * 100000 AS default_example_trigger, 100 + 0.02 * 100000 AS lab_example_trigger;
SELECT reloptions FROM pg_class WHERE oid='ch036.events'::regclass;
ALTER TABLE ch036.events SET (autovacuum_vacuum_threshold=100,autovacuum_vacuum_scale_factor=0.02);
SELECT reloptions FROM pg_class WHERE oid='ch036.events'::regclass;
\echo '3. Controlled churn'
UPDATE ch036.events SET status='updated',payload=payload || 'x' WHERE id BETWEEN 1 AND 15000;
DELETE FROM ch036.events WHERE id BETWEEN 15001 AND 20000;
SELECT pg_stat_clear_snapshot();
SELECT relname,n_live_tup,n_dead_tup,n_tup_upd,n_tup_hot_upd FROM pg_stat_user_tables WHERE relid='ch036.events'::regclass;
\echo '4. Targeted maintenance'
VACUUM (ANALYZE) ch036.events;
SELECT pg_stat_clear_snapshot();
SELECT relname,n_live_tup,n_dead_tup,last_vacuum,last_autovacuum FROM pg_stat_user_tables WHERE relid='ch036.events'::regclass;
SELECT age(relfrozenxid) AS table_xid_age,mxid_age(relminmxid) AS table_multixact_age FROM pg_class WHERE oid='ch036.events'::regclass;
\echo '5. Read-only blockers and progress'
SELECT pid,state,xact_start,backend_xmin FROM pg_stat_activity WHERE xact_start IS NOT NULL ORDER BY xact_start LIMIT 10;
SELECT slot_name,slot_type,active,xmin,catalog_xmin FROM pg_replication_slots;
SELECT pid,relid::regclass,phase FROM pg_stat_progress_vacuum WHERE relid='ch036.events'::regclass;
\echo '6. Restore lab defaults'
ALTER TABLE ch036.events RESET (autovacuum_vacuum_threshold,autovacuum_vacuum_scale_factor);
SELECT reloptions FROM pg_class WHERE oid='ch036.events'::regclass;
