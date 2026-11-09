# 035 — DELETE versus TRUNCATE versus DROP

**Part 04 — Data Modification & Transaction Fundamentals** · **60 minutes** · **PostgreSQL 18 isolated lab**

[Master TOC](../MASTER-TOC.md) · [Previous: 034](034-delete-with-safe-predicates-and-referential-implications.md) · [SQL lab](../labs/035-delete-truncate-drop.sql) · [Status tracker](../STATUS-TRACKER.md)

> **Safety:** These statements can permanently destroy data or schema. Execute the lab only on an independently verified, disposable PostgreSQL 18 instance with synthetic data and nonproduction credentials. The lab uses temporary tables, a version/database guard, timeouts, and ROLLBACK. A database name check alone is not proof of isolation. Never run these examples on production.

## 0–5 minutes — Objectives and prerequisites

By the end you can (1) distinguish row deletion from table truncation and object removal, (2) predict transaction and identity behavior in PostgreSQL, (3) explain foreign-key and dependency constraints, (4) select a safe staging-data lifecycle operation, (5) verify affected objects and rows, and (6) prepare a DBRE/SRE change review. Prerequisites: [CREATE TABLE](../part-03-modeling/022-create-database-create-schema-and-create-table.md), [foreign keys](../part-03-modeling/025-foreign-keys-and-referential-integrity.md), and [safe DELETE](034-delete-with-safe-predicates-and-referential-implications.md).

## 5–15 minutes — Three operations, three scopes

| Statement | Scope | WHERE | Table remains? | PostgreSQL 18 operational detail |
|---|---|---|---|---|
| `DELETE FROM t WHERE ...` | Matching rows | Yes | Yes | Row-level DELETE triggers; creates dead tuples requiring vacuum eventually |
| `DELETE FROM t` | All rows | Optional, omitted here | Yes | Still performs row deletions and DELETE triggers |
| `TRUNCATE TABLE t` | All rows of named table(s) | No | Yes | Takes ACCESS EXCLUSIVE lock; does not fire ON DELETE triggers; fires ON TRUNCATE triggers |
| `DROP TABLE t` | Table object, its data, indexes and constraints | No | No | Dependent objects may prevent drop; CASCADE can remove dependent objects |

**Portable baseline:** `DELETE ... WHERE` is widely supported. `TRUNCATE` and `DROP TABLE` exist in major SQL systems, but their transactional behavior, identity handling, privilege rules, triggers, foreign-key constraints, and implicit commit semantics vary. Never infer cross-dialect behavior from PostgreSQL.

In **PostgreSQL 18**, DELETE, TRUNCATE, and DROP TABLE are transactional: if performed inside a transaction that is rolled back, their effects are undone. This is **not** a universal SQL guarantee; for example, some platforms implicitly commit DDL or TRUNCATE. A committed DROP is not reversed by a later ROLLBACK. Backups and point-in-time recovery are separate procedures requiring rehearsal.

PostgreSQL TRUNCATE is not MVCC-safe for concurrent snapshots: after truncation, a table can appear empty to a transaction using an older snapshot. It acquires ACCESS EXCLUSIVE locks and blocks concurrent reads. DELETE also takes locks and can generate substantial WAL and dead tuples. Neither is automatically the best choice for large retention jobs.

### Identity and referential integrity

PostgreSQL `TRUNCATE ... CONTINUE IDENTITY` (default) preserves sequence positions; `RESTART IDENTITY` restarts owned sequences transactionally. DELETE does not reset identity sequences. DROP removes the table and owned identity sequences. Sequence values consumed by ordinary INSERT are not generally rolled back.

PostgreSQL refuses TRUNCATE of a table referenced by another table's foreign key unless the referencing tables are truncated in the same statement (or CASCADE is specified). **Do not use CASCADE as a shortcut**: it can truncate additional tables. DROP TABLE defaults to RESTRICT for dependencies; DROP ... CASCADE can remove dependent views and foreign-key constraints on other tables. It does not necessarily delete the referencing table itself.

## 15–30 minutes — Worked synthetic data-engineering example

Assume a temporary ingestion staging table `stage_events` contains three synthetic events. A downstream `curated_events` table holds validated records. After a successful, audited reconciliation, the staging table might be emptied for reuse or removed at the end of an isolated test.

**Option A — remove one rejected staging event (portable SQL):**

```sql
SELECT event_id, quality_status
FROM stage_events
WHERE event_id = 'EV-003' AND quality_status = 'rejected';
-- Expected: EV-003 | rejected

DELETE FROM stage_events
WHERE event_id = 'EV-003' AND quality_status = 'rejected';
-- Expected: 1 row affected; 2 rows remain
```

**Option B — empty the entire staging table (PostgreSQL):**

```sql
TRUNCATE TABLE stage_events CONTINUE IDENTITY;
-- Expected: 0 rows; table structure remains
```

**Option C — remove the staging object (portable basic syntax, varying semantics):**

