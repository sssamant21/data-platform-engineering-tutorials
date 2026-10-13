\set ON_ERROR_STOP on
DO $$
BEGIN
 IF current_database() <> 'ch054_lab' THEN RAISE EXCEPTION 'Use ch054_lab only'; END IF;
 IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='ch054_auditor') THEN
   RAISE EXCEPTION 'Role ch054_auditor exists; refusing collision';
 END IF;
END $$;
CREATE ROLE ch054_auditor NOLOGIN;
CREATE SCHEMA ch054;
CREATE TABLE ch054.audit_fixture(id integer PRIMARY KEY,note text);
ALTER TABLE ch054.audit_fixture ADD COLUMN created_at timestamptz DEFAULT now();
GRANT USAGE ON SCHEMA ch054 TO ch054_auditor;
GRANT SELECT ON ch054.audit_fixture TO ch054_auditor;
REVOKE SELECT ON ch054.audit_fixture FROM ch054_auditor;
INSERT INTO ch054.audit_fixture(id,note) VALUES(1,'lab event');
SELECT count(*) AS fixture_rows FROM ch054.audit_fixture;
