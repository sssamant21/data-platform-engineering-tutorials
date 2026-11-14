# Targeted local-link smoke check — Chapters 067–072

**Date:** 2026-11-13 (America/New_York)  
**Repository:** `sssamant21/data-platform-engineering-tutorials`, branch `main`  
**Scope:** `sql-tutorials/` only

## Method

Read the current `main` copies of `MASTER-TOC.md`, `README.md`, `STATUS-TRACKER.md`, and Chapters 067–072. Extracted ordinary inline Markdown links with a regular expression and classified relative paths versus HTTP(S) URLs. Fetched all distinct linked local chapter/lab files and checked that the shared root documentation files were readable. Repeated occurrences were counted individually. Fragments were not programmatically validated; headings/anchors, reference-style links, images, and complex Markdown syntax require a separate parser-based pass. External links were counted, not visited.

## Findings

| Chapter | Local inline link occurrences | External HTTP(S) occurrences |
|---|---:|---:|
| 067 — UNION versus UNION ALL | 5 | 4 |
| 068 — INTERSECT and EXCEPT | 6 | 4 |
| 069 — Refactor complex SQL | 5 | 4 |
| 070 — Organizational hierarchy lab | 6 | 4 |
| 071 — Window function anatomy | 7 | 4 |
| 072 — ROW_NUMBER, RANK, DENSE_RANK | 5 | 4 |
| **Total** | **34** | **24** |

**Result:** 0 missing paths among the 34 local inline link occurrences. Distinct linked chapter and lab targets were fetched successfully. `MASTER-TOC.md`, `README.md`, and `STATUS-TRACKER.md` were also fetched from `main`.

## Limits and next work

This is a **targeted static path smoke check only**. It does not certify complete Markdown parsing, heading fragments, external URL reachability, SQL syntax, SQL expected results, safe lab execution, or editorial quality. No SQL was executed. No PostgreSQL 18 runtime acceptance evidence was collected. Independent editorial review remains **0/120** and actual isolated PostgreSQL 18 runtime validation remains **0/120**.

Cumulative chapter coverage for targeted local-link checks: **72/120**. Next: Chapters **073–078** targeted path checks, then comprehensive repository-wide Markdown/anchor, SQL, safety and isolated PostgreSQL 18 acceptance work.
