# SQL Tutorials — Beginner to Advanced

**Audience:** Analysts, application developers, data engineers, DBREs, and SREs  
**Curriculum:** 12 parts, 120 chapters, approximately 60 minutes per chapter  
**Primary lab target:** PostgreSQL 18. Dialect-specific features are labeled, with comparisons to other SQL platforms where useful.

[MASTER-TOC.md](MASTER-TOC.md) · [STATUS-TRACKER.md](STATUS-TRACKER.md)

## Start here

1. [001 — Introduction to SQL: purpose, use cases, and stakeholder roles](part-01-fundamentals/001-introduction-to-sql.md) — published; runtime testing pending.
2. [002 — Relational databases and DBMS architecture](part-01-fundamentals/002-relational-databases-and-dbms-architecture.md) — published; runtime testing pending.
3. [003 — Set up the SQL lab: PostgreSQL 18, Docker, and SQL clients](part-01-fundamentals/003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md) — published; PostgreSQL 18 runtime acceptance pending.
4. [004 — Databases, schemas, tables, rows, and columns](part-01-fundamentals/004-databases-schemas-tables-rows-columns.md) — published; runtime testing pending.
5. [005 — Records, relationships, keys, and relational terminology](part-01-fundamentals/005-records-relationships-keys-and-relational-terminology.md) — published; runtime testing pending.
6. [006 — Anatomy of a SQL statement and logical query processing](part-01-fundamentals/006-anatomy-of-sql-statement-and-logical-query-processing.md) — published; runtime testing pending.
7. [007 — SELECT fundamentals: retrieve rows and columns](part-01-fundamentals/007-select-fundamentals-retrieve-rows-and-columns.md) — published; runtime testing pending.
8. [008 — Aliases, expressions, literals, and calculated columns](part-01-fundamentals/008-aliases-expressions-literals-and-calculated-columns.md) — published; runtime testing pending.
9. [009 — Data types, NULL, and explicit type conversion](part-01-fundamentals/009-data-types-null-and-explicit-type-conversion.md) — published; runtime testing pending.
10. [010 — Lab 01: explore the sample database and write first queries](part-01-fundamentals/010-lab-01-explore-sample-database-and-write-first-queries.md) — published; PostgreSQL 18 runtime validation pending.

## Part 02 — Filtering, Sorting & Conditional Logic

11. [011 — WHERE and comparison operators](part-02-filtering/011-where-and-comparison-operators.md) — published; [read-only SQL lab](labs/011-where-comparison-operators.sql); independent review and PostgreSQL 18 runtime testing pending.
12. [012 — AND, OR, NOT, and Boolean precedence](part-02-filtering/012-and-or-not-and-boolean-precedence.md) — published; [read-only SQL lab](labs/012-and-or-not-boolean-precedence.sql); independent review and PostgreSQL 18 runtime testing pending.

13. [013 — NULL handling and SQL three-valued logic](part-02-filtering/013-null-handling-and-sql-three-valued-logic.md) — published; [read-only SQL lab](labs/013-null-three-valued-logic.sql); independent review and PostgreSQL 18 runtime testing pending.

14. [014 — IN, BETWEEN, and range predicates](part-02-filtering/014-in-between-and-range-predicates.md) — published; [read-only SQL lab](labs/014-in-between-range-predicates.sql); independent review and PostgreSQL 18 runtime testing pending.

15. [015 — LIKE, wildcard matching, and dialect-specific ILIKE](part-02-filtering/015-like-wildcard-matching-and-dialect-specific-ilike.md) — published; [read-only SQL lab](labs/015-like-wildcards-ilike.sql); independent review and PostgreSQL 18 runtime testing pending.

16. [016 — DISTINCT and duplicate handling](part-02-filtering/016-distinct-and-duplicate-handling.md) — published; [read-only SQL lab](labs/016-distinct-duplicate-handling.sql); targeted static checks completed; independent editorial review and PostgreSQL 18 runtime testing pending.

17. [017 — ORDER BY and deterministic sorting](part-02-filtering/017-order-by-and-deterministic-sorting.md) — published; [read-only SQL lab](labs/017-order-by-deterministic-sorting.sql); targeted static inspection completed; independent editorial review and PostgreSQL 18 runtime validation pending.

The introductory lab is intentionally read-only and does not require permanent database objects.

## How chapters are developed

Read the authoritative chapter title and sequence in the Master TOC; publish one well-scoped chapter at a time under the designated part folder. Include clear explanations, executable SQL, expected results, troubleshooting, safety notes, review questions, references, and a hands-on lab. Record the publication and separately record content review and runtime validation; a published file alone is not proof of successful execution.

## Important safety rule

Use disposable/sandbox databases for any mutation or DDL exercises. Never run tutorial scripts against a production environment or include sensitive records. PostgreSQL 18 is the baseline, and other vendors are treated explicitly rather than assuming identical syntax.
