-- Chapter 040: safe, auditable transaction capstone; PostgreSQL 18 ONLY.
-- WARNING: disposable sql_tutorials database ONLY. Verify endpoint/credentials separately.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/040-lab-04-safe-auditable-transaction.sql
-- Synthetic data. Temporary tables. Final ROLLBACK. Never use production.
BEGIN;
SET LOCAL statement_timeout = '15s';
SET LOCAL lock_timeout = '3s';
SET LOCAL idle_in_transaction_session_timeout = '30s';

DO $guard$
BEGIN
 IF current_database() <> 'sql_tutorials'
    OR current_setting('server_version_num')::integer NOT BETWEEN 180000 AND 189999
    OR pg_is_in_recovery() THEN
   RAISE EXCEPTION 'STOP: require disposable PostgreSQL 18 primary database sql_tutorials';
 END IF;
 RAISE NOTICE 'PASS target version/database guard (verify environment independently)';
END
$guard$;

CREATE TEMP TABLE lab040_orders (
 order_id integer PRIMARY KEY,
 amount numeric(12,2) NOT NULL CHECK (amount > 0),
 status text NOT NULL CHECK (status IN ('pending','paid'))
) ON COMMIT DROP;
CREATE TEMP TABLE lab040_payments (
 payment_id text PRIMARY KEY,
 order_id integer NOT NULL UNIQUE REFERENCES lab040_orders(order_id),
 amount numeric(12,2) NOT NULL CHECK (amount > 0)
) ON COMMIT DROP;
CREATE TEMP TABLE lab040_audit (
 event_id text PRIMARY KEY,
 order_id integer NOT NULL REFERENCES lab040_orders(order_id),
 old_status text NOT NULL,
 new_status text NOT NULL,
 CHECK (old_status <> new_status)
) ON COMMIT DROP;

INSERT INTO lab040_orders(order_id,amount,status)
VALUES (1001,40.00,'pending'),(1002,35.00,'pending'),(1003,25.00,'pending');

DO $initial$
BEGIN
 IF (SELECT count(*) FROM lab040_orders) <> 3
    OR (SELECT sum(amount) FROM lab040_orders) <> 100.00
    OR (SELECT count(*) FROM lab040_orders WHERE order_id=1001 AND status='pending' AND amount=40.00) <> 1 THEN
  RAISE EXCEPTION 'Initial/preview reconciliation failed';
 END IF;
 RAISE NOTICE 'PASS preview: 3 orders, 100.00 total, exactly one eligible order';
END
$initial$;

SELECT order_id,amount,status FROM lab040_orders
WHERE order_id=1001 AND status='pending';

SAVEPOINT before_bad_update;
UPDATE lab040_orders SET status='paid' WHERE order_id=1002 AND status='pending';
ROLLBACK TO SAVEPOINT before_bad_update;
RELEASE SAVEPOINT before_bad_update;

DO $savepoint$
BEGIN
 IF (SELECT status FROM lab040_orders WHERE order_id=1002) <> 'pending' THEN
  RAISE EXCEPTION 'Savepoint rollback failed';
 END IF;
 RAISE NOTICE 'PASS savepoint rollback: order 1002 remains pending';
END
$savepoint$;

DO $workflow$
DECLARE affected bigint;
BEGIN
 UPDATE lab040_orders SET status='paid'
 WHERE order_id=1001 AND status='pending' AND amount=40.00;
 GET DIAGNOSTICS affected = ROW_COUNT;
 IF affected <> 1 THEN
  RAISE EXCEPTION 'Expected exactly 1 updated order, got %',affected;
 END IF;
 INSERT INTO lab040_payments(payment_id,order_id,amount)
 VALUES ('payment-1001',1001,40.00);
 INSERT INTO lab040_audit(event_id,order_id,old_status,new_status)
 VALUES ('audit-1001',1001,'pending','paid');
 RAISE NOTICE 'PASS guarded update, payment and audit insertion';
END
$workflow$;

DO $verify$
BEGIN
 IF (SELECT count(*) FROM lab040_orders) <> 3
    OR (SELECT sum(amount) FROM lab040_orders) <> 100.00
    OR (SELECT count(*) FROM lab040_orders WHERE status='paid') <> 1
    OR (SELECT count(*) FROM lab040_orders WHERE status='pending') <> 2
    OR (SELECT count(*) FROM lab040_payments) <> 1
    OR (SELECT sum(amount) FROM lab040_payments) <> 40.00
    OR (SELECT count(*) FROM lab040_audit
        WHERE order_id=1001 AND old_status='pending' AND new_status='paid') <> 1
    OR (SELECT count(*) FROM lab040_payments p
        JOIN lab040_orders o USING (order_id)
        WHERE p.amount <> o.amount OR o.status <> 'paid') <> 0 THEN
  RAISE EXCEPTION 'Final reconciliation failed; transaction must not commit';
 END IF;
 RAISE NOTICE 'PASS final reconciliation: 3 orders, 1 paid, 2 pending, 1 payment, 1 audit, total 100.00';
END
$verify$;

SELECT order_id,amount,status FROM lab040_orders ORDER BY order_id;
SELECT payment_id,order_id,amount FROM lab040_payments ORDER BY payment_id;
SELECT event_id,order_id,old_status,new_status FROM lab040_audit ORDER BY event_id;
ROLLBACK;
-- Expected final psql status: ROLLBACK. No persistent objects or rows.
