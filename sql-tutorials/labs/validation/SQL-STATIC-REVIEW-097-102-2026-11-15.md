# Targeted SQL static review — Chapters 097–102

**Date:** 2026-11-15 (America/New_York)  
**Scope:** Six existing chapter Markdown files and six matching SQL lab files, inspected from GitHub `main`. No new chapters authored: curriculum already 120/120.

## Scope and evidence

| Chapter | Focus | Source-based expected checks |
|---|---|---|
| 097 | Index-friendly predicates | Date range IDs 2,3,4; amount 90; case-insensitive IDs 1,2; numeric rewrite IDs 3,4,5 |
| 098 | Joins and aggregation grain | Correct order totals (101:50/50, 102:40/40, 103:10/0); naive join 5 rows; line total 100; settled total 90; EXISTS 101,102 |
| 099 | Keyset pagination | Three ordered pages: 109,108,107 / 106,105,104 / 103,102,101; 9 unique rows, 3 pages; tie-breaker included |
| 100 | Query rewrite capstone | 12 synthetic orders; tenant 10 PAID on Nov 1: four orders, 100.00 revenue; two-way EXCEPT ALL comparison |
| 101 | Least privilege | Nine synthetic policy rows; four allowed grants; no missing/extra allowed grants |
| 102 | Roles and ownership | Three synthetic principals, one membership, two approved grants, one rejected candidate; two-way multiset assertion |

The lab scripts explicitly use `BEGIN READ ONLY`, `ROLLBACK`, statement and lock timeouts, and checks for database name `sql_tutorials` and PostgreSQL major version 18. Database-name/version checks **do not establish isolation**. No real roles, grants, physical indexes, or object ownership changes are exercised. The chapter Markdown explicitly distinguishes portable SQL concepts from PostgreSQL-specific behavior.

## Findings and limits

- **No targeted arithmetic or expected-result contradiction identified** by manual static reasoning for the six lab fixtures.
- **Coverage gap, not a lab failure:** Chapters 097–100 use inline `VALUES`/CTEs and `EXPLAIN` without persistent indexed tables; they cannot demonstrate measured speedups, buffer differences, index access paths, or production regression acceptance.
- **Coverage gap, not a lab failure:** Chapters 101–102 model permissions using synthetic rows. They do not validate effective privileges, membership inheritance, ownership, default grants, or actual `GRANT`/`REVOKE` behavior.
- **Security caution:** The Chapter 101–102 introspection queries return information about the connected lab role, not the simulated principals. Do not interpret them as access-control certification.
- No comprehensive Markdown-aware link/anchor audit, independent editorial review, SQL parser check, PostgreSQL execution, or benchmark was performed during this review.
- **Actual PostgreSQL 18 runtime-validated chapters: 0/120** (previously reported); no isolated PostgreSQL 18 execution evidence was generated.

## Next acceptance work

Review Chapters **103–108** for SQL semantics and expected outputs. Independently perform repository-wide Markdown link and anchor verification, parser-based SQL syntax checking, and PostgreSQL 18 isolated runtime execution with captured version, environment identity, commands, stdout/stderr, and exit status. For Chapters 097–102, add separate disposable integration tests for physical indexes/plans and effective role privileges before claiming operational acceptance.

**Status:** Targeted static expected-output inspection complete for Chapters 097–102; cumulative targeted static review **102/120 (85%)**. Previously reported structural inspection **120/120**. Authored/published **120/120**. Independent editorial review **0/120**. Actual isolated PostgreSQL 18 runtime validation **0/120**.
