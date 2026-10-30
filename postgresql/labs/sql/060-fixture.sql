\set ON_ERROR_STOP on
-- Mutations allowed only on the independently verified Chapter 004 disposable PG18 primary.
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
SELECT CASE WHEN current_database()='ch060_lab'
 AND current_user='lab_admin'
 AND inet_server_addr()=inet '127.0.0.1' AND inet_server_port()=55432
 AND current_setting('server_version_num')::integer BETWEEN 180000 AND 189999
 AND current_setting('data_directory') ~ '^/tmp/postgresql-dbre-lab\.[A-Za-z0-9]+/primary$'
 AND NOT pg_is_in_recovery()
 AND EXISTS(SELECT 1 FROM pg_control_system() c
            WHERE c.system_identifier::text=:'expected_system_id')
 AND :'confirm_stage'='060-CREATE-IDEMPOTENCY'
 AND to_regnamespace('ch060') IS NULL
 THEN 'true' ELSE 'false' END AS stage_permitted
\gset
\if :stage_permitted
 \echo 'Verified disposable Chapter 004 lab identity and initial state.'
\else
 \echo 'REFUSED: wrong database, cluster identity, role, stage or existing lab fixture'
 \quit 3
\endif
BEGIN;
SET LOCAL statement_timeout='30s';
SET LOCAL lock_timeout='1s';
CREATE SCHEMA ch060 AUTHORIZATION lab_admin;
CREATE TABLE ch060.requests (
 request_id text PRIMARY KEY,
 payload text NOT NULL,
 committed_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
INSERT INTO ch060.requests(request_id,payload)
VALUES ('baseline-001','sample')
ON CONFLICT (request_id) DO NOTHING;
-- This deliberate repeat tests the PRIMARY KEY/ON CONFLICT behavior inside a NEW fixture.
INSERT INTO ch060.requests(request_id,payload)
VALUES ('baseline-001','sample')
ON CONFLICT (request_id) DO NOTHING;
DO $assert$
BEGIN
 IF (SELECT count(*) FROM ch060.requests)<>1
  OR NOT EXISTS(SELECT 1 FROM ch060.requests
                WHERE request_id='baseline-001' AND payload='sample')
 THEN RAISE EXCEPTION 'FAIL: idempotency fixture returned unexpected state'; END IF;
END $assert$;

COMMIT;
