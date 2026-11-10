-- Chapter 039: read-only PostgreSQL 18 isolation lab.
-- Verify independently that host, port, role, and database are disposable.
-- Run with: psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/039-isolation-levels-transaction-anomalies.sql
-- This single-session lab does NOT demonstrate concurrent anomalies.
BEGIN ISOLATION LEVEL READ COMMITTED READ ONLY;
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
 IF current_setting('transaction_isolation') <> 'read committed'
    OR current_setting('transaction_read_only') <> 'on' THEN
  RAISE EXCEPTION 'Read committed read-only transaction expected';
 END IF;
 RAISE NOTICE 'PASS read committed';
END
$guard$;

WITH inventory(sku, quantity) AS (
 VALUES ('SKU-A', 10), ('SKU-B', 5)
)
SELECT sku, quantity, CASE WHEN sku='SKU-A' AND quantity>=2
 THEN quantity-2 ELSE quantity END AS hypothetical_after_reservation
FROM inventory ORDER BY sku;

DO $synthetic$
DECLARE total_qty integer; remaining integer;
BEGIN
 WITH inventory(sku, quantity) AS (VALUES ('SKU-A',10),('SKU-B',5))
 SELECT sum(quantity), max(quantity) FILTER (WHERE sku='SKU-A') - 2
 INTO total_qty, remaining FROM inventory;
 IF total_qty <> 15 OR remaining <> 8 THEN
  RAISE EXCEPTION 'Synthetic inventory mismatch';
 END IF;
 RAISE NOTICE 'PASS synthetic inventory: total 15, SKU-A after hypothetical reservation 8';
END
$synthetic$;
ROLLBACK;

BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
DO $rr$
BEGIN
 IF current_setting('transaction_isolation') <> 'repeatable read'
    OR current_setting('transaction_read_only') <> 'on' THEN
  RAISE EXCEPTION 'Repeatable read configuration mismatch';
 END IF;
 RAISE NOTICE 'PASS repeatable read';
END
$rr$;
ROLLBACK;

BEGIN ISOLATION LEVEL SERIALIZABLE READ ONLY;
DO $serial$
BEGIN
 IF current_setting('transaction_isolation') <> 'serializable'
    OR current_setting('transaction_read_only') <> 'on' THEN
  RAISE EXCEPTION 'Serializable configuration mismatch';
 END IF;
 RAISE NOTICE 'PASS serializable';
END
$serial$;
ROLLBACK;
