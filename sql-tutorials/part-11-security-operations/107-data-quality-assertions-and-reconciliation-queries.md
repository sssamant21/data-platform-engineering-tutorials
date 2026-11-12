# 107 — Data Quality Assertions and Reconciliation Queries

**Part 11 — Security, Data Quality & DBRE/SRE Operations** · **60 minutes** · PostgreSQL 18 lab · Beginner-friendly

[Master TOC](../MASTER-TOC.md) · [Tutorial index](../README.md) · [Lab 107 SQL](../labs/107-data-quality-assertions-reconciliation.sql) · [Previous: 106](106-backward-compatible-migrations-and-deployment-controls.md) · Next: 108 — Backup, recovery, and restore-validation concepts (planned)

## 1. Outcomes, prerequisites, and scenario (0–5 minutes)

By the end, you can define dataset grain, validate uniqueness and required fields, detect orphaned references, reconcile source-to-target counts and amounts, compare row-level multisets, interpret exceptions, and design fail-closed deployment gates. Read [constraints (026)](../part-03-modeling/026-not-null-check-default-and-constraint-validation.md), [joins (041)](../part-05-joins/041-join-fundamentals-and-relationship-cardinality.md), and [migration controls (106)](106-backward-compatible-migrations-and-deployment-controls.md).

**Scenario:** A synthetic retail ingestion pipeline receives order records and a downstream reporting table. We must decide whether a batch can be promoted. Quality checks are *business assertions*, not just SQL syntax checks. Never use real customer, patient, or production data in this exercise.

## 2. Quality dimensions and the contract (5–15 minutes)

| Dimension | Example invariant | Operational consequence |
|---|---|---|
| Completeness | order ID, customer ID, amount, status present | Missing data blocks joins or reconciliation |
| Uniqueness | one source record per (batch_id, order_id) | Duplicates inflate metrics |
| Validity | amount >= 0; status in approved vocabulary | Invalid rows poison downstream calculations |
| Referential integrity | every customer ID maps to a known customer | Orphaned orders cannot be attributed |
| Consistency | source and target represent the same business grain | Mismatched aggregates hide lost/duplicated rows |
| Freshness | batch timestamp within agreed SLA | Stale reporting creates incorrect decisions |

Define **grain** first: one row per order in each snapshot. A count equality is necessary but not sufficient: one missing row plus one duplicated row can preserve the count. A total-amount equality is also insufficient when two wrong amounts offset. Use independent controls, not one aggregate.

**Portable SQL:** `COUNT`, `SUM`, `CASE`, `GROUP BY`, `HAVING`, `LEFT JOIN`, and `NOT EXISTS` are broadly portable. `EXCEPT ALL`, `FILTER`, `IS DISTINCT FROM`, PostgreSQL `DO` blocks, and `SET LOCAL` have dialect-specific availability or syntax. For portability, compare keys with `NOT EXISTS` and NULL-aware equality, but preserve duplicate multiplicity separately.

## 3. Worked examples: build an evidence-based gate (15–30 minutes)

Use the synthetic snapshots in the [lab](../labs/107-data-quality-assertions-reconciliation.sql): source orders 101–104 with amounts 40, 30, 20, 10; target orders 101–104 with amounts 40, 30, 25, 5. Both contain four rows and sum to 100, **but two amounts differ**. A separate candidate feed includes duplicate order 103, NULL customer ID, negative amount, and orphan customer 99. The candidate feed is intentionally dirty; the source/target snapshots are intentionally distinct examples.

### A. Detect duplicate business keys

```sql
SELECT order_id, COUNT(*) AS occurrences
FROM candidate_orders
GROUP BY order_id
HAVING COUNT(*) > 1;
-- Expected: order_id 103, occurrences 2
```

### B. Validate required fields and domain values

```sql
SELECT COUNT(*) AS invalid_rows
FROM candidate_orders
WHERE order_id IS NULL OR customer_id IS NULL
   OR amount IS NULL OR amount < 0
   OR status NOT IN ('paid', 'pending') OR status IS NULL;
-- Expected: 2 rows (the NULL-customer and negative-amount records)
```

### C. Find orphaned foreign keys without mutating data

```sql
SELECT o.order_id
FROM candidate_orders AS o
WHERE o.customer_id IS NOT NULL
  AND NOT EXISTS (
    SELECT 1 FROM customers AS c WHERE c.customer_id = o.customer_id
  );
-- Expected: 105 (customer 99 does not exist)
```

### D. Reconcile exact rows, not only totals

```sql
-- PostgreSQL 18; the lab defines source_orders and target_orders CTEs.
(SELECT * FROM source_orders EXCEPT ALL SELECT * FROM target_orders)
UNION ALL
(SELECT * FROM target_orders EXCEPT ALL SELECT * FROM source_orders);
-- Expected: four directional differences, not zero.
```

