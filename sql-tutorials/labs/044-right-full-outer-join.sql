-- Chapter 044: RIGHT and FULL OUTER JOIN; synthetic data only.
-- Run ONLY in disposable PostgreSQL 18 database sql_tutorials.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/044-right-full-outer-join.sql
BEGIN;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
DO $guard$
BEGIN
 IF current_setting('server_version_num')::integer < 180000
    OR current_database() <> 'sql_tutorials'
    OR pg_is_in_recovery() THEN
  RAISE EXCEPTION 'Requires isolated writable sql_tutorials database on PostgreSQL 18+';
 END IF;
END
$guard$;

CREATE TEMP TABLE lab044_a (
 order_id integer PRIMARY KEY, amount numeric(10,2) NOT NULL CHECK (amount >= 0)
) ON COMMIT DROP;
CREATE TEMP TABLE lab044_b (
 order_id integer PRIMARY KEY, amount numeric(10,2) NOT NULL CHECK (amount >= 0)
) ON COMMIT DROP;
INSERT INTO lab044_a VALUES (101,20.00),(102,30.00),(104,9.00);
INSERT INTO lab044_b VALUES (102,30.00),(103,15.00),(104,9.00);

-- RIGHT preserves B: 102,103,104 (103 has NULL a_id).
SELECT b.order_id, a.order_id AS a_id
FROM lab044_a a RIGHT JOIN lab044_b b ON a.order_id=b.order_id
ORDER BY b.order_id;
-- Equivalent reversed LEFT.
SELECT b.order_id, a.order_id AS a_id
FROM lab044_b b LEFT JOIN lab044_a a ON a.order_id=b.order_id
ORDER BY b.order_id;

-- FULL: 101 A_ONLY; 102 MATCHED; 103 B_ONLY; 104 MATCHED.
SELECT COALESCE(a.order_id,b.order_id) AS order_id,
       a.amount AS amount_a, b.amount AS amount_b,
       CASE WHEN a.order_id IS NULL THEN 'B_ONLY'
            WHEN b.order_id IS NULL THEN 'A_ONLY'
            ELSE 'MATCHED' END AS match_status
FROM lab044_a a FULL OUTER JOIN lab044_b b ON a.order_id=b.order_id
ORDER BY order_id;

DO $verify$
DECLARE
 a_n bigint; b_n bigint; full_n bigint; matched_n bigint;
 a_only_n bigint; b_only_n bigint; right_n bigint; reversed_n bigint;
 a_sum numeric; b_sum numeric; duplicate_n bigint; discrepancy_n bigint;
BEGIN
 SELECT count(*),sum(amount) INTO a_n,a_sum FROM lab044_a;
 SELECT count(*),sum(amount) INTO b_n,b_sum FROM lab044_b;
 SELECT count(*),
        count(*) FILTER (WHERE a.order_id IS NOT NULL AND b.order_id IS NOT NULL),
        count(*) FILTER (WHERE b.order_id IS NULL),
        count(*) FILTER (WHERE a.order_id IS NULL),
        count(*) FILTER (WHERE a.order_id IS NOT NULL AND b.order_id IS NOT NULL AND a.amount <> b.amount)
 INTO full_n,matched_n,a_only_n,b_only_n,discrepancy_n
 FROM lab044_a a FULL OUTER JOIN lab044_b b ON a.order_id=b.order_id;
 SELECT count(*) INTO right_n FROM lab044_a a RIGHT JOIN lab044_b b ON a.order_id=b.order_id;
 SELECT count(*) INTO reversed_n FROM lab044_b b LEFT JOIN lab044_a a ON a.order_id=b.order_id;
 SELECT count(*) INTO duplicate_n FROM (
  SELECT order_id FROM lab044_a GROUP BY order_id HAVING count(*)>1
  UNION ALL
  SELECT order_id FROM lab044_b GROUP BY order_id HAVING count(*)>1
 ) d;
 IF (a_n,b_n,full_n,matched_n,a_only_n,b_only_n,right_n,reversed_n,a_sum,b_sum,duplicate_n,discrepancy_n)
 IS DISTINCT FROM
 (3::bigint,3::bigint,4::bigint,2::bigint,1::bigint,1::bigint,3::bigint,3::bigint,59.00::numeric,54.00::numeric,0::bigint,0::bigint)
 THEN RAISE EXCEPTION 'Chapter 044 reconciliation failed'; END IF;
 IF full_n <> matched_n+a_only_n+b_only_n
    OR a_n <> matched_n+a_only_n OR b_n <> matched_n+b_only_n THEN
  RAISE EXCEPTION 'Chapter 044 conservation check failed'; END IF;
 RAISE NOTICE 'PASS: A 3/59.00, B 3/54.00, FULL 4, matched 2, A-only 1, B-only 1, RIGHT 3';
END
$verify$;
ROLLBACK;
-- Expected final tag ROLLBACK; no persistent tables or rows.
