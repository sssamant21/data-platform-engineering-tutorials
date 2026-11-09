# Chapter 023 — Choosing Numeric, Character, Boolean, and Temporal Types

> [Master TOC](../MASTER-TOC.md) · [Learning path](../README.md) · [Previous: 022](022-create-database-create-schema-and-create-table.md) · [Next: 024](../MASTER-TOC.md)
>
> **Part 03 · 60 minutes · PostgreSQL 18 read-only lab**
>
> **Validation:** Authored; targeted static reasoning only. Independent editorial review, comprehensive syntax checks, and actual isolated PostgreSQL 18 runtime execution pending.

## Learning outcomes and schedule (0–5 minutes)

After this chapter you can choose a SQL type from a business requirement, distinguish exact from approximate arithmetic, select bounded versus unbounded text, model three-state booleans, choose date/time types and avoid timezone ambiguity, and detect unsafe casts before migrations. Prerequisite: [Chapter 022](022-create-database-create-schema-and-create-table.md).

| Minutes | Exercise |
|---|---|
| 0–5 | Outcomes, safety and prerequisites |
| 5–15 | Type families and portability |
| 15–30 | Worked retail/operational examples |
| 30–50 | Read-only PostgreSQL 18 lab |
| 50–55 | Troubleshooting and acceptance |
| 55–60 | Questions and answers |

## Type selection principles (5–15 minutes)

A **type** constrains valid values, arithmetic, storage and comparison semantics. Choose based on domain, precision, range, units, timezone and expected evolution—not just apparent sample values. A nullable column is not the same as a Boolean false or an empty string. Define constraints separately (Chapter 026).

| Requirement | Portable-first choice | PostgreSQL 18 notes / caveats |
|---|---|---|
| Counts, IDs within signed 32-bit range | `INTEGER` | `BIGINT` for larger counters; IDs are identifiers, not quantities |
| Currency-like exact amount | `DECIMAL(12,2)` / `NUMERIC(12,2)` | Exact decimal; specify precision and scale; choose larger range when needed |
| Approximate scientific measurement | `DOUBLE PRECISION` | Binary floating point; do not use for exact financial reconciliation |
| Short bounded code | `VARCHAR(20)` | Length is characters, not necessarily bytes; validate business format separately |
| Description | `VARCHAR(n)` or implementation-specific large text | PostgreSQL `TEXT` is unbounded and commonly preferred when no domain limit |
| Yes/no/unknown | `BOOLEAN` | PostgreSQL literals `TRUE`, `FALSE`; `NULL` means unknown/not supplied |
| Calendar day | `DATE` | Does not carry a timezone or time-of-day |
| Local wall-clock appointment | `TIMESTAMP WITHOUT TIME ZONE` | Interpret only with an explicitly documented location/timezone |
| Instant/event timestamp | Vendor-specific timezone-aware timestamp | PostgreSQL `TIMESTAMPTZ` stores an instant, displayed in session timezone; does not preserve original zone name |

**Portability:** SQL-standard `DECIMAL`, `INTEGER`, `CHARACTER VARYING`, `DATE`, and `BOOLEAN` are common, but vendor implementations vary. SQL Server uses `BIT` rather than a native `BOOLEAN` column; MySQL `BOOLEAN` aliases `TINYINT(1)`; Oracle SQL Boolean column support depends on version. SQL Server `DATETIMEOFFSET`, Snowflake timestamp variants and BigQuery `TIMESTAMP`/`DATETIME` have different semantics. PostgreSQL `TIMESTAMPTZ` is an alias for `TIMESTAMP WITH TIME ZONE` but **does not store the original time zone**.

## Worked examples (15–30 minutes)

Imagine a synthetic order event with `order_id=9001`, `order_amount=19.95`, `is_paid=true`, and event time `2026-11-01 14:30:00+00`. Use `BIGINT` for potentially large order identifiers, `NUMERIC(12,2)` for amount, `BOOLEAN` for payment state, and `TIMESTAMPTZ` for the event instant. If a customer selects a shipping *day*, store `DATE`, not a timestamp set to midnight.

```sql
-- PostgreSQL 18; SELECT-only synthetic example
SELECT 9001::bigint AS order_id,
       19.95::numeric(12,2) AS amount_usd,
       TRUE::boolean AS is_paid,
       DATE '2026-11-02' AS ship_date,
       TIMESTAMPTZ '2026-11-01 14:30:00+00' AS occurred_at;
-- Expected: 9001 | 19.95 | true | 2026-11-02 | same UTC instant
```

**Exact vs approximate:** `0.1::numeric + 0.2::numeric = 0.3::numeric` is true. Binary `double precision` cannot represent most decimal fractions exactly; never compare floating values for financial equality without a carefully defined tolerance, and never silently convert monetary amounts to floating point.

