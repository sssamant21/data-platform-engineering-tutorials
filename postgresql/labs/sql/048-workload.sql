\set ON_ERROR_STOP on
CREATE SCHEMA IF NOT EXISTS ch048;
CREATE TABLE IF NOT EXISTS ch048.events(id integer PRIMARY KEY,payload text NOT NULL);
INSERT INTO ch048.events(id,payload)
SELECT g,repeat(md5(g::text),8) FROM generate_series(1,5000) g
ON CONFLICT(id) DO UPDATE SET payload=excluded.payload;
SELECT count(*) AS fixture_rows FROM ch048.events;
SELECT pg_current_wal_lsn() AS observed_primary_lsn;
