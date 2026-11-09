-- Chapter 035: DELETE versus TRUNCATE versus DROP
-- Run ONLY on an independently verified disposable PostgreSQL 18 sql_tutorials DB.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/035-delete-truncate-drop.sql
BEGIN;
SET LOCAL lock_timeout = '2s';
SET LOCAL statement_timeout = '30s';
SET LOCAL idle_in_transaction_session_timeout = '60s';

DO $guard$
BEGIN
 IF current_setting('server_version_num')::integer NOT BETWEEN 180000 AND 189999
    OR current_database() <> 'sql_tutorials'
    OR pg_is_in_recovery()
 THEN RAISE EXCEPTION 'Unsafe PostgreSQL version/database/standby; abort'; END IF;
END
$guard$;

-- TEMP table and all synthetic values are scoped to this isolated session.
CREATE TEMP TABLE stage_events (
 event_id TEXT PRIMARY KEY,
 quality_status TEXT NOT NULL CHECK (quality_status IN ('accepted','rejected')),
 amount NUMERIC(10,2) NOT NULL
) ON COMMIT DROP;
INSERT INTO stage_events(event_id,quality_status,amount) VALUES
 ('EV-001','accepted',10.00),
 ('EV-002','accepted',20.00),
 ('EV-003','rejected',5.00);

DO $initial$
BEGIN
 IF (SELECT count(*) FROM pg_temp.stage_events) <> 3
 THEN RAISE EXCEPTION 'Initial cardinality mismatch'; END IF;
END
$initial$;

-- Preview exact eligible row; fail closed before DELETE.
SELECT event_id,quality_status FROM pg_temp.stage_events
 WHERE event_id='EV-003' AND quality_status='rejected' ORDER BY event_id;
DO $preview$
BEGIN
 IF (SELECT array_agg(event_id ORDER BY event_id)
       FROM pg_temp.stage_events WHERE event_id='EV-003' AND quality_status='rejected')
    IS DISTINCT FROM ARRAY['EV-003']::TEXT[]
 THEN RAISE EXCEPTION 'DELETE candidate set mismatch'; END IF;
END
$preview$;

CREATE TEMP TABLE deleted_keys(event_id TEXT PRIMARY KEY) ON COMMIT DROP;
WITH removed AS (
 DELETE FROM pg_temp.stage_events
 WHERE event_id='EV-003' AND quality_status='rejected'
 RETURNING event_id
)
INSERT INTO pg_temp.deleted_keys SELECT event_id FROM removed;

DO $after_delete$
BEGIN
 IF (SELECT array_agg(event_id ORDER BY event_id) FROM pg_temp.deleted_keys)
      IS DISTINCT FROM ARRAY['EV-003']::TEXT[]
 OR (SELECT array_agg(event_id ORDER BY event_id) FROM pg_temp.stage_events)
      IS DISTINCT FROM ARRAY['EV-001','EV-002']::TEXT[]
 THEN RAISE EXCEPTION 'DELETE acceptance mismatch'; END IF;
END
$after_delete$;

-- PostgreSQL-specific TRUNCATE. No CASCADE, no RESTART IDENTITY.
TRUNCATE TABLE pg_temp.stage_events CONTINUE IDENTITY;
DO $after_truncate$
BEGIN
 IF (SELECT count(*) FROM pg_temp.stage_events) <> 0
 OR to_regclass('pg_temp.stage_events') IS NULL
 THEN RAISE EXCEPTION 'TRUNCATE acceptance mismatch'; END IF;
END
$after_truncate$;

-- DROP the disposable TEMP object only.
DROP TABLE pg_temp.stage_events RESTRICT;
DO $after_drop$
BEGIN
 IF to_regclass('pg_temp.stage_events') IS NOT NULL
 THEN RAISE EXCEPTION 'DROP acceptance mismatch'; END IF;
 IF (SELECT count(*) FROM pg_temp.deleted_keys) <> 1
 THEN RAISE EXCEPTION 'Deleted key audit mismatch'; END IF;
END
$after_drop$;

SELECT 'PASS' AS lab_acceptance,
       3 AS initial_rows,
       1 AS deleted_rows,
       2 AS rows_after_delete,
       0 AS rows_after_truncate,
       'absent' AS table_after_drop;
ROLLBACK;
