\set ON_ERROR_STOP on
-- Only a separately approved disposable PG18 source may execute this write stage.
\if :{?expected_system_id}
\else
 \echo 'REFUSED: expected_system_id required'
 SELECT 1/0 AS refusal_nonzero;
\endif
\if :{?expected_data_directory}
\else
 \echo 'REFUSED: expected_data_directory required'
 SELECT 1/0 AS refusal_nonzero;
\endif
\if :{?expected_operator}
\else
 \echo 'REFUSED: expected_operator required'
 SELECT 1/0 AS refusal_nonzero;
\endif
\if :{?confirm_stage}
\else
 \echo 'REFUSED: confirm_stage required'
 SELECT 1/0 AS refusal_nonzero;
\endif
SELECT CASE WHEN current_database()='postgres'
 AND current_user=:'expected_operator'
 AND current_setting('server_version_num')::integer BETWEEN 180000 AND 189999
 AND current_setting('data_directory')=:'expected_data_directory'
 AND NOT pg_is_in_recovery()
 AND EXISTS (SELECT 1 FROM pg_control_system() c
             WHERE c.system_identifier::text=:'expected_system_id')
 AND :'confirm_stage'='044-MARKER'
 AND to_regnamespace('ch044') IS NULL
 THEN 'true' ELSE 'false' END AS stage_permitted
\gset
\if :stage_permitted
 \echo 'Explicitly identified disposable source and lab state matched'
\else
 \echo 'REFUSED: source identity, approval or lab fixture state mismatch'
 SELECT 1/0 AS refusal_nonzero;
\endif
BEGIN;
SET LOCAL statement_timeout='10s';
SET LOCAL lock_timeout='1s';
CREATE SCHEMA ch044;
CREATE TABLE ch044.recovery_markers (
 marker_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 marker_name text NOT NULL UNIQUE,
 inserted_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
INSERT INTO ch044.recovery_markers(marker_name)
VALUES ('before-pitr-drill');
COMMIT;
SELECT marker_id,marker_name,inserted_at FROM ch044.recovery_markers ORDER BY marker_id;
SELECT pg_current_wal_lsn() AS observed_lsn,clock_timestamp() AS observed_at;
