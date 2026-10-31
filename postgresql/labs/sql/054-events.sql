\set ON_ERROR_STOP on
-- Mutations allowed only on the independently verified Chapter 004 disposable PG18 primary.
\if :{?expected_system_id}
\else
 \echo 'REFUSED: expected_system_id required'
 SELECT 1/0 AS refusal_nonzero;
\endif
\if :{?confirm_stage}
\else
 \echo 'REFUSED: confirm_stage required'
 SELECT 1/0 AS refusal_nonzero;
\endif
SELECT CASE WHEN current_database()='ch054_lab'
 AND current_user='lab_admin'
 AND inet_server_addr()=inet '127.0.0.1' AND inet_server_port()=55432
 AND current_setting('server_version_num')::integer BETWEEN 180000 AND 189999
 AND current_setting('data_directory') ~ '^/tmp/postgresql-dbre-lab\.[A-Za-z0-9]+/primary$'
 AND NOT pg_is_in_recovery()
 AND EXISTS(SELECT 1 FROM pg_control_system() c
            WHERE c.system_identifier::text=:'expected_system_id')
 AND :'confirm_stage'='054-GENERATE-EVENTS'
 AND to_regnamespace('ch054') IS NULL AND NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='ch054_auditor')
 THEN 'true' ELSE 'false' END AS stage_permitted
\gset
\if :stage_permitted
 \echo 'Verified disposable Chapter 004 lab identity and initial state.'
\else
 \echo 'REFUSED: wrong database, cluster identity, role, stage or existing lab fixture'
 SELECT 1/0 AS refusal_nonzero;
\endif
BEGIN;
SET LOCAL statement_timeout='30s';
SET LOCAL lock_timeout='1s';
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

COMMIT;
