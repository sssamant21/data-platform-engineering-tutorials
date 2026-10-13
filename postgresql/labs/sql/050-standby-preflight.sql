\set ON_ERROR_STOP on
SELECT pg_is_in_recovery() AS in_recovery,current_setting('server_version') AS version;
SELECT system_identifier FROM pg_control_system();
SELECT pg_last_wal_receive_lsn() AS receive_lsn,
 pg_last_wal_replay_lsn() AS replay_lsn,
 pg_wal_lsn_diff(pg_last_wal_receive_lsn(),pg_last_wal_replay_lsn()) AS receive_replay_gap_bytes,
 pg_last_xact_replay_timestamp() AS last_replayed_commit;
SELECT status,latest_end_lsn,latest_end_time,sender_host,slot_name FROM pg_stat_wal_receiver;
SELECT datname,confl_lock,confl_snapshot,confl_bufferpin,confl_deadlock
FROM pg_stat_database_conflicts;
