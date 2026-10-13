\set ON_ERROR_STOP on
DO $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname='ch048') THEN
  RAISE EXCEPTION 'Expected lab schema not found; cleanup refused';
 END IF;
END $$;
DROP SCHEMA ch048 CASCADE;
