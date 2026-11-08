# SQL Tutorials — Master Table of Contents

> **Audience:** Beginners, data analysts, data engineers, application engineers, DBREs, and SREs.
> **Primary hands-on platform:** PostgreSQL 18 (SQL concepts taught portably first).
> **Additional dialects:** MySQL/MariaDB, SQL Server, Oracle, Snowflake, BigQuery, and SQLite where useful.
> **Scope:** 12 parts · 120 chapters · foundational to production-focused SQL.
> **Status:** Proposed curriculum / master TOC; tutorials and runtime validation are not implied to be complete.

## Learning objectives

- Read, write, test, and review SQL queries safely.
- Model relational data and maintain integrity with constraints and transactions.
- Build analytical queries using joins, aggregations, subqueries, CTEs, and window functions.
- Interpret query plans, improve performance, and troubleshoot operational SQL issues.
- Apply security, quality, migration, and recoverability controls in DBRE/SRE workflows.
- Recognize vendor-specific SQL features and validate portability across platforms.

## Curriculum map

| Part | Chapters | Focus | Milestone |
|---|---:|---|---|
| 01 | 001–010 | SQL & Relational Database Fundamentals | Lab 01 — explore the sample database and write first queries |
| 02 | 011–020 | Filtering, Sorting & Conditional Logic | Lab 02 — filter and rank operational records |
| 03 | 021–030 | Data Modeling, DDL & Constraints | Lab 03 — design and build a normalized operational schema |
| 04 | 031–040 | Data Modification & Transaction Fundamentals | Lab 04 — complete a safe, auditable transaction workflow |
| 05 | 041–050 | Joins & Relational Query Patterns | Lab 05 — consolidate customers, orders, and payments |
| 06 | 051–060 | Aggregation, Grouping & Reporting | Lab 06 — build a monthly KPI report |
| 07 | 061–070 | Subqueries, CTEs & Set Operations | Lab 07 — query a multi-level organizational hierarchy |
| 08 | 071–080 | Window Functions & Advanced Analytics | Lab 08 — produce an analytical customer activity report |
| 09 | 081–090 | SQL Objects, Functions & Semi-Structured Data | Lab 09 — build reusable reporting objects |
| 10 | 091–100 | SQL Performance & Query Optimization | Lab 10 — baseline, tune, and remeasure a slow query |
| 11 | 101–110 | Security, Data Quality & DBRE/SRE Operations | Lab 11 — operational SQL incident and recovery exercise |
| 12 | 111–120 | Data Engineering, SQL Dialects & Final Projects | Final capstone — end-to-end operational and analytical SQL project |

## Complete chapter index

### Part 01 — SQL & Relational Database Fundamentals

- **001.** Introduction to SQL — purpose, use cases, and stakeholder roles
- **002.** Relational databases and DBMS architecture
- **003.** Set up the SQL lab — PostgreSQL 18, Docker, and SQL clients
- **004.** Databases, schemas, tables, rows, and columns
- **005.** Records, relationships, keys, and relational terminology
- **006.** Anatomy of a SQL statement and logical query processing
- **007.** SELECT fundamentals — retrieve rows and columns
- **008.** Aliases, expressions, literals, and calculated columns
- **009.** Data types, NULL, and explicit type conversion
- **010.** Lab 01 — explore the sample database and write first queries

### Part 02 — Filtering, Sorting & Conditional Logic

- **011.** WHERE and comparison operators
- **012.** AND, OR, NOT, and Boolean precedence
- **013.** NULL handling and SQL three-valued logic
- **014.** IN, BETWEEN, and range predicates
- **015.** LIKE, wildcard matching, and dialect-specific ILIKE
- **016.** DISTINCT and duplicate handling
- **017.** ORDER BY and deterministic sorting
- **018.** LIMIT, OFFSET, FETCH, and TOP across dialects
- **019.** CASE, COALESCE, and NULLIF
- **020.** Lab 02 — filter and rank operational records

### Part 03 — Data Modeling, DDL & Constraints

- **021.** Entity relationships and conceptual data modeling
- **022.** CREATE DATABASE, CREATE SCHEMA, and CREATE TABLE
- **023.** Choosing numeric, character, Boolean, and temporal types
- **024.** Primary keys, natural keys, surrogate keys, and UNIQUE
- **025.** Foreign keys and referential integrity
- **026.** NOT NULL, CHECK, DEFAULT, and constraint validation
- **027.** Identity columns, sequences, and generated values
- **028.** ALTER TABLE, rename operations, and safe schema changes
- **029.** Normalization (1NF–3NF) and intentional denormalization
- **030.** Lab 03 — design and build a normalized operational schema

