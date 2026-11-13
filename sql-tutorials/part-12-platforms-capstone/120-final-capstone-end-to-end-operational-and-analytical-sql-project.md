# 120 — Final Capstone: End-to-End Operational and Analytical SQL Project

**Part 12 — Data Engineering, SQL Dialects & Final Projects | 60 minutes | Audience:** beginner data engineers, analytics engineers, DBREs and SREs.

**Status:** Authored capstone; expected results calculated from synthetic input. Independent editorial review, comprehensive automated static QA and isolated PostgreSQL 18 runtime execution are **pending**.

## 1. Objectives and prerequisites (0–5 minutes)

Build a small, reproducible order-processing pipeline that moves from delivered change events to a trustworthy analytical report. By the end you can (1) define the event and fact grains, (2) deduplicate replayed CDC events, (3) preserve deletes, (4) reconcile totals without join fan-out, (5) produce operational acceptance evidence, and (6) explain rollback, access control, and portability.

Prerequisites: [003 — PostgreSQL 18 lab setup](../part-01-fundamentals/003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md), [107 — data quality](../part-11-security-operations/107-data-quality-assertions-and-reconciliation-queries.md), [111 — OLTP vs OLAP](111-oltp-versus-olap-query-design.md), [112 — star schema](112-star-schemas-facts-dimensions-and-surrogate-keys.md), [113 — CDC](113-elt-incremental-loads-and-change-data-capture-patterns.md), [115 — portability](115-portable-sql-versus-vendor-specific-syntax-and-testing.md), [119 — cloud analytical SQL](119-snowflake-and-bigquery-cloud-analytical-sql-patterns.md).

## 2. Architecture and contract (5–15 minutes)

**Synthetic source events → delivery deduplication → latest event per order → active order fact → daily region KPI → quality gate.** This is a *query-only simulation*, not a deployed Kafka connector, production ETL job, or disaster-recovery exercise.

Each delivered message has an immutable `event_id`, business key `order_id`, timestamp `event_ts`, operation `U` (upsert) or `D` (delete), region and amount. Event identity is distinct from business-key identity: a retry can repeat an event, while an order can legitimately have multiple different events. An ordering tie uses `event_id` after timestamp; real systems require a trustworthy monotonic source sequence/LSN and documented conflict rules. The analytical grain is **one active row per order**, not one row per event. Never discard delete events before selecting the latest state.

The SQL uses standard-style `WITH`, `ROW_NUMBER`, `CASE`, `GROUP BY`, and `EXCEPT` concepts. `VALUES` with PostgreSQL casts, `DO` blocks, `SET LOCAL`, `EXCEPT ALL`, `current_setting` and transaction-local guardrails are **PostgreSQL-specific lab mechanics**. Snowflake and BigQuery offer `QUALIFY` for post-window filtering, but syntax, types, timestamp semantics, partition pruning and costs must be separately tested; no cross-engine execution is claimed.

## 3. Worked example: expected business state (15–30 minutes)

Six unique source events arrive as **seven delivered messages** because event 2 is retried:

| Event | Order | Timestamp (UTC, synthetic) | Operation | Region | Amount |
|---:|---:|---|---|---|---:|
| 1 | 701 | Jan 1 09:00 | U | East | 40.00 |
| 2 | 702 | Jan 1 09:05 | U | West | 20.00 |
| 2 (retry) | 702 | Jan 1 09:05 | U | West | 20.00 |
| 3 | 701 | Jan 2 10:00 | U | East | 55.00 |
| 4 | 703 | Jan 2 11:00 | U | West | 30.00 |
| 5 | 702 | Jan 3 08:00 | D | West | NULL |
| 6 | 704 | Jan 3 09:00 | U | East | 15.00 |

First rank deliveries by `event_id` to remove identical retries, then rank the unique events by `order_id ORDER BY event_ts DESC, event_id DESC`. Filter `operation = 'U'` **after** ranking. The final active orders are 701 (55.00 East), 703 (30.00 West), and 704 (15.00 East). Order 702 is deleted.

Expected analytical KPI, grouped by region:

| Region | Active orders | Revenue |
|---|---:|---:|
| East | 2 | 70.00 |
| West | 1 | 30.00 |
| **Total** | **3** | **100.00** |

**Important distinction:** the KPI is a *current-state* snapshot, not historical sales revenue by order date. For historical event-time metrics, retain immutable facts and explicit reversal logic; do not reuse a current-state snapshot as a financial ledger.

## 4. Hands-on PostgreSQL 18 lab (30–50 minutes)

