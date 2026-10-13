\set ON_ERROR_STOP on
\echo 'Disposable lab only: ch040 schema cleanup'
DROP SCHEMA ch040 CASCADE;
SELECT count(*) AS remaining FROM pg_namespace WHERE nspname='ch040';
