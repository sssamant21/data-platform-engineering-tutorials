# SQL Tutorials — Status Tracker

> **Scope:** 120 planned chapters in 12 parts. Source of truth for titles and chapter order: [MASTER-TOC.md](MASTER-TOC.md).
> **Updated:** 2026-11-13. Content publication and runtime validation are distinct milestones.

| Metric | Count |
|---|---:|
| Planned chapters | 120 |
| Authored and published chapters | 120 |
| Remaining to draft | 0 |
| Independently reviewed chapters | 0 |
| PostgreSQL 18 runtime-validated chapters | 0 |


## QA phase — initial baseline (2026-11-13)

[Targeted QA baseline, findings, corrections and acceptance plan](labs/validation/QA-BASELINE-2026-11-13.md). Initial inspection corrected stale publication wording in MASTER-TOC and Chapter 001. This is **not** comprehensive static QA or independent editorial certification. Full link/SQL checks and PostgreSQL 18 runtime execution remain pending; independently reviewed = 0 and runtime-validated = 0. Next: repository-wide file/link inventory, SQL expected-output review and isolated PostgreSQL 18 evidence collection.

## QA follow-up — README navigation (2026-11-13)

Resolved QA-003 by moving guidance below the complete chapter listing ([README](README.md), commit `d8047202e239bf41dc5a9f21d5506a1b2f4e97bb`). A fresh `main` fetch confirmed 120 numbered README entries, exactly 001–120, with no duplicate or missing chapter numbers. This verifies README numbering **only**; link targets, Markdown anchors, SQL syntax, expected outputs, independent review and PostgreSQL 18 runtime acceptance remain pending. [QA baseline](labs/validation/QA-BASELINE-2026-11-13.md) records the closure. Next: repository-wide link-target and lab inventory checks.

## QA follow-up — pinned repository inventory (2026-11-13)

[Repository inventory evidence](labs/validation/REPOSITORY-INVENTORY-2026-11-13.md), commit `31bc12d693b5544ba495e10301fc829fe66dbcc9`: non-truncated `main` tree `7c985eee50a7807d935aa82a5c7c207f1417c6af` contains 246 SQL-tutorials files, 120 unique numbered chapter Markdown files (001–120; zero gaps or duplicates), and 120 SQL files. All 232 local relative README link occurrences resolve to tracked paths. This is **targeted static inventory and README target verification**, not a full chapter/link/anchor audit, one-to-one lab mapping, SQL syntax check, independent editorial review or runtime validation. Independently reviewed: **0/120**; isolated PostgreSQL 18 runtime-validated: **0/120**. Next: resolve all chapter Markdown links/anchors and review SQL syntax, expected results and lab safety before isolated PostgreSQL 18 acceptance.

## QA follow-up — Chapters 001–006 local-link smoke check (2026-11-13)

[Targeted evidence](labs/validation/MARKDOWN-LINK-SMOKE-001-006-2026-11-13.md), commit `3cdbb5ce5e2deee492712a540ebe2bd902f8a190`: 34 inline local-link path targets across Chapters 001–006 were checked against GitHub `main` tree `f9ed726705b56055c988d9a0990f9b5e9bf1cd20`; zero missing paths. This is a limited static smoke check, **not** comprehensive Markdown link/anchor QA. Independent review **0/120**; actual PostgreSQL 18 runtime validation **0/120**. Next: full chapter-level reference/anchor audit, SQL syntax and lab-safety checks, then isolated PostgreSQL 18 runtime evidence.


## QA follow-up — Chapters 025–030 local-link smoke check (2026-11-13)

[Targeted evidence](labs/validation/MARKDOWN-LINK-SMOKE-025-030-2026-11-13.md), commit `f3f505fb6adfb0263f3c90fa0af99f8ef2fafc31`: 58 local inline Markdown link occurrences checked across Chapters 025–030 against non-truncated Git tree `06641da0aaf4154601b65f7a77016dce3e89e2e2`; zero missing tracked targets. 25 external HTTP(S) occurrences identified but not tested. Cumulative targeted local-link smoke-check coverage: **30/120** chapters. This is not full Markdown/anchor QA or SQL correctness. Independent editorial review: **0/120**; isolated PostgreSQL 18 runtime validation: **0/120**. Next: Chapters 031–036 local-link QA, comprehensive Markdown and SQL review, lab safety, and isolated runtime acceptance.


## QA follow-up — Chapters 031–036 local-link smoke check (2026-11-13)

[Targeted evidence](labs/validation/MARKDOWN-LINK-SMOKE-031-036-2026-11-13.md), commit `b6c6abf2ecf050fc69d299e678a3f077fe869eca`: 58 inline local Markdown link occurrences checked across Chapters 031–036 against Git tree `6f74e4a9fe035877d798f457f66193cac7bdc6b5`; zero missing tracked paths. 27 external HTTP(S) occurrences identified but not tested. Cumulative targeted local-path smoke coverage: **36/120** chapters. This is not comprehensive Markdown/anchor QA or SQL correctness. Independent editorial review: **0/120**; isolated PostgreSQL 18 runtime validation: **0/120**. Next: Chapters 037–042 local-link QA, full Markdown and SQL review, lab safety, and isolated runtime acceptance.

## QA follow-up — Chapters 037–042 local-link smoke check (2026-11-13)

[Targeted evidence](labs/validation/MARKDOWN-LINK-SMOKE-037-042-2026-11-13.md), commit `4cea9de1ec7006b4a9c1bf1b5d08a60c2d12d95e`: 45 local inline Markdown link occurrences checked across Chapters 037–042 against non-truncated Git tree `15177341979733ec4050597e66de758a5a5fcf73`; zero missing tracked paths. 28 external HTTP(S) occurrences identified but not tested. Cumulative targeted local-path smoke coverage: **42/120** chapters. This is not comprehensive Markdown/anchor QA, SQL correctness, or lab-safety certification. Independent editorial review: **0/120**; isolated PostgreSQL 18 runtime validation: **0/120**. Next: Chapters 043–048 local-link QA, full Markdown/SQL review, lab safety, and isolated runtime acceptance.


## QA follow-up — Chapters 043–048 local-link smoke check (2026-11-13)

[Targeted evidence](labs/validation/MARKDOWN-LINK-SMOKE-043-048-2026-11-13.md), commit `cfcbc9f199dcd174cfba62faf6d1f52b4b154e7d`: 32 inline local Markdown link occurrences checked across Chapters 043–048 against non-truncated Git tree `ef1374894ec12ffeb4e356dcb6d36d08272c6319`; zero missing tracked targets. 19 external HTTP(S) occurrences identified but not tested. Cumulative targeted local-path smoke coverage: **48/120** chapters. This is not comprehensive Markdown/anchor QA, SQL correctness, or lab-safety certification. Independent editorial review: **0/120**; isolated PostgreSQL 18 runtime validation: **0/120**. Next: Chapters 049–054 local-link QA, full Markdown/SQL review, lab safety, and isolated runtime acceptance.

## QA follow-up — Chapters 049–054 local-link smoke check (2026-11-13)

[Targeted evidence](labs/validation/MARKDOWN-LINK-SMOKE-049-054-2026-11-13.md), commit `96b9057fe71cf33492b0402bc38ffddb765f8985`: 43 local inline Markdown link occurrences checked across Chapters 049–054 against non-truncated Git tree `d99cc49e0bc60fd6aaa98a5134b7911c3c238774`; zero missing tracked paths. 29 external HTTP(S) occurrences identified but not tested. Cumulative targeted local-path smoke coverage: **54/120** chapters. This is not comprehensive Markdown/anchor QA, SQL correctness, or lab-safety certification. Independent editorial review: **0/120**; isolated PostgreSQL 18 runtime validation: **0/120**. Next: Chapters 055–060 local-link QA, comprehensive Markdown/SQL review, lab safety, and isolated runtime acceptance.

## QA follow-up — Chapters 055–060 local-link smoke check (2026-11-13)

[Targeted evidence](labs/validation/MARKDOWN-LINK-SMOKE-055-060-2026-11-13.md), commit `e54753bcc31c74124e452ffd8e8941ee24718f66`: 49 inline local Markdown link occurrences checked across Chapters 055–060 against complete Git tree `0391af5a1b86e2b27db361b9011b648ba16ffff6`; zero missing tracked paths. 24 external HTTP(S) occurrences identified but not tested. Cumulative targeted local-path smoke coverage: **60/120** chapters. This is not comprehensive Markdown/anchor QA, SQL correctness, or lab-safety certification. Independent editorial review: **0/120**; isolated PostgreSQL 18 runtime validation: **0/120**. Next: Chapters 061–066 targeted link QA, comprehensive Markdown/SQL review, lab safety, and isolated runtime acceptance.

## QA follow-up — Chapters 061–066 local-link smoke check (2026-11-13)

[Targeted evidence](labs/validation/MARKDOWN-LINK-SMOKE-061-066-2026-11-13.md), commit `08d8f4ec6751d9a7b6f85769423cd31752122c64`: 35 inline local Markdown link occurrences checked across Chapters 061–066 against complete Git tree `7a69e93d354c47ec402f4032aed0f64ebaa21855`; zero missing tracked paths. 20 external HTTP(S) occurrences identified but not tested. Cumulative targeted local-path smoke coverage: **66/120** chapters. This is not comprehensive Markdown/anchor QA, SQL correctness, or lab-safety certification. Independent editorial review: **0/120**; isolated PostgreSQL 18 runtime validation: **0/120**. Next: Chapters 067–072 local-link QA, comprehensive Markdown/SQL review, lab safety, and isolated runtime acceptance.

## QA follow-up — Chapters 067–072 local-link smoke check (2026-11-13)

[Targeted evidence](labs/validation/MARKDOWN-LINK-SMOKE-067-072-2026-11-13.md), commit `26b39d9ba17f5dc8287f3dafe7e89562fbe0c78c`: 34 inline local Markdown link occurrences checked across Chapters 067–072; zero missing local targets. 24 external HTTP(S) occurrences identified but not tested. Cumulative targeted local-path smoke coverage: **72/120** chapters. This does **not** establish comprehensive Markdown/anchor QA, SQL correctness, or lab-safety certification. Independent editorial review: **0/120**; isolated PostgreSQL 18 runtime validation: **0/120**. Next: Chapters 073–078 targeted link QA, comprehensive Markdown/SQL review, lab safety, and isolated runtime acceptance.

## QA follow-up — Chapters 073–078 local-link smoke check (2026-11-13)

[Targeted evidence](labs/validation/MARKDOWN-LINK-SMOKE-073-078-2026-11-13.md), commit `8f8b23789f4d59ebb017bc60e33c92f926686069`: 36 local inline Markdown link occurrences checked across Chapters 073–078 against complete Git tree `4bb55a2b8f87965dec618ee04fe43c29bfd06fda`; zero missing tracked targets. 19 external HTTP(S) occurrences identified but not tested. Six chapter and six corresponding lab files were read; lab SQL was not executed. Cumulative targeted local-path smoke coverage: **78/120** chapters. This is **not** comprehensive Markdown/anchor QA, SQL correctness, or lab-safety certification. Independent editorial review: **0/120**; isolated PostgreSQL 18 runtime validation: **0/120**. Next: Chapters 079–084 targeted local-link QA, comprehensive Markdown/SQL review, lab safety, and isolated runtime acceptance.

## QA follow-up — Chapters 079–084 local-link smoke check (2026-11-14)

[Targeted evidence](labs/validation/MARKDOWN-LINK-SMOKE-079-084-2026-11-14.md), commit `ee4a60a93a4ba7b2a784b4a3e2754d103ab32cff`: 52 inline local Markdown link occurrences across Chapters 079–084 resolved to 24 distinct tracked paths against non-truncated Git tree `f46834713a8b93850c3b6eca5c94a6899ac2a5d4`; zero missing targets. 24 external HTTP(S) occurrences were identified but not tested. Evidence file was fetched back from `main` before this tracker update. Cumulative targeted local-link smoke coverage: **84/120** chapters. This is not comprehensive Markdown/anchor QA, SQL correctness, expected-output or lab-safety certification. Independent editorial review: **0/120**; actual isolated PostgreSQL 18 runtime validation: **0/120**. Next: Chapters 085–090 local-link QA, comprehensive static checks, and isolated PostgreSQL 18 runtime acceptance.

## QA follow-up — Chapters 085–090 local-link smoke check (2026-11-14)

[Targeted evidence](labs/validation/MARKDOWN-LINK-SMOKE-085-090-2026-11-14.md), commit `81e363f244ffd3f0d2d343f1f864801269348e59`: Chapter 088 broken transaction prerequisite path corrected in commit `ca264bee67a03cd061c0a757723b31911f840833`. Across Chapters 085–090, **48** inline local Markdown links checked against complete, non-truncated Git tree `ca264bee67a03cd061c0a757723b31911f840833`; **zero missing tracked targets** after correction. **31** external HTTP(S) links identified but not tested. Evidence file fetched back and verified on `main` before tracker update. Cumulative targeted local-path smoke coverage: **90/120** chapters. This is **not** comprehensive Markdown/anchor QA, SQL correctness, expected-output verification, or lab-safety certification. Independent editorial review: **0/120**; actual isolated PostgreSQL 18 runtime validation: **0/120**. Next: Chapters 091–096 targeted link QA, comprehensive static QA, and isolated PostgreSQL 18 runtime acceptance with reproducible evidence.

## Part-level progress

| Part | Chapters | Published | Remaining |
|---|---|---:|---:|
| 01 — Fundamentals | 001–010 | 10 | 0 |
| 02 — Filtering and sorting | 011–020 | 10 | 0 |
| 03 — Modeling, DDL, constraints | 021–030 | 10 | 0 |
| 04 — Transactions and DML | 031–040 | 10 | 0 |
| 05 — Joins | 041–050 | 10 | 0 |
| 06 — Aggregation and reporting | 051–060 | 10 | 0 |
| 07 — Subqueries and CTEs | 061–070 | 10 | 0 |
| 08 — Window functions | 071–080 | 10 | 0 |
| 09 — Functions, views, JSON | 081–090 | 10 | 0 |
| 10 — Performance | 091–100 | 10 | 0 |
| 11 — Security and DBRE/SRE | 101–110 | 10 | 0 |
| 12 — Data engineering and dialects | 111–120 | 10 | 0 |

## Chapter status

| Chapter | Title | Content | Review | Runtime |
|---|---|---|---|---|
| [001](part-01-fundamentals/001-introduction-to-sql.md) | Introduction to SQL — purpose, use cases, and stakeholder roles | Published | Pending | Pending |
| [002](part-01-fundamentals/002-relational-databases-and-dbms-architecture.md) | Relational databases and DBMS architecture | Published | Pending | Pending |
| [003](part-01-fundamentals/003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md) | Set up the SQL lab — PostgreSQL 18, Docker, and SQL clients | Published | Pending | Pending |
| [004](part-01-fundamentals/004-databases-schemas-tables-rows-columns.md) | Databases, schemas, tables, rows, and columns | Published | Pending | Pending |
| [005](part-01-fundamentals/005-records-relationships-keys-and-relational-terminology.md) | Records, relationships, keys, and relational terminology | Published | Pending | Pending |
| [006](part-01-fundamentals/006-anatomy-of-sql-statement-and-logical-query-processing.md) | Anatomy of a SQL statement and logical query processing | Published | Pending | Pending |
| [007](part-01-fundamentals/007-select-fundamentals-retrieve-rows-and-columns.md) | SELECT fundamentals — retrieve rows and columns | Published | Pending | Pending |
| [008](part-01-fundamentals/008-aliases-expressions-literals-and-calculated-columns.md) | Aliases, expressions, literals, and calculated columns | Published | Pending | Pending |
| [009](part-01-fundamentals/009-data-types-null-and-explicit-type-conversion.md) | Data types, NULL, and explicit type conversion | Published | Pending | Pending |
| [010](part-01-fundamentals/010-lab-01-explore-sample-database-and-write-first-queries.md) | Lab 01 — explore the sample database and write first queries | Published | Pending | Pending |
| [011](part-02-filtering/011-where-and-comparison-operators.md) | WHERE and comparison operators | Published | Pending | Pending |
| [012](part-02-filtering/012-and-or-not-and-boolean-precedence.md) | AND, OR, NOT, and Boolean precedence | Published | Pending | Pending |
| [013](part-02-filtering/013-null-handling-and-sql-three-valued-logic.md) | NULL handling and SQL three-valued logic | Published | Pending | Pending |
| [014](part-02-filtering/014-in-between-and-range-predicates.md) | IN, BETWEEN, and range predicates | Published | Pending | Pending |
| [015](part-02-filtering/015-like-wildcard-matching-and-dialect-specific-ilike.md) | LIKE, wildcard matching, and dialect-specific ILIKE | Published | Pending | Pending |
| [016](part-02-filtering/016-distinct-and-duplicate-handling.md) | DISTINCT and duplicate handling | Published | Pending | Pending |
| [017](part-02-filtering/017-order-by-and-deterministic-sorting.md) | ORDER BY and deterministic sorting | Published | Pending | Pending |
| [018](part-02-filtering/018-limit-offset-fetch-and-top-across-dialects.md) | LIMIT, OFFSET, FETCH, and TOP across dialects | Published | Pending | Pending |
| [019](part-02-filtering/019-case-coalesce-and-nullif.md) | CASE, COALESCE, and NULLIF | Published | Pending | Pending |
| [020](part-02-filtering/020-lab-02-filter-and-rank-operational-records.md) | Lab 02 — filter and rank operational records | Published | Pending | Pending |
| [021](part-03-modeling/021-entity-relationships-and-conceptual-data-modeling.md) | Entity relationships and conceptual data modeling | Published | Pending | Pending |
| [022](part-03-modeling/022-create-database-create-schema-and-create-table.md) | CREATE DATABASE, CREATE SCHEMA, and CREATE TABLE | Published | Pending | Pending |
| [023](part-03-modeling/023-choosing-numeric-character-boolean-and-temporal-types.md) | Choosing numeric, character, Boolean, and temporal types | Published | Pending | Pending |
| [024](part-03-modeling/024-primary-keys-natural-keys-surrogate-keys-and-unique.md) | Primary keys, natural keys, surrogate keys, and UNIQUE | Published | Pending | Pending |
| [025](part-03-modeling/025-foreign-keys-and-referential-integrity.md) | Foreign keys and referential integrity | Published | Pending | Pending |
| [026](part-03-modeling/026-not-null-check-default-and-constraint-validation.md) | NOT NULL, CHECK, DEFAULT, and constraint validation | Published | Pending | Pending |
| [027](part-03-modeling/027-identity-columns-sequences-and-generated-values.md) | Identity columns, sequences, and generated values | Published | Pending | Pending |
| [028](part-03-modeling/028-alter-table-rename-operations-and-safe-schema-changes.md) | ALTER TABLE, rename operations, and safe schema changes | Published | Pending | Pending |
| [029](part-03-modeling/029-normalization-1nf-3nf-and-intentional-denormalization.md) | Normalization (1NF–3NF) and intentional denormalization | Published | Pending | Pending |
| [030](part-03-modeling/030-lab-03-design-and-build-a-normalized-operational-schema.md) | Lab 03 — design and build a normalized operational schema | Published | Pending | Pending |
| [031](part-04-data-modification/031-insert-single-row-and-multi-row-records.md) | INSERT single-row and multi-row records | Published | Pending | Pending |
| [032](part-04-data-modification/032-insert-select-and-bulk-loading-fundamentals.md) | INSERT ... SELECT and bulk-loading fundamentals | Published | Pending | Pending |
| [033](part-04-data-modification/033-update-with-safe-predicates-and-preview-queries.md) | UPDATE with safe predicates and preview queries | Published | Pending | Pending |
| [034](part-04-data-modification/034-delete-with-safe-predicates-and-referential-implications.md) | DELETE with safe predicates and referential implications | Published | Pending | Pending |
| [035](part-04-data-modification/035-delete-versus-truncate-versus-drop.md) | DELETE versus TRUNCATE versus DROP | Published | Pending | Pending |
| [036](part-04-data-modification/036-upsert-and-merge-patterns-across-sql-dialects.md) | UPSERT and MERGE patterns across SQL dialects | Published | Pending | Pending |
| [037](part-04-data-modification/037-returning-output-and-write-verification.md) | RETURNING, OUTPUT, and write verification | Published | Pending | Pending |
| [038](part-04-data-modification/038-begin-commit-rollback-and-savepoint.md) | BEGIN, COMMIT, ROLLBACK, and SAVEPOINT | Published | Pending | Pending |
| [039](part-04-data-modification/039-isolation-levels-and-common-transaction-anomalies.md) | Isolation levels and common transaction anomalies | Published | Pending | Pending |
| [040](part-04-data-modification/040-lab-04-complete-a-safe-auditable-transaction-workflow.md) | Lab 04 — complete a safe, auditable transaction workflow | Published | Pending | Pending |
| [041](part-05-joins/041-join-fundamentals-and-relationship-cardinality.md) | Join fundamentals and relationship cardinality | Published | Pending | Pending |
| [042](part-05-joins/042-inner-join-matched-records.md) | INNER JOIN — matched records | Published | Pending | Pending |
| [043](part-05-joins/043-left-outer-join-preserve-unmatched-left-rows.md) | LEFT OUTER JOIN — preserve unmatched left rows | Published | Pending | Pending |
| [044](part-05-joins/044-right-and-full-outer-join-applicability-and-portability.md) | RIGHT and FULL OUTER JOIN — applicability and portability | Published | Pending | Pending |
| [045](part-05-joins/045-cross-join-and-self-join.md) | CROSS JOIN and SELF JOIN | Published | Pending | Pending |
| [046](part-05-joins/046-multi-table-joins-and-join-condition-design.md) | Multi-table joins and join condition design | Published | Pending | Pending |
| [047](part-05-joins/047-one-to-many-and-many-to-many-relationships.md) | One-to-many and many-to-many relationships | Published | Pending | Pending |
| [048](part-05-joins/048-semi-joins-and-anti-joins-using-exists-and-not-exists.md) | Semi-joins and anti-joins using EXISTS and NOT EXISTS | Published | Pending | Pending |
| [049](part-05-joins/049-diagnose-duplicate-rows-fan-out-and-null-join-pitfalls.md) | Diagnose duplicate rows, fan-out, and NULL join pitfalls | Published | Pending | Pending |
| [050](part-05-joins/050-lab-05-consolidate-customers-orders-and-payments.md) | Lab 05 — consolidate customers, orders, and payments | Published | Pending | Pending |
| [051](part-06-aggregation/051-count-sum-avg-min-and-max.md) | COUNT, SUM, AVG, MIN, and MAX | Published | Pending | Pending |
| [052](part-06-aggregation/052-group-by-and-aggregation-grain.md) | GROUP BY and aggregation grain | Published | Pending | Pending |
| [053](part-06-aggregation/053-having-versus-where.md) | HAVING versus WHERE | Published | Pending | Pending |
| [054](part-06-aggregation/054-conditional-aggregation-with-case-and-filter.md) | Conditional aggregation with CASE and FILTER | Published | Pending | Pending |
| [055](part-06-aggregation/055-date-based-grouping-and-time-buckets.md) | Date-based grouping and time buckets | Published | Pending | Pending |
| [056](part-06-aggregation/056-text-transformations-for-reporting.md) | Text transformations for reporting | Published | Pending | Pending |
| [057](part-06-aggregation/057-numeric-rounding-ratios-and-safe-division.md) | Numeric rounding, ratios, and safe division | Published | Pending | Pending |
| [058](part-06-aggregation/058-rollup-cube-and-grouping-sets.md) | ROLLUP, CUBE, and GROUPING SETS | Published | Pending | Pending |
| [059](part-06-aggregation/059-pivoting-and-unpivoting-portable-and-vendor-features.md) | Pivoting and unpivoting — portable and vendor features | Published | Pending | Pending |
| [060](part-06-aggregation/060-lab-06-build-a-monthly-kpi-report.md) | Lab 06 — build a monthly KPI report | Published | Pending | Pending |
| [061](part-07-subqueries/061-scalar-subqueries-and-derived-tables.md) | Scalar subqueries and derived tables | Published | Pending | Pending |
| [062](part-07-subqueries/062-in-any-all-and-multi-row-subqueries.md) | IN, ANY, ALL, and multi-row subqueries | Published | Pending | Pending |
| [063](part-07-subqueries/063-exists-versus-in-and-null-sensitive-behavior.md) | EXISTS versus IN and NULL-sensitive behavior | Published | Pending | Pending |
| [064](part-07-subqueries/064-correlated-subqueries-and-performance-tradeoffs.md) | Correlated subqueries and performance tradeoffs | Published | Pending | Pending |
| [065](part-07-subqueries/065-common-table-expressions-with.md) | Common table expressions (WITH) | Published | Pending | Pending |
| [066](part-07-subqueries/066-recursive-ctes-and-hierarchical-queries.md) | Recursive CTEs and hierarchical queries | Published | Pending | Pending |
| [067](part-07-subqueries/067-union-versus-union-all.md) | UNION versus UNION ALL | Published | Pending | Pending |
| [068](part-07-subqueries/068-intersect-and-except.md) | INTERSECT and EXCEPT (MINUS in some systems) | Published | Pending | Pending |
| [069](part-07-subqueries/069-refactor-complex-sql-for-readability-and-correctness.md) | Refactor complex SQL for readability and correctness | Published | Pending | Pending |
| [070](part-07-subqueries/070-lab-07-query-a-multi-level-organizational-hierarchy.md) | Lab 07 — query a multi-level organizational hierarchy | Published | Pending | Pending |
| [071](part-08-window-functions/071-window-function-anatomy-over-partition-by-order-by.md) | Window-function anatomy: OVER, PARTITION BY, ORDER BY | Published | Pending | Pending |

