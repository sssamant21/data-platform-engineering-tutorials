-- Chapter 028: ALTER TABLE, rename and safe schema changes
-- Run ONLY on independently verified disposable PostgreSQL 18 primary database sql_tutorials.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/028-alter-table-safe-schema-changes.sql
-- Synthetic data, temporary objects, transaction rollback. Runtime validation PENDING.
BEGIN;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';
DO $guard$
BEGIN
 IF current_setting('server_version_num')::integer NOT BETWEEN 180000 AND 189999
    OR current_database() <> 'sql_tutorials'
    OR pg_is_in_recovery() THEN
  RAISE EXCEPTION 'Requires independently isolated PostgreSQL 18 primary sql_tutorials';
 END IF;
END
$guard$;

CREATE TEMP TABLE ch028_events (
 event_id integer PRIMARY KEY,
 event_code text NOT NULL UNIQUE,
 amount numeric(10,2) NOT NULL
) ON COMMIT DROP;
INSERT INTO ch028_events VALUES (1,'SYN-A',12.50),(2,'SYN-B',7.25);

ALTER TABLE ch028_events ADD COLUMN source_system text;
-- Existing rows are NULL. Default applies to subsequent inserts, not old rows.
ALTER TABLE ch028_events ALTER COLUMN source_system SET DEFAULT 'batch';
DO $pre$
BEGIN
 IF (SELECT COUNT(*) FROM ch028_events WHERE source_system IS NULL) <> 2 THEN
  RAISE EXCEPTION 'Existing NULL semantics assertion failed';
 END IF;
END
$pre$;
UPDATE ch028_events SET source_system = 'legacy' WHERE source_system IS NULL;
ALTER TABLE ch028_events RENAME COLUMN source_system TO ingestion_source;
ALTER TABLE ch028_events ADD CONSTRAINT ch028_amount_nonnegative CHECK (amount >= 0);
ALTER TABLE ch028_events ALTER COLUMN ingestion_source SET NOT NULL;
INSERT INTO ch028_events (event_id,event_code,amount) VALUES (3,'SYN-C',5.00);

DO $negative$
DECLARE check_rejected boolean := false; duplicate_rejected boolean := false;
BEGIN
 BEGIN
  INSERT INTO ch028_events (event_id,event_code,amount) VALUES (4,'SYN-BAD',-1.00);
 EXCEPTION WHEN check_violation THEN check_rejected := true;
 END;
 BEGIN
  INSERT INTO ch028_events (event_id,event_code,amount) VALUES (4,'SYN-A',2.00);
 EXCEPTION WHEN unique_violation THEN duplicate_rejected := true;
 END;
 IF NOT check_rejected OR NOT duplicate_rejected THEN
  RAISE EXCEPTION 'Expected constraint rejection absent: check %, duplicate %',
   check_rejected,duplicate_rejected;
 END IF;
END
$negative$;

SELECT event_id,event_code,amount,ingestion_source
FROM ch028_events ORDER BY event_id;
-- Expected: (1,SYN-A,12.50,legacy),(2,SYN-B,7.25,legacy),(3,SYN-C,5.00,batch).
DO $assert$
DECLARE n bigint; total numeric; legacy_n bigint; batch_n bigint; null_n bigint;
BEGIN
 SELECT COUNT(*), SUM(amount),
        COUNT(*) FILTER (WHERE ingestion_source = 'legacy'),
        COUNT(*) FILTER (WHERE ingestion_source = 'batch'),
        COUNT(*) FILTER (WHERE ingestion_source IS NULL)
 INTO n,total,legacy_n,batch_n,null_n FROM ch028_events;
 IF n <> 3 OR total IS DISTINCT FROM 24.75::numeric
    OR legacy_n <> 2 OR batch_n <> 1 OR null_n <> 0
    OR NOT EXISTS (SELECT 1 FROM ch028_events WHERE event_id=3 AND event_code='SYN-C' AND ingestion_source='batch')
 THEN
  RAISE EXCEPTION 'Chapter 028 assertion failed: n %, total %, legacy %, batch %, null %',
    n,total,legacy_n,batch_n,null_n;
 END IF;
 RAISE NOTICE 'Chapter 028 synthetic assertions passed';
END
$assert$;
ROLLBACK;
-- Temporary objects created in this transaction are discarded. No persistent changes.
