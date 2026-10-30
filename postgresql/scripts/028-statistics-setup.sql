\set ON_ERROR_STOP on
BEGIN;
-- SQL-level identity guard supplements the OS/psql lab preflight.
-- No changes to an unexpected database, role, cluster, or standby.
DO $lab_target$
BEGIN
  IF current_database() <> 'ops_lab'
    OR current_user <> 'lab_admin'
    OR pg_is_in_recovery()
    OR inet_server_addr() IS DISTINCT FROM inet '127.0.0.1'
    OR inet_server_port() IS DISTINCT FROM 55432
    OR current_setting('server_version_num')::integer NOT BETWEEN 180000 AND 189999
    OR current_setting('data_directory') !~ '^/tmp/postgresql-dbre-lab\.[A-Za-z0-9]+/primary
SET LOCAL lock_timeout = '1s';
SET LOCAL statement_timeout = '10s';
CREATE SCHEMA c028_stats AUTHORIZATION lab_admin;
CREATE TABLE c028_stats.correlated (
    id integer PRIMARY KEY, a integer NOT NULL, b integer NOT NULL
);
INSERT INTO c028_stats.correlated
SELECT i, (i-1)%100, (i-1)%100 FROM generate_series(1,20000) AS s(i);
GRANT USAGE ON SCHEMA c028_stats TO lab_app;
GRANT SELECT ON c028_stats.correlated TO lab_app;
COMMIT;
ANALYZE c028_stats.correlated;

  THEN
    RAISE EXCEPTION 'Refused: this setup belongs only on the Chapter 004 disposable PG18 primary';
  END IF;
END
$lab_target$;
SET LOCAL lock_timeout = '1s';
SET LOCAL statement_timeout = '10s';
CREATE SCHEMA c028_stats AUTHORIZATION lab_admin;
CREATE TABLE c028_stats.correlated (
    id integer PRIMARY KEY, a integer NOT NULL, b integer NOT NULL
);
INSERT INTO c028_stats.correlated
SELECT i, (i-1)%100, (i-1)%100 FROM generate_series(1,20000) AS s(i);
GRANT USAGE ON SCHEMA c028_stats TO lab_app;
GRANT SELECT ON c028_stats.correlated TO lab_app;
COMMIT;
ANALYZE c028_stats.correlated;
