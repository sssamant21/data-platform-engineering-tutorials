-- Chapter 060: Monthly ingestion KPI capstone. SYNTHETIC DATA ONLY.
-- Execute ONLY on a separately verified disposable PostgreSQL 18 instance.
-- Run: psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f 060-lab-06-monthly-kpi-report.sql
-- Database name/version checks do NOT prove that an endpoint is isolated.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';
SET LOCAL TIME ZONE 'UTC';
DO $guard$
BEGIN
 IF current_setting('server_version_num')::integer NOT BETWEEN 180000 AND 189999
 THEN RAISE EXCEPTION 'PostgreSQL 18.x required'; END IF;
 IF current_database() <> 'sql_tutorials'
 THEN RAISE EXCEPTION 'Wrong database: %', current_database(); END IF;
END $guard$;
SELECT current_database() AS database_name, inet_server_addr() AS server_ip,
 inet_server_port() AS server_port, version() AS server_version;
CREATE TEMP TABLE ch060_batches (
 batch_id integer PRIMARY KEY,
 received_at timestamptz NOT NULL,
 source_system text NOT NULL CHECK (source_system IN ('api','file')),
 accepted integer NOT NULL CHECK (accepted >= 0),
 rejected integer NOT NULL CHECK (rejected >= 0)
) ON COMMIT DROP;
INSERT INTO ch060_batches VALUES
 (1,'2026-01-05 10:00+00','api',90,10),
 (2,'2026-01-31 23:59+00','file',40,10),
 (3,'2026-02-01 00:00+00','api',60,20),
 (4,'2026-02-15 12:00+00','file',20,0),
 (5,'2026-03-01 00:00+00','api',95,5),
 (6,'2026-03-20 15:00+00','file',45,5),
 (7,'2026-03-21 09:00+00','api',0,0),
 (8,'2026-03-31 23:59+00','file',30,10);
-- Portable core: CASE + SUM + GROUP BY; PostgreSQL-specific UTC bucket expression.
SELECT date_trunc('month', received_at AT TIME ZONE 'UTC')::date AS month_start,
 COUNT(*) AS batches,
 SUM(accepted) AS accepted,
 SUM(rejected) AS rejected,
 SUM(accepted + rejected) AS processed,
 ROUND(100.0 * SUM(accepted) / NULLIF(SUM(accepted + rejected),0),2) AS acceptance_pct,
 SUM(CASE WHEN source_system='api' THEN accepted + rejected ELSE 0 END) AS api_processed,
 SUM(CASE WHEN source_system='file' THEN accepted + rejected ELSE 0 END) AS file_processed
FROM ch060_batches
WHERE received_at >= TIMESTAMPTZ '2026-01-01 00:00+00'
  AND received_at < TIMESTAMPTZ '2026-04-01 00:00+00'
GROUP BY 1 ORDER BY 1;
-- Overall weighted rate, NOT the arithmetic mean of monthly percentages.
SELECT COUNT(*) AS batches, SUM(accepted) AS accepted,
 SUM(rejected) AS rejected, SUM(accepted+rejected) AS processed,
 ROUND(100.0 * SUM(accepted)/NULLIF(SUM(accepted+rejected),0),2) AS acceptance_pct
FROM ch060_batches;
-- Zero-denominator demonstration: NULL is intentional for an empty batch.
SELECT batch_id,
 ROUND(100.0 * accepted / NULLIF(accepted+rejected,0),2) AS acceptance_pct
FROM ch060_batches WHERE batch_id=7;
DO $assert$
DECLARE n bigint; a bigint; r bigint; p bigint; rate numeric; months bigint;
BEGIN
 SELECT COUNT(*),SUM(accepted),SUM(rejected),SUM(accepted+rejected),
 ROUND(100.0*SUM(accepted)/NULLIF(SUM(accepted+rejected),0),2)
 INTO n,a,r,p,rate FROM ch060_batches;
 IF (n,a,r,p,rate) IS DISTINCT FROM (8::bigint,380::bigint,60::bigint,440::bigint,86.36::numeric)
 THEN RAISE EXCEPTION 'Grand totals mismatch'; END IF;
 WITH monthly AS (
  SELECT date_trunc('month',received_at AT TIME ZONE 'UTC')::date AS m,
   COUNT(*) AS n, SUM(accepted) AS a, SUM(rejected) AS r,
   SUM(accepted+rejected) AS p,
   SUM(CASE WHEN source_system='api' THEN accepted+rejected ELSE 0 END) AS api,
   SUM(CASE WHEN source_system='file' THEN accepted+rejected ELSE 0 END) AS file
  FROM ch060_batches GROUP BY 1
 ), expected(m,n,a,r,p,api,file) AS (
  VALUES ('2026-01-01'::date,2::bigint,130::bigint,20::bigint,150::bigint,100::bigint,50::bigint),
         ('2026-02-01'::date,2::bigint,80::bigint,20::bigint,100::bigint,80::bigint,20::bigint),
         ('2026-03-01'::date,4::bigint,170::bigint,20::bigint,190::bigint,100::bigint,90::bigint)
 )
 SELECT COUNT(*) INTO months FROM (
  (SELECT * FROM monthly EXCEPT ALL SELECT * FROM expected)
  UNION ALL
  (SELECT * FROM expected EXCEPT ALL SELECT * FROM monthly)
 ) diffs;
 IF months <> 0 THEN RAISE EXCEPTION 'Monthly reconciliation mismatch'; END IF;
 IF EXISTS (SELECT 1 FROM ch060_batches WHERE accepted+rejected < 0)
 THEN RAISE EXCEPTION 'Invalid batch'; END IF;
 IF (SELECT COUNT(*) FROM ch060_batches WHERE accepted+rejected=0) <> 1
 THEN RAISE EXCEPTION 'Zero denominator fixture mismatch'; END IF;
 RAISE NOTICE 'Chapter 060 deterministic assertions passed in this execution';
END $assert$;
ROLLBACK;
-- Runtime certification requires retained psql output, exit status, server identity,
-- Docker/container identity, and rollback evidence. This file alone proves none of these.