| [072](part-08-window-functions/072-row-number-rank-and-dense-rank.md) | ROW_NUMBER, RANK, and DENSE_RANK | Published | Pending | Pending |
| [073](part-08-window-functions/073-lag-and-lead-for-change-analysis.md) | LAG and LEAD for change analysis | Published | Pending | Pending |
| [074](part-08-window-functions/074-running-totals-and-cumulative-measures.md) | Running totals and cumulative measures | Published | Pending | Pending |
| [075](part-08-window-functions/075-rolling-averages-and-moving-windows.md) | Rolling averages and moving windows | Published | Pending | Pending |
| [076](part-08-window-functions/076-first-value-last-value-and-window-frames.md) | FIRST_VALUE, LAST_VALUE, and window frames | Published | Pending | Pending |
| [077](part-08-window-functions/077-ntile-percentiles-and-distribution-analysis.md) | NTILE, percentiles, and distribution analysis | Published | Pending | Pending |
| [078](part-08-window-functions/078-gaps-and-islands-patterns.md) | Gaps-and-islands patterns | Published | Pending | Pending |
| [079](part-08-window-functions/079-cohort-analysis-retention-and-event-sequencing.md) | Cohort analysis, retention, and event sequencing | Published | Pending | Pending |

| [081](part-09-functions-views-json/081-string-functions-and-regular-expressions.md) | String functions and regular expressions | Published | Pending | Pending |
| [082](part-09-functions-views-json/082-dates-intervals-timestamps-and-time-zones.md) | Dates, intervals, timestamps, and time zones | Published | Pending | Pending |
| [083](part-09-functions-views-json/083-numeric-expressions-and-precision-considerations.md) | Numeric expressions and precision considerations | Published | Pending | Pending |
| [084](part-09-functions-views-json/084-json-and-semi-structured-sql-queries.md) | JSON and semi-structured SQL queries | Published | Pending | Pending |
| [085](part-09-functions-views-json/085-views-and-secure-abstraction.md) | Views and secure abstraction | Published | Pending | Pending |
| [086](part-09-functions-views-json/086-materialized-views-and-refresh-strategies.md) | Materialized views and refresh strategies | Published | Pending | Pending |
| [087](part-09-functions-views-json/087-temporary-tables-and-intermediate-result-sets.md) | Temporary tables and intermediate result sets | Published | Pending | Pending |

| [088](part-09-functions-views-json/088-stored-functions-and-procedures-dialect-specific-syntax.md) | Stored functions and procedures — dialect-specific syntax | Published | Pending | Pending |
| [089](part-09-functions-views-json/089-triggers-dynamic-sql-and-parameterization-safeguards.md) | Triggers, dynamic SQL, and parameterization safeguards | Published | Pending | Pending |
| [090](part-09-functions-views-json/090-lab-09-build-reusable-reporting-objects.md) | Lab 09 — build reusable reporting objects | Published | Pending | Pending |

| [091](part-10-performance/091-read-execution-plans-with-explain.md) | Read execution plans with EXPLAIN | Published | Pending | Pending |
| [092](part-10-performance/092-table-scans-index-scans-row-estimates-and-selectivity.md) | Table scans, index scans, row estimates, and selectivity | Published | Pending | Pending |
| [093](part-10-performance/093-btree-indexes-and-common-index-access-patterns.md) | B-tree indexes and common index access patterns | Published | Pending | Pending |
| [094](part-10-performance/094-composite-indexes-and-column-order.md) | Composite indexes and column order | Published | Pending | Pending |
| [095](part-10-performance/095-partial-expression-and-covering-indexes.md) | Partial, expression, and covering indexes | Published | Pending | Pending |
| [096](part-10-performance/096-optimizer-statistics-and-postgresql-maintenance-basics.md) | Optimizer statistics and PostgreSQL maintenance basics | Published | Pending | Pending |
| [097](part-10-performance/097-make-predicates-index-friendly-and-rewrite-expensive-sql.md) | Make predicates index-friendly and rewrite expensive SQL | Published | Pending | Pending |
| [098](part-10-performance/098-optimize-joins-aggregations-and-subqueries.md) | Optimize joins, aggregations, and subqueries | Published | Pending | Pending |
| [099](part-10-performance/099-keyset-pagination-benchmarking-and-regression-tests.md) | Keyset pagination, benchmarking, and regression tests | Published | Pending | Pending |
| [100](part-10-performance/100-lab-10-baseline-tune-and-remeasure-a-slow-query.md) | Lab 10 — baseline, tune, and remeasure a slow query | Published | Pending | Pending |
| [101](part-11-security-operations/101-least-privilege-and-sql-access-control-principles.md) | Least privilege and SQL access-control principles | Published | Pending | Pending |
| [102](part-11-security-operations/102-users-roles-grant-revoke-and-ownership.md) | Users, roles, GRANT, REVOKE, and ownership | Published | Pending | Pending |
| [103](part-11-security-operations/103-row-level-security-and-data-access-policies.md) | Row-level security and data-access policies | Published | Pending | Pending |
| [104](part-11-security-operations/104-sensitive-data-protection-masking-and-audit-requirements.md) | Sensitive data protection, masking, and audit requirements | Published | Pending | Pending |
| [105](part-11-security-operations/105-locks-blocking-deadlocks-and-troubleshooting.md) | Locks, blocking, deadlocks, and troubleshooting | Published | Pending | Pending |

| [106](part-11-security-operations/106-backward-compatible-migrations-and-deployment-controls.md) | Backward-compatible migrations and deployment controls | Published | Pending | Pending |
| [107](part-11-security-operations/107-data-quality-assertions-and-reconciliation-queries.md) | Data quality assertions and reconciliation queries | Published | Pending | Pending |
| [108](part-11-security-operations/108-backup-recovery-and-restore-validation-concepts.md) | Backup, recovery, and restore-validation concepts | Published | Pending | Pending |
| [109](part-11-security-operations/109-slow-query-investigation-monitoring-and-incident-runbooks.md) | Slow-query investigation, monitoring, and incident runbooks | Published | Pending | Pending |
| [110](part-11-security-operations/110-lab-11-operational-sql-incident-and-recovery-exercise.md) | Lab 11 — operational SQL incident and recovery exercise | Published | Pending | Pending |
| [111](part-12-platforms-capstone/111-oltp-versus-olap-query-design.md) | OLTP versus OLAP query design | Published | Pending | Pending |
| [112](part-12-platforms-capstone/112-star-schemas-facts-dimensions-and-surrogate-keys.md) | Star schemas, facts, dimensions, and surrogate keys | Published | Pending | Pending |
| [113](part-12-platforms-capstone/113-elt-incremental-loads-and-change-data-capture-patterns.md) | ELT, incremental loads, and change data capture patterns | Published | Pending | Pending |
| [114](part-12-platforms-capstone/114-data-warehouse-sql-and-analytical-cost-considerations.md) | Data warehouse SQL and analytical cost considerations | Published | Pending | Pending |
| [115](part-12-platforms-capstone/115-portable-sql-versus-vendor-specific-syntax-and-testing.md) | Portable SQL versus vendor-specific syntax and testing | Published | Pending | Pending |
| [116](part-12-platforms-capstone/116-postgresql-18-sql-lab-baseline-and-advanced-features.md) | PostgreSQL 18 SQL — lab baseline and advanced features | Published | Pending | Pending |
| [117](part-12-platforms-capstone/117-mysql-and-mariadb-key-syntax-and-behavior-differences.md) | MySQL and MariaDB — key syntax and behavior differences | Published | Pending | Pending |
| [118](part-12-platforms-capstone/118-sql-server-tsql-and-oracle-sql-key-differences.md) | SQL Server/T-SQL and Oracle SQL — key differences | Published | Pending | Pending |
| [119](part-12-platforms-capstone/119-snowflake-and-bigquery-cloud-analytical-sql-patterns.md) | Snowflake and BigQuery — cloud analytical SQL patterns | Published | Pending | Pending |
| [120](part-12-platforms-capstone/120-final-capstone-end-to-end-operational-and-analytical-sql-project.md) | Final capstone — end-to-end operational and analytical SQL project | Published | Pending | Pending |

## Chapter 002 publication evidence

- Chapter: [002](part-01-fundamentals/002-relational-databases-and-dbms-architecture.md); commit `bb9c5761befd5ef469e0fdc10f12968c49dddd2f`.
- Lab: [002 SQL](labs/002-relational-architecture.sql); commit `3381fbee46c8199797ecd0a8c029749e00afc893`.
- GitHub fetch verified both files on `main`; read-only static check completed. Independent review and PostgreSQL 18 runtime execution remain pending.

## Chapter 003 publication evidence

- Chapter: [003](part-01-fundamentals/003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md); commit `1efd2d4da9fc7809d7a58895d6863f4d6f5b3e5d`.
- Docker Compose: [compose.yaml](labs/docker/compose.yaml); commit `b1c1324798a19400e6e42aca1e33a07127f9a9d5`.
- SQL: [003-lab-smoke-test.sql](labs/003-lab-smoke-test.sql); commit `618cb38e25eef5ee43cd22aa6f2834534819347f`.
- Lab guide: [Docker README](labs/docker/README.md); commit `79be3378d1dc564deec58e9673ab40756bceb94b`.
- GitHub fetch confirmed all four artifacts on `main`. Static checks: read-only SQL, version assertion, loopback port, PostgreSQL 18 volume path. **No PostgreSQL 18 container was run**; independent review and runtime evidence remain pending.

## Chapter 004 publication evidence

- Chapter: [004](part-01-fundamentals/004-databases-schemas-tables-rows-columns.md); commit `d688a90b294b0cc5de10b58be5ce2eac7d5d49f5`.
- Lab: [004 SQL](labs/004-databases-schemas-tables-rows-columns.sql); commit `75d0d135f93f88e34e8baf79a8a6b25ba1194ef8`.
- GitHub fetch verified both files on `main`. Lab uses `BEGIN READ ONLY` and synthetic in-query rows. Expected counts and sums reviewed. **No PostgreSQL 18 execution evidence**; independent review and runtime acceptance remain pending.

## Chapter 005 publication evidence

- Chapter: [005](part-01-fundamentals/005-records-relationships-keys-and-relational-terminology.md); commit `3c136e65ae133fa5c53a806e559dcae17d8cfe10`.
- Lab: [005 SQL](labs/005-records-relationships-keys.sql); commit `d4b165fb857fc714207bf238df3fd94227b48673`.
- GitHub fetch verified both files on `main`. Static review found a read-only transaction, environment checks, synthetic data and expected-output assertions. **Independent editorial review and actual PostgreSQL 18 execution are pending**.

## Chapter 006 publication evidence

- Chapter: [006](part-01-fundamentals/006-anatomy-of-sql-statement-and-logical-query-processing.md); commit `565e76ee88ea194bc13438f9224341a62af69ffc`.
- Lab: [006 SQL](labs/006-statement-anatomy-logical-processing.sql); commit `ce6d2247b8c6db8d23d8185e39a26c4fd5c204cf`.
- Both artifacts fetched and verified on `main`; read-only transaction, synthetic dataset, environment guards and deterministic expected-result assertions checked statically. **Independent editorial review and PostgreSQL 18 runtime execution remain pending.**

## Chapter 007 publication evidence

- Chapter: [007](part-01-fundamentals/007-select-fundamentals-retrieve-rows-and-columns.md); commit `fdb84ad882d409c3465b2a11eda2d08f9bca07d6`.
- Lab: [007 SQL](labs/007-select-fundamentals.sql); commit `224e32e508fa0db6fb8f87d08e3cda581b919f6d`.
- Both files re-fetched and verified on `main`. Read-only transaction, synthetic CTE data, environment assertion, and expected-results acceptance checks reviewed statically. **Independent editorial review and PostgreSQL 18 runtime execution remain pending.**

## Chapter 008 publication evidence

- Chapter: [008](part-01-fundamentals/008-aliases-expressions-literals-and-calculated-columns.md); commit `cc4f9d272ff6fc0e7fd64fc88a6a5b07b77c8e83`.
- Lab: [008 SQL](labs/008-aliases-expressions-calculated-columns.sql); commit `f73a41bc9f39408bf6cd4a9c756d35b89832ed15`.
- Both files were re-fetched from `main`; basic static inspection confirmed the lab contains no persistent write/DDL commands. Expected arithmetic and results were reviewed manually. **Independent editorial review and PostgreSQL 18 runtime execution remain pending**.

## Chapter 009 publication evidence

- Chapter: [009](part-01-fundamentals/009-data-types-null-and-explicit-type-conversion.md); commit `04db4722ca526560a32997d4ebb2f9810a5ea9b5`.
- Lab: [009 SQL](labs/009-data-types-null-explicit-conversion.sql); commit `550f2eca4b3e453608bfecada7b50d6b287dd2f2`.
- README navigation: commit `4f57cbb884c6e77197d4add7f3523dcb402ebccc`.
- Both chapter and lab re-fetched from GitHub `main`. Targeted static inspection confirmed the SQL lab's PostgreSQL 18/database guard, read-only transaction, synthetic data, deterministic checks, and rollback. Expected results reviewed against literal inputs; full independent editorial review and automated SQL syntax verification remain pending.
- **No isolated PostgreSQL 18 runtime execution or reproducible runtime evidence was obtained; runtime validation remains pending.**

## Chapter 010 publication evidence

- Chapter: [010](part-01-fundamentals/010-lab-01-explore-sample-database-and-write-first-queries.md); commit `0d19c77c02a777aca3a030486247ed58603e31af`.
- Lab: [010 SQL](labs/010-lab-01-explore-sample-database.sql); commit `1231f6269e01c8313ca7168064db6afe06e4a6fe`.
- Both files were re-fetched and verified on GitHub main. Static inspection checked synthetic CTE datasets, read-only transaction, PostgreSQL 18/database assertion, deterministic expected counts/totals and rollback. Independent editorial review and actual isolated PostgreSQL 18 execution with retained evidence are **pending**.
- Part 01 authored/published: **10/10**. This is not a runtime certification.

## Chapter 011 publication evidence

- Chapter: [011](part-02-filtering/011-where-and-comparison-operators.md); commit `a408496b1310e033d91a28b04685d2b2ed07165d`.
- Lab: [011 SQL](labs/011-where-comparison-operators.sql); commit `e1c0c0398966635f2bc1f763f8fac0da448dcebb`.
- README navigation: commit `a25de1adde8c6f7acd7cf83192b223c21aca333e`.
- Chapter and lab re-fetched from GitHub main. Targeted static review: lab uses synthetic VALUES, read-only transaction, PostgreSQL 18/database guard, six expected ID-set checks, fail-closed assertion and ROLLBACK. Link paths inspected. **Independent editorial review, comprehensive SQL syntax validation, and actual isolated PostgreSQL 18 execution are pending**; no runtime evidence obtained.

## Chapter 012 publication evidence

- Chapter: [012](part-02-filtering/012-and-or-not-and-boolean-precedence.md); commit `3dfcdc4fd9522cde1cc5d8ce978dec9d8b30cb6b`.
- Lab: [012 SQL](labs/012-and-or-not-boolean-precedence.sql); commit `ef90ac64ac1753691731c97f1836d2e92e89482a`.
- README navigation commit `bd1febc26a6b54a0658db0f2bbfd44d7bb981fa3`.
- Both chapter and lab were re-fetched from GitHub `main`. Targeted static inspection confirmed synthetic `VALUES`, read-only transaction, version/database guard, six exact ID-set acceptance checks, and rollback. Expected ID sets reviewed from literal data. **Independent editorial review, comprehensive SQL syntax checks, and actual isolated PostgreSQL 18 execution remain pending**; no runtime evidence was collected.

## Chapter 013 publication evidence

- Chapter: [013](part-02-filtering/013-null-handling-and-sql-three-valued-logic.md); commit `1f2f5332773e478e99e8b6995dc24a50ab4a1acd`.
- Lab: [013 SQL](labs/013-null-three-valued-logic.sql); commit `bdb0622d5cebb91cd42d5fc1b52e25aa75f2713a`.
- README navigation: commit `38b64b43aea7d1482a0aa29fe187cfe34cd5b6a1`.
- Chapter and lab fetched and verified on GitHub main. Targeted static inspection: synthetic VALUES, read-only transaction, PostgreSQL version/database assertion, exact-result acceptance checks, and ROLLBACK. Expected outputs manually reasoned from literal inputs. **Independent editorial review, full SQL syntax checks, and isolated PostgreSQL 18 runtime execution remain pending.** No runtime evidence obtained.

## Chapter 014 publication evidence

- Chapter: [014](part-02-filtering/014-in-between-and-range-predicates.md); commit `0f45320d52f9b5e61e63749c5d5afa14e562e78d`.
- Lab: [014 SQL](labs/014-in-between-range-predicates.sql); commit `2344290efa45eccac7bbbe777a2cb794c97e6f32`.
- README navigation: commit `f1ac6cc4b5808e3f4abb13345665a4c9f6c96c64`.
- Both new files were re-fetched from GitHub `main`. Targeted static inspection confirmed synthetic inline data, a read-only transaction, PostgreSQL 18/database guard, expected-result assertions, and rollback. Relative navigation paths inspected; expected ID sets reasoned from literal rows. **Independent editorial review, comprehensive SQL syntax checks, and actual isolated PostgreSQL 18 execution remain pending.** No runtime evidence was collected.

## Chapter 015 publication evidence

- Chapter: [015](part-02-filtering/015-like-wildcard-matching-and-dialect-specific-ilike.md); commit `5a244acc78427699052f44ecbab3f58aa62169ea`.
- Lab: [015 SQL](labs/015-like-wildcards-ilike.sql); commit `0e627742f0657fafc21a4aa085ea9b8021d6c14c`.
- Both files re-fetched from GitHub `main`. Targeted static inspection: synthetic inline VALUES, read-only transaction, PostgreSQL 18/database guard, explicit C collation for case-sensitive examples, expected ID-set assertions, and rollback. Expected outputs manually reasoned; Markdown relative paths inspected. **Independent editorial review, comprehensive SQL syntax checks, and actual isolated PostgreSQL 18 runtime execution remain pending.** No runtime evidence collected.

## Chapter 016 publication evidence

