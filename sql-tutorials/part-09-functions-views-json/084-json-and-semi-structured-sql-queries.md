# 084 — JSON and Semi-Structured SQL Queries

**Part 09 — SQL Objects, Functions & Semi-Structured Data | 60 minutes | PostgreSQL 18**

[Master TOC](../MASTER-TOC.md) · [Tutorial index](../README.md) · [SQL lab](../labs/084-json-semi-structured-queries.sql) · [Previous: 083](083-numeric-expressions-and-precision-considerations.md) · [Next: 085](../MASTER-TOC.md#part-09--sql-objects-functions--semi-structured-data)

## 1. Outcomes and schedule (0–5 minutes)

After this chapter, you can explain when to store JSON rather than relational columns, extract scalar fields, distinguish absent keys from JSON null and SQL NULL, expand arrays safely, validate JSON types before casting, and reconcile event counts. Prerequisites: [009 — Data types](../part-01-fundamentals/009-data-types-null-and-explicit-type-conversion.md), [041 — Join fundamentals](../part-05-joins/041-join-fundamentals-and-relationship-cardinality.md), and an **isolated** PostgreSQL 18 database named `sql_tutorials`.

| Time | Work |
|---|---|
| 0–5 | Objectives, isolation and safety |
| 5–15 | JSON model, portability, NULL semantics |
| 15–30 | Worked extraction and array examples |
| 30–50 | Read-only synthetic lab and exercises |
| 50–55 | Troubleshooting and operational controls |
| 55–60 | Review and answers |

## 2. Concepts and syntax (5–15 minutes)

JSON represents objects, arrays, strings, numbers, booleans and JSON null. It is useful for ingestion envelopes, vendor payloads, optional attributes and changing event schemas. Keep stable identifiers, join keys, required constraints and frequently filtered attributes in typed relational columns when practical. Do not assume a JSON document is a validated business schema.

**PostgreSQL-specific:** `json` preserves the input representation; `jsonb` stores a decomposed representation suitable for operators and indexing, without preserving object-key order, duplicate object keys or insignificant whitespace. PostgreSQL operators `->` (JSON value), `->>` (text), `#>` (JSON path array), `#>>` (text), `?` (top-level key existence) and `@>` (containment) are **not portable SQL**. `jsonb_array_elements` is PostgreSQL-specific. SQL/JSON facilities such as `JSON_VALUE`, `JSON_QUERY` and `JSON_TABLE` exist across multiple engines, but supported syntax, paths, error handling and versions differ: test each target dialect.

**Three different missing states:** a missing object key can produce SQL NULL on extraction; an explicit JSON `null` is a JSON value; a SQL NULL column is not a JSON document. `payload->>'priority'` produces SQL NULL for both missing and JSON null. Use `payload ? 'priority'` and `jsonb_typeof(payload->'priority')` to distinguish them. `jsonb_typeof('null'::jsonb)` returns text `null`, whereas `jsonb_typeof(NULL::jsonb)` returns SQL NULL.

## 3. Worked examples (15–30 minutes)

The following are **PostgreSQL 18** examples with invented ingestion events; no tables are needed.

### A. Extract typed values and check key presence

```sql
WITH events(event_id, payload) AS (
  VALUES (1, '{"source":"api","status":200,"priority":null}'::jsonb),
         (2, '{"source":"file","status":503}'::jsonb)
)
SELECT event_id,
       payload->>'source' AS source_name,
       (payload->>'status')::integer AS status_code,
       payload ? 'priority' AS has_priority_key,
       jsonb_typeof(payload->'priority') AS priority_json_type
FROM events ORDER BY event_id;
```

Expected:

| event_id | source_name | status_code | has_priority_key | priority_json_type |
|---:|---|---:|---|---|
| 1 | api | 200 | true | null (text value) |
| 2 | file | 503 | false | SQL NULL |

**Safety:** casting arbitrary source text to `integer` can fail. In production ingestion, validate the JSON type and numeric range before casting, quarantine malformed records, and retain the raw payload for audit.

### B. Safely expand an array

```sql
WITH events(event_id, payload) AS (
  VALUES (1, '{"tags":["etl","urgent"]}'::jsonb),
         (2, '{"tags":[]}'::jsonb),
         (3, '{}'::jsonb)
)
SELECT e.event_id, tag.value AS tag
FROM events AS e
CROSS JOIN LATERAL jsonb_array_elements_text(
  CASE WHEN jsonb_typeof(e.payload->'tags') = 'array'
       THEN e.payload->'tags' ELSE '[]'::jsonb END
) AS tag(value)
ORDER BY e.event_id, tag.value;
```

Expected: two rows, `(1,etl)` and `(1,urgent)`. **Important:** a cross join removes parent events whose arrays are empty. For parent preservation, use `LEFT JOIN LATERAL ... ON TRUE` and distinguish the NULL tag rows. Never compare expanded row counts directly with event counts without accounting for fan-out.

### C. Containment and structured predicates

```sql
SELECT '{"source":"api","status":200}'::jsonb
       @> '{"source":"api"}'::jsonb AS contains_source;
```

Expected: `true`. JSON containment is not the same as substring search; it is structural. For production workloads, benchmark with realistic selectivity before adding a JSONB GIN index; indexing adds storage and write cost.

## 4. Hands-on lab (30–50 minutes)

Only use a disposable PostgreSQL 18 database **named `sql_tutorials`**, with a non-production login. The canonical [SQL lab](../labs/084-json-semi-structured-queries.sql) is a read-only transaction using synthetic inline `VALUES`, local timeouts, a database/version guard, expected-result assertions and `ROLLBACK`.

From the repository root:

```bash
psql -X -d sql_tutorials -c "SELECT current_database(), current_setting('server_version');"
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/084-json-semi-structured-queries.sql
```

The dataset has four events: two API events, one FILE event and one API event with an empty tags array; one API event has an explicit JSON null priority, one FILE event lacks the priority key, and one event has a SQL NULL payload. The lab validates extracted sources, key presence, safe tag expansion and reconciled counts. Expected: **4 events, 3 non-NULL JSON payloads, 2 tag rows, 1 explicit JSON null priority, 1 absent priority key among non-NULL payloads, 1 SQL NULL payload**. The canonical script compares actual and expected rows in both directions with `EXCEPT ALL` and fails closed on differences.

Exercises, using your own scratch `WITH` query (do not change the canonical file):

1. Change `CROSS JOIN LATERAL` to `LEFT JOIN LATERAL ... ON TRUE`; explain why the output now includes rows for empty/missing arrays.
2. Count the events with a present `priority` key separately from events with a non-null textual priority. Explain the difference.
3. Add a synthetic record with `"tags":"etl"` (a string). Verify that the guarded array expansion produces no tag rows instead of an exception.
4. Propose a relational `events(event_id, source, received_at, payload)` schema; identify which fields should be typed and constrained.

**Acceptance evidence to retain during future runtime QA:** PostgreSQL version, isolated database identity, exact command, stdout/stderr, exit status, and comparison outputs. This chapter and lab are authored; **no PostgreSQL 18 execution is claimed here**.

## 5. Troubleshooting, safety and portability (50–55 minutes)

- **Operator not found:** `->`, `->>`, `?`, `@>` and `jsonb_array_elements` are PostgreSQL-specific; consult the target database's SQL/JSON support.
- **Unexpected NULL:** distinguish absent key, JSON null and SQL NULL before using `COALESCE`.
- **Array expansion error:** guard `jsonb_array_elements` with `jsonb_typeof(...)= 'array'`.
- **Row count increased:** one-to-many expansion changes grain; reconcile distinct parent event IDs separately.
- **Unexpected text sorting:** `->>` returns text; typed numerical comparisons need validated conversion.
- **Operational safety:** never run unbounded JSON expansion against production, never use live credentials or sensitive patient data, and avoid dynamic SQL built from JSON field values. Apply statement timeouts, validate schema evolution and inspect execution plans before deploying JSON indexes.

## 6. Review questions and answers (55–60 minutes)

1. **When is JSON appropriate?** For optional or evolving attributes and raw event envelopes; model stable keys and required constraints relationally.
2. **How does `->>` differ from `->`?** It returns text rather than a JSON/JSONB value in PostgreSQL.
3. **Does missing key equal JSON null?** No; key-existence checks and JSON type inspection distinguish them.
4. **Why can array expansion lose or duplicate events?** Cross join emits one row per element and none for an empty array; use parent-aware joins and grain checks.
5. **Is PostgreSQL `@>` portable?** No; SQL/JSON support and syntax differ by vendor.
6. **What proves runtime validation?** Execution against an isolated PostgreSQL 18 instance with reproducible output and exit status, not manual reasoning.

## References

- [PostgreSQL 18 — JSON types](https://www.postgresql.org/docs/18/datatype-json.html)
- [PostgreSQL 18 — JSON functions and operators](https://www.postgresql.org/docs/18/functions-json.html)
- [PostgreSQL 18 — LATERAL subqueries](https://www.postgresql.org/docs/18/queries-table-expressions.html#QUERIES-LATERAL)
- [PostgreSQL 18 — JSON indexes](https://www.postgresql.org/docs/18/datatype-json.html#JSON-INDEXING)

**Status:** Authored; targeted static reasoning only. Independent editorial review, comprehensive syntax/link QA and isolated PostgreSQL 18 runtime validation pending.
