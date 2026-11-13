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

36. [036 — UPSERT and MERGE patterns across SQL dialects](part-04-data-modification/036-upsert-and-merge-patterns-across-sql-dialects.md) — published; [isolated rollback-only PostgreSQL 18 lab](labs/036-upsert-merge-patterns.sql); targeted static reasoning only; independent editorial review, comprehensive SQL syntax verification, and actual PostgreSQL 18 runtime validation pending.

37. [037 — RETURNING, OUTPUT, and write verification](part-04-data-modification/037-returning-output-and-write-verification.md) — published; [isolated rollback-only PostgreSQL 18 lab](labs/037-returning-output-write-verification.sql); targeted static inspection only; independent editorial review, comprehensive syntax checks and PostgreSQL 18 runtime execution pending.

38. [038 — BEGIN, COMMIT, ROLLBACK, and SAVEPOINT](part-04-data-modification/038-begin-commit-rollback-and-savepoint.md) — published; [isolated rollback-only PostgreSQL 18 lab](labs/038-begin-commit-rollback-savepoint.sql); targeted static reasoning only; independent editorial review, comprehensive syntax verification and PostgreSQL 18 runtime execution pending.

39. [039 — Isolation levels and common transaction anomalies](part-04-data-modification/039-isolation-levels-and-common-transaction-anomalies.md) — published; [read-only PostgreSQL 18 lab](labs/039-isolation-levels-transaction-anomalies.sql); targeted static reasoning only; independent editorial review, comprehensive SQL syntax verification and PostgreSQL 18 runtime validation pending.

40. [040 — Lab 04: complete a safe, auditable transaction workflow](part-04-data-modification/040-lab-04-complete-a-safe-auditable-transaction-workflow.md) — published; [isolated rollback-only PostgreSQL 18 lab](labs/040-lab-04-safe-auditable-transaction.sql); targeted static reasoning only; independent editorial review, comprehensive SQL syntax verification, and PostgreSQL 18 runtime validation pending. Part 04 complete.

41. [041 — Join fundamentals and relationship cardinality](part-05-joins/041-join-fundamentals-and-relationship-cardinality.md) — published; [isolated rollback-only PostgreSQL 18 lab](labs/041-join-fundamentals-cardinality.sql); targeted static inspection only; independent editorial review, comprehensive SQL syntax verification and PostgreSQL 18 runtime execution pending. Part 05: 1/10.

42. [042 — INNER JOIN: matched records](part-05-joins/042-inner-join-matched-records.md) — published; [isolated rollback-only PostgreSQL 18 lab](labs/042-inner-join-matched-records.sql); targeted static reasoning only; independent editorial review, comprehensive SQL syntax checks, and actual PostgreSQL 18 runtime validation pending. Part 05: 2/10.

43. [043 — LEFT OUTER JOIN: preserve unmatched left rows](part-05-joins/043-left-outer-join-preserve-unmatched-left-rows.md) — published; [isolated rollback-only PostgreSQL 18 lab](labs/043-left-outer-join-unmatched-rows.sql); targeted static reasoning only; independent editorial review, comprehensive SQL syntax and link QA, and actual PostgreSQL 18 runtime validation pending. Part 05: 3/10.

44. [044 — RIGHT and FULL OUTER JOIN: applicability and portability](part-05-joins/044-right-and-full-outer-join-applicability-and-portability.md) — published; [isolated rollback-only PostgreSQL 18 lab](labs/044-right-full-outer-join.sql); targeted static reasoning only; independent editorial review, comprehensive syntax/link QA and actual PostgreSQL 18 runtime validation pending. Part 05: 4/10.

45. [045 — CROSS JOIN and SELF JOIN](part-05-joins/045-cross-join-and-self-join.md) — published; [isolated rollback-only PostgreSQL 18 lab](labs/045-cross-join-self-join.sql); targeted static reasoning only; independent editorial review, comprehensive static QA, and actual PostgreSQL 18 runtime validation pending. Part 05: 5/10.

46. [046 — Multi-table joins and join condition design](part-05-joins/046-multi-table-joins-and-join-condition-design.md) — published; [isolated rollback-only PostgreSQL 18 lab](labs/046-multi-table-joins-condition-design.sql); targeted static reasoning only; independent editorial review, comprehensive syntax/link QA and actual PostgreSQL 18 runtime validation pending. Part 05: 6/10.

