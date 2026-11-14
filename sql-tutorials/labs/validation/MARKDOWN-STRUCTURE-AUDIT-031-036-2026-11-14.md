# Targeted Markdown structural audit — Chapters 031–036

Date: 2026-11-14  
Branch: `main`  
Scope: `sql-tutorials/` only

## Method and evidence boundaries

Fetched the current `main` versions of `MASTER-TOC.md`, `README.md`, `STATUS-TRACKER.md`, six Part 04 chapter Markdown files and their six matching SQL labs through the GitHub connector. Counted physical lines, ATX heading lines, lines beginning with triple-backtick fence delimiters, and Markdown inline link occurrences with a textual regular-expression scan. These are **limited structural indicators**, not a full CommonMark parser, anchor resolver, SQL parser, external-link checker, or editorial certification.

| Chapter | Physical lines | ATX headings | Backtick fence candidate lines | Local inline links | External inline links |
|---|---:|---:|---:|---:|---:|
| 031 | 113 | 8 | 8 | 12 | 4 |
| 032 | 114 | 9 | 6 | 9 | 4 |
| 033 | 123 | 9 | 8 | 9 | 4 |
| 034 | 128 | 9 | 10 | 9 | 5 |
| 035 | 125 | 10 | 8 | 9 | 5 |
| 036 | 141 | 9 | 8 | 10 | 5 |
| **Total** | **744** | **54** | **48** | **58** | **27** |

All six files have even numbers of candidate triple-backtick fence lines. This is not proof of correctly nested/closed Markdown fences. No new publication/navigation wording marked `planned` or `coming soon` was detected by the targeted scan; the word `planned` appears in Chapter 034's recovery discussion and is not a navigation issue.

## Matching lab inspection

| Chapter | Lab | Textual observations |
|---|---|---|
| 031 | [SQL](../031-insert-single-row-and-multi-row-records.sql) | PostgreSQL version reference, temporary table, transaction and rollback present |
| 032 | [SQL](../032-insert-select-bulk-loading.sql) | PostgreSQL version reference, temporary table, transaction and rollback present |
| 033 | [SQL](../033-update-safe-predicates-preview.sql) | PostgreSQL version reference, temporary table, transaction and rollback present |
| 034 | [SQL](../034-delete-safe-predicates-referential-implications.sql) | PostgreSQL version reference, temporary table, transaction and rollback present |
| 035 | [SQL](../035-delete-truncate-drop.sql) | PostgreSQL 18/database/standby guard, temporary objects, transaction and rollback; contains actual DELETE/TRUNCATE/DROP statements against temporary objects |
| 036 | [SQL](../036-upsert-merge-patterns.sql) | PostgreSQL 18/database/standby guard, temporary objects, transaction and rollback; contains actual INSERT/UPSERT/MERGE statements against temporary objects |

**Important:** These are potentially modifying SQL exercises. The existence of a guard, transaction and `ROLLBACK` does not certify safe execution. Use only an independently verified disposable PostgreSQL 18 instance and synthetic data, never production systems or credentials. No SQL was executed during this audit.

## Findings and next actions

1. No obvious unmatched fence **by parity** in this six-chapter sample; full Markdown parsing and heading-anchor validation remain open.
2. No new stale successor-navigation label found in Chapters 031–036 by the targeted phrase scan. Previously recorded stale navigation issues in earlier chapters remain separately tracked.
3. The 27 external inline links were counted but **not** contacted or validated.
4. SQL syntax, semantic correctness, expected outputs, actual transaction behavior and rollback safety are **not certified**.
5. Continue with Chapters 037–042 targeted structural QA. Prioritize complete Markdown-aware anchor/link validation, SQL syntax and expected-output checks, and reproducible isolated PostgreSQL 18 runtime acceptance.

## Progress at this checkpoint

- Authored and published: **120/120**.
- Initial targeted local-file path smoke coverage: **120/120**.
- Targeted structural audit coverage after this batch: **36/120**.
- Independent editorial review: **0/120**.
- Actual isolated PostgreSQL 18 runtime validation: **0/120**.

This report records textual inspection only and makes no runtime-validation claim.
