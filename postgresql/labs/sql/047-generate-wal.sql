\set ON_ERROR_STOP on
-- Chapter 047 mutating operations are restricted to the disposable Chapter 004 primary.
\if :{?expected_system_id}
\else
 \echo 'REFUSED: expected_system_id required'
 \quit 3
\endif
\if :{?confirm_stage}
\else
 \echo 'REFUSED: confirm_stage required'
 \quit 3
\endif
SELECT CASE WHEN current_database()='ops_lab' AND current_user='lab_admin'
 AND inet_server_addr()=inet '127.0.0.1' AND inet_server_port()=55432
 AND current_setting('server_version_num')::integer BETWEEN 180000 AND 189999
 AND current_setting('data_directory') ~ '^/tmp/postgresql-dbre-lab\.[A-Za-z0-9]+/primary$'
 AND NOT pg_is_in_recovery()
 AND EXISTS (SELECT 1 FROM pg_control_system() c
             WHERE c.system_identifier::text=:'expected_system_id')
 AND :'confirm_stage'='047-GENERATE-WAL'
 AND to_regnamespace('ch047') IS NULL AND EXISTS (SELECT 1 FROM pg_replication_slots WHERE slot_name='ch047_lab_physical' AND slot_type='physical' AND NOT active)
 THEN 'true' ELSE 'false' END AS stage_permitted
\gset
\if :stage_permitted
 \echo 'Disposable PostgreSQL 18 lab target and fixture state verified'
\else
 \echo 'REFUSED: wrong target, approval token or fixture state'
 \quit 3
\endif
BEGIN;
SET LOCAL statement_timeout='10s';
SET LOCAL lock_timeout='1s';
CREATE SCHEMA ch047 AUTHORIZATION lab_admin;
CREATE TABLE ch047.wal_fixture (
 id integer PRIMARY KEY,
 payload text NOT NULL
);
INSERT INTO ch047.wal_fixture(id,payload)
SELECT g,repeat(md5(g::text),8) FROM generate_series(1,2000) g;
COMMIT;
SELECT count(*) AS fixture_rows FROM ch047.wal_fixture;
SELECT pg_current_wal_lsn() AS observed_lsn;
