\set ON_ERROR_STOP on
CREATE SCHEMA IF NOT EXISTS ch047;
CREATE TABLE IF NOT EXISTS ch047.wal_fixture (
 id integer PRIMARY KEY,
 payload text NOT NULL
);
INSERT INTO ch047.wal_fixture(id,payload)
SELECT g,repeat(md5(g::text),8) FROM generate_series(1,2000) g
ON CONFLICT(id) DO UPDATE SET payload=excluded.payload;
SELECT count(*) AS fixture_rows FROM ch047.wal_fixture;
SELECT pg_current_wal_lsn() AS observed_lsn;
