-- Chapter 109: synthetic slow-query triage model; NOT production telemetry.
-- PostgreSQL 18, isolated database sql_tutorials, nonproduction credentials only.
-- Expected: six samples; three >=500ms; two BLOCKING; one PLAN_REVIEW.
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';

DO $guard$
BEGIN
  IF current_database() <> 'sql_tutorials' THEN
    RAISE EXCEPTION 'Expected isolated database sql_tutorials, got %', current_database();
  END IF;
  IF current_setting('server_version_num')::integer NOT BETWEEN 180000 AND 189999 THEN
    RAISE EXCEPTION 'PostgreSQL 18 required, got %', current_setting('server_version');
  END IF;
END
$guard$;

WITH samples(query_id, duration_ms, blocked, index_hypothesis) AS (
 VALUES ('q01',120,false,false), ('q02',780,true,false),
        ('q03',910,false,true), ('q04',80,false,false),
        ('q05',650,true,false), ('q06',240,false,false)
), classified AS (
 SELECT query_id, duration_ms,
        CASE WHEN blocked THEN 'BLOCKING'
             WHEN duration_ms >= 500 AND index_hypothesis THEN 'PLAN_REVIEW'
             ELSE 'NORMAL' END AS triage
 FROM samples
)
SELECT query_id, duration_ms, triage FROM classified ORDER BY query_id;

WITH samples(query_id, duration_ms, blocked, index_hypothesis) AS (
 VALUES ('q01',120,false,false), ('q02',780,true,false),
        ('q03',910,false,true), ('q04',80,false,false),
        ('q05',650,true,false), ('q06',240,false,false)
)
SELECT count(*) AS sample_count,
       count(*) FILTER (WHERE duration_ms >= 500) AS slow_count,
       count(*) FILTER (WHERE blocked) AS blocking_count,
       count(*) FILTER (WHERE duration_ms >= 500 AND index_hypothesis AND NOT blocked) AS plan_review_count
FROM samples;
-- Expected: 6 | 3 | 2 | 1

DO $assert$
DECLARE mismatch_count integer;
DECLARE observed_count integer;
DECLARE slow_count integer;
DECLARE blocked_count integer;
DECLARE plan_count integer;
BEGIN
  WITH samples(query_id, duration_ms, blocked, index_hypothesis) AS (
    VALUES ('q01',120,false,false), ('q02',780,true,false),
           ('q03',910,false,true), ('q04',80,false,false),
           ('q05',650,true,false), ('q06',240,false,false)
  ), actual AS (
    SELECT query_id, CASE WHEN blocked THEN 'BLOCKING'
      WHEN duration_ms >= 500 AND index_hypothesis THEN 'PLAN_REVIEW'
      ELSE 'NORMAL' END AS triage FROM samples
  ), expected(query_id,triage) AS (
    VALUES ('q01','NORMAL'),('q02','BLOCKING'),('q03','PLAN_REVIEW'),
           ('q04','NORMAL'),('q05','BLOCKING'),('q06','NORMAL')
  ), difference AS (
    (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected)
    UNION ALL
    (SELECT * FROM expected EXCEPT ALL SELECT * FROM actual)
  )
  SELECT count(*) INTO mismatch_count FROM difference;

  WITH samples(query_id, duration_ms, blocked, index_hypothesis) AS (
    VALUES ('q01',120,false,false), ('q02',780,true,false),
           ('q03',910,false,true), ('q04',80,false,false),
           ('q05',650,true,false), ('q06',240,false,false)
  )
  SELECT count(*), count(*) FILTER (WHERE duration_ms >= 500),
         count(*) FILTER (WHERE blocked),
         count(*) FILTER (WHERE duration_ms >= 500 AND index_hypothesis AND NOT blocked)
    INTO observed_count, slow_count, blocked_count, plan_count FROM samples;
  IF mismatch_count <> 0 OR observed_count <> 6 OR slow_count <> 3
     OR blocked_count <> 2 OR plan_count <> 1 THEN
    RAISE EXCEPTION 'Chapter 109 assertions failed: diff %, rows %, slow %, blocked %, plan %',
      mismatch_count, observed_count, slow_count, blocked_count, plan_count;
  END IF;
  RAISE NOTICE 'Chapter 109 synthetic assertions passed; no actual incident or benchmark validated';
END
$assert$;
ROLLBACK;
