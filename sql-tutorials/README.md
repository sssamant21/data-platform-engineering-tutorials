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
9. 009 — Data types, NULL, and explicit type conversion — planned.

The introductory lab is intentionally read-only and does not require permanent database objects.

## How chapters are developed

Read the authoritative chapter title and sequence in the Master TOC; publish one well-scoped chapter at a time under the designated part folder. Include clear explanations, executable SQL, expected results, troubleshooting, safety notes, review questions, references, and a hands-on lab. Record the publication and separately record content review and runtime validation; a published file alone is not proof of successful execution.

## Important safety rule

Use disposable/sandbox databases for any mutation or DDL exercises. Never run tutorial scripts against a production environment or include sensitive records. PostgreSQL 18 is the baseline, and other vendors are treated explicitly rather than assuming identical syntax.