Use a **disposable local database named `sql_tutorials`** with PostgreSQL major version 18. Do not use a production connection or real customer data. Run [the capstone SQL file](../labs/120-final-capstone-operational-analytical-sql.sql) through `psql` with error stopping:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/120-final-capstone-operational-analytical-sql.sql
```

Run from the repository root; set a local sandbox connection via normal `PGHOST`/`PGPORT` or explicit `-h` and `-p`. Avoid environment variables or command history containing passwords; use a dedicated least-privilege sandbox role. The file begins a read-only transaction, sets local statement/lock/idle timeouts, checks the database name and server major version, uses only synthetic `VALUES`, asserts the expected metrics, and ends with `ROLLBACK`. It creates no tables, users, roles, extensions or persistent checkpoints.

**Exercise A (5 min):** Explain why seven deliveries become six unique events, then four latest order states.

**Exercise B (5 min):** Inspect the active orders and explain why the deleted order must not be resurrected.

**Exercise C (5 min):** Reconcile region totals to the active fact. Verify the exact assertions report zero differences; this is a calculated expectation until the SQL is actually run.

**Exercise D (5 min):** Modify the *copy in your disposable workspace* to add a second retry of event 4. Predict that unique event count and final revenue remain unchanged. Restore the original file before recording acceptance.

## 5. Operational acceptance and troubleshooting (50–55 minutes)

A successful run requires the **actual** PostgreSQL 18 version, isolated database identity, exit code 0, exact-result assertion notice, and no SQL errors. Record the command, Git commit SHA, database version, sanitized output, and execution date in a separate QA evidence artifact. **Do not mark runtime-validated based on calculated expected results or a successful GitHub upload.**

| Symptom | Likely cause | Safe response |
|---|---|---|
| Guard raises exception | Wrong database or PostgreSQL version | Stop; reconnect to isolated PostgreSQL 18 |
| Active order 702 appears | Tombstones filtered before ranking | Rank all changes first |
| Seven events counted as unique | Delivery retries not deduplicated | Partition by immutable event identity |
| KPI total inflated | Join fan-out or double-counting | Aggregate at one-row-per-order grain |
| SQL times out | Unexpected plan or unavailable sandbox | Inspect locally; do not increase production limits |
| Assertion fails | Data, ordering or expectation mismatch | Preserve failure evidence; investigate before acceptance |

For a real deployment, require source-offset/LSN checkpoint durability, schema-contract tests, late-event policy, duplicate/conflict handling, data freshness SLO, replay strategy, observability, and a documented rollback/cutover plan. DBRE owns database access, resource limits, backup/restore and operational guardrails; data engineering owns CDC semantics, transformations and reconciliation; application owners approve business meaning and downstream consumption. Ownership is agreed by the team, not inferred from this tutorial.

## 6. Review and answer key (55–60 minutes)

1. **Why deduplicate by event ID and then order ID?** The first removes transport retries; the second selects current business state.
2. **Why retain tombstones until after ranking?** Removing them early can resurrect deleted records.
3. **Why not sum event amounts?** Updates and retries are not independent sales; summing them double-counts.
4. **What makes this lab safe?** Synthetic in-memory values, sandbox/version guards, read-only transaction, timeouts, and rollback.
5. **Does an assertion in a file prove runtime validation?** No; retain executed results from isolated PostgreSQL 18.
6. **What must be revalidated on Snowflake/BigQuery?** Dialect syntax, NULL/time behavior, ordering, result parity, query scan/compute costs and permissions.

## Completion criteria and next work

Capstone authoring is complete only when chapter, lab and navigation are published and fetched back. **Curriculum completion is not certification.** Next: comprehensive static link/syntax QA for chapters 001–120, independent editorial and expected-output review, then isolated PostgreSQL 18 execution with retained evidence and tracked defects. Freeze new chapter authoring once 120 are published.

## References

- [PostgreSQL 18 SELECT and WITH](https://www.postgresql.org/docs/18/sql-select.html)
- [PostgreSQL 18 window functions](https://www.postgresql.org/docs/18/tutorial-window.html)
- [PostgreSQL 18 transaction control](https://www.postgresql.org/docs/18/tutorial-transactions.html)
- [PostgreSQL 18 runtime configuration: client connection defaults](https://www.postgresql.org/docs/18/runtime-config-client.html)
- [Google BigQuery QUALIFY](https://cloud.google.com/bigquery/docs/reference/standard-sql/query-syntax#qualify_clause)
- [Snowflake QUALIFY](https://docs.snowflake.com/en/sql-reference/constructs/qualify)
