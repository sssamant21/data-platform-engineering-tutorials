\set ON_ERROR_STOP on
-- Disposable Chapter 004 PostgreSQL 18 instance ONLY. Never a shared cluster.
\if :{?expected_system_id}
\else
 \echo 'REFUSED: expected_system_id is mandatory'
 DO $$ BEGIN RAISE EXCEPTION 'REFUSED: PostgreSQL lab safety guard'; END $$;
\endif
\if :{?confirm_stage}
\else
 \echo 'REFUSED: confirm_stage is mandatory'
 DO $$ BEGIN RAISE EXCEPTION 'REFUSED: PostgreSQL lab safety guard'; END $$;
\endif
SELECT CASE WHEN current_database()='ch068_lab'
  AND current_user='lab_admin'
  AND inet_server_addr()=inet '127.0.0.1'
  AND inet_server_port()=55432
  AND current_setting('server_version_num')::integer BETWEEN 180000 AND 189999
  AND current_setting('data_directory') ~ '^/tmp/postgresql-dbre-lab\.[A-Za-z0-9]+/primary$'
  AND NOT pg_is_in_recovery()
  AND EXISTS (SELECT 1 FROM pg_control_system() c
              WHERE c.system_identifier::text=:'expected_system_id')
  AND :'confirm_stage'='068-CREATE-SLOT'
  AND to_regnamespace('ch068') IS NULL
  AND NOT EXISTS (SELECT 1 FROM pg_replication_slots
                  WHERE slot_name='ch068_lab_slot')
  THEN 'true' ELSE 'false' END AS allowed
\gset
\if :allowed
 \echo 'Verified Chapter 004 disposable PG18 target, empty fixture and stage token.'
\else
 \echo 'REFUSED: unsafe database/identity or existing schema/slot'
 DO $$ BEGIN RAISE EXCEPTION 'REFUSED: PostgreSQL lab safety guard'; END $$;
\endif

BEGIN;
SET LOCAL statement_timeout='30s';
SET LOCAL lock_timeout='1s';
CREATE SCHEMA ch068;
CREATE TABLE ch068.wal_probe (
  id integer PRIMARY KEY,
  payload text NOT NULL
);
COMMIT;
-- A physical slot is a CLUSTER-WIDE resource. Ensure no other clients use it.
SELECT slot_name,lsn FROM pg_create_physical_replication_slot('ch068_lab_slot',true);
