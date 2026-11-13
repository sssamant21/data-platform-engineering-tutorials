# 113 — ELT, Incremental Loads, and Change Data Capture Patterns

**Part 12 — Data Engineering, SQL Dialects & Final Projects | 60 minutes | Audience:** beginner data engineers, analysts, DBREs, SREs.

**Validation status:** authored; independent editorial review pending; targeted static inspection only; **not executed on PostgreSQL 18**. Expected results are calculated, not observed.

## 1. Outcomes and prerequisites (0–5 minutes)

After this chapter, explain ETL versus ELT, full refresh versus incremental processing, high-water marks, CDC ordering and deletes, idempotent replay, late arrivals, and safe promotion gates. Prerequisites: [036 — UPSERT and MERGE](../part-04-data-modification/036-upsert-and-merge-patterns-across-sql-dialects.md), [107 — Data quality assertions](../part-11-security-operations/107-data-quality-assertions-and-reconciliation-queries.md), and [112 — Star schemas](112-star-schemas-facts-dimensions-and-surrogate-keys.md).

**Plan:** outcomes 5 min; concepts 10; worked example 15; lab 20; troubleshooting 5; review 5.

## 2. Concepts (5–15 minutes)

**ETL** transforms data before loading the target; **ELT** loads raw/staged records first, then transforms them in the analytical platform. Neither guarantees quality or exactly-once effects. A **full refresh** recomputes the complete target; an **incremental load** applies a bounded set of changes. **CDC** conveys inserts, updates, and deletes from a source change stream, typically with source ordering metadata (LSN/offset/sequence), operation, primary key, and event time.

A timestamp watermark is easy to understand but unsafe by itself: ties, clock skew, delayed events, and source updates to old records can cause omissions. Prefer a stable source cursor (for example, commit LSN plus event ordinal) and retain a replay overlap or durable checkpoint. An extraction checkpoint means **all earlier events have been durably applied**, not merely read.

An idempotent target converges to the same state after replaying a committed batch. Deduplicate by source event identity, choose the latest event per business key using a deterministic ordering, and compare that ordering with the target's last applied cursor. An event's ingestion time is not its business-effective time; historical corrections may require recomputing affected downstream aggregates or SCD2 versions.

**Delete/tombstone:** an event can remove a target row or mark it deleted; never silently ignore deletes. A CDC retention gap requires a controlled re-snapshot/reconciliation, not guessing the missing events. Kafka offsets, database LSNs, and cloud ingestion metadata are platform-specific; SQL window functions and joins are broadly portable, though syntax differs.

## 3. Worked synthetic example (15–30 minutes)

Suppose a warehouse currently holds two fictional orders: order 10 amount 50.00 and order 20 amount 30.00. The incoming source change batch is:

| Cursor | Event ID | Order | Operation | Amount |
|---:|---|---:|---|---:|
| 101 | e101 | 10 | U | 55.00 |
| 102 | e102 | 30 | I | 20.00 |
| 103 | e103 | 20 | D | NULL |
| 104 | e104 | 10 | U | 60.00 |
| 104 | e104 | 10 | U | 60.00 |

The final row repeats the same event ID and cursor: it represents a duplicate delivery, **not** a new change. First deduplicate exact event identities, then rank by cursor for each order:

```sql
WITH changes(cursor_no, event_id, order_id, op, amount) AS (
  VALUES (101,'e101',10,'U',55.00),
         (102,'e102',30,'I',20.00),
         (103,'e103',20,'D',NULL),
         (104,'e104',10,'U',60.00),
         (104,'e104',10,'U',60.00)
), distinct_events AS (
  SELECT DISTINCT cursor_no,event_id,order_id,op,amount FROM changes
), ranked AS (
  SELECT *, ROW_NUMBER() OVER (
    PARTITION BY order_id ORDER BY cursor_no DESC, event_id DESC
  ) AS rn FROM distinct_events
)
SELECT order_id, op, amount
FROM ranked WHERE rn=1 ORDER BY order_id;
```

**Calculated result:** order 10 U 60.00; order 20 D NULL; order 30 I 20.00. The final active target is order 10 = 60.00 and order 30 = 20.00; 2 rows totaling 80.00. Cursor 104 is safe to checkpoint **only after** the target changes, validation, and durable commit succeed. This example assumes each source cursor has a total order; in a real CDC system, define a compound cursor if multiple events share a position.

