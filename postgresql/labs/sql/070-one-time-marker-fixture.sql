\set ON_ERROR_STOP on
-- This is a one-time lab fixture. Require independent operator-verified identity.
\if :{?expected_system_id}
\else
 \echo 'REFUSED: expected_system_id required'
 DO $$ BEGIN RAISE EXCEPTION 'REFUSED: PostgreSQL lab safety guard'; END $$;
\endif
\if :{?expected_lab_data_directory}
\else
 \echo 'REFUSED: expected_lab_data_directory required'
 DO $$ BEGIN RAISE EXCEPTION 'REFUSED: PostgreSQL lab safety guard'; END $$;
\endif
\if :{?expected_lab_role}
\else
 \echo 'REFUSED: expected_lab_role required'
 DO $$ BEGIN RAISE EXCEPTION 'REFUSED: PostgreSQL lab safety guard'; END $$;
\endif
\if :{?confirm_stage}
\else
 \echo 'REFUSED: confirm_stage required'
 DO $$ BEGIN RAISE EXCEPTION 'REFUSED: PostgreSQL lab safety guard'; END $$;
\endif
SELECT CASE WHEN current_database()='ch070_lab'
 AND current_user=:'expected_lab_role'
 AND current_setting('data_directory')=:'expected_lab_data_directory'
 AND current_setting('server_version_num')::integer BETWEEN 180000 AND 189999
 AND NOT pg_is_in_recovery()
 AND EXISTS (SELECT 1 FROM pg_control_system() c
             WHERE c.system_identifier::text=:'expected_system_id')
 AND :'confirm_stage'='070-ONE-TIME-MARKER'
 AND to_regnamespace('ch070') IS NULL
 THEN 'true' ELSE 'false' END AS allowed
\gset
\if :allowed
 \echo 'Verified disposable lab cluster and unused one-time fixture.'
\else
 \echo 'REFUSED: wrong role, system ID, PGDATA, stage or preexisting lab schema'
 DO $$ BEGIN RAISE EXCEPTION 'REFUSED: PostgreSQL lab safety guard'; END $$;
\endif
BEGIN;
SET LOCAL lock_timeout='1s';
SET LOCAL statement_timeout='30s';
CREATE SCHEMA ch070;
CREATE TABLE ch070.markers (
 id text PRIMARY KEY,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
INSERT INTO ch070.markers(id) VALUES ('before-switchover');
COMMIT;
SELECT id,created_at FROM ch070.markers ORDER BY id;
