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
  AND :'confirm_cleanup' = '036-DROP'
  AND EXISTS (SELECT 1 FROM pg_namespace n
              WHERE n.nspname='ch036'
                AND n.nspowner=(SELECT oid FROM pg_roles WHERE rolname=current_user))
  AND EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
              WHERE n.nspname='ch036' AND c.relname='events'
                AND c.relkind IN ('r','p')
                AND c.relowner=(SELECT oid FROM pg_roles WHERE rolname=current_user))
  AND NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                  WHERE n.nspname='ch036' AND c.relkind IN ('r','p','v','m','f')
                    AND c.relname NOT IN ('events'))
  THEN 'true' ELSE 'false' END AS cleanup_permitted
\gset
\if :cleanup_permitted
  \echo 'Cleanup preflight passed: exact lab database, cluster and token matched.'
\else
  \echo 'REFUSED: database, cluster, version, role or cleanup token mismatch'
  \quit 3
\endif
\echo 'DISPOSABLE DATABASE ONLY: remove ch036 schema'
-- Refuse unknown independent dependencies; no schema-wide CASCADE.
BEGIN;
SET LOCAL lock_timeout='1s';
SET LOCAL statement_timeout='15s';
DROP TABLE ch036.events;
DROP SCHEMA ch036;
COMMIT;
SELECT count(*) AS remaining_ch036_schemas FROM pg_namespace WHERE nspname='ch036';