- Chapter: [016](part-02-filtering/016-distinct-and-duplicate-handling.md); commit `da2b5aeadb8a9949eb5e087adfba2367aed3b3a4`.
- Lab: [016 SQL](labs/016-distinct-duplicate-handling.sql); commit `3e0adfb603108b5660bbd3fb1e8f4c86fd4518f3`.
- README navigation: commit `cf355ae9131e1abcfd2c55bb6ff17c70c0d2f387`.
- Chapter and lab fetched from GitHub `main` after creation. Targeted static checks: read-only transaction, inline synthetic data, PostgreSQL 18/database guard, deterministic expected counts, exact acceptance checks, rollback and relative navigation. **No independent editorial review, comprehensive SQL syntax verification, or actual isolated PostgreSQL 18 runtime execution was completed.** Runtime acceptance remains pending.

## Chapter 017 publication evidence

- Chapter: [017](part-02-filtering/017-order-by-and-deterministic-sorting.md); commit `96480970b248d7aa3ab7a5d30cf43a29cecc912d`.
- Lab: [017 SQL](labs/017-order-by-deterministic-sorting.sql); commit `0e1a0edfc0fb7e1cba0871a7e15d01d0773e69c6`.
- README navigation: commit `e1997e73b068214d730d0feb8a8808f353725ad0`.
- Both files were fetched from GitHub `main` after publication. Targeted static inspection checked synthetic inline values, read-only transaction, database/version assertion, deterministic expected ID arrays, rollback, and chapter-relative paths. Expected arrays were manually reasoned, **not executed**. Independent editorial review, comprehensive syntax checks and actual isolated PostgreSQL 18 runtime acceptance remain **pending**; no runtime evidence collected.

## Next work item

**091 — Read execution plans with EXPLAIN.** Begin Part 10; independent editorial review, comprehensive static QA, and isolated PostgreSQL 18 runtime acceptance remain pending.

## Quality gates

1. Before authoring, read current `main`, Master TOC, this tracker, and existing chapter files.
2. Do not overwrite existing chapters automatically or duplicate chapter numbers.
3. Review SQL syntax, expected outputs, Markdown paths, and safety instructions before publication.
4. Run PostgreSQL 18 examples in an isolated environment when available; retain command output/evidence and label validation correctly. When unavailable, record **runtime pending**, not **passed**.
5. Update this tracker after each confirmed GitHub publication; report exact commit and next unfinished chapter.
6. Continue through all 120 chapters without a manual `NEXT`. Stop advancing when the curriculum is complete or if a real safety, access, or correctness blocker prevents progress.

## Chapter 018 publication evidence

- Chapter: [018](part-02-filtering/018-limit-offset-fetch-and-top-across-dialects.md); published with commit `615cd870769c64c10170c621306c58571e4352cc`.
- Lab: [018 SQL](labs/018-limit-offset-fetch-top.sql); same commit `615cd870769c64c10170c621306c58571e4352cc`.
- README navigation updated in the same commit. GitHub `main` fetch verified the three files.
- Targeted static inspection: inline synthetic data, read-only transaction, timeout, rollback, environment assertion, expected result arrays, deterministic ordering and links. This is **not** comprehensive SQL syntax verification or independent editorial review.
- **Actual PostgreSQL 18 runtime execution: pending.** No isolated instance was run and no runtime evidence is claimed.
- **Next unfinished chapter:** 019 — CASE, COALESCE, and NULLIF.

## Chapter 019 publication evidence

- Chapter: [019](part-02-filtering/019-case-coalesce-and-nullif.md); commit `b81971eadd78bde98cd94129207787f2fca9940b`.
- Lab: [019 SQL](labs/019-case-coalesce-nullif.sql); commit `bf1ddd9f51ffe28fb699df654758b303726b1f6a`.
- README navigation: commit `f11057c7c3d2d3889bc1fbd3e2d4730cb1c9c0dc`.
- Chapter, lab, and README re-fetched from GitHub `main` before tracker update. Targeted static reasoning checked six synthetic events, NULL rate semantics, read-only transaction, version/database guard, timeout, exact assertions, and rollback. **Independent editorial review and comprehensive SQL syntax checks pending.**
- **Actual isolated PostgreSQL 18 runtime validation pending; no execution evidence was collected.**
- **Next unfinished chapter:** 020 — Lab 02: filter and rank operational records.

## Chapter 020 publication evidence

- Chapter: [020](part-02-filtering/020-lab-02-filter-and-rank-operational-records.md), commit `945e3c0db2f6684ad54505d731c476081e96d094`.
- Lab: [020 SQL](labs/020-lab-02-filter-and-rank-operational-records.sql), commit `e8fd8a331ca0da25f907c9d9353207da2f0f4b80`.
- README navigation commit `85768b25fb6ba58c873ab0fe61627f919aa8f1ce`.
- Chapter and lab were re-fetched from GitHub `main`. Targeted static reasoning reviewed six selected synthetic events, deterministic ranking, expected pagination arrays, service counts, read-only transaction, environment assertion, timeout and rollback. This is **not** independent editorial review or comprehensive SQL syntax verification.
- **PostgreSQL 18 runtime validation pending:** no isolated PostgreSQL 18 instance was executed and no reproducible runtime evidence was collected.
- Part 02 authored/published: 10/10. Next unfinished chapter: **021 — Entity relationships and conceptual data modeling**.

## Chapter 021 publication evidence

- Chapter: [021](part-03-modeling/021-entity-relationships-and-conceptual-data-modeling.md), commit `243a8fac8b11a6524585166532562638aeabdc45`.
- Lab: [021 SQL](labs/021-entity-relationships-conceptual-modeling.sql), commit `e1b94742c7d93acbb9c3f1ac20c146d05344ffb8`.
- README navigation commit `c6d7263cd5741e6299dca93ef335fd43ba891836`.
- Chapter and lab fetched from GitHub `main` after creation. Targeted static inspection confirmed synthetic inline datasets, PostgreSQL 18/database guard, read-only transaction, expected results and fail-closed assertions. This is not comprehensive SQL syntax verification or independent editorial review.
- **Actual isolated PostgreSQL 18 runtime validation pending**; no execution evidence obtained.
- **Next unfinished chapter:** 022 — CREATE DATABASE, CREATE SCHEMA, and CREATE TABLE.

## Chapter 022 publication evidence

- Chapter: [022](part-03-modeling/022-create-database-create-schema-and-create-table.md), commit `2739a5fb188f772b35d2146e9ceebe4d7542f491`.
- Lab: [022 SQL](labs/022-create-schema-and-tables-isolated.sql), commit `570c5080dff38feb9442b42d9d2ee04c3e72fe21`.
- README navigation commit `9b05fd209200a2697ead671e281f7032368a26f9`.
- Chapter and lab fetched from GitHub `main` after creation; README link verified before tracker update. Targeted static inspection reviewed version/database guard, pre-existing-schema refusal, transaction-scoped DDL, synthetic rows, count/amount assertions, foreign key metadata, ROLLBACK and post-rollback schema absence check. This is **not** independent editorial review or comprehensive syntax validation.
- **Actual isolated PostgreSQL 18 runtime validation: pending.** No PostgreSQL 18 execution or reproducible runtime evidence was obtained.
- **Next unfinished chapter: 023 — Choosing numeric, character, Boolean, and temporal types.**

## Chapter 023 publication evidence

- Chapter: [023](part-03-modeling/023-choosing-numeric-character-boolean-and-temporal-types.md); commit `dcafd32dfac87953ed8ae711784664feea70c2ff`.
- Lab: [023 SQL](labs/023-choosing-sql-data-types.sql); commit `2315ef338e922a7117728c812e0b230847bc0912`.
- README navigation commit `d418f895a1b95949241b25301be5e0b0b7600e9b`.
- All three files re-fetched from GitHub `main` before tracker update. Targeted static reasoning reviewed six synthetic records, exact amount total 91.45, NULL count 2, read-only transaction, PostgreSQL 18/database checks, timeout and rollback. This is **not** independent editorial review or comprehensive SQL syntax verification.
- **Actual isolated PostgreSQL 18 runtime validation: pending**; no execution evidence was collected.
- **Next unfinished chapter: 024 — Primary keys, natural keys, surrogate keys, and UNIQUE.**

## Chapter 024 publication evidence

- Chapter: [024](part-03-modeling/024-primary-keys-natural-keys-surrogate-keys-and-unique.md); commit `8ad6c848298676027fbea05d7e64ab07ea57aac9`.
- Isolated rollback-only lab: [024 SQL](labs/024-primary-natural-surrogate-unique.sql); commit `3dccc07552297f83660be16bfeb5a0513f74e711`.
- README navigation commit `e84e14fdeb7da80bc978c657e1942580cad8ce2f`.
- Both authored files were fetched from GitHub `main`; targeted static inspection covers transaction rollback, temporary synthetic tables, version/database guard, expected values, and duplicate-key assertions. Independent editorial review, comprehensive SQL syntax verification, and actual isolated PostgreSQL 18 runtime execution **remain pending**. No runtime evidence claimed.
- **Next:** Chapter 025 — Foreign keys and referential integrity.

## Chapter 025 publication evidence

- Chapter: [025](part-03-modeling/025-foreign-keys-and-referential-integrity.md); commit `b5d872555cc8992f4b68715d91d47c072536190d`.
- Isolated rollback-only lab: [025 SQL](labs/025-foreign-keys-referential-integrity.sql); commit `1b9547f597293d1447ef4769d4c49af14cce3954`.
- README navigation: commit `c935e4a4e1350cd9356e7a3f2dce9d92e35a458f`.
- Both authored artifacts were fetched from GitHub `main` after publication. Targeted static inspection covered synthetic data, guardrails, rollback, expected counts and foreign-key rejection handling. **Independent editorial review, comprehensive SQL syntax checks and actual PostgreSQL 18 runtime validation are pending.** No isolated PostgreSQL 18 execution evidence was obtained.
- Part 03: **5/10**; total: **25/120**. Next: **026 — NOT NULL, CHECK, DEFAULT, and constraint validation**.

## Chapter 026 publication evidence

- Chapter: [026](part-03-modeling/026-not-null-check-default-and-constraint-validation.md); commit `646a93e76740415fffebc847bb0c94b79c9e863a`.
- Isolated rollback-only lab: [026 SQL](labs/026-not-null-check-default-validation.sql); commit `315e9643e6c7bf41016e5279714cf47d1c6b80d7`.
- README navigation: commit `d96176eb7dfaad03c8c61d708aee0eb903b42074`.
- Chapter, SQL lab and README were fetched from GitHub `main` after publication. Targeted static inspection reviewed chapter links, synthetic row counts (3), defaulted values, expected SQLSTATEs 23502/23514, five synthetic legacy rows (3 invalid), environment guards, timeouts and rollback. These are reasoned checks, **not executed SQL**.
- **Independent editorial review: pending. Comprehensive SQL syntax verification: pending. Actual isolated PostgreSQL 18 runtime validation: pending.** No runtime evidence obtained.
- Part 03: **6/10**; total **26/120**; next unfinished chapter: **027 — Identity columns, sequences, and generated values**.

## Chapter 027 publication evidence

- Chapter: [027](part-03-modeling/027-identity-columns-sequences-and-generated-values.md); commit `bebac562009e524e6aae343c15d48fb511f77072`.
- Isolated rollback-only lab: [027 SQL](labs/027-identity-sequences-generated-values.sql); commit `5d67dade4b05f05ae7c66ff96286cef6b7bf0f47`.
- README navigation: commit `dc4847b52d4b9444e757ef06846465790ae18647`.
- Chapter, lab, and README fetched and verified from GitHub `main` before updating this tracker. Targeted static reasoning inspected identity ALWAYS/BY DEFAULT semantics, expected IDs (100,101,102,999 and 1,500), SQLSTATE 428C9, unique violation handling, generated total 46.75, temporary sequence values 10/15, version/database guard, transaction rollback and relative links. These are **not runtime test results**.
- **Independent editorial review: pending. Comprehensive SQL syntax verification: pending. Actual isolated PostgreSQL 18 runtime validation: pending.** No execution evidence collected.
- Part 03: **7/10**; total **27/120**; next unfinished chapter **028 — ALTER TABLE, rename operations, and safe schema changes**.

## Chapter 028 publication evidence

- Chapter: [028](part-03-modeling/028-alter-table-rename-operations-and-safe-schema-changes.md); commit `16c4b5c8da7b6e9eec328fa5360935eab63f5b44`.
- Isolated rollback-only lab: [028 SQL](labs/028-alter-table-safe-schema-changes.sql); commit `0744a00e4817a9d7f0a90511e68e5e7f7031eead`.
- README navigation: commit `5b5b56013180e08ae85e652f98fff8bf781333bc`.
- Both new files and README were fetched and verified from GitHub `main` before updating this tracker. Targeted static inspection reviewed chapter/lab paths, synthetic values (3 records, 24.75 total), default/backfill distinction, SQLSTATE classes for CHECK/UNIQUE, version/database guard, temporary objects, timeouts, and rollback. This is **not** an independent editorial review or comprehensive SQL syntax verification.
- **Independent editorial review: pending. Comprehensive SQL syntax verification: pending. Actual isolated PostgreSQL 18 runtime validation: pending.** No PostgreSQL 18 execution evidence obtained.
- Part 03: **8/10**; total **28/120**; next unfinished chapter **029 — Normalization (1NF–3NF) and intentional denormalization**.

## Chapter 029 publication evidence

- Chapter: [029](part-03-modeling/029-normalization-1nf-3nf-and-intentional-denormalization.md); commit `8df8ca0cb595e2bd9b87533789cd77b0755f3d76`.
- Read-only lab: [029 SQL](labs/029-normalization-1nf-3nf-denormalization.sql); commit `ff4db34435d0d3a1a6f66a3be13064ac463f6aec`.
- README navigation: commit `bd2770f8cb45ded6d2026a167625c4dccca07610`.
- Chapter and lab fetched from GitHub `main` after creation; targeted static reasoning reviewed synthetic cardinalities (2 customers, 2 products, 2 orders, 3 lines), expected total 85.00, stale cache drift 5.00, PostgreSQL 18/database guards, read-only transaction, fail-closed assertions, and rollback. This is **not** independent editorial review or comprehensive SQL syntax verification.
- **Independent editorial review: pending. Comprehensive SQL syntax verification: pending. Actual isolated PostgreSQL 18 runtime validation: pending.** No PostgreSQL 18 execution or reproducible runtime evidence obtained.
- Part 03: **9/10**; total **29/120**; next unfinished chapter **030 — Lab 03: design and build a normalized operational schema**.

## Chapter 030 publication evidence

- Chapter: [030](part-03-modeling/030-lab-03-design-and-build-a-normalized-operational-schema.md); commit `4d5f411bf827ee6cb1a728cb255b97f660a9d49d`.
- Lab: [030 SQL](labs/030-lab-03-normalized-operational-schema.sql); commit `08cfca4f45df1071e6b62c400e9807fab466dc2a`.
- README navigation: commit `4a05b6fcd0a80052924c1a33827f04ba23f3cb15`.
- Both new artifacts and README navigation re-fetched from GitHub `main`. Targeted static inspection: four synthetic temporary tables, PK/FK/UNIQUE/CHECK constraints, database/version/standby guard, timeouts, rollback, expected counts and revenue reconciliation (85.00). Relative paths reviewed. **Independent editorial review and comprehensive SQL syntax verification remain pending. No isolated PostgreSQL 18 instance was executed and no runtime evidence was collected.**
- Part 03 authored/published: **10/10**; not runtime certified.

## Chapter 031 publication evidence

- Chapter: [031](part-04-data-modification/031-insert-single-row-and-multi-row-records.md); commit `c7d2dbd5956ba8abcb838d655ec2464c648467bf`.
- Isolated rollback-only lab: [031 SQL](labs/031-insert-single-row-and-multi-row-records.sql); commit `2eb1b699fdbdbd4af8346a0b3e72f97b14b1a560`.
- README navigation commit `739fe267b72fbbefca124744736280dc5d2e8a79`.
- Both files and README navigation re-fetched from GitHub `main` after publication. Targeted static inspection covered version/database/standby guard, synthetic values, three expected constraint failures, transaction rollback, count 3 and sum 39.75, and relative links. **This is not comprehensive SQL syntax verification or independent editorial review.**
- **Independent editorial review: pending. Comprehensive SQL syntax verification: pending. Actual isolated PostgreSQL 18 runtime validation: pending.** No PostgreSQL 18 instance was executed or runtime evidence retained.
- Part 04: **1/10**; total **31/120**; next unfinished chapter **032 — INSERT ... SELECT and bulk-loading fundamentals**.

## Chapter 032 publication evidence

- Chapter: [032](part-04-data-modification/032-insert-select-and-bulk-loading-fundamentals.md); commit `0ce801a64c31b6310a0709e16f89eb3fc67ac32f`.
- Isolated rollback-only PostgreSQL 18 lab: [032 SQL](labs/032-insert-select-bulk-loading.sql); commit `fb26329adb4d58adac56ba0192d57c080d82ffd0`.
- README navigation commit `91d740252b2343aee32aef5053420cadcef7e704`.
- Chapter and lab re-fetched from GitHub main before tracker update. Targeted static reasoning checked five synthetic source events, accepted IDs EV-101/102/104, three accepted, two rejected, total 39.75, version/database/standby guard, timeouts and ROLLBACK. This does **not** constitute comprehensive SQL syntax verification.
- **Independent editorial review: pending. Comprehensive SQL syntax verification: pending. Actual isolated PostgreSQL 18 runtime validation: pending.** No PostgreSQL 18 instance was executed and no runtime evidence collected.
- Part 04: **2/10**; total **32/120**; next unfinished chapter **033 — UPDATE with safe predicates and preview queries**.

## Chapter 033 publication evidence

- Chapter: [033](part-04-data-modification/033-update-with-safe-predicates-and-preview-queries.md); commit `6623c98265a31464fa420a3a04146b2b1e6e0d93`.
- Isolated rollback-only PostgreSQL 18 lab: [033 SQL](labs/033-update-safe-predicates-preview.sql); commit `a89a5d23f3b4e39c779c04309f8b9454cc8a0f14`.
- README navigation commit `20e08e70f57af6b76947d095b72b65712c8de482`.
- Chapter and lab were re-fetched from GitHub `main` after publication. Targeted static reasoning reviewed four synthetic events, exact candidate key EV-102, before/after row identities, 2 pending/2 reviewed, total 44.75, version/database/standby checks, temporary objects, timeouts and ROLLBACK. Relative link targets were checked against known repository paths. This is **not** comprehensive SQL syntax verification or independent editorial review.
- **Independent editorial review: pending. Comprehensive SQL syntax verification: pending. Actual isolated PostgreSQL 18 runtime validation: pending.** No PostgreSQL 18 execution evidence collected.
- Part 04: **3/10**; total **33/120**; next unfinished chapter **034 — DELETE with safe predicates and referential implications**.


## Chapter 034 publication evidence — 2026-11-09

- [Chapter 034 — DELETE with safe predicates and referential implications](part-04-data-modification/034-delete-with-safe-predicates-and-referential-implications.md), commit `845ccb5a0d41e457d657a62a7e3a66f070853867`.
- [PostgreSQL 18 rollback-only lab](labs/034-delete-safe-predicates-referential-implications.sql), commit `c5da8654414ceb2bec4e70a0d3d8a1a7e94ce82e`.
- README navigation commit `b31600f299bfe0a49a7145a05c1bf25d0e4b1b24`.
- Chapter and lab re-fetched from GitHub main. Targeted static inspection: synthetic temporary parent/child tables, guarded PostgreSQL 18 database/version, pre-delete exact ID assertion, DELETE RETURNING capture, expected foreign-key rejection, post-delete IDs/counts/orphan assertions, ROLLBACK. Relative paths checked against repository layout.
- **Authored/published: 34/120 (28.3%); remaining: 86. Part 04: 4/10.** Independent editorial review: **pending**. Comprehensive SQL syntax checks: **pending**. Actual isolated PostgreSQL 18 runtime execution and reproducible evidence: **pending**. No runtime certification claimed.
- **Next:** Chapter 035 — DELETE versus TRUNCATE versus DROP.

## Chapter 035 publication evidence — 2026-11-09

- [Chapter 035 — DELETE versus TRUNCATE versus DROP](part-04-data-modification/035-delete-versus-truncate-versus-drop.md), commit `9eda0adecbd64f1c4ad298905f0375bbb9ccf258`.
- [PostgreSQL 18 rollback-only synthetic lab](labs/035-delete-truncate-drop.sql), commit `1b7cd5f48df8f02665bf95a2595e98b07f208fe3`.
- README navigation commit `cb13819bb943e563e6a7ab250c0e262d1aef289f`.
- Both new files and README re-fetched from GitHub main. Targeted static inspection: database/version/standby guard, synthetic temporary data, exact DELETE candidate and affected-key checks, TRUNCATE row-count/table-presence checks, DROP absence assertion, conservative timeouts and ROLLBACK. Link paths checked against known chapter/lab locations. This does not establish comprehensive SQL syntax correctness or independent review.
- **Authored/published: 35/120 (29.2%); remaining: 85. Part 04: 5/10.** Independent editorial review: **pending**. Comprehensive SQL syntax verification: **pending**. Actual isolated PostgreSQL 18 runtime validation and reproducible evidence: **pending**; no execution performed.
- **Next:** Chapter 036 — UPSERT and MERGE patterns across SQL dialects.

## Chapter 036 publication evidence — 2026-11-09

- [Chapter 036 — UPSERT and MERGE patterns across SQL dialects](part-04-data-modification/036-upsert-and-merge-patterns-across-sql-dialects.md), commit `e8e7c5a5e7a6ea694d034d2b4fe5f87dbb168db1`.
- [PostgreSQL 18 isolated rollback-only SQL lab](labs/036-upsert-merge-patterns.sql), commit `36dc923073b8a0152d70c8047fcd456d22ed2171`.
- README navigation commit `b682e36c9559f20267d9d84b6f24e968ac1dcdd4`.
- All three files re-fetched from GitHub `main` before tracker update. Targeted static reasoning checked synthetic keys and version-guarded conflict updates, MERGE reconciliation (4 SKUs, quantity sum 31), repeatability, version/database/standby guard, timeouts, temp tables, and ROLLBACK. Relative links reviewed. This is **not** comprehensive SQL syntax validation or independent editorial review.
- **Authored/published: 36/120 (30.0%); remaining: 84; Part 04: 6/10.** Independent editorial review: **pending**. Comprehensive SQL syntax verification: **pending**. Actual isolated PostgreSQL 18 runtime execution: **pending**; no runtime evidence collected.
- **Next:** Chapter 037 — RETURNING, OUTPUT, and write verification.

