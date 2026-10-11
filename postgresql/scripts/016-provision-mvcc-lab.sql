-- PG18 disposable Chapter 004 primary, ops_lab, lab_admin.
-- Require the lab guide's OS marker/data-directory guard first.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL statement_timeout='5s';
SET LOCAL lock_timeout='1s';
DO $guard$
BEGIN
  IF current_user <> 'lab_admin' OR current_database() <> 'ops_lab'
     OR pg_is_in_recovery()
     OR current_setting('server_version_num')::integer/10000 <> 18 THEN
    RAISE EXCEPTION 'Wrong lab identity/database/version';
  END IF;
  IF EXISTS (SELECT FROM pg_namespace WHERE nspname='c016_mvcc') THEN
    RAISE EXCEPTION 'Exercise schema occupied; inspect rather than overwrite';
  END IF;
END
$guard$;
CREATE SCHEMA c016_mvcc AUTHORIZATION lab_admin;
CREATE TABLE c016_mvcc.probe(
  id integer PRIMARY KEY,
  value integer NOT NULL,
  payload text NOT NULL
);
INSERT INTO c016_mvcc.probe VALUES (1,100,'first-fixture'),(2,200,'second-fixture');
GRANT USAGE ON SCHEMA c016_mvcc TO lab_app,lab_observer;
GRANT SELECT,INSERT,UPDATE,DELETE ON c016_mvcc.probe TO lab_app;
GRANT SELECT ON c016_mvcc.probe TO lab_observer;
COMMIT;
