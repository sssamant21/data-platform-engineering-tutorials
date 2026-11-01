-- PostgreSQL DBRE V04 -- READ-ONLY STAGING TRIAGE (NOT EXECUTED)
-- Intended for PostgreSQL 14-18 under approved monitoring credentials.
-- Use ONLY on an authorized staging instance. Confirm correct cluster identity.
-- Requires pg_read_all_stats or approved equivalent for full session visibility.
-- No SELECT pg_promote(), session termination, slot deletion or VACUUM.
-- SQL clients must use -X, ON_ERROR_STOP, a restricted role and encrypted connection.
-- On an overloaded instance, even these queries can consume resources.
-- Client tool should stop if identity/role/statement timeout do not match approval.

BEGIN READ ONLY;
SET LOCAL statement_timeout = '5s';

-- V04-Q01: identity, version and role; log as controlled evidence.
SELECT current_database() AS database_name,
       current_user AS monitoring_role,
       current_setting('server_version_num')::int AS server_version_num,
       pg_is_in_recovery() AS is_standby,
       (now() AT TIME ZONE 'UTC') AS sampled_utc;

-- V04-Q02: client count by state (not all backend processes).
SELECT datname, state, COUNT(*) AS clients
FROM pg_stat_activity
WHERE backend_type = 'client backend'
GROUP BY datname,state ORDER BY clients DESC;

-- V04-Q03: emergency connection capacity settings. reserved_connections
-- is NULL if unsupported (e.g. PostgreSQL 14/15).
SELECT current_setting('max_connections')::int AS max_connections,
       current_setting('superuser_reserved_connections')::int AS superuser_reserved,
       current_setting('reserved_connections',true) AS reserved_if_supported;

-- V04-Q04: current lock waiters and blocker PID mapping. Do not kill.
SELECT pid, datname, state, wait_event_type, wait_event,
       pg_blocking_pids(pid) AS blocker_pids
FROM pg_stat_activity
WHERE wait_event_type = 'Lock'
ORDER BY datname,pid LIMIT 50;

-- V04-Q05: long transactions, no potentially sensitive SQL text.
SELECT pid, datname, state, now()-xact_start AS xact_age,
       backend_type
FROM pg_stat_activity
WHERE xact_start IS NOT NULL
ORDER BY xact_start NULLS LAST LIMIT 50;

-- V04-Q06: deadlocks and counter reset; compare time windows.
SELECT datname,deadlocks,stats_reset
FROM pg_stat_database WHERE datname IS NOT NULL;

-- V04-Q07: replication sender metadata: meaningful on the primary only.
SELECT application_name,state,sync_state,
       sent_lsn,write_lsn,flush_lsn,replay_lsn,
       write_lag,flush_lag,replay_lag
FROM pg_stat_replication;

-- V04-Q08: slot risk; wal_status, safe_wal_size, xmin/catalog_xmin.
-- No pg_current_wal_lsn() here, to remain safe to query from standby.
SELECT slot_name,slot_type,active,wal_status,safe_wal_size,
       restart_lsn,xmin,catalog_xmin
FROM pg_replication_slots;

-- V04-Q09: archiver counters are not a complete PITR proof.
SELECT archived_count,last_archived_wal,last_archived_time,
       failed_count,last_failed_wal,last_failed_time,stats_reset
FROM pg_stat_archiver;

-- V04-Q10: active autovacuum and progress, relation OIDs scoped by datname.
SELECT pid,datname,relid AS relation_oid,phase,
       heap_blks_total,heap_blks_scanned
FROM pg_stat_progress_vacuum;

-- V04-Q11: database XID and multixact ages.
SELECT datname,age(datfrozenxid) AS xid_age,
       mxid_age(datminmxid) AS multixact_age
FROM pg_database ORDER BY xid_age DESC;

-- V04-Q12: relation-level age in CURRENT database ONLY.
-- Inspect table/TOAST relations; for other databases connect separately.
SELECT n.nspname,c.relname,c.relkind,
       age(c.relfrozenxid) AS xid_age,
       mxid_age(c.relminmxid) AS multixact_age
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE c.relkind IN ('r','m','t')
ORDER BY xid_age DESC LIMIT 50;

-- V04-Q13: current session/read-only transaction ends with no DML.
COMMIT;
