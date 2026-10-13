\set ON_ERROR_STOP on
DO $$
DECLARE
 row_count integer;
 amount_total numeric(12,2);
 pk_count integer;
BEGIN
 IF current_database() <> 'ch062_restored' THEN
  RAISE EXCEPTION 'Refusing verification outside ch062_restored';
 END IF;
 SELECT count(*),sum(amount) INTO row_count,amount_total FROM ch062.orders;
 IF row_count <> 3 OR amount_total <> 61.50 THEN
  RAISE EXCEPTION 'Unexpected restored data: rows %, total %',row_count,amount_total;
 END IF;
 SELECT count(*) INTO pk_count FROM pg_constraint
 WHERE conrelid='ch062.orders'::regclass AND contype='p';
 IF pk_count <> 1 THEN
  RAISE EXCEPTION 'Primary key missing after restore';
 END IF;
 RAISE NOTICE 'PASS: rows, totals and primary key verified';
END $$;
SELECT pg_get_serial_sequence('ch062.orders','order_id') AS identity_sequence;
SELECT order_id,order_ref,amount FROM ch062.orders ORDER BY order_id;
