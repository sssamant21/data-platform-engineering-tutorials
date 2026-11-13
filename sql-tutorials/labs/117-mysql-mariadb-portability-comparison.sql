-- Chapter 117: PostgreSQL 18 read-only comparison lab.
-- Synthetic data only. Execute ONLY on a separate disposable PostgreSQL 18
-- instance with database sql_tutorials; never on production.
-- Calculated expectations, NOT observed runtime results.
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';

DO $guard$
BEGIN
  IF current_database() <> 'sql_tutorials'
     OR current_setting('server_version_num')::integer NOT BETWEEN 180000 AND 189999
  THEN
    RAISE EXCEPTION 'Requires disposable sql_tutorials database on PostgreSQL 18';
  END IF;
END
$guard$;

-- All observations are portable-style PostgreSQL queries, NOT MySQL tests.
WITH orders(order_id, region, amount) AS (
  VALUES (101,'East',40.00::numeric(10,2)),
         (102,'east',20.00::numeric(10,2)),
         (103,'West',NULL::numeric(10,2)),
         (104,'West',60.00::numeric(10,2))
)
SELECT COUNT(*) AS rows_total, COUNT(amount) AS known_amounts,
       COUNT(*)-COUNT(amount) AS null_amounts,
       SUM(amount) AS known_total
FROM orders;
-- Expected: 4, 3, 1, 120.00

WITH orders(order_id, region, amount) AS (
  VALUES (101,'East',40.00::numeric(10,2)),
         (102,'east',20.00::numeric(10,2)),
         (103,'West',NULL::numeric(10,2)),
         (104,'West',60.00::numeric(10,2))
)
SELECT lower(region) AS region_key, COUNT(*) AS orders,
       SUM(COALESCE(amount,0)) AS total
FROM orders GROUP BY lower(region) ORDER BY region_key;
-- Expected: east 2 60.00; west 2 60.00

WITH orders(order_id, region) AS (
  VALUES (101,'East'),(102,'east'),(103,'West'),(104,'West')
)
SELECT order_id,region FROM orders ORDER BY order_id LIMIT 2 OFFSET 1;
-- Expected: 102/east, 103/West

WITH ids(id) AS (VALUES (101),(102),(103),(104)),
     excluded(id) AS (VALUES (101),(102),(103),(NULL::integer))
SELECT id FROM ids WHERE id NOT IN (SELECT id FROM excluded) ORDER BY id;
-- Expected: no rows due to NULL in subquery

WITH ids(id) AS (VALUES (101),(102),(103),(104)),
     excluded(id) AS (VALUES (101),(102),(103),(NULL::integer))
SELECT i.id FROM ids AS i
WHERE NOT EXISTS (SELECT 1 FROM excluded AS e WHERE e.id = i.id)
ORDER BY i.id;
-- Expected: 104

-- Fail-closed exact-result assertion using duplicate-aware multiset comparison.
DO $assert$
DECLARE mismatch_count integer;
BEGIN
  WITH orders(order_id,region,amount) AS (
    VALUES (101,'East',40.00::numeric(10,2)),
           (102,'east',20.00::numeric(10,2)),
           (103,'West',NULL::numeric(10,2)),
           (104,'West',60.00::numeric(10,2))
  ),
  observed AS (
    SELECT 'summary'::text AS metric, COUNT(*)::numeric AS n FROM orders
    UNION ALL SELECT 'known', COUNT(amount)::numeric FROM orders
    UNION ALL SELECT 'nulls', (COUNT(*)-COUNT(amount))::numeric FROM orders
    UNION ALL SELECT 'total', SUM(amount) FROM orders
    UNION ALL SELECT 'east_total', SUM(COALESCE(amount,0)) FROM orders WHERE lower(region)='east'
    UNION ALL SELECT 'west_total', SUM(COALESCE(amount,0)) FROM orders WHERE lower(region)='west'
    UNION ALL SELECT 'page_first', (SELECT order_id::numeric FROM orders ORDER BY order_id LIMIT 1 OFFSET 1)
    UNION ALL SELECT 'page_second', (SELECT order_id::numeric FROM orders ORDER BY order_id LIMIT 1 OFFSET 2)
  ),
  expected(metric,n) AS (
    VALUES ('summary',4::numeric),('known',3::numeric),('nulls',1::numeric),
           ('total',120::numeric),('east_total',60::numeric),('west_total',60::numeric),
           ('page_first',102::numeric),('page_second',103::numeric)
  ),
  differences AS (
    (SELECT * FROM observed EXCEPT ALL SELECT * FROM expected)
    UNION ALL
    (SELECT * FROM expected EXCEPT ALL SELECT * FROM observed)
  )
  SELECT COUNT(*) INTO mismatch_count FROM differences;
  IF mismatch_count <> 0 THEN
    RAISE EXCEPTION 'Chapter 117 calculated assertions failed: % mismatches', mismatch_count;
  END IF;
  RAISE NOTICE 'Chapter 117 calculated assertions matched: 0 mismatches';
END
$assert$;
ROLLBACK;
