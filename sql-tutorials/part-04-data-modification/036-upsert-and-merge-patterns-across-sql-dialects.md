# 036 — UPSERT and MERGE Patterns Across SQL Dialects

**Part 04 — Data Modification & Transaction Fundamentals** · **60 minutes** · **PostgreSQL 18 isolated lab**

[Master TOC](../MASTER-TOC.md) · [Previous: 035](035-delete-versus-truncate-versus-drop.md) · [Lab SQL](../labs/036-upsert-merge-patterns.sql) · [Status tracker](../STATUS-TRACKER.md)

> **Safety:** All write examples are for an independently verified disposable PostgreSQL 18 database with synthetic inventory only. A database-name guard is not proof of isolation. Never run these examples against production data or with production credentials. The lab uses temporary objects, timeouts, a transaction, assertions, and ROLLBACK.

## 0–5 minutes — Outcomes and prerequisites

You will explain the insert-or-update problem, choose a conflict key, implement PostgreSQL `ON CONFLICT`, compare standard-style `MERGE`, design version-aware idempotent ingestion, recognize concurrency and dialect risks, and reconcile changed rows. Prerequisites: [INSERT](031-insert-single-row-and-multi-row-records.md), [UPDATE](033-update-with-safe-predicates-and-preview-queries.md), [primary and unique keys](../part-03-modeling/024-primary-keys-natural-keys-surrogate-keys-and-unique.md).

**Scenario:** A synthetic retail inventory feed periodically sends the latest absolute stock quantity for each SKU. Replays and out-of-order arrivals are expected. A unique SKU is the business key; `source_version` increases for newer source records. This example models **state replacement**, not additive inventory movements.

## 5–15 minutes — Concepts and portability

A naïve `SELECT` followed by `INSERT` or `UPDATE` has a race: another session may insert the key after the check. A unique constraint and database-supported conflict handling are essential. A duplicate key is not necessarily an error in an ingestion workflow; it may mean an existing row should be updated or left unchanged.

| Pattern | PostgreSQL 18 | Other SQL systems / portability |
|---|---|---|
| Insert or ignore | `INSERT ... ON CONFLICT (sku) DO NOTHING` | SQLite has ON CONFLICT; MySQL `INSERT IGNORE` differs in error handling |
| Insert or update | `INSERT ... ON CONFLICT (sku) DO UPDATE SET ...` | SQLite similar syntax; MySQL/MariaDB `ON DUPLICATE KEY UPDATE` with different conflict semantics |
| Conditional matched/not-matched actions | `MERGE INTO ... USING ... ON ... WHEN MATCHED ... WHEN NOT MATCHED ...` | SQL standard concept; PostgreSQL, SQL Server, Oracle, Snowflake and others differ in syntax, behavior and supported clauses |
| Verify affected rows | PostgreSQL `RETURNING` for INSERT/ON CONFLICT | SQL Server `OUTPUT`; others vary; covered next chapter |

**Key distinction:** `ON CONFLICT` is PostgreSQL-specific syntax, not portable ANSI SQL. `MERGE` is standardized in concept, but **not** a drop-in portable script. PostgreSQL `MERGE` and `INSERT ... ON CONFLICT` do not offer identical concurrency guarantees: `ON CONFLICT DO UPDATE` provides an atomic insert-or-update outcome for each proposed row when no independent error occurs; a concurrent insert can still cause `MERGE` to raise a uniqueness violation. Build retry handling and test your chosen engine.

**Data quality first:** deduplicate a source batch to one row per business key; validate nonnegative quantities, positive versions, and monotonically increasing versions; reconcile accepted, stale, and rejected records. A `MERGE` that attempts to modify the same target row more than once can fail. Do not assume last-write-wins from unordered input.

## 15–30 minutes — Worked example

The isolated lab starts with:

| sku | quantity | source_version |
|---|---:|---:|
| SKU-A | 10 | 1 |
| SKU-B | 5 | 2 |

The feed contains A=(12,2), B=(99,1), C=(7,1). The older B event must not overwrite B version 2.

**PostgreSQL 18 UPSERT:**

```sql
INSERT INTO inventory (sku, quantity, source_version)
VALUES ('SKU-A',12,2), ('SKU-B',99,1), ('SKU-C',7,1)
ON CONFLICT (sku) DO UPDATE
SET quantity = EXCLUDED.quantity,
    source_version = EXCLUDED.source_version
WHERE EXCLUDED.source_version > inventory.source_version
RETURNING sku;
-- Expected returned keys: SKU-A, SKU-C
-- SKU-B remains quantity 5/version 2; C inserted; A updated
```

`EXCLUDED` denotes the proposed insert row. The `WHERE` on the conflict update suppresses stale and equal-version updates; suppressed rows are not returned. The target requires a matching unique index/constraint. This operation is safe to retry for **the same absolute values and version**, but that does not make every possible UPSERT idempotent (e.g., `quantity = quantity + EXCLUDED.quantity` is not).

**PostgreSQL 18 MERGE:**

```sql
MERGE INTO inventory AS target
USING (VALUES ('SKU-B',8,3), ('SKU-D',4,1), ('SKU-A',999,1))
  AS incoming(sku, quantity, source_version)
ON target.sku = incoming.sku
WHEN MATCHED AND incoming.source_version > target.source_version THEN
  UPDATE SET quantity=incoming.quantity, source_version=incoming.source_version
WHEN NOT MATCHED THEN
  INSERT (sku,quantity,source_version)
  VALUES (incoming.sku,incoming.quantity,incoming.source_version);
```

