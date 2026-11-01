-- PostgreSQL DBRE V05: READ-ONLY STAGING CAPACITY INVENTORY
-- Reference: PostgreSQL 14-18; no extension dependencies.
-- Do NOT run on a busy production cluster without database-owner approval.
-- Use an approved monitoring role and a named database; record source, region
-- and cluster identity out-of-band. PG SQL DOES NOT give real cloud free disk.
-- pg_stat_wal cumulative WAL generated is not current pg_wal directory size.
-- Physical disk, backups and bills require provider/OS data collection.
BEGIN READ ONLY;
SET LOCAL statement_timeout = '8s';

-- V05-Q01: source/version and role (UTC label)
SELECT current_database() AS database_name,
       current_user AS monitoring_role,
       current_setting('server_version_num')::int AS pg_version_num,
       pg_is_in_recovery() AS is_standby,
       (now() AT TIME ZONE 'UTC') AS sample_utc;

-- V05-Q02: logical size for current database (includes table/index/TOAST).
SELECT oid AS database_oid, datname,
       pg_database_size(oid) AS database_bytes
FROM pg_database WHERE datname = current_database();

-- V05-Q03: representative table/partition LEAF and materialized-view sizes.
-- The top 50 selection avoids repeated size scans for a massive catalog.
-- Table_bytes includes TOAST; total = table_bytes + attached index_bytes.
WITH eligible AS MATERIALIZED (
  SELECT c.oid,c.relname,c.relkind,c.relispartition,n.nspname
  FROM pg_class AS c
  JOIN pg_namespace AS n ON n.oid = c.relnamespace
  WHERE c.relkind IN ('r','m')
    AND n.nspname NOT IN ('pg_catalog','information_schema')
  ORDER BY c.oid LIMIT 50
)
SELECT nspname AS schema_name,relname AS relation_name,
       oid AS relation_oid,relkind,relispartition,
       pg_table_size(oid) AS table_including_toast_bytes,
       pg_indexes_size(oid) AS attached_index_bytes,
       pg_total_relation_size(oid) AS table_total_bytes
FROM eligible ORDER BY table_total_bytes DESC;

-- V05-Q04: per-index MAIN FORK bytes only; index views are resettable.
SELECT schemaname,relname AS table_name,indexrelname AS index_name,
       indexrelid AS index_oid,
       pg_relation_size(indexrelid) AS index_main_fork_bytes,
       idx_scan
FROM pg_stat_user_indexes
ORDER BY index_main_fork_bytes DESC LIMIT 30;

-- V05-Q05: WAL generated as a cumulative counter, reset aware.
-- On a standby this is not a primary WAL production rate.
SELECT wal_bytes, stats_reset FROM pg_stat_wal;

-- V05-Q06: replication slots carry WAL retention exposure, not exact disk use.
SELECT slot_name,slot_type,active,restart_lsn,
       wal_status,safe_wal_size
FROM pg_replication_slots;

-- V05-Q07: counters for workload normalization.
SELECT datname,numbackends,xact_commit,xact_rollback,stats_reset
FROM pg_stat_database WHERE datname=current_database();

COMMIT;
