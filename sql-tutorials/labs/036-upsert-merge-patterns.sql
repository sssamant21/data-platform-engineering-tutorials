-- Chapter 036: UPSERT and MERGE patterns across SQL dialects
-- ONLY run on independently verified disposable PostgreSQL 18 sql_tutorials instance.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/036-upsert-merge-patterns.sql
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL lock_timeout = '2s';
SET LOCAL statement_timeout = '30s';
SET LOCAL idle_in_transaction_session_timeout = '60s';

DO $guard$
BEGIN
 IF current_setting('server_version_num')::integer NOT BETWEEN 180000 AND 189999
    OR current_database() <> 'sql_tutorials'
    OR pg_is_in_recovery()
 THEN RAISE EXCEPTION 'Wrong PostgreSQL version, database or standby: abort'; END IF;
END $guard$;

CREATE TEMP TABLE inventory (
 sku TEXT PRIMARY KEY,
 quantity INTEGER NOT NULL CHECK (quantity >= 0),
 source_version INTEGER NOT NULL CHECK (source_version > 0)
) ON COMMIT DROP;
INSERT INTO inventory(sku,quantity,source_version) VALUES
 ('SKU-A',10,1),('SKU-B',5,2);

-- ON CONFLICT requires a suitable unique arbiter (here PRIMARY KEY).
-- Update only for strictly newer source versions. This is state replacement,
-- NOT an increment; retries of the same batch are idempotent.
CREATE TEMP TABLE upsert_audit(sku TEXT PRIMARY KEY) ON COMMIT DROP;
WITH changed AS (
 INSERT INTO inventory(sku,quantity,source_version) VALUES
  ('SKU-A',12,2),('SKU-B',99,1),('SKU-C',7,1)
 ON CONFLICT (sku) DO UPDATE
 SET quantity=EXCLUDED.quantity, source_version=EXCLUDED.source_version
 WHERE EXCLUDED.source_version > inventory.source_version
 RETURNING sku
)
INSERT INTO upsert_audit(sku) SELECT sku FROM changed;

DO $upsert_check$
BEGIN
 IF (SELECT array_agg(sku ORDER BY sku) FROM upsert_audit)
      IS DISTINCT FROM ARRAY['SKU-A','SKU-C']::TEXT[]
 OR (SELECT count(*) FROM inventory) <> 3
 OR (SELECT quantity FROM inventory WHERE sku='SKU-B') <> 5
 THEN RAISE EXCEPTION 'UPSERT reconciliation failed'; END IF;
END $upsert_check$;

-- PostgreSQL 18 MERGE: matched newer rows updated, unmatched rows inserted.
-- One source row per target key: duplicates may cause cardinality errors.
-- The source is synthetic VALUES, with unique SKU values.
MERGE INTO inventory AS target
USING (VALUES ('SKU-B',8,3),('SKU-D',4,1),('SKU-A',999,1))
      AS incoming(sku,quantity,source_version)
ON target.sku = incoming.sku
WHEN MATCHED AND incoming.source_version > target.source_version THEN
 UPDATE SET quantity=incoming.quantity, source_version=incoming.source_version
WHEN NOT MATCHED THEN
 INSERT (sku,quantity,source_version)
 VALUES (incoming.sku,incoming.quantity,incoming.source_version);

DO $merge_check$
BEGIN
 IF (SELECT array_agg(sku || ':' || quantity::TEXT || ':' || source_version::TEXT ORDER BY sku)
     FROM inventory)
 IS DISTINCT FROM ARRAY['SKU-A:12:2','SKU-B:8:3','SKU-C:7:1','SKU-D:4:1']::TEXT[]
 OR (SELECT sum(quantity) FROM inventory) <> 31
 THEN RAISE EXCEPTION 'MERGE reconciliation failed'; END IF;
END $merge_check$;

-- Replay identical MERGE batch: no state change (idempotency demonstration).
MERGE INTO inventory AS target
USING (VALUES ('SKU-B',8,3),('SKU-D',4,1),('SKU-A',999,1))
      AS incoming(sku,quantity,source_version)
ON target.sku = incoming.sku
WHEN MATCHED AND incoming.source_version > target.source_version THEN
 UPDATE SET quantity=incoming.quantity, source_version=incoming.source_version
WHEN NOT MATCHED THEN
 INSERT (sku,quantity,source_version)
 VALUES (incoming.sku,incoming.quantity,incoming.source_version);

DO $replay_check$
BEGIN
 IF (SELECT sum(quantity) FROM inventory) <> 31
 OR (SELECT count(*) FROM inventory) <> 4
 THEN RAISE EXCEPTION 'Idempotency replay failed'; END IF;
END $replay_check$;

SELECT sku,quantity,source_version FROM inventory ORDER BY sku;
SELECT 'PASS' AS lab_acceptance, 4 AS final_skus, 31 AS final_quantity,
       2 AS first_upsert_changed_keys;
ROLLBACK;
