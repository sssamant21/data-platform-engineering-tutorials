-- Reset only owned disposable fixtures, between completed lab phases.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL statement_timeout='5s';
SET LOCAL lock_timeout='1s';
DO $guard$
BEGIN
 IF current_user <> 'lab_admin' OR current_database() <> 'ops_lab' OR pg_is_in_recovery() THEN
   RAISE EXCEPTION 'Wrong reset connection';
 END IF;
 IF EXISTS (SELECT FROM pg_stat_activity
   WHERE datname=current_database() AND application_name IN ('chapter017-A','chapter017-B')
   AND (xact_start IS NOT NULL OR state IN ('idle in transaction','idle in transaction (aborted)'))) THEN
   RAISE EXCEPTION 'Finish or roll back actor transactions before reset';
 END IF;
 IF (SELECT count(*) FROM c017_iso.counter) <> 1
    OR NOT EXISTS (SELECT FROM c017_iso.counter WHERE id=1)
    OR (SELECT count(*) FROM c017_iso.roster) <> 2
    OR (SELECT count(*) FROM c017_iso.roster WHERE id IN (1,2)) <> 2 THEN
   RAISE EXCEPTION 'Unexpected fixture contents; inspect before resetting';
 END IF;
END
$guard$;
UPDATE c017_iso.counter SET units=100 WHERE id=1;
UPDATE c017_iso.roster SET on_call=true WHERE id IN (1,2);
COMMIT;
