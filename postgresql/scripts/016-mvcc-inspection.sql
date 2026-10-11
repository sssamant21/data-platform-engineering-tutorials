-- PG18, ops_lab as lab_observer (pg_monitor) or lab_admin.
-- Read-only evidence: no query text, transaction cancellation or ID allocation.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout='5s';
SET LOCAL lock_timeout='1s';
SELECT clock_timestamp() AS observed_at,current_database(),current_user,
       inet_server_addr(),inet_server_port(),pg_is_in_recovery(),
       pg_current_xact_id_if_assigned() AS observer_xid_if_assigned;
WITH snapshot AS (SELECT pg_current_snapshot() AS s)
SELECT s::text AS snapshot,pg_snapshot_xmin(s) AS xmin,
       pg_snapshot_xmax(s) AS xmax
FROM snapshot;
SELECT pid,application_name,state,wait_event_type,wait_event,
       backend_xid,backend_xmin,age(backend_xmin) AS xmin_age_xids,
       clock_timestamp()-xact_start AS transaction_age,
       pg_blocking_pids(pid) AS blocking_pids
FROM pg_stat_activity
WHERE datname=current_database()
  AND application_name IN ('chapter016-reader','chapter016-writer','chapter016-observer')
  AND pid <> pg_backend_pid()
ORDER BY xact_start NULLS LAST,pid;
SELECT id,value,payload,xmin::text AS tuple_xmin,xmax::text AS tuple_xmax,
       ctid::text AS tuple_location
FROM c016_mvcc.probe ORDER BY id;
SELECT schemaname,relname,n_live_tup,n_dead_tup,n_tup_upd,n_tup_hot_upd,
       last_vacuum,last_autovacuum,last_analyze
FROM pg_stat_user_tables WHERE schemaname='c016_mvcc';
SELECT count(*) AS replication_slot_count FROM pg_replication_slots;
SELECT slot_name,slot_type,active,xmin,catalog_xmin
FROM pg_replication_slots ORDER BY slot_name LIMIT 20;
SELECT count(*) AS prepared_transaction_count FROM pg_prepared_xacts;
SELECT transaction,prepared,owner,database
FROM pg_prepared_xacts WHERE database=current_database()
ORDER BY prepared LIMIT 20;
COMMIT;
