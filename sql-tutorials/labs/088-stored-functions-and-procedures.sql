-- Chapter 088: stored-function concepts using read-only synthetic SQL.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/088-stored-functions-and-procedures.sql
-- No routine creation, persistent writes, or privileges modified.
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '20s';
SELECT current_database() AS database_name,
       current_setting('server_version') AS server_version,
       1 / CASE WHEN current_database() = 'sql_tutorials'
                 AND current_setting('server_version_num')::integer BETWEEN 180000 AND 189999
                THEN 1 ELSE 0 END AS environment_guard;
-- Inspect one built-in function without invoking user-created routines.
SELECT p.proname, p.prokind, p.provolatile
FROM pg_catalog.pg_proc AS p
JOIN pg_catalog.pg_namespace AS n ON n.oid = p.pronamespace
WHERE n.nspname = 'pg_catalog' AND p.oid = 'pg_catalog.abs(numeric)'::pg_catalog.regprocedure;
-- Expected: abs | f | i (function, immutable).
WITH invoices(invoice_id, subtotal, fee_rate) AS (
 VALUES (1,100.00::numeric,0.05::numeric),
        (2,40.00::numeric,0.10::numeric),
        (3,20.00::numeric,0.00::numeric)
), calculated AS (
 SELECT invoice_id, subtotal, round(subtotal * fee_rate,2) AS fee,
        subtotal + round(subtotal * fee_rate,2) AS total
 FROM invoices
)
SELECT * FROM calculated ORDER BY invoice_id;
-- Fail-closed exact rows and aggregate reconciliation.
WITH invoices(invoice_id, subtotal, fee_rate) AS (
 VALUES (1,100.00::numeric,0.05::numeric),
        (2,40.00::numeric,0.10::numeric),
        (3,20.00::numeric,0.00::numeric)
), actual AS (
 SELECT invoice_id, subtotal, round(subtotal * fee_rate,2) AS fee,
        subtotal + round(subtotal * fee_rate,2) AS total
 FROM invoices
), expected(invoice_id,subtotal,fee,total) AS (
 VALUES (1,100.00::numeric,5.00::numeric,105.00::numeric),
        (2,40.00::numeric,4.00::numeric,44.00::numeric),
        (3,20.00::numeric,0.00::numeric,20.00::numeric)
), delta AS (
 (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected)
 UNION ALL
 (SELECT * FROM expected EXCEPT ALL SELECT * FROM actual)
), checks AS (
 SELECT (SELECT count(*)=0 FROM delta) AS exact_rows,
        (SELECT count(*)=3 FROM invoices) AS three_invoices,
        (SELECT sum(fee)=9.00::numeric FROM actual) AS fees_nine,
        (SELECT sum(total)=169.00::numeric FROM actual) AS total_169,
        (SELECT count(*)=1 FROM pg_catalog.pg_proc AS p
          JOIN pg_catalog.pg_namespace AS n ON n.oid=p.pronamespace
          WHERE n.nspname='pg_catalog'
            AND p.oid='pg_catalog.abs(numeric)'::pg_catalog.regprocedure
            AND p.prokind='f' AND p.provolatile='i') AS built_in_metadata
)
SELECT *, 1 / CASE WHEN exact_rows AND three_invoices AND fees_nine
                        AND total_169 AND built_in_metadata THEN 1 ELSE 0 END
          AS fail_closed_acceptance
FROM checks;
ROLLBACK;