## Chapter 037 publication evidence — 2026-11-09

- [Chapter 037 — RETURNING, OUTPUT, and write verification](part-04-data-modification/037-returning-output-and-write-verification.md), commit `f15db09a1a2a7e7b5a2b2b6d00e23d6dd72190c0`.
- [PostgreSQL 18 rollback-only SQL lab](labs/037-returning-output-write-verification.sql), commit `cb8705f273ba302ff6a3d9bd8bb048bed65587d1`.
- README navigation commit `5c6ccd45e8006e5f54a6bff953dec3de7a1a23e4`.
- Chapter and lab re-fetched from GitHub main. Targeted static reasoning checked synthetic payments, expected UPDATE/INSERT/DELETE counts, reconciliation (3 rows; amount 41.75), PostgreSQL 18 guard, timeouts, temporary objects and ROLLBACK. **Not** an independent editorial review or comprehensive syntax check.
- **Authored/published: 37/120 (30.8%); remaining: 83; Part 04: 7/10.** Independent editorial review: **pending**. Comprehensive SQL syntax verification: **pending**. Actual isolated PostgreSQL 18 runtime validation: **pending**; no reproducible execution evidence collected.
- **Next:** Chapter 038 — BEGIN, COMMIT, ROLLBACK, and SAVEPOINT.

## Chapter 038 publication evidence — 2026-11-09

- [Chapter 038 — BEGIN, COMMIT, ROLLBACK, and SAVEPOINT](part-04-data-modification/038-begin-commit-rollback-and-savepoint.md), authored commit `045ec248340efd9c7b5bb16186914ed3be7bfa07`; link correction commit `bdf7c8356b5dc2ad8007388779e0ff9e78e98a5c`.
- [PostgreSQL 18 rollback-only SQL lab](labs/038-begin-commit-rollback-savepoint.sql), commit `e9aacdf8ed8f69b40f059b65a14d7d8381a46085`.
- README navigation commit `7bbdae9d71fdf047542eefd180862a3257e87254`.
- All three artifacts re-fetched from GitHub `main` before tracker update. Targeted static reasoning checked the two synthetic balances, conserved total (150.00), savepoint rollback, version/database/standby guard, temporary table, timeout settings, and outer rollback. No independent editorial review or comprehensive SQL syntax verification performed.
- **Authored/published: 38/120 (31.7%); remaining: 82; Part 04: 8/10.** Independent editorial review: **pending**. Actual isolated PostgreSQL 18 runtime execution: **pending**; no reproducible execution evidence collected.
- **Next:** Chapter 039 — Isolation levels and common transaction anomalies.

## Chapter 039 publication checkpoint

- [Chapter 039](part-04-data-modification/039-isolation-levels-and-common-transaction-anomalies.md) and [read-only lab](labs/039-isolation-levels-transaction-anomalies.sql) authored and published; targeted static reasoning only.
- Independent editorial review: pending. Comprehensive SQL syntax/static QA: pending. Actual PostgreSQL 18 runtime validation: pending (no isolated execution evidence).
- Next unfinished chapter: **040 — Lab 04: Complete a Safe, Auditable Transaction Workflow**.


## Latest milestone — Chapter 040

- Chapter and isolated rollback-only SQL lab published and re-fetched on GitHub main; Part 04 complete (40/120).
- Targeted static reasoning performed. **Independent editorial review: pending. Comprehensive static QA: pending. PostgreSQL 18 runtime execution: not performed; evidence pending.**
- Next unfinished chapter per Master TOC: **041 — Join fundamentals and relationship cardinality** (Part 05).

## Chapter 041 publication checkpoint — 2026-11-09

- [Chapter 041 — Join fundamentals and relationship cardinality](part-05-joins/041-join-fundamentals-and-relationship-cardinality.md): commit `3a0edc076e3690fe074d8503ea047e34ec038cd9`.
- [PostgreSQL 18 isolated rollback-only lab](labs/041-join-fundamentals-cardinality.sql): commit `76d86021c72e5a9a2676787cd30b6fab233797d6`.
- README navigation: commit `f5db77be55507d88f4cb9fd56fda799360b91c67`.
- All three artifacts re-fetched from GitHub main before this tracker update. Targeted static inspection reviewed join keys, synthetic counts (3 customers, 3 orders, 3 inner rows, 4 left rows, 4 line-item rows), revenue 65.00, temporary tables, database/version/standby guard and rollback. **Not independently editorially reviewed; comprehensive SQL syntax and link QA pending; no actual isolated PostgreSQL 18 execution or retained runtime evidence.**
- **Published 41/120 (34.2%), 79 remaining, Part 05 1/10. Next: 042 — INNER JOIN: matched records.**

## Chapter 042 publication checkpoint — 2026-11-09

- [Chapter 042 — INNER JOIN: matched records](part-05-joins/042-inner-join-matched-records.md): commit `ebf8fa8824a1e61c84af78415778d2ede2f01a5f`.
- [PostgreSQL 18 isolated rollback-only lab](labs/042-inner-join-matched-records.sql): commit `0a0418c12c4b529b9bef7b93592f5504be0a8127`.
- README navigation: commit `33e5a0506aab656c59e02cfcf96468aaab5174a7`.
- Chapter and lab re-fetched from GitHub main; targeted static reasoning checked synthetic join results, count/amount conservation, version/database guard, temporary tables and rollback. **Independent editorial review pending; comprehensive static syntax and link QA pending; actual PostgreSQL 18 runtime validation not performed and no execution evidence retained.**
- **Published 42/120 (35.0%), 78 remaining, Part 05 2/10. Next: 043 — LEFT OUTER JOIN: preserve unmatched left rows.**

## Chapter 043 publication checkpoint — 2026-11-10

- [Chapter 043 — LEFT OUTER JOIN](part-05-joins/043-left-outer-join-preserve-unmatched-left-rows.md): commit `9219c4e332bef04de436adac451e3070f613e5ec`.
- [Isolated PostgreSQL 18 SQL lab](labs/043-left-outer-join-unmatched-rows.sql): commit `7cd9ac88e1bd2379435d1a92e706dd70fd2427fa`.
- README navigation: commit `3d3dd3bd7d71213756c1305fa9728171ea3c3906`.
- Chapter and lab fetched from GitHub main after creation; README link fetched and confirmed. Targeted static reasoning reviewed source 4/74.00, left 4/74.00, matched 3/65.00, unmatched 1/9.00, ON vs WHERE 4 vs 2, customer-left 4, synthetic temporary tables, version/database guard, transaction timeouts, assertions, and rollback. This is **not** independent editorial review or comprehensive SQL syntax/link QA.
- **Actual PostgreSQL 18 execution: not performed; no reproducible runtime evidence.** Runtime acceptance pending.
- **Published 43/120 (35.8%), 77 remaining, Part 05 3/10. Next: 044 — RIGHT and FULL OUTER JOIN: applicability and portability.**

## Chapter 044 publication checkpoint — 2026-11-10

- [Chapter 044 — RIGHT and FULL OUTER JOIN](part-05-joins/044-right-and-full-outer-join-applicability-and-portability.md): commit `70cf14948c6de803aa1d0eb77b81e86266fce60f`.
- [Isolated PostgreSQL 18 SQL lab](labs/044-right-full-outer-join.sql): commit `5b92d218ccca49b25a7ccc0a0b89bece61938be9`.
- README navigation: commit `8bf387464b8c1fb4760c668e6a234c644a8fed26`.
- Chapter, lab, and README re-fetched from GitHub main. Targeted static reasoning checked fixture arithmetic (A 3/59.00, B 3/54.00, FULL 4, matched 2, A-only 1, B-only 1), RIGHT/LEFT equivalence, key uniqueness, PostgreSQL version/database/standby guard, timeouts, temporary tables and final rollback. **Not independently editorially reviewed; comprehensive syntax and link QA pending. Actual isolated PostgreSQL 18 runtime execution not performed; no retained runtime evidence.**
- **Published 44/120 (36.7%), 76 remaining, Part 05 4/10. Next: 045 — CROSS JOIN and SELF JOIN.**

## Chapter 045 publication evidence

- [Chapter 045](part-05-joins/045-cross-join-and-self-join.md): commit `51c2828cb610bd6f2a7e93f5c010c99c92bce64f`.
- [PostgreSQL 18 lab](labs/045-cross-join-self-join.sql): commit `ab6084efce7a98c9ce2b0cb7d4eb7a2069d9959a`.
- README navigation: commit `e66b24edbf1e9e38593be6237e68781d31171204`.
- Chapter, lab and README fetched from GitHub main; fixture/cardinality assertions reviewed by static reasoning. **Independent editorial review pending; comprehensive static SQL/link QA pending; PostgreSQL 18 runtime execution not performed, evidence pending.**
- **Published 45/120 (37.5%); 75 remaining; Part 05 5/10. Next: Chapter 046 — Multi-table joins and join condition design.**

## Chapter 046 publication evidence (2026-11-10)

- [Chapter 046](part-05-joins/046-multi-table-joins-and-join-condition-design.md): commit `f1d878b607ff05f3e04e0dd6afd51ce32f05e6a9`.
- [Lab 046](labs/046-multi-table-joins-condition-design.sql): commit `18abddd3cfe2e4a51e30d0f9e4d906f889c35bdf`.
- [README navigation](README.md): commit `5fa2c0b62903e5de69d7703a2e9e5dea8f0cb76d`.
- Both new files re-fetched from GitHub `main`. Targeted static reasoning inspected joins, fixture totals, assertions, temporary-table isolation and rollback. **No independent editorial review, comprehensive syntax/link QA, or actual PostgreSQL 18 runtime execution completed.** Runtime evidence pending.
- **Next:** Chapter 047 — One-to-many and many-to-many relationships.

## Chapter 047 publication evidence (2026-11-10)

- [Chapter 047](part-05-joins/047-one-to-many-and-many-to-many-relationships.md): commit `b850bafed28bc11a9a8dc390dfb6742affd43c10`.
- [PostgreSQL 18 lab](labs/047-one-to-many-many-to-many.sql): commit `c624143b6e0fbcd496ed189052584c0ea09b8d5b`.
- [README navigation](README.md): commit `70cb718a279e5b3a013373ded8120ad07ee5f470`.
- Chapter and lab fetched back from GitHub main; targeted static reasoning checked fixture counts, join cardinality, customer and tag totals, uniqueness assertions, transaction guard and rollback. **No independent editorial review, comprehensive automated syntax/link QA, or isolated PostgreSQL 18 runtime execution completed.** No runtime evidence retained.
- **Published 47/120 (39.2%), 73 remaining; Part 05 7/10. Next: Chapter 048 — Semi-joins and anti-joins using EXISTS and NOT EXISTS.**

## Chapter 048 publication evidence (2026-11-10)

- [Chapter 048](part-05-joins/048-semi-joins-and-anti-joins-using-exists-and-not-exists.md): commit `3b05be658cd1bbae5c2806be47b6650a3c521858`.
- [PostgreSQL 18 lab](labs/048-exists-not-exists-semi-anti-joins.sql): commit `23a212d5ed428be0f873b3603bbc0b5d45ab13f9`.
- [README navigation](README.md): commit `c9dd41006da7f54380fd03f1af4fa4a1a6611933`.
- Chapter and lab fetched back from GitHub main, README navigation fetched and verified. Targeted static reasoning checked correlated EXISTS/NOT EXISTS, NULL-sensitive NOT IN, synthetic fixture counts, transaction guard and rollback. **Independent editorial review pending; comprehensive automated SQL syntax/link QA pending; actual isolated PostgreSQL 18 execution not performed and runtime evidence not retained.**
- **Published 48/120 (40.0%), 72 remaining; Part 05 8/10. Next: Chapter 049 — Diagnose duplicate rows, fan-out, and NULL join pitfalls.**

## Chapter 049 publication evidence (2026-11-10)

- [Chapter 049](part-05-joins/049-diagnose-duplicate-rows-fan-out-and-null-join-pitfalls.md): commit `17f624489d3ff2758c62e898ce7bd9e8e2a4760f`.
- [Isolated PostgreSQL 18 lab](labs/049-duplicate-rows-fanout-null-join-pitfalls.sql): commit `5a577943c0b1c9f5006a40469e805b4dd47caf91`.
- [README navigation](README.md): commit `25e574f2650eb547683c468b73265fcfcff64d64`.
- Both new files were re-fetched from GitHub main. Targeted static reasoning checked three-order 90.00 source total, six-row multi-child fan-out and incorrect 210.00 sum, safe one-row-per-order preaggregation, NULL orphan detection, duplicate staging key check, PostgreSQL version/database guard, temporary objects, timeouts, and rollback. **Independent editorial review and comprehensive SQL syntax/link QA pending. Actual isolated PostgreSQL 18 execution not performed; no reproducible runtime evidence.**
- **Published 49/120 (40.8%), 71 remaining; Part 05 9/10. Next: Chapter 050 — Lab 05: consolidate customers, orders, and payments.**

## Chapter 050 publication evidence (2026-11-10)

- [Chapter 050](part-05-joins/050-lab-05-consolidate-customers-orders-and-payments.md): commit `5ba65fb85aa794e4c72b97f5caeb1a26112bd127`.
- [Isolated PostgreSQL 18 lab](labs/050-lab-05-consolidate-customers-orders-payments.sql): commit `8e238e8cb93646a4b25cb35774ab629e6f78644d`.
- [README navigation](README.md): commit `bae99124e0cb54b76cee538ae9f86611517820e0`.
- Both new files and README link re-fetched from GitHub main. Targeted static reasoning checked synthetic order/payment sums, 6-row fan-out, 5-row order grain, NULL customer preservation, zero-payment order, fail-closed guards and rollback. **Not independently editorially reviewed; comprehensive static SQL syntax/link QA pending; no isolated PostgreSQL 18 execution or runtime evidence.**
- **Published 50/120 (41.7%), 70 remaining; Part 05 complete 10/10. Next: Chapter 051 — COUNT, SUM, AVG, MIN, and MAX.**

## Chapter 051 publication evidence (2026-11-10)

- [Chapter 051](part-06-aggregation/051-count-sum-avg-min-and-max.md): commit `65d0d2dc547c865e25a5baa0ab205c50a2b36e0e`.
- [Isolated PostgreSQL 18 lab](labs/051-count-sum-avg-min-max.sql): commit `f785880398a043b490c9f94a0195108f959e524c`.
- [README navigation](README.md): commit `520fbe4fe34ffcd0737a7d44fec3c8b4a65caca5`.
- Chapter, lab, and README re-fetched from GitHub `main`. Targeted static reasoning checked five synthetic payment events, four non-NULL amounts, one missing amount, four distinct orders, sum 100.00, AVG 25.00, min 10.00, max 40.00, zero-filled AVG 20.00, empty-input aggregate behavior, version/database guard, temporary table, timeouts, and rollback. This is **not** an independent editorial review or comprehensive automated SQL syntax/link QA. **Actual isolated PostgreSQL 18 runtime execution not performed; no runtime evidence retained.**
- **Published 51/120 (42.5%), 69 remaining; Part 06 1/10. Next: Chapter 052 — GROUP BY and aggregation grain.**

## Chapter 052 publication evidence (2026-11-10)

- [Chapter 052](part-06-aggregation/052-group-by-and-aggregation-grain.md): commit `767655fe57400b2b9aff76903e8122fe5b7055e9`.
- [Isolated PostgreSQL 18 lab](labs/052-group-by-aggregation-grain.sql): commit `f78e8c6d10d14020de34a8c289ee6386959ecb8b`.
- [README navigation](README.md): commit `d42a9249f3ff80da4764511585db2b5655df69fa`.
- Chapter and lab were re-fetched from GitHub `main`. Targeted static reasoning checked 7 synthetic events, 6 non-NULL amounts, 5 region/status groups, 3 region groups, 78.00 reconciled total, NULL grouping and aggregation behavior, version/database guard, temporary fixture, timeouts, and rollback. **Not independently editorially reviewed; comprehensive automated SQL syntax/link QA pending; actual isolated PostgreSQL 18 execution not performed and no runtime evidence retained.**
- **Published 52/120 (43.3%), 68 remaining; Part 06 2/10. Next: Chapter 053 — HAVING versus WHERE.**

## Chapter 053 publication evidence (2026-11-10)

- [Chapter 053](part-06-aggregation/053-having-versus-where.md): commit `e268eb9980bb0be6b2b7a5c6647285055b9677a7`.
- [Isolated PostgreSQL 18 lab](labs/053-having-versus-where.sql): commit `bfb85b8efcc261efcf835100ccdb6dc05b9e5297`.
- [README navigation](README.md): commit `fcff93c2e4d22c159d2b6bac4022131ff743a730`.
- Chapter and lab were re-fetched from GitHub `main`; README link re-fetched. Targeted static reasoning checked 10 synthetic events, 9 non-NULL amounts, all-status net 143.00, 7 captured events totaling 143.00, qualifying North 2/60.00 and West 2/45.00, report total 105.00, excluded captured total 38.00, NULL pending behavior, PostgreSQL 18/database guard, temporary table, timeouts and rollback. **Independent editorial review pending; comprehensive automated SQL syntax/link QA pending; actual isolated PostgreSQL 18 runtime execution not performed and no runtime evidence retained.**
- **Published 54/120 (45.0%), 66 remaining; Part 06 3/10. Next: Chapter 054 — Conditional aggregation with CASE and FILTER.**

## Chapter 054 publication evidence (2026-11-10)

- [Chapter 054](part-06-aggregation/054-conditional-aggregation-with-case-and-filter.md): commit `86779f7e61abbd403c42e26474935c94950ad42b`.
- [Isolated PostgreSQL 18 lab](labs/054-conditional-aggregation-case-filter.sql): commit `341723b3f4c40ca68a801b4c0c6ee4e593d208d1`.
- [README navigation](README.md): commit `c21ebad3df8b36ce3be616e62cdbfbe18c738918`.
- Chapter and lab re-fetched from GitHub `main`; README navigation re-fetched. Targeted static reasoning checked 12 synthetic events, 8 known amounts, 6 captured events, 2 refunds, 4 pending, captured total 125.00, refunds -15.00, pending 15.00, five region groups, missing captured amount, CASE/FILTER parity, version/database guard, temporary fixture, transaction-local timeouts, and rollback. **Not independently editorially reviewed; comprehensive automated SQL syntax/link QA pending; actual isolated PostgreSQL 18 execution not performed and no runtime evidence retained.**
- **Published 54/120 (45.0%), 66 remaining; Part 06 4/10. Next: Chapter 055 — Date-based grouping and time buckets.**

## Chapter 055 publication evidence (2026-11-10)

- [Chapter 055](part-06-aggregation/055-date-based-grouping-and-time-buckets.md): commit `80f0083ee9873b0804995a4e3b49ded162954d56`.
- [Isolated PostgreSQL 18 lab](labs/055-date-based-grouping-time-buckets.sql): commit `8c714a74d7fa4340c8d1de3b3cb9d987d7cb25ac`.
- [README navigation](README.md): commit `201899316130f076b8b1b11c541b7dab3ef6e179`.
- Chapter, lab, and README re-fetched from GitHub `main`. Targeted static reasoning checked six UTC events, January 1/10.00, February 3/90.00, March 2/110.00, source total 210.00, February half-open filter, New York local boundary, PostgreSQL 18/database guards, temporary fixture, transaction-local timeouts, and rollback. **Independent editorial review and comprehensive automated SQL syntax/link QA pending. Actual isolated PostgreSQL 18 execution not performed; no reproducible runtime evidence.**
- **Published 55/120 (45.8%), 65 remaining; Part 06 5/10. Next: Chapter 056 — Text transformations for reporting.**

## Chapter 056 publication evidence (2026-11-10)

- [Chapter 056](part-06-aggregation/056-text-transformations-for-reporting.md): commit `88c95e9715953b4711fca420ce5087b4df1c6942`.
- [Isolated PostgreSQL 18 lab](labs/056-text-transformations-for-reporting.sql): commit `c2b89adc60f4dceef4fe004fd89d18333e98ac26`.
- [README navigation](README.md): commit `11bd48cdb83526266f7c409d7ec45e3130384736`.
- Chapter and lab re-fetched from GitHub `main`; README navigation re-fetched. Targeted static reasoning checked six synthetic events, normalized region counts and totals (NORTH 2/50.00, SOUTH 2/55.00, UNKNOWN 1/10.00, WEST 1/5.00), status totals (CAPTURED 4/100.00, PENDING 1/15.00, UNKNOWN 1/5.00), source reconciliation 6/120.00, NULL/blank distinction, temporary fixture, version/database guard, transaction-local timeouts and rollback. **Independent editorial review pending; comprehensive automated SQL syntax/link QA pending; actual isolated PostgreSQL 18 execution not performed and no runtime evidence retained.**
- **Published 56/120 (46.7%), 64 remaining; Part 06 6/10. Next: Chapter 057 — Numeric rounding, ratios, and safe division.**

## Chapter 057 publication evidence (2026-11-10)

- [Chapter 057](part-06-aggregation/057-numeric-rounding-ratios-and-safe-division.md): commit `452811babdb6e80d280b77ca7e9e63d89ffc754e`.
- [Isolated PostgreSQL 18 lab](labs/057-numeric-rounding-ratios-safe-division.sql): commit `b231bc113fa2e7f6c89b9928f0b3967ae8119fb7`.
- [README navigation](README.md): commit `412d4184177e1c3c754be55fd4456c87115522c7`.
- Chapter and lab re-fetched from GitHub `main`; README navigation re-fetched. Targeted static reasoning checked five synthetic batches, source totals (164 accepted, 36 rejected, 200 processed), claims 125/150 = 83.33%, events 39/50 = 78.00%, overall 82.00%, unweighted batch average 83.75%, NULL for zero-volume batch, exact numeric cast, temporary fixture, version/database guard, transaction-local timeouts and rollback. **Independent editorial review pending; comprehensive automated SQL syntax/link QA pending; actual isolated PostgreSQL 18 runtime execution not performed and no reproducible runtime evidence retained.**
- **Published 57/120 (47.5%), 63 remaining; Part 06 7/10. Next: Chapter 058 — ROLLUP, CUBE, and GROUPING SETS.**