The `EXCEPT ALL` comparison is **multiset-sensitive**: it detects duplicate counts as well as values. For production, compare stable keys, normalized types, and explicit columns, not `SELECT *` across evolving schemas. Compare in a consistent snapshot or a clearly defined watermark; otherwise concurrent ingestion can create false positives.

### E. Decide whether to promote

A pipeline gate should fail when any **blocking** assertion is nonzero. Distinguish warnings (late-arriving records within an agreed grace period) from blockers (duplicate keys, lost rows, invalid financial amounts). Publish exception counts and sample IDs to a restricted evidence store; avoid exposing sensitive row contents.

## 4. Hands-on lab (30–50 minutes)

Run from the repository root against a disposable PostgreSQL 18 database called `sql_tutorials`, using a nonproduction, least-privilege account:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials \
  -f sql-tutorials/labs/107-data-quality-assertions-reconciliation.sql
```

The [read-only SQL lab](../labs/107-data-quality-assertions-reconciliation.sql) uses inline `VALUES`, guards for database and server major version, transaction-local timeouts, a deterministic two-way `EXCEPT ALL` assertion, and `ROLLBACK`. It neither creates persistent tables nor changes application data.

**Expected (calculated, not observed):** candidate rows 6; duplicate-key groups 1; invalid rows 2; orphan rows 1; source and target each 4 rows and 100.00 total; source-only differences 2; target-only differences 2; exact-match gate **FAIL**. The SQL assertion confirms this *expected failing quality gate* and exits successfully when the modeled results match; successful lab execution must not be confused with approval to promote the dirty batch.

Practice: (1) identify both amount mismatches; (2) explain why equal totals fail to prove equality; (3) decide which exceptions block promotion; (4) design a batch_id + source watermark; (5) describe how to distinguish a late arrival from a missing row; (6) propose a reconciliation evidence record containing batch ID, query revision, timestamp, row counts, sums, mismatch counts, reviewer, and decision.

## 5. Troubleshooting, controls, and validation (50–55 minutes)

| Symptom | Likely cause | Safe response |
|---|---|---|
| Counts equal but values differ | Compensating changes or duplicated/missing rows | Compare keyed rows and multisets |
| Orphan count unexpectedly high | Dimension load lag or wrong join key | Check dependency order and watermark |
| Duplicate count rises | Retry without idempotency or wrong grain | Quarantine batch; fix deduplication contract |
| Reconciliation drifts during run | Source and target captured at different times | Use stable batch boundaries or consistent snapshot |
| Query times out | Large scans, skew, or inadequate indexing | Run bounded diagnostics; review plan and capacity |
| NULL comparisons miss changes | `NULL = NULL` yields unknown | Use explicit NULL-safe comparison rules |

**Guardrails:** Read-only checks can still consume I/O, CPU, and locks; schedule and bound production diagnostics through change control. Never run large `EXCEPT ALL` operations on production without an approved resource budget. Do not disable constraints to make a batch pass. Reconciliation does not replace backups, restore tests, CDC replay verification, or application sign-off. The lab contains no real access control or data-quality enforcement.

**Validation status:** Authored and manually reasoned; independent editorial review, comprehensive parser/link QA, and actual isolated PostgreSQL 18 execution with retained evidence are pending.

## 6. Review questions and answers (55–60 minutes)

1. **Why define grain?** It determines the uniqueness key and meaning of a count.
2. **Does equal row count prove equality?** No; missing and duplicate rows can cancel.
3. **Does equal SUM prove equality?** No; compensating amount errors can cancel.
4. **What is an orphan?** A reference to a parent key absent from the approved parent set.
5. **Why use `EXCEPT ALL`?** It preserves duplicate multiplicity when comparing row sets.
6. **Why check NULL explicitly?** Ordinary equality does not return true for two NULLs.
7. **What should a promotion gate do on blocking exceptions?** Fail closed, retain evidence, and request an authorized decision.
8. **What comes next?** Chapter 108 — Backup, recovery, and restore-validation concepts.

## References

- [PostgreSQL 18 — SELECT, including set operations](https://www.postgresql.org/docs/18/sql-select.html)
- [PostgreSQL 18 — Aggregate Functions](https://www.postgresql.org/docs/18/functions-aggregate.html)
- [PostgreSQL 18 — Comparison Functions and Operators](https://www.postgresql.org/docs/18/functions-comparison.html)
- [PostgreSQL 18 — Transaction Isolation](https://www.postgresql.org/docs/18/transaction-iso.html)
- [PostgreSQL 18 — Constraints](https://www.postgresql.org/docs/18/ddl-constraints.html)
