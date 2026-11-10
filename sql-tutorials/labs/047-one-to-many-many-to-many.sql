-- Chapter 047: synthetic 1:N and M:N relationships.
-- Run ONLY in a disposable PostgreSQL 18+ database named sql_tutorials.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/047-one-to-many-many-to-many.sql
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
CREATE TEMP TABLE lab047_customers (
 customer_id integer PRIMARY KEY, customer_name text NOT NULL
) ON COMMIT DROP;
CREATE TEMP TABLE lab047_orders (
 order_id integer PRIMARY KEY,
 customer_id integer NOT NULL REFERENCES lab047_customers(customer_id),
 amount numeric(12,2) NOT NULL CHECK (amount >= 0)
) ON COMMIT DROP;
CREATE TEMP TABLE lab047_products (
 product_id integer PRIMARY KEY, product_name text NOT NULL
) ON COMMIT DROP;
CREATE TEMP TABLE lab047_tags (
 tag_id integer PRIMARY KEY, tag_name text NOT NULL UNIQUE
) ON COMMIT DROP;
CREATE TEMP TABLE lab047_product_tags (
 product_id integer NOT NULL REFERENCES lab047_products(product_id),
 tag_id integer NOT NULL REFERENCES lab047_tags(tag_id),
 PRIMARY KEY (product_id,tag_id)
) ON COMMIT DROP;
INSERT INTO lab047_customers VALUES (1,'Ana'),(2,'Ben'),(3,'Cleo');
INSERT INTO lab047_orders VALUES (101,1,30.00),(102,1,20.00),(103,2,15.00);
INSERT INTO lab047_products VALUES (1,'Keyboard'),(2,'Mouse'),(3,'Notebook');
INSERT INTO lab047_tags VALUES (1,'Office'),(2,'Tech');
INSERT INTO lab047_product_tags VALUES (1,1),(1,2),(2,2),(3,1);

-- One-to-many: Cleo appears once with NULL order fields.
SELECT c.customer_id,c.customer_name,o.order_id,o.amount
FROM lab047_customers c LEFT JOIN lab047_orders o ON o.customer_id=c.customer_id
ORDER BY c.customer_id,o.order_id;

-- Many-to-many: 4 association rows.
SELECT p.product_name,t.tag_name
FROM lab047_products p
JOIN lab047_product_tags pt ON pt.product_id=p.product_id
JOIN lab047_tags t ON t.tag_id=pt.tag_id
ORDER BY p.product_id,t.tag_name;

-- Preserve correct customer grain.
WITH order_totals AS (
 SELECT customer_id,COUNT(*) AS order_count,SUM(amount) AS total_amount
 FROM lab047_orders GROUP BY customer_id
)
SELECT c.customer_name,COALESCE(o.order_count,0) AS order_count,
       COALESCE(o.total_amount,0) AS total_amount
FROM lab047_customers c LEFT JOIN order_totals o ON o.customer_id=c.customer_id
ORDER BY c.customer_id;

-- Per-tag counts (Office=2, Tech=2).
SELECT t.tag_name,COUNT(pt.product_id) AS product_count
FROM lab047_tags t LEFT JOIN lab047_product_tags pt ON pt.tag_id=t.tag_id
GROUP BY t.tag_id,t.tag_name ORDER BY t.tag_name;

DO $verify$
DECLARE v_customers bigint; v_orders bigint; v_left bigint; v_total numeric;
        v_products bigint; v_tags bigint; v_links bigint; v_dups bigint;
        v_bad_customer_totals bigint; v_bad_tag_counts bigint;
BEGIN
 SELECT COUNT(*) INTO v_customers FROM lab047_customers;
 SELECT COUNT(*),SUM(amount) INTO v_orders,v_total FROM lab047_orders;
 SELECT COUNT(*) INTO v_left FROM lab047_customers c
 LEFT JOIN lab047_orders o ON o.customer_id=c.customer_id;
 SELECT COUNT(*) INTO v_products FROM lab047_products;
 SELECT COUNT(*) INTO v_tags FROM lab047_tags;
 SELECT COUNT(*) INTO v_links FROM lab047_product_tags;
 SELECT COUNT(*) INTO v_dups FROM (
  SELECT product_id,tag_id FROM lab047_product_tags
  GROUP BY product_id,tag_id HAVING COUNT(*) > 1
 ) d;
 WITH totals AS (
  SELECT c.customer_id,COUNT(o.order_id) AS n,COALESCE(SUM(o.amount),0) AS amount
  FROM lab047_customers c LEFT JOIN lab047_orders o ON o.customer_id=c.customer_id
  GROUP BY c.customer_id
 )
 SELECT COUNT(*) INTO v_bad_customer_totals FROM totals
 WHERE (customer_id=1 AND (n,amount) IS DISTINCT FROM (2::bigint,50::numeric))
    OR (customer_id=2 AND (n,amount) IS DISTINCT FROM (1::bigint,15::numeric))
    OR (customer_id=3 AND (n,amount) IS DISTINCT FROM (0::bigint,0::numeric));
 SELECT COUNT(*) INTO v_bad_tag_counts FROM (
  SELECT tag_id,COUNT(*) AS n FROM lab047_product_tags GROUP BY tag_id
 ) x WHERE n <> 2;
 IF (v_customers,v_orders,v_left,v_total,v_products,v_tags,v_links,v_dups,v_bad_customer_totals,v_bad_tag_counts)
 IS DISTINCT FROM
 (3::bigint,3::bigint,4::bigint,65::numeric,3::bigint,2::bigint,4::bigint,0::bigint,0::bigint,0::bigint)
 THEN RAISE EXCEPTION 'Chapter 047 acceptance assertions failed'; END IF;
 RAISE NOTICE 'PASS: customers=3, orders=3, left_join_rows=4, order_total=65.00, products=3, tags=2, associations=4, duplicates=0';
END
$verify$;
ROLLBACK;
-- Expected: PASS notice and ROLLBACK; no persistent objects.
