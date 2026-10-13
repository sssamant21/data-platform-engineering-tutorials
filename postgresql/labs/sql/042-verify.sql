\set ON_ERROR_STOP on
SELECT current_database() AS database_name,
 count(*) AS row_count,
 min(order_id) AS min_id,
 max(order_id) AS max_id,
 sum(amount) AS total_amount,
 md5(string_agg(order_id::text || ':' || amount::text || ':' || status, ',' ORDER BY order_id)) AS data_digest
FROM ch042_orders;
SELECT indexname,indexdef FROM pg_indexes
WHERE schemaname='public' AND tablename='ch042_orders'
ORDER BY indexname;
SELECT pg_get_serial_sequence('public.ch042_orders','order_id') AS sequence_name;
