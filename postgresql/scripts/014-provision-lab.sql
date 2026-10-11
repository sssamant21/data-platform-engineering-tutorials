-- PG18, guarded Chapter 004 primary; run from ops_lab as lab_admin.
-- Creates an isolated database and five roles. No passwords appear in this file.
\set ON_ERROR_STOP on
SET statement_timeout='10s';
SET lock_timeout='1s';
DO $guard$
BEGIN
  IF current_user <> 'lab_admin' OR current_database() <> 'ops_lab'
     OR pg_is_in_recovery()
     OR current_setting('server_version_num')::integer/10000 <> 18 THEN
    RAISE EXCEPTION 'Wrong lab identity/database/version';
  END IF;
  IF EXISTS (SELECT FROM pg_roles WHERE rolname IN
       ('c014_owner','c014_reader','c014_single','c014_blue','c014_green'))
     OR EXISTS (SELECT FROM pg_database WHERE datname='c014_db') THEN
    RAISE EXCEPTION 'Chapter 014 names occupied; inspect rather than overwrite';
  END IF;
END
$guard$;
BEGIN;
CREATE ROLE c014_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE c014_reader NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE c014_single LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE c014_blue LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE c014_green LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
GRANT c014_reader TO c014_single,c014_blue,c014_green
  WITH INHERIT TRUE, SET FALSE, ADMIN FALSE;
COMMIT;
CREATE DATABASE c014_db OWNER c014_owner TEMPLATE template0;
REVOKE ALL ON DATABASE c014_db FROM PUBLIC;
GRANT CONNECT ON DATABASE c014_db TO c014_single,c014_blue,c014_green,lab_observer;
\connect c014_db
SET statement_timeout='10s';
SET lock_timeout='1s';
BEGIN;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
SET LOCAL ROLE c014_owner;
CREATE SCHEMA c014_data AUTHORIZATION c014_owner;
REVOKE ALL ON SCHEMA c014_data FROM PUBLIC;
GRANT USAGE ON SCHEMA c014_data TO c014_reader;
ALTER DEFAULT PRIVILEGES FOR ROLE c014_owner IN SCHEMA c014_data
  GRANT SELECT ON TABLES TO c014_reader;
CREATE TABLE c014_data.probe(id integer PRIMARY KEY,payload text NOT NULL);
INSERT INTO c014_data.probe VALUES (1,'service-access-fixture');
COMMIT;
