\set ON_ERROR_STOP on
-- Only a separately approved disposable PG18 source may execute this write stage.
\if :{?expected_system_id}
\else
 \echo 'REFUSED: expected_system_id required'
 \quit 3
\endif
\if :{?expected_data_directory}
\else
 \echo 'REFUSED: expected_data_directory required'
 \quit 3
\endif
\if :{?expected_operator}
\else
 \echo 'REFUSED: expected_operator required'
 \quit 3
\endif
\if :{?confirm_stage}
\else
 \echo 'REFUSED: confirm_stage required'
 \quit 3
\endif
SELECT CASE WHEN current_database()='postgres'
 AND current_user=:'expected_operator'
 AND current_setting('server_version_num')::integer BETWEEN 180000 AND 189999
 AND current_setting('data_directory')=:'expected_data_directory'
 AND NOT pg_is_in_recovery()
 AND EXISTS (SELECT 1 FROM pg_control_system() c
             WHERE c.system_identifier::text=:'expected_system_id')
 AND :'confirm_stage'='045-CREATE-FIXTURE'
 AND to_regnamespace('ch045') IS NULL
 THEN 'true' ELSE 'false' END AS stage_permitted
\gset
\if :stage_permitted
 \echo 'Explicitly identified disposable source and lab state matched'
\else
 \echo 'REFUSED: source identity, approval or lab fixture state mismatch'
 \quit 3
\endif
BEGIN;
SET LOCAL statement_timeout='10s';
SET LOCAL lock_timeout='1s';
CREATE SCHEMA ch045;
CREATE TABLE ch045.orders (
 order_id integer PRIMARY KEY,
 status text NOT NULL,
 amount numeric(12,2) NOT NULL,
 updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
INSERT INTO ch045.orders(order_id,status,amount)
SELECT g,'valid',(g%1000)::numeric/100 FROM generate_series(1,1000) g;
CREATE TABLE ch045.recovery_markers (
 marker_name text PRIMARY KEY,
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
COMMIT;
SELECT count(*) AS baseline_rows FROM ch045.orders;
