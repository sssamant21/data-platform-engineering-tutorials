\set ON_ERROR_STOP on
UPDATE ch045.orders SET status='corrupted',updated_at=clock_timestamp()
WHERE order_id BETWEEN 1 AND 100;
SELECT count(*) AS simulated_corrupt_rows FROM ch045.orders WHERE status='corrupted';
SELECT pg_current_wal_lsn() AS observed_lsn,clock_timestamp() AS observed_at;
