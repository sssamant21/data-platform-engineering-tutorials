-- PostgreSQL 18 configuration evidence; requires approved access to pg_file_settings.
\set ON_ERROR_STOP on
\pset pager off
BEGIN READ ONLY;
SET LOCAL statement_timeout = '5s';
SET LOCAL lock_timeout = '1s';
SELECT clock_timestamp() AS observed_at, current_database(), current_user,
       inet_server_port(), pg_postmaster_start_time(), pg_is_in_recovery();
SELECT name, setting, unit, context, source, reset_val,
       sourcefile, sourceline, pending_restart
FROM pg_catalog.pg_settings
WHERE name IN ('log_min_duration_statement','shared_buffers','work_mem')
ORDER BY name;
SELECT seqno, sourcefile, sourceline, name, setting, applied, error
FROM pg_catalog.pg_file_settings
WHERE name IN ('log_min_duration_statement','shared_buffers')
   OR error IS NOT NULL
ORDER BY seqno LIMIT 50;
SELECT COALESCE(d.datname,'all databases') AS database_scope,
       COALESCE(r.rolname,'all roles') AS role_scope, s.setconfig
FROM pg_catalog.pg_db_role_setting AS s
LEFT JOIN pg_catalog.pg_database AS d ON d.oid=s.setdatabase
LEFT JOIN pg_catalog.pg_roles AS r ON r.oid=s.setrole
WHERE s.setdatabase IN (0,(SELECT oid FROM pg_catalog.pg_database WHERE datname='ops_lab'))
  AND s.setrole IN (0,(SELECT oid FROM pg_catalog.pg_roles WHERE rolname='lab_app'))
ORDER BY database_scope, role_scope LIMIT 20;
COMMIT;