47. [047 — One-to-many and many-to-many relationships](part-05-joins/047-one-to-many-and-many-to-many-relationships.md) — published; [isolated rollback-only PostgreSQL 18 lab](labs/047-one-to-many-many-to-many.sql); targeted static reasoning only; independent editorial review, comprehensive syntax/link QA and PostgreSQL 18 runtime execution pending. Part 05: 7/10.

48. [048 — Semi-joins and anti-joins using EXISTS and NOT EXISTS](part-05-joins/048-semi-joins-and-anti-joins-using-exists-and-not-exists.md) — published; [isolated rollback-only PostgreSQL 18 lab](labs/048-exists-not-exists-semi-anti-joins.sql); targeted static reasoning only; independent editorial review, comprehensive syntax/link QA and PostgreSQL 18 runtime execution pending. Part 05: 8/10.

49. [049 — Diagnose duplicate rows, fan-out, and NULL join pitfalls](part-05-joins/049-diagnose-duplicate-rows-fan-out-and-null-join-pitfalls.md) — published; [isolated rollback-only PostgreSQL 18 lab](labs/049-duplicate-rows-fanout-null-join-pitfalls.sql); targeted static reasoning only; independent editorial review, comprehensive SQL syntax/link QA and PostgreSQL 18 runtime execution pending. Part 05: 9/10.

50. [050 — Lab 05: consolidate customers, orders, and payments](part-05-joins/050-lab-05-consolidate-customers-orders-and-payments.md) — published; [isolated rollback-only PostgreSQL 18 lab](labs/050-lab-05-consolidate-customers-orders-payments.sql); targeted static reasoning only; independent editorial review, comprehensive SQL syntax/link QA, and actual PostgreSQL 18 runtime execution pending. Part 05 complete (10/10).

51. [051 — COUNT, SUM, AVG, MIN, and MAX](part-06-aggregation/051-count-sum-avg-min-and-max.md) — published; [isolated rollback-only PostgreSQL 18 lab](labs/051-count-sum-avg-min-max.sql); targeted static reasoning only; independent editorial review, comprehensive syntax/link QA, and actual PostgreSQL 18 runtime validation pending. Part 06: 1/10.

52. [052 — GROUP BY and aggregation grain](part-06-aggregation/052-group-by-and-aggregation-grain.md) — published; [isolated rollback-only PostgreSQL 18 lab](labs/052-group-by-aggregation-grain.sql); targeted static reasoning only; independent editorial review, comprehensive SQL syntax/link QA, and actual PostgreSQL 18 runtime execution pending. Part 06: 2/10.

53. [053 — HAVING versus WHERE](part-06-aggregation/053-having-versus-where.md) — published; [isolated rollback-only PostgreSQL 18 lab](labs/053-having-versus-where.sql); targeted static reasoning only; independent editorial review, comprehensive SQL syntax/link QA, and actual PostgreSQL 18 runtime execution pending. Part 06: 3/10.

54. [054 — Conditional aggregation with CASE and FILTER](part-06-aggregation/054-conditional-aggregation-with-case-and-filter.md) — published; [isolated rollback-only PostgreSQL 18 lab](labs/054-conditional-aggregation-case-filter.sql); targeted static reasoning only; independent editorial review, comprehensive SQL syntax/link QA, and actual PostgreSQL 18 runtime execution pending. Part 06: 4/10.

55. [055 — Date-based grouping and time buckets](part-06-aggregation/055-date-based-grouping-and-time-buckets.md) — published; [isolated rollback-only PostgreSQL 18 lab](labs/055-date-based-grouping-time-buckets.sql); targeted static reasoning only; independent editorial review, comprehensive SQL syntax/link QA and actual PostgreSQL 18 runtime execution pending. Part 06: 5/10.

56. [056 — Text transformations for reporting](part-06-aggregation/056-text-transformations-for-reporting.md) — published; [isolated rollback-only PostgreSQL 18 lab](labs/056-text-transformations-for-reporting.sql); targeted static reasoning only; independent editorial review, comprehensive SQL syntax/link QA, and actual PostgreSQL 18 runtime execution pending. Part 06: 6/10.

