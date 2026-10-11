-- PostgreSQL 18 bounded metadata inspection. Run using an approved observer.
\set ON_ERROR_STOP on
\pset pager off
\if :{?schema_name}
\else
  \set schema_name public
\endif
BEGIN READ ONLY;
SET LOCAL statement_timeout = '5s';
SET LOCAL lock_timeout = '1s';
SET LOCAL search_path = pg_catalog;
SELECT clock_timestamp() AS observed_at, current_database() AS database_name,
       current_user AS connected_role, inet_server_addr() AS server_address,
       inet_server_port() AS server_port,
       current_setting('server_version') AS server_version,
       pg_is_in_recovery() AS in_recovery;
SELECT n.nspname AS schema_name, c.relname, c.relkind,
       pg_get_userbyid(c.relowner) AS owner,
       c.relpersistence
FROM pg_class AS c JOIN pg_namespace AS n ON n.oid = c.relnamespace
WHERE n.nspname = :'schema_name'
  AND c.relkind IN ('r','p','v','m','f','S')
ORDER BY c.relname LIMIT 30;
SELECT extname, extversion
FROM pg_extension ORDER BY extname LIMIT 30;
SELECT rolname, rolsuper, rolcreaterole, rolcreatedb, rolcanlogin, rolreplication
FROM pg_roles WHERE rolname = current_user;
SELECT name, setting, unit, source, context, pending_restart
FROM pg_settings
WHERE name IN ('statement_timeout','lock_timeout','idle_in_transaction_session_timeout',
              'default_transaction_read_only','search_path','max_connections')
ORDER BY name;
SELECT table_schema, table_name, table_type
FROM information_schema.tables
WHERE table_schema = :'schema_name'
ORDER BY table_name LIMIT 30;
COMMIT;