## Chapter 058 publication evidence (2026-11-10)

- [Chapter 058](part-06-aggregation/058-rollup-cube-and-grouping-sets.md): initial commit `5a8ca1ed70a3fc85a4d89e8c5bcf705c7580208a`; clarification commit `f3e531ec78ec92fa201298f9eb7a786de47a1aac`.
- [Isolated PostgreSQL 18 lab](labs/058-rollup-cube-grouping-sets.sql): commit `d1f3c36e80da70b2f2e18f482567e961e2942543`.
- [README navigation](README.md): commit `c0cd60ad4259748f27fbe7a835439628171eace3`.
- Chapter, lab and README navigation re-fetched from GitHub `main`. Targeted static reasoning checked six synthetic records, 155.00 total, five detail groups, three region subtotals, two channel subtotals, 9 ROLLUP rows, 11 CUBE rows, 9 explicit grouping-set rows, real NULL region semantics, version/database guard, transaction-local timeouts, and rollback. **Not independently editorially reviewed; comprehensive automated SQL syntax/link QA pending; actual isolated PostgreSQL 18 execution not performed and no reproducible runtime evidence retained.**
- **Published 58/120 (48.3%), 62 remaining; Part 06 8/10. Next: Chapter 059 — Pivoting and unpivoting — portable and vendor features.**

## Chapter 059 publication evidence (2026-11-10)

- [Chapter 059](part-06-aggregation/059-pivoting-and-unpivoting-portable-and-vendor-features.md): commit `197acfbf397fe97d0c5d0b76d5cf91bd6f6b6d48`.
- [Isolated PostgreSQL 18 lab](labs/059-pivoting-unpivoting-portable-vendor.sql): commit `fcaa57c1e5e79eba51792a4c4aa4bbac2cac3adf`.
- [README navigation](README.md): commit `4b7f16cbac83b8e15222900f8aa3eace529a31b3`.
- Chapter and lab fetched back from GitHub `main`; README navigation fetched back. Targeted static reasoning checked eight synthetic events totaling 180.00, three region pivot rows (East 60.00, North 25.00, West 95.00), web 85.00, store 95.00, six unpivoted region/channel rows totaling 180.00, category allowlist checks, PostgreSQL 18/database guard, temporary fixture, transaction-local timeouts, and rollback. **Independent editorial review pending; comprehensive automated SQL syntax/link QA pending; actual isolated PostgreSQL 18 execution not performed, with no reproducible runtime evidence retained.**
- **Published 59/120 (49.2%), 61 remaining; Part 06 9/10. Next: Chapter 060 — Lab 06: build a monthly KPI report.**

## Chapter 060 publication evidence (2026-11-10)

- [Chapter 060](part-06-aggregation/060-lab-06-build-a-monthly-kpi-report.md): commit `17f41f10f40e806b129f287b6e43bb7cca42b013`.
- [Isolated rollback-only PostgreSQL 18 lab](labs/060-lab-06-monthly-kpi-report.sql): commit `9af145de1cbc36313240808b5d95a17b22710c43`.
- [README navigation](README.md): commit `e7ab9e761bae42ee7d1507a2dea8fbeeba26f2fe`.
- Chapter, lab, and README were fetched back from GitHub `main`. Targeted static arithmetic and structural inspection: 8 synthetic batches, accepted 380, rejected 60, processed 440, overall acceptance 86.36%; monthly processed January 150, February 100, March 190; source breakdown API 280/file 160; zero-denominator handling, UTC boundaries, transaction-local timeouts, temporary fixture, and rollback. **No independent editorial review; comprehensive automated SQL syntax/link QA pending; no actual PostgreSQL 18 runtime execution or reproducible runtime evidence.**
- **Published 60/120 (50.0%), 60 remaining; Part 06 complete (10/10). Next: Chapter 061 — Scalar subqueries and derived tables (Part 07).**

## Chapter 061 publication evidence

- Chapter: [061](part-07-subqueries/061-scalar-subqueries-and-derived-tables.md); commit `ca414ba59a0838e14178487155ad9c1a8827840c`.
- Lab: [061 SQL](labs/061-scalar-subqueries-derived-tables.sql); commit `9a514a8ca3589a5576a84def6c674f80fb726bc5`.
- README navigation commit `72820a33310f19ff40a952b726942f495ba73371`.
- Chapter, lab and README fetched from GitHub `main`; targeted static reasoning completed. **Independent editorial review, comprehensive automated syntax/link QA, and actual isolated PostgreSQL 18 runtime validation pending.** No execution evidence was collected.
- **Next:** 062 — IN, ANY, ALL, and multi-row subqueries.

## Chapter 062 publication evidence (2026-11-10)

- [Chapter 062](part-07-subqueries/062-in-any-all-and-multi-row-subqueries.md): commit `a335a7cc1cb98e29814b63ee4e7d40770e7254d9`.
- [Synthetic read-only PostgreSQL 18 lab](labs/062-in-any-all-multi-row-subqueries.sql): commit `84962bb53f518fca1b2b80b24d70fcfdc1f634b6`.
- README navigation: commit `60204ccb44de642ebca4666d0aa81d93f65901cb`.
- Both new artifacts were fetched back from GitHub `main` before tracker update. Targeted static reasoning checked six batches, five known processed values totaling 290, membership IDs 1/2/5/6, ANY IDs 1/2/3, ALL ID 1, NULL-sensitive NOT IN, empty-set semantics, read-only transaction, PostgreSQL 18/database guards, timeouts, fail-closed acceptance and rollback. **No independent editorial review, no comprehensive automated SQL syntax/link QA, and no actual isolated PostgreSQL 18 execution or retained runtime evidence.**
- **Published 62/120 (51.7%), 58 remaining; Part 07 2/10. Next: Chapter 063 — EXISTS versus IN and NULL-sensitive behavior.**

## Chapter 063 publication evidence (2026-11-10)

- [Chapter 063](part-07-subqueries/063-exists-versus-in-and-null-sensitive-behavior.md): initial commit `23159745efeab6a3522ad4c6fdb2490fdcc9093f`; clarification commit `03db0dee36fded7df5eb4bc95a21113c37ced8c1`.
- [Read-only PostgreSQL 18 lab](labs/063-exists-versus-in-null-sensitive.sql): commit `6fba3ef2d4b9f942ea65915e9e041f77c712d48d`.
- [README navigation](README.md): commit `ce06e8201a947629f9de8a6d3e848fbdde93e57a`.
- Chapter, lab and README re-fetched from GitHub `main` before tracker update. Targeted static reasoning checked six synthetic batches, five alerts, three distinct known alert batch IDs, membership IDs 1/3/6, anti-membership IDs 2/4/5, one orphan alert, one NULL measurement, known processed total 280, NULL-bearing NOT IN returning no rows, version/database checks, read-only transaction, timeouts, fail-closed assertions, and rollback. **Not independently editorially reviewed; comprehensive automated SQL syntax/link QA pending; actual isolated PostgreSQL 18 execution not performed, no reproducible runtime evidence retained.**
- **Published 63/120 (52.5%), 57 remaining; Part 07 3/10. Next: Chapter 064 — Correlated subqueries and performance tradeoffs.**

## Chapter 064 publication evidence (2026-11-10)

- [Chapter 064](part-07-subqueries/064-correlated-subqueries-and-performance-tradeoffs.md): commit `bbc9d76ff90d2c8d7432284b6109a1e737e8cc8e`.
- [Synthetic read-only PostgreSQL 18 lab](labs/064-correlated-subqueries-performance.sql): commit `ba2c374c94cd608c2c112feffac091d4367108a5`.
- [README navigation](README.md): commit `2fe043ac44f6ebdf6b87dd6beb2c5643bcbf7cce`.
- All three files re-fetched from GitHub `main` before updating this tracker. Targeted static reasoning checked 6 synthetic batches, total 320, 4 alerts, above-source-average IDs 1/5, alerted IDs 1/4/6, unalerted IDs 2/3/5, per-batch alert counts 2/0/0/1/0/1, relative links, read-only transaction, version/database guards, timeouts, executable assertions and rollback. **Independent editorial review not performed; comprehensive automated SQL syntax/link QA pending; actual isolated PostgreSQL 18 execution not performed; no runtime evidence retained.**
- **Published 64/120 (53.3%), 56 remaining; Part 07 4/10. Next: Chapter 065 — Common table expressions (WITH).**

## Chapter 065 publication evidence (2026-11-10)

- [Chapter 065](part-07-subqueries/065-common-table-expressions-with.md): commit `b79f59f4ac9704b602df60cebcbd6746a6aaa749`.
- [Read-only PostgreSQL 18 lab](labs/065-common-table-expressions-with.sql): commit `447a9f111017480f523b473da9fdda9aee8fe070`.
- [README navigation](README.md): commit `6f5822f24181ca6b903023e8a0b4f44daa285324`.
- Chapter, lab, and README fetched back from GitHub `main` before this tracker update. Targeted static inspection and arithmetic reasoning checked six synthetic batches, 240 accepted, 60 rejected, 300 processed, API 170, file 130, weighted acceptance 80.00%, transaction-local timeouts, version/database guards, fail-closed SQL acceptance and ROLLBACK. **No independent editorial review; comprehensive automated syntax/link QA pending; actual isolated PostgreSQL 18 runtime execution not performed and no runtime evidence retained.**
- **Published 65/120 (54.2%), 55 remaining; Part 07 5/10. Next: Chapter 066 — Recursive CTEs and hierarchical queries.**


## Chapter 066 publication evidence (2026-11-11)

- [Chapter 066](part-07-subqueries/066-recursive-ctes-and-hierarchical-queries.md): commit `af83425ba3a4078cf71f905bc051762f2b0d3d3e`.
- [Synthetic read-only PostgreSQL 18 lab](labs/066-recursive-ctes-hierarchical-queries.sql): commit `98c2cc72dc09655117309d868ec918e9bd078229`.
- [README navigation](README.md): commit `14bdf7184d7607b5e5d0fc51d1073db82d62bcec`.
- Chapter and lab fetched back from GitHub `main`; targeted static inspection performed for six reachable employees, one orphan, manager subtree, and a three-edge cycle. Independent editorial review and comprehensive automated SQL syntax/link QA pending. **Actual isolated PostgreSQL 18 runtime execution was not performed; no runtime evidence retained.**
- **Published 66/120 (55.0%), 54 remaining; Part 07 6/10. Next: Chapter 067 — UNION versus UNION ALL.**


## Chapter 067 publication evidence (2026-11-11)

- [Chapter 067](part-07-subqueries/067-union-versus-union-all.md): commit `6b9bbeccc54877efdbe22d62137d5cdcf665fbae`.
- [Synthetic read-only PostgreSQL 18 lab](labs/067-union-versus-union-all.sql): commit `043071e2071de16c168dcba7062c5d0440584a7c`.
- [README navigation](README.md): commit `a0b1e2581929d6cb71d194897b9a8b63dd15268b`.
- Chapter, lab, and README were fetched back from GitHub `main` before this tracker update. Targeted static reasoning: 8 UNION ALL rows, 6 distinct UNION rows, 180 versus 140 numeric sum, 6 versus 5 non-NULL measurements, and two duplicated complete-row groups. Transaction is READ ONLY with local timeouts, version/database guards, fail-closed assertions and ROLLBACK. **Independent editorial review not performed; comprehensive automated syntax/link QA not performed; actual isolated PostgreSQL 18 runtime execution not performed and no runtime evidence retained.**
- **Published 67/120 (55.8%), 53 remaining; Part 07 7/10. Next: Chapter 068 — INTERSECT and EXCEPT (MINUS in some systems).**

## Chapter 068 publication evidence (2026-11-11)

- [Chapter 068](part-07-subqueries/068-intersect-and-except.md): commit `78e2412f4d8c5983926c2c633c6f2d0ea43450a0`.
- [Synthetic read-only PostgreSQL 18 lab](labs/068-intersect-except-set-operations.sql): commit `27c13678b43ba7ef63e3614f484e5d74d746208b`.
- [README navigation](README.md): commit `dc2d54f56c3c681289988ac97ec2f81dd12e7c08`.
- Chapter, lab, and README fetched or published on GitHub `main`; targeted static reasoning checked 3 shared distinct rows (102,103,NULL), source-only 101/104, warehouse-only 105, and EXCEPT ALL 101/102/104 (sum 307). Read-only transaction, version/database checks, local timeouts, fail-closed assertions and ROLLBACK included. **Independent editorial review not performed; comprehensive automated syntax/link QA pending; actual isolated PostgreSQL 18 runtime execution not performed and no runtime evidence retained.**
- **Published 68/120 (56.7%), 52 remaining; Part 07 8/10. Next: Chapter 069 — Refactor complex SQL for readability and correctness.**


## Chapter 069 publication evidence (2026-11-11)

- [Chapter 069](part-07-subqueries/069-refactor-complex-sql-for-readability-and-correctness.md): commit `5745d6dc7f350e316b8eb1dd8a6d15ed05ec59de`.
- [Synthetic read-only PostgreSQL 18 lab](labs/069-refactor-complex-sql.sql): commit `9918170181c4bd16dfcf9a746233ffdc26d25568`.
- [README navigation](README.md): commit `647d80e722e032c52447dc774819c420b6349974`.
- Chapter, SQL lab and README fetched back from GitHub `main` before tracker update. Targeted static reasoning checked six synthetic batches; East accepted/rejected/processed 140/30/170 (82.35%), West 100/30/130 (76.92%), overall 240/60/300 (80.00%), expected empty two-way EXCEPT ALL differences, transaction-local timeouts, read-only transaction, fail-closed assertions and rollback. **Independent editorial review not performed; comprehensive automated SQL syntax/link QA pending; actual isolated PostgreSQL 18 runtime execution not performed and no runtime evidence retained.**
- **Published 69/120 (57.5%), 51 remaining; Part 07 9/10. Next: Chapter 070 — Lab 07: query a multi-level organizational hierarchy.**

## Chapter 070 publication evidence — 2026-11-11

- Chapter: [070](part-07-subqueries/070-lab-07-query-a-multi-level-organizational-hierarchy.md), publication commit `273b64dbb1f412b64b8fcbf15a29cd8e3fd9c7e3`, navigation correction `52a65aa8e075d90945d5da02c208f95f56a24cfb`.
- Read-only synthetic PostgreSQL 18 lab: [070 SQL](labs/070-lab-07-organizational-hierarchy.sql), publication commit `634138d57d351393b69ed11410e28b582bf0138f`.
- README navigation commit `9211161c9ad8c12e83c495e06f02c6a72e65d680`.
- Chapter and lab fetched back from GitHub main. Targeted static reasoning checked nine fictional employees, six reachable, Ben subtree IDs 2/4/5, orphan ID 7, unreachable IDs 7/8/9, cycle starts 8/9, bounded recursion, read-only transaction, timeout and rollback. These are reasoned expectations, **not actual SQL execution**. Independent editorial review, comprehensive automated SQL syntax/link QA and actual isolated PostgreSQL 18 runtime validation remain pending; no runtime evidence retained.
- Part 07 complete by authorship: **10/10**. Overall **70/120 published**, **50 remaining**. Next: **071 — Window-function anatomy: OVER, PARTITION BY, ORDER BY**.

## Chapter 071 publication evidence — 2026-11-11

- Chapter: [071 — Window-function anatomy](part-08-window-functions/071-window-function-anatomy-over-partition-by-order-by.md), commit `d17a133529c487ebc88e4532cee5def54424c7ec`.
- Synthetic read-only PostgreSQL 18 lab: [071 SQL](labs/071-window-function-anatomy.sql), commit `ce6af7883e5170571b26f4b00a4a6f9592a25bd5`.
- [README navigation](README.md), commit `4b594d83ca95860d72949a8b1c26c23e82114045`.
- All three artifacts fetched back from GitHub `main` before tracker update. Targeted static inspection and manual arithmetic checked six synthetic batches, global total 230, API 120, FILE 110, running totals by batch ID [40,100,30,100,120,110], explicit ROWS frame, read-only transaction, timeouts, version/database guards, fail-closed assertions and rollback. **No independent editorial review; comprehensive automated SQL syntax/link QA not performed; actual isolated PostgreSQL 18 runtime execution not performed, no runtime evidence retained.**
- **Published 71/120 (59.2%), 49 remaining; Part 08 1/10. Next: Chapter 072 — ROW_NUMBER, RANK, and DENSE_RANK.**

## Chapter 072 publication evidence — 2026-11-11

- [Chapter 072](part-08-window-functions/072-row-number-rank-and-dense-rank.md): commit `8fda38ac4bb98da3cc422af8ec847cac2c094522`.
- [Synthetic read-only PostgreSQL 18 lab](labs/072-row-number-rank-dense-rank.sql): commit `001ac8882241c3d93a24a887d8eba3f41a4692a7`.
- [README navigation](README.md): commit `02e89fa19fb0cf50083ef3e6189f88ee490efb06`.
- Chapter, lab and README fetched back from GitHub `main` before tracker update. Targeted static reasoning: eight batches, four per service, ranks [1,1,3,4], dense ranks [1,1,2,3], deterministic winners 1/5, tied leaders 1/3/5/6, one NULL last. Lab includes read-only transaction, local timeouts, PostgreSQL 18/database guards, exact two-way EXCEPT ALL checks and rollback. **Independent editorial review not performed; comprehensive automated SQL syntax/link QA not performed; actual isolated PostgreSQL 18 runtime execution not performed and no runtime evidence retained.**
- **Published 72/120 (60.0%), 48 remaining; Part 08 2/10. Next: Chapter 073 — LAG and LEAD for change analysis.**

## Chapters 073–074 publication reconciliation — 2026-11-11

- [Chapter 073](part-08-window-functions/073-lag-and-lead-for-change-analysis.md) and [073 read-only lab](labs/073-lag-lead-change-analysis.sql) were already present on GitHub `main` when this run began; README navigation already linked both. The tracker had not yet recorded them. Their prior publication commit SHAs were not independently established in this reconciliation.
- [Chapter 074](part-08-window-functions/074-running-totals-and-cumulative-measures.md): commit `481fa59a2f06948ce0328c311b841a8a80cbec6e`.
- [074 synthetic read-only PostgreSQL 18 lab](labs/074-running-totals-cumulative-measures.sql): commit `ea64f600187434b2d0c7ffbfa0574b6d4853fe17`.
- [README navigation](README.md): commit `b37863cfee6585547203b3b2a0acc3d8d32a5c62`.
- Chapter 074 and its lab were fetched back from GitHub `main` before updating this tracker. Targeted static inspection confirmed the seven-row inline dataset, read-only transaction, version/database guards, local timeouts, explicit ROWS frame, bidirectional EXCEPT ALL expected-row checks, and ROLLBACK. Manually reasoned expected results: API running totals 20/50/60/100 (total 100); FILE 15/15/40 (total 40), one NULL measurement, and 100% final cumulative percentages.
- **Authored/published:** 74/120 (61.7%), 46 remaining; Part 08 4/10. **Independent editorial review:** pending. **Comprehensive automated SQL syntax/link QA:** pending. **Actual isolated PostgreSQL 18 runtime validation:** not performed; no execution evidence retained. **Next:** Chapter 075 — Rolling averages and moving windows.

## Chapter 075 publication evidence — 2026-11-11

- [Chapter 075](part-08-window-functions/075-rolling-averages-and-moving-windows.md): commit `bf802cf32d4f80747993b1c271d87c6d5b7e2326`.
- [075 synthetic read-only PostgreSQL 18 lab](labs/075-rolling-averages-moving-windows.sql): commit `f383deeb236c56f6c7d49f80633530e4198ed909`.
- [README navigation](README.md): commit `f10581e81f76198de7f7b187f9a0a6002368e3de`.
- Chapter and lab were fetched back from GitHub `main` before tracker update. Targeted static reasoning checked eight synthetic rows, trailing three-row averages (API 100/150/200/250/400; FILE 40/60/80), NULL handling, strict complete windows (IDs 3/8), transaction-local timeouts, version/database guards, two-way `EXCEPT ALL` assertions, and rollback. This is **not** independent editorial review or comprehensive automated SQL syntax/link QA.
- **Actual isolated PostgreSQL 18 runtime execution: pending.** No instance was run or runtime evidence retained.
- **Authored/published: 75/120 (62.5%), 45 remaining; Part 08: 5/10. Next: Chapter 076 — FIRST_VALUE, LAST_VALUE, and window frames.**


## Chapter 076 publication evidence — 2026-11-11

- [Chapter 076](part-08-window-functions/076-first-value-last-value-and-window-frames.md): commit `64cb01ea1b258b57a46d32ee49013be707cc3c30`.
- [076 synthetic read-only PostgreSQL 18 lab](labs/076-first-last-value-window-frames.sql): commit `73d1f988c60a225330e47e6a9c8805bf966dbbe9`.
- [README navigation](README.md): commit `f5581817871fdcc4e0c31af6817fff2422900bbc`.
- Chapter, lab and README fetched back from GitHub `main` before tracker update. Targeted static inspection and manually reasoned expectations: eight synthetic events; API first/final IDs 1/5, FILE 6/8, running last IDs match each event ID, API final latency NULL, FILE final latency 90. Read-only transaction, local timeouts, version/database guards, bidirectional EXCEPT ALL assertions and ROLLBACK present. **Not independently editorially reviewed; comprehensive automated SQL syntax/link QA not performed; actual isolated PostgreSQL 18 runtime execution not performed and no execution evidence retained.**
- **Published 76/120 (63.3%), 44 remaining; Part 08: 6/10. Next: Chapter 077 — NTILE, percentiles, and distribution analysis.**

## Chapter 077 publication evidence — 2026-11-11

