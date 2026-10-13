\set ON_ERROR_STOP on
SELECT current_database() AS database_name,
 count(*) AS row_count,
 min(order_id) AS first_order,
 max(order_id) AS last_order,
 sum(amount) AS total_amount,
 md5(string_agg(order_id::text || ':' || amount::text, ',' ORDER BY order_id)) AS fixture_digest
FROM ch041_orders;
SELECT indexname,indexdef FROM pg_indexes
WHERE schemaname='public' AND tablename='ch041_orders'
ORDER BY indexname;