B updates to 8/version 3; D inserts 4/version 1; A's stale version 1 is ignored. Final state: A=12, B=8, C=7, D=4; **4 SKUs, quantity sum 31**. Replaying the same MERGE should leave the final state unchanged. The full lab tests this.

### Production-minded design notes

A version number is useful only when the upstream system guarantees a meaningful order. Timestamp-only ordering can collide or arrive late; define tie-breakers or source sequence numbers. If a feed contains additive stock movements, store immutable movement IDs and deduplicate events instead of overwriting quantities. Decide whether missing keys mean unchanged or deleted; this lab never deletes missing rows. For healthcare or financial records, retain provenance and audit history rather than silently overwriting prior states.

## 30–50 minutes — Hands-on lab

1. Provision an isolated PostgreSQL 18 instance using [Chapter 003](../part-01-fundamentals/003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md). Independently verify host, container, database, role, and endpoint.
2. Read [036 lab SQL](../labs/036-upsert-merge-patterns.sql) before execution. Confirm `CREATE TEMP TABLE`, version/database/standby guard, `SET LOCAL` timeouts, and final `ROLLBACK`.
3. From repository root run:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials \
  -f sql-tutorials/labs/036-upsert-merge-patterns.sql
```

4. Inspect expected output:

```text
SKU-A | 12 | 2
SKU-B |  8 | 3
SKU-C |  7 | 1
SKU-D |  4 | 1
PASS  |  4 | 31 | 2
```

5. **Exercise A:** Change the stale B UPSERT input to version 4 and predict the outcome (quantity becomes 99); do this only in a copied disposable lab.
6. **Exercise B:** Explain why a duplicate SKU in one `ON CONFLICT DO UPDATE` statement can produce a cardinality error. Propose source deduplication with a deterministic version/order rule.
7. **Exercise C:** Sketch a safe CDC pipeline with landing, validation, deduplication, version checks, merge, reconciliation and retry evidence.
8. **Exercise D:** Replay the MERGE and prove all four rows and the sum remain unchanged.

## 50–55 minutes — Troubleshooting and DBRE/SRE controls

| Symptom | Likely cause | Safe action |
|---|---|---|
| `42P10` no matching unique/exclusion constraint | Incorrect `ON CONFLICT` target | Inspect unique constraints; do not remove uniqueness |
| `23505` duplicate key during MERGE | Concurrent insert or duplicate source key | Deduplicate, retry boundedly, investigate key |
| `21000` cardinality violation | Same target row affected twice in a statement | Enforce one source row per key |
| Unexpected stale overwrite | No source version guard | Require strict source version comparison |
| Deadlock `40P01` or serialization failure `40001` | Concurrent transactions | Roll back entire transaction, retry with bounded backoff |
| Lock timeout `55P03` | Contended target | Inspect blockers, reduce batch size, reschedule |
| Sum mismatch | Incorrect accepted/stale classification | Reconcile per-key and aggregate results before commit |

**Operational safeguards:** verify the exact target environment; constrain privileges; enforce unique keys and check constraints; preview candidate counts; cap batch sizes; record batch ID, source high-water mark and accepted/rejected/stale counts; test retries and concurrency; set lock and statement timeouts; monitor WAL, replication lag and lock waits; plan rollback before commit and recovery after commit. No automatic deletion of unmatched target rows.

## 55–60 minutes — Review questions with answers

1. **Why is check-then-insert unsafe?** Concurrent writers can race between SELECT and INSERT.
2. **What enforces SKU uniqueness?** The primary key or unique constraint.
3. **What does `EXCLUDED` mean?** Proposed row values in PostgreSQL ON CONFLICT.
4. **Why use `source_version`?** Reject stale or equal-version updates.
5. **Does `ON CONFLICT` mean ANSI SQL?** No; it is dialect-specific.
6. **Is MERGE identical on all vendors?** No; grammar and concurrency semantics differ.
7. **Why deduplicate a batch?** Avoid multiple updates to one target key and ambiguous winners.
8. **What is the expected final quantity sum?** 31.
9. **Why is an incrementing UPSERT not generally replay-safe?** Retries can double-count.
10. **What evidence precedes a production rollout?** Isolated runtime results, reconciliation, concurrency/retry tests, approvals and rollback/restore plan.

## References

- [PostgreSQL 18 INSERT / ON CONFLICT](https://www.postgresql.org/docs/18/sql-insert.html)
- [PostgreSQL 18 MERGE](https://www.postgresql.org/docs/18/sql-merge.html)
- [PostgreSQL 18 transaction isolation](https://www.postgresql.org/docs/18/transaction-iso.html)
- [PostgreSQL 18 error codes](https://www.postgresql.org/docs/18/errcodes-appendix.html)
- [SQL Server MERGE documentation](https://learn.microsoft.com/en-us/sql/t-sql/statements/merge-transact-sql)

**Next:** [Chapter 037 — RETURNING, OUTPUT, and write verification](../MASTER-TOC.md).

**Validation state:** Authored and targeted static reasoning only. Independent editorial review, comprehensive SQL syntax verification and actual isolated PostgreSQL 18 runtime execution remain pending.
