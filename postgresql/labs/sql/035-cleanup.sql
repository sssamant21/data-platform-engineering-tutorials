\set ON_ERROR_STOP on
-- V02-B fail-closed cleanup gate. Never run on a shared/production cluster.
-- Capture the disposable cluster's system_identifier independently first.
-- Required psql -v inputs: expected_db, expected_system_id, confirm_cleanup.
\if :{?expected_db}
\else
  \echo 'REFUSED: pass -v expected_db=YOUR_LAB_DATABASE'
  \quit 3
\endif
\if :{?expected_system_id}
\else
  \echo 'REFUSED: pass -v expected_system_id=OBSERVED_LAB_CLUSTER_ID'
  \quit 3
\endif
\if :{?confirm_cleanup}
\else
  \echo 'REFUSED: explicit chapter-specific cleanup confirmation required'
  \quit 3
\endif
SELECT CASE WHEN current_database() = :'expected_db'
  AND current_database() NOT IN ('template0','template1')
  AND current_setting('server_version_num')::integer BETWEEN 180000 AND 189999
  AND NOT pg_is_in_recovery()
  AND EXISTS (SELECT 1 FROM pg_control_system() c
              WHERE c.system_identifier::text = :'expected_system_id')
  AND :'confirm_cleanup' = '035-DROP'
  THEN 'true' ELSE 'false' END AS cleanup_permitted
\gset
\if :cleanup_permitted
  \echo 'Cleanup preflight passed: exact lab database, cluster and token matched.'
\else
  \echo 'REFUSED: database, cluster, version, role or cleanup token mismatch'
  \quit 3
\endif
\echo 'DISPOSABLE DATABASE ONLY: dropping ch035'
DROP SCHEMA IF EXISTS ch035 CASCADE;
SELECT count(*) AS remaining_ch035_schemas FROM pg_namespace WHERE nspname='ch035';
