-- Chapter 057 — Numeric rounding, ratios, and safe division
-- Isolated disposable PostgreSQL 18 only; database name does not prove isolation.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';
DO $guard$
BEGIN
 IF current_setting('server_version_num')::integer NOT BETWEEN 180000 AND 189999
 THEN RAISE EXCEPTION 'PostgreSQL 18.x required: %', current_setting('server_version'); END IF;
 IF current_database() <> 'sql_tutorials'
 THEN RAISE EXCEPTION 'Wrong database: %', current_database(); END IF;
END
$guard$;
SELECT current_database() AS database_name, inet_server_addr() AS server_ip,
       inet_server_port() AS server_port, version() AS server_version;
CREATE TEMP TABLE ch057_batches (
 batch_id integer PRIMARY KEY,
 pipeline text NOT NULL,
 accepted_count integer NOT NULL CHECK (accepted_count >= 0),
 rejected_count integer NOT NULL CHECK (rejected_count >= 0)
) ON COMMIT DROP;
INSERT INTO ch057_batches VALUES
 (1,'claims',80,20),(2,'claims',45,5),(3,'events',0,0),
 (4,'events',30,10),(5,'events',9,1);
-- Integer versus exact decimal division (PostgreSQL behavior).
SELECT 5 / 2 AS integer_quotient,
       CAST(5 AS DECIMAL(10,2)) / 2 AS decimal_quotient;
SELECT batch_id, pipeline, accepted_count, rejected_count,
       accepted_count + rejected_count AS processed_count,
       ROUND(100.0 * accepted_count /
             NULLIF(accepted_count + rejected_count,0),2) AS acceptance_pct
FROM ch057_batches ORDER BY batch_id;
SELECT pipeline, SUM(accepted_count) AS accepted,
       SUM(rejected_count) AS rejected,
       SUM(accepted_count + rejected_count) AS processed,
       ROUND(100.0 * SUM(accepted_count) /
             NULLIF(SUM(accepted_count + rejected_count),0),2) AS acceptance_pct
FROM ch057_batches GROUP BY pipeline ORDER BY pipeline;
SELECT SUM(accepted_count) AS accepted,
       SUM(rejected_count) AS rejected,
       SUM(accepted_count + rejected_count) AS processed,
       ROUND(100.0 * SUM(accepted_count) /
             NULLIF(SUM(accepted_count + rejected_count),0),2) AS overall_pct
FROM ch057_batches;
SELECT ROUND(AVG(batch_pct),2) AS unweighted_mean_pct
FROM (
 SELECT 100.0 * accepted_count /
        NULLIF(accepted_count + rejected_count,0) AS batch_pct
 FROM ch057_batches
) s;
DO $checks$
DECLARE n bigint; a bigint; r bigint; p bigint; rate numeric; unweighted numeric;
BEGIN
 SELECT COUNT(*), SUM(accepted_count), SUM(rejected_count),
        SUM(accepted_count + rejected_count)
 INTO n,a,r,p FROM ch057_batches;
 IF (n,a,r,p) IS DISTINCT FROM (5::bigint,164::bigint,36::bigint,200::bigint)
 THEN RAISE EXCEPTION 'Source reconciliation failed: %, %, %, %',n,a,r,p; END IF;
 IF (SELECT 100.0 * accepted_count /
       NULLIF(accepted_count + rejected_count,0)
     FROM ch057_batches WHERE batch_id=3) IS NOT NULL
 THEN RAISE EXCEPTION 'Zero-volume batch should have NULL ratio'; END IF;
 IF (SELECT COUNT(*) FROM ch057_batches
     WHERE accepted_count + rejected_count > 0) <> 4
 THEN RAISE EXCEPTION 'Nonempty batch count mismatch'; END IF;
 IF EXISTS (
  WITH actual AS (
   SELECT pipeline, SUM(accepted_count) AS accepted,
          SUM(rejected_count) AS rejected,
          SUM(accepted_count + rejected_count) AS processed,
          ROUND(100.0 * SUM(accepted_count) /
                NULLIF(SUM(accepted_count + rejected_count),0),2) AS pct
   FROM ch057_batches GROUP BY pipeline
  ), expected(pipeline,accepted,rejected,processed,pct) AS (
   VALUES ('claims',125::bigint,25::bigint,150::bigint,83.33::numeric),
          ('events',39::bigint,11::bigint,50::bigint,78.00::numeric)
  )
  (SELECT * FROM actual EXCEPT SELECT * FROM expected)
  UNION ALL
  (SELECT * FROM expected EXCEPT SELECT * FROM actual)
 ) THEN RAISE EXCEPTION 'Pipeline KPI mismatch'; END IF;
 SELECT ROUND(100.0 * SUM(accepted_count) /
        NULLIF(SUM(accepted_count + rejected_count),0),2)
 INTO rate FROM ch057_batches;
 IF rate IS DISTINCT FROM 82.00 THEN
  RAISE EXCEPTION 'Overall rate mismatch: %',rate; END IF;
 SELECT ROUND(AVG(batch_pct),2) INTO unweighted
 FROM (SELECT 100.0 * accepted_count /
       NULLIF(accepted_count + rejected_count,0) AS batch_pct
       FROM ch057_batches) s;
 IF unweighted IS DISTINCT FROM 83.75 THEN
  RAISE EXCEPTION 'Unweighted average mismatch: %',unweighted; END IF;
 IF (SELECT 5 / 2) <> 2 OR
    (SELECT CAST(5 AS DECIMAL(10,2)) / 2) <> 2.5
 THEN RAISE EXCEPTION 'Numeric division behavior mismatch'; END IF;
 RAISE NOTICE 'Chapter 057 assertions passed in this execution';
END
$checks$;
ROLLBACK;
-- For runtime acceptance retain actual stdout/stderr, command, exit code,
-- PostgreSQL version/endpoint identity and rollback verification.
