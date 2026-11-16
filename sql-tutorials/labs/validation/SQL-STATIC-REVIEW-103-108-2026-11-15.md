# Targeted SQL static review — Chapters 103–108 (2026-11-15)

**Scope:** Six existing chapters and corresponding PostgreSQL 18 synthetic read-only labs, reviewed against `main` and the Master TOC. No new chapters authored (120/120 already published). This is source-based reasoning, **not** PostgreSQL execution, independent editorial certification, comprehensive Markdown/anchor QA, or parser-based syntax validation.

| Chapter | Reviewed subject | Source-derived expected outcome | Boundary |
|---|---|---|---|
| 103 | RLS/tenant isolation model | Tenant 10: 3 orders / 90.00; tenant 20: 2 / 60.00; missing: 0; total 5 | CTE filtering is not real PostgreSQL RLS or role-based testing |
| 104 | Masking/audit model | 4 claims / 200.00; four grouped rows and four masked emails; 3 complete synthetic audit events | No real GRANT, masking policy, audit extension, or logging tested |
| 105 | Lock wait graph | 5 directed edges, 2 participants in direct 2-node cycle, 3 noncycle waiters, 2 distinct noncycle blockers | Direct reciprocal-edge detection is **not** general multi-hop deadlock detection; current-session `pg_locks` observation is environment-dependent |
| 106 | Expand/contract migration | 5 rows, 3 copied, 2 missing, 5 compatible, 2 divergent; contract blocked | No actual DDL, lock, backfill, or rollout measured |
| 107 | Quality/reconciliation | 6 candidates, 1 duplicate key group, 2 invalid, 1 orphan; source/target each 4 rows / 100.00, with 2 source-only and 2 target-only rows | A passing lab assertion means expected quality-gate **failure** detected, not data approved for promotion |
| 108 | Recovery acceptance model | drill_a ACCEPT; drill_b BLOCK (RPO); drill_c BLOCK (missing signoff) | Fictional metrics; **no backup or restore executed**, no RPO/RTO certified |

## Corrections published on main

- Chapter 103: replace tautological `tenant_id = 20 AND tenant_id = 10` and `tenant_id = NULL` pseudo-leak checks with explicit reliance on the bidirectional `EXCEPT ALL` comparison against all three context outcomes. The old predicates could never identify a leak and gave misleading assurance. Exact modeled output still tests zero visibility for absent context; it does **not** establish actual tenant security.
- Chapters 103 and 104: replace stale “next chapter planned” text with direct relative links to already-published successors.
- Lab 108: add `\\set ON_ERROR_STOP on` so direct `psql` file execution stops on SQL errors, consistent with other labs. **Still requires** `psql -X -v ON_ERROR_STOP=1`, independent environment identity verification, and nonproduction credentials.

## Remaining acceptance gates

1. Comprehensive Markdown relative-link **and anchor** validation across all 120 chapters, with external-reference checks separately tracked.
2. Parser-based PostgreSQL 18 SQL syntax checks and verification of assertions against actual outputs.
3. Isolated PostgreSQL 18 runtime execution with version, container/database identity, exact command, stdout/stderr, exit status, immutable source commit, and reproducible evidence.
4. Separately scoped disposable integration tests for real RLS/roles and bypass paths, audit coverage, locking/deadlocks, migration locking/backfill, and physical backup/restore. Synthetic models cannot certify these features.
5. Independent editorial review and issue tracking.

**Counts after this review:** published 120/120; previously reported targeted structural QA 120/120; cumulative targeted SQL static review **108/120 (90%)**; independent editorial review **0/120**; actual PostgreSQL 18 runtime validation **0/120**. Next targeted review: **109–114**. No production access or SQL execution occurred.
