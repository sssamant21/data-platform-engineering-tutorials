# Targeted local-link smoke check — Chapters 115–120 (2026-11-14)

## Scope and provenance
- Repository: `sssamant21/data-platform-engineering-tutorials`, branch `main`.
- Complete, non-truncated Git tree used for path existence: `bd43a00f505d72327aa729846084829c716b3be8`.
- Chapters 115–120, plus six corresponding `sql-tutorials/labs/*.sql` files, fetched from `main`.
- Checked inline Markdown links matching `[label](target)` (including image syntax), resolving relative paths and ignoring fragments for **file existence only**.
- This smoke check does not parse reference-style links, validate fragment anchors, check external HTTP status, validate SQL syntax or expected results, or execute SQL.

## Results

| Chapter | Local inline link occurrences | External HTTP(S) link occurrences | Missing local file targets |
|---|---:|---:|---:|
| 115 | 5 | 6 | 0 |
| 116 | 9 | 6 | 0 |
| 117 | 6 | 7 | 0 |
| 118 | 6 | 8 | 0 |
| 119 | 11 | 6 | 0 |
| 120 | 8 | 6 | 0 |
| **Total** | **45** | **39** | **0** |

All 45 local inline-link occurrences resolved to existing tracked paths in the full Git tree. External links were counted, **not tested**.

## Corresponding lab inspection
- `labs/115-portable-sql-dialect-testing.sql`
- `labs/116-postgresql-18-baseline-advanced-features.sql`
- `labs/117-mysql-mariadb-portability-comparison.sql`
- `labs/118-sql-server-oracle-portability-comparison.sql`
- `labs/119-snowflake-bigquery-cloud-analytical-patterns.sql`
- `labs/120-final-capstone-operational-analytical-sql.sql`

All six files contain textual `BEGIN READ ONLY`, `ROLLBACK`, and version-check references. These are **presence checks**, not proof that statements are safe, syntactically valid, or executed. No database was contacted. No cross-engine runtime tests were performed.

## Status and follow-up
- Authored/published: **120/120** (as recorded in repository tracker).
- Targeted inline local-file path smoke coverage: **120/120** chapters, based on preceding evidence records and this pass.
- Independent editorial review: **0/120**.
- Actual isolated PostgreSQL 18 runtime validation: **0/120**.
- Next: comprehensive Markdown-aware links/anchors and external-reference checks; SQL syntax, expected-output and safety review; isolated PostgreSQL 18 execution with reproducible logs and explicit acceptance criteria. Do not treat link-smoke coverage as certification.
