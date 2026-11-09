-- Chapter 033 — UPDATE with safe predicates and preview queries
-- Disposable PostgreSQL 18 instance ONLY; independently verify connection.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/033-update-safe-predicates-preview.sql
BEGIN;
SET LOCAL lock_timeout = '2s';
SET LOCAL statement_timeout = '30s';
SET LOCAL idle_in_transaction_session_timeout = '60s';
DO $guard$
BEGIN
 IF current_setting('server_version_num')::integer NOT BETWEEN 180000 AND 189999
    OR current_database() <> 'sql_tutorials'
    OR pg_is_in_recovery()
 THEN RAISE EXCEPTION 'Unsafe version/database/standby: abort'; END IF;
END
$guard$;

CREATE TEMP TABLE order_events (
 event_id TEXT PRIMARY KEY,
 processing_status TEXT NOT NULL CHECK (processing_status IN ('pending','reviewed')),
 amount NUMERIC(12,2) NOT NULL CHECK (amount >= 0)
) ON COMMIT DROP;

INSERT INTO order_events (event_id,processing_status,amount) VALUES
 ('EV-101','pending',12.50),
 ('EV-102','pending',20.00),
 ('EV-103','reviewed',7.25),
 ('EV-104','pending',5.00);

-- Preview exact candidate rows BEFORE mutation.
SELECT event_id,processing_status,amount
FROM order_events
WHERE event_id = 'EV-102' AND processing_status = 'pending'
ORDER BY event_id;

DO $precheck$
DECLARE ids TEXT[]; total NUMERIC;
BEGIN
 SELECT array_agg(event_id ORDER BY event_id) INTO ids
 FROM order_events
 WHERE event_id = 'EV-102' AND processing_status = 'pending';
 SELECT sum(amount) INTO total FROM order_events;
 IF ids IS DISTINCT FROM ARRAY['EV-102']::TEXT[]
    OR total IS DISTINCT FROM 44.75::NUMERIC
 THEN RAISE EXCEPTION 'Preview mismatch: ids %, total %',ids,total; END IF;
END
$precheck$;

-- Record the exact returned IDs in a temporary table using a CTE.
CREATE TEMP TABLE changed_events (
 event_id TEXT PRIMARY KEY,
 processing_status TEXT NOT NULL
) ON COMMIT DROP;

WITH changed AS (
 UPDATE order_events
 SET processing_status = 'reviewed'
 WHERE event_id = 'EV-102' AND processing_status = 'pending'
 RETURNING event_id, processing_status
)
INSERT INTO changed_events (event_id,processing_status)
SELECT event_id,processing_status FROM changed;

SELECT event_id,processing_status FROM changed_events ORDER BY event_id;
SELECT event_id,processing_status,amount FROM order_events ORDER BY event_id;

DO $assert$
DECLARE changed_ids TEXT[]; pending_ids TEXT[]; reviewed_ids TEXT[];
        row_n INTEGER; total NUMERIC;
BEGIN
 SELECT array_agg(event_id ORDER BY event_id) INTO changed_ids FROM changed_events;
 SELECT array_agg(event_id ORDER BY event_id) INTO pending_ids
 FROM order_events WHERE processing_status = 'pending';
 SELECT array_agg(event_id ORDER BY event_id) INTO reviewed_ids
 FROM order_events WHERE processing_status = 'reviewed';
 SELECT count(*),sum(amount) INTO row_n,total FROM order_events;
 IF changed_ids IS DISTINCT FROM ARRAY['EV-102']::TEXT[]
    OR pending_ids IS DISTINCT FROM ARRAY['EV-101','EV-104']::TEXT[]
    OR reviewed_ids IS DISTINCT FROM ARRAY['EV-102','EV-103']::TEXT[]
    OR row_n <> 4 OR total IS DISTINCT FROM 44.75::NUMERIC
 THEN RAISE EXCEPTION 'Chapter 033 acceptance failed: changed %, pending %, reviewed %, rows %, total %',
 changed_ids,pending_ids,reviewed_ids,row_n,total; END IF;
END
$assert$;
SELECT 'PASS' AS lab_acceptance, 1 AS expected_updated,
       2 AS expected_pending, 2 AS expected_reviewed,
       44.75::NUMERIC(12,2) AS expected_total;
ROLLBACK;
