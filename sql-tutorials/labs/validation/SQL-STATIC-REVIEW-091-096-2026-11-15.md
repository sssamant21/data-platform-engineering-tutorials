# Targeted SQL static review — Chapters 091–096 (2026-11-15)

## Scope and method
Read current `main` MASTER-TOC.md, README.md, STATUS-TRACKER.md, six existing Part 10 chapters and six matching SQL labs. Compared synthetic VALUES, expected counts/sums, bidirectional EXCEPT ALL checks, read-only boundaries, PostgreSQL-specific semantics and claims about EXPLAIN. **Source-based manual inspection only**; no SQL execution, PostgreSQL 18 server, parser-based syntax QA, comprehensive Markdown link/anchor checks, independent editorial sign-off, or index benchmark.

## Chapter findings
| Chapter | Static expected result | Finding |
|---|---|---|
| 091 | Four orders, three paid, paid sum 45.00; customer totals 35.00, 10.00, 0.00 | Exact bidirectional multiset checks and source counts consistent. EXPLAIN estimates only. |
| 092 | Ten events; paid 7 (0.70), failed 2 (0.20), pending 1 (0.10) | Expected multiset matches synthetic counts. No physical index tested. |
| 093 | Five orders total 100.00; point lookup 103=8.00; half-open range IDs 102–104 sum 73.00 | Checks consistent. VALUES cannot demonstrate a B-tree index scan. |
| 094 | Six orders; tenant-10 paid 3 sum 100.00; bounded range 2 sum 50.00; tenant-20 paid 1 sum 40.00 | Checks consistent. EXPLAIN over VALUES does not measure composite-index access. |
| 095 | Six orders; open 4 sum 100.00; tenant-10 open 3 sum 60.00; email expression matches IDs 1 and 3 | Bidirectional checks consistent. No partial, expression, or covering index actually created. |
| 096 | Eight rows; tenant-10 4, paid 4, joint 3 (37.5%), tenant-20 pending 3 | Checks consistent. Catalog queries vary by database; no ANALYZE or VACUUM executed. |

## Open follow-ups and limitations
- **QA-091-NAV — resolved:** Chapters 091 and 092 incorrectly called their next already-published chapters `(planned)`. Replaced with direct relative links to Chapters 092 and 093 in commits `7ed9e01563e6d9b2c4c8d03c997e4bbf7bd2c870` and `19bfbfd8697d80cb68f60c1b492e63495b04e4b2`.
- **QA-091-PERF-INTEGRATION:** Inline VALUES have no physical indexes or persistent planner statistics. Chapters 093–096 teach index/statistics concepts but their read-only labs **do not verify** real index scans, index-only scans, partial-index predicate implication, or statistics maintenance. Separate disposable PostgreSQL 18 integration tests must create synthetic tables/indexes, capture actual EXPLAIN evidence, and clean up. Do not conflate synthetic result checks with performance acceptance.
- Chapter 091 requires `psql -X -v ON_ERROR_STOP=1` at invocation (unlike labs 092–096, it does not set ON_ERROR_STOP internally). Its arithmetic fail-closed guard and `BEGIN READ ONLY` remain useful but do not prove isolation.
- The `sql_tutorials` name/version checks in labs are **not proof** of a disposable environment. Verify connection endpoint and isolation independently before any execution.
- Plan costs and node selection are environment dependent; none of the six labs asserts a specific EXPLAIN tree.
- Full Markdown link/anchor QA, parser SQL checks, independent editorial review and PostgreSQL 18 runtime acceptance remain **pending**.

## Progress and next acceptance
Previously reported: 120/120 authored/published, 120/120 targeted structural QA, 90/120 targeted SQL expected-output review, 0/120 independently reviewed, 0/120 PostgreSQL 18 runtime-validated. This batch advances targeted static SQL review to **96/120 (80%)**. Next review **097–102**, then comprehensive Markdown links/anchors, parser-based SQL checks and isolated PostgreSQL 18 execution with retained command/output/version/endpoint evidence. No production credentials or systems used.
