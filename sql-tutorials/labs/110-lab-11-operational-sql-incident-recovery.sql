-- Chapter 110: fictional incident/recovery decision exercise, not a real restore.
-- Run ONLY against isolated PostgreSQL 18 database sql_tutorials, with nonproduction credentials.
-- Expected: 4 observations, 3 slow, 2 blocked, 1 plan review;
--           1 accepted recovery, 2 blocked; 1 source-only and 1 target-only row.
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
   RAISE EXCEPTION 'PostgreSQL 18 required; got %', current_setting('server_version');
 END IF;
END
$guard$;

WITH observations(query_id, duration_ms, blocked, plan_concern) AS (
 VALUES ('q01',90,false,false), ('q02',820,true,false),
        ('q03',950,false,true), ('q04',710,true,true)
)
SELECT query_id, duration_ms,
 CASE WHEN blocked THEN 'BLOCKING'
      WHEN duration_ms >= 500 AND plan_concern THEN 'PLAN_REVIEW'
      ELSE 'NORMAL' END AS triage
FROM observations ORDER BY query_id;

WITH candidates(name, loss_min, rpo_min, restore_min, rto_min, checksum_ok, app_signoff, reconciled) AS (
 VALUES ('drill_a',3,5,18,30,true,true,true),
        ('drill_b',8,5,20,30,true,true,true),
        ('drill_c',2,5,24,30,true,false,true)
)
SELECT name,
 CASE WHEN loss_min <= rpo_min AND restore_min <= rto_min
        AND checksum_ok AND app_signoff AND reconciled
      THEN 'ACCEPT' ELSE 'BLOCK' END AS decision
FROM candidates ORDER BY name;

WITH source(order_id, amount) AS (
 VALUES (1,20.00::numeric(10,2)),(2,30.00::numeric(10,2)),(3,40.00::numeric(10,2))
), target(order_id, amount) AS (
 VALUES (1,20.00::numeric(10,2)),(2,30.00::numeric(10,2)),(4,40.00::numeric(10,2))
), diff AS (
 (SELECT * FROM source EXCEPT ALL SELECT * FROM target)
 UNION ALL
 (SELECT * FROM target EXCEPT ALL SELECT * FROM source)
)
SELECT (SELECT count(*) FROM source) AS source_rows,
       (SELECT sum(amount) FROM source) AS source_total,
       (SELECT count(*) FROM target) AS target_rows,
       (SELECT sum(amount) FROM target) AS target_total,
       (SELECT count(*) FROM diff) AS total_multiset_differences,
       CASE WHEN EXISTS (SELECT 1 FROM diff) THEN 'BLOCK' ELSE 'ACCEPT' END AS closure_decision;
-- Expected: 3 | 90.00 | 3 | 90.00 | 2 | BLOCK

DO $assert$
DECLARE v_samples integer; v_slow integer; v_blocked integer; v_plan integer;
        v_accept integer; v_reject integer; v_source_only integer; v_target_only integer;
        v_source_sum numeric; v_target_sum numeric; v_source_rows integer; v_target_rows integer;
BEGIN
 WITH observations(query_id, duration_ms, blocked, plan_concern) AS (
  VALUES ('q01',90,false,false), ('q02',820,true,false),
         ('q03',950,false,true), ('q04',710,true,true)
 )
 SELECT count(*), count(*) FILTER (WHERE duration_ms >= 500),
        count(*) FILTER (WHERE blocked),
        count(*) FILTER (WHERE NOT blocked AND duration_ms >= 500 AND plan_concern)
 INTO v_samples,v_slow,v_blocked,v_plan FROM observations;

 WITH candidates(name, loss_min, rpo_min, restore_min, rto_min, checksum_ok, app_signoff, reconciled) AS (
  VALUES ('drill_a',3,5,18,30,true,true,true),
         ('drill_b',8,5,20,30,true,true,true),
         ('drill_c',2,5,24,30,true,false,true)
 ), decisions AS (
  SELECT loss_min <= rpo_min AND restore_min <= rto_min
     AND checksum_ok AND app_signoff AND reconciled AS accepted
  FROM candidates
 )
 SELECT count(*) FILTER (WHERE accepted),count(*) FILTER (WHERE NOT accepted)
 INTO v_accept,v_reject FROM decisions;

 WITH source(order_id, amount) AS (
  VALUES (1,20.00::numeric(10,2)),(2,30.00::numeric(10,2)),(3,40.00::numeric(10,2))
 ), target(order_id, amount) AS (
  VALUES (1,20.00::numeric(10,2)),(2,30.00::numeric(10,2)),(4,40.00::numeric(10,2))
 ), source_only AS (SELECT * FROM source EXCEPT ALL SELECT * FROM target),
    target_only AS (SELECT * FROM target EXCEPT ALL SELECT * FROM source)
 SELECT (SELECT count(*) FROM source_only), (SELECT count(*) FROM target_only),
        (SELECT count(*) FROM source), (SELECT count(*) FROM target),
        (SELECT sum(amount) FROM source), (SELECT sum(amount) FROM target)
 INTO v_source_only,v_target_only,v_source_rows,v_target_rows,v_source_sum,v_target_sum;
 IF (v_samples,v_slow,v_blocked,v_plan,v_accept,v_reject,
     v_source_only,v_target_only,v_source_rows,v_target_rows,v_source_sum,v_target_sum)
    IS DISTINCT FROM (4,3,2,1,1,2,1,1,3,3,90.00::numeric,90.00::numeric) THEN
   RAISE EXCEPTION 'Chapter 110 assertions failed: samples %, slow %, blocked %, plan %, accepted %, rejected %, source_only %, target_only %',
     v_samples,v_slow,v_blocked,v_plan,v_accept,v_reject,v_source_only,v_target_only;
 END IF;
 RAISE NOTICE 'Chapter 110 synthetic assertions passed; no actual restore or incident validated';
END
$assert$;
ROLLBACK;
