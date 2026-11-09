# 032 — INSERT ... SELECT and Bulk-Loading Fundamentals

**Part 04 — Data Modification & Transaction Fundamentals** · **60 minutes** · **PostgreSQL 18 isolated lab**

[Master TOC](../MASTER-TOC.md) · [Previous: 031](031-insert-single-row-and-multi-row-records.md) · [Runnable lab](../labs/032-insert-select-bulk-loading.sql) · [Status](../STATUS-TRACKER.md)

> **Safety:** Run write demonstrations only on an independently verified disposable PostgreSQL 18 instance, dedicated `sql_tutorials` database and nonproduction credentials. Database-name/version guards alone cannot establish isolation. This lab uses temporary tables and rolls back. Never point it at a production endpoint.

## 0–5 min — Objectives and prerequisites

By the end you can: (1) distinguish `INSERT ... VALUES` from `INSERT ... SELECT`; (2) transform source rows during ingestion; (3) reconcile input, accepted and rejected counts; (4) compare multi-row INSERT, INSERT SELECT and PostgreSQL COPY; (5) explain atomicity, retries and idempotency; and (6) design operational safeguards. Review [Chapter 031](031-insert-single-row-and-multi-row-records.md), [constraints](../part-03-modeling/026-not-null-check-default-and-constraint-validation.md) and [keys](../part-03-modeling/024-primary-keys-natural-keys-surrogate-keys-and-unique.md).

## 5–15 min — Core syntax and portability

`INSERT ... SELECT` copies the rows produced by a query into a destination. It is useful for staging-to-curated transformations and backfills.

```sql
INSERT INTO curated_events (event_id, customer_id, amount)
SELECT event_id, customer_id, amount
FROM staging_events
WHERE amount >= 0;
```

This is broadly portable SQL; target columns should be explicit and source expression types compatible. `SELECT` does not guarantee insertion order. Use explicit filters to avoid accidentally loading all source rows. A source-to-target schema change can break positional inserts, so never rely on `SELECT *` for production pipelines.

`INSERT INTO ... SELECT` is not automatically a deduplication strategy. Replays require a stable source key, uniqueness constraint, and reviewed conflict policy. `INSERT ... SELECT` is a single SQL statement; a constraint violation ordinarily causes the statement to fail atomically. Transaction boundaries determine whether earlier statements commit.

**Vendor notes:** PostgreSQL supports `COPY FROM STDIN`, `COPY FROM '/server/path'` (server-side permissions), and `\\copy` in psql (client-side). `COPY` is PostgreSQL-specific; SQL Server BULK INSERT, MySQL LOAD DATA and cloud warehouse COPY/LOAD commands have different permissions and semantics. `ON CONFLICT` is PostgreSQL-specific; MERGE support and behavior differ across engines. Do not assume COPY automatically validates CSV business rules or prevents duplicates.

## 15–30 min — Worked example: synthetic retail event pipeline

A staging batch has five synthetic events:

| Event | Customer | Raw amount | Meaning |
|---|---|---:|---|
| EV-101 | C-01 | 12.50 | accepted |
| EV-102 | C-02 | 20.00 | accepted |
| EV-103 | C-03 | -4.00 | rejected: negative |
| EV-104 | C-01 | 7.25 | accepted |
| EV-105 | C-04 | NULL | rejected: missing |

The lab builds a temporary staging table, inserts these five rows, and uses a filtered `INSERT ... SELECT` into a constrained temporary curated table. Expected accepted IDs: EV-101, EV-102, EV-104; accepted total: **39.75**. Rejected count: **2**. The acceptance check asserts **5 = 3 + 2** and verifies exact IDs, not just aggregate totals.

```sql
INSERT INTO curated_events (event_id, customer_id, amount)
SELECT event_id, customer_id, raw_amount
FROM staging_events
WHERE raw_amount IS NOT NULL AND raw_amount >= 0;
```

Filtering invalid records is a teaching example, **not** an adequate production quarantine process. Real ingestion should persist reject reasons in a controlled, auditable staging/reject workflow, with lineage, batch identifiers and access controls. Keep monetary amounts in exact `NUMERIC` types, not floating-point types.

### Choosing an ingestion method

