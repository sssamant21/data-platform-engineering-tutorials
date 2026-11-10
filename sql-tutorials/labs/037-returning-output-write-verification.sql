-- Chapter 037: PostgreSQL 18 only; synthetic data, isolated sql_tutorials database.
-- Verify the endpoint and role independently BEFORE execution.
-- Run: psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/037-returning-output-write-verification.sql
BEGIN;
SET LOCAL statement_timeout = '15s';
SET LOCAL lock_timeout = '3s';
SET LOCAL idle_in_transaction_session_timeout = '30s';

DO $guard$
BEGIN
  IF current_database() <> 'sql_tutorials'
     OR current_setting('server_version_num')::integer < 180000
     OR current_setting('server_version_num')::integer >= 190000
     OR pg_is_in_recovery() THEN
    RAISE EXCEPTION 'Unsafe lab target: require isolated sql_tutorials on PostgreSQL 18 primary';
  END IF;
END
$guard$;

CREATE TEMP TABLE payments (
  payment_id integer PRIMARY KEY,
  amount numeric(10,2) NOT NULL CHECK (amount >= 0),
  status text NOT NULL CHECK (status IN ('pending','reviewed','settled'))
) ON COMMIT DROP;

INSERT INTO payments(payment_id,amount,status)
VALUES (101,12.50,'pending'),(102,18.00,'pending'),(103,9.25,'settled');

-- Preview candidate set before any update.
SELECT payment_id, amount, status FROM payments
WHERE payment_id=101 AND status='pending' ORDER BY payment_id;

-- Capture actual changed rows; exact-cardinality assertion is fail-closed.
DO $verify_update$
DECLARE affected integer; got_id integer; got_status text; got_amount numeric;
BEGIN
  WITH changed AS (
    UPDATE payments SET status='reviewed'
    WHERE payment_id=101 AND status='pending'
    RETURNING payment_id, amount, status
  )
  SELECT count(*)::integer, min(payment_id), min(status), min(amount)
  INTO affected, got_id, got_status, got_amount FROM changed;
  IF affected <> 1 OR got_id <> 101 OR got_status <> 'reviewed' OR got_amount <> 12.50 THEN
    RAISE EXCEPTION 'UPDATE verification failed: rows=%', affected;
  END IF;
  RAISE NOTICE 'PASS UPDATE returned 1 row: 101 reviewed 12.50';
END
$verify_update$;

DO $verify_insert$
DECLARE affected integer; got_id integer; got_amount numeric;
BEGIN
  WITH changed AS (
    INSERT INTO payments(payment_id,amount,status)
    VALUES (104,20.00,'pending')
    RETURNING payment_id,amount
  )
  SELECT count(*)::integer, min(payment_id), min(amount)
  INTO affected, got_id, got_amount FROM changed;
  IF affected <> 1 OR got_id <> 104 OR got_amount <> 20.00 THEN
    RAISE EXCEPTION 'INSERT verification failed';
  END IF;
  RAISE NOTICE 'PASS INSERT returned 1 row: 104 20.00';
END
$verify_insert$;

DO $verify_delete$
DECLARE affected integer; got_id integer; got_amount numeric;
BEGIN
  WITH changed AS (
    DELETE FROM payments WHERE payment_id=102 AND status='pending'
    RETURNING payment_id,amount
  )
  SELECT count(*)::integer, min(payment_id), min(amount)
  INTO affected, got_id, got_amount FROM changed;
  IF affected <> 1 OR got_id <> 102 OR got_amount <> 18.00 THEN
    RAISE EXCEPTION 'DELETE verification failed';
  END IF;
  RAISE NOTICE 'PASS DELETE returned 1 row: 102 18.00';
END
$verify_delete$;

DO $final$
DECLARE n integer; total numeric; reviewed integer;
BEGIN
  SELECT count(*)::integer, coalesce(sum(amount),0),
         count(*) FILTER (WHERE status='reviewed')
  INTO n,total,reviewed FROM payments;
  IF n <> 3 OR total <> 41.75 OR reviewed <> 1 THEN
    RAISE EXCEPTION 'Final reconciliation failed: rows %, amount %, reviewed %', n,total,reviewed;
  END IF;
  RAISE NOTICE 'PASS final: 3 rows, amount 41.75, reviewed 1';
END
$final$;
SELECT payment_id,amount,status FROM payments ORDER BY payment_id;
ROLLBACK;
