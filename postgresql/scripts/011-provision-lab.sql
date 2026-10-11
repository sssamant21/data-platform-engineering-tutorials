-- PG18, disposable Chapter 004 primary only. Run from ops_lab as lab_admin.
-- The lab guide's OS marker/data-directory guard is required first.
-- No passwords in this file. Configure the two LOGIN passwords with \password.
\set ON_ERROR_STOP on
SET statement_timeout='10s';
SET lock_timeout='1s';
DO $guard$
BEGIN
  IF current_user <> 'lab_admin' OR current_database() <> 'ops_lab'
     OR pg_is_in_recovery()
     OR current_setting('server_version_num')::integer/10000 <> 18 THEN
    RAISE EXCEPTION 'Wrong lab identity/database/role/version';
  END IF;
  IF EXISTS (SELECT FROM pg_roles WHERE rolname IN
       ('c011_owner','c011_reader','c011_writer','c011_runtime','c011_deploy'))
     OR EXISTS (SELECT FROM pg_database WHERE datname='c011_db') THEN
    RAISE EXCEPTION 'Chapter 011 names occupied; do not overwrite them';
  END IF;
END
$guard$;

BEGIN;
CREATE ROLE c011_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE c011_reader NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE c011_writer NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE c011_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE c011_deploy LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
GRANT c011_reader TO c011_writer WITH INHERIT TRUE, SET FALSE, ADMIN FALSE;
GRANT c011_writer TO c011_runtime WITH INHERIT TRUE, SET FALSE, ADMIN FALSE;
GRANT c011_owner TO c011_deploy WITH INHERIT FALSE, SET TRUE, ADMIN FALSE;
COMMIT;

-- CREATE DATABASE cannot run in a transaction.
CREATE DATABASE c011_db OWNER c011_owner TEMPLATE template0;
REVOKE ALL ON DATABASE c011_db FROM PUBLIC;
GRANT CONNECT ON DATABASE c011_db TO c011_runtime,c011_deploy,lab_observer;
\connect c011_db
SET statement_timeout='10s';
SET lock_timeout='1s';
BEGIN;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
SET LOCAL ROLE c011_owner;
CREATE SCHEMA c011_data AUTHORIZATION c011_owner;
REVOKE ALL ON SCHEMA c011_data FROM PUBLIC;
GRANT USAGE ON SCHEMA c011_data TO c011_reader;
ALTER DEFAULT PRIVILEGES FOR ROLE c011_owner IN SCHEMA c011_data
  GRANT SELECT ON TABLES TO c011_reader;
ALTER DEFAULT PRIVILEGES FOR ROLE c011_owner IN SCHEMA c011_data
  GRANT INSERT,UPDATE ON TABLES TO c011_writer;
ALTER DEFAULT PRIVILEGES FOR ROLE c011_owner IN SCHEMA c011_data
  GRANT USAGE ON SEQUENCES TO c011_writer;
CREATE TABLE c011_data.jobs(id bigserial PRIMARY KEY,payload text NOT NULL);
INSERT INTO c011_data.jobs(payload) VALUES ('owner-fixture');
COMMIT;
