# Chapter 025 — Foreign Keys and Referential Integrity

> [Master TOC](../MASTER-TOC.md) · [Learning path](../README.md) · [Previous: 024](024-primary-keys-natural-keys-surrogate-keys-and-unique.md) · [Next: 026](../MASTER-TOC.md)
>
> **Part 03 · 60 minutes · PostgreSQL 18 disposable-database lab**
>
> **Validation:** Authored for publication. Independent editorial review, comprehensive syntax verification and isolated PostgreSQL 18 runtime acceptance remain pending.

## Outcomes and schedule (0–5 minutes)

After this lesson you can explain parent and child tables, declare a foreign key, distinguish referential integrity from join correctness, compare delete/update actions, and troubleshoot orphan rows without disabling production constraints. Prerequisites: [021 — modeling](021-entity-relationships-and-conceptual-data-modeling.md), [022 — DDL](022-create-database-create-schema-and-create-table.md), and [024 — keys](024-primary-keys-natural-keys-surrogate-keys-and-unique.md).

| Minutes | Topic |
|---|---|
| 0–5 | Outcomes, prerequisites, safety |
| 5–15 | Parent/child keys, actions and portability |
| 15–30 | Walkthrough and expected results |
| 30–50 | Hands-on isolated lab |
| 50–55 | Troubleshooting and operational checks |
| 55–60 | Review questions and answers |

## Concepts and portable SQL (5–15 minutes)

An **orders** row references one **customers** row; `customers` is the parent, `orders` is the child. A foreign key enforces that each *non-NULL* referenced key exists in the parent. It does not guarantee that an order has a payment, that business data is correct, or that a query join has the intended cardinality.

Portable SQL illustrates the relationship:

```sql
CREATE TABLE customers (
  customer_id INTEGER PRIMARY KEY,
  customer_name VARCHAR(80) NOT NULL
);
CREATE TABLE orders (
  order_id INTEGER PRIMARY KEY,
  customer_id INTEGER NOT NULL,
  CONSTRAINT fk_orders_customer FOREIGN KEY (customer_id)
    REFERENCES customers(customer_id)
);
```

Create the parent before the child. A referenced key normally must be a primary or eligible unique key; matching types and compatible collations matter. `NOT NULL` is separate: without it, a single-column NULL foreign key is permitted. Composite foreign keys have dialect-dependent NULL semantics; PostgreSQL's default `MATCH SIMPLE` does not require a match if any referencing component is NULL, while `MATCH FULL` requires either all components NULL or none.

| Action | Parent row deleted or key updated | Operational consideration |
|---|---|---|
| `NO ACTION` (default) | Reject if child references remain; check may be deferred where supported | Safer default for important history |
| `RESTRICT` | Reject immediately under PostgreSQL semantics | Distinct from deferrable `NO ACTION` |
| `CASCADE` | Delete children or update their key | Potentially large cascading writes |
| `SET NULL` | Clear referencing key | Requires nullable child columns |
| `SET DEFAULT` | Apply default value | Default must still satisfy FK |

Do not use cascade for financial or clinical history without explicit retention and legal review. PostgreSQL supports `DEFERRABLE` constraints and `NOT VALID` / `VALIDATE CONSTRAINT`; these are **PostgreSQL-specific** operational techniques, not portable assumptions. SQL Server, MySQL, SQLite, Snowflake and analytical warehouses vary in enforcement and supported actions; confirm actual engine behavior rather than assuming declared metadata is enforced.

## Walkthrough (15–30 minutes)

In a disposable PostgreSQL 18 database, the companion lab creates two **temporary** tables and inserts three fictional customers and four orders. Orders 101 and 102 belong to customer 1, order 103 to customer 2, and order 104 to customer 3. Expected: **3 customers, 4 orders, 0 orphans**.

```sql
SELECT c.customer_id, c.customer_name, COUNT(o.order_id) AS order_count
FROM ch025_customers AS c
LEFT JOIN ch025_orders AS o ON o.customer_id = c.customer_id
GROUP BY c.customer_id, c.customer_name
ORDER BY c.customer_id;
```

Expected results:

| customer_id | customer_name | order_count |
|---:|---|---:|
| 1 | Fictional Ada | 2 |
| 2 | Fictional Ben | 1 |
| 3 | Fictional Cy | 1 |

The following query detects orphans in *unconstrained* staging data; with a valid, enforced non-null foreign key it should return zero:

