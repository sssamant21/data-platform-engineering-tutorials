-- Chapter 038 — PostgreSQL 18 isolated rollback-only transaction lab
-- IMPORTANT: independently verify endpoint, host, role, and disposable environment.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/038-begin-commit-rollback-savepoint.sql
BEGIN;
SET LOCAL statement_timeout = '15s';
SET LOCAL lock_timeout = '3s';
SET LOCAL idle_in_transaction_session_timeout = '30s';

DO $guard$
BEGIN
 IF current_database() <> 'sql_tutorials'
    OR current_setting('server_version_num')::integer NOT BETWEEN 180000 AND 189999
    OR pg_is_in_recovery() THEN
  RAISE EXCEPTION 'Unsafe target: require isolated PostgreSQL 18 primary sql_tutorials';
 END IF;
END
$guard$;

CREATE TEMP TABLE budgets (
 bucket_id integer PRIMARY KEY,
 balance numeric(12,2) NOT NULL CHECK (balance >= 0)
) ON COMMIT DROP;
INSERT INTO budgets(bucket_id,balance) VALUES (1,100.00),(2,50.00);

DO $check_initial$
BEGIN
 IF (SELECT count(*) FROM budgets) <> 2
    OR (SELECT balance FROM budgets WHERE bucket_id=1) <> 100.00
    OR (SELECT balance FROM budgets WHERE bucket_id=2) <> 50.00 THEN
  RAISE EXCEPTION 'Initial state mismatch';
 END IF;
 RAISE NOTICE 'PASS initial: 2 rows, 100.00 and 50.00';
END
$check_initial$;

-- Both updates are in one outer transaction; assert exact affected rows.
DO $transfer$
DECLARE n integer;
BEGIN
 UPDATE budgets SET balance=balance-20.00 WHERE bucket_id=1 AND balance>=20.00;
 GET DIAGNOSTICS n = ROW_COUNT;
 IF n <> 1 THEN RAISE EXCEPTION 'Debit affected % rows', n; END IF;
 UPDATE budgets SET balance=balance+20.00 WHERE bucket_id=2;
 GET DIAGNOSTICS n = ROW_COUNT;
 IF n <> 1 THEN RAISE EXCEPTION 'Credit affected % rows', n; END IF;
 IF (SELECT balance FROM budgets WHERE bucket_id=1) <> 80.00
    OR (SELECT balance FROM budgets WHERE bucket_id=2) <> 70.00
    OR (SELECT sum(balance) FROM budgets) <> 150.00 THEN
  RAISE EXCEPTION 'Transfer invariant failed';
 END IF;
 RAISE NOTICE 'PASS transfer: 80.00 and 70.00, sum 150.00';
END
$transfer$;

SAVEPOINT optional_transfer;
UPDATE budgets SET balance=balance-5.00 WHERE bucket_id=1;
UPDATE budgets SET balance=balance+5.00 WHERE bucket_id=2;
DO $check_optional$
BEGIN
 IF (SELECT balance FROM budgets WHERE bucket_id=1) <> 75.00
    OR (SELECT balance FROM budgets WHERE bucket_id=2) <> 75.00 THEN
  RAISE EXCEPTION 'Optional transfer mismatch';
 END IF;
 RAISE NOTICE 'PASS optional: 75.00 and 75.00';
END
$check_optional$;

ROLLBACK TO SAVEPOINT optional_transfer;
DO $check_undo$
BEGIN
 IF (SELECT balance FROM budgets WHERE bucket_id=1) <> 80.00
    OR (SELECT balance FROM budgets WHERE bucket_id=2) <> 70.00 THEN
  RAISE EXCEPTION 'Savepoint rollback failed';
 END IF;
 RAISE NOTICE 'PASS savepoint rollback: 80.00 and 70.00';
END
$check_undo$;
RELEASE SAVEPOINT optional_transfer;

DO $final$
BEGIN
 IF (SELECT count(*) FROM budgets) <> 2
    OR (SELECT sum(balance) FROM budgets) <> 150.00 THEN
  RAISE EXCEPTION 'Final reconciliation failed';
 END IF;
 RAISE NOTICE 'PASS final: 2 rows, sum 150.00';
END
$final$;
SELECT bucket_id,balance FROM budgets ORDER BY bucket_id;
ROLLBACK;
