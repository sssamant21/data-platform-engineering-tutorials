\set ON_ERROR_STOP on
SELECT pg_is_in_recovery() AS in_recovery,current_setting('server_version') AS version,
 current_setting('primary_conninfo') <> '' AS primary_conninfo_configured,
 current_setting('wal_log_hints') AS wal_log_hints,
 current_setting('full_page_writes') AS full_page_writes;
SELECT pg_last_wal_receive_lsn() AS receive_lsn,
 pg_last_wal_replay_lsn() AS replay_lsn,
 pg_wal_lsn_diff(pg_last_wal_receive_lsn(),pg_last_wal_replay_lsn()) AS receive_replay_gap_bytes,
 pg_last_xact_replay_timestamp() AS last_replayed_commit;
SELECT status,latest_end_lsn,latest_end_time,sender_host,slot_name FROM pg_stat_wal_receiver;