- [Chapter 077](part-08-window-functions/077-ntile-percentiles-and-distribution-analysis.md): commit `170510106d112fbef9e6ef9bb73da0076f0cb52f`.
- [077 synthetic read-only PostgreSQL 18 lab](labs/077-ntile-percentiles-distribution.sql): commit `b961f8ec1cd97e96528e2c8869893da775f76ae7`.
- [README navigation](README.md): commit `ec35c0ef246fb85423577d26efbe8f8f9c858a4f`.
- Both new artifacts fetched back from GitHub `main` before updating tracker. Targeted static inspection checked inline synthetic rows, read-only transaction, local timeouts, PostgreSQL 18/database guards, deterministic NTILE ordering, two-way EXCEPT ALL assertions, fail-closed acceptance and ROLLBACK. Manually reasoned expected p50/p95: API 20/88, FILE 20/33.5, with discrete p50 API 20 and FILE 15; 9 measured and 1 missing row. This is not a comprehensive parser or link audit.
- **Published 77/120 (64.2%), 43 remaining; Part 08 7/10.** Independent editorial review: **pending**. Comprehensive SQL syntax/link QA: **pending**. Actual isolated PostgreSQL 18 runtime execution: **not performed**, no reproducible runtime evidence retained. **Next:** Chapter 078 — Gaps-and-islands patterns.

## Chapter 078 publication evidence

- Chapter: [078](part-08-window-functions/078-gaps-and-islands-patterns.md); commit `2f53885b588a47d855825a8befe4fe1f549d7344`.
- Lab: [078 SQL](labs/078-gaps-and-islands-patterns.sql); commit `4c3373a9cabde3e6780ca4b9f5f67691dca564d5`.
- README navigation: commit `71cc2ef3cb1eb52e569337d56a30a6ae5a1abbbd`.
- Chapter and lab fetched back from GitHub main. Targeted static inspection: PostgreSQL 18/database guard, synthetic data, read-only transaction, transaction-local timeouts, bidirectional EXCEPT ALL acceptance, rollback, and relative links. Expected 5 islands, 3 gap ranges, and 4 missing positions reasoned manually. **No independent editorial review, comprehensive automated SQL syntax/link QA, or actual isolated PostgreSQL 18 execution was performed.** Runtime evidence pending.
- Next: **079 — Cohort analysis, retention, and event sequencing**. Part 08: 8/10.

## Chapter 079 publication evidence — 2026-11-11

- Chapter: [079](part-08-window-functions/079-cohort-analysis-retention-and-event-sequencing.md); commit `96ff2b618c33b9ed0d4a377d47aa63a3b248bec3`.
- Synthetic read-only PostgreSQL 18 lab: [079 SQL](labs/079-cohort-retention-event-sequencing.sql); commit `49dd7218136a97e4a34bc160b863f533608a6b9b`.
- [README navigation](README.md): commit `029deb428591c5836f2822cf03fbb52affccfe15`.
- Chapter and lab were fetched back from GitHub main; README navigation fetched and confirmed before tracker update. Targeted static reasoning checked six cohort-week rows, 10 synthetic events, six users, distinct user-week grain, fixed denominators, expected percentages 100/66.67/33.33 and 100/50 and 100, deterministic sequencing, read-only transaction, timeouts, version/database guards, two-way EXCEPT ALL assertions, and rollback. This is **not** comprehensive parser-based SQL syntax QA or independent editorial review.
- **Published: 79/120 (65.8%), 41 remaining; Part 08: 9/10.** Independent editorial review: **pending (0 certified)**. Comprehensive automated SQL syntax/link QA: **pending**. Actual isolated PostgreSQL 18 runtime execution: **not performed**; no reproducible runtime evidence collected. **Next:** Chapter 080 — Lab 08: produce an analytical customer activity report.

## Chapter 080 publication evidence — 2026-11-11

- [Chapter 080](part-08-window-functions/080-lab-08-produce-an-analytical-customer-activity-report.md): commit `4593a0d3b603fc15e297f348a192f44f8f61f74b`.
- [Synthetic read-only PostgreSQL 18 lab](labs/080-lab-08-analytical-customer-activity-report.sql): commit `3ba94c0ff1a5e3b6e6e8b11e9bf14c8473b3bf68`.
- [README navigation](README.md): commit `e6636643f5512519ec9af1f2ef89ec962e4d84aa`.
- Both new files were fetched back from GitHub main before README update; README navigation was fetched back and verified before this tracker update. Targeted static reasoning checked seven synthetic events, four customers (three active), five purchases, spend 115, Aster/Birch tied at spend 50, Dune zero activity, deterministic window ordering, two-way `EXCEPT ALL` assertions, PostgreSQL 18/database guards, read-only transaction, timeouts and rollback. This is **not** comprehensive parser-based syntax QA or independent editorial review.
- **Authored/published: 80/120 (66.7%), 40 remaining; Part 08 complete (10/10).** Independent editorial review: **pending**. Comprehensive automated SQL syntax/link QA: **pending**. Actual isolated PostgreSQL 18 runtime execution: **not performed**, no reproducible runtime evidence retained. **Next: Chapter 081 — String functions and regular expressions (Part 09).**

## Chapter 081 publication evidence — 2026-11-11

- [Chapter 081](part-09-functions-views-json/081-string-functions-and-regular-expressions.md): commit `8a79c911dda9144c4f74df14ee241b32a4e7fcfa`.
- [Synthetic read-only PostgreSQL 18 lab](labs/081-string-functions-and-regular-expressions.sql): commit `49447511c253dafa2dab947d59e0f156b0ed56b1`.
- [README navigation](README.md): commit `b4bb460c327827e6f809f2720b4bf1b2e5bbedd0`.
- Chapter and SQL lab fetched back from GitHub main; README navigation fetched back before tracker update. Targeted static reasoning checked synthetic five-row dataset, two valid/two invalid/one missing code statuses, deterministic ordering, null handling, two-way `EXCEPT ALL` assertions, transaction-local timeouts, read-only transaction, database/version guards, and rollback. No automated PostgreSQL parser-based SQL syntax test or independent editorial review was performed.
- **Authored/published: 81/120 (67.5%), 39 remaining; Part 09: 1/10.** Independent editorial review: **pending**. Comprehensive automated SQL syntax/link QA: **pending**. Actual isolated PostgreSQL 18 runtime execution: **not performed**; no reproducible evidence retained. **Next: Chapter 082 — Dates, intervals, timestamps, and time zones.**

## Latest milestone — Chapter 082

Chapter [082](part-09-functions-views-json/082-dates-intervals-timestamps-and-time-zones.md) and its [synthetic read-only lab](labs/082-dates-intervals-timestamps-time-zones.sql) were published and fetched back from GitHub main. Targeted static reasoning and path inspection only; independent editorial review, comprehensive static QA, and actual isolated PostgreSQL 18 runtime execution remain **pending**. Next: Chapter 083 — Numeric expressions and precision considerations. Published 82/120; remaining 38.

## Chapter 083 publication evidence — 2026-11-11

- [Chapter 083 — Numeric expressions and precision considerations](part-09-functions-views-json/083-numeric-expressions-and-precision-considerations.md): commit `c75c30de69ebbfbb56808b86803d3f4e614de953`.
- [Synthetic read-only PostgreSQL 18 lab](labs/083-numeric-expressions-precision.sql): commit `2a056464c690cc884e8a7944dc8e00619ea89123`.
- [README navigation](README.md): commit `e6fdda19481de0042cfabe806f853500d503423e`.
- Chapter, lab, and README were re-fetched from GitHub `main` before this tracker update. Targeted static inspection checked synthetic four-row amounts, exact decimal versus binary float, safe zero-denominator behavior, integer division, round-before/after-sum expectations (30.100 raw, 30.10 rounded total, 30.11 summed rounded lines), read-only transaction, version/database guards, timeouts, bidirectional `EXCEPT ALL` assertions and rollback. Manual expected-result reasoning is **not** PostgreSQL runtime execution or comprehensive parser-based syntax QA.
- **Authored/published: 83/120 (69.2%), 37 remaining; Part 09: 3/10.** Independent editorial review: **pending (0 certified)**. Comprehensive automated SQL syntax/link QA: **pending**. Actual isolated PostgreSQL 18 runtime execution: **not performed**; no reproducible runtime evidence retained. **Next: Chapter 084 — JSON and semi-structured SQL queries.**

## Chapter 084 publication evidence — 2026-11-11

- [Chapter 084](part-09-functions-views-json/084-json-and-semi-structured-sql-queries.md): commit `c52976679897cbd24cd635acec1442a14d16564a`.
- [Synthetic read-only SQL lab](labs/084-json-semi-structured-queries.sql): commit `63be0636906b1ff3b18f2b08aacc275418b1ced1`.
- [README navigation](README.md): commit `5850112989fd7ca95884f2aa902f2e26d697078e`.
- Chapter and lab fetched back from GitHub `main` before tracker update; README navigation updated. Targeted static inspection checked the four-event synthetic dataset, missing key versus JSON null versus SQL NULL, guarded array expansion, counts, read-only transaction, database/version guards, local timeouts, bidirectional `EXCEPT ALL` and rollback. **No isolated PostgreSQL 18 runtime execution was performed; no runtime evidence retained.** Comprehensive automated SQL syntax/link QA and independent editorial review remain pending.
- **Authored/published: 84/120 (70.0%), 36 remaining; Part 09: 4/10.** Independently reviewed: **0**; PostgreSQL 18 runtime-validated: **0**. **Next: Chapter 085 — Views and secure abstraction.**

## Chapter 085 publication evidence — 2026-11-11

- [Chapter 085 — Views and secure abstraction](part-09-functions-views-json/085-views-and-secure-abstraction.md): commit `4be84717526331482426c72bf9fa1bfa6df57668`.
- [Synthetic read-only PostgreSQL 18 lab](labs/085-views-secure-abstraction.sql): commit `32a42299a1700f741470a8a4eced88950ee2cb58`.
- [README navigation](README.md): commit `a408a1c03f56d2f6d2bf55f50412366d011666e0`.
- Chapter and lab fetched back from GitHub `main`, and README navigation updated. Targeted static inspection checked four customers, six orders, four paid orders totaling 72.50, preservation of zero-activity customers, exact two-way `EXCEPT ALL` assertions, PostgreSQL 18/database guard, transaction-local timeouts, read-only transaction and rollback. The canonical lab models a view-shaped CTE without creating any persistent view or changing privileges. This is **not** a comprehensive parser-based SQL check or independent editorial review.
- **Authored/published: 85/120 (70.8%), 35 remaining; Part 09: 5/10.** Independently reviewed: **0**. Comprehensive automated SQL syntax/link QA: **pending**. Actual isolated PostgreSQL 18 runtime execution: **not performed**, no runtime evidence retained. **Next: Chapter 086 — Materialized views and refresh strategies.**


## Chapter 086 publication evidence — 2026-11-11

- [Chapter 086](part-09-functions-views-json/086-materialized-views-and-refresh-strategies.md): commit `7423e7ab897591807f5cb91a0c5a3ff3f8e787cf`.
- [Read-only PostgreSQL 18 lab](labs/086-materialized-views-refresh-strategies.sql): commit `88097f171f0cf2e6463d3bf391528ca6e8ece2ea`.
- [README navigation](README.md): commit `d9818d6f1731613bc825a72b507f4389e921d241`.
- Chapter, lab, and README were re-fetched from GitHub main before this tracker update. Targeted static reasoning reviewed five synthetic orders, snapshot versus live counts and revenue, one late paid event, read-only transaction, environment guards, timeouts, bidirectional EXCEPT ALL assertions and rollback. This is not independent editorial review, comprehensive parser-based syntax/link QA, or runtime execution.
- **Published: 86/120 (71.7%), 34 remaining; Part 09: 6/10.** Independently reviewed: **0**; isolated PostgreSQL 18 runtime-validated: **0**; comprehensive automated SQL syntax/link QA: **pending**. **Next: Chapter 087 — Temporary tables and intermediate result sets.**

## Chapter 087 publication evidence — 2026-11-11

- [Chapter 087](part-09-functions-views-json/087-temporary-tables-and-intermediate-result-sets.md): commit `ee9af104f82eeab429e4d08f9046b00163e91306`.
- [Synthetic read-only PostgreSQL 18 lab](labs/087-temporary-tables-intermediate-results.sql): commit `b8a2de723090b3b043d39b83d580dc74a04f4af5`.
- [README navigation](README.md): commit `7abd002584b770d816f27d6f5ec5840574be74d8`.
- Both new files fetched back from GitHub `main`; README navigation re-fetched before tracker update. Targeted static/manual checks: synthetic six-order source, four paid rows, two customer groups (101: 3/30.00; 102: 1/20.00), total paid 50.00, read-only transaction, database/major-version guard, local timeouts, bidirectional `EXCEPT ALL`, and rollback. No isolated PostgreSQL 18 execution or independent editorial review occurred; comprehensive automated SQL syntax/link QA pending.
- **Published: 87/120 (72.5%), 33 remaining; Part 09: 7/10.** Independently reviewed: **0**; actual PostgreSQL 18 runtime-validated: **0**. **Next: Chapter 088 — Stored functions and procedures — dialect-specific syntax.**

## Chapter 088 publication evidence — 2026-11-11

- [Chapter 088](part-09-functions-views-json/088-stored-functions-and-procedures-dialect-specific-syntax.md): commit `d90844c3425ec857373ad9d2270db8ea460979bb`.
- [Read-only PostgreSQL 18 lab](labs/088-stored-functions-and-procedures.sql): commit `674941e351ca5ce60829ccd08a815ca8cd562577`.
- [README navigation](README.md): commit `8a5274f498f992c61633dd13acef38ecab814732`.
- Chapter and lab fetched back from GitHub `main` before README update. Targeted manual/static inspection: three synthetic invoices; fees 5.00, 4.00, 0.00; aggregate fee 9.00 and total 169.00; read-only transaction, database/version guard, local timeouts, catalog routine metadata, two-way EXCEPT ALL and rollback. **No PostgreSQL 18 instance was executed**, and no runtime evidence exists. Independent editorial review and comprehensive automated syntax/link QA pending.
- **Published: 88/120 (73.3%), 32 remaining; Part 09: 8/10.** Independently reviewed: **0**; actual PostgreSQL 18 runtime-validated: **0**. **Next: Chapter 089 — Triggers, dynamic SQL, and parameterization safeguards.**

## Chapter 089 publication evidence — 2026-11-11

- [Chapter 089](part-09-functions-views-json/089-triggers-dynamic-sql-and-parameterization-safeguards.md): commit `1946d41bd109bec7eb970133419288288c150c0c`.
- [Synthetic read-only PostgreSQL 18 lab](labs/089-triggers-dynamic-sql-parameterization.sql): commit `c227033bf018a9329e7cc4b1fce968f7126966ef`.
- [README navigation](README.md): commit `4fcd921d35b4900dc96d7fd9592045c61f15e1b5`.
- Chapter, lab and README re-fetched from GitHub `main` before tracker update. Targeted static/manual reasoning checked five synthetic transitions, four changed rows, one unchanged row, one NULL-to-value change, one paid transition, bidirectional `EXCEPT ALL` assertions, database/version guard, read-only transaction, local timeouts and rollback. The lab models trigger behavior without creating triggers or executing actual dynamic SQL. Independent editorial review and comprehensive parser-based SQL syntax/link QA remain pending. **Actual isolated PostgreSQL 18 runtime execution was not performed and no runtime evidence was retained.**
- **Authored/published: 89/120 (74.2%), 31 remaining; Part 09: 9/10.** Independently reviewed: **0**; PostgreSQL 18 runtime-validated: **0**. **Next: Chapter 090 — Lab 09: Build reusable reporting objects.**

## Chapter 090 publication evidence

- Chapter: [090](part-09-functions-views-json/090-lab-09-build-reusable-reporting-objects.md); commit `dbbf608d4cbca77a6172cb91e823e5dd148177f0`.
- Lab: [090 SQL](labs/090-lab-09-reusable-reporting-objects.sql); commit `be309a44e3b866c61bf7ab5c992faec1092c31e6`.
- Both files fetched from GitHub `main` after creation. Targeted manual checks: one-row-per-customer contract, exact multiset comparison, paid total 85.00, stale snapshot 75.00, read-only transaction, version/database guard and rollback. **Not independently reviewed or comprehensively syntax-checked.**
- **Actual isolated PostgreSQL 18 runtime validation pending**: no PostgreSQL 18 instance was executed and no runtime evidence retained.
- Part 09 complete (10/10). **Next: 091 — Read execution plans with EXPLAIN.**

## Chapter 091 publication evidence — 2026-11-12

- Chapter: [091 — Read execution plans with EXPLAIN](part-10-performance/091-read-execution-plans-with-explain.md); commit `9af3e1a3200da19eecd22392830312693a7dd08a`.
- Lab: [091 synthetic read-only SQL](labs/091-read-execution-plans-with-explain.sql); commit `652f4607b01eb44b4bbb409ae968db6ce29bf027`.
- README navigation commit `54f7a94a1489fef44d765dc6e0bc74a0916a7919`.
- Chapter and lab fetched from GitHub `main` after publication. Targeted static/manual inspection checked relative links, read-only transaction, PostgreSQL 18/database guard, timeout limits, estimated EXPLAIN without ANALYZE, synthetic counts (four orders, three paid, 45.00 paid total), and exact multiset assertion. These are reasoned expectations, **not executed results**.
- **Authored/published: 91/120; remaining: 29; Part 10: 1/10.** Independent editorial review: **pending**. Comprehensive automated SQL syntax/link QA: **pending**. Actual isolated PostgreSQL 18 runtime validation with reproducible evidence: **pending**. No PostgreSQL 18 execution performed or runtime certification claimed.
- **Next unfinished chapter: 092 — Table scans, index scans, row estimates, and selectivity.**

## Chapter 092 publication evidence — 2026-11-12

- [Chapter 092](part-10-performance/092-table-scans-index-scans-row-estimates-and-selectivity.md): commit `3df3a58fc3639a931bbb5a074350ef575c54d28c`.
- [Read-only synthetic PostgreSQL 18 lab](labs/092-scans-estimates-selectivity.sql): commit `368336f672a671f078e4fe3dcca6338e7dcb467c`.
- [README navigation](README.md): commit `e61684ccb496ec7913b6bc4381789d36c06e2755`.
- Chapter, lab, and README fetched from GitHub `main` after publication. Targeted static/manual reasoning: 10 synthetic events; failed 2/0.20, paid 7/0.70, pending 1/0.10; two-way `EXCEPT ALL` assertion, database/version guard, read-only transaction, transaction-local timeouts, and rollback. Exact plan nodes intentionally not asserted. No independent editorial review or comprehensive parser-based SQL/link QA completed. **No isolated PostgreSQL 18 runtime execution performed; no runtime evidence retained.**
- **Published 92/120 (76.7%), remaining 28; Part 10 2/10.** Independent review: **0**. PostgreSQL 18 runtime-validated: **0**. **Next: 093 — B-tree indexes and common index access patterns.**

## Chapter 093 publication evidence — 2026-11-12

- [Chapter 093](part-10-performance/093-btree-indexes-and-common-index-access-patterns.md): commit `f7ea1fb0d02c3b1ca7c8f394a09b27402dd71f18`.
- [Synthetic read-only PostgreSQL 18 lab](labs/093-btree-index-access-patterns.sql): commit `0007a50df14d3c2fdbda7346de44a9d7c7d8a39f`.
- [README navigation](README.md): commit `9dc9f176c17bf9405ef41ad5a29f9db77b70d3fb`.
- Both new files and README navigation re-fetched and verified on GitHub `main` before updating this tracker. Targeted static/manual checks: chapter numbering, relative links, read-only transaction, synthetic five-order dataset, database/version guards, local timeouts, estimated EXPLAIN without ANALYZE, exact two-way multiset assertions, and rollback. Reasoned results: point order 103 = 8.00; range orders 102–104 sum 73.00; all five total 100.00.
- **Validation distinctions:** authored/published yes; targeted static/manual reasoning yes; independent editorial review no; comprehensive parser-based SQL/link QA no; actual isolated PostgreSQL 18 execution no; retained runtime evidence none.
- **Published: 93/120 (77.5%), remaining: 27; Part 10: 3/10.** Independently reviewed: **0**. PostgreSQL 18 runtime-validated: **0**. **Next: 094 — Composite indexes and column order.**

## Chapter 094 publication evidence — 2026-11-12

- [Chapter 094](part-10-performance/094-composite-indexes-and-column-order.md): commit `dfeb18735283fb69b265229d1d1a8957d7d5ccaf`.
- [Synthetic read-only PostgreSQL 18 lab](labs/094-composite-indexes-column-order.sql): commit `1bd78df9dbbb89898941201010b2cde47deb32c5`.
- [README navigation](README.md): commit `8082c6320b2d14eb63d89bf0a7ceaf76553fae47`.
- Chapter and lab re-fetched from GitHub main after creation. Targeted static/manual checks: expected chapter numbering and relative paths, PostgreSQL 18/database guard, read-only transaction, transaction-local timeouts, synthetic six-order data, estimated EXPLAIN without ANALYZE, two-way EXCEPT ALL assertions, and rollback. Manually reasoned expectations: tenant-10 paid range IDs 103 and 101, range revenue 50.00, tenant-10 paid total 100.00, six orders overall.
- **Validation distinction:** authored/published yes; targeted static/manual reasoning yes; independent editorial review no; comprehensive parser-based SQL/link QA no; actual isolated PostgreSQL 18 execution no; retained runtime evidence none.
- **Published: 94/120 (78.3%), remaining: 26; Part 10: 4/10.** Independently reviewed: **0**; PostgreSQL 18 runtime-validated: **0**. **Next: 095 — Partial, expression, and covering indexes.**

## Chapter 095 publication evidence — 2026-11-12