| Method | Appropriate when | Important risks |
|---|---|---|
| Multi-row `INSERT VALUES` | Small application batches | Client-side SQL size, repeated round trips |
| `INSERT ... SELECT` | Set-based in-database transformations | Incorrect joins, filters, duplicates, large transactions |
| PostgreSQL `COPY` | Large file/stream import into staging | File permissions, parsing failures, WAL, locks, error handling |

A measured throughput comparison must control for batch size, indexes, constraints, durability, network and concurrency. No universal fastest method exists.

## 30–50 min — Hands-on isolated lab

1. Provision the disposable PostgreSQL 18 lab described in [Chapter 003](../part-01-fundamentals/003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md). Verify the actual host, port, user, container and database independently.
2. Inspect [the SQL lab](../labs/032-insert-select-bulk-loading.sql) before running it. It sets short timeouts, asserts the major version/database/primary state, creates only temporary objects, and ends in `ROLLBACK`.
3. From the repository root, run:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials \
  -f sql-tutorials/labs/032-insert-select-bulk-loading.sql
```

4. Verify the ordered accepted IDs, the reconciliation result and `lab_acceptance = PASS`. A successful script execution is not proof of isolation; retain environment and execution evidence for runtime acceptance.
5. **Exercise A:** In a local copy, add a sixth valid row `EV-106` for 10.00. Update expected assertions: source 6, accepted 4, rejected 2, total 49.75.
6. **Exercise B:** Change the filter to `raw_amount > 0`. Explain the effect on a hypothetical zero-amount event and whether your business rules permit it.
7. **Exercise C:** Explain why a second run against a persistent destination would require a reviewed idempotency design.
8. **Exercise D:** Sketch a two-stage COPY workflow: load a file into an isolated staging table, validate and quarantine rows, then INSERT SELECT into curated storage. Do not run server-side file import on shared infrastructure.

## 50–55 min — Troubleshooting and operational guardrails

| Symptom | Likely cause | Safe action |
|---|---|---|
| Unique violation `23505` | Duplicate source key or replay | Reconcile batch keys; do not silently ignore |
| Check violation `23514` | Invalid transformed value | Quarantine and inspect source |
| Not-null violation `23502` | Missing required value | Validate mapping and input |
| Transaction aborted `25P02` | Earlier SQL error | ROLLBACK and diagnose |
| Unexpected row counts | Filter or join fan-out | Compare source, reject and accepted ID sets |
| Slow import / replica lag | WAL, indexes, locks or large batch | Measure staging workload; reduce batch size as appropriate |
| COPY permission error | Server-file permissions or role restrictions | Prefer authorized client-side `\\copy` in isolated lab |

**DBRE/SRE checklist:** preview `SELECT` and counts, verify destination and privileges, use an explicit transaction, monitor WAL and replication, cap batch size and runtime, enforce uniqueness and business rules, maintain batch audit and reject records, test restart/retry semantics, and document rollback or restore plans. Avoid disabling constraints to force a load through.

## 55–60 min — Review questions with answers

1. **How does INSERT SELECT differ from VALUES?** It inserts a query's result rows rather than literal row lists.
2. **Does INSERT SELECT deduplicate automatically?** No; implement explicit uniqueness and retry policy.
3. **Why not use SELECT *?** Source column order/schema changes can corrupt mappings or break the load.
4. **What does 5 = 3 + 2 verify?** Source-to-accepted/rejected count reconciliation; exact ID checks are still needed.
5. **When is COPY useful?** Large bulk imports into a validated staging workflow.
6. **Is COPY portable?** No; syntax, access and error semantics differ by database.
7. **Does ROLLBACK make a production connection safe?** No; isolation must be independently established.

## References

- [PostgreSQL 18 INSERT](https://www.postgresql.org/docs/18/sql-insert.html)
- [PostgreSQL 18 COPY](https://www.postgresql.org/docs/18/sql-copy.html)
- [PostgreSQL 18 psql](https://www.postgresql.org/docs/18/app-psql.html)
- [PostgreSQL 18 Transactions](https://www.postgresql.org/docs/18/tutorial-transactions.html)

**Next:** Chapter 033 — UPDATE with safe predicates and preview queries.

**Validation:** Authorship/publication and targeted static reasoning are separate from independent editorial review, comprehensive syntax checks and actual PostgreSQL 18 runtime execution. The latter require retained evidence.
