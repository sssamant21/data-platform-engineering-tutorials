# Chapter 024 — Primary Keys, Natural Keys, Surrogate Keys, and UNIQUE

> [Master TOC](../MASTER-TOC.md) · [Learning path](../README.md) · [Previous: 023](023-choosing-numeric-character-boolean-and-temporal-types.md) · [Next: 025](../MASTER-TOC.md)
>
> **Part 03 · 60 minutes · PostgreSQL 18 isolated rollback-only lab**
>
> **Validation:** Authored; targeted static reasoning pending publication. Independent editorial review, comprehensive syntax checking, and actual PostgreSQL 18 runtime execution pending.

## Outcomes and agenda (0–5 minutes)

By the end, distinguish a primary key from a candidate key, choose natural versus surrogate identifiers, explain composite keys and UNIQUE constraints, and recognize NULL and concurrency pitfalls. Prerequisites: [Chapter 021](021-entity-relationships-and-conceptual-data-modeling.md), [Chapter 022](022-create-database-create-schema-and-create-table.md), and [Chapter 023](023-choosing-numeric-character-boolean-and-temporal-types.md).

| Time | Activity |
|---|---|
| 0–5 min | Outcomes, safety and prerequisites |
| 5–15 min | Key concepts and portability |
| 15–30 min | Worked data engineering examples |
| 30–50 min | Isolated PostgreSQL 18 lab |
| 50–55 min | Troubleshooting, acceptance and operations |
| 55–60 min | Review questions and answers |

## Concepts and syntax (5–15 minutes)

A **superkey** identifies rows uniquely; a **candidate key** is a minimal superkey; the selected candidate key is the **primary key**. Other candidate keys can be enforced with `UNIQUE` and appropriate `NOT NULL` constraints. A primary key cannot contain NULL and there is at most one primary-key constraint per table, though it may span multiple columns. `UNIQUE` does not necessarily imply `NOT NULL`.

A **natural key** comes from a domain (for example, a vendor-scoped external order code); a **surrogate key** is generated independently (for example, `order_id BIGINT GENERATED ... AS IDENTITY`). A natural key is useful for deduplication but may change, be reused, contain personal information, or be unique only within a tenant. Surrogate keys are stable join identifiers, but do **not** replace enforcement of business uniqueness.

Portable SQL-style definitions:

```sql
CREATE TABLE customer (
    customer_id BIGINT PRIMARY KEY,
    external_code VARCHAR(30) NOT NULL UNIQUE
);
CREATE TABLE order_line (
    order_id BIGINT NOT NULL,
    line_no INTEGER NOT NULL,
    sku VARCHAR(30) NOT NULL,
    PRIMARY KEY (order_id, line_no)
);
```

These statements illustrate constraints, not a production migration. PostgreSQL 18, SQL Server, MySQL and other systems differ in generated identifiers, index implementation, collations, NULL uniqueness and constraint deferral. PostgreSQL automatically creates a unique B-tree index for primary-key and UNIQUE constraints. A foreign key is a separate relationship rule, covered in Chapter 025.

**NULL semantics:** PostgreSQL's ordinary `UNIQUE (email)` permits multiple NULLs; PostgreSQL 15+ supports `UNIQUE NULLS NOT DISTINCT (email)` to treat NULLs as equal for uniqueness. Do not assume identical behavior across vendors. PostgreSQL's case-sensitive text equality may allow `Alice@example.test` and `alice@example.test` as distinct values; normalize and enforce a documented business rule, using an appropriate collation or expression index after review.

## Worked examples (15–30 minutes)

Consider synthetic multi-tenant retail ingestion. The incoming external order reference `A-100` may occur in tenant `T1` and `T2`. Thus `external_ref` alone is **not** a valid key; `(tenant_code, external_ref)` is a candidate business key. A generated `order_id` can be the primary key for joins, while `UNIQUE (tenant_code, external_ref)` protects against duplicate ingestion.

```sql
-- Illustrative PostgreSQL 18 DDL; execute only in an approved disposable database.
CREATE TABLE retail_order (
    order_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_code TEXT NOT NULL,
    external_ref TEXT NOT NULL,
    amount_usd NUMERIC(12,2) NOT NULL,
    CONSTRAINT uq_tenant_external_ref UNIQUE (tenant_code, external_ref)
);
```

**Expected:** `(T1,A-100)` and `(T2,A-100)` coexist; a second `(T1,A-100)` is rejected with SQLSTATE `23505`. The identity value is not guaranteed to be gapless, and rollback or failed inserts may consume sequence values. Never use ID gaps to infer deleted rows.

**Data engineering:** Source duplicates should be profiled before loading. A surrogate primary key alone does not stop duplicate business events. In distributed pipelines, agree on event identity, tenant scope, retry/idempotency semantics, and late-arriving corrections. `SELECT NOT EXISTS (...)` followed by `INSERT` is race-prone under concurrency; rely on a declared uniqueness constraint and an explicit conflict-handling policy.

