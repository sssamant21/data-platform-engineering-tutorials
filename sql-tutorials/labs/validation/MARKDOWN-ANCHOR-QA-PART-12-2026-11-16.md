# Part 12 — Targeted Markdown navigation, fragment and fence QA

Date: 2026-11-16 (America/New_York)  
Scope: Chapters 111–120 under `sql-tutorials/part-12-platforms-capstone/` on GitHub `main`.

## Inputs and method

Read `MASTER-TOC.md`, `README.md`, `STATUS-TRACKER.md`, all ten Part 12 chapter Markdown files and the complete recursive Git tree (`truncated=false`). Inspected inline Markdown fragment destinations, counts of line-start triple-backtick fences, reference-style definition patterns and stale navigation wording. This is a **targeted pattern-based static audit**; it is **not** a CommonMark/GitHub rendered Markdown parser check.

## Findings

| Check | Result |
|---|---:|
| Chapter files inspected | 10 (111–120) |
| Local inline fragment destinations matching scoped pattern | 0 |
| External fragment destinations | 2 occurrences, both BigQuery `#qualify_clause`; not HTTP-verified |
| Chapters with even line-start triple-backtick fence counts | 10/10 |
| Reference-style definitions matching scoped pattern | 0 |
| Confirmed stale chapter navigation links corrected | 1 |

Chapter 111 ended with “112 — Star schemas, facts, dimensions, and surrogate keys (planned; no link until published)”, despite Chapter 112 being published. Corrected this to a relative link to `112-star-schemas-facts-dimensions-and-surrogate-keys.md` in commit [`8d27a64bf2893c720f3a402595cdb2d7d2a11f81`](https://github.com/sssamant21/data-platform-engineering-tutorials/commit/8d27a64bf2893c720f3a402595cdb2d7d2a11f81). Re-fetched Chapter 111 from `main` and confirmed the corrected link. Chapter 112 exists in the repository tree.

Even fence counts do not establish valid Markdown fence nesting or parser correctness. The two external fragment references were not tested against rendered pages. No SQL was executed.

## Validation states and next work

- Authored/published: **120/120**, as recorded in the status tracker.
- Targeted SQL static review: **120/120**, previously reported; not independently rerun here.
- Scoped local Markdown path audits: **120/120**, previously reported; not comprehensive parser QA.
- Independent editorial review: **0/120**.
- Actual isolated PostgreSQL 18 runtime validation: **0/120**.

Next: parser-aware Markdown checks across the curriculum (fences, reference-style links, duplicate slugs and rendered anchors); then SQL parser/expected-output QA; finally isolated PostgreSQL 18 execution with versioned, reproducible evidence. Keep production systems and credentials out of testing.
