-- Connect as the actual c011_runtime login to c011_db.
-- Positive writes are rolled back. Sequences may advance even on rollback.
-- Negative tests accept only SQLSTATE 42501, not an arbitrary error.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL statement_timeout='5s';
SET LOCAL lock_timeout='1s';
DO $guard$
BEGIN
  IF session_user <> 'c011_runtime' OR current_user <> 'c011_runtime'
     OR current_database() <> 'c011_db' OR pg_is_in_recovery() THEN
    RAISE EXCEPTION 'Use the real runtime login on the lab primary';
  END IF;
  IF EXISTS (SELECT FROM pg_roles WHERE rolname=current_user
             AND (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls)) THEN
    RAISE EXCEPTION 'Runtime role has unexpected powerful attributes';
  END IF;
END
$guard$;

SELECT session_user,current_user;
SELECT id,payload FROM c011_data.jobs ORDER BY id;
INSERT INTO c011_data.jobs(payload) VALUES ('runtime-rolled-back') RETURNING id,payload;
UPDATE c011_data.jobs SET payload='updated-rolled-back'
WHERE payload='runtime-rolled-back' RETURNING id,payload;

DO $check$
BEGIN
  BEGIN
    EXECUTE 'DELETE FROM c011_data.jobs WHERE false';
  EXCEPTION WHEN insufficient_privilege THEN
    RAISE NOTICE 'PASS: DELETE denied (42501)'; RETURN;
  END;
  RAISE EXCEPTION 'FAIL: DELETE unexpectedly allowed';
END
$check$;
DO $check$
BEGIN
  BEGIN
    EXECUTE 'TRUNCATE c011_data.jobs';
  EXCEPTION WHEN insufficient_privilege THEN
    RAISE NOTICE 'PASS: TRUNCATE denied (42501)'; RETURN;
  END;
  RAISE EXCEPTION 'FAIL: TRUNCATE unexpectedly allowed';
END
$check$;
DO $check$
BEGIN
  BEGIN
    EXECUTE 'CREATE TABLE c011_data.runtime_forbidden(id integer)';
  EXCEPTION WHEN insufficient_privilege THEN
    RAISE NOTICE 'PASS: schema CREATE denied (42501)'; RETURN;
  END;
  RAISE EXCEPTION 'FAIL: schema CREATE unexpectedly allowed';
END
$check$;
DO $check$
BEGIN
  BEGIN
    EXECUTE 'ALTER TABLE c011_data.jobs ADD COLUMN runtime_forbidden integer';
  EXCEPTION WHEN insufficient_privilege THEN
    RAISE NOTICE 'PASS: owner DDL denied (42501)'; RETURN;
  END;
  RAISE EXCEPTION 'FAIL: owner DDL unexpectedly allowed';
END
$check$;
DO $check$
BEGIN
  BEGIN
    EXECUTE 'SET ROLE c011_owner';
  EXCEPTION WHEN insufficient_privilege THEN
    RAISE NOTICE 'PASS: owner assumption denied (42501)'; RETURN;
  END;
  RAISE EXCEPTION 'FAIL: owner assumption unexpectedly allowed';
END
$check$;
DO $check$
BEGIN
  BEGIN
    EXECUTE 'SET ROLE c011_writer';
  EXCEPTION WHEN insufficient_privilege THEN
    RAISE NOTICE 'PASS: writer SET ROLE denied (42501)'; RETURN;
  END;
  RAISE EXCEPTION 'FAIL: writer SET ROLE unexpectedly allowed';
END
$check$;
DO $check$
BEGIN
  BEGIN
    EXECUTE 'GRANT c011_writer TO c011_deploy';
  EXCEPTION WHEN insufficient_privilege THEN
    RAISE NOTICE 'PASS: membership delegation denied (42501)'; RETURN;
  END;
  RAISE EXCEPTION 'FAIL: membership delegation unexpectedly allowed';
END
$check$;
ROLLBACK;
