\set ON_ERROR_STOP on
CREATE SCHEMA IF NOT EXISTS ch044;
CREATE TABLE IF NOT EXISTS ch044.recovery_markers (
 marker_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 marker_name text NOT NULL UNIQUE,
 inserted_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
INSERT INTO ch044.recovery_markers(marker_name)
VALUES ('before-pitr-drill') ON CONFLICT(marker_name) DO NOTHING;
SELECT marker_id,marker_name,inserted_at FROM ch044.recovery_markers ORDER BY marker_id;
SELECT pg_current_wal_lsn() AS observed_lsn,clock_timestamp() AS observed_at;
