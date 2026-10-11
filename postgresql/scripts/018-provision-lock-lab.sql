-- PG18 disposable Chapter 004 primary, ops_lab as lab_admin.
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
 IF EXISTS (SELECT FROM pg_namespace WHERE nspname='c018_locks') THEN
   RAISE EXCEPTION 'Exercise schema occupied; inspect rather than overwrite';
 END IF;
END
$guard$;
CREATE SCHEMA c018_locks AUTHORIZATION lab_admin;
CREATE TABLE c018_locks.probe(id integer PRIMARY KEY,quantity integer NOT NULL);
INSERT INTO c018_locks.probe VALUES (1,100),(2,200);
GRANT USAGE ON SCHEMA c018_locks TO lab_app,lab_observer;
GRANT SELECT,UPDATE ON c018_locks.probe TO lab_app;
GRANT SELECT ON c018_locks.probe TO lab_observer;
COMMIT;
