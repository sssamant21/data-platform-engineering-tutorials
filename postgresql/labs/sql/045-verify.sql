\set ON_ERROR_STOP on
-- Recovery validation must be run on the independently identified isolated target.
-- Command-line token is an operator confirmation, not proof of authorization.
\if :{?expected_recovery_data_directory}
\else
  \echo 'REFUSED: expected_recovery_data_directory missing'
  SELECT 1/0 AS refusal_nonzero;
\endif
\if :{?expected_system_id}
\else
  \echo 'REFUSED: expected_system_id missing'
  SELECT 1/0 AS refusal_nonzero;
\endif
\if :{?confirm_recovery}
\else
  \echo 'REFUSED: confirm_recovery=045-VERIFY-RECOVERY missing'
  SELECT 1/0 AS refusal_nonzero;
\endif
SELECT CASE WHEN current_setting('server_version_num')::integer BETWEEN 180000 AND 189999
  AND current_database() = 'postgres'
  AND current_setting('data_directory') = :'expected_recovery_data_directory'
  AND EXISTS (SELECT 1 FROM pg_control_system() c
              WHERE c.system_identifier::text = :'expected_system_id')
  AND :'confirm_recovery' = '045-VERIFY-RECOVERY'
  THEN 'true' ELSE 'false' END AS target_permitted
\gset
\if :target_permitted
  \echo 'Recovery target identity matched supplied isolated-instance evidence.'
\else
  \echo 'REFUSED: recovery target cluster/path/token mismatch'
  SELECT 1/0 AS refusal_nonzero;
\endif
SELECT current_database() AS recovered_database, pg_is_in_recovery() AS in_recovery,
       current_setting('data_directory') AS recovered_directory;
SELECT count(*) AS total_rows,
       count(*) FILTER (WHERE status='valid') AS valid_rows,
       count(*) FILTER (WHERE status='corrupted') AS corrupt_rows,
       sum(amount) AS total_amount
FROM ch045.orders;
SELECT marker_name,recorded_at FROM ch045.recovery_markers ORDER BY marker_name;
-- This result is an actual exit-code gate; unlike a SELECT 'FAIL', it cannot
-- accidentally be treated as successful by a zero-exit psql wrapper.
SELECT CASE WHEN (SELECT count(*) FROM ch045.orders)=1000
 AND (SELECT count(*) FROM ch045.orders WHERE status='valid')=1000
 AND (SELECT count(*) FROM ch045.orders WHERE status='corrupted')=0
 AND (SELECT count(*) FROM ch045.recovery_markers)=1
 AND EXISTS(SELECT 1 FROM ch045.recovery_markers WHERE marker_name='known-good')
 THEN 'true' ELSE 'false' END AS recovery_accepted
\gset
\if :recovery_accepted
  \echo 'PASS: isolated PITR fixture marker/rows validated'
\else
  \echo 'FAIL: PITR fixture did not satisfy expected committed state'
  SELECT 1/0 AS refusal_nonzero;
\endif
