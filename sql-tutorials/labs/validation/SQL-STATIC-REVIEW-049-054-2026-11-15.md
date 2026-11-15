# SQL targeted static review — Chapters 049–054 (2026-11-15)

## Scope and method

Read current `main` Master TOC, README, STATUS-TRACKER, all six published chapter Markdown files and their corresponding six SQL labs. This is source-based manual review of fixture arithmetic, aggregation grain, NULL handling, expected result sets, transaction guards and portability notes. **No PostgreSQL 18 instance was started and no SQL executed.** This is neither parser-based syntax certification nor independent editorial approval.

## Findings by chapter

| Chapter | Source-based expectations checked | Result |
|---|---|---|
| 049 | 3 orders totaling 90; 4 valid item rows plus 1 NULL-key item; 4 payments; 2×2+1+1=6 joined rows; inflated order sum 210; child aggregates each total 90; 1 orphan item and 1 duplicated staging key | Consistent in reviewed assertions |
| 050 | 3 customers, 5 orders, 5 payments; orders 115, payments 100, balance 15; raw left payment join 6 rows and inflated sum 155; final order-grain report 5 rows, one missing customer, one no-payment order, one partially paid order | Consistent in reviewed assertions |
| 051 | 5 events, 4 non-NULL amounts, 4 distinct orders; SUM 100, AVG 25, min 10, max 40; zero-filled AVG 20; empty input COUNT 0 and SUM/AVG NULL | Consistent in reviewed assertions |
| 052 | 7 events, 6 known amounts, sum 78; 5 (region,status) groups; East 30, West 40, NULL region 8; East pending sum NULL | Consistent in reviewed assertions |
| 053 | 10 events, 9 known amounts, all-status net 143; captured 7 events/net 143; qualifying North 2/60 and West 2/45; East 2/30 excluded; all-status East 30, North 65, West 40; East pending NULL | Consistent in reviewed assertions |
| 054 | 12 events, 8 known amounts, captured 6/125, refunded 2/-15, pending 4/15, net 125; one captured NULL amount; 5 region groups; CASE/FILTER parity includes NULL region via IS NOT DISTINCT FROM | Consistent in reviewed assertions |

No contradictory expected-result arithmetic was found **within this limited review**. This is not a guarantee that all SQL statements execute.

## Safety, portability and follow-up

All six SQL scripts use `psql`-specific `\\set ON_ERROR_STOP on`, `BEGIN`, `SET LOCAL` timeouts, temporary tables, synthetic inserts, PostgreSQL-version/database checks and final `ROLLBACK`. These are **not read-only** scripts. Execute only on an independently verified disposable PostgreSQL 18 instance with nonproduction credentials; a database name or version guard is not sufficient evidence of isolation. The scripts use PostgreSQL-specific `DO` assertions and `FILTER` syntax; the chapter explanations identify portable CASE alternatives. Chapter 054 uses NULL-safe `IS NOT DISTINCT FROM` to compare group keys.

Still pending: Markdown-aware links and anchors, parser-based SQL checks, external reference checks, independent editorial review, actual isolated PostgreSQL 18 execution, stdout/stderr and exit-code capture, environment identity, rollback confirmation, and reproducible evidence. Do not interpret textual `RAISE NOTICE` messages as observed execution.

Cumulative targeted SQL static review after this batch: **54/120 (45%)**. Authored/published: **120/120**. Previously reported limited structural QA: **120/120**. Independent editorial review: **0/120**. Actual isolated PostgreSQL 18 runtime validation: **0/120**.

**Next:** Chapters 055–060 targeted semantic/expected-output review; comprehensive Markdown/anchor and parser-based SQL checks; isolated PostgreSQL 18 acceptance with retained evidence. Chapter authoring remains frozen.
