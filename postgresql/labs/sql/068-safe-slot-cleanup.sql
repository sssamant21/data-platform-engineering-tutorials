\set ON_ERROR_STOP on
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
 AND EXISTS(SELECT 1 FROM pg_control_system() c
            WHERE c.system_identifier::text=:'expected_system_id')
 AND :'confirm_stage'='068-DROP-LAB-SLOT'
 AND to_regclass('ch068.wal_probe') IS NOT NULL
 AND EXISTS(SELECT 1 FROM pg_replication_slots
            WHERE slot_name='ch068_lab_slot' AND slot_type='physical' AND NOT active)
 THEN 'true' ELSE 'false' END AS allowed
\gset
\if :allowed
\else
 \echo 'REFUSED: incorrect cluster, slot state, fixture or cleanup token'
 DO $$ BEGIN RAISE EXCEPTION 'REFUSED: PostgreSQL lab safety guard'; END $$;
\endif
-- Only the dedicated, inactive, lab-created slot may be dropped.
SELECT pg_drop_replication_slot('ch068_lab_slot');
-- RESTRICT is implicit. An unexpected dependency refuses deletion.
DROP TABLE ch068.wal_probe;
DROP SCHEMA ch068;
