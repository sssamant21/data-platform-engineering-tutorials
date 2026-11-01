-- PostgreSQL DBRE V06: READ-ONLY BACKUP/HA/DR INVENTORY
-- Authoritative reference: PostgreSQL 14-18. NOT EXECUTED.
-- Staging-first and intended monitoring role only; no cluster changes.
-- BEGIN READ ONLY limits SQL mutation but still consumes connection/CPU.
-- This pack does NOT prove PITR, fencing, archive continuity, RPO or RTO.
-- Do NOT use these outputs alone to authorize failover or restore.
-- Run only on explicitly approved primary or standby as documented.
BEGIN READ ONLY;
SET LOCAL statement_timeout = '5s';

-- V06-Q01: exact role/version and UTC context.
SELECT current_database() AS database_name,
       current_user AS monitoring_role,
       current_setting('server_version_num')::int AS version_num,
       pg_is_in_recovery() AS standby_role,
       (now() AT TIME ZONE 'UTC') AS sampled_utc;

-- V06-Q02: WAL/archiving/retention parameters, no secret archive commands.
SELECT current_setting('wal_level') AS wal_level,
       current_setting('archive_mode') AS archive_mode,
       current_setting('archive_timeout') AS archive_timeout,
       current_setting('wal_log_hints') AS wal_log_hints,
       current_setting('full_page_writes') AS full_page_writes,
       current_setting('max_slot_wal_keep_size') AS slot_wal_limit;

-- V06-Q03: archive counters; missing segments/chain not proven here.
SELECT archived_count, last_archived_wal, last_archived_time,
       failed_count, last_failed_wal, last_failed_time, stats_reset
FROM pg_stat_archiver;

-- V06-Q04: sender stats, most meaningful on primary; may have zero rows.
SELECT application_name, state, sync_state,
       sent_lsn, write_lsn, flush_lsn, replay_lsn,
       write_lag, flush_lag, replay_lag
FROM pg_stat_replication;

-- V06-Q05: slot metadata; check consumers, retention and health separately.
SELECT slot_name, slot_type, active, restart_lsn,
       confirmed_flush_lsn, wal_status, safe_wal_size
FROM pg_replication_slots;

-- V06-Q06: standby receiver, exclude conninfo (sensitive endpoint details).
SELECT status, flushed_lsn, received_tli,
       latest_end_lsn, latest_end_time, slot_name
FROM pg_stat_wal_receiver;

-- V06-Q07: standby replay LSN/timestamp, NULL on primary.
-- Timestamp can be old on an idle source and is NOT a business RPO.
SELECT pg_last_wal_receive_lsn() AS received_lsn,
       pg_last_wal_replay_lsn() AS replayed_lsn,
       pg_last_xact_replay_timestamp() AS latest_replayed_commit;

-- V06-Q08: cluster statistics, not evidence of single-writer fencing.
SELECT datname, xact_commit, xact_rollback, stats_reset
FROM pg_stat_database
WHERE datname = current_database();

COMMIT;
