-- Chapter 089: read-only simulation of trigger change events and bound-value filtering.
-- Run only against isolated PostgreSQL 18 database sql_tutorials:
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/089-triggers-dynamic-sql-parameterization.sql
-- No DDL, trigger creation, persistent writes or production data.
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '20s';
SELECT current_database() AS database_name,
       current_setting('server_version') AS server_version,
       1 / CASE WHEN current_database() = 'sql_tutorials'
                 AND current_setting('server_version_num')::integer BETWEEN 180000 AND 189999
                THEN 1 ELSE 0 END AS environment_guard;
-- A trigger-like transition set; NULL-safe comparison catches order 105.
WITH changes(order_id, old_status, new_status) AS (
 VALUES (101,'pending'::text,'paid'::text),
        (102,'pending','pending'),
        (103,'paid','refunded'),
        (104,'pending','cancelled'),
        (105,NULL::text,'pending')
)
SELECT order_id, old_status, new_status
FROM changes WHERE old_status IS DISTINCT FROM new_status
ORDER BY order_id;
-- Parameter-like CTE keeps data values separate from SQL structure.
-- In application code use actual driver-bound parameters, not interpolation.
WITH changes(order_id, old_status, new_status) AS (
 VALUES (101,'pending'::text,'paid'::text),
        (102,'pending','pending'),
        (103,'paid','refunded'),
        (104,'pending','cancelled'),
        (105,NULL::text,'pending')
), supplied_parameter(status_filter) AS (VALUES ('paid'::text))
SELECT c.order_id
FROM changes AS c CROSS JOIN supplied_parameter AS p
WHERE c.old_status IS DISTINCT FROM c.new_status
  AND c.new_status = p.status_filter
ORDER BY c.order_id;
-- Fail-closed exact multiset assertions and source reconciliation.
WITH changes(order_id, old_status, new_status) AS (
 VALUES (101,'pending'::text,'paid'::text),
        (102,'pending','pending'),
        (103,'paid','refunded'),
        (104,'pending','cancelled'),
        (105,NULL::text,'pending')
), actual AS (
 SELECT order_id, old_status, new_status
 FROM changes WHERE old_status IS DISTINCT FROM new_status
), expected(order_id, old_status, new_status) AS (
 VALUES (101,'pending'::text,'paid'::text),
        (103,'paid','refunded'),
        (104,'pending','cancelled'),
        (105,NULL::text,'pending')
), delta AS (
 (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected)
 UNION ALL
 (SELECT * FROM expected EXCEPT ALL SELECT * FROM actual)
), supplied_parameter(status_filter) AS (VALUES ('paid'::text)),
filtered AS (
 SELECT a.order_id FROM actual AS a CROSS JOIN supplied_parameter AS p
 WHERE a.new_status = p.status_filter
), filtered_expected(order_id) AS (VALUES (101)),
filtered_delta AS (
 (SELECT * FROM filtered EXCEPT ALL SELECT * FROM filtered_expected)
 UNION ALL
 (SELECT * FROM filtered_expected EXCEPT ALL SELECT * FROM filtered)
), checks AS (
 SELECT (SELECT count(*)=5 FROM changes) AS five_source_rows,
        (SELECT count(*)=4 FROM actual) AS four_changed_rows,
        (SELECT count(*)=0 FROM delta) AS exact_change_rows,
        (SELECT count(*)=1 FROM filtered) AS one_paid_transition,
        (SELECT count(*)=0 FROM filtered_delta) AS exact_filtered_rows,
        (SELECT count(*)=1 FROM actual WHERE old_status IS NULL AND new_status='pending') AS null_transition_preserved,
        (SELECT count(*)=1 FROM changes WHERE old_status IS NOT DISTINCT FROM new_status) AS one_unchanged_row
)
SELECT *, 1 / CASE WHEN five_source_rows AND four_changed_rows
                     AND exact_change_rows AND one_paid_transition
                     AND exact_filtered_rows AND null_transition_preserved
                     AND one_unchanged_row THEN 1 ELSE 0 END AS fail_closed_acceptance
FROM checks;
ROLLBACK;
