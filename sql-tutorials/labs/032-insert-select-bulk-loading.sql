-- Chapter 032: INSERT SELECT and bulk-loading fundamentals
-- Isolated PostgreSQL 18 disposable sql_tutorials database only.
-- Verify actual host, port, user, container and credentials independently.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/032-insert-select-bulk-loading.sql
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

CREATE TEMP TABLE staging_events (
 event_id TEXT PRIMARY KEY,
 customer_id TEXT NOT NULL,
 raw_amount NUMERIC(12,2)
) ON COMMIT DROP;
CREATE TEMP TABLE curated_events (
 event_id TEXT PRIMARY KEY,
 customer_id TEXT NOT NULL,
 amount NUMERIC(12,2) NOT NULL CHECK (amount >= 0)
) ON COMMIT DROP;

INSERT INTO staging_events(event_id,customer_id,raw_amount) VALUES
 ('EV-101','C-01',12.50),
 ('EV-102','C-02',20.00),
 ('EV-103','C-03',-4.00),
 ('EV-104','C-01',7.25),
 ('EV-105','C-04',NULL);

-- Preview before modification.
SELECT event_id, customer_id, raw_amount,
 CASE WHEN raw_amount IS NULL THEN 'REJECT_NULL'
      WHEN raw_amount < 0 THEN 'REJECT_NEGATIVE'
      ELSE 'ACCEPT' END AS decision
FROM staging_events ORDER BY event_id;

INSERT INTO curated_events(event_id,customer_id,amount)
SELECT event_id,customer_id,raw_amount
FROM staging_events
WHERE raw_amount IS NOT NULL AND raw_amount >= 0;

SELECT event_id, customer_id, amount FROM curated_events ORDER BY event_id;

DO $assert$
DECLARE source_n INTEGER; accepted_n INTEGER; rejected_n INTEGER;
        total NUMERIC; ids TEXT[];
BEGIN
 SELECT count(*) INTO source_n FROM staging_events;
 SELECT count(*),coalesce(sum(amount),0),array_agg(event_id ORDER BY event_id)
 INTO accepted_n,total,ids FROM curated_events;
 SELECT count(*) INTO rejected_n FROM staging_events
 WHERE raw_amount IS NULL OR raw_amount < 0;
 IF source_n <> 5 OR accepted_n <> 3 OR rejected_n <> 2
    OR source_n <> accepted_n + rejected_n
    OR total IS DISTINCT FROM 39.75::NUMERIC
    OR ids IS DISTINCT FROM ARRAY['EV-101','EV-102','EV-104']::TEXT[]
 THEN RAISE EXCEPTION 'Chapter 032 reconciliation failed: source %, accepted %, rejected %, total %, ids %',
 source_n,accepted_n,rejected_n,total,ids; END IF;
END
$assert$;
SELECT 'PASS' AS lab_acceptance, 5 AS expected_source,
       3 AS expected_accepted, 2 AS expected_rejected,
       39.75::NUMERIC(12,2) AS expected_total;
ROLLBACK;
