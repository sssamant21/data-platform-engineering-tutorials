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
 AND :'confirm_stage'='045-GOOD-MARKER'
 AND to_regclass('ch045.orders') IS NOT NULL AND to_regclass('ch045.recovery_markers') IS NOT NULL AND (SELECT count(*) FROM ch045.orders)=1000 AND (SELECT count(*) FROM ch045.orders WHERE status='valid')=1000 AND NOT EXISTS (SELECT 1 FROM ch045.recovery_markers WHERE marker_name='known-good')
 THEN 'true' ELSE 'false' END AS stage_permitted
\gset
\if :stage_permitted
 \echo 'Explicitly identified disposable source and lab state matched'
\else
 \echo 'REFUSED: source identity, approval or lab fixture state mismatch'
 SELECT 1/0 AS refusal_nonzero;
\endif
INSERT INTO ch045.recovery_markers(marker_name) VALUES ('known-good');
SELECT marker_name,recorded_at FROM ch045.recovery_markers;
SELECT pg_current_wal_lsn() AS observed_lsn,clock_timestamp() AS observed_at;
