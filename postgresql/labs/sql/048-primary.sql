\set ON_ERROR_STOP on
SELECT pg_is_in_recovery() AS in_recovery,current_setting('server_version') AS version;
SELECT pid,application_name,client_addr,state,sync_state,
 sent_lsn,write_lsn,flush_lsn,replay_lsn,
 pg_wal_lsn_diff(pg_current_wal_lsn(),sent_lsn) AS unsent_bytes,
 pg_wal_lsn_diff(sent_lsn,write_lsn) AS transport_write_gap_bytes,
 pg_wal_lsn_diff(write_lsn,flush_lsn) AS unflushed_bytes,
 pg_wal_lsn_diff(flush_lsn,replay_lsn) AS replay_gap_bytes,
 write_lag,flush_lag,replay_lag
FROM pg_stat_replication;
SELECT slot_name,slot_type,active,restart_lsn,wal_status,safe_wal_size FROM pg_replication_slots;
SELECT archived_count,failed_count,last_archived_time,last_failed_time FROM pg_stat_archiver;
