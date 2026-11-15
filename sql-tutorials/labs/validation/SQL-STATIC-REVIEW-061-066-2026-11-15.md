# SQL static review — Chapters 061–066 (2026-11-15)

## Scope and evidence classification

Reviewed current `main` copies of `MASTER-TOC.md`, `README.md`, `STATUS-TRACKER.md`, six numbered chapter Markdown files under `part-07-subqueries/`, and corresponding `labs/061-*.sql` through `labs/066-*.sql`. This is a **targeted source-based manual static review**, not parser-based SQL verification, full Markdown/anchor QA, independent editorial certification, or actual PostgreSQL 18 runtime testing. No SQL was executed. No production credentials or data were used.

## Findings by chapter

| Chapter | Targeted reasoning and expected output | Finding |
|---|---|---|
| 061 — Scalar subqueries and derived tables | Six batches sum to 300; mean 50; values greater than 50 are IDs 1 and 4; regional totals East 150, West 100, North 50; selected regions East and West sum to 250; empty scalar subquery yields NULL | Targeted arithmetic consistent |
| 062 — IN, ANY, ALL | IN IDs 1,2,5,6; > ANY(40,90) IDs 1,2,3; > ALL(40,90) ID 1; NULL-bearing NOT IN returns no rows; filtered NOT IN IDs 1,3; empty ANY = false, empty ALL = true, empty IN = false, NULL > ALL(empty) = true | **Corrected a documentation defect**: comment claimed three expected Boolean columns although SELECT returns four; now states `f,t,f,t` |
| 063 — EXISTS versus IN | Six batches, five alerts, three distinct non-NULL alert batch IDs; flagged IDs 1,3,6; unflagged IDs 2,4,5; known processed total 280; NULL-bearing NOT IN returns no rows; nonmatching IN with NULL lookup is UNKNOWN | Targeted reasoning consistent |
| 064 — Correlated subqueries | Six batches total 320; source averages api 200/3, file 50, queue 20; above-source-average IDs 1 and 5; alert counts [2,0,0,1,0,1] and flagged IDs 1,4,6 | Targeted reasoning consistent; EXPLAIN without ANALYZE cannot establish performance |
| 065 — Common table expressions | Per-batch processed [100,50,60,40,20,30]; api accepted/rejected/processed 140/30/170; file 100/30/130; weighted acceptance 240/300 = 80%; source percentages 82.35% and 76.92% | Targeted reasoning consistent |
| 066 — Recursive CTEs | Root tree has six reachable nodes with depths 0/1/2 counts 1/2/3; Ben subtree IDs 2,4,5; orphan 7 points to missing 99; three-edge cycle closes on node 1 at depth 3, four emitted walk rows | Targeted reasoning consistent; depth cap and visited-path checks are essential |

## Safety, portability, and remaining work

All six lab files use inline synthetic `VALUES` fixtures, `BEGIN READ ONLY`, local timeouts, database/version identification and guards, and `ROLLBACK`. The scripts contain psql meta-command `\\set ON_ERROR_STOP on` and PostgreSQL-specific expressions such as `::integer`, arrays, and `ANY(array)`; do not treat the entire scripts as portable ANSI SQL. Guard checks do **not** prove that a database endpoint is disposable. Verify isolation externally before execution. The PostgreSQL major-version guard is a prerequisite, not evidence of PostgreSQL 18 runtime validation.

The SQL examples and expected outcomes were reasoned from source; SQL syntax was **not** parser-validated and no executable evidence was captured. The labs' Boolean checks and fail-closed acceptance guards still require isolated execution and saved stdout/stderr, server version, connection target identity, exit code and fixture checks. No independent editorial review was performed.

**Correction commit:** `39e09a7202ed73627639711a8d210d911e94772d` — [lab 062](../062-in-any-all-multi-row-subqueries.sql). The correction was fetched back from `main`.

**Cumulative targeted SQL static review:** 66/120 chapters (55%), subject to the scope limitation above. **Authored/published:** 120/120. **Previously reported targeted structural QA:** 120/120, not comprehensive. **Independent editorial review:** 0/120. **Actual isolated PostgreSQL 18 runtime-validated:** 0/120.

**Next:** Chapters 067–072 targeted SQL expected-output and semantic review; comprehensive Markdown link/anchor and parser-based SQL checks; isolated PostgreSQL 18 acceptance with reproducible evidence.