57. [057 — Numeric rounding, ratios, and safe division](part-06-aggregation/057-numeric-rounding-ratios-and-safe-division.md) — published; [isolated rollback-only PostgreSQL 18 lab](labs/057-numeric-rounding-ratios-safe-division.sql); targeted static reasoning only; independent editorial review, comprehensive SQL syntax/link QA and actual PostgreSQL 18 runtime execution pending. Part 06: 7/10.

58. [058 — ROLLUP, CUBE, and GROUPING SETS](part-06-aggregation/058-rollup-cube-and-grouping-sets.md) — published; [isolated rollback-only PostgreSQL 18 lab](labs/058-rollup-cube-grouping-sets.sql); targeted static reasoning only; independent editorial review, comprehensive SQL syntax/link QA, and actual PostgreSQL 18 runtime validation pending. Part 06: 8/10.

59. [059 — Pivoting and unpivoting: portable and vendor features](part-06-aggregation/059-pivoting-and-unpivoting-portable-and-vendor-features.md) — published; [isolated rollback-only PostgreSQL 18 lab](labs/059-pivoting-unpivoting-portable-vendor.sql); targeted static reasoning only; independent editorial review, comprehensive SQL syntax/link QA, and actual PostgreSQL 18 runtime validation pending. Part 06: 9/10.

60. [060 — Lab 06: build a monthly KPI report](part-06-aggregation/060-lab-06-build-a-monthly-kpi-report.md) — published; [isolated rollback-only PostgreSQL 18 lab](labs/060-lab-06-monthly-kpi-report.sql); targeted static reasoning only; independent editorial review, comprehensive automated SQL syntax/link QA, and actual isolated PostgreSQL 18 runtime execution pending. Part 06 complete (10/10).

## Part 07 — Subqueries, CTEs & Set Operations

61. [061 — Scalar subqueries and derived tables](part-07-subqueries/061-scalar-subqueries-and-derived-tables.md) — published; [read-only synthetic PostgreSQL 18 lab](labs/061-scalar-subqueries-derived-tables.sql); targeted static reasoning only; independent editorial review, comprehensive syntax/link QA, and actual isolated PostgreSQL 18 runtime execution pending. Part 07: 1/10.

62. [062 — IN, ANY, ALL, and multi-row subqueries](part-07-subqueries/062-in-any-all-and-multi-row-subqueries.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/062-in-any-all-multi-row-subqueries.sql); targeted static reasoning only; independent editorial review, comprehensive syntax/link QA, and actual isolated PostgreSQL 18 runtime execution pending. Part 07: 2/10.

63. [063 — EXISTS versus IN and NULL-sensitive behavior](part-07-subqueries/063-exists-versus-in-and-null-sensitive-behavior.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/063-exists-versus-in-null-sensitive.sql); targeted static inspection only; independent editorial review, comprehensive SQL syntax/link QA, and actual isolated PostgreSQL 18 runtime execution pending. Part 07: 3/10.

64. [064 — Correlated subqueries and performance tradeoffs](part-07-subqueries/064-correlated-subqueries-and-performance-tradeoffs.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/064-correlated-subqueries-performance.sql); targeted static reasoning only; independent editorial review, comprehensive syntax/link QA, and actual isolated PostgreSQL 18 runtime execution pending. Part 07: 4/10.

65. [065 — Common table expressions (WITH)](part-07-subqueries/065-common-table-expressions-with.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/065-common-table-expressions-with.sql); targeted static reasoning only; independent editorial review, comprehensive SQL syntax/link QA, and actual isolated PostgreSQL 18 runtime execution pending. Part 07: 5/10.

66. [066 — Recursive CTEs and hierarchical queries](part-07-subqueries/066-recursive-ctes-and-hierarchical-queries.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/066-recursive-ctes-hierarchical-queries.sql); targeted static inspection only; independent editorial review, comprehensive syntax/link QA and actual isolated PostgreSQL 18 execution pending. Part 07: 6/10.

67. [067 — UNION versus UNION ALL](part-07-subqueries/067-union-versus-union-all.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/067-union-versus-union-all.sql); targeted static reasoning only; independent editorial review, comprehensive syntax/link QA, and actual isolated PostgreSQL 18 runtime execution pending. Part 07: 7/10.

68. [068 — INTERSECT and EXCEPT (MINUS in some systems)](part-07-subqueries/068-intersect-and-except.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/068-intersect-except-set-operations.sql); targeted static reasoning only; independent editorial review, comprehensive syntax/link QA, and actual isolated PostgreSQL 18 runtime execution pending. Part 07: 8/10.

