# Targeted local-link QA — Chapters 085–090 (2026-11-14)

## Scope and source
- Repository: `sssamant21/data-platform-engineering-tutorials`, branch `main`; exclusively `sql-tutorials/`.
- Complete, non-truncated Git tree at verification: `ca264bee67a03cd061c0a757723b31911f840833`.
- Six chapter Markdown files 085–090 were fetched from `main`; six corresponding lab SQL files were fetched for limited textual inspection.
- Chapter 088's broken prerequisite link `../part-04-transactions/038-begin-commit-rollback-and-savepoint.md` was corrected to `../part-04-data-modification/038-begin-commit-rollback-and-savepoint.md` in commit `ca264bee67a03cd061c0a757723b31911f840833`.

## Verified results

| Chapter | Local inline Markdown links | External HTTP(S) links identified (not tested) | Missing tracked local targets |
|---|---:|---:|---:|
| 085 | 9 | 5 | 0 |
| 086 | 8 | 5 | 0 |
| 087 | 6 | 5 | 0 |
| 088 | 7 | 5 | 0 |
| 089 | 8 | 5 | 0 |
| 090 | 10 | 6 | 0 |
| **Total** | **48** | **31** | **0** |

Local link targets were resolved relative to each chapter path, URL-decoded, stripped of fragments/query parameters, normalized, and checked for membership in the complete tracked Git tree.

## Limitations and next acceptance work
This targeted smoke check **does not** validate Markdown reference-style links, images, fragment/heading anchors, external URL reachability, SQL syntax, query results, or full lab safety. SQL labs were **not executed**; textual transaction delimiters alone do not establish safe execution. No independent editorial review or isolated PostgreSQL 18 runtime validation was performed. Retain independent review at **0/120** and actual PostgreSQL 18 runtime validation at **0/120**.

Next: Chapters 091–096 targeted local-link QA, followed by comprehensive Markdown/anchor QA, SQL correctness and expected-output review, isolated PostgreSQL 18 execution with reproducible evidence, and issue tracking.