### Part 04 — Data Modification & Transaction Fundamentals

- **031.** INSERT single-row and multi-row records
- **032.** INSERT ... SELECT and bulk-loading fundamentals
- **033.** UPDATE with safe predicates and preview queries
- **034.** DELETE with safe predicates and referential implications
- **035.** DELETE versus TRUNCATE versus DROP
- **036.** UPSERT and MERGE patterns across SQL dialects
- **037.** RETURNING, OUTPUT, and write verification
- **038.** BEGIN, COMMIT, ROLLBACK, and SAVEPOINT
- **039.** Isolation levels and common transaction anomalies
- **040.** Lab 04 — complete a safe, auditable transaction workflow

### Part 05 — Joins & Relational Query Patterns

- **041.** Join fundamentals and relationship cardinality
- **042.** INNER JOIN — matched records
- **043.** LEFT OUTER JOIN — preserve unmatched left rows
- **044.** RIGHT and FULL OUTER JOIN — applicability and portability
- **045.** CROSS JOIN and SELF JOIN
- **046.** Multi-table joins and join condition design
- **047.** One-to-many and many-to-many relationships
- **048.** Semi-joins and anti-joins using EXISTS and NOT EXISTS
- **049.** Diagnose duplicate rows, fan-out, and NULL join pitfalls
- **050.** Lab 05 — consolidate customers, orders, and payments

### Part 06 — Aggregation, Grouping & Reporting

- **051.** COUNT, SUM, AVG, MIN, and MAX
- **052.** GROUP BY and aggregation grain
- **053.** HAVING versus WHERE
- **054.** Conditional aggregation with CASE and FILTER
- **055.** Date-based grouping and time buckets
- **056.** Text transformations for reporting
- **057.** Numeric rounding, ratios, and safe division
- **058.** ROLLUP, CUBE, and GROUPING SETS
- **059.** Pivoting and unpivoting — portable and vendor features
- **060.** Lab 06 — build a monthly KPI report

### Part 07 — Subqueries, CTEs & Set Operations

- **061.** Scalar subqueries and derived tables
- **062.** IN, ANY, ALL, and multi-row subqueries
- **063.** EXISTS versus IN and NULL-sensitive behavior
- **064.** Correlated subqueries and performance tradeoffs
- **065.** Common table expressions (WITH)
- **066.** Recursive CTEs and hierarchical queries
- **067.** UNION versus UNION ALL
- **068.** INTERSECT and EXCEPT (MINUS in some systems)
- **069.** Refactor complex SQL for readability and correctness
- **070.** Lab 07 — query a multi-level organizational hierarchy

### Part 08 — Window Functions & Advanced Analytics

- **071.** Window-function anatomy: OVER, PARTITION BY, ORDER BY
- **072.** ROW_NUMBER, RANK, and DENSE_RANK
- **073.** LAG and LEAD for change analysis
- **074.** Running totals and cumulative measures
- **075.** Rolling averages and moving windows
- **076.** FIRST_VALUE, LAST_VALUE, and window frames
- **077.** NTILE, percentiles, and distribution analysis
- **078.** Gaps-and-islands patterns
- **079.** Cohort analysis, retention, and event sequencing
- **080.** Lab 08 — produce an analytical customer activity report

### Part 09 — SQL Objects, Functions & Semi-Structured Data

- **081.** String functions and regular expressions
- **082.** Dates, intervals, timestamps, and time zones
- **083.** Numeric expressions and precision considerations
- **084.** JSON and semi-structured SQL queries
- **085.** Views and secure abstraction
- **086.** Materialized views and refresh strategies
- **087.** Temporary tables and intermediate result sets
- **088.** Stored functions and procedures — dialect-specific syntax
- **089.** Triggers, dynamic SQL, and parameterization safeguards
- **090.** Lab 09 — build reusable reporting objects

### Part 10 — SQL Performance & Query Optimization

- **091.** Read execution plans with EXPLAIN
- **092.** Table scans, index scans, row estimates, and selectivity
- **093.** B-tree indexes and common index access patterns
- **094.** Composite indexes and column order
- **095.** Partial, expression, and covering indexes
- **096.** Optimizer statistics and PostgreSQL maintenance basics
- **097.** Make predicates index-friendly and rewrite expensive SQL
- **098.** Optimize joins, aggregations, and subqueries
- **099.** Keyset pagination, benchmarking, and regression tests
- **100.** Lab 10 — baseline, tune, and remeasure a slow query

