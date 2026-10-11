-- Between completed lab phases only; never resets arbitrary production data.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL statement_timeout='5s';
SET LOCAL lock_timeout='1s';
DO $guard$
BEGIN
 IF current_user <> 'lab_admin' OR current_database() <> 'ops_lab'
    OR pg_is_in_recovery() THEN
   RAISE EXCEPTION 'Wrong reset connection';
 END IF;
 IF EXISTS (SELECT FROM pg_stat_activity
   WHERE datname=current_database()
    AND application_name IN ('chapter018-A','chapter018-B','chapter018-C')
    AND (xact_start IS NOT NULL OR state IN ('idle in transaction','idle in transaction (aborted)'))) THEN
   RAISE EXCEPTION 'Finish/roll back all actor transactions before reset';
 END IF;
 IF (SELECT count(*) FROM c018_locks.probe)<>2
    OR (SELECT count(*) FROM c018_locks.probe WHERE id IN (1,2))<>2 THEN
   RAISE EXCEPTION 'Unexpected fixture contents; inspect before reset';
 END IF;
END
$guard$;
UPDATE c018_locks.probe SET quantity=CASE id WHEN 1 THEN 100 ELSE 200 END WHERE id IN (1,2);
COMMIT;
