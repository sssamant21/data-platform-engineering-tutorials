-- Chapter 056: Text transformations for reporting — isolated PostgreSQL 18 lab
-- Confirm the endpoint is disposable; database-name checks alone cannot prove isolation.
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
SELECT current_database() AS isolated_database, inet_server_addr() AS server_ip, inet_server_port() AS server_port, version() AS server_version;
CREATE TEMP TABLE ch056_payments (
 event_id integer PRIMARY KEY,
 region_raw text,
 status_raw text,
 amount numeric(12,2) NOT NULL
) ON COMMIT DROP;
INSERT INTO ch056_payments VALUES
 (1, '  North  ', '  CAPTURED ', 20.00),
 (2, 'north', 'captured', 30.00),
 (3, ' SOUTH ', ' Pending ', 15.00),
 (4, 'South', 'CAPTURED', 40.00),
 (5, NULL, 'captured', 10.00),
 (6, '  West  ', NULL, 5.00);
-- Preserve original values for audit; normalize only in derived query expressions.
SELECT event_id, region_raw, status_raw, amount FROM ch056_payments ORDER BY event_id;
WITH normalized AS (
 SELECT event_id, COALESCE(UPPER(TRIM(region_raw)), 'UNKNOWN') AS region,
        COALESCE(UPPER(TRIM(status_raw)), 'UNKNOWN') AS status, amount
 FROM ch056_payments
)
SELECT region, COUNT(*) AS events, SUM(amount) AS total
FROM normalized GROUP BY region ORDER BY region;
WITH normalized AS (
 SELECT COALESCE(UPPER(TRIM(status_raw)), 'UNKNOWN') AS status, amount
 FROM ch056_payments
)
SELECT status, COUNT(*) AS events, SUM(amount) AS total
FROM normalized GROUP BY status ORDER BY status;
SELECT UPPER(TRIM(region_raw)) AS normalized_region,
       COUNT(*) AS rows_in_group, COUNT(DISTINCT region_raw) AS raw_spellings
FROM ch056_payments WHERE region_raw IS NOT NULL
GROUP BY UPPER(TRIM(region_raw)) ORDER BY normalized_region;
SELECT event_id,
       'REGION=' || COALESCE(UPPER(TRIM(region_raw)), 'UNKNOWN')
       || '; STATUS=' || COALESCE(UPPER(TRIM(status_raw)), 'UNKNOWN') AS display_label
FROM ch056_payments ORDER BY event_id;
-- Blank-string policy is distinct from NULL policy.
SELECT TRIM('   ') AS blank_after_trim,
       COALESCE(NULLIF(TRIM('   '), ''), 'UNKNOWN') AS blank_as_missing,
       REPLACE('A-B', '-', ' ') AS replaced,
       CHAR_LENGTH('A B') AS character_count;
DO $checks$
DECLARE n bigint; total numeric;
BEGIN
 SELECT COUNT(*), SUM(amount) INTO n,total FROM ch056_payments;
 IF n IS DISTINCT FROM 6 OR total IS DISTINCT FROM 120.00
 THEN RAISE EXCEPTION 'Source count/total mismatch: %, %',n,total; END IF;
 IF EXISTS (
  WITH actual AS (
   SELECT COALESCE(UPPER(TRIM(region_raw)), 'UNKNOWN') AS label,
          COUNT(*) AS n, SUM(amount) AS total
   FROM ch056_payments GROUP BY 1
  ), expected(label,n,total) AS (
   VALUES ('NORTH',2::bigint,50.00::numeric),
          ('SOUTH',2::bigint,55.00::numeric),
          ('UNKNOWN',1::bigint,10.00::numeric),
          ('WEST',1::bigint,5.00::numeric)
  )
  (SELECT * FROM actual EXCEPT SELECT * FROM expected)
  UNION ALL
  (SELECT * FROM expected EXCEPT SELECT * FROM actual)
 ) THEN RAISE EXCEPTION 'Region report mismatch'; END IF;
 IF EXISTS (
  WITH actual AS (
   SELECT COALESCE(UPPER(TRIM(status_raw)), 'UNKNOWN') AS label,
          COUNT(*) AS n, SUM(amount) AS total
   FROM ch056_payments GROUP BY 1
  ), expected(label,n,total) AS (
   VALUES ('CAPTURED',4::bigint,100.00::numeric),
          ('PENDING',1::bigint,15.00::numeric),
          ('UNKNOWN',1::bigint,5.00::numeric)
  )
  (SELECT * FROM actual EXCEPT SELECT * FROM expected)
  UNION ALL
  (SELECT * FROM expected EXCEPT SELECT * FROM actual)
 ) THEN RAISE EXCEPTION 'Status report mismatch'; END IF;
 IF (SELECT COUNT(DISTINCT region_raw) FROM ch056_payments
     WHERE UPPER(TRIM(region_raw))='NORTH') IS DISTINCT FROM 2
 THEN RAISE EXCEPTION 'North spelling count mismatch'; END IF;
 IF (SELECT COUNT(DISTINCT region_raw) FROM ch056_payments
     WHERE UPPER(TRIM(region_raw))='SOUTH') IS DISTINCT FROM 2
 THEN RAISE EXCEPTION 'South spelling count mismatch'; END IF;
 IF COALESCE(NULLIF(TRIM('   '),''),'UNKNOWN') IS DISTINCT FROM 'UNKNOWN'
 THEN RAISE EXCEPTION 'Blank normalization mismatch'; END IF;
 RAISE NOTICE 'Chapter 056 assertions passed in this execution';
END
$checks$;
ROLLBACK;
-- Record server identity, command, stdout/stderr, exit status, and rollback evidence for runtime acceptance.
