# Targeted Markdown link smoke check — Chapters 091–096 (2026-11-14)

## Scope and provenance

Repository: `sssamant21/data-platform-engineering-tutorials`, branch `main`, exclusively `sql-tutorials/`.
Pinned, non-truncated Git tree: `b5d9e28103c6784139a0985f10df3b920424145f`.

Read `MASTER-TOC.md`, `README.md`, `STATUS-TRACKER.md`, six chapter Markdown files (091–096) and their six associated PostgreSQL 18 lab SQL files. Checked inline Markdown link destinations by normalizing each local relative path against its chapter directory and testing existence in the pinned Git tree. This is a **path existence smoke test**, not heading-anchor validation or a complete Markdown parser.

| Chapter | Local inline link occurrences | Missing tracked paths | External HTTP(S) links (not tested) |
|---|---:|---:|---:|
| 091 | 6 | 0 | 4 |
| 092 | 7 | 0 | 4 |
| 093 | 8 | 0 | 6 |
| 094 | 9 | 0 | 5 |
| 095 | 9 | 0 | 5 |
| 096 | 9 | 0 | 6 |
| **Total** | **48** | **0** | **30** |

All six lab files contain a textual `BEGIN READ ONLY;`, PostgreSQL version guard, and `ROLLBACK;`. This is **not** proof of SQL syntax correctness, transaction safety, or successful execution. The synthetic inline VALUES examples are not representative index benchmarks. No SQL was executed, no production access was attempted, and no PostgreSQL 18 runtime evidence was produced.

## Status and next acceptance work

- Authored/published curriculum: **120/120** (pre-existing).
- Cumulative targeted local-inline-link smoke coverage after this check: **96/120** chapters.
- Independent editorial certification: **0/120**.
- Actually executed and validated on isolated PostgreSQL 18: **0/120**.
- Still pending: full Markdown parser and anchor checks, external reference checks, SQL syntax and expected-output review, lab safety assessment, independent editorial review, and isolated PostgreSQL 18 runtime acceptance with reproducible logs.
- Next targeted batch: **097–102**. Do not confuse this smoke check with comprehensive static QA.
