-- PostgreSQL DBRE V08: read-only identity-gated staging diagnostics.
-- PG14-18; no user SQL text, rows, business IDs, credentials, hostnames.
-- DOES NOT prove WAL continuity, app recovery or old primary fencing.
BEGIN READ ONLY;
SET LOCAL statement_timeout = '5s';
SET LOCAL lock_timeout = '2s';

SELECT current_database() AS database_name, current_user AS monitoring_role,
       current_setting('server_version_num')::int AS pg_version,
       pg_is_in_recovery() AS is_standby,
       (now() AT TIME ZONE 'UTC') AS sampled_utc;

SELECT state, COUNT(*) AS client_backends
FROM pg_stat_activity WHERE backend_type = 'client backend'
GROUP BY state ORDER BY state;

SELECT COUNT(*) FILTER (WHERE wait_event_type='Lock') AS lock_waiters,
       COUNT(*) FILTER (WHERE xact_start IS NOT NULL
         AND now()-xact_start > INTERVAL '5 minutes') AS long_transactions
FROM pg_stat_activity WHERE backend_type = 'client backend';

SELECT COUNT(*) AS streaming_senders FROM pg_stat_replication
WHERE state='streaming';

SELECT COUNT(*) AS slots,
       COUNT(*) FILTER (WHERE active) AS active_slots,
       COUNT(*) FILTER (WHERE wal_status='lost') AS lost_slots
FROM pg_replication_slots;

SELECT COUNT(*) AS wal_receivers FROM pg_stat_wal_receiver;

SELECT archived_count,failed_count,stats_reset FROM pg_stat_archiver;

SELECT MAX(age(datfrozenxid)) AS max_xid_age,
       MAX(mxid_age(datminmxid)) AS max_multixact_age
FROM pg_database;

SELECT pg_database_size(current_database()) AS current_database_bytes;

COMMIT;
