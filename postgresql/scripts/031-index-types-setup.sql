\set ON_ERROR_STOP on
BEGIN;
SET LOCAL statement_timeout='20s';
SET LOCAL lock_timeout='1s';
CREATE SCHEMA c031_indexes AUTHORIZATION lab_admin;
CREATE TABLE c031_indexes.events(
 id integer PRIMARY KEY,
 event_key integer NOT NULL,
 ordered_at timestamp NOT NULL,
 scattered_at timestamp NOT NULL,
 tags text[] NOT NULL,
 span int4range NOT NULL,
 location point NOT NULL,
 payload text NOT NULL
);
INSERT INTO c031_indexes.events
SELECT i,i%10000,
 timestamp '2026-01-01'+i*interval '1 second',
 timestamp '2026-01-01'+((i*7919)%50000)*interval '1 second',
 ARRAY['common',CASE WHEN i%1000=0 THEN 'rare' ELSE 'normal' END],
 int4range(i,i+10,'[)'),point(i%100,i/100),repeat(md5(i::text),4)
FROM generate_series(1,50000) AS s(i) ORDER BY i;
GRANT USAGE ON SCHEMA c031_indexes TO lab_app;
GRANT SELECT ON c031_indexes.events TO lab_app;
COMMIT;
ANALYZE c031_indexes.events;
