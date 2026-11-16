# SQL Tutorials — Part 03 scoped Markdown link-path audit (2026-11-16)

## Scope and method
- Repository: `sssamant21/data-platform-engineering-tutorials`, branch `main`.
- Chapters: 021–030, ten Markdown files under `sql-tutorials/part-03-modeling/`.
- Fetched all ten chapter contents and a GitHub recursive tree of **1,688 entries** with `truncated=false`.
- Extracted inline Markdown links with a regular-expression scan, decoded percent-escaped paths, resolved `.` and `..` relative to each chapter, and checked each local path against the tracked tree. This is a scoped pattern scan, **not a full CommonMark parser**.

## Results

| Chapter | Local inline links checked | All inline links inventoried |
|---|---:|---:|
| 021 | 11 | 14 |
| 022 | 7 | 13 |
| 023 | 7 | 12 |
| 024 | 9 | 13 |
| 025 | 9 | 13 |
| 026 | 9 | 13 |
| 027 | 9 | 14 |
| 028 | 9 | 13 |
| 029 | 9 | 13 |
| 030 | 13 | 17 |
| **Total** | **92** | **135** |

**Result:** 92 local inline link paths checked; **0 missing tracked targets**. 43 HTTP(S) external links inventoried but not tested. No fragment-only or local path-with-fragment references were found by this scan.

## Limitations and follow-up
- This result does **not** certify reference-style links, escaped/complex nested Markdown link syntax, generated heading anchors, external URL reachability, or link targets' semantic correctness.
- No SQL parser was run; no PostgreSQL 18 instance was used; no SQL was executed.
- This is not an independent editorial review or production acceptance.
- Next: Parts 04–12 link and anchor checks; full Markdown parsing; SQL parser checks; isolated PostgreSQL 18 runtime validation with captured versions, commands, results and reproducible evidence.
