# Targeted SQL static review — 085–090 (2026-11-26)

Scope: manual source-based comparison of chapter expectations and canonical lab SQL on main; not parser execution, independent editorial acceptance or runtime testing. Master TOC blob bddcb3692f334ff9587ef6c8dc83b226a2793768; README blob 4e6faa4c0218e66a01fb08419aebc42d8784b5ce.

| Chapter | Lab blob SHA | Recomputed expectations |
|---|---|---|
| 085 | 100256b881fc2af46b9cf09c4bc25308f77e6668 | Ada 2/50, Ben 1/15, Cy 0/0, Dee 1/7.50; four paid orders, 72.50; including pending adds 99 |
| 086 | f4fae16cafda38d7e1944d8312ec74c69d64c3e9 | API snapshot 2/50, live 3/60; file 1/15 both; live total 75, one late paid order |
| 087 | 8b6069d5183ebc35b0b2cab94a323d52de22c0c2 | 101 3/30, 102 1/20; six source rows, four paid, total 50; excluded 149 |
| 088 | bfd7f93dfb0692259d9fc615231427a47a0e6984 | fees 5,4,0; totals 105,44,20; fees 9, total 169; built-in abs(numeric) metadata expectation f/i remains runtime pending |
| 089 | 5e55ede69022ab33f95d7cd99c50154a154ab7c8 | changed 101,103,104,105; unchanged 102; paid transition 101; NULL transition preserved |
| 090 | 929a00c23103ceb476dcb43d23ec5f09ae1e24f4 | Aster 2/50 high, Birch 1/25 standard, Cedar 1/10 unassigned region, Dune 0/0; four paid, live 85, snapshot 75 |

Chapter blobs respectively: 4621d68863deba800f04fa093d05417ac8f12d47, 210911246058d37dfdcd365c72b4fabb9c04d8a7, 09e1ecf0334d3ad894fd853546aec49a8da3073d, 5b197768b8f3539d44ebe8dedcf33b6e318d814c, f7fd3cac2a796d6018b22a8d9449b550703523e4, 0a4f6803b064a54127396ed1b956c0a4e091296d.

All six labs use read-only transactions, local timeouts, psql ON_ERROR_STOP, database/version guards, bidirectional EXCEPT ALL comparisons and final arithmetic acceptance expressions, followed by rollback. No contradiction found in the targeted fixture arithmetic. Guards do not establish isolation. These CTE simulations do not exercise actual view privileges, materialized refresh, temp-table lifecycle, user routine creation, trigger execution or driver parameter binding. Chapter 086's fixed cutoff is adequate for its fixture but a half-open next-day boundary is preferable for fractional-second timestamps; the modeled gap assumes both services exist in both snapshots. These are scope limitations, not runtime findings.

No SQL or regression tests executed. Comprehensive Markdown/link checks, parser-based checks, optional DDL examples and independent editorial acceptance remain pending. Next: reconcile tracker, review 091–096, execute regression suite and isolated PostgreSQL 18 acceptance with retained evidence.
