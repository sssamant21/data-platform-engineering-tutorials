# V02 — Levels 3–4 Performance, Observability and FinOps Review

**Date:** 2026-10-30  
**Branch:** `feature/snowflake-7-level-dbre-sre-20261030`  
**Status:** Static author review and training smoke scripts prepared; Snowflake execution **NOT RUN**; independent technical review **PENDING**.  
**Scope:** `level-03-performance-query-optimization.md`, `level-04-monitoring-observability-cost.md` and their training smoke scripts.

## Findings and changes

| ID | Severity | Finding | Remediation | Gate |
|---|---|---|---|---|
| SF-013 | P2 | Level 3 lacked precise numeric acceptance totals for deterministic data | Specify 1,000 total rows, 54,110 total sales, 100 rows in region 1 and 5,060 regional total | Authored; runtime pending |
| SF-014 | P2 | Level 3 query-history demonstration could mix sessions | Add current-session query-history inspection in smoke script | Authored; runtime pending |
| SF-015 | P1 | Level 4's `CREDITS_USED` aggregate could be misread as final billed credits | Explicitly separate gross warehouse credits, compute/cloud services credits and account-level daily billed credits | Authored; runtime pending |
| SF-016 | P2 | Level 4 data freshness and permission gaps could be incorrectly marked PASS | Explicit BLOCKED/no-data outcome and monitoring-role prerequisite | Authored; runtime pending |
| SF-017 | P2 | Validator did not inspect Levels 3–4 runtime SQL | Add both files, acceptance-marker checks and regression tests | CI must pass |

## Reference calculations, not Snowflake runtime results

Level 3 generates order IDs `1..1000`, `REGION_ID = MOD(ORDER_ID,10)`, and `AMOUNT = 10 + MOD(ORDER_ID,90)`.

| Assertion | Expected value | Verified method |
|---|---:|---|
| Rows | 1,000 | Deterministic 1..1000 range |
| Distinct order IDs | 1,000 | Unique range |
| Total amount | 54,110 | Pure arithmetic sum |
| Region 1 row count | 100 | Exactly one in each ten IDs |
| Region 1 amount | 5,060 | Pure arithmetic sum |

The corresponding Python regression test checks these calculations. This does **not** establish that Snowflake executed the SQL.

## Level 3 manual acceptance

1. Confirm designated nonproduction warehouse, role, database and **empty scratch schema**, with no existing permanent/transient/temp object matching the training table name.
2. Execute [Level 3 smoke](runtime/level-03-smoke.sql). Capture query IDs and actual row-count/amount assertions.
3. Inspect Query Profile and compare scan/aggregate operators, including cache effects and any spill if present.
4. Record warehouse credits if metering is available; no claim of representative performance from 1,000 rows.
5. Ensure the session-scoped temporary object disappears when the session ends; redact all evidence.

## Level 4 manual acceptance

1. Use a read-only role with approved ACCOUNT_USAGE grants. Do not use ACCOUNTADMIN for convenience.
2. Execute [Level 4 smoke](runtime/level-04-smoke.sql); note any view not accessible and any empty result set.
3. Validate that credits are **gross warehouse usage** and not necessarily `CREDITS_BILLED`. Compare daily account billing adjustment data if accessible.
4. Confirm `EXECUTION_STATUS='fail'` in ACCOUNT_USAGE and the distinction from Information Schema values such as `failed_with_error`.
5. Record data latency (some views lag up to hours) and prevent use of these historical views as low-latency incident alert sources.

## Official references

- Query History table functions (session scope, seven-day range, RESULT_LIMIT):
  https://docs.snowflake.com/en/sql-reference/functions/query_history
- Warehouse load view (five-minute intervals, lag up to three hours):
  https://docs.snowflake.com/en/sql-reference/account-usage/warehouse_load_history
- Warehouse metering (gross credits, not billed adjustment):
  https://docs.snowflake.com/en/sql-reference/account-usage/warehouse_metering_history
- Account daily metering (`CREDITS_BILLED`):
  https://docs.snowflake.com/en/sql-reference/account-usage/metering_daily_history

## Final gate

**V02 static:** Await latest Actions confirmation.  
**V03 runtime:** NOT RUN — no authorized Snowflake environment connected.  
**V04 independent review:** PENDING.  
**V05 production certification:** NOT CERTIFIED.
