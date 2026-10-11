-- PostgreSQL 18 read-only installation/directory metadata.
-- Use an approved settings reader. Restricted values may be hidden.
\set ON_ERROR_STOP on
\pset pager off
BEGIN READ ONLY;
SET LOCAL statement_timeout = '5s';
SET LOCAL lock_timeout = '1s';
SELECT clock_timestamp() AS observed_at, current_database(), current_user,
       inet_server_addr(), inet_server_port(),
       current_setting('server_version') AS server_version;
SELECT name, setting, unit, source, context, pending_restart
FROM pg_catalog.pg_settings
WHERE name IN ('data_directory','config_file','hba_file','ident_file',
              'logging_collector','log_destination','log_directory','log_filename',
              'shared_preload_libraries')
ORDER BY name;
SELECT spcname, pg_catalog.pg_get_userbyid(spcowner) AS owner,
       pg_catalog.pg_tablespace_location(oid) AS external_location
FROM pg_catalog.pg_tablespace
ORDER BY spcname LIMIT 30;
SELECT extname, extversion FROM pg_catalog.pg_extension ORDER BY extname LIMIT 30;
SELECT name, default_version, installed_version
FROM pg_catalog.pg_available_extensions ORDER BY name LIMIT 30;
COMMIT;
