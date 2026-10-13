\set ON_ERROR_STOP on
SELECT current_setting('server_version') AS version;
SELECT name,setting,unit,context,source,pending_restart
FROM pg_settings WHERE name IN (
 'logging_collector','log_destination','log_line_prefix',
 'log_connections','log_disconnections','log_min_error_statement',
 'log_min_duration_statement','log_statement','log_lock_waits',
 'log_checkpoints','log_timezone','shared_preload_libraries'
) ORDER BY name;
SELECT extname,extversion FROM pg_extension WHERE extname='pgaudit';
SELECT name,setting,source FROM pg_settings WHERE name LIKE 'pgaudit.%' ORDER BY name;
SELECT ssl,version,cipher,bits FROM pg_stat_ssl WHERE pid=pg_backend_pid();
