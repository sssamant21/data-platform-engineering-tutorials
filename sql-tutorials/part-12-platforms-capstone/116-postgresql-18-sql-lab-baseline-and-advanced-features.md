# 116 — PostgreSQL 18 SQL: Lab Baseline and Advanced Features

**Part 12 — Data Engineering, SQL Dialects & Final Projects · 60 minutes · Audience:** beginner data engineers, analysts, DBREs and SREs.

**Validation:** Authored material with targeted static/manual inspection. Independent editorial review, comprehensive parser/link QA, and actual isolated PostgreSQL 18 execution **pending**. All results below are calculated expectations, not observed output.

## 1. Outcomes and prerequisites (0–5 minutes)

By the end, you can verify the server version and disposable database, explain transaction and timeout safety, use PostgreSQL-specific `DISTINCT ON`, `FILTER`, `jsonb`, and `generate_series`, contrast these with portable alternatives, and interpret exact-result assertions. Read [003 — lab setup](../part-01-fundamentals/003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md), [071 — windows](../part-08-window-functions/071-window-function-anatomy-over-partition-by-order-by.md), [084 — JSON](../part-09-functions-json/084-json-and-semi-structured-sql-queries.md), and [115 — dialect testing](115-portable-sql-versus-vendor-specific-syntax-and-testing.md). If any prerequisite link is unavailable, consult [the master TOC](../MASTER-TOC.md).

**Agenda:** 5 minutes objectives, 10 concepts, 15 walkthrough, 20 lab, 5 troubleshooting, 5 review.

## 2. PostgreSQL 18 baseline and safety (5–15 minutes)

PostgreSQL is a relational database; SQL features are versioned. The tutorial targets **major version 18**, not just any PostgreSQL server. Confirm with `SHOW server_version;` and `SELECT current_setting('server_version_num');`. The lab insists on the **disposable database named `sql_tutorials`** and server version number from 180000 through 189999. This name check is a defense in depth, **not proof of isolation**: use a dedicated container or disposable instance and nonproduction credentials.

`BEGIN READ ONLY` prohibits writes in the transaction, including ordinary table DML. `SET LOCAL statement_timeout = '10s'` and `SET LOCAL lock_timeout = '2s'` limit runaway work and lock waits; `idle_in_transaction_session_timeout` limits abandoned sessions. `ROLLBACK` ends the transaction. Do not run any of these examples against a production database; the examples are synthetic and do not need external datasets. PostgreSQL `DO` and `RAISE EXCEPTION` provide a fail-closed assertion mechanism, not standard portable SQL.

| Feature | PostgreSQL-specific or portable? | Why data engineers and DBRE/SREs care |
|---|---|---|
| `ROW_NUMBER() OVER (PARTITION BY ... ORDER BY ...)` | Broadly portable SQL window syntax | Latest event per business key with deterministic tie-breaking |
| `DISTINCT ON (key)` | PostgreSQL extension | Compact latest-row query; requires matching leftmost `ORDER BY` expressions |
| `COUNT(*) FILTER (WHERE ...)` | SQL-standard feature, not universally implemented | Conditional quality and operational metrics |
| `jsonb`, `->>` | PostgreSQL-specific type/operators | Extract typed fields from event payloads |
| `generate_series()` | PostgreSQL set-returning function | Synthetic sequences and calendar scaffolding |
| `ON CONFLICT` | PostgreSQL extension | Idempotent writes; **not executed** in this read-only lab |

**Operational caveat:** `DISTINCT ON` chooses the *first* row per group after ordering. Always include a deterministic tie-breaker such as event ID. JSON extraction returns text; cast only after validating payload shape. `FILTER` does not eliminate the need to check row grain before joins. Never treat a green assertion as evidence of performance, concurrency safety, recovery readiness, or cross-engine portability.

## 3. Worked walkthrough (15–30 minutes)

Imagine five delivered change events for three fictional orders. Order 101 is updated, order 102 is deleted, and order 103 remains active. A duplicate or out-of-order delivery is possible in real CDC, so order by sequence **and** unique event ID.

```sql
WITH events(order_id, event_seq, event_id, operation, payload) AS (
  VALUES
    (101,1,1001,'U','{"amount":20}'::jsonb),
    (102,1,1002,'U','{"amount":50}'::jsonb),
    (101,2,1003,'U','{"amount":30}'::jsonb),
    (103,1,1004,'U','{"amount":40}'::jsonb),
    (102,2,1005,'D','{}'::jsonb)
)
SELECT DISTINCT ON (order_id)
       order_id, event_seq, operation, payload ->> 'amount' AS amount_text
FROM events
ORDER BY order_id, event_seq DESC, event_id DESC;
```

**Calculated rows:** (101,2,U,'30'), (102,2,D,NULL), (103,1,U,'40'). The deleted key is retained in the *latest-event* representation as a tombstone. Filtering out deletes **before** selecting the latest event would incorrectly resurrect order 102.

