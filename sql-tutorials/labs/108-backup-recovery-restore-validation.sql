-- Chapter 108: synthetic backup/recovery acceptance model, NOT a real restore.
-- Run only on isolated PostgreSQL 18 database sql_tutorials with nonproduction credentials.
-- Expected: drill_a ACCEPT; drill_b and drill_c BLOCK. No persistent changes.
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';

DO $guard$
BEGIN
  IF current_database() <> 'sql_tutorials' THEN
    RAISE EXCEPTION 'Expected isolated database sql_tutorials; got %', current_database();
  END IF;
  IF current_setting('server_version_num')::integer < 180000
     OR current_setting('server_version_num')::integer >= 190000 THEN
    RAISE EXCEPTION 'PostgreSQL 18 required; got %', current_setting('server_version');
  END IF;
END
$guard$;

-- Fictional measurements and evidence flags, never production metadata.
WITH drills(drill_id, loss_minutes, recovery_minutes, rpo_limit, rto_limit,
            backup_verified, wal_continuous, data_reconciled, app_signed_off) AS (
  VALUES
    ('drill_a', 5, 35, 10, 45, true, true, true, true),
    ('drill_b',15, 30, 10, 45, true, true, true, true),
    ('drill_c', 2, 20, 10, 45, true, true, true, false)
)
SELECT drill_id, loss_minutes, recovery_minutes,
       CASE WHEN loss_minutes <= rpo_limit AND recovery_minutes <= rto_limit
                 AND backup_verified AND wal_continuous AND data_reconciled AND app_signed_off
            THEN 'ACCEPT' ELSE 'BLOCK' END AS decision
FROM drills ORDER BY drill_id;
-- Expected:
-- drill_a | 5  | 35 | ACCEPT
-- drill_b | 15 | 30 | BLOCK
-- drill_c | 2  | 20 | BLOCK

DO $assert$
DECLARE
  mismatches integer;
BEGIN
  WITH drills(drill_id, loss_minutes, recovery_minutes, rpo_limit, rto_limit,
              backup_verified, wal_continuous, data_reconciled, app_signed_off) AS (
    VALUES
      ('drill_a', 5, 35, 10, 45, true, true, true, true),
      ('drill_b',15, 30, 10, 45, true, true, true, true),
      ('drill_c', 2, 20, 10, 45, true, true, true, false)
  ),
  actual AS (
    SELECT drill_id,
      CASE WHEN loss_minutes <= rpo_limit AND recovery_minutes <= rto_limit
                AND backup_verified AND wal_continuous AND data_reconciled AND app_signed_off
           THEN 'ACCEPT' ELSE 'BLOCK' END AS decision
    FROM drills
  ),
  expected(drill_id, decision) AS (
    VALUES ('drill_a','ACCEPT'), ('drill_b','BLOCK'), ('drill_c','BLOCK')
  ),
  diff AS (
    (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected)
    UNION ALL
    (SELECT * FROM expected EXCEPT ALL SELECT * FROM actual)
  )
  SELECT COUNT(*) INTO mismatches FROM diff;
  IF mismatches <> 0 THEN
    RAISE EXCEPTION 'Recovery decision model mismatch count: %', mismatches;
  END IF;
  RAISE NOTICE 'Chapter 108 synthetic acceptance assertions passed; NOT a restore test';
END
$assert$;

ROLLBACK;