69. [069 — Refactor complex SQL for readability and correctness](part-07-subqueries/069-refactor-complex-sql-for-readability-and-correctness.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/069-refactor-complex-sql.sql); targeted static reasoning only; independent editorial review, comprehensive SQL syntax/link QA, and actual isolated PostgreSQL 18 runtime execution pending. Part 07: 9/10.

70. [070 — Lab 07: query a multi-level organizational hierarchy](part-07-subqueries/070-lab-07-query-a-multi-level-organizational-hierarchy.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/070-lab-07-organizational-hierarchy.sql); targeted static reasoning only; independent editorial review, comprehensive syntax/link QA, and isolated PostgreSQL 18 runtime validation pending. Part 07 complete (10/10).

## Part 08 — Window Functions & Advanced Analytics

71. [071 — Window-function anatomy: OVER, PARTITION BY, ORDER BY](part-08-window-functions/071-window-function-anatomy-over-partition-by-order-by.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/071-window-function-anatomy.sql); targeted static inspection and expected-output reasoning only. Independent editorial review, comprehensive automated SQL syntax/link QA and actual isolated PostgreSQL 18 runtime validation pending. Part 08: 1/10.

72. [072 — ROW_NUMBER, RANK, and DENSE_RANK](part-08-window-functions/072-row-number-rank-and-dense-rank.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/072-row-number-rank-dense-rank.sql); targeted static reasoning only. Independent editorial review, comprehensive automated SQL syntax/link QA and actual isolated PostgreSQL 18 runtime execution pending. Part 08: 2/10.

73. [073 — LAG and LEAD for change analysis](part-08-window-functions/073-lag-and-lead-for-change-analysis.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/073-lag-lead-change-analysis.sql); targeted static reasoning only. Independent editorial review, comprehensive automated SQL syntax/link QA and actual isolated PostgreSQL 18 runtime execution pending. Part 08: 3/10.

74. [074 — Running totals and cumulative measures](part-08-window-functions/074-running-totals-and-cumulative-measures.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/074-running-totals-cumulative-measures.sql); targeted static reasoning only. Independent editorial review, comprehensive SQL syntax/link QA and actual isolated PostgreSQL 18 runtime validation pending. Part 08: 4/10.

75. [075 — Rolling averages and moving windows](part-08-window-functions/075-rolling-averages-and-moving-windows.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/075-rolling-averages-moving-windows.sql); targeted static reasoning only. Independent editorial review, comprehensive automated SQL syntax/link QA and actual isolated PostgreSQL 18 runtime execution pending. Part 08: 5/10.

76. [076 — FIRST_VALUE, LAST_VALUE, and window frames](part-08-window-functions/076-first-value-last-value-and-window-frames.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/076-first-last-value-window-frames.sql); targeted static reasoning only. Independent editorial review, comprehensive SQL syntax/link QA and actual isolated PostgreSQL 18 runtime execution pending. Part 08: 6/10.

77. [077 — NTILE, percentiles, and distribution analysis](part-08-window-functions/077-ntile-percentiles-and-distribution-analysis.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/077-ntile-percentiles-distribution.sql); targeted static inspection and manual expected-result reasoning only. Independent editorial review, comprehensive automated SQL syntax/link QA and actual isolated PostgreSQL 18 runtime execution pending. Part 08: 7/10.

78. [078 — Gaps-and-islands patterns](part-08-window-functions/078-gaps-and-islands-patterns.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/078-gaps-and-islands-patterns.sql); targeted static inspection and expected-result reasoning only. Independent editorial review, comprehensive automated SQL syntax/link QA, and actual isolated PostgreSQL 18 runtime execution pending. Part 08: 8/10.

79. [079 — Cohort analysis, retention, and event sequencing](part-08-window-functions/079-cohort-analysis-retention-and-event-sequencing.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/079-cohort-retention-event-sequencing.sql); targeted static reasoning only. Independent editorial review, comprehensive automated SQL syntax/link QA, and actual isolated PostgreSQL 18 runtime execution pending. Part 08: 9/10.

80. [080 — Lab 08: produce an analytical customer activity report](part-08-window-functions/080-lab-08-produce-an-analytical-customer-activity-report.md) — published; [synthetic read-only PostgreSQL 18 capstone lab](labs/080-lab-08-analytical-customer-activity-report.sql); targeted static reasoning only. Independent editorial review, comprehensive automated SQL syntax/link QA and actual isolated PostgreSQL 18 runtime execution pending. Part 08 complete (10/10).