Portable-style equivalent, where supported:

```sql
WITH ranked AS (
  SELECT e.*, ROW_NUMBER() OVER (
    PARTITION BY order_id ORDER BY event_seq DESC, event_id DESC
  ) AS rn
  FROM events AS e
)
SELECT order_id, event_seq, operation
FROM ranked WHERE rn = 1 ORDER BY order_id;
```

Here `events` denotes the CTE from the preceding example; the second snippet is conceptual unless that CTE is included. A real CDC pipeline must also handle transaction boundaries, checkpoint advancement, schema changes, and exactly-once *effects* through idempotency—not assume exactly-once delivery.

For conditional totals, calculate from latest rows, not all delivered events:

```sql
SELECT COUNT(*) FILTER (WHERE operation = 'D') AS tombstones
FROM latest_events;
```

`latest_events` is an illustrative relation. Calculated result: **1 tombstone**. Among active latest events, numeric amounts 30 and 40 total **70.00**. A naïve sum of every delivered amount gives 140.00 and is wrong for current state.

## 4. Hands-on isolated PostgreSQL 18 lab (30–50 minutes)

Run the companion [Chapter 116 SQL lab](../labs/116-postgresql-18-baseline-advanced-features.sql) from the repository root, after provisioning a **separate disposable PostgreSQL 18 instance** with database `sql_tutorials`. Do not connect to managed production databases.

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials \
  -f sql-tutorials/labs/116-postgresql-18-baseline-advanced-features.sql
```

**Practice sequence:** (1) verify the server/database guard; (2) examine the five synthetic events; (3) compare `DISTINCT ON` to `ROW_NUMBER`; (4) inspect JSON `->>` text and explicit numeric conversion; (5) calculate active total, tombstone count, and `generate_series(1,3)`; (6) review the bidirectional duplicate-aware `EXCEPT ALL` assertions; (7) confirm `ROLLBACK`. No persistent objects or data are created.

**Calculated expected results:** five delivered events; three latest keys; two active keys; one tombstone; active amount total 70.00; three generated integers (1,2,3); zero mismatches between latest-event methods and the expected rows. A passing assertion notice is only meaningful if **actually observed** on an isolated PostgreSQL 18 runtime.

## 5. Validation, troubleshooting and production safeguards (50–55 minutes)

- **Wrong database/version:** the guard raises an exception; stop and provision the correct isolated instance. Do not bypass the guard.
- **Permission or connection error:** check disposable database existence and the lab-only role; never substitute production credentials.
- **Wrong latest row:** ensure `ORDER BY order_id, event_seq DESC, event_id DESC`; compare to the window-function result and check unique event IDs.
- **Unexpected NULL amount:** a delete tombstone has no amount; do not coerce it into an active order.
- **Timeout:** investigate environment health and query behavior rather than increasing production timeouts.
- **Assertion mismatch:** retain SQL, PostgreSQL version, command, stdout/stderr, and exit status; mark runtime acceptance **failed**, not validated.

For a future runtime evidence record, capture container image digest, `SELECT version()`, disposable database identity, the exact Git commit, `psql -X -v ON_ERROR_STOP=1` command, output, exit code, and independent reviewer. None of that evidence is claimed here.

## 6. Review questions and answers (55–60 minutes)

1. **Why require a unique event-ID tie-breaker?** To select the same latest row when sequences tie.
2. **Why retain delete tombstones through ranking?** Filtering them early can resurrect deleted keys.
3. **Is `DISTINCT ON` portable SQL?** No; use a `ROW_NUMBER` strategy for engines supporting windows.
4. **What does `->>` return?** Text (or NULL); explicitly cast valid numeric payload values before arithmetic.
5. **Does `ROLLBACK` prove the server is isolated?** No; isolation must be established outside SQL.
6. **What is the difference between authored and runtime-validated?** Runtime validation requires execution on an isolated PostgreSQL 18 instance with reproducible retained evidence.

## References and navigation

- [PostgreSQL 18 — SELECT and DISTINCT ON](https://www.postgresql.org/docs/18/sql-select.html)
- [PostgreSQL 18 — JSON functions and operators](https://www.postgresql.org/docs/18/functions-json.html)
- [PostgreSQL 18 — window functions](https://www.postgresql.org/docs/18/tutorial-window.html)
- [PostgreSQL 18 — set-returning functions](https://www.postgresql.org/docs/18/functions-srf.html)
- [PostgreSQL 18 — transaction modes](https://www.postgresql.org/docs/18/sql-set-transaction.html)
- [PostgreSQL 18 — runtime configuration](https://www.postgresql.org/docs/18/runtime-config-client.html)
- [Master TOC](../MASTER-TOC.md) · [Part 12 navigation](../README.md) · [Status tracker](../STATUS-TRACKER.md)

**Next:** Chapter 117 — MySQL and MariaDB: key syntax and behavior differences (not yet linked as published).
