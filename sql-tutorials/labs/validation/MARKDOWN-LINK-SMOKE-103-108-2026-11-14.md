# Targeted Markdown link smoke check — Chapters 103–108 (2026-11-14)

## Scope and baseline

- Repository: `sssamant21/data-platform-engineering-tutorials`, branch `main`.
- Pinned non-truncated recursive Git tree: `ff06c5e947be47afc3f99f5fc6a4cac511530319` (`truncated: false`).
- Read current `MASTER-TOC.md`, `README.md`, `STATUS-TRACKER.md` and all six chapter files 103–108.
- Chapters cover row-level security, sensitive-data masking/auditing, locks/deadlocks, safe migrations, data quality, and backup/restore concepts.

## Results

| Check | Observed result |
|---|---:|
| Chapter Markdown files read | 6 |
| Inline local Markdown link occurrences resolved against tracked Git paths | 41 |
| Missing tracked local target paths | **0** |
| External HTTP(S) link occurrences identified, **not checked** | 32 |
| Associated SQL lab files read | 6 |
| Lab files containing textual `BEGIN READ ONLY;` | 6 |
| Lab files containing textual `ROLLBACK;` | 6 |
| Lab files containing PostgreSQL version-guard text | 6 |

Local link resolution normalized `..` and `.` relative to each chapter directory, removed URL fragments and query strings for file-path checks, and matched paths against the full tracked Git tree. This is a limited regex-based **inline Markdown path-existence smoke check**, not a full Markdown parser. Heading fragments, reference-style links, generated anchors, case-sensitive URL behavior, and external URLs were **not** validated.

The SQL labs were inspected textually, not executed. The Chapter 103 lab explicitly models tenant isolation without testing actual PostgreSQL RLS enforcement; Chapter 104 models masking/audit metadata without a live authorization or audit test; Chapter 105 uses a fictional wait-for graph without inducing real contention; Chapter 108 models restore acceptance rather than performing a restore. Transaction markers alone do **not** certify lab safety, syntactic correctness, or expected outputs.

## Validation state

- Authored/published chapters: **120/120** (existing curriculum; no new chapter authored).
- Targeted inline local-link smoke coverage after this pass: **108/120** chapters.
- Independently editorially reviewed: **0/120**.
- Actually PostgreSQL 18 runtime-validated: **0/120**; no SQL executed or runtime evidence captured.
- Comprehensive Markdown/anchor QA, SQL syntax, expected-output verification, cross-engine portability, and lab safety certification: **pending**.

## Next work

Inspect Chapters 109–114 and their labs for targeted local-link existence; then finish 115–120. Follow with repository-wide Markdown-aware anchors/links, SQL semantic/syntax and expected-output checks, lab safety review, and isolated PostgreSQL 18 execution with version, commands, output, and reproducible evidence. Do not infer operational recovery or RLS certification from synthetic read-only models.