**DBRE/SRE:** Adding a unique constraint to an existing large table may fail on duplicates and may require expensive scanning, locking, disk space and index builds. Profile candidate keys first; plan concurrent index creation and constraint attachment only where supported and operationally appropriate, with tested rollback, replication monitoring and a maintenance/change plan. Never casually remove constraints to make ingestion succeed.

## Hands-on lab (30–50 minutes)

Use [Chapter 024 SQL lab](../labs/024-primary-natural-surrogate-unique.sql). It creates **temporary tables only**, inside a transaction that ends in `ROLLBACK`. It does not alter persistent objects. Independently confirm an isolated PostgreSQL 18 primary database named `sql_tutorials`; database-name/version checks alone do not establish isolation. Never use production credentials.

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/024-primary-natural-surrogate-unique.sql
```

Lab tasks: (1) inspect a composite candidate key; (2) see an identity-backed primary key; (3) count records and unique business keys; (4) verify a duplicate is rejected without aborting the entire exercise using a guarded PL/pgSQL exception block; (5) verify PostgreSQL's default multiple-NULL behavior in a UNIQUE column; (6) verify cleanup via rollback. Expected before rollback: **3 orders**, **2 distinct tenants**, **3 distinct tenant/reference combinations**, **2 NULL contact emails**, and **one deliberate duplicate rejected with SQLSTATE 23505**. The lab includes fail-closed assertions for these results.

For practice, explain whether a patient medical record number is globally unique, hospital-scoped, or changeable; use fictional identifiers only. Then propose a stable surrogate identifier plus the appropriate scoped uniqueness constraint, rather than treating an unverified external field as globally unique.

## Troubleshooting, safety and acceptance (50–55 minutes)

| Symptom | Likely cause | Safe response |
|---|---|---|
| `duplicate key value violates unique constraint` (`23505`) | Existing business key repeated | Quarantine/reconcile synthetic source; never drop the constraint reflexively |
| `null value in column ... violates not-null constraint` (`23502`) | Missing primary-key or required natural-key component | Fix input validation upstream |
| Two seemingly identical emails coexist | Case/collation/normalization differences | Document canonicalization and test collisions |
| Identity values skip | Sequence allocations are not transactional | Do not infer missing rows or reset sequence in production |
| Constraint addition blocks writes | Table scan/index build/lock acquisition | Use staged migration and approved downtime/online strategy |
| `permission denied` | Wrong role or environment | Stop; verify disposable lab identity; never elevate production privileges |

**Safety:** The lab uses transaction-local timeouts, temporary tables, synthetic data, a version/database guard, explicit assertions, and `ROLLBACK`. Temporary objects can still consume resources and locks; do not execute on shared or production systems. The exception handler checks the exact duplicate-key SQLSTATE so unrelated failures do not masquerade as success.

**Acceptance distinction:** Published = files exist on GitHub. Targeted static review = inspection, not execution. Independent editorial review requires separate review evidence. PostgreSQL 18 runtime validation requires an isolated PG18 instance, exact command, captured server version and identity, complete output, passing assertions, rollback verification and retained evidence. Until then runtime validation is **pending**.

## Review questions and answers (55–60 minutes)

1. **What is the difference between PRIMARY KEY and UNIQUE?** A table has at most one primary-key constraint, its columns are non-NULL; multiple UNIQUE constraints are possible and NULL behavior depends on dialect.
2. **Why keep a business UNIQUE constraint when using an identity primary key?** The identity distinguishes rows but does not prevent duplicate source business events.
3. **What makes `(tenant_code, external_ref)` better than `external_ref` alone?** The reference is unique only within a tenant.
4. **Are identity numbers gapless?** No; allocations can be consumed by failures and rollbacks.
5. **Do two NULL values violate ordinary PostgreSQL UNIQUE?** No, unless `NULLS NOT DISTINCT` is specified.
6. **Can an application SELECT pre-check replace a unique constraint?** No; concurrent writers can race.
7. **What proves the lab was runtime-validated?** Retained, reproducible isolated PostgreSQL 18 execution evidence with passing assertions.

## References and next

- [PostgreSQL 18 — Constraints](https://www.postgresql.org/docs/18/ddl-constraints.html)
- [PostgreSQL 18 — Identity Columns](https://www.postgresql.org/docs/18/ddl-identity-columns.html)
- [PostgreSQL 18 — CREATE TABLE](https://www.postgresql.org/docs/18/sql-createtable.html)
- [PostgreSQL 18 — Unique Indexes](https://www.postgresql.org/docs/18/indexes-unique.html)
- Next: **025 — Foreign keys and referential integrity** ([Master TOC](../MASTER-TOC.md)).
