# Part 12 — Scoped Markdown link-path audit (2026-11-16)

## Scope and provenance

- Repository: `sssamant21/data-platform-engineering-tutorials`, branch `main`.
- Pinned complete recursive Git tree: `0ffb0def6f51bd1a65512d9184fb3f6792cc08d6`; `truncated=false`.
- Files inspected: all ten chapter Markdown files under `sql-tutorials/part-12-platforms-capstone/` (111–120).
- Method: inspect Markdown inline links using a scoped regular-expression scan, resolve relative destinations against the source chapter directory, normalize `.` and `..`, and compare against tracked paths in the pinned Git tree. HTTP(S) URLs inventoried but not requested. Scan reference-style definitions and inline fragments separately.
- This method is intentionally **not** a CommonMark parser and may miss complex links, code-context distinctions, images with unusual syntax, and rendered anchors.

## Per-chapter results

| Chapter | Local inline paths checked | External HTTP(S) occurrences | Fragment occurrences |
|---|---:|---:|---:|
| 111 | 5 | 4 | 0 |
| 112 | 5 | 5 | 0 |
| 113 | 5 | 4 | 0 |
| 114 | 5 | 5 | 0 |
| 115 | 6 | 6 | 0 |
| 116 | 10 | 6 | 0 |
| 117 | 6 | 7 | 0 |
| 118 | 6 | 8 | 0 |
| 119 | 12 | 6 | 0 |
| 120 | 8 | 6 | 0 |
| **Total** | **68** | **57** | **0** |

**Findings:** Zero missing tracked targets among 68 scoped local inline links. Zero reference-style definitions detected by the scoped pattern. No fragment occurrences detected. External URLs were **not** tested.

## Interpretation and follow-up

- Scoped local Markdown path audit coverage now totals **120/120 chapters** (Parts 01–12). This does **not** certify comprehensive Markdown link correctness.
- Previously reported targeted SQL static review: **120/120**; this audit does not independently repeat those checks.
- Independent editorial review: **0/120**.
- Isolated PostgreSQL 18 runtime-validated chapters: **0/120**. No SQL was executed for this audit.
- Next: comprehensive Markdown parser validation (including anchors, reference links, fenced-code exclusion, and external references), SQL syntax/parser and expected-output QA, then execute labs on an isolated PostgreSQL 18 instance with retained version, commands, outputs, and pass/fail evidence.
- Use synthetic data only. Do not execute DDL or DML against production.
