-- Chapter 118: PostgreSQL 18 read-only lab for portable query semantics.
-- This DOES NOT execute T-SQL or Oracle SQL. Calculated expectations only.
-- Run only in disposable PostgreSQL 18 database sql_tutorials.
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';

DO $guard$
BEGIN
  IF current_database() <> 'sql_tutorials'
     OR current_setting('server_version_num')::integer NOT BETWEEN 180000 AND 189999
  THEN
    RAISE EXCEPTION 'Chapter 118 requires disposable sql_tutorials on PostgreSQL 18';
  END IF;
END
$guard$;

WITH orders(order_id,region,amount) AS (
 VALUES (201,'East',25.00::numeric(10,2)),
        (202,'East',NULL::numeric(10,2)),
        (203,'West',40.00::numeric(10,2)),
        (204,'West',15.00::numeric(10,2)),
        (205,'East',20.00::numeric(10,2))
)
SELECT region,COUNT(*) AS orders,COUNT(amount) AS priced_orders,
       SUM(amount) AS revenue
FROM orders GROUP BY region ORDER BY region;
-- Calculated: East 3/2/45.00; West 2/2/55.00.

WITH orders(order_id,region) AS (
 VALUES (201,'East'),(202,'East'),(203,'West'),(204,'West'),(205,'East')
)
SELECT order_id,region FROM orders ORDER BY order_id
OFFSET 2 ROWS FETCH NEXT 2 ROWS ONLY;
-- Calculated: 203 West; 204 West.

WITH ids(id) AS (VALUES (201),(202),(203),(204),(205)),
     excluded(id) AS (VALUES (201),(202),(203),(204),(NULL::integer))
SELECT id FROM ids WHERE id NOT IN (SELECT id FROM excluded);
-- Calculated: zero rows due to NULL in exclusion set.

WITH ids(id) AS (VALUES (201),(202),(203),(204),(205)),
     excluded(id) AS (VALUES (201),(202),(203),(204),(NULL::integer))
SELECT i.id FROM ids i WHERE NOT EXISTS (
 SELECT 1 FROM excluded e WHERE e.id=i.id
);
-- Calculated: 205.

-- Duplicate-aware, bidirectional exact result assertions; fail closed.
DO $assert$
DECLARE mismatch_count integer;
BEGIN
 WITH orders(order_id,region,amount) AS (
  VALUES (201,'East',25.00::numeric(10,2)),
         (202,'East',NULL::numeric(10,2)),
         (203,'West',40.00::numeric(10,2)),
         (204,'West',15.00::numeric(10,2)),
         (205,'East',20.00::numeric(10,2))
 ),
 observed(metric,n) AS (
   SELECT 'rows'::text,COUNT(*)::numeric FROM orders
   UNION ALL SELECT 'priced',COUNT(amount)::numeric FROM orders
   UNION ALL SELECT 'nulls',(COUNT(*)-COUNT(amount))::numeric FROM orders
   UNION ALL SELECT 'revenue',SUM(amount) FROM orders
   UNION ALL SELECT 'east_rows',COUNT(*)::numeric FROM orders WHERE region='East'
   UNION ALL SELECT 'east_revenue',SUM(amount) FROM orders WHERE region='East'
   UNION ALL SELECT 'west_rows',COUNT(*)::numeric FROM orders WHERE region='West'
   UNION ALL SELECT 'west_revenue',SUM(amount) FROM orders WHERE region='West'
   UNION ALL SELECT 'page_1',(SELECT order_id::numeric FROM orders ORDER BY order_id OFFSET 2 ROWS FETCH NEXT 1 ROW ONLY)
   UNION ALL SELECT 'page_2',(SELECT order_id::numeric FROM orders ORDER BY order_id OFFSET 3 ROWS FETCH NEXT 1 ROW ONLY)
   UNION ALL SELECT 'not_in_rows',(
     WITH excluded(id) AS (VALUES (201),(202),(203),(204),(NULL::integer))
     SELECT COUNT(*)::numeric FROM orders o WHERE o.order_id NOT IN (SELECT id FROM excluded))
   UNION ALL SELECT 'not_exists_id',(
     WITH excluded(id) AS (VALUES (201),(202),(203),(204),(NULL::integer))
     SELECT MAX(o.order_id)::numeric FROM orders o WHERE NOT EXISTS (
       SELECT 1 FROM excluded e WHERE e.id=o.order_id))
 ),
 expected(metric,n) AS (
   VALUES ('rows',5::numeric),('priced',4::numeric),('nulls',1::numeric),
          ('revenue',100::numeric),('east_rows',3::numeric),('east_revenue',45::numeric),
          ('west_rows',2::numeric),('west_revenue',55::numeric),
          ('page_1',203::numeric),('page_2',204::numeric),
          ('not_in_rows',0::numeric),('not_exists_id',205::numeric)
 ),
 differences AS (
  (SELECT * FROM observed EXCEPT ALL SELECT * FROM expected)
  UNION ALL
  (SELECT * FROM expected EXCEPT ALL SELECT * FROM observed)
 )
 SELECT COUNT(*) INTO mismatch_count FROM differences;
 IF mismatch_count <> 0 THEN
   RAISE EXCEPTION 'Chapter 118 assertions failed: % mismatches',mismatch_count;
 END IF;
 RAISE NOTICE 'Chapter 118 calculated assertions matched: zero mismatches';
END
$assert$;
ROLLBACK;
