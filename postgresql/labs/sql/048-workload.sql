\set ON_ERROR_STOP on
-- Chapter 048 mutating operations are restricted to the disposable Chapter 004 primary.
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
 AND :'confirm_stage'='048-WORKLOAD'
 AND to_regnamespace('ch048') IS NULL
 THEN 'true' ELSE 'false' END AS stage_permitted
\gset
\if :stage_permitted
 \echo 'Disposable PostgreSQL 18 lab target and fixture state verified'
\else
 \echo 'REFUSED: wrong target, approval token or fixture state'
 SELECT 1/0 AS refusal_nonzero;
\endif
BEGIN;
SET LOCAL statement_timeout='15s';
SET LOCAL lock_timeout='1s';
CREATE SCHEMA ch048 AUTHORIZATION lab_admin;
CREATE TABLE ch048.events(id integer PRIMARY KEY,payload text NOT NULL);
INSERT INTO ch048.events(id,payload)
SELECT g,repeat(md5(g::text),8) FROM generate_series(1,5000) g;
COMMIT;
SELECT count(*) AS fixture_rows FROM ch048.events;
SELECT pg_current_wal_lsn() AS observed_primary_lsn;
