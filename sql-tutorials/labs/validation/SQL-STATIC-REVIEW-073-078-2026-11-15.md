# SQL static review — Chapters 073–078 (2026-11-15)

## Scope and method
Read the current `main` Master TOC, README, status tracker, all six chapter Markdown sources and corresponding six SQL labs. Manually inspected SQL expressions, synthetic inputs, expected-row assertions, safety controls, and vendor-specific syntax. **Source-based targeted reasoning only:** no PostgreSQL connection, parser execution, independent editorial certification, or runtime evidence.

## Targeted findings
| Chapter | Focus | Source-derived expected result and check |
|---|---|---|
| 073 | LAG/LEAD | Eight observations, four per service; API row 2 delta +30, file row 8 delta -10 after a ten-minute gap; a NULL predecessor yields NULL delta |
| 074 | Running totals | API final total 100, FILE final total 40; FILE NULL batch does not increment the known-measurement count |
| 075 | Three-row moving average | Eight rows; API row 4 average 250 across two known measurements, row 5 average 400; complete three-measurement windows occur for API row 3 and FILE row 8 |
| 076 | FIRST/LAST_VALUE | API final event ID 5 with NULL latency; FILE final event ID 8 with latency 90; explicit full frame versus running frame distinguished |
| 077 | NTILE/percentiles | Nine non-NULL observations; API p50 20 and p95 88; FILE continuous p50 20, discrete p50 15, p95 33.5; tied API 20-ms observations can occupy separate NTILE buckets |
| 078 | Gaps and islands | Five islands and three gap ranges; four missing positions total; 11 source rows deduplicate to ten service/batch pairs |

No contradictory expected-output arithmetic identified in this **limited** inspection. The six labs are read-only transactions using synthetic inline data, psql `ON_ERROR_STOP`, version/database guards, transaction-local timeouts, and rollback. Database names and version checks do **not** independently prove the endpoint is disposable. `psql` backslash commands and PostgreSQL-specific percentile/interval syntax must not be described as portable SQL.

## Blocker resolved first — QA-070-ASSERT
The Chapter 070 capstone previously displayed eight diagnostics but its separate terminal guard enforced only three conditions. Updated the lab to use the same eight diagnostic Boolean values in one fail-closed assertion: input, reachable count, reachable IDs, subtree, orphan, unreachable, cycles, and depths. Removed the duplicate weaker guard. [Corrected lab](../070-lab-07-organizational-hierarchy.sql), commit `1481ba5d68e30302e4bfe08cf504fdae9fac48b4`; fetched back from `main` and text equality confirmed. **Static correction only; runtime validation pending.**

## Validation ledger
- Authored and published: **120/120** (existing published curriculum; no new chapters needed).
- Targeted structural QA: **120/120** (previously reported limited checks, not full static certification).
- Targeted SQL source/expected-output static review: **78/120**.
- Independent editorial review: **0/120**.
- Actual isolated PostgreSQL 18 runtime acceptance: **0/120**.
- Comprehensive Markdown anchor/external-link validation and parser-based SQL syntax checks: **pending**.

Next: Chapters **079–084** targeted SQL expected-output review, comprehensive Markdown link/anchor and SQL parser QA, then isolated PostgreSQL 18 runtime acceptance with retained execution logs and environment identity.
