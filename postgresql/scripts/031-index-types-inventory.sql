\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout='3s';
SET LOCAL lock_timeout='500ms';
SELECT c.relname AS index_name,am.amname AS method,
 i.indisprimary,i.indisunique,i.indisvalid,i.indisready,
 pg_relation_size(c.oid) AS index_bytes,c.reloptions,
 (SELECT array_agg(op.opcname ORDER BY u.ord)
  FROM unnest(i.indclass::oid[]) WITH ORDINALITY AS u(opclass_oid,ord)
  JOIN pg_opclass op ON op.oid=u.opclass_oid) AS operator_classes
FROM pg_index i
JOIN pg_class c ON c.oid=i.indexrelid
JOIN pg_am am ON am.oid=c.relam
WHERE i.indrelid='c031_indexes.events'::regclass
ORDER BY c.relname;
SELECT attname,correlation FROM pg_stats
WHERE schemaname='c031_indexes' AND tablename='events'
AND attname IN ('ordered_at','scattered_at') ORDER BY attname;
SELECT pg_relation_size('c031_indexes.events'::regclass) AS heap_bytes,
 pg_indexes_size('c031_indexes.events'::regclass) AS all_index_bytes;
ROLLBACK;
