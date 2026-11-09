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

18. [018 — LIMIT, OFFSET, FETCH, and TOP across dialects](part-02-filtering/018-limit-offset-fetch-and-top-across-dialects.md) — published; [read-only SQL lab](labs/018-limit-offset-fetch-top.sql); targeted static inspection completed; independent editorial review and PostgreSQL 18 runtime validation pending.

19. [019 — CASE, COALESCE, and NULLIF](part-02-filtering/019-case-coalesce-and-nullif.md) — published; [read-only PostgreSQL 18 lab](labs/019-case-coalesce-nullif.sql); targeted static reasoning completed; independent review and PostgreSQL 18 runtime validation pending.


20. [020 — Lab 02: filter and rank operational records](part-02-filtering/020-lab-02-filter-and-rank-operational-records.md) — published; [read-only PostgreSQL 18 lab](labs/020-lab-02-filter-and-rank-operational-records.sql); targeted static reasoning only; independent review and PostgreSQL 18 runtime validation pending.

## Part 03 — Data Modeling, DDL & Constraints

21. [021 — Entity relationships and conceptual data modeling](part-03-modeling/021-entity-relationships-and-conceptual-data-modeling.md) — published; [read-only synthetic PostgreSQL 18 lab](labs/021-entity-relationships-conceptual-modeling.sql); targeted static inspection only, independent review and actual runtime validation pending.

22. [022 — CREATE DATABASE, CREATE SCHEMA, and CREATE TABLE](part-03-modeling/022-create-database-create-schema-and-create-table.md) — published; [isolated rollback-only PostgreSQL 18 DDL lab](labs/022-create-schema-and-tables-isolated.sql); targeted static inspection only; independent review, comprehensive syntax checks, and PostgreSQL 18 runtime validation pending.

23. [023 — Choosing numeric, character, Boolean, and temporal types](part-03-modeling/023-choosing-numeric-character-boolean-and-temporal-types.md) — published; [read-only PostgreSQL 18 lab](labs/023-choosing-sql-data-types.sql); targeted static reasoning only; independent review, comprehensive syntax checks, and runtime validation pending.


24. [024 — Primary keys, natural keys, surrogate keys, and UNIQUE](part-03-modeling/024-primary-keys-natural-keys-surrogate-keys-and-unique.md) — published; [isolated rollback-only PostgreSQL 18 lab](labs/024-primary-natural-surrogate-unique.sql); targeted static inspection only; independent editorial review, comprehensive syntax checks and actual PostgreSQL 18 runtime validation pending.

25. [025 — Foreign keys and referential integrity](part-03-modeling/025-foreign-keys-and-referential-integrity.md) — published; [isolated rollback-only PostgreSQL 18 lab](labs/025-foreign-keys-referential-integrity.sql); targeted static checks only; independent editorial review, comprehensive syntax checks and PostgreSQL 18 runtime validation pending.

26. [026 — NOT NULL, CHECK, DEFAULT, and constraint validation](part-03-modeling/026-not-null-check-default-and-constraint-validation.md) — published; [isolated rollback-only PostgreSQL 18 lab](labs/026-not-null-check-default-validation.sql); targeted static inspection only; independent editorial review, comprehensive SQL syntax checks and PostgreSQL 18 runtime validation pending.

27. [027 — Identity columns, sequences, and generated values](part-03-modeling/027-identity-columns-sequences-and-generated-values.md) — published; [isolated rollback-only PostgreSQL 18 lab](labs/027-identity-sequences-generated-values.sql); targeted static inspection only; independent editorial review, comprehensive SQL syntax checks, and PostgreSQL 18 runtime validation pending.

28. [028 — ALTER TABLE, rename operations, and safe schema changes](part-03-modeling/028-alter-table-rename-operations-and-safe-schema-changes.md) — published; [isolated rollback-only PostgreSQL 18 lab](labs/028-alter-table-safe-schema-changes.sql); targeted static inspection only; independent editorial review, comprehensive syntax checks and actual PostgreSQL 18 runtime validation pending.

29. [029 — Normalization (1NF–3NF) and intentional denormalization](part-03-modeling/029-normalization-1nf-3nf-and-intentional-denormalization.md) — published; [read-only PostgreSQL 18 lab](labs/029-normalization-1nf-3nf-denormalization.sql); targeted static reasoning only; independent editorial review, comprehensive syntax checks, and PostgreSQL 18 runtime validation pending.

30. [030 — Lab 03: design and build a normalized operational schema](part-03-modeling/030-lab-03-design-and-build-a-normalized-operational-schema.md) — published; [rollback-only PostgreSQL 18 lab](labs/030-lab-03-normalized-operational-schema.sql); targeted static inspection only; independent editorial review, comprehensive SQL syntax checks, and actual PostgreSQL 18 runtime validation pending.

## Part 04 — Data Modification & Transaction Fundamentals

31. [031 — INSERT single-row and multi-row records](part-04-data-modification/031-insert-single-row-and-multi-row-records.md) — published; [isolated rollback-only PostgreSQL 18 lab](labs/031-insert-single-row-and-multi-row-records.sql); targeted static inspection only; independent editorial review, comprehensive SQL syntax checks, and actual PostgreSQL 18 runtime validation pending.

32. [032 — INSERT ... SELECT and bulk-loading fundamentals](part-04-data-modification/032-insert-select-and-bulk-loading-fundamentals.md) — published; [isolated rollback-only PostgreSQL 18 lab](labs/032-insert-select-bulk-loading.sql); targeted static reasoning only; independent editorial review, comprehensive SQL syntax verification and actual PostgreSQL 18 runtime validation pending.

33. [033 — UPDATE with safe predicates and preview queries](part-04-data-modification/033-update-with-safe-predicates-and-preview-queries.md) — published; [isolated rollback-only PostgreSQL 18 lab](labs/033-update-safe-predicates-preview.sql); targeted static inspection only; independent editorial review, comprehensive SQL syntax verification and actual PostgreSQL 18 runtime validation pending.

The introductory lab is intentionally read-only and does not require permanent database objects.

## How chapters are developed

Read the authoritative chapter title and sequence in the Master TOC; publish one well-scoped chapter at a time under the designated part folder. Include clear explanations, executable SQL, expected results, troubleshooting, safety notes, review questions, references, and a hands-on lab. Record the publication and separately record content review and runtime validation; a published file alone is not proof of successful execution.

## Important safety rule

Use disposable/sandbox databases for any mutation or DDL exercises. Never run tutorial scripts against a production environment or include sensitive records. PostgreSQL 18 is the baseline, and other vendors are treated explicitly rather than assuming identical syntax.

34. [034 — DELETE with safe predicates and referential implications](part-04-data-modification/034-delete-with-safe-predicates-and-referential-implications.md) — published; [isolated rollback-only PostgreSQL 18 lab](labs/034-delete-safe-predicates-referential-implications.sql); targeted static inspection only; independent editorial review, comprehensive syntax verification and actual PostgreSQL 18 runtime execution pending.

35. [035 — DELETE versus TRUNCATE versus DROP](part-04-data-modification/035-delete-versus-truncate-versus-drop.md) — published; [isolated rollback-only PostgreSQL 18 lab](labs/035-delete-truncate-drop.sql); targeted static inspection only; independent editorial review, comprehensive SQL syntax verification, and actual PostgreSQL 18 runtime validation pending.
