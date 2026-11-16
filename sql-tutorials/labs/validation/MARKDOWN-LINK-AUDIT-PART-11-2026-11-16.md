# Part 11 — Scoped Markdown Link-Path Audit (2026-11-16)

## Scope and provenance

- Repository: `sssamant21/data-platform-engineering-tutorials`, branch `main`.
- Pinned complete recursive Git tree: `73132ef85117046d1246a8a7a065e6f3766f09e3` (1,696 entries; `truncated=false`).
- Inspected ten existing chapter Markdown files, `sql-tutorials/part-11-security-operations/101-*.md` through `110-*.md`.
- The audit read the current `MASTER-TOC.md`, `README.md`, and `STATUS-TRACKER.md` before proceeding. All 120 chapters are already published; no additional chapter authoring is warranted.

## Method

Extracted Markdown inline link destinations matching `[label](destination)` (excluding image links), resolved relative paths against each chapter's parent directory, normalized `.` and `..` components, and compared against the pinned, non-truncated repository tree. External HTTP(S) URLs were counted, not contacted. A separate scoped scan counted fragment occurrences and reference-style link definitions. This is pattern-based path checking, not a full Markdown parser.

| Chapter | Local paths | External URLs |
|---|---:|---:|
| 101 | 7 | 6 |
| 102 | 7 | 7 |
| 103 | 7 | 5 |
| 104 | 7 | 6 |
| 105 | 7 | 5 |
| 106 | 8 | 5 |
| 107 | 9 | 5 |
| 108 | 6 | 6 |
| 109 | 10 | 5 |
| 110 | 6 | 5 |
| **Total** | **74** | **55** |

## Findings

- **74 local inline link paths checked; 0 missing tracked targets.**
- **55 external HTTP(S) link occurrences inventoried; 0 external URLs verified.**
- **0 fragment occurrences** and **0 reference-style link definitions** detected by the scoped patterns.
- No chapter or lab source was modified; no defect was established within this scope.

## Validation boundaries

This does **not** establish GitHub-rendered anchor validity, comprehensive Markdown/reference-style parsing, external URL health, SQL parser correctness, independent editorial review, real security/locking/backup integration tests, or PostgreSQL 18 runtime validation. No SQL was executed. The lab examples use synthetic data and do not establish production readiness.

## Progress and next work

- Authored and published: **120/120**.
- Previously reported targeted SQL static review: **120/120** (not repeated in this audit).
- Scoped Markdown path audits: **110/120** after this batch.
- Independent editorial review: **0/120**.
- Actually runtime-validated on isolated PostgreSQL 18: **0/120**.

Next: Part 12 (111–120) scoped link-path audit; comprehensive Markdown links/anchors and SQL parser QA; isolated PostgreSQL 18 execution with reproducible version, environment, commands, expected/actual output, and cleanup evidence.
