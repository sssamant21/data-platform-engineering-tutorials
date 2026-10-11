-- PG18 disposable Chapter 004 primary; ops_lab as lab_admin.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL statement_timeout='5s';
SET LOCAL lock_timeout='1s';
DO $guard$
BEGIN
 IF current_user <> 'lab_admin' OR current_database() <> 'ops_lab'
    OR pg_is_in_recovery() OR current_setting('server_version_num')::integer/10000 <> 18 THEN
   RAISE EXCEPTION 'Wrong lab identity/database/version';
 END IF;
 IF EXISTS (SELECT FROM pg_namespace WHERE nspname='c017_iso') THEN
   RAISE EXCEPTION 'Exercise schema occupied; inspect rather than overwrite';
 END IF;
END
$guard$;
CREATE SCHEMA c017_iso AUTHORIZATION lab_admin;
CREATE TABLE c017_iso.counter(id integer PRIMARY KEY,units integer NOT NULL CHECK(units>=0));
CREATE TABLE c017_iso.roster(id integer PRIMARY KEY,on_call boolean NOT NULL);
INSERT INTO c017_iso.counter VALUES (1,100);
INSERT INTO c017_iso.roster VALUES (1,true),(2,true);
GRANT USAGE ON SCHEMA c017_iso TO lab_app,lab_observer;
GRANT SELECT,UPDATE ON c017_iso.counter,c017_iso.roster TO lab_app;
GRANT SELECT ON c017_iso.counter,c017_iso.roster TO lab_observer;
COMMIT;
