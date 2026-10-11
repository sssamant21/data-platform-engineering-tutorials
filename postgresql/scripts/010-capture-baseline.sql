-- PostgreSQL 18. Fresh authenticated session; use psql -X -q.
-- Redirect stdout to CSV and keep stderr separate.
-- Collection time, endpoint and login identity belong in the evidence report.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '5s';
SET LOCAL lock_timeout = '1s';
\copy (SELECT name, setting, COALESCE(unit,'') AS unit, source, context, COALESCE(sourcefile,'') AS sourcefile, pending_restart, (current_setting('server_version_num')::integer / 10000)::text AS server_major, pg_is_in_recovery() AS is_in_recovery FROM pg_settings WHERE name IN ('data_directory','port','listen_addresses','shared_buffers','max_connections','work_mem','fsync','full_page_writes','synchronous_commit','wal_level','synchronous_standby_names','log_min_duration_statement') ORDER BY name) TO STDOUT WITH (FORMAT csv, HEADER true)
COMMIT;
