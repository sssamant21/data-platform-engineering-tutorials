# Chapter 026 — NOT NULL, CHECK, DEFAULT, and Constraint Validation

> [Master TOC](../MASTER-TOC.md) · [Learning path](../README.md) · [Previous: 025](025-foreign-keys-and-referential-integrity.md) · [Next: 027](../MASTER-TOC.md)
>
> **Part 03 · 60 minutes · PostgreSQL 18 isolated lab**
>
> **Status:** Authored; targeted static inspection planned. Independent editorial review, comprehensive SQL syntax checks and actual PostgreSQL 18 runtime acceptance pending.

## Objectives and schedule (0–5 minutes)

By the end, distinguish mandatory fields from allowed values, design `NOT NULL`, `CHECK` and `DEFAULT` constraints, predict three-valued CHECK behavior, identify existing bad data, and plan safe constraint rollout. Prerequisites: [022 — DDL](022-create-database-create-schema-and-create-table.md), [023 — data types](023-choosing-numeric-character-boolean-and-temporal-types.md), and [025 — foreign keys](025-foreign-keys-and-referential-integrity.md).

| Time | Activity |
|---|---|
| 0–5 min | Goals, lab isolation and prerequisites |
| 5–15 min | Concepts and portable SQL |
| 15–30 min | Synthetic examples and expected outputs |
| 30–50 min | Isolated PostgreSQL 18 lab and exercises |
| 50–55 min | Troubleshooting, validation and rollout safety |
| 55–60 min | Review questions and answers |

## Concepts and syntax (5–15 minutes)

- **NOT NULL:** a column must have a non-NULL value. An empty string is not NULL in PostgreSQL; Oracle treats empty character strings differently.
- **CHECK:** a Boolean expression must not evaluate to **FALSE**. Both TRUE and UNKNOWN (NULL) satisfy a CHECK in PostgreSQL. Combine with NOT NULL when absence is prohibited.
- **DEFAULT:** supplies a value when an INSERT omits the column or explicitly requests `DEFAULT`; explicitly inserting NULL does **not** invoke the default. Defaults are not retroactive data-cleaning rules.
- **Constraint validation:** distinguish checking newly written rows from validating pre-existing rows during migration. A constraint is not a substitute for upstream data-quality monitoring.

Portable-style illustrative SQL (run only in a disposable database):

```sql
CREATE TABLE job_runs (
  run_id INTEGER PRIMARY KEY,
  service_name VARCHAR(40) NOT NULL,
  status VARCHAR(12) DEFAULT 'queued' NOT NULL,
  attempts INTEGER DEFAULT 0 NOT NULL,
  CONSTRAINT ck_attempts CHECK (attempts >= 0),
  CONSTRAINT ck_status CHECK (status IN ('queued','running','done','failed'))
);
```

The core syntax is broadly portable, but constraint names, default expressions, online validation, error codes, and ALTER TABLE behavior vary across PostgreSQL, SQL Server, MySQL, Oracle, Snowflake and BigQuery. Do not assume analytical warehouses enforce every declared constraint.

## Walkthrough and expected results (15–30 minutes)

Imagine a synthetic operational ingestion table with three runs:

| run_id | service_name | status | attempts |
|---:|---|---|---:|
| 101 | ingest-a | queued | 0 |
| 102 | ingest-b | running | 2 |
| 103 | ingest-c | done | 1 |

The companion lab inserts row 101 without `status` or `attempts`: defaults produce `queued` and `0`. Row 102 supplies both explicitly; row 103 supplies a different valid status. Expected total: **3 rows**, **1 queued**, **3 total attempts**.

```sql
SELECT status, COUNT(*) AS run_count
FROM ch026_runs
GROUP BY status
ORDER BY status;
```

Expected: `done = 1`, `queued = 1`, `running = 1`. Invalid examples are deliberately attempted inside exception handlers in the lab: NULL service name produces PostgreSQL SQLSTATE **23502**, negative attempts produces **23514**, and an unrecognized status produces **23514**. Explicit NULL status produces **23502**, not the default.

**Important NULL trap:** `CHECK (attempts >= 0)` alone allows NULL because the predicate becomes UNKNOWN. Here `attempts NOT NULL` closes that gap. For an optional nonnegative value, allowing NULL may instead be intentional.

