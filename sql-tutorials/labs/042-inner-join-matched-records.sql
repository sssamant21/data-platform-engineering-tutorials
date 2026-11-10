-- Chapter 042 — INNER JOIN: matched records
-- PostgreSQL 18; synthetic data only; isolated disposable database sql_tutorials.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/042-inner-join-matched-records.sql
-- Never run against production or with production credentials.
BEGIN;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
DO $guard$
BEGIN
  IF current_setting('server_version_num')::int < 180000
     OR current_database() <> 'sql_tutorials'
     OR pg_is_in_recovery() THEN
    RAISE EXCEPTION 'Requires isolated writable sql_tutorials on PostgreSQL 18+';
  END IF;
END
$guard$;

CREATE TEMP TABLE lab042_customers (
  customer_id integer PRIMARY KEY,
  customer_name text NOT NULL
) ON COMMIT DROP;
-- Staging intentionally has no FK: one synthetic unmatched key is the exercise.
CREATE TEMP TABLE lab042_staging_orders (
  order_id integer PRIMARY KEY,
  customer_id integer NOT NULL,
  amount numeric(10,2) NOT NULL CHECK (amount >= 0)
) ON COMMIT DROP;
INSERT INTO lab042_customers VALUES (1,'Ada'),(2,'Ben'),(3,'Cy');
INSERT INTO lab042_staging_orders VALUES
 (101,1,20.00),(102,1,30.00),(103,2,15.00),(104,99,9.00);

-- Matched records: expected 101/Ada, 102/Ada, 103/Ben.
SELECT o.order_id, c.customer_name, o.amount
FROM lab042_staging_orders AS o
INNER JOIN lab042_customers AS c ON c.customer_id = o.customer_id
ORDER BY o.order_id;

-- Business filter: expected 102/Ada.
SELECT o.order_id, c.customer_name
FROM lab042_staging_orders AS o
INNER JOIN lab042_customers AS c ON c.customer_id = o.customer_id
WHERE o.amount >= 25.00
ORDER BY o.order_id;

-- Anti-join audit: expected 104 / 99 / 9.00.
SELECT o.order_id, o.customer_id, o.amount
FROM lab042_staging_orders AS o
WHERE NOT EXISTS (
  SELECT 1 FROM lab042_customers AS c
  WHERE c.customer_id = o.customer_id
)
ORDER BY o.order_id;

-- Reconciliation: source 4 / 74.00; matched 3 / 65.00; unmatched 1 / 9.00.
SELECT 'source' AS segment, COUNT(*) AS rows, SUM(amount) AS amount
FROM lab042_staging_orders
UNION ALL
SELECT 'matched', COUNT(*), SUM(o.amount)
FROM lab042_staging_orders AS o
JOIN lab042_customers AS c ON c.customer_id = o.customer_id
UNION ALL
SELECT 'unmatched', COUNT(*), SUM(o.amount)
FROM lab042_staging_orders AS o
WHERE NOT EXISTS (SELECT 1 FROM lab042_customers AS c WHERE c.customer_id=o.customer_id);

DO $verify$
DECLARE
  src_n bigint; matched_n bigint; missing_n bigint;
  src_amt numeric; matched_amt numeric; missing_amt numeric;
  distinct_customers bigint; filtered_n bigint;
BEGIN
  SELECT COUNT(*),SUM(amount) INTO src_n,src_amt FROM lab042_staging_orders;
  SELECT COUNT(*),SUM(o.amount),COUNT(DISTINCT o.customer_id)
    INTO matched_n,matched_amt,distinct_customers
    FROM lab042_staging_orders o
    JOIN lab042_customers c ON c.customer_id=o.customer_id;
  SELECT COUNT(*),SUM(o.amount) INTO missing_n,missing_amt
    FROM lab042_staging_orders o
    WHERE NOT EXISTS (SELECT 1 FROM lab042_customers c WHERE c.customer_id=o.customer_id);
  SELECT COUNT(*) INTO filtered_n
    FROM lab042_staging_orders o
    JOIN lab042_customers c ON c.customer_id=o.customer_id
    WHERE o.amount >= 25.00;
  IF (src_n,matched_n,missing_n,src_amt,matched_amt,missing_amt,distinct_customers,filtered_n)
     IS DISTINCT FROM (4::bigint,3::bigint,1::bigint,74.00::numeric,65.00::numeric,9.00::numeric,2::bigint,1::bigint)
  THEN RAISE EXCEPTION 'Chapter 042 reconciliation failed'; END IF;
  IF src_n <> matched_n + missing_n OR src_amt <> matched_amt + missing_amt
  THEN RAISE EXCEPTION 'Chapter 042 conservation check failed'; END IF;
  RAISE NOTICE 'PASS: source 4/74.00; matched 3/65.00; unmatched 1/9.00; matched customers 2; filtered 1';
END
$verify$;
ROLLBACK;
-- Expected final command tag: ROLLBACK. No persistent objects.
