\set ON_ERROR_STOP on
SELECT current_database() AS recovered_database,pg_is_in_recovery() AS in_recovery;
SELECT count(*) AS total_rows,
 count(*) FILTER (WHERE status='valid') AS valid_rows,
 count(*) FILTER (WHERE status='corrupted') AS corrupt_rows,
 sum(amount) AS total_amount
FROM ch045.orders;
SELECT marker_name,recorded_at FROM ch045.recovery_markers ORDER BY marker_name;
SELECT CASE WHEN (SELECT count(*) FROM ch045.orders)=1000
 AND (SELECT count(*) FROM ch045.orders WHERE status='corrupted')=0
 AND EXISTS(SELECT 1 FROM ch045.recovery_markers WHERE marker_name='known-good')
 THEN 'PASS' ELSE 'FAIL' END AS recovery_acceptance;
