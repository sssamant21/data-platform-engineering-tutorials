\set ON_ERROR_STOP on
SELECT pg_is_in_recovery() AS in_recovery,
 pg_last_wal_receive_lsn() AS receive_lsn,
 pg_last_wal_replay_lsn() AS replay_lsn,
 pg_wal_lsn_diff(pg_last_wal_receive_lsn(),pg_last_wal_replay_lsn()) AS receive_replay_gap_bytes,
 pg_last_xact_replay_timestamp() AS last_replayed_commit_time;
SELECT status,receive_start_lsn,written_lsn,flushed_lsn,latest_end_lsn,
 latest_end_time,slot_name,sender_host,sender_port FROM pg_stat_wal_receiver;
SELECT datname,confl_tablespace,confl_lock,confl_snapshot,
 confl_bufferpin,confl_deadlock,confl_active_logicalslot FROM pg_stat_database_conflicts;
SELECT pid,usename,state,wait_event_type,wait_event,
 clock_timestamp()-query_start AS query_age,left(query,120) AS query_excerpt
FROM pg_stat_activity WHERE state='active' ORDER BY query_start LIMIT 20;