**Timezones:** A PostgreSQL `TIMESTAMP WITHOUT TIME ZONE` represents local calendar date/time without an offset. A `TIMESTAMPTZ` represents an instant. `SET TIME ZONE` changes its display, not the instant. For audit trails and distributed pipelines, normalize to UTC and retain the source timezone identifier separately if future reconstruction of local civil time is required. Daylight-saving transitions can make local times ambiguous or nonexistent.

**Text and identifiers:** `VARCHAR(12)` can enforce a maximum character count, but `VARCHAR` does not enforce business patterns. Preserve leading zeros in postal codes and account-like external identifiers by storing them as text; do not use integer arithmetic on them. Avoid `CHAR(n)` padding surprises unless fixed-width semantics are intentional.

**Casting:** `CAST('19.95' AS NUMERIC(12,2))` is broadly portable; PostgreSQL `'19.95'::numeric(12,2)` is dialect-specific. Invalid casts error. Narrowing precision may round or overflow; a schema migration needs data profiling and an approved rollback plan.

## Hands-on lab (30–50 minutes)

Use [023 SQL lab](../labs/023-choosing-sql-data-types.sql) on an **independently verified disposable PostgreSQL 18 database named `sql_tutorials`**. No production credentials, customer data, or persistent objects. From repository root:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/023-choosing-sql-data-types.sql
```

The script begins a read-only transaction, verifies PostgreSQL major version and database identity, creates a six-row **in-query synthetic** dataset using `VALUES`, checks type-specific behavior and raises an error on unexpected results. It ends with `ROLLBACK`. Database name/version checks are **not proof of isolation**: independently verify host, cluster ownership, credentials and network destination before running.

**Practice tasks:** (1) Identify why order amounts are numeric, not double precision. (2) Count missing payment states using `IS NULL`, not `= FALSE`. (3) Show the same instant in UTC and New York without changing the underlying event. (4) Explain why `'00123'` must remain text for a postal code. (5) Decide whether a local appointment needs a zone identifier alongside wall-clock time.

Expected aggregate for the synthetic dataset: **6 events; 4 known paid/unpaid states and 2 unknown; amount total 91.45; 2 events with missing payment state**. The lab asserts these figures; do not treat expected results as runtime evidence until executed.

## Troubleshooting, safety, and acceptance (50–55 minutes)

| Symptom | Likely cause | Safe action |
|---|---|---|
| `numeric field overflow` | Precision/scale insufficient | Profile max values in sandbox; redesign type, do not truncate |
| Amount differs after cast | Binary floating conversion or rounding | Keep exact decimal end-to-end |
| Timestamp displays differently | Session timezone | Inspect `SHOW TIME ZONE`; compare UTC instants |
| Invalid input syntax | Bad source string for target type | Quarantine/validate source in staging |
| Unexpected NULL count | Unknown conflated with false | Use `IS NULL` and explicit tri-state rules |
| `permission denied` | Wrong database/role | Stop; use approved isolated lab credentials, not elevated production access |

**DBRE/SRE guardrails:** Type changes can rewrite large tables, hold locks, change index behavior, break consumers and invalidate replication/CDC assumptions. Before a real migration, profile data distributions, review application contracts, estimate lock/space/time impact, test on a restored isolated dataset, define backout and monitor replication lag. Never execute DDL from this chapter on production.

**Acceptance states:** Authored/published is a GitHub content state; targeted static inspection is not full syntax certification; independent editorial review is separate; PostgreSQL 18 runtime acceptance requires executing this exact script on an isolated PostgreSQL 18 instance, retaining version, command, output, assertions, cleanup and operator evidence. No such runtime evidence is claimed here.

## Review questions with answers (55–60 minutes)

1. **Why `NUMERIC(12,2)` instead of `DOUBLE PRECISION` for prices?** Exact decimal representation and predictable scale for reconciliation.
2. **Can `BOOLEAN` contain three logical states?** With nullable columns, TRUE, FALSE and NULL (unknown).
3. **Does PostgreSQL `TIMESTAMPTZ` retain the named source timezone?** No; retain it in another column if needed.
4. **Why store a postal code as text?** Leading zeros and formatting are meaningful; arithmetic is not.
5. **What is the risk of `VARCHAR(8)` for growing external IDs?** Valid future values may be rejected.
6. **What proves this lab ran successfully?** Recorded isolated PostgreSQL 18 execution with passing assertions and retained evidence, not a published SQL file.

## References and next

- [PostgreSQL 18 Data Types](https://www.postgresql.org/docs/18/datatype.html)
- [PostgreSQL 18 Numeric Types](https://www.postgresql.org/docs/18/datatype-numeric.html)
- [PostgreSQL 18 Character Types](https://www.postgresql.org/docs/18/datatype-character.html)
- [PostgreSQL 18 Date/Time Types](https://www.postgresql.org/docs/18/datatype-datetime.html)
- [PostgreSQL 18 Type Conversion](https://www.postgresql.org/docs/18/typeconv.html)
- Next: **024 — Primary keys, natural keys, surrogate keys, and UNIQUE** ([Master TOC](../MASTER-TOC.md)).
