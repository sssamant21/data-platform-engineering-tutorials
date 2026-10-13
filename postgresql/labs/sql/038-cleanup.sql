\set ON_ERROR_STOP on
SELECT current_database();
DROP SCHEMA ch038 CASCADE;
SELECT count(*) FROM pg_namespace WHERE nspname='ch038';
