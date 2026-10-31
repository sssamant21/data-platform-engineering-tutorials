\set ON_ERROR_STOP on
-- Chapter 047 mutating operations are restricted to the disposable Chapter 004 primary.
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
SELECT CASE WHEN current_database()='ops_lab' AND current_user='lab_admin'
 AND inet_server_addr()=inet '127.0.0.1' AND inet_server_port()=55432
 AND current_setting('server_version_num')::integer BETWEEN 180000 AND 189999
 AND current_setting('data_directory') ~ '^/tmp/postgresql-dbre-lab\.[A-Za-z0-9]+/primary$'
 AND NOT pg_is_in_recovery()
 AND EXISTS (SELECT 1 FROM pg_control_system() c
             WHERE c.system_identifier::text=:'expected_system_id')
 AND :'confirm_stage'='047-CREATE-SLOT'
 -- Require spare slot capacity and a finite WAL-retention setting in the isolated lab.
 AND current_setting('max_replication_slots')::integer >= 1
 AND (SELECT count(*) FROM pg_replication_slots) < current_setting('max_replication_slots')::integer
 AND EXISTS (SELECT 1 FROM pg_settings WHERE name='max_slot_wal_keep_size'
             AND unit='MB' AND setting::integer BETWEEN 1 AND 512)
 AND NOT EXISTS (SELECT 1 FROM pg_replication_slots WHERE slot_name='ch047_lab_physical')
 THEN 'true' ELSE 'false' END AS stage_permitted
\gset
\if :stage_permitted
 \echo 'Disposable PostgreSQL 18 lab target and fixture state verified'
\else
 \echo 'REFUSED: wrong target, approval token or fixture state'
 SELECT 1/0 AS refusal_nonzero;
\endif
SELECT slot_name,lsn FROM pg_create_physical_replication_slot('ch047_lab_physical',false);