**Portability:** `VALUES`, `DISTINCT`, `ROW_NUMBER()`, `CASE`, and `WITH` are broadly supported but their exact use and type inference vary. PostgreSQL `INSERT ... ON CONFLICT`, SQL Server/Oracle `MERGE`, Snowflake `MERGE`, and BigQuery `MERGE` have different syntax and concurrency semantics. Do not copy a production write statement across vendors without testing.

## 4. Hands-on lab (30–50 minutes)

Run [113 — read-only incremental CDC simulation](../labs/113-elt-incremental-loads-cdc-patterns.sql) only in a disposable isolated PostgreSQL **18** database called `sql_tutorials`:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/113-elt-incremental-loads-cdc-patterns.sql
```

The lab uses synthetic CTEs, a read-only transaction, version/database checks, transaction-local timeouts, assertions, and `ROLLBACK`. It does not create tables, apply CDC, advance a real checkpoint, or touch any production system.

**Practice:** (1) list unique event IDs; (2) identify the latest event for each order; (3) explain the tombstone; (4) calculate final active order count and total; (5) simulate replay of the same batch and explain why the outcome is unchanged; (6) change event 104 to cursor 99 in a scratch copy and explain why a target cursor guard is required. Optional: add a late update with an older business timestamp but newer commit cursor and distinguish these clocks.

**Calculated expected results:** 5 delivered messages; 4 distinct events; 3 latest-key events; 2 active orders; total 80.00; one deleted order; zero assertion mismatches.

## 5. Production design and troubleshooting (50–55 minutes)

| Symptom | Likely cause | Safe action |
|---|---|---|
| Missing records | timestamp-only watermark, retention gap | stop promotion; inspect source cursor coverage; re-snapshot if needed |
| Double-counted revenue | replay without idempotency or grain mismatch | compare event IDs and target keys; reconcile at business-key grain |
| Deleted rows reappear | tombstones ignored or stale updates applied | persist last-applied cursor; reject stale events |
| Late corrections absent | only event-time filter used | reprocess affected partitions and dependent aggregates |
| CDC lag increases | consumer backpressure, target contention | measure source-to-apply lag, queue depth, lock waits |
| Target and source totals match but rows differ | offsetting discrepancies | bidirectional key-level `EXCEPT ALL` comparison |

**DBRE/SRE deployment controls:** isolate raw staging from published tables; use least-privilege credentials and encrypted transport; never log payload secrets; define source retention and recovery limits; monitor cursor progress and lag; reconcile counts, key sets, amounts, and delete semantics; hold checkpoint advancement until a durable transaction commits. On failure, retain immutable batch metadata and replay safely. A read-only teaching exercise does not establish CDC connector correctness, exactly-once delivery, crash consistency, or performance. Production backfills, schema changes, and deletes require approved change windows, tested recovery, and accountable owners.

## 6. Review questions with answers (55–60 minutes)

1. **ETL versus ELT?** Transformation before loading versus transformation after loading into staging/warehouse.
2. **Why is `updated_at > watermark` insufficient?** Late arrivals, ties, and timestamp inconsistencies can skip changes.
3. **What makes replay safe?** Stable event identity, deterministic ordering, and cursor-guarded idempotent application.
4. **What does a CDC delete require?** Explicit tombstone/delete handling and prevention of stale resurrection.
5. **When advance the checkpoint?** After applying, reconciling, and durably committing the corresponding changes.
6. **Does equal total revenue prove correctness?** No; row-level mismatches can offset.

**Next:** 114 — Data warehouse SQL and analytical cost considerations (planned; link will be added after publication).

**References:** [PostgreSQL 18 — Logical replication](https://www.postgresql.org/docs/18/logical-replication.html); [PostgreSQL 18 — Window functions](https://www.postgresql.org/docs/18/tutorial-window.html); [PostgreSQL 18 — INSERT / ON CONFLICT](https://www.postgresql.org/docs/18/sql-insert.html); [PostgreSQL 18 — Transaction isolation](https://www.postgresql.org/docs/18/transaction-iso.html).