- [Chapter 095](part-10-performance/095-partial-expression-and-covering-indexes.md): commit `fe4dbf6c0978b5fde5a02ed24e94ed0bae6ce9aa`.
- [Synthetic read-only PostgreSQL 18 lab](labs/095-partial-expression-covering-indexes.sql): commit `1196f4cf3f5646bb19ea5014b400f677d3e9762a`.
- [README navigation](README.md): commit `262b77abbf97d16d2016b9065c62e7765a618d4b`.
- Chapter and lab fetched back from GitHub `main` after creation. Targeted static/manual reasoning checked chapter number, paths, PostgreSQL 18/database guards, read-only transaction, timeouts, estimated EXPLAIN (no ANALYZE), exact bidirectional EXCEPT ALL checks and ROLLBACK. Static expectations: six orders; four open amount 100.00; three tenant-10 open amount 60.00; newest IDs 105, 103, 101; two matching normalized email records. No actual query execution was performed.
- **Validation distinction:** authored/published yes; targeted static/manual reasoning yes; independent editorial review no; comprehensive automated parser-based SQL/link QA no; actual isolated PostgreSQL 18 runtime execution no; retained runtime evidence none.
- **Published: 95/120 (79.2%), remaining: 25; Part 10: 5/10.** Independently reviewed: **0**; PostgreSQL 18 runtime-validated: **0**. **Next: 096 — Optimizer statistics and PostgreSQL maintenance basics.**

## Chapter 096 publication evidence — 2026-11-12

- [Chapter 096](part-10-performance/096-optimizer-statistics-and-postgresql-maintenance-basics.md): commit `f857f971b4fbebcd6bf583ad779454edcc24cc80`.
- [Synthetic read-only PostgreSQL 18 lab](labs/096-optimizer-statistics-maintenance.sql): commit `91a46d6d708bec33cca3e0e047acde58ce00e420`.
- [README navigation](README.md): commit `1845d75cc56fb2735720a2c435c1bad1440480c6`.
- Both new files and README links re-fetched from GitHub `main` before tracker update. Targeted static/manual inspection checked chapter numbering, relative links, PostgreSQL 18/database guard, read-only transaction, timeouts, synthetic eight-row data, estimated EXPLAIN without ANALYZE, catalog-only inspection, bidirectional EXCEPT ALL assertions, and ROLLBACK. Reasoned values: 8 total, 4 tenant 10, 4 paid, 3 joint, 3 tenant-20 pending, 37.5% joint; independence approximation 2 versus actual 3. No SQL execution was performed.
- **Validation distinction:** authored/published yes; targeted static/manual reasoning yes; independent editorial review no; comprehensive parser-based SQL/link QA no; actual isolated PostgreSQL 18 runtime execution no; retained runtime evidence none.
- **Published: 96/120 (80.0%), remaining: 24; Part 10: 6/10.** Independently reviewed: **0**; PostgreSQL 18 runtime-validated: **0**. **Next: 097 — Make predicates index-friendly and rewrite expensive SQL.**

## Chapter 097 publication evidence

- Chapter: [097](part-10-performance/097-make-predicates-index-friendly-and-rewrite-expensive-sql.md); commit `4e4bea56607a40af164c028169a4a181866be13d`.
- Lab: [097 SQL](labs/097-index-friendly-predicates-rewrites.sql); commit `5ef8b31539ef85cf7344982acade35c7745c48c9`.
- README navigation: commit `5260752aca426aa59d2874b9a11875b6638b6c76`.
- Chapter and lab fetched back from GitHub main; README navigation re-fetched. Targeted static inspection of relative links, version/database guard, synthetic data, read-only transaction, bidirectional EXCEPT ALL assertions and ROLLBACK completed; expected IDs and totals manually reasoned. **Independent editorial review, comprehensive automated SQL syntax/link QA, and actual isolated PostgreSQL 18 runtime execution remain pending.** No PostgreSQL runtime evidence was collected.
- Progress: **97/120 published (80.8%); 23 remaining; Part 10 7/10**. Next: **098 — Optimize joins, aggregations, and subqueries**.

## Chapter 098 publication evidence — 2026-11-12

- [Chapter 098](part-10-performance/098-optimize-joins-aggregations-and-subqueries.md): commit `36c7bb404bec5da0ae9113563fab38685c8d88f6`.
- [Synthetic read-only PostgreSQL 18 lab](labs/098-optimize-joins-aggregations-subqueries.sql): commit `c338f7275cdc63b983fe90a7feca2f9f8e11683e`.
- [README navigation](README.md): commit `18688490db4164dcd1e20667c7c899a8c457238f`.
- Chapter and lab fetched back from GitHub main; reference to Chapter 052 confirmed. Targeted manual static reasoning checked chapter number, link paths, synthetic data, read-only transaction, database/version guards, local timeouts, estimated EXPLAIN, two-way EXCEPT ALL checks and ROLLBACK. Expected corrected order totals: (101,50,50), (102,40,40), (103,10,0); naive inner join has 5 rows overall (4 for 101, 1 for 102). These are **calculated expectations, not observed SQL results**.
- **Validation distinction:** authored/published yes; targeted static/manual reasoning yes; independent editorial review no; comprehensive automated SQL syntax/link QA no; isolated PostgreSQL 18 runtime execution no; reproducible runtime evidence none.
- **Progress: 98/120 published (81.7%), 22 remaining; Part 10 8/10. Next: 099 — Keyset pagination, benchmarking, and regression tests.**

## Chapter 099 publication evidence — 2026-11-12

- [Chapter 099](part-10-performance/099-keyset-pagination-benchmarking-and-regression-tests.md): commit `893319d5251c7cf79471e1c3c99463ef3b9426c8`.
- [Read-only PostgreSQL 18 lab](labs/099-keyset-pagination-benchmark-regression.sql): commit `25bf7cbd6bbf48a53c67c6a2fe5c560e3a82f1e0`.
- [README navigation](README.md): commit `accccb8f10ea650a1b003d576abbfe1231d36ff7`.
- Chapter, lab and README link re-fetched on GitHub main before this tracker update. Targeted static/manual review covered numbering, relative links, database/version guard, read-only transaction, local timeouts, inline synthetic data, estimated EXPLAIN, multiset assertions and rollback. Calculated expectation: pages (109,108,107), (106,105,104), (103,102,101), 9 unique rows, zero mismatches with fixed-data OFFSET pages. These are **reasoned expected values, not observed execution output**.
- **Validation distinction:** authored/published yes; targeted static/manual inspection yes; independent editorial review no; comprehensive parser-based SQL/link QA no; actual isolated PostgreSQL 18 runtime execution no; retained runtime evidence none.
- **Progress: 99/120 published (82.5%), 21 remaining; Part 10: 9/10. Next: 100 — Lab 10: baseline, tune, and remeasure a slow query.**


## Chapter 100 publication evidence — 2026-11-12

- [Chapter 100](part-10-performance/100-lab-10-baseline-tune-and-remeasure-a-slow-query.md): commit `785231f9cb41619e911e00ca0f402e935949fb35`.
- [Synthetic read-only PostgreSQL 18 lab](labs/100-lab-10-baseline-tune-remeasure.sql): commit `ee7ac56ec10c452df8c43e46a48855777e2d8237`.
- [README navigation](README.md): commit `5e3c505c90142b9c945c1a9b29b6b5f531a322c5`.
- Chapter, lab, and README links fetched back from GitHub main before tracker update. Targeted static/manual checks covered numbering, file presence, relative links, synthetic 12-row fixture, PostgreSQL 18/database guard, read-only transaction, local timeouts, estimated EXPLAIN only, two-way EXCEPT ALL assertions and rollback. Expected values reasoned manually: 12 orders; 4 paid orders for tenant 10 on Nov 1; revenue 100.00; zero multiset differences. These are calculated expectations, **not observed execution results**.
- **Validation distinction:** authored/published yes; targeted static/manual reasoning yes; independent editorial review no; comprehensive automated SQL syntax/link QA no; actual isolated PostgreSQL 18 runtime execution no; retained runtime evidence none. No measured query speedup is claimed.
- **Progress: 100/120 published (83.3%), 20 remaining; Part 10 complete (10/10). Next: 101 — Least privilege and SQL access-control principles.**

## Chapter 101 publication evidence — 2026-11-12

- [Chapter 101](part-11-security-operations/101-least-privilege-and-sql-access-control-principles.md): commit `ab31e8a137f0d20827b223862f4c76019cb9b5c7`.
- [Synthetic read-only PostgreSQL 18 lab](labs/101-least-privilege-access-control.sql): commit `2b03223480d8e610635a6439608f9425b3304a0e`.
- [README navigation](README.md): commit `2bccb04c4b1b1a69e5f1fb847a772de58f18ea2d`.
- Chapter and lab fetched back from GitHub main; README link confirmed. Targeted static/manual reasoning checked numbering, relative paths, synthetic 9-row policy, 4 allowed grants, 0 forbidden and 0 missing, PostgreSQL 18/database guards, read-only transaction, local timeouts, introspection-only catalog functions and ROLLBACK. Expected values are calculated, **not observed PostgreSQL results**.
- **Validation distinction:** authored/published yes; targeted static/manual reasoning yes; independent editorial review no; comprehensive parser-based SQL/link QA no; actual isolated PostgreSQL 18 runtime execution no; retained runtime evidence none.
- **Progress: 101/120 published (84.2%), 19 remaining; Part 11 1/10. Next: 102 — Users, roles, GRANT, REVOKE, and ownership.**


## Chapter 102 publication evidence — 2026-11-12

- [Chapter 102](part-11-security-operations/102-users-roles-grant-revoke-and-ownership.md): commit `0b7eba8a0298a147967506bf738fa7f5b14c5d89`.
- [Synthetic read-only PostgreSQL 18 lab](labs/102-users-roles-grant-revoke-ownership.sql): commit `5792a500c0a0dacd14dfc8559bf6b062329a0813`.
- [README navigation](README.md): commit `4050c61232a1bd7317a523333977efc8857d0253`.
- Chapter, lab, and README were fetched back from GitHub main. Targeted static/manual checks reviewed chapter number, relative paths, read-only transaction, database/version guards, timeouts, synthetic model and two-way `EXCEPT ALL` assertions. Expected 3 principals, 1 membership, 2 approved grants, 1 rejected candidate, and 0 differences are **calculated, not observed PostgreSQL output**.
- **Validation distinction:** authored/published yes; targeted static/manual checks yes; independent editorial review no; comprehensive automated parser-based SQL/link QA no; isolated PostgreSQL 18 runtime execution no; reproducible runtime evidence none. This synthetic model is not a live privilege audit.
- **Progress: 102/120 published (85.0%); 18 remaining; Part 11 2/10. Next: 103 — Row-level security and data-access policies.**

## Chapter 103 publication evidence — 2026-11-12

- [Chapter 103](part-11-security-operations/103-row-level-security-and-data-access-policies.md): commit `c8492a007e9f166cebcc0f5e237a7aa0ebee85a3`.
- [Synthetic read-only PostgreSQL 18 lab](labs/103-row-level-security-data-access-policies.sql): commit `11a8138ca336b1021b49aab34e83ea663feb2fef`.
- [README navigation](README.md): commit `11c2f8f73ca356e77a70a35d62525b445a122428`.
- Chapter, lab and README were fetched back from GitHub main before this tracker update. Targeted manual/static checks: numbering and links, read-only transaction, database/version guard, local timeouts, five synthetic orders, three context groups, bidirectional EXCEPT ALL assertions, and rollback. Expected tenant 10 = 3 rows/90.00; tenant 20 = 2 rows/60.00; missing = 0; total = 5; zero mismatches. These are **calculated expected results, not observed PostgreSQL output**. The lab models tenant filtering and does not execute actual RLS policy enforcement.
- **Validation distinction:** authored/published yes; targeted static/manual reasoning yes; independent editorial review no; comprehensive automated parser-based SQL/link QA no; isolated PostgreSQL 18 runtime execution no; retained runtime evidence none.
- **Progress: 103/120 published (85.8%); 17 remaining; Part 11 3/10. Next: 104 — Sensitive data protection, masking, and audit requirements.**

## Chapter 104 publication evidence — 2026-11-12

- [Chapter 104](part-11-security-operations/104-sensitive-data-protection-masking-and-audit-requirements.md): commit `3d7eb2737538c6e1bb39c413f855806f515128e8`.
- [Synthetic read-only PostgreSQL 18 lab](labs/104-sensitive-data-masking-audit.sql): commit `0098206e53c105c2f55ae06512db0d570605da50`.
- [README navigation](README.md): commit `429dbc4bb55124f46073fce02a7c6f3bfad6662c`.
- Chapter and lab fetched back from GitHub `main`; README navigation re-fetched before tracker update. Targeted static/manual inspection covered chapter numbering, local relative paths, PostgreSQL 18/database guard, transaction-local timeouts, synthetic-only data, read-only transaction, deterministic two-way `EXCEPT ALL` assertions and rollback. Expected four claims, 200.00 total, four masked contacts, three complete synthetic audit events, and zero mismatches were reasoned from literals; **not observed PostgreSQL output**. The lab does not test real privileges, masking enforcement, or database audit logging.
- **Validation distinction:** authored/published yes; targeted manual/static inspection yes; independent editorial review no; comprehensive automated SQL parser/link QA no; isolated PostgreSQL 18 runtime execution no; retained runtime evidence none.
- **Progress: 104/120 published (86.7%); 16 remaining; Part 11 4/10. Next: 105 — Locks, blocking, deadlocks, and troubleshooting.**


## Chapter 105 publication evidence — 2026-11-12

- [Chapter 105](part-11-security-operations/105-locks-blocking-deadlocks-and-troubleshooting.md): initial commit `b213539a312a4ed4c3be25b2ec3b0cb487c72fe5`; correction commit `19725b05e03768dcd3c7cf09d83d0ca5d8bf6929`.
- [Synthetic read-only PostgreSQL 18 lab](labs/105-locks-blocking-deadlocks-troubleshooting.sql): commit `9e6a0a43f9b1091fc6703f56c12ac56e19410a5b`.
- [README navigation](README.md): commit `84dae78be40ce874d7e612dff7632f5d70c468be`.
- Chapter, lab and README fetched back from GitHub `main` before tracker update. Targeted static/manual inspection covered numbering and relative links, PostgreSQL 18/database guard, read-only transaction, local timeouts, no backend termination or induced deadlocks, five fictional graph edges, two direct-cycle participants, three noncycle waiters, two noncycle blocker IDs, bidirectional `EXCEPT ALL` assertions, and rollback. All expected counts are **reasoned, not observed PostgreSQL execution**. Actual `pg_locks` output is environment-dependent.
- **Validation distinction:** authored/published yes; targeted static/manual inspection yes; independent editorial review no; comprehensive automated SQL parser/link QA no; isolated PostgreSQL 18 runtime execution no; retained runtime evidence none.
- **Progress: 105/120 published (87.5%); 15 remaining; Part 11 5/10. Next: 106 — Backward-compatible migrations and deployment controls.**

## Chapter 106 publication evidence — 2026-11-12

- [Chapter 106](part-11-security-operations/106-backward-compatible-migrations-and-deployment-controls.md): initial commit `39ece264a0dabf702ce802a324ad17fc5a021b00`; prerequisite-link correction `75fb7ea2be774da44eecb99b64606e216bfe1b12`.
- [Synthetic read-only PostgreSQL 18 lab](labs/106-backward-compatible-migrations-deployment-controls.sql): commit `128f5aab09651dd53c74d3d1061aa568a7536ca9`.
- [README navigation](README.md): commit `1a95f6a94fcb24e60ede18feea1001e211c52ea9`.
- Chapter, lab, and README were fetched back from GitHub `main` before this tracker update. A broken Chapter 038 prerequisite link was detected and corrected; the corrected target was fetched successfully. Targeted static/manual inspection covered chapter numbering, links, PostgreSQL 18/database guard, read-only transaction, local timeouts, synthetic data, multiset assertions and rollback. Calculated expected results: 5 total rows, 3 copied, 2 missing, 5 compatible-visible, 2 divergent, contraction blocked. These are **not observed PostgreSQL output**.
- **Validation distinction:** authored/published yes; targeted static/manual reasoning yes; independent editorial review no; comprehensive automated SQL parser/link QA no; isolated PostgreSQL 18 runtime execution no; reproducible runtime evidence none. This is a synthetic migration-readiness model, not a live DDL or deployment test.
- **Progress: 106/120 published (88.3%); 14 remaining; Part 11 6/10. Next: 107 — Data quality assertions and reconciliation queries.**

## Chapter 107 publication evidence — 2026-11-12

- [Chapter 107](part-11-security-operations/107-data-quality-assertions-and-reconciliation-queries.md): commit `30dcdb2e713d12681d0c82cdf4f294e3e7aa3689`.
- [Synthetic read-only PostgreSQL 18 lab](labs/107-data-quality-assertions-reconciliation.sql): commit `159824cfb10ea471b361a04416315731cb3de050`.
- [README navigation](README.md): commit `3a5ab3976f88c97653490119eb57da1a91577fa6`.
- Chapter, lab, and README were fetched from GitHub `main` before tracker update. Targeted manual/static checks covered numbering, prerequisite links, synthetic-only values, database/version guard, read-only transaction, transaction-local timeouts, two-way `EXCEPT ALL` assertions, and rollback. Calculated expectations: 6 candidate rows, 1 duplicate-key group, 2 invalid rows, 1 orphan, 4 rows and 100.00 on each snapshot, 2 source-only and 2 target-only rows, promotion blocked. The lab assertion intentionally passes when it detects the expected **failed** quality gate. Expected values are reasoned, **not observed PostgreSQL output**.
- **Validation distinction:** authored/published yes; targeted static/manual reasoning yes; independent editorial review no; comprehensive parser-based SQL/link QA no; actual isolated PostgreSQL 18 runtime execution no; retained runtime evidence none.
- **Progress: 107/120 published (89.2%); 13 remaining; Part 11 7/10. Next: 108 — Backup, recovery, and restore-validation concepts.**

## Chapter 108 publication evidence — 2026-11-12

- [Chapter 108](part-11-security-operations/108-backup-recovery-and-restore-validation-concepts.md): original commit `fed84cdfabc2a8950d97c0b648bc784a0f50a9b7`; prerequisite-link correction `843401146f5dafc03b5675f00c0276fa3ffd432a`.
- [Synthetic read-only PostgreSQL 18 decision-model lab](labs/108-backup-recovery-restore-validation.sql): commit `c36db22a3d58079fb144a7288088d4d94dcf18b4`.
- [README navigation](README.md): commit `cb9f4b692f342cb2b61d66c35debc1a9df2064d2`.
- Chapter, lab, and README were fetched from GitHub `main` before this tracker update. Targeted static/manual inspection checked chapter numbering, prerequisite navigation (and corrected a missing Chapter 038 file link), synthetic-only data, PostgreSQL 18/database guard, read-only transaction, local timeouts, expected classification (one accepted, two blocked), and rollback. These results are calculated, not observed execution.
- **Validation distinction:** authored/published yes; targeted static/manual inspection yes; independent editorial review no; comprehensive SQL parser/link QA no; actual isolated PostgreSQL 18 execution no; retained runtime evidence none; actual backup/restore rehearsal not performed.
- **Progress: 108/120 published (90.0%); 12 remaining; Part 11 8/10. Next: 109 — Slow-query investigation, monitoring, and incident runbooks.**

## Chapter 109 publication evidence — 2026-11-12

- [Chapter 109](part-11-security-operations/109-slow-query-investigation-monitoring-and-incident-runbooks.md): commit `246e16d840f472f64daa7aa9cf691bdaec573b96`.
- [Synthetic read-only PostgreSQL 18 lab](labs/109-slow-query-monitoring-incident-runbook.sql): commit `76f3e573501699fd91698664f5995709222526cd`.
- [README navigation](README.md): commit `4f76b3510097a18f930bf2f4b6b63cb836485692`.
- Chapter and lab fetched back from GitHub main; prerequisite links to Chapters 091, 105, 108 and lab target checked; README navigation re-fetched before tracker update. Targeted static/manual inspection covered chapter numbering, read-only transaction, PostgreSQL 18/database guard, local timeouts, synthetic samples, exact bidirectional `EXCEPT ALL` assertions, and rollback. Expected six samples, three slow, two blocking, one plan-review and zero mismatches are **calculated, not observed PostgreSQL output**. No production telemetry or actual performance benchmark was collected.
- **Validation distinction:** authored/published yes; targeted static/manual checks yes; independent editorial review no; comprehensive parser-based SQL/link QA no; actual isolated PostgreSQL 18 runtime execution no; retained runtime evidence none.
- **Progress: 109/120 published (90.8%); 11 remaining; Part 11 9/10. Next: 110 — Lab 11: operational SQL incident and recovery exercise.**

## Chapter 110 publication evidence — 2026-11-12

- [Chapter 110](part-11-security-operations/110-lab-11-operational-sql-incident-and-recovery-exercise.md): commit `c539e987d8df6d6d5b737caf3d60c7f506db5e59`.
- [Synthetic read-only PostgreSQL 18 lab](labs/110-lab-11-operational-sql-incident-recovery.sql): commit `9853cc8ae82e968184daeff158abb058989eaa38`.
- [README navigation](README.md): commit `d5e8069e6d3210fe7d7d87f260d68a9b14962873`.
- GitHub `main` chapter and lab fetched back before tracker update. Targeted manual/static checks: numbering, expected values, synthetic-only inputs, PostgreSQL 18/database guard, read-only transaction, local timeouts, rollback, and prerequisite relative links. Corrected stale tracker headline and restored omitted Chapter 109 row. Expected: 4 query observations, 3 slow, 2 blocking, 1 plan review; 1 accepted and 2 blocked recovery candidates; 3 source/3 target records totaling 90.00 each, with 1 source-only and 1 target-only discrepancy; closure BLOCKED. **All expectations are calculated, not observed PostgreSQL output.**
- **Validation distinction:** authored/published yes; targeted static/manual inspection yes; independent editorial review no; comprehensive automated SQL syntax/link QA no; actual isolated PostgreSQL 18 runtime execution no; retained runtime evidence none; no real restore or incident drill performed.
- **Progress: 110/120 published (91.7%); 10 remaining; Part 11 complete (10/10). Next: 111 — OLTP versus OLAP query design.**

## Chapter 111 publication evidence — 2026-11-12

