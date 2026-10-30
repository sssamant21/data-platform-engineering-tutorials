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
  AND current_database()='ops_lab'
  AND current_user='lab_admin'
  AND inet_server_addr()=inet '127.0.0.1' AND inet_server_port()=55432
  AND current_setting('data_directory') ~ '^/tmp/postgresql-dbre-lab\.[A-Za-z0-9]+/primary$'
  AND current_setting('server_version_num')::integer BETWEEN 180000 AND 189999
  AND NOT pg_is_in_recovery()
  AND EXISTS (SELECT 1 FROM pg_control_system() c
              WHERE c.system_identifier::text = :'expected_system_id')
  AND :'confirm_cleanup' = '040-DROP'
  AND EXISTS (SELECT 1 FROM pg_namespace n
              WHERE n.nspname='ch040' AND n.nspowner=(SELECT oid FROM pg_roles WHERE rolname=current_user))
  AND to_regclass('ch040.events') IS NOT NULL
  AND (SELECT count(*) FROM ch040.events)=12002
  AND (SELECT count(*) FROM pg_inherits i
       WHERE i.inhparent='ch040.events'::regclass
         AND i.inhrelid::regclass::text IN
           ('ch040.events_2026_01','ch040.events_2026_02',
            'ch040.events_2026_03','ch040.events_2026_04'))=4
  AND (SELECT count(*) FROM pg_inherits WHERE inhparent='ch040.events'::regclass)=4
  THEN 'true' ELSE 'false' END AS cleanup_permitted
\gset
\if :cleanup_permitted
  \echo 'Cleanup preflight passed: exact lab database, cluster and token matched.'
\else
  \echo 'REFUSED: database, cluster, version, role or cleanup token mismatch'
  \quit 3
\endif
\echo 'Disposable lab only: ch040 schema cleanup'
-- DROP TABLE automatically removes its attached partitions; do not CASCADE other dependencies.
-- Both operations are atomic; an unexpected detached table/foreign dependency
-- causes DROP SCHEMA to fail and rolls the transaction back.
BEGIN;
SET LOCAL lock_timeout='1s';
SET LOCAL statement_timeout='15s';
DROP TABLE ch040.events;
DROP SCHEMA ch040;
COMMIT;
SELECT count(*) AS remaining FROM pg_namespace WHERE nspname='ch040';
