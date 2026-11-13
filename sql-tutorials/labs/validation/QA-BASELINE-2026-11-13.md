# SQL Tutorials — QA baseline (2026-11-13)

## Scope and evidence boundary

All 120 numbered chapters are marked published in [STATUS-TRACKER](../../STATUS-TRACKER.md). This is an **initial targeted repository inspection**, not a completed repository-wide audit. Inspected the live `main` versions of [MASTER-TOC](../../MASTER-TOC.md), [README](../../README.md), [STATUS-TRACKER](../../STATUS-TRACKER.md), [Chapter 001](../../part-01-fundamentals/001-introduction-to-sql.md), [Chapter 120](../../part-12-platforms-capstone/120-final-capstone-end-to-end-operational-and-analytical-sql-project.md), and [Lab 120](../120-final-capstone-operational-analytical-sql.sql). GitHub source fetch is **not** SQL execution.

## Findings and corrections

- **QA-001 (fixed):** MASTER-TOC introduction still called the completed curriculum a proposed plan. Updated to distinguish 120 published chapters from pending validation. Commit: `af9e1c9b4b79b161524760ea46b32836ecaa8134`.
- **QA-002 (fixed):** Chapter 001 described the already-published Chapter 002 as planned. Corrected publication wording. Commit: `579996d942d8213d9ae47ecf98af809f0fb81709`.
- **QA-003 (fixed, documentation consistency):** Moved README's `How chapters are developed`, `Important safety rule`, and introductory-lab note below the complete numbered chapter index. Verified the updated `main` README still has exactly 120 numbered chapter entries (001–120), with no missing or duplicate numbers; this is an index-numbering check, **not** a repository-wide link-target check. Commit: `d8047202e239bf41dc5a9f21d5506a1b2f4e97bb`.
- **QA-004 (open, runtime evidence):** Lab 120 has a PostgreSQL 18 database/version guard, read-only transaction, local timeouts, synthetic CTE data, exact-result assertion and ROLLBACK. Expected regional totals of 70.00 and 30.00 are consistent with the displayed synthetic rows by manual reasoning. **No isolated PostgreSQL 18 execution was performed**; the SQL syntax and assertion behavior are not certified.
- **QA-005 (open, coverage):** Full 120-chapter relative-link resolution, SQL parser checks, and executable lab acceptance have not yet been completed. No global PASS status is warranted.

## Validation matrix

| Area | State | Evidence |
|---|---|---|
| Authored/published | 120/120 reported by tracker | Main-branch tracker inspection |
| Targeted editorial checks | Partial, not independent certification | Corrections QA-001 and QA-002 |
| Repository-wide static links and numbering | Pending | No full filesystem crawl yet |
| SQL syntax and expected-output review | Partial manual reasoning for Lab 120 | No SQL parser/runtime output |
| PostgreSQL 18 isolated runtime acceptance | 0/120 confirmed | No executable PostgreSQL 18 evidence |
| Cross-engine dialect validation | Pending | No MySQL/Oracle/SQL Server/Snowflake/BigQuery execution |

## Next acceptance sequence

1. Enumerate all tracked files under `sql-tutorials/` at a pinned `main` SHA; reconcile 001–120 chapter files and referenced lab paths, duplicates and missing targets.
2. Check every local Markdown link relative to its containing file, including anchors and case sensitivity; emit machine-readable failures with source path and line.
3. Extract SQL code fences and `labs/*.sql`, classify portable versus PostgreSQL-specific code and intentional negative examples; check parseability and review all expected outputs without treating static inspection as execution.
4. Provision a disposable PostgreSQL **18** instance and a dedicated `sql_tutorials` database. Execute approved labs with `psql -X -v ON_ERROR_STOP=1`, capture `SELECT version()`, command, exit status, redacted stdout/stderr, Git SHA and timestamp per lab. Isolate any DDL/DML labs, verify rollback and no persistent changes. Never connect to production.
5. Track each defect with reproduction, severity, owner, fix SHA and rerun evidence. Update status counts only after independently checkable results.

**Certification gate:** Publication does not imply independent review, comprehensive static QA, or runtime acceptance.