## Hands-on lab (30–50 minutes)

Open [026 SQL lab](../labs/026-not-null-check-default-validation.sql) and inspect every statement before running. The SQL creates temporary objects and rolls back, but **only run it against an independently verified disposable PostgreSQL 18 primary database named `sql_tutorials`**. The version/name guard cannot prove isolation. Never use production credentials or endpoints.

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/026-not-null-check-default-validation.sql
```

Exercises:

1. Predict the defaulted values for row 101; verify the SELECT output.
2. Predict each invalid insert's SQLSTATE before reading the notices.
3. Explain why `CHECK (attempts >= 0)` does not alone reject NULL.
4. Use the included read-only staging CTE to find invalid legacy rows before migration.
5. Explain why an added constraint should be validated in staging before an approved production rollout.

The staging CTE contains five synthetic legacy rows: two valid and three invalid (missing service, negative attempts, invalid status). Expected `invalid_rows = 3`. The acceptance block checks exact totals and counts and raises an exception if unexpected.

## Data engineering and DBRE/SRE operations (50–55 minutes)

For incoming files, reject or quarantine malformed records before writing curated tables. Distinguish **schema defaults** from **source-system semantics**: defaulting a missing status to `queued` may be wrong for historical replay. Reconcile input counts, accepted rows, and rejected rows.

PostgreSQL-specific migration pattern (illustration only; **do not run against production**):

```sql
-- After assessing existing rows, locks, write path, and rollback:
ALTER TABLE job_runs
  ADD CONSTRAINT ck_attempts_new CHECK (attempts >= 0) NOT VALID;
-- New/updated rows are checked; old rows are not yet scanned.
-- After repairing old violations in an approved change:
ALTER TABLE job_runs VALIDATE CONSTRAINT ck_attempts_new;
```

`NOT VALID` is supported for PostgreSQL CHECK and foreign-key constraints, not as a blanket option for every constraint. Adding `NOT NULL` to a populated table requires separate analysis of existing NULLs and lock behavior. Validation still consumes I/O and takes locks; plan timeouts, monitoring, and a rollback strategy. Never remove constraints merely to make a pipeline green.

| Symptom | Cause | Safe next action |
|---|---|---|
| `23502` | Required column received NULL | Check omitted versus explicit NULL and upstream mapping |
| `23514` | CHECK expression evaluated FALSE | Inspect offending synthetic value and rule |
| NULL unexpectedly accepted by CHECK | UNKNOWN passes CHECK | Add NOT NULL if absence is disallowed |
| Default not applied | Explicit NULL or nonmatching insert behavior | Inspect INSERT column list |
| Constraint validation fails | Existing rows violate rule | Stage reconciliation, repair, then revalidate |
| Migration blocks writes | DDL lock contention | Stop; evaluate locks and approved maintenance plan |

## Review questions and answers (55–60 minutes)

1. **Does DEFAULT prevent NULL?** No. Add NOT NULL where required.
2. **Does CHECK reject UNKNOWN?** No; in PostgreSQL, FALSE is rejected, UNKNOWN is accepted.
3. **What does SQLSTATE 23514 mean?** A CHECK constraint violation.
4. **Why validate existing rows?** New-write enforcement does not prove historical data quality.
5. **Can NOT VALID be used on every constraint?** No; PostgreSQL supports it for selected constraint types such as CHECK and FK.
6. **Why not execute this lab in production?** It deliberately tests invalid writes and creates temporary DDL; the isolated environment is part of its safety design.
7. **What is needed for runtime acceptance?** PostgreSQL 18 execution on an isolated instance, complete output, passing assertions, cleanup verification and retained evidence.

## References and next

- [PostgreSQL 18 — Constraints](https://www.postgresql.org/docs/18/ddl-constraints.html)
- [PostgreSQL 18 — Default Values](https://www.postgresql.org/docs/18/ddl-default.html)
- [PostgreSQL 18 — ALTER TABLE](https://www.postgresql.org/docs/18/sql-altertable.html)
- [PostgreSQL 18 — Error Codes](https://www.postgresql.org/docs/18/errcodes-appendix.html)

Next: **027 — Identity columns, sequences, and generated values** ([Master TOC](../MASTER-TOC.md)).
