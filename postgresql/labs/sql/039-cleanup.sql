\set ON_ERROR_STOP on
\echo 'Disposable lab only: removing ch039 schema'
DROP SCHEMA ch039 CASCADE;
SELECT count(*) AS remaining FROM pg_namespace WHERE nspname='ch039';
