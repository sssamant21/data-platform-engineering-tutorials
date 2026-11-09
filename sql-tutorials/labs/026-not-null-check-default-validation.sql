-- Chapter 026: NOT NULL, CHECK, DEFAULT and constraint validation
-- ONLY on an independently verified disposable PostgreSQL 18 primary sql_tutorials.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/026-not-null-check-default-validation.sql
-- Synthetic data; temporary objects; rollback-only. Runtime validation pending.
BEGIN;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';
DO $guard$
BEGIN
 IF current_setting('server_version_num')::integer NOT BETWEEN 180000 AND 189999
    OR current_database() <> 'sql_tutorials' OR pg_is_in_recovery() THEN
   RAISE EXCEPTION 'Requires independently isolated PostgreSQL 18 primary sql_tutorials';
 END IF;
END
$guard$;

CREATE TEMP TABLE ch026_runs (
 run_id integer PRIMARY KEY,
 service_name varchar(40) NOT NULL,
 status varchar(12) NOT NULL DEFAULT 'queued',
 attempts integer NOT NULL DEFAULT 0,
 CONSTRAINT ch026_status_ck CHECK (status IN ('queued','running','done','failed')),
 CONSTRAINT ch026_attempts_ck CHECK (attempts >= 0)
) ON COMMIT DROP;

INSERT INTO ch026_runs (run_id,service_name) VALUES (101,'ingest-a');
INSERT INTO ch026_runs (run_id,service_name,status,attempts)
VALUES (102,'ingest-b','running',2),(103,'ingest-c','done',1);

SELECT run_id,service_name,status,attempts FROM ch026_runs ORDER BY run_id;
-- Expected: 101 ingest-a queued 0; 102 ingest-b running 2; 103 ingest-c done 1.
SELECT status,COUNT(*) AS run_count FROM ch026_runs GROUP BY status ORDER BY status;
-- Expected: done=1, queued=1, running=1.

DO $negative_tests$
DECLARE null_service boolean := false; negative_attempts boolean := false;
        invalid_status boolean := false; explicit_null_status boolean := false;
BEGIN
 BEGIN
  INSERT INTO ch026_runs (run_id,service_name) VALUES (104,NULL);
 EXCEPTION WHEN not_null_violation THEN null_service := true;
 END;
 BEGIN
  INSERT INTO ch026_runs (run_id,service_name,attempts) VALUES (105,'ingest-x',-1);
 EXCEPTION WHEN check_violation THEN negative_attempts := true;
 END;
 BEGIN
  INSERT INTO ch026_runs (run_id,service_name,status) VALUES (106,'ingest-x','unknown');
 EXCEPTION WHEN check_violation THEN invalid_status := true;
 END;
 BEGIN
  INSERT INTO ch026_runs (run_id,service_name,status) VALUES (107,'ingest-x',NULL);
 EXCEPTION WHEN not_null_violation THEN explicit_null_status := true;
 END;
 IF NOT (null_service AND negative_attempts AND invalid_status AND explicit_null_status) THEN
  RAISE EXCEPTION 'Chapter 026 negative tests did not all reject as expected';
 END IF;
 RAISE NOTICE 'Chapter 026 expected 23502/23514 violations rejected';
END
$negative_tests$;

-- Read-only reconciliation of synthetic legacy rows, BEFORE adding a constraint.
WITH legacy(run_id,service_name,status,attempts) AS (
 VALUES
 (1,'ingest-a','queued',0),
 (2,'ingest-b','running',2),
 (3,NULL::text,'done',1),
 (4,'ingest-d','queued',-1),
 (5,'ingest-e','unknown',0)
)
SELECT COUNT(*) AS invalid_rows
FROM legacy
WHERE service_name IS NULL OR status IS NULL OR attempts IS NULL
   OR status NOT IN ('queued','running','done','failed') OR attempts < 0;
-- Expected invalid_rows = 3.

DO $assert$
DECLARE n bigint; queued bigint; attempts_sum bigint; invalid bigint;
BEGIN
 SELECT COUNT(*),COUNT(*) FILTER (WHERE status='queued'),SUM(attempts)
 INTO n,queued,attempts_sum FROM ch026_runs;
 WITH legacy(service_name,status,attempts) AS (
  VALUES ('ingest-a'::text,'queued'::text,0),
         ('ingest-b','running',2),
         (NULL::text,'done',1),
         ('ingest-d','queued',-1),
         ('ingest-e','unknown',0)
 )
 SELECT COUNT(*) INTO invalid FROM legacy
 WHERE service_name IS NULL OR status IS NULL OR attempts IS NULL
    OR status NOT IN ('queued','running','done','failed') OR attempts < 0;
 IF n <> 3 OR queued <> 1 OR attempts_sum <> 3 OR invalid <> 3 THEN
  RAISE EXCEPTION 'Chapter 026 assertions failed: rows %, queued %, attempts %, invalid %',
    n,queued,attempts_sum,invalid;
 END IF;
 RAISE NOTICE 'Chapter 026 synthetic assertions passed';
END
$assert$;
ROLLBACK;
-- All temporary DDL and data discarded; no persistent changes.