```sql
SELECT COUNT(*) AS orphan_count
FROM ch025_orders o
LEFT JOIN ch025_customers c ON c.customer_id = o.customer_id
WHERE c.customer_id IS NULL;
```

Expected: `0`. Note that an inner join would silently hide orphan records and cannot replace this reconciliation check.

A deliberately invalid insert of customer 999 should raise PostgreSQL SQLSTATE `23503` (`foreign_key_violation`). The lab catches **only** that expected error inside a PL/pgSQL exception block and fails if the insert unexpectedly succeeds. An attempted parent delete with referencing orders is likewise rejected. Do not disable triggers or constraints to make tests pass.

## Hands-on lab (30–50 minutes)

Read [025 SQL lab](../labs/025-foreign-keys-referential-integrity.sql) before executing. Only run on a verified **isolated, disposable PostgreSQL 18 primary** named `sql_tutorials`. Database name/version checks are useful safeguards, **not proof of isolation**; independently verify Docker/container identity and credentials. Never point this script at production.

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/025-foreign-keys-referential-integrity.sql
```

Exercises: (1) predict the customer counts; (2) explain why customer 999 is rejected; (3) explain why deleting customer 1 is rejected; (4) count orphans; (5) reason about what `ON DELETE CASCADE` would do, **without executing it**. Expected lab notices: invalid child rejected, referenced parent delete rejected, acceptance assertions passed. The final `ROLLBACK` removes the temporary objects; a failed script should be investigated, not re-run against another environment.

For extra read-only practice, compare `NOT EXISTS` to the left-join orphan check and explain why both should agree on the synthetic dataset. Do not change the supplied acceptance assertions to force a pass.

## Data engineering and DBRE/SRE application (50–55 minutes)

For ETL/ELT, load parent dimensions before dependent fact rows, or stage unmatched references in a quarantine table. Reconcile source and target counts before enforcing a new relationship. A foreign key does **not** automatically create an index on the referencing column in PostgreSQL; assess indexing for parent deletes/updates and common joins. Adding or validating constraints on large tables can acquire locks and scan data. Plan lock timeouts, staged validation, monitoring and rollback with the DBRE team.

| Symptom | Likely cause | Safe response |
|---|---|---|
| `23503` on INSERT | Parent key absent | Inspect source mapping and load order; quarantine synthetic bad row |
| `23503` on DELETE | Referencing child exists | Identify child dependencies; never force a cascade |
| Unexpected NULL child key | FK alone allows NULL | Add a separately reviewed `NOT NULL` requirement |
| Slow parent deletes | Child FK column lacks useful index | Review `EXPLAIN` and indexing in staging |
| FK validation fails | Existing orphan data | Reconcile and repair upstream; do not silently skip validation |
| Lock timeout | Concurrent workload or DDL contention | Stop and reschedule approved migration |

**Acceptance levels:** Authored/published is not independent review. Targeted static inspection is not SQL execution. Runtime-validated requires retained PostgreSQL 18 version, isolated instance identity, invocation, complete output, assertion pass, rollback check and reviewer sign-off.

## Review questions and answers (55–60 minutes)

1. **Does a foreign key prevent all NULLs?** No; use `NOT NULL` for a required single-column reference.
2. **Which side is the parent?** The table containing the referenced candidate/primary key.
3. **What is SQLSTATE 23503?** A foreign-key violation in PostgreSQL.
4. **Why avoid casual CASCADE?** A parent change may modify or remove many child records.
5. **Does PostgreSQL auto-index the child FK?** No; consider a separate index based on workload.
6. **Can an inner join detect missing parents?** No; it hides unmatched child rows.
7. **What is the difference between authored and runtime-validated?** Runtime-validated requires actual isolated execution and retained reproducible evidence.

## References and next

- [PostgreSQL 18 — Foreign Keys and Constraints](https://www.postgresql.org/docs/18/ddl-constraints.html)
- [PostgreSQL 18 — CREATE TABLE](https://www.postgresql.org/docs/18/sql-createtable.html)
- [PostgreSQL 18 — ALTER TABLE](https://www.postgresql.org/docs/18/sql-altertable.html)
- [PostgreSQL 18 — Explicit Locking](https://www.postgresql.org/docs/18/explicit-locking.html)

Next: **026 — NOT NULL, CHECK, DEFAULT, and constraint validation** ([Master TOC](../MASTER-TOC.md)).
