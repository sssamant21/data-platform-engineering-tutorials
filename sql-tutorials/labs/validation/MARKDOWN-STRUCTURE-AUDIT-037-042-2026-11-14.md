# Targeted Markdown structural audit — Chapters 037–042 (2026-11-14)

## Scope and method

Read current `main` versions of `sql-tutorials/MASTER-TOC.md`, `README.md`, `STATUS-TRACKER.md`, six chapters 037–042, and their six corresponding PostgreSQL 18 SQL labs. Counted physical lines, ATX heading lines, backtick-fence delimiter candidates, inline local Markdown link occurrences, and inline external HTTP(S) link occurrences using simple textual patterns. These checks do not implement a full Markdown parser, validate heading fragments, check external URLs, or prove SQL correctness.

| Chapter | Physical lines | ATX headings | Backtick-fence candidates | Inline local links | Inline external links |
|---|---:|---:|---:|---:|---:|
| 037 | 145 | 8 | 8 | 6 | 6 |
| 038 | 113 | 8 | 6 | 8 | 7 |
| 039 | 123 | 12 | 6 | 7 | 4 |
| 040 | 112 | 8 | 2 | 9 | 5 |
| 041 | 126 | 11 | 6 | 8 | 3 |
| 042 | 126 | 9 | 10 | 7 | 3 |
| **Total** | **745** | **56** | **38** | **45** | **28** |

All six files had even backtick-fence candidate counts. Even counts alone do not establish properly paired or correctly nested fences. External URLs were identified, not checked. The previously recorded 120/120 local-path smoke checks remain separate and do not constitute comprehensive Markdown/anchor validation.

## Findings and corrections

Three stale references to already-published successor chapters were repaired, then fetched back from `main`:
- Chapter 038 now links directly to Chapter 039 (commit `f580485968d0fa63f26862a8206e0361427ad577`).
- Chapter 041 now links directly to Chapter 042 (commit `285e19bd197f17f4ca596db6ebf9ffc73501a5c7`).
- Chapter 042 now links directly to Chapter 043 (commit `49c0914aabe0148b0d6920861c0e869547446a75`).

## Lab safety inspection and validation boundaries

Six matching SQL files were read. All six mention PostgreSQL version checks and transaction/rollback controls; five include synthetic temporary-table work, while Chapter 039 is explicitly read-only and single-session, not a demonstration of concurrent anomalies. These are **textual observations**, not independently tested safety controls. DML and temporary DDL exercises must run only on a verified disposable PostgreSQL 18 database using non-production credentials. **No SQL was executed.** No runtime acceptance, expected-output certification, comprehensive SQL syntax certification, or independent editorial review is claimed.

## Progress and next work

- Authored/published: **120/120** chapters.
- Prior targeted local-file path smoke checks: **120/120**.
- Cumulative limited Markdown structural text audit: **42/120** chapters.
- Independently editorially reviewed: **0/120**.
- Actually isolated PostgreSQL 18 runtime-validated with reproducible evidence: **0/120**.

Next: Chapters 043–048 structural audit; full Markdown-aware link and anchor resolution; SQL correctness, expected-output, and lab-safety review; isolated PostgreSQL 18 runtime acceptance with captured environment/version and command/output evidence.
