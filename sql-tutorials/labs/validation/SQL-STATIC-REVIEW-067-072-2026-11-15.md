# SQL targeted static expected-output review — Chapters 067–072

**Date:** 2026-11-15  
**Branch:** main  
**Scope:** six published chapter Markdown files and six corresponding synthetic PostgreSQL-oriented SQL labs.  
**Method:** source inspection and independent arithmetic/set/window reasoning; **no SQL execution**. This is not parser-based syntax validation, comprehensive Markdown link/anchor verification, independent editorial certification, or runtime acceptance.

| Chapter | Reviewed scenario | Source-derived expected values | Finding |
|---|---|---|---|
| 067 | UNION vs UNION ALL; NULL duplicate elimination | ALL: 8 rows, 180 non-NULL sum, 6 non-NULL values; DISTINCT: 6 rows, 140 sum, 5 non-NULL values; two duplicate groups of size 2 | Consistent |
| 068 | INTERSECT/EXCEPT and ALL multiplicities | Shared distinct: 102,103,NULL; source-only: 101,104; source EXCEPT ALL: 101,102,104 (sum 307); warehouse-only: 105 | Consistent |
| 069 | CTE refactor and bidirectional EXCEPT ALL | East 140 accepted/30 rejected/170 processed/82.35%; West 100/30/130/76.92%; global 240/60/300/80.00%; zero set differences | Consistent for the fixture; filtered invalid inputs would change semantics if present |
| 070 | Recursive hierarchy, orphan/cycle detection | 9 employees; root-reachable 1–6 with depths 0,1,1,2,2,2; subtree 2,4,5; orphan 7; unreachable 7,8,9; cycle starters 8,9 | Consistent; see acceptance-strength limitation below |
| 071 | Window totals and running sums | 6 rows; global 230; API 120, FILE 110; running totals by batch ID 40,100,30,100,120,110; GROUP BY yields 2 service rows | Consistent |
| 072 | ROW_NUMBER/RANK/DENSE_RANK with ties and NULL | 8 rows; 4 per service; each partition rank 1,1,3,4; dense rank 1,1,2,3; winners batch 1,5; tied leaders 1,3,5,6; NULL batch 8 last | Consistent |

## Safety and quality findings

- All six SQL labs use inline synthetic VALUES, `BEGIN READ ONLY`, local statement/lock/idle timeouts, PostgreSQL 18 version checks, a `sql_tutorials` database-name guard, and `ROLLBACK`. They also use psql's `\\set ON_ERROR_STOP on`, so execution requires **psql**, not an arbitrary SQL-only client.
- Database-name and version checks **do not establish isolation**. Do not run on production. Before runtime acceptance, independently verify the disposable endpoint, least-privilege role, PostgreSQL 18 server identity, and retained command/output evidence.
- **QA-070-ASSERT (open, nonblocking for static review):** Chapter 070's consolidated diagnostic query displays eight Boolean checks for orphan, unreachable, cycle, depth and subtree behavior, but its final fail-closed guard checks only input count and reachable IDs. Runtime acceptance must assert all eight checks (or verify each result programmatically), otherwise the script can exit successfully despite incorrect orphan/cycle results. No production impact; no runtime certification claimed.
- No contradictory numeric expectations were found in the targeted cases. This does **not** prove full SQL syntax, all prose claims, or edge-case correctness.

## Coverage and next work

Targeted SQL expected-output review: **72/120** (previous baseline 66/120). Authored/published **120/120**; previously reported targeted structural QA **120/120** (not comprehensive); independent editorial review **0/120**; actual isolated PostgreSQL 18 runtime-validated **0/120**.

**Next:** Chapters **073–078** targeted expected-output review; strengthen Chapter 070's fail-closed acceptance before runtime certification; comprehensive Markdown-aware link/anchor QA, parser-based SQL checks, and isolated PostgreSQL 18 execution with reproducible evidence.