## Part 09 — SQL Objects, Functions & Semi-Structured Data

81. [081 — String functions and regular expressions](part-09-functions-views-json/081-string-functions-and-regular-expressions.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/081-string-functions-and-regular-expressions.sql); targeted static reasoning only. Independent editorial review, comprehensive automated SQL syntax/link QA, and actual PostgreSQL 18 runtime execution pending. Part 09: 1/10.

82. [082 — Dates, intervals, timestamps, and time zones](part-09-functions-views-json/082-dates-intervals-timestamps-and-time-zones.md) — published; [read-only PostgreSQL 18 lab](labs/082-dates-intervals-timestamps-time-zones.sql); targeted static reasoning completed; independent editorial review, comprehensive static QA and actual PostgreSQL 18 runtime validation pending.

83. [083 — Numeric expressions and precision considerations](part-09-functions-views-json/083-numeric-expressions-and-precision-considerations.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/083-numeric-expressions-precision.sql); targeted static reasoning only. Independent editorial review, comprehensive SQL syntax/link QA, and actual PostgreSQL 18 runtime validation pending. Part 09: 3/10.

84. [084 — JSON and semi-structured SQL queries](part-09-functions-views-json/084-json-and-semi-structured-sql-queries.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/084-json-semi-structured-queries.sql); targeted static inspection only. Independent editorial review, comprehensive SQL syntax/link QA and isolated PostgreSQL 18 runtime validation pending. Part 09: 4/10.

85. [085 — Views and secure abstraction](part-09-functions-views-json/085-views-and-secure-abstraction.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/085-views-secure-abstraction.sql); targeted static inspection only. Independent editorial review, comprehensive automated SQL syntax/link QA and actual isolated PostgreSQL 18 runtime validation pending. Part 09: 5/10.

86. [086 — Materialized views and refresh strategies](part-09-functions-views-json/086-materialized-views-and-refresh-strategies.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/086-materialized-views-refresh-strategies.sql); targeted static reasoning only. Independent editorial review, comprehensive SQL syntax/link QA, and isolated PostgreSQL 18 runtime validation pending. Part 09: 6/10.

87. [087 — Temporary tables and intermediate result sets](part-09-functions-views-json/087-temporary-tables-and-intermediate-result-sets.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/087-temporary-tables-intermediate-results.sql); targeted static reasoning only. Independent editorial review, comprehensive automated SQL syntax/link QA and actual isolated PostgreSQL 18 runtime execution pending. Part 09: 7/10.

88. [088 — Stored functions and procedures: dialect-specific syntax](part-09-functions-views-json/088-stored-functions-and-procedures-dialect-specific-syntax.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/088-stored-functions-and-procedures.sql); targeted static/manual reasoning only. Independent editorial review, comprehensive SQL syntax/link QA and actual isolated PostgreSQL 18 runtime execution pending. Part 09: 8/10.

89. [089 — Triggers, dynamic SQL, and parameterization safeguards](part-09-functions-views-json/089-triggers-dynamic-sql-and-parameterization-safeguards.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/089-triggers-dynamic-sql-parameterization.sql); targeted static/manual reasoning only. Independent editorial review, comprehensive automated SQL syntax/link QA and actual isolated PostgreSQL 18 runtime execution pending. Part 09: 9/10.

90. [090 — Lab 09: build reusable reporting objects](part-09-functions-views-json/090-lab-09-build-reusable-reporting-objects.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/090-lab-09-reusable-reporting-objects.sql); targeted static/manual reasoning only. Independent editorial review, comprehensive automated SQL syntax/link QA, and actual isolated PostgreSQL 18 runtime execution pending. Part 09 complete (10/10).

## Part 10 — SQL Performance & Query Optimization

91. [091 — Read execution plans with EXPLAIN](part-10-performance/091-read-execution-plans-with-explain.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/091-read-execution-plans-with-explain.sql); targeted static reasoning only. Independent editorial review, comprehensive SQL syntax/link QA, and actual isolated PostgreSQL 18 runtime execution pending. Part 10: 1/10.

