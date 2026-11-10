-- Chapter 058: ROLLUP, CUBE, GROUPING SETS. Synthetic, isolated PostgreSQL 18 ONLY.
-- Database-name and version checks do NOT prove isolation.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';
DO $guard$
BEGIN
 IF current_setting('server_version_num')::integer NOT BETWEEN 180000 AND 189999
 THEN RAISE EXCEPTION 'PostgreSQL 18.x required: %', current_setting('server_version'); END IF;
 IF current_database() <> 'sql_tutorials'
 THEN RAISE EXCEPTION 'Wrong database: %', current_database(); END IF;
END
$guard$;
SELECT current_database() AS database_name, inet_server_addr() AS server_ip,
       inet_server_port() AS server_port, version() AS server_version;
CREATE TEMP TABLE ch058_events (
 event_id integer PRIMARY KEY, region text, channel text NOT NULL,
 amount numeric(12,2) NOT NULL
) ON COMMIT DROP;
INSERT INTO ch058_events VALUES
 (1,'East','web',10.00),(2,'East','web',20.00),
 (3,'East','store',30.00),(4,'West','web',40.00),
 (5,'West','store',50.00),(6,NULL,'web',5.00);
SELECT COUNT(*) AS events, SUM(amount) AS source_total FROM ch058_events;
SELECT region, channel, GROUPING(region) AS gr, GROUPING(channel) AS gc,
       COUNT(*) AS events, SUM(amount) AS total
FROM ch058_events GROUP BY ROLLUP(region,channel)
ORDER BY gr,region NULLS LAST,gc,channel NULLS LAST;
SELECT region, channel, GROUPING(region) AS gr, GROUPING(channel) AS gc,
       COUNT(*) AS events, SUM(amount) AS total
FROM ch058_events GROUP BY CUBE(region,channel)
ORDER BY gr,region NULLS LAST,gc,channel NULLS LAST;
SELECT region, channel, GROUPING(region) AS gr, GROUPING(channel) AS gc,
       COUNT(*) AS events, SUM(amount) AS total
FROM ch058_events
GROUP BY GROUPING SETS ((region,channel),(region),())
ORDER BY gr,region NULLS LAST,gc,channel NULLS LAST;
DO $checks$
DECLARE source_count bigint; source_total numeric;
 roll_rows bigint; cube_rows bigint; sets_rows bigint; grand_rows bigint;
BEGIN
 SELECT COUNT(*),SUM(amount) INTO source_count,source_total FROM ch058_events;
 IF (source_count,source_total) IS DISTINCT FROM (6::bigint,155.00::numeric)
 THEN RAISE EXCEPTION 'Source mismatch'; END IF;
 SELECT COUNT(*) INTO roll_rows FROM
 (SELECT region,channel FROM ch058_events GROUP BY ROLLUP(region,channel)) x;
 SELECT COUNT(*) INTO cube_rows FROM
 (SELECT region,channel FROM ch058_events GROUP BY CUBE(region,channel)) x;
 SELECT COUNT(*) INTO sets_rows FROM
 (SELECT region,channel FROM ch058_events
  GROUP BY GROUPING SETS ((region,channel),(region),())) x;
 IF (roll_rows,cube_rows,sets_rows) IS DISTINCT FROM (9::bigint,11::bigint,9::bigint)
 THEN RAISE EXCEPTION 'Grouping row counts mismatch: %, %, %',roll_rows,cube_rows,sets_rows; END IF;
 IF EXISTS (
   WITH actual AS (
     SELECT region, GROUPING(region) AS gr, GROUPING(channel) AS gc,
            SUM(amount) AS total
     FROM ch058_events GROUP BY ROLLUP(region,channel)
   )
   SELECT 1 FROM actual WHERE gc=1 AND gr=0
   GROUP BY region,total
   HAVING NOT ((region='East' AND total=60.00) OR
               (region='West' AND total=90.00) OR
               (region IS NULL AND total=5.00))
 ) THEN RAISE EXCEPTION 'Unexpected region subtotal'; END IF;
 IF EXISTS (
   WITH actual AS (
    SELECT channel, GROUPING(region) AS gr, GROUPING(channel) AS gc,
           SUM(amount) AS total
    FROM ch058_events GROUP BY CUBE(region,channel)
   ), expected(channel,total) AS (
    VALUES ('web'::text,75.00::numeric),('store'::text,80.00::numeric)
   )
   (SELECT channel,total FROM actual WHERE gr=1 AND gc=0
    EXCEPT SELECT * FROM expected)
   UNION ALL
   (SELECT * FROM expected
    EXCEPT SELECT channel,total FROM actual WHERE gr=1 AND gc=0)
 ) THEN RAISE EXCEPTION 'Channel subtotal mismatch'; END IF;
 SELECT COUNT(*) INTO grand_rows FROM (
   SELECT GROUPING(region) AS gr,GROUPING(channel) AS gc,
          COUNT(*) AS events,SUM(amount) AS total
   FROM ch058_events GROUP BY ROLLUP(region,channel)
 ) x WHERE gr=1 AND gc=1 AND events=6 AND total=155.00;
 IF grand_rows<>1 THEN RAISE EXCEPTION 'Grand total mismatch'; END IF;
 IF (SELECT COUNT(*) FROM (
    SELECT region,channel,GROUPING(region) AS gr,GROUPING(channel) AS gc
    FROM ch058_events GROUP BY ROLLUP(region,channel)
 ) x WHERE region IS NULL AND gr=0 AND gc=1) <> 1
 THEN RAISE EXCEPTION 'Real NULL region subtotal missing'; END IF;
 RAISE NOTICE 'Chapter 058 static assertions passed in this execution';
END
$checks$;
ROLLBACK;
-- Runtime acceptance: retain actual psql stdout/stderr, exit code, server identity,
-- version and rollback verification. No execution is claimed by this source file.
