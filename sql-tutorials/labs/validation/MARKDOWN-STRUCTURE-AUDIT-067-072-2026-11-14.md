# Targeted Markdown structural audit — Chapters 067–072

Date: 2026-11-14 (America/New_York). Scope: existing published chapters and corresponding SQL labs, inspected via GitHub connector on `main`. This is a limited static inspection, not an executable acceptance test.

| Chapter | Physical Markdown lines | ATX headings | Fence delimiter candidates | Inline local links | Inline external links | SQL lab lines |
|---|---:|---:|---:|---:|---:|---:|
| 067 UNION versus UNION ALL | 138 | 12 | 6 | 5 | 4 | 101 |
| 068 INTERSECT and EXCEPT | 127 | 10 | 6 | 6 | 4 | 106 |
| 069 Refactor complex SQL | 161 | 11 | 6 | 5 | 4 | 122 |
| 070 Organizational hierarchy lab | 119 | 8 | 2 | 6 | 4 | 95 |
| 071 Window-function anatomy | 156 | 8 | 8 | 7 | 4 | 67 |
| 072 ROW_NUMBER, RANK, DENSE_RANK | 164 | 8 | 6 | 5 | 4 | 82 |
| **Total** | **865** | **57** | **34** | **34** | **24** | **573** |

## Method and findings

- Counted physical lines, ATX headings, lines beginning with Markdown triple-backtick fences, and inline Markdown link occurrences by text pattern. All six fence delimiter candidate counts are even. This does **not** prove correct Markdown nesting, reference-style link resolution, local target existence, heading-anchor correctness, or HTTP availability.
- Checked six corresponding SQL lab texts for version references, `BEGIN READ ONLY`, `ROLLBACK`, and `statement_timeout`. All six contain textual matches for all four patterns. This is **not** a security review or proof of safe SQL execution.
- Scanned chapter text for `planned`, `coming soon`, and `not yet published`; none found in these six chapters. The scan does not prove all navigation links are correct.
- No SQL was executed, no PostgreSQL 18 server was provisioned, and no expected-output comparison or independent editorial review was performed. Do not interpret this report as PostgreSQL 18 runtime validation.

## Status and follow-up

- Authored/published: **120/120** (per repository tracker; not independently re-inventoried in this pass).
- Cumulative targeted structural audit: **72/120** (prior reported 66/120 plus these six).
- Previously reported targeted local-file path smoke coverage: **120/120**; this pass did not rerun it.
- Independently editorially reviewed: **0/120**.
- Actually runtime-validated against isolated PostgreSQL 18 with reproducible evidence: **0/120**.

Next: Chapters **073–078** targeted structural audit; comprehensive Markdown-aware links/anchors, SQL semantics and expected outputs, lab-safety assessment, then isolated PostgreSQL 18 runtime execution with captured version, commands, outputs, and reviewer evidence.