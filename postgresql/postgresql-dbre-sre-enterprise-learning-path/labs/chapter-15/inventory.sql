\set ON_ERROR_STOP on
-- Read-only PostgreSQL 17 inventory. Execute only in the named lab container.
\echo '== Collection timestamp and instance observation =='
SELECT now() AT TIME ZONE 'UTC' AS observed_at_utc,
       current_setting('server_version') AS server_version,
       pg_is_in_recovery() AS is_standby,
       pg_postmaster_start_time() AS postmaster_started_at;

\echo '== Cluster system identifier (admin-only; not a business asset ID) =='
SELECT system_identifier::text AS postgres_system_identifier
FROM pg_control_system();

\echo '== Database inventory (database authorization role != business owner) =='
SELECT datname AS database_name,
       pg_get_userbyid(datdba) AS database_role_owner,
       pg_database_size(oid) AS database_bytes,
       datallowconn AS allows_connections
FROM pg_database
WHERE datallowconn AND NOT datistemplate
ORDER BY datname;

\echo '== Synthetic owner roles (no password hashes) =='
SELECT rolname, rolcanlogin, rolsuper, rolreplication, rolbypassrls
FROM pg_roles
WHERE rolname LIKE 'fleet_lab_%'
ORDER BY rolname;

\echo '== Non-secret configuration baseline =='
SELECT name, setting, unit, source, pending_restart
FROM pg_settings
WHERE name IN ('max_connections', 'shared_buffers', 'wal_level',
               'password_encryption', 'ssl', 'max_wal_size')
ORDER BY name;

\echo '== Database activity (counters can reset; not proof of usage) =='
SELECT datname, numbackends, xact_commit, xact_rollback, stats_reset
FROM pg_stat_database
WHERE datname IN ('fleet_lab_app', 'fleet_lab_reporting')
ORDER BY datname;