### Part 11 — Security, Data Quality & DBRE/SRE Operations

- **101.** Least privilege and SQL access-control principles
- **102.** Users, roles, GRANT, REVOKE, and ownership
- **103.** Row-level security and data-access policies
- **104.** Sensitive data protection, masking, and audit requirements
- **105.** Locks, blocking, deadlocks, and troubleshooting
- **106.** Backward-compatible migrations and deployment controls
- **107.** Data quality assertions and reconciliation queries
- **108.** Backup, recovery, and restore-validation concepts
- **109.** Slow-query investigation, monitoring, and incident runbooks
- **110.** Lab 11 — operational SQL incident and recovery exercise

### Part 12 — Data Engineering, SQL Dialects & Final Projects

- **111.** OLTP versus OLAP query design
- **112.** Star schemas, facts, dimensions, and surrogate keys
- **113.** ELT, incremental loads, and change data capture patterns
- **114.** Data warehouse SQL and analytical cost considerations
- **115.** Portable SQL versus vendor-specific syntax and testing
- **116.** PostgreSQL 18 SQL — lab baseline and advanced features
- **117.** MySQL and MariaDB — key syntax and behavior differences
- **118.** SQL Server/T-SQL and Oracle SQL — key differences
- **119.** Snowflake and BigQuery — cloud analytical SQL patterns
- **120.** Final capstone — end-to-end operational and analytical SQL project

## Recommended common tutorial format (60 minutes per chapter)

| Section | Suggested time | Expected material |
|---|---:|---|
| Learning outcomes and prerequisites | 5 min | Why the topic matters; dependencies |
| Key concepts and syntax | 10 min | Portable SQL first; dialect differences labeled |
| Walkthrough examples | 15 min | Readable, commented queries with results |
| Hands-on lab | 20 min | Setup, steps, assertions, expected outputs, cleanup |
| Validation and troubleshooting | 5 min | Correctness checks, performance/safety notes |
| Review questions and next chapter | 5 min | Knowledge check and links |

## Shared sample datasets

1. **Retail / e-commerce:** customers, products, orders, order_items, payments, inventory (introductory and intermediate chapters).
2. **Synthetic healthcare:** patients, providers, encounters, observations, claims, claim_lines (advanced joins, quality, security, and analytics). Use fictional data only.
3. **DBRE/SRE operations:** query samples, audit events, workload metrics, migration history, and incident evidence (operational chapters).

## Safety and quality rules

- Run write and schema-change labs only against isolated disposable databases; never reuse production credentials.
- Show SELECT previews, row counts, transaction boundaries, and rollback plans before UPDATE/DELETE/DDL demonstrations.
- Explicitly distinguish ANSI/ISO-style portable SQL from PostgreSQL-specific features and other dialect differences.
- Include expected results and automated checks where practical; do not claim a chapter or lab is validated without executing it.
- Use synthetic data; avoid real patient records, credentials, or sensitive production data.
- For performance exercises, record query plan, execution timing, data volume, and database version.

## Suggested GitHub layout

```text
sql-tutorials/
├── MASTER-TOC.md
├── README.md
├── STATUS-TRACKER.md
├── datasets/
│   ├── retail/
│   └── synthetic-healthcare/
├── labs/
│   ├── docker/
│   └── validation/
├── part-01-fundamentals/
│   ├── 001-introduction-to-sql.md
│   └── ...
├── part-02-filtering/
├── ...
└── part-12-platforms-capstone/
```

## Publication and validation checkpoints

- **Content:** chapters drafted, reviewed for correctness and beginner clarity.
- **Static QA:** all Markdown links, SQL formatting, prerequisites, and navigation checked.
- **Runtime QA:** setup scripts, SQL snippets, expected output, and cleanup executed in an isolated database.
- **Safety QA:** any destructive command has an explicit warning, isolated scope, and rollback/restore guidance.
- **Portability QA:** vendor-specific features have supported-version notes and equivalent patterns where applicable.
- **Progress:** track each chapter as `planned → drafted → reviewed → runtime-validated → published`.

**Recommended starting point:** Chapter 001 and the retail lab dataset; add the synthetic healthcare track beginning in the joins/analytics modules.