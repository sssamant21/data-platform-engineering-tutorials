-- Chapter 073 read-only PostgreSQL 18 HA inspection
SELECT current_setting('server_version') AS version, pg_is_in_recovery() AS standby, clock_timestamp() AS inspected_at;
SELECT application_name,state,sync_state,sent_lsn,write_lsn,flush_lsn,replay_lsn FROM pg_stat_replication;
SELECT status,latest_end_lsn FROM pg_stat_wal_receiver;
SELECT slot_name,slot_type,active,restart_lsn,wal_status FROM pg_replication_slots;
SELECT archived_count,failed_count,last_failed_time FROM pg_stat_archiver;
