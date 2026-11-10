-- Chapter 051: COUNT, SUM, AVG, MIN, MAX
-- Synthetic, disposable PostgreSQL 18 lab. Run with psql -X -v ON_ERROR_STOP=1.
-- Verify isolated endpoint and nonproduction credentials BEFORE running.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';

DO $guard$
BEGIN
  IF current_setting('server_version_num')::integer < 180000
     OR current_setting('server_version_num')::integer >= 190000 THEN
    RAISE EXCEPTION 'Requires PostgreSQL 18.x; found %', current_setting('server_version');
  END IF;
  IF current_database() <> 'sql_tutorials' THEN
    RAISE EXCEPTION 'Refusing unexpected database: %', current_database();
  END IF;
END
$guard$;

CREATE TEMP TABLE ch051_payments (
  payment_id integer PRIMARY KEY,
  order_id integer NOT NULL,
  amount numeric(12,2)
) ON COMMIT DROP;

INSERT INTO ch051_payments(payment_id,order_id,amount) VALUES
 (1,101,10.00),
 (2,101,30.00),
 (3,102,20.00),
 (4,103,NULL),
 (5,104,40.00);

-- Expected one row: 5, 4, 4, 100.00, 25.00, 10.00, 40.00.
SELECT COUNT(*) AS event_count,
       COUNT(amount) AS known_amount_count,
       COUNT(DISTINCT order_id) AS distinct_orders,
       SUM(amount) AS total_amount,
       AVG(amount) AS mean_known_amount,
       MIN(amount) AS minimum_amount,
       MAX(amount) AS maximum_amount
FROM ch051_payments;

-- Expected one row: 5, 4, 1, 20.00.
SELECT COUNT(*) AS events,
       COUNT(amount) AS known_amounts,
       COUNT(*) - COUNT(amount) AS missing_amounts,
       AVG(COALESCE(amount, 0)) AS zero_filled_average
FROM ch051_payments;

-- Expected one row: 0, NULL, NULL, 0.
SELECT COUNT(*) AS empty_count,
       SUM(amount) AS empty_sum,
       AVG(amount) AS empty_avg,
       COALESCE(SUM(amount), 0) AS displayed_zero
FROM ch051_payments
WHERE order_id = -999;

DO $checks$
DECLARE
  r record;
  empty_r record;
BEGIN
  SELECT COUNT(*) AS n,
         COUNT(amount) AS known,
         COUNT(DISTINCT order_id) AS distinct_orders,
         COUNT(*) - COUNT(amount) AS missing,
         SUM(amount) AS total,
         AVG(amount) AS mean_amount,
         MIN(amount) AS smallest,
         MAX(amount) AS largest,
         AVG(COALESCE(amount,0)) AS mean_zero
    INTO r FROM ch051_payments;

  IF r.n <> 5 OR r.known <> 4 OR r.distinct_orders <> 4
     OR r.missing <> 1 OR r.total <> 100.00 OR r.mean_amount <> 25.00
     OR r.smallest <> 10.00 OR r.largest <> 40.00 OR r.mean_zero <> 20.00 THEN
    RAISE EXCEPTION 'Chapter 051 aggregate acceptance failed: %', row_to_json(r);
  END IF;

  SELECT COUNT(*) AS n, SUM(amount) AS total, AVG(amount) AS mean_amount
    INTO empty_r FROM ch051_payments WHERE order_id = -999;

  IF empty_r.n <> 0 OR empty_r.total IS NOT NULL OR empty_r.mean_amount IS NOT NULL THEN
    RAISE EXCEPTION 'Chapter 051 empty-input acceptance failed';
  END IF;

  RAISE NOTICE 'Chapter 051 assertions passed (expected only until independently executed)';
END
$checks$;

ROLLBACK;
-- Expected psql exit code 0 and final ROLLBACK after successful isolated execution.
