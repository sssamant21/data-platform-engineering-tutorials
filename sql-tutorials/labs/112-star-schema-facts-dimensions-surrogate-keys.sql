-- Chapter 112: Star schemas, facts, dimensions, surrogate keys
-- Synthetic only. Intended for disposable PostgreSQL 18 database sql_tutorials.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/112-star-schema-facts-dimensions-surrogate-keys.sql
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';

DO $guard$
BEGIN
  IF current_database() <> 'sql_tutorials' THEN
    RAISE EXCEPTION 'Expected disposable sql_tutorials database; got %', current_database();
  END IF;
  IF current_setting('server_version_num')::integer NOT BETWEEN 180000 AND 189999 THEN
    RAISE EXCEPTION 'Requires PostgreSQL 18; got %', current_setting('server_version');
  END IF;
END
$guard$;

-- Category revenue at the fact's order-line grain.
WITH dim_product(product_sk, product_code, category, valid_from, valid_to) AS (
  VALUES (101,'SKU-A','Basic',DATE '2026-01-01',DATE '2026-02-01'),
         (102,'SKU-A','Premium',DATE '2026-02-01',NULL::date),
         (201,'SKU-B','Basic',DATE '2026-01-01',NULL::date)
), fact_sales(order_id,line_no,sale_date,product_sk,net_amount) AS (
  VALUES (5001,1,DATE '2026-01-15',101,30.00::numeric),
         (5001,2,DATE '2026-01-15',201,20.00::numeric),
         (5002,1,DATE '2026-02-10',102,40.00::numeric),
         (5003,1,DATE '2026-02-12',201,10.00::numeric)
)
SELECT d.category, count(*) AS line_count, sum(f.net_amount) AS revenue
FROM fact_sales f JOIN dim_product d USING (product_sk)
GROUP BY d.category ORDER BY d.category;

-- Fail-closed exact assertions, including demonstration of a wrong business-key join.
DO $assert$
DECLARE
  fact_count integer; dimension_count integer; correct_total numeric;
  wrong_count integer; wrong_total numeric; missing_matches integer;
  invalid_scd_matches integer; mismatch_count integer;
BEGIN
  WITH dim_product(product_sk,product_code,category,valid_from,valid_to) AS (
    VALUES (101,'SKU-A','Basic',DATE '2026-01-01',DATE '2026-02-01'),
           (102,'SKU-A','Premium',DATE '2026-02-01',NULL::date),
           (201,'SKU-B','Basic',DATE '2026-01-01',NULL::date)
  ), fact_sales(order_id,line_no,sale_date,product_sk,product_code,net_amount) AS (
    VALUES (5001,1,DATE '2026-01-15',101,'SKU-A',30.00::numeric),
           (5001,2,DATE '2026-01-15',201,'SKU-B',20.00::numeric),
           (5002,1,DATE '2026-02-10',102,'SKU-A',40.00::numeric),
           (5003,1,DATE '2026-02-12',201,'SKU-B',10.00::numeric)
  ), actual AS (
    SELECT d.category, count(*) AS n, sum(f.net_amount) AS revenue
    FROM fact_sales f JOIN dim_product d USING (product_sk)
    GROUP BY d.category
  ), expected(category,n,revenue) AS (
    VALUES ('Basic',3::bigint,60.00::numeric),
           ('Premium',1::bigint,40.00::numeric)
  ), diffs AS (
    (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected)
    UNION ALL
    (SELECT * FROM expected EXCEPT ALL SELECT * FROM actual)
  )
  SELECT
    (SELECT count(*) FROM fact_sales),
    (SELECT count(*) FROM dim_product),
    (SELECT sum(net_amount) FROM fact_sales),
    (SELECT count(*) FROM fact_sales f JOIN dim_product d USING(product_code)),
    (SELECT sum(f.net_amount) FROM fact_sales f JOIN dim_product d USING(product_code)),
    (SELECT count(*) FROM fact_sales f LEFT JOIN dim_product d USING(product_sk) WHERE d.product_sk IS NULL),
    (SELECT count(*) FROM fact_sales f JOIN dim_product d USING(product_sk)
      WHERE f.sale_date < d.valid_from OR (d.valid_to IS NOT NULL AND f.sale_date >= d.valid_to)),
    (SELECT count(*) FROM diffs)
  INTO fact_count,dimension_count,correct_total,wrong_count,wrong_total,
       missing_matches,invalid_scd_matches,mismatch_count;

  IF (fact_count,dimension_count,correct_total,wrong_count,wrong_total,
      missing_matches,invalid_scd_matches,mismatch_count)
     IS DISTINCT FROM (4,3,100.00::numeric,6,170.00::numeric,0,0,0) THEN
    RAISE EXCEPTION 'Chapter 112 synthetic assertions failed: facts %, dims %, total %, wrong rows %, wrong total %, missing %, invalid version %, mismatches %',
      fact_count,dimension_count,correct_total,wrong_count,wrong_total,
      missing_matches,invalid_scd_matches,mismatch_count;
  END IF;
  RAISE NOTICE 'Chapter 112 synthetic assertions passed: 4 facts, 3 versions, 100.00 revenue, 6 incorrect join rows, 170.00 incorrect sum, zero mismatches';
END
$assert$;

ROLLBACK;