92. [092 — Table scans, index scans, row estimates, and selectivity](part-10-performance/092-table-scans-index-scans-row-estimates-and-selectivity.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/092-scans-estimates-selectivity.sql); targeted static/manual reasoning only. Independent editorial review, comprehensive SQL syntax/link QA, and isolated PostgreSQL 18 runtime validation pending. Part 10: 2/10.

93. [093 — B-tree indexes and common index access patterns](part-10-performance/093-btree-indexes-and-common-index-access-patterns.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/093-btree-index-access-patterns.sql); targeted static/manual reasoning only. Independent editorial review, comprehensive automated SQL syntax/link QA, and actual isolated PostgreSQL 18 runtime validation pending. Part 10: 3/10.

94. [094 — Composite indexes and column order](part-10-performance/094-composite-indexes-and-column-order.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/094-composite-indexes-column-order.sql); targeted static/manual reasoning only. Independent editorial review, comprehensive parser-based SQL/link QA, and actual isolated PostgreSQL 18 runtime validation pending. Part 10: 4/10.

95. [095 — Partial, expression, and covering indexes](part-10-performance/095-partial-expression-and-covering-indexes.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/095-partial-expression-covering-indexes.sql); targeted static/manual reasoning only. Independent editorial review, comprehensive automated SQL syntax/link QA, and actual isolated PostgreSQL 18 runtime execution pending. Part 10: 5/10.

96. [096 — Optimizer statistics and PostgreSQL maintenance basics](part-10-performance/096-optimizer-statistics-and-postgresql-maintenance-basics.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/096-optimizer-statistics-maintenance.sql); targeted static/manual reasoning only. Independent editorial review, comprehensive automated SQL syntax/link QA and actual isolated PostgreSQL 18 runtime execution pending. Part 10: 6/10.

97. [097 — Make predicates index-friendly and rewrite expensive SQL](part-10-performance/097-make-predicates-index-friendly-and-rewrite-expensive-sql.md) — published; [read-only PostgreSQL 18 lab](labs/097-index-friendly-predicates-rewrites.sql); targeted static/manual checks completed; independent editorial review, comprehensive SQL syntax/link QA, and actual PostgreSQL 18 runtime execution pending. Part 10: 7/10.

98. [098 — Optimize joins, aggregations, and subqueries](part-10-performance/098-optimize-joins-aggregations-and-subqueries.md) — published; [read-only PostgreSQL 18 lab](labs/098-optimize-joins-aggregations-subqueries.sql); targeted static reasoning only, independent review and runtime validation pending.

99. [099 — Keyset pagination, benchmarking, and regression tests](part-10-performance/099-keyset-pagination-benchmarking-and-regression-tests.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/099-keyset-pagination-benchmark-regression.sql); targeted static/manual reasoning only. Independent editorial review, comprehensive SQL syntax/link QA and actual PostgreSQL 18 runtime execution pending. Part 10: 9/10.

100. [100 — Lab 10: baseline, tune, and remeasure a slow query](part-10-performance/100-lab-10-baseline-tune-and-remeasure-a-slow-query.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/100-lab-10-baseline-tune-remeasure.sql); targeted static/manual reasoning only. Independent editorial review, comprehensive SQL syntax/link QA, and actual PostgreSQL 18 runtime execution pending. Part 10 complete (10/10).

## Part 11 — Security, Data Quality & DBRE/SRE Operations

101. [101 — Least privilege and SQL access-control principles](part-11-security-operations/101-least-privilege-and-sql-access-control-principles.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/101-least-privilege-access-control.sql); targeted static/manual reasoning only. Independent editorial review, comprehensive SQL syntax/link QA, and isolated PostgreSQL 18 runtime validation pending. Part 11: 1/10.

102. [102 — Users, roles, GRANT, REVOKE, and ownership](part-11-security-operations/102-users-roles-grant-revoke-and-ownership.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/102-users-roles-grant-revoke-ownership.sql); targeted static/manual checks only. Independent editorial review, comprehensive SQL syntax/link QA, and actual isolated PostgreSQL 18 runtime validation pending. Part 11: 2/10.

103. [103 — Row-level security and data-access policies](part-11-security-operations/103-row-level-security-and-data-access-policies.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/103-row-level-security-data-access-policies.sql); targeted static/manual reasoning only. Independent editorial review, comprehensive parser-based SQL/link QA and actual isolated PostgreSQL 18 runtime execution pending. Part 11: 3/10.

