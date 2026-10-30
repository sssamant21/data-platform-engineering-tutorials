\set ON_ERROR_STOP on
-- Deliberate data corruption simulation. NEVER run on production/shared data.
-- Must explicitly match the disposable PostgreSQL 18 cluster before UPDATE.
\if :{?expected_db}
\else
  \echo 'REFUSED: expected_db required'
  \quit 3
\endif
\if :{?expected_system_id}
\else
  \echo 'REFUSED: expected_system_id required'
  \quit 3
\endif
\if :{?expected_source_data_directory}
\else
  \echo 'REFUSED: independently verified expected_source_data_directory required'
  \quit 3
\endif
\if :{?expected_operator}
\else
  \echo 'REFUSED: expected_operator required'
  \quit 3
\endif
\if :{?confirm_incident}
\else
  \echo 'REFUSED: chapter-specific incident token required'
  \quit 3
\endif
SELECT CASE WHEN current_database() = :'expected_db'
  AND current_setting('server_version_num')::integer BETWEEN 180000 AND 189999
  AND NOT pg_is_in_recovery()
  AND current_user = :'expected_operator'
  AND current_setting('data_directory') = :'expected_source_data_directory'
  AND EXISTS (SELECT 1 FROM pg_control_system() c
              WHERE c.system_identifier::text = :'expected_system_id')
  AND :'confirm_incident' = '045-INCIDENT'
  AND to_regclass('ch045.orders') IS NOT NULL
  THEN 'true' ELSE 'false' END AS incident_permitted
\gset
\if :incident_permitted
  \echo 'Verified disposable cluster and incident approval token'
\else
  \echo 'REFUSED: cluster, database, fixture or incident token mismatch'
  \quit 3
\endif
UPDATE ch045.orders SET status='corrupted',updated_at=clock_timestamp()
WHERE order_id BETWEEN 1 AND 100;
SELECT count(*) AS simulated_corrupt_rows FROM ch045.orders WHERE status='corrupted';
SELECT pg_current_wal_lsn() AS observed_lsn,clock_timestamp() AS observed_at;