- [Chapter 111](part-12-platforms-capstone/111-oltp-versus-olap-query-design.md): original commit `61ef67725a1b6145f1cb0d9f18809fc7a72bd282`; arithmetic correction `a85b37c0bc6b7940f72589ddcbdbc0a0dd8dd46c`; future-link correction `347c982fed000f9bd044eeec7946c0ed5dd435bb`.
- [Synthetic read-only PostgreSQL 18 lab](labs/111-oltp-versus-olap-query-design.sql): original commit `4d7b6bf13cb2b9490a27e98e7f45cc50dc864dd4`; arithmetic correction `db609b7232b525126a7a721e4868b07c1c20dfe9`.
- [README navigation](README.md): commit `ac673b604df40d3a8abdf478cf618be743975e51`.
- Chapter and lab fetched back from GitHub `main` after publication; prerequisite links fetched successfully. Corrected a real manual arithmetic error before tracker update: joining order headers to seven lines sums to **260.00**, not 230.00; true revenue is 170.00, so the overcount is 90.00. Removed a link to unpublished Chapter 112. Targeted static/manual inspection checked numbering, synthetic-only dataset, database/version guard, read-only transaction, transaction-local timeouts, exact reconciliation assertion and rollback. README navigation published before tracker update. Expectations are **calculated, not observed PostgreSQL output**.
- **Validation distinction:** authored/published yes; targeted static/manual reasoning yes; independent editorial review no; comprehensive automated SQL parser/link QA no; actual isolated PostgreSQL 18 execution no; reproducible runtime evidence none.
- **Progress: 111/120 published (92.5%); 9 remaining; Part 12 1/10. Next: 112 — Star schemas, facts, dimensions, and surrogate keys.**

## Chapter 112 publication evidence — 2026-11-12

- [Chapter 112](part-12-platforms-capstone/112-star-schemas-facts-dimensions-and-surrogate-keys.md): commit `5ca0c819a4e0036c431c1c09e392641a108f1574`.
- [Synthetic read-only PostgreSQL 18 lab](labs/112-star-schema-facts-dimensions-surrogate-keys.sql): commit `20df3a7462b37eded17eab1346ec3bc28209d3ae`.
- [README navigation](README.md): commit `0f288093a55ac1f127b2a8f0e11c169bf013efef`.
- Chapter and lab fetched back from GitHub `main` before tracker update. Targeted static/manual review covered grain, historical dimension mapping, read-only/version/database guards, local timeouts, expected totals, and rollback. Calculated expectations: 4 fact rows, 3 product dimension versions, 100.00 correct revenue, Basic 60.00 and Premium 40.00, incorrect business-key join 6 rows / 170.00, zero assertion mismatches. These are calculated expectations, **not observed database results**.
- **Validation distinction:** authored/published yes; targeted static/manual reasoning yes; independent editorial review no; comprehensive automated SQL parser/link QA no; actual isolated PostgreSQL 18 execution no; retained runtime evidence none.
- **Progress: 112/120 published (93.3%); 8 remaining; Part 12 2/10. Next: 113 — ELT, incremental loads, and change data capture patterns.**

## Chapter 113 publication evidence — 2026-11-13

- [Chapter 113](part-12-platforms-capstone/113-elt-incremental-loads-and-change-data-capture-patterns.md): commit `42029b259979f8d84e9b66cc5e2eee45585130b0`; forward-link correction `957a71afd7f128078d1baf0af41b670f22511568`.
- [Synthetic read-only PostgreSQL 18 lab](labs/113-elt-incremental-loads-cdc-patterns.sql): commit `e44d00c3050072d59b77dc0af3e421b28e00c268`.
- [README navigation](README.md): commit `4ffe8f79222355686afac50bb59c3c66be90749f`.
- Chapter, lab and README were fetched back from GitHub `main` before this tracker update. Prerequisite Chapter 036 and Chapter 112 links checked; removed forward link to unpublished Chapter 114. Targeted static/manual reasoning checked synthetic CDC deduplication, latest-per-key ordering, tombstone, database/version guard, read-only transaction, timeouts, bidirectional EXCEPT ALL assertion and rollback. Expected 5 delivered messages, 4 unique events, 3 latest-key events, 2 active orders totaling 80.00, 1 tombstone and zero assertion mismatches are **calculated, not observed PostgreSQL results**.
- **Validation distinction:** authored/published yes; targeted static/manual checks yes; independent editorial review no; comprehensive parser-based SQL/link QA no; actual isolated PostgreSQL 18 runtime execution no; retained runtime evidence none. No real CDC connector, source checkpoint or production system was accessed.
- **Progress: 113/120 published (94.2%); 7 remaining; Part 12 3/10. Next: 114 — Data warehouse SQL and analytical cost considerations.**


### Chapter 114 checkpoint (2026-11-13)

Published chapter and synthetic read-only SQL lab on main; both fetched back successfully. Targeted manual/static arithmetic review: 4 orders, 6 lines, correct 200.00, fan-out 270.00. Independent editorial review, comprehensive automated static QA, and isolated PostgreSQL 18 runtime execution with retained evidence remain pending. Next: Chapter 115 — Portable SQL versus vendor-specific syntax and testing.

## Chapter 115 publication checkpoint — 2026-11-13

- [Chapter 115](part-12-platforms-capstone/115-portable-sql-versus-vendor-specific-syntax-and-testing.md): authored commit `8cfa7a4cd1132ff4fb46766fdb86e1a31fb11511`; prerequisite-link correction `5c685d85483cd96a9c4c1a55a2bcd421973c1458`.
- [Synthetic PostgreSQL 18 read-only lab](labs/115-portable-sql-dialect-testing.sql): commit `a87bd5b2e921b19512e3dd84f6c22216a49a3743`.
- [README navigation](README.md): commit `2a2fd658971d6cc132c02fde0a4deecf9ff8f9a2`.
- Fetched chapter, lab, README and prerequisite 036 from GitHub main after publication; corrected one missing prerequisite link. Targeted manual/static inspection checked synthetic dataset, read-only transaction, database/version guard, transaction-local timeouts, rollback, and calculated assertions: 4 orders, 3 known amounts, 1 NULL, total 120.00, East 40.00, West 80.00, two matching case-insensitive filters and identical 3-ID pages. Expected values are calculated, **not observed**.
- **Validation:** authored/published yes; targeted manual/static inspection yes; independent editorial review no; comprehensive automated SQL parser/link QA no; actual isolated PostgreSQL 18 execution no; cross-engine execution no; reproducible runtime evidence none.
- **Progress: 115/120 (95.8%), 5 remaining; Part 12: 5/10. Next: Chapter 116 — PostgreSQL 18 SQL: lab baseline and advanced features.**


## Chapter 116 publication checkpoint — 2026-11-13

- [Chapter 116](part-12-platforms-capstone/116-postgresql-18-sql-lab-baseline-and-advanced-features.md): initial commit `b7827a277a5300f1b8599bef0d961b9ef5765627`; prerequisite-link correction `c316df335f2314b63021ac49bff11379a308a216`.
- [Synthetic PostgreSQL 18 read-only lab](labs/116-postgresql-18-baseline-advanced-features.sql): commit `7fd152eeb977acb4c4b45ff9f4370298bf798158`.
- [README navigation](README.md): commit `b54e5067e931107592da6cc6d990c7d6c18b6c78`.
- Chapter, lab, README, and corrected prerequisite 084 were fetched back from GitHub `main` before this tracker update. Targeted static/manual checks covered synthetic CDC events, latest-event tie-breaker, delete tombstone semantics, exact-result `EXCEPT ALL` assertions, PostgreSQL version/database guards, read-only transaction, local timeouts and rollback. Calculated expectations: five events, three latest keys, two active orders, one tombstone, active amount 70.00, three generated integers, and zero assertion mismatches. **These are calculated, not observed SQL output.**
- **Validation distinction:** authored/published yes; targeted static/manual reasoning yes; independent editorial review no; comprehensive parser-based SQL/link QA no; actual isolated PostgreSQL 18 runtime execution no; retained reproducible runtime evidence none.
- **Progress: 116/120 (96.7%), four remaining; Part 12: 6/10. Next: Chapter 117 — MySQL and MariaDB: key syntax and behavior differences.**

## Chapter 117 publication checkpoint — 2026-11-13

- [Chapter 117](part-12-platforms-capstone/117-mysql-and-mariadb-key-syntax-and-behavior-differences.md): commit `2bc18f3845cbad184a58ef73392f6acf1449d89a`.
- [Synthetic PostgreSQL 18 read-only comparison lab](labs/117-mysql-mariadb-portability-comparison.sql): commit `84be53441b156b92bbcc4d8075ad0683c4c46a40`.
- [README navigation](README.md): commit `2b2f814f00ddee30e92381d72720b672284a746a`.
- Chapter and lab were fetched back from GitHub `main`; prerequisite Chapter 036 and 115 links were checked and README navigation was re-fetched. Targeted static/manual reasoning checked four synthetic orders, three known amounts, one NULL, known total 120.00, two case-normalized groups totaling 60.00 each, deterministic page IDs 102 and 103, and NULL-sensitive `NOT IN` versus `NOT EXISTS`. All expected values are **calculated, not observed SQL results**.
- **Validation:** authored/published yes; targeted static/manual inspection yes; independent editorial review no; comprehensive automated parser/link QA no; isolated PostgreSQL 18 runtime execution no; MySQL/MariaDB cross-engine execution no; retained reproducible runtime evidence none.
- **Progress: 117/120 (97.5%), three remaining; Part 12: 7/10. Next: Chapter 118 — SQL Server/T-SQL and Oracle SQL: key differences.**

## Chapter 118 publication checkpoint — 2026-11-13

- [Chapter 118](part-12-platforms-capstone/118-sql-server-tsql-and-oracle-sql-key-differences.md): commit `47a3a84f203af5aaa14f7ce66b9748ebd2ee890a`.
- [Synthetic read-only PostgreSQL 18 comparison lab](labs/118-sql-server-oracle-portability-comparison.sql): commit `9c79b0f324de1c8945fcab6665fd579147e71b21`.
- [README navigation](README.md): commit `8c1479ab99c17fc117e55f00beb5d5abdeed70be`.
- Chapter and lab were fetched back from GitHub main before updating this tracker. Targeted manual/static reasoning checked five synthetic orders, four priced orders, one NULL, total 100.00, East 45.00, West 55.00, page IDs 203 and 204, NULL-sensitive NOT IN versus NOT EXISTS, and bidirectional EXCEPT ALL assertions. Expected outputs are **calculated, not observed**.
- **Validation distinction:** authored/published yes; targeted static/manual inspection yes; independent editorial review no; comprehensive automated SQL parser/link QA no; actual isolated PostgreSQL 18 execution no; SQL Server/Oracle cross-engine execution no; reproducible runtime evidence none.
- **Progress: 118/120 (98.3%); 2 remaining; Part 12: 8/10. Next: Chapter 119 — Snowflake and BigQuery: cloud analytical SQL patterns.**

## Chapter 119 publication checkpoint — 2026-11-13

- [Chapter 119](part-12-platforms-capstone/119-snowflake-and-bigquery-cloud-analytical-sql-patterns.md): initial commit `2b364ef23e654543907e9fa97af249bb268d22ad`; first-day count correction `e7f1dec4010e3374e265e613aa7deb238e234fb0`.
- [Synthetic PostgreSQL 18 read-only comparison lab](labs/119-snowflake-bigquery-cloud-analytical-patterns.sql): commit `a8a34965a3491997394f958853d38e207f540dd3`.
- [README navigation](README.md): commit `3821060f2e79193a26efc697bc5b4702a9388906`.
- Chapter, lab and README were fetched back from GitHub `main`. Targeted manual/static checks reviewed the six synthetic events, three distinct keys, two active orders totaling 90.00, one delete tombstone, three first-day events, and exact multiset assertion design. All expected results are **calculated, not observed**.
- **Validation distinction:** authored/published yes; targeted static/manual inspection yes; independent editorial review no; comprehensive automated SQL parser/link QA no; isolated PostgreSQL 18 runtime execution no; Snowflake/BigQuery cross-engine execution no; retained runtime evidence none.
- **Progress: 119/120 (99.2%), one remaining; Part 12: 9/10. Next: Chapter 120 — Final capstone: end-to-end operational and analytical SQL project.**

## Chapter 120 publication checkpoint — 2026-11-13

- [Chapter 120](part-12-platforms-capstone/120-final-capstone-end-to-end-operational-and-analytical-sql-project.md): commit `3be15e59c01311009a9c32befb0419d71953c776`.
- [Synthetic read-only PostgreSQL 18 capstone lab](labs/120-final-capstone-operational-analytical-sql.sql): commit `f7089d6e6b6de8a633fab08dff7c5391d36bac41`.
- [README navigation](README.md): commit `48685a241551785707164e72734a67b23095b5be`.
- Chapter, lab, README and Chapter 107 prerequisite were fetched back from GitHub main. Targeted manual/static reasoning checks 7 deliveries, 6 unique event IDs, 4 latest orders, 3 active orders, one tombstone, East 70.00, West 30.00 and total 100.00. **These are calculated expectations, not observed database results.**
- **Validation distinction:** authored/published yes (120/120); targeted static/manual inspection of Chapter 120 yes; independent editorial review 0/120; comprehensive automated SQL parser/link QA not completed; actual isolated PostgreSQL 18 execution 0/120; retained reproducible runtime evidence none.
- **Next milestone:** stop authoring new chapters; conduct repository-wide static QA for links, SQL syntax and expected outputs; triage defects; execute labs against isolated PostgreSQL 18 with captured version, command, logs, results and reviewer approvals. Publication is not certification.

## Markdown local-link QA — Chapters 007–012 (2026-11-13)

- [Pinned-tree smoke-test evidence](labs/validation/MARKDOWN-LINK-SMOKE-007-012-2026-11-13.md), commit `b43393f251f88853f44d475d4c90a7b54316e4d4`.
- Git tree SHA `245d1b2c20593e6ccd45d063227bd12296ef9b6a`; 6 chapters inspected, 45 inline local-link occurrences checked, 0 missing local target paths. 26 external links observed but not tested; anchors and reference-style links not validated.
- Curriculum publication remains **120/120**. Independent editorial review **0/120**; actual isolated PostgreSQL 18 runtime validation **0/120**. This pass is **targeted static path checking only**, not comprehensive Markdown QA or SQL execution.
- **Next:** Chapters 013–018 local-link QA, then full Markdown-aware links/anchors, SQL syntax/expected-output and safety audit, followed by isolated PostgreSQL 18 runtime evidence.

## QA follow-up — Chapters 013–018 local-link smoke check (2026-11-13)

[Targeted evidence](labs/validation/MARKDOWN-LINK-SMOKE-013-018-2026-11-13.md), commit `87fffd17b59e2a6f51c93c2ed3a24db2d8f386ea`: 58 inline local-link occurrences checked against non-truncated `main` Git tree `c106089a06628e0743ba32723cbecdb3b01207ee`; zero missing local targets. 25 external URL occurrences were identified but not checked. Together with earlier targeted smoke checks, Chapters 001–018 have been covered for inline local path existence only. This is not comprehensive Markdown/anchor QA or SQL validation. Independent editorial review: **0/120**; actual isolated PostgreSQL 18 runtime validation: **0/120**. Next: Chapters 019–024 local-link QA, comprehensive Markdown-aware validation, SQL syntax/expected-output and safety checks, and isolated PostgreSQL 18 runtime evidence.


## QA follow-up — Chapters 019–024 local-link smoke check (2026-11-13)

[Targeted evidence](labs/validation/MARKDOWN-LINK-SMOKE-019-024-2026-11-13.md), commit `065377348e6059e43bffcd26c7b413df1fe8c9d7`: 57 inline local-link occurrences across Chapters 019–024 checked against complete Git tree `df18f97d391800b99db837de7b1a4dcbea8cfcca`, with zero missing tracked paths; 26 external URL occurrences identified but not tested. Targeted local-path smoke coverage now extends through Chapter 024 (24/120). This is not comprehensive Markdown/anchor QA or SQL validation. Independent editorial review: **0/120**; actual isolated PostgreSQL 18 runtime validation: **0/120**. Next: Chapters 025–030 local-link smoke check, then comprehensive Markdown/SQL and lab-safety audits followed by isolated PostgreSQL 18 runtime evidence.


## QA follow-up — Chapters 091–096 local-link smoke check (2026-11-14)

[Targeted evidence](labs/validation/MARKDOWN-LINK-SMOKE-091-096-2026-11-14.md), commit `b108bd016517585ba92119c91abc9c62005a1eb3`: 48 local inline Markdown link occurrences across Chapters 091–096 resolved against non-truncated Git tree `b5d9e28103c6784139a0985f10df3b920424145f`; zero missing tracked paths. 30 external HTTP(S) links identified but not tested. Six PostgreSQL 18 labs inspected for textual read-only transaction, version guard, and rollback; **not executed**. Cumulative targeted local-link path coverage: **96/120** chapters. This is not comprehensive Markdown/anchor QA, SQL correctness, expected-output or lab-safety certification. Authored/published **120/120**; independent editorial review **0/120**; actual isolated PostgreSQL 18 runtime validation **0/120**. Next: Chapters 097–102 targeted local-link QA, then comprehensive static/SQL review and isolated PostgreSQL 18 runtime acceptance with reproducible evidence.

## QA follow-up — Chapters 097–102 local-link smoke check (2026-11-14)

[Targeted evidence](labs/validation/MARKDOWN-LINK-SMOKE-097-102-2026-11-14.md), commit `0662a4feaf630dc98f507dbe82a4e891b0d30d33`: 50 inline local Markdown link occurrences across Chapters 097–102 checked against complete Git tree `b785c6a9300c56b4225f1a2ced5c5d83a6e3990a`; zero missing tracked paths. 34 external HTTP(S) occurrences identified but not tested. Six SQL labs inspected textually for `BEGIN READ ONLY;`, `ROLLBACK;`, and PostgreSQL 18 version guards; SQL not executed. Cumulative targeted local-link path coverage: **102/120** chapters. This is not comprehensive Markdown/anchor QA, SQL correctness, expected-output or lab-safety certification. Authored/published **120/120**; independent editorial review **0/120**; actual isolated PostgreSQL 18 runtime validation **0/120**. Next: Chapters 103–108 targeted link QA, comprehensive static/SQL review and isolated PostgreSQL 18 runtime acceptance with reproducible evidence.

## QA follow-up — Chapters 103–108 local-link smoke check (2026-11-14)

[Targeted evidence](labs/validation/MARKDOWN-LINK-SMOKE-103-108-2026-11-14.md), commit `03d512db2c41eea8d281c3dfc134b534146079e2`: 41 inline local Markdown links checked across Chapters 103–108 against non-truncated Git tree `ff06c5e947be47afc3f99f5fc6a4cac511530319`; zero missing tracked targets. 32 external HTTP(S) occurrences identified but not tested. Six corresponding labs were inspected for textual read-only transaction, rollback and version guards, but SQL was not executed. Evidence was fetched back from GitHub `main` before this tracker update. Cumulative targeted inline local-path smoke coverage: **108/120** chapters. This does not establish comprehensive Markdown/anchor QA, SQL correctness, expected outputs, or lab safety certification. Authored/published **120/120**; independent editorial review **0/120**; actual isolated PostgreSQL 18 runtime validation **0/120**. Next: Chapters 109–114 targeted link QA, then 115–120, comprehensive static/SQL review and isolated PostgreSQL 18 runtime acceptance.

## QA follow-up — Chapters 109–114 local-link smoke check (2026-11-14)

[Targeted evidence](labs/validation/MARKDOWN-LINK-SMOKE-109-114-2026-11-14.md), commit `f9004611b3fb92921f09fcc052272a16d269d9f7`: checked 33 local inline Markdown link occurrences across Chapters 109–114 against non-truncated Git tree `801d9f2800fcbcacbc71b0897b0f1b795b7e2707`; zero missing tracked paths. Identified 28 external HTTP(S) occurrences without testing them. Read six corresponding SQL labs and observed textual transaction/version guards, but did not execute them. Cumulative targeted local-path smoke coverage: **114/120** chapters. This is not comprehensive Markdown/anchor QA, SQL syntax or expected-output verification, or lab-safety certification. Independent editorial review: **0/120**; actual isolated PostgreSQL 18 runtime validation: **0/120**. Next: Chapters 115–120 targeted local-link QA, then comprehensive static QA and isolated PostgreSQL 18 runtime acceptance with reproducible evidence.

## QA follow-up — Chapters 115–120 local-link smoke check (2026-11-14)

[Targeted evidence](labs/validation/MARKDOWN-LINK-SMOKE-115-120-2026-11-14.md), commit `be17ebcddb9b6b13634e258b742db214639c20be`: 45 local inline Markdown link occurrences checked against complete, non-truncated Git tree `bd43a00f505d72327aa729846084829c716b3be8`; zero missing tracked file targets. 39 external HTTP(S) occurrences identified but not tested. Six corresponding labs inspected for textual read-only transaction, rollback and version-check references; SQL not executed. **Initial targeted inline local-file path smoke coverage: 120/120 chapters.** This does not establish comprehensive Markdown/anchor QA, SQL correctness, expected outputs, external-link validity, or lab safety. Authored/published: **120/120**; independent editorial review: **0/120**; actual isolated PostgreSQL 18 runtime validation: **0/120**. **Next:** comprehensive Markdown-aware links/anchors and external references, SQL syntax/expected-output/safety audit, then isolated PostgreSQL 18 runtime acceptance with reproducible evidence and issue tracking.


## QA follow-up — Chapters 001–006 Markdown structural audit (2026-11-14)

[Targeted structural evidence](labs/validation/MARKDOWN-STRUCTURE-AUDIT-001-006-2026-11-14.md), published in commit `dfc19811ad2a12022c44542aea5cb43dc3794f6f` and fetched back from `main`: six Part 01 chapter files inspected; 84 heading lines, 84 code-fence delimiter lines (even counts in all six files), 34 local inline links, 28 external inline links, and zero inline fragment links. This is a **limited textual structural audit of 6/120 chapters**, distinct from previously completed **120/120 targeted local-file path smoke coverage**. It does not establish full Markdown parsing/anchor correctness, external URL validity, SQL syntax, expected-output accuracy or lab safety. Independently editorially reviewed **0/120**; actually PostgreSQL 18 runtime-validated **0/120**. Next: Chapters 007–012 structural audit, then repository-wide Markdown-aware link/anchor verification, SQL and expected-output review, safety checks, and isolated PostgreSQL 18 runtime acceptance with evidence.