104. [104 — Sensitive data protection, masking, and audit requirements](part-11-security-operations/104-sensitive-data-protection-masking-and-audit-requirements.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/104-sensitive-data-masking-audit.sql); targeted static/manual inspection only. Independent editorial review, comprehensive parser-based SQL/link QA and actual isolated PostgreSQL 18 runtime execution pending. Part 11: 4/10.
105. [105 — Locks, blocking, deadlocks, and troubleshooting](part-11-security-operations/105-locks-blocking-deadlocks-and-troubleshooting.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/105-locks-blocking-deadlocks-troubleshooting.sql); targeted static/manual checks only. Independent editorial review, comprehensive SQL syntax/link QA, and actual isolated PostgreSQL 18 runtime execution pending. Part 11: 5/10.
106. [106 — Backward-compatible migrations and deployment controls](part-11-security-operations/106-backward-compatible-migrations-and-deployment-controls.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/106-backward-compatible-migrations-deployment-controls.sql); targeted static/manual inspection only. Independent editorial review, comprehensive parser-based SQL/link QA, and actual isolated PostgreSQL 18 runtime execution pending. Part 11: 6/10.

107. [107 — Data quality assertions and reconciliation queries](part-11-security-operations/107-data-quality-assertions-and-reconciliation-queries.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/107-data-quality-assertions-reconciliation.sql); targeted static/manual reasoning only. Independent editorial review, comprehensive SQL syntax/link QA, and actual isolated PostgreSQL 18 runtime validation pending. Part 11: 7/10.
108. [108 — Backup, recovery, and restore-validation concepts](part-11-security-operations/108-backup-recovery-and-restore-validation-concepts.md) — published; [synthetic read-only PostgreSQL 18 acceptance-model lab](labs/108-backup-recovery-restore-validation.sql); targeted static inspection only. No real restore performed. Independent editorial review, comprehensive parser/link QA, and actual PostgreSQL 18 execution pending. Part 11: 8/10.

109. [109 — Slow-query investigation, monitoring, and incident runbooks](part-11-security-operations/109-slow-query-investigation-monitoring-and-incident-runbooks.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/109-slow-query-monitoring-incident-runbook.sql); targeted static/manual checks only. Independent editorial review, comprehensive SQL syntax/link QA, and actual isolated PostgreSQL 18 runtime validation pending. Part 11: 9/10.

110. [110 — Lab 11: operational SQL incident and recovery exercise](part-11-security-operations/110-lab-11-operational-sql-incident-and-recovery-exercise.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/110-lab-11-operational-sql-incident-recovery.sql); targeted static/manual inspection only. Independent editorial review, comprehensive SQL syntax/link QA, and actual PostgreSQL 18 runtime execution pending. No real incident or restore tested. Part 11 complete (10/10).

## Part 12 — Data Engineering, SQL Dialects & Final Projects

111. [111 — OLTP versus OLAP query design](part-12-platforms-capstone/111-oltp-versus-olap-query-design.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/111-oltp-versus-olap-query-design.sql); targeted static/manual reasoning only. Independent editorial review, comprehensive SQL syntax/link QA, and actual isolated PostgreSQL 18 runtime execution pending. Part 12: 1/10.

112. [112 — Star schemas, facts, dimensions, and surrogate keys](part-12-platforms-capstone/112-star-schemas-facts-dimensions-and-surrogate-keys.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/112-star-schema-facts-dimensions-surrogate-keys.sql); targeted static/manual reasoning completed; independent review, comprehensive SQL/link QA, and actual PostgreSQL 18 runtime validation pending.

113. [113 — ELT, incremental loads, and change data capture patterns](part-12-platforms-capstone/113-elt-incremental-loads-and-change-data-capture-patterns.md) — published; [synthetic read-only PostgreSQL 18 lab](labs/113-elt-incremental-loads-cdc-patterns.sql); targeted static/manual inspection only; independent editorial review, comprehensive SQL/link QA, and actual isolated PostgreSQL 18 runtime validation pending. Part 12: 3/10.

114. [114 — Data Warehouse SQL and Analytical Cost Considerations](part-12-platforms-capstone/114-data-warehouse-sql-and-analytical-cost-considerations.md) — published; [read-only PostgreSQL 18 lab](labs/114-data-warehouse-sql-analytical-cost.sql); targeted static inspection only; independent review and runtime validation pending.
