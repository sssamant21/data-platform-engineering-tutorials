-- Chapter 059: pivoting/unpivoting. Synthetic disposable PostgreSQL 18 ONLY.
-- The database-name/version guard does NOT establish actual isolation.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';
DO $guard$
BEGIN
 IF current_setting('server_version_num')::integer NOT BETWEEN 180000 AND 189999
 THEN RAISE EXCEPTION 'PostgreSQL 18.x required'; END IF;
 IF current_database() <> 'sql_tutorials'
 THEN RAISE EXCEPTION 'Wrong database: %',current_database(); END IF;
END
$guard$;
SELECT current_database() AS database_name, inet_server_addr() AS server_ip,
       inet_server_port() AS server_port, version() AS server_version;
CREATE TEMP TABLE ch059_events (
 event_id integer PRIMARY KEY,
 region text NOT NULL,
 channel text NOT NULL,
 amount numeric(12,2) NOT NULL
) ON COMMIT DROP;
INSERT INTO ch059_events VALUES
 (1,'East','web',10.00),(2,'East','web',20.00),
 (3,'East','store',30.00),(4,'West','web',40.00),
 (5,'West','store',50.00),(6,'West','store',5.00),
 (7,'North','web',15.00),(8,'North','store',10.00);
SELECT COUNT(*) AS source_events, SUM(amount) AS source_total FROM ch059_events;
SELECT region,
 SUM(CASE WHEN channel='web' THEN amount ELSE 0 END) AS web_amount,
 SUM(CASE WHEN channel='store' THEN amount ELSE 0 END) AS store_amount,
 SUM(amount) AS region_total
FROM ch059_events GROUP BY region ORDER BY region;
SELECT region,
 COALESCE(SUM(amount) FILTER (WHERE channel='web'),0) AS web_amount,
 COALESCE(SUM(amount) FILTER (WHERE channel='store'),0) AS store_amount
FROM ch059_events GROUP BY region ORDER BY region;
WITH wide AS (
 SELECT region,
  SUM(CASE WHEN channel='web' THEN amount ELSE 0 END) AS web_amount,
  SUM(CASE WHEN channel='store' THEN amount ELSE 0 END) AS store_amount
 FROM ch059_events GROUP BY region
)
SELECT region,'web' AS channel,web_amount AS amount FROM wide
UNION ALL
SELECT region,'store' AS channel,store_amount AS amount FROM wide
ORDER BY region,channel;
DO $checks$
DECLARE n bigint; total numeric; pivot_rows bigint; pivot_total numeric;
 unpivot_rows bigint; unpivot_total numeric;
BEGIN
 SELECT COUNT(*),SUM(amount) INTO n,total FROM ch059_events;
 IF (n,total) IS DISTINCT FROM (8::bigint,180.00::numeric)
 THEN RAISE EXCEPTION 'Source mismatch'; END IF;
 IF EXISTS (SELECT 1 FROM ch059_events WHERE channel NOT IN ('web','store'))
 THEN RAISE EXCEPTION 'Unexpected channel: update reviewed pivot allowlist'; END IF;
 WITH wide AS (
  SELECT region,
   SUM(CASE WHEN channel='web' THEN amount ELSE 0 END) AS web_amount,
   SUM(CASE WHEN channel='store' THEN amount ELSE 0 END) AS store_amount,
   SUM(amount) AS region_total
  FROM ch059_events GROUP BY region
 )
 SELECT COUNT(*),SUM(web_amount+store_amount)
 INTO pivot_rows,pivot_total FROM wide;
 IF (pivot_rows,pivot_total) IS DISTINCT FROM (3::bigint,180.00::numeric)
 THEN RAISE EXCEPTION 'Pivot grain or total mismatch'; END IF;
 IF EXISTS (
  WITH actual AS (
   SELECT region,
    SUM(CASE WHEN channel='web' THEN amount ELSE 0 END) AS web_amount,
    SUM(CASE WHEN channel='store' THEN amount ELSE 0 END) AS store_amount
   FROM ch059_events GROUP BY region
  ), expected(region,web_amount,store_amount) AS (
   VALUES ('East'::text,30.00::numeric,30.00::numeric),
          ('North'::text,15.00::numeric,10.00::numeric),
          ('West'::text,40.00::numeric,55.00::numeric)
  )
  SELECT 1 FROM (
   (SELECT * FROM actual EXCEPT SELECT * FROM expected)
   UNION ALL
   (SELECT * FROM expected EXCEPT SELECT * FROM actual)
  ) differences
 ) THEN RAISE EXCEPTION 'Pivot region amounts mismatch'; END IF;
 WITH wide AS (
  SELECT region,
   SUM(CASE WHEN channel='web' THEN amount ELSE 0 END) AS web_amount,
   SUM(CASE WHEN channel='store' THEN amount ELSE 0 END) AS store_amount
  FROM ch059_events GROUP BY region
 ), long_form AS (
  SELECT region,'web' AS channel,web_amount AS amount FROM wide
  UNION ALL
  SELECT region,'store' AS channel,store_amount AS amount FROM wide
 )
 SELECT COUNT(*),SUM(amount) INTO unpivot_rows,unpivot_total FROM long_form;
 IF (unpivot_rows,unpivot_total) IS DISTINCT FROM (6::bigint,180.00::numeric)
 THEN RAISE EXCEPTION 'Unpivot row count or total mismatch'; END IF;
 RAISE NOTICE 'Chapter 059 assertions passed in this execution';
END
$checks$;
ROLLBACK;
-- For runtime certification retain psql stdout/stderr, exit code, version,
-- endpoint identity and evidence of rollback. Source alone is NOT execution.
