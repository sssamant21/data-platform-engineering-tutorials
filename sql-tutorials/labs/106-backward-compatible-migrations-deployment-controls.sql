-- Chapter 106: synthetic migration readiness model; read-only, no DDL/DML.
-- Requires isolated PostgreSQL 18 database sql_tutorials. Expected values are static.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '15s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';

DO $guard$
BEGIN
 IF current_database() <> 'sql_tutorials' THEN
  RAISE EXCEPTION 'Disposable database sql_tutorials required; got %', current_database();
 END IF;
 IF current_setting('server_version_num')::integer / 10000 <> 18 THEN
  RAISE EXCEPTION 'PostgreSQL 18 required; got %', current_setting('server_version');
 END IF;
END
$guard$;

-- Synthetic transition snapshot: three copied values, two legacy-only rows.
WITH orders(order_id,old_name,new_name) AS (
 VALUES (101,'Ada'::text,'Ada'::text),
        (102,'Ben',NULL::text),
        (103,'Cleo','Cleo'),
        (104,'Dara',NULL::text),
        (105,'Eli','Eli')
)
SELECT order_id, COALESCE(new_name,old_name) AS compatible_display_name,
       (new_name IS NULL) AS requires_backfill
FROM orders ORDER BY order_id;

-- Readiness is a policy gate, not actual database permissions.
WITH orders(order_id,old_name,new_name) AS (
 VALUES (101,'Ada'::text,'Ada'::text),
        (102,'Ben',NULL::text),
        (103,'Cleo','Cleo'),
        (104,'Dara',NULL::text),
        (105,'Eli','Eli')
), flags AS (
 SELECT count(*)::bigint AS total,
        count(*) FILTER (WHERE new_name IS NOT NULL)::bigint AS copied,
        count(*) FILTER (WHERE new_name IS NULL)::bigint AS missing,
        count(*) FILTER (WHERE COALESCE(new_name,old_name) IS NOT NULL)::bigint AS compatible_visible,
        count(*) FILTER (WHERE new_name IS DISTINCT FROM old_name)::bigint AS divergent
 FROM orders
)
SELECT *, (missing = 0 AND divergent = 0 AND false) AS safe_to_contract
FROM flags;

DO $assert$
DECLARE missing_count integer; extra_count integer;
BEGIN
 WITH orders(order_id,old_name,new_name) AS (
  VALUES (101,'Ada'::text,'Ada'::text),
         (102,'Ben',NULL::text),
         (103,'Cleo','Cleo'),
         (104,'Dara',NULL::text),
         (105,'Eli','Eli')
 ), flags AS (
  SELECT count(*)::bigint AS total,
         count(*) FILTER (WHERE new_name IS NOT NULL)::bigint AS copied,
         count(*) FILTER (WHERE new_name IS NULL)::bigint AS missing,
         count(*) FILTER (WHERE COALESCE(new_name,old_name) IS NOT NULL)::bigint AS compatible_visible,
         count(*) FILTER (WHERE new_name IS DISTINCT FROM old_name)::bigint AS divergent
  FROM orders
 ), actual(metric,n) AS (
  SELECT 'total',total FROM flags
  UNION ALL SELECT 'copied',copied FROM flags
  UNION ALL SELECT 'missing',missing FROM flags
  UNION ALL SELECT 'compatible_visible',compatible_visible FROM flags
  UNION ALL SELECT 'divergent',divergent FROM flags
  UNION ALL SELECT 'contract_approved',0::bigint -- old readers and writers still present
 ), expected(metric,n) AS (
  VALUES ('total',5::bigint),('copied',3::bigint),('missing',2::bigint),
         ('compatible_visible',5::bigint),('divergent',2::bigint),
         ('contract_approved',0::bigint)
 ), missing_rows AS (SELECT * FROM expected EXCEPT ALL SELECT * FROM actual),
    extra_rows AS (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected)
 SELECT (SELECT count(*) FROM missing_rows),(SELECT count(*) FROM extra_rows)
 INTO missing_count,extra_count;
 IF missing_count <> 0 OR extra_count <> 0 THEN
  RAISE EXCEPTION '106 assertion mismatch: missing %, extra %',missing_count,extra_count;
 END IF;
 RAISE NOTICE '106 synthetic migration assertions passed: 5 total, 3 copied, 2 missing, 5 compatible, 2 divergent, contract blocked';
END
$assert$;
ROLLBACK;
