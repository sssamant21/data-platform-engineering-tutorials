-- Use an actual c014_single/blue/green login on c014_db.
-- Positive read plus explicit privilege-denial tests; no committed writes.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL statement_timeout='5s';
SET LOCAL lock_timeout='1s';
DO $guard$
BEGIN
  IF session_user NOT IN ('c014_single','c014_blue','c014_green')
     OR current_user <> session_user OR current_database() <> 'c014_db'
     OR pg_is_in_recovery() THEN
    RAISE EXCEPTION 'Use a real Chapter 014 service login on the lab primary';
  END IF;
  IF EXISTS (SELECT FROM pg_roles WHERE rolname=current_user
    AND (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls)) THEN
    RAISE EXCEPTION 'Unexpected powerful service-role attributes';
  END IF;
  IF NOT EXISTS (SELECT FROM c014_data.probe
                 WHERE id=1 AND payload='service-access-fixture') THEN
    RAISE EXCEPTION 'Expected service fixture missing';
  END IF;
END
$guard$;
SELECT session_user,current_user,current_database(),pg_backend_pid();
SELECT id,payload FROM c014_data.probe WHERE id=1;
DO $check$
BEGIN
  BEGIN
    INSERT INTO c014_data.probe VALUES (2,'forbidden-write');
  EXCEPTION WHEN insufficient_privilege THEN
    RAISE NOTICE 'PASS: service INSERT denied (42501)'; RETURN;
  END;
  RAISE EXCEPTION 'FAIL: service INSERT unexpectedly allowed';
END
$check$;
DO $check$
BEGIN
  BEGIN
    EXECUTE 'SET ROLE c014_owner';
  EXCEPTION WHEN insufficient_privilege THEN
    RAISE NOTICE 'PASS: owner assumption denied (42501)'; RETURN;
  END;
  RAISE EXCEPTION 'FAIL: owner assumption unexpectedly allowed';
END
$check$;
ROLLBACK;
