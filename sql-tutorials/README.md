# SQL Tutorials — Beginner to Advanced

**Audience:** Analysts, application developers, data engineers, DBREs, and SREs  
**Curriculum:** 12 parts, 120 chapters, approximately 60 minutes per chapter  
**Primary lab target:** PostgreSQL 18. Dialect-specific features are labeled, with comparisons to other SQL platforms where useful.

[MASTER-TOC.md](MASTER-TOC.md) · [STATUS-TRACKER.md](STATUS-TRACKER.md)

## Start here

1. [001 — Introduction to SQL: purpose, use cases, and stakeholder roles](part-01-fundamentals/001-introduction-to-sql.md) — published; runtime testing pending.
2. [002 — Relational databases and DBMS architecture](part-01-fundamentals/002-relational-databases-and-dbms-architecture.md) — published; runtime testing pending.
3. 003 — Set up the SQL lab: PostgreSQL 18, Docker, and SQL clients — planned.

The introductory lab is intentionally read-only and does not require permanent database objects.

## How chapters are developed

Read the authoritative chapter title and sequence in the Master TOC; publish one well-scoped chapter at a time under the designated part folder. Include clear explanations, executable SQL, expected results, troubleshooting, safety notes, review questions, references, and a hands-on lab. Record the publication and separately record content review and runtime validation; a published file alone is not proof of successful execution.

## Important safety rule

Use disposable/sandbox databases for any mutation or DDL exercises. Never run tutorial scripts against a production environment or include sensitive records. PostgreSQL 18 is the baseline, and other vendors are treated explicitly rather than assuming identical syntax.
