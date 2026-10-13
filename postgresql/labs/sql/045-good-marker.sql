\set ON_ERROR_STOP on
INSERT INTO ch045.recovery_markers(marker_name) VALUES ('known-good');
SELECT marker_name,recorded_at FROM ch045.recovery_markers;
SELECT pg_current_wal_lsn() AS observed_lsn,clock_timestamp() AS observed_at;