```sql
DROP TABLE stage_events;
-- Expected: table no longer exists
```

Do **not** run these snippets sequentially against shared data. The accompanying isolated lab recreates each example in a controlled transaction, checks table existence and row counts, and rolls back.

### Operational decision guide

Use targeted DELETE when a subset of records must be removed and row-level auditing/trigger semantics matter. Consider TRUNCATE only when the **entire** table is disposable, downstream foreign keys and readers are understood, and an exclusive lock is acceptable. Use DROP when the **table object itself** is no longer needed, after confirming dependencies, ownership, retention, restore evidence, and change approval. For time-partitioned datasets, partition lifecycle operations may be preferable, but require separate planning.

## 30–50 minutes — Hands-on lab

1. Start a disposable PostgreSQL 18 database following [Chapter 003](../part-01-fundamentals/003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md). Independently confirm endpoint, host, port, database, role, and container identity.
2. Review [the SQL lab](../labs/035-delete-truncate-drop.sql) in full. Confirm that it uses only temporary synthetic objects and ends with ROLLBACK.
3. From repository root, run:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials \
  -f sql-tutorials/labs/035-delete-truncate-drop.sql
```

4. Verify acceptance: initial 3 rows; targeted DELETE affects exactly EV-003 leaving 2 rows; TRUNCATE leaves 0 rows while the table exists; DROP removes the temporary table; final assertion displays PASS. The outer transaction rolls back.
5. **Exercise A:** Explain why `DELETE FROM stage_events` without WHERE is unsafe even if it is syntactically valid.
6. **Exercise B:** Predict the effect of `TRUNCATE ... RESTART IDENTITY` on an owned identity sequence and why that differs from DELETE.
7. **Exercise C:** Describe the risk of `TRUNCATE ... CASCADE` on tables with foreign-key dependencies.
8. **Exercise D:** Draft a non-executable retention plan for a synthetic 30-day landing table: owner approval, row counts, dependent consumers, lock budget, restore rehearsal, monitoring, audit log, and abort conditions.

## 50–55 minutes — Validation, troubleshooting, DBRE/SRE safeguards

| Symptom | Explanation | Safe response |
|---|---|---|
| `TRUNCATE` blocked by foreign key | Other tables reference target | Inspect dependencies; never blindly add CASCADE |
| `DROP TABLE` dependency error | View, constraint or other dependent object | Inventory dependents and change plan; avoid CASCADE |
| Lock timeout (`55P03`) | ACCESS EXCLUSIVE lock unavailable | Roll back; identify blockers; reschedule |
| Permission denied (`42501`) | Insufficient privileges | Use approved least-privilege change process |
| Relation does not exist (`42P01`) | Wrong schema/name or already dropped | Verify qualified identifier and environment |
| Unexpected sequence number | Identity state differs from row count | Inspect sequence semantics; never assume gapless IDs |

**Safety checklist:** verify environment out-of-band; use explicit schema and target names; inventory dependent views, foreign keys, triggers, replication and CDC; take baseline counts; confirm data retention/legal holds; estimate lock and WAL impact; obtain approval; set `lock_timeout` and `statement_timeout`; capture results and post-change invariants; use a tested restore path; define rollback versus post-commit recovery; monitor application latency and replicas. TRUNCATE and DROP should never be hidden inside routine cleanup automation without strict eligibility checks and explicit authorization.

## 55–60 minutes — Review questions and answers

1. **Which supports WHERE?** DELETE.
2. **Which keeps the table but removes all rows quickly in PostgreSQL?** TRUNCATE, subject to locks/dependencies.
3. **Which removes the table definition?** DROP TABLE.
4. **Does PostgreSQL TRUNCATE fire DELETE triggers?** No; it fires TRUNCATE triggers where defined.
5. **Does DELETE reset identity sequences?** No.
6. **Can PostgreSQL TRUNCATE be rolled back before COMMIT?** Yes.
7. **Is TRUNCATE rollback portable across databases?** No.
8. **Why avoid CASCADE?** It may affect additional dependent objects or tables.
9. **Can a committed DROP be undone with ROLLBACK?** No.
10. **What is the first operational step?** Verify target/environment and preview dependencies and intended data impact.

## References

- [PostgreSQL 18 DELETE](https://www.postgresql.org/docs/18/sql-delete.html)
- [PostgreSQL 18 TRUNCATE](https://www.postgresql.org/docs/18/sql-truncate.html)
- [PostgreSQL 18 DROP TABLE](https://www.postgresql.org/docs/18/sql-droptable.html)
- [PostgreSQL 18 transaction control](https://www.postgresql.org/docs/18/tutorial-transactions.html)
- [PostgreSQL 18 explicit locking](https://www.postgresql.org/docs/18/explicit-locking.html)

**Next:** Chapter 036 — UPSERT and MERGE patterns across SQL dialects.

**Validation state:** Authored; targeted static reasoning only. Independent editorial review, comprehensive syntax checks, and actual isolated PostgreSQL 18 execution are pending.
