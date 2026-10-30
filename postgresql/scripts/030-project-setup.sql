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
SET LOCAL statement_timeout='10s';
SET LOCAL lock_timeout='1s';
CREATE SCHEMA c030_incident AUTHORIZATION lab_admin;
CREATE TABLE c030_incident.requests(id integer PRIMARY KEY,a integer NOT NULL,b integer NOT NULL);
INSERT INTO c030_incident.requests
SELECT i,(i-1)%100,(i-1)%100 FROM generate_series(1,20000) AS s(i);
GRANT USAGE ON SCHEMA c030_incident TO lab_app;
GRANT SELECT ON c030_incident.requests TO lab_app;
COMMIT;
ANALYZE c030_incident.requests;

  THEN
    RAISE EXCEPTION 'Refused: this setup belongs only on the Chapter 004 disposable PG18 primary';
  END IF;
END
$lab_target$;
SET LOCAL statement_timeout='10s';
SET LOCAL lock_timeout='1s';
CREATE SCHEMA c030_incident AUTHORIZATION lab_admin;
CREATE TABLE c030_incident.requests(id integer PRIMARY KEY,a integer NOT NULL,b integer NOT NULL);
INSERT INTO c030_incident.requests
SELECT i,(i-1)%100,(i-1)%100 FROM generate_series(1,20000) AS s(i);
GRANT USAGE ON SCHEMA c030_incident TO lab_app;
GRANT SELECT ON c030_incident.requests TO lab_app;
COMMIT;
ANALYZE c030_incident.requests;
