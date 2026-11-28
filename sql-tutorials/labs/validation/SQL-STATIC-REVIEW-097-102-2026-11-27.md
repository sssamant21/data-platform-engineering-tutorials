# Chapters 097–102 — targeted static semantic review

Date: 2026-11-27. Scope: manual source reasoning on six chapter/lab pairs from main, not parser or runtime certification.

## Source inventory

| Source | Blob SHA |
|---|---|
| [097-make-predicates-index-friendly-and-rewrite-expensive-sql.md](../../part-10-performance/097-make-predicates-index-friendly-and-rewrite-expensive-sql.md) | `b636257dfa9b25b76f1c63fec935c41087c1d51b` |
| [097-index-friendly-predicates-rewrites.sql](../../labs/097-index-friendly-predicates-rewrites.sql) | `e87ed7c48589ac44695f8dcd92aaf0fb50a7a7b9` |
| [098-optimize-joins-aggregations-and-subqueries.md](../../part-10-performance/098-optimize-joins-aggregations-and-subqueries.md) | `b9cc35efe74eebea0bf87ed8e1634765439a8635` |
| [098-optimize-joins-aggregations-subqueries.sql](../../labs/098-optimize-joins-aggregations-subqueries.sql) | `78405c81c19f3759ea7dffd41b3420d8e5012d83` |
| [099-keyset-pagination-benchmarking-and-regression-tests.md](../../part-10-performance/099-keyset-pagination-benchmarking-and-regression-tests.md) | `a8f51202cad86d4c6b924e7ac0c749ebdec45a76` |
| [099-keyset-pagination-benchmark-regression.sql](../../labs/099-keyset-pagination-benchmark-regression.sql) | `6f28d06b5de5cd8ea02a7c5b890cf5365b35b0f9` |
| [100-lab-10-baseline-tune-and-remeasure-a-slow-query.md](../../part-10-performance/100-lab-10-baseline-tune-and-remeasure-a-slow-query.md) | `52a96c126377d080f4b79ff5e4f21e83c183c658` |
| [100-lab-10-baseline-tune-remeasure.sql](../../labs/100-lab-10-baseline-tune-remeasure.sql) | `35f77c33c763bde54340852a169992690a3c8451` |
| [101-least-privilege-and-sql-access-control-principles.md](../../part-11-security-operations/101-least-privilege-and-sql-access-control-principles.md) | `b91c115be0b8b3a70b8055415ce931ef26f6d41f` |
| [101-least-privilege-access-control.sql](../../labs/101-least-privilege-access-control.sql) | `4137d49d532727eea92bdd6165ddcbce888c9332` |
| [102-users-roles-grant-revoke-and-ownership.md](../../part-11-security-operations/102-users-roles-grant-revoke-and-ownership.md) | `f9a3cc5a58808835a2b41548a2ae24a52a78d115` |
| [102-users-roles-grant-revoke-ownership.sql](../../labs/102-users-roles-grant-revoke-ownership.sql) | `911e6a4efe62e0f2f4189ffe8f4ea0f4b25333f2` |

## Findings

| Chapter | Derived expectations and checks |
|---|---|
| 097 | Half-open timestamp range selects IDs 2,3,4 (20+30+40=90); lowercase email selects 1,2; numeric rewrite selects 3,4,5 and excludes NULL. Two-way EXCEPT ALL checks date and numeric equivalence and fixed expected rows. |
| 098 | Naive inner join produces 2×2+1×1=5 rows; preaggregation yields (101,50,50), (102,40,40), (103,10,0). Total lines 100, settled 90, outstanding 10. EXISTS and DISTINCT select 101,102. |
| 099 | Descending timestamp and ID tie-breaker yields pages 109/108/107, 106/105/104, 103/102/101. Fixed fixture has nine rows and three pages; multiset comparison against OFFSET detects membership differences, not independent ordering certification. |
| 100 | Twelve orders; tenant 10 paid on Nov 1 selects 101–104, including fractional-second boundary; sum 100. Tenant 20 has one paid order that day. Baseline/candidate and expected row multisets compared. |
| 101 | Nine policy rows; allowed assignments 1+2+1=4; forbidden and missing approved assignments zero. Session metadata is variable, not a fixed oracle. |
| 102 | Three principals, one membership, two approved grants, one rejected candidate; zero missing or extra approved grants. Model derives approved grants from decisions and compares with allowlist. |

All six scripts contain ON_ERROR_STOP, BEGIN READ ONLY, local statement/lock/idle timeouts, exact major-version and database-name guards, and rollback. Database name does not prove isolation. No production access. Performance fixtures contain inline rows, not physical index benchmarks; security fixtures model policy rather than test actual privilege enforcement. No SQL executed. No comprehensive link/anchor, parser, independent editorial or runtime acceptance claimed. Targeted expectations above are manually derived, not observed.

Next: 103–108 targeted review, then remaining chapters and comprehensive QA.
