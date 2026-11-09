-- Chapter 031: INSERT single-row and multi-row records
-- PostgreSQL 18 only; isolated disposable sql_tutorials database only.
-- Verify host, port, user and container independently BEFORE running.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/031-insert-single-row-and-multi-row-records.sql
BEGIN;
SET LOCAL lock_timeout = '2s';
SET LOCAL statement_timeout = '30s';
SET LOCAL idle_in_transaction_session_timeout = '60s';
DO $guard$
BEGIN
 IF current_setting('server_version_num')::integer NOT BETWEEN 180000 AND 189999
    OR current_database() <> 'sql_tutorials'
    OR pg_is_in_recovery()
 THEN RAISE EXCEPTION 'Wrong PostgreSQL version/database or standby: abort'; END IF;
END
$guard$;

CREATE TEMP TABLE ingest_events (
 source_event_id VARCHAR(20) PRIMARY KEY,
 customer_code VARCHAR(20) NOT NULL,
 amount NUMERIC(12,2) NOT NULL CHECK (amount >= 0),
 status VARCHAR(10) NOT NULL DEFAULT 'NEW'
   CHECK (status IN ('NEW','READY','HELD'))
) ON COMMIT DROP;

-- Single-row INSERT: omitted status uses default NEW.
INSERT INTO ingest_events (source_event_id, customer_code, amount)
VALUES ('EVT-001', 'C-001', 12.50);

-- Multi-row INSERT: explicit values.
INSERT INTO ingest_events (source_event_id, customer_code, amount, status)
VALUES ('EVT-002', 'C-002', 20.00, 'READY'),
       ('EVT-003', 'C-001', 7.25, 'HELD');

SELECT source_event_id, customer_code, amount, status
FROM ingest_events ORDER BY source_event_id;

-- Expected constraint failures are trapped in PL/pgSQL subtransactions.
DO $negative$
DECLARE code TEXT;
BEGIN
 BEGIN
  INSERT INTO ingest_events (source_event_id,customer_code,amount)
  VALUES ('EVT-001','C-999',1.00);
  RAISE EXCEPTION 'Duplicate test unexpectedly succeeded';
 EXCEPTION WHEN unique_violation THEN
  GET STACKED DIAGNOSTICS code = RETURNED_SQLSTATE;
  IF code <> '23505' THEN RAISE EXCEPTION 'Unexpected duplicate SQLSTATE %',code; END IF;
 END;
 BEGIN
  INSERT INTO ingest_events (source_event_id,customer_code,amount)
  VALUES ('EVT-004','C-001',-1.00);
  RAISE EXCEPTION 'Negative amount unexpectedly succeeded';
 EXCEPTION WHEN check_violation THEN
  GET STACKED DIAGNOSTICS code = RETURNED_SQLSTATE;
  IF code <> '23514' THEN RAISE EXCEPTION 'Unexpected CHECK SQLSTATE %',code; END IF;
 END;
 BEGIN
  INSERT INTO ingest_events (source_event_id,customer_code,amount,status)
  VALUES ('EVT-005','C-001',1.00,NULL);
  RAISE EXCEPTION 'Explicit NULL unexpectedly succeeded';
 EXCEPTION WHEN not_null_violation THEN
  GET STACKED DIAGNOSTICS code = RETURNED_SQLSTATE;
  IF code <> '23502' THEN RAISE EXCEPTION 'Unexpected NOT NULL SQLSTATE %',code; END IF;
 END;
END
$negative$;

DO $assert$
DECLARE actual_amount NUMERIC;
BEGIN
 SELECT sum(amount) INTO actual_amount FROM ingest_events;
 IF (SELECT count(*) FROM ingest_events) <> 3
    OR actual_amount IS DISTINCT FROM 39.75::NUMERIC
    OR (SELECT count(*) FROM ingest_events WHERE status='NEW') <> 1
    OR (SELECT count(*) FROM ingest_events WHERE status='READY') <> 1
    OR (SELECT count(*) FROM ingest_events WHERE status='HELD') <> 1
    OR (SELECT status FROM ingest_events WHERE source_event_id='EVT-001') IS DISTINCT FROM 'NEW'
 THEN RAISE EXCEPTION 'Chapter 031 reconciliation failed'; END IF;
END
$assert$;
SELECT 'PASS' AS lab_acceptance, 3 AS expected_rows,
       39.75::NUMERIC(12,2) AS expected_amount;
ROLLBACK;
