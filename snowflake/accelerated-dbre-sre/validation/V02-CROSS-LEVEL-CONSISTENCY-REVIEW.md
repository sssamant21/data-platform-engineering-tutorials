# V02 — Cross-Level Lesson / Smoke Script Consistency Review

**Date:** 2026-10-31  
**Scope:** Seven 60-minute accelerated DBRE/SRE lessons, their seven manual runtime SQL scripts, offline instructor pack and validation gates.  
**Mode:** Static source comparison, Python-only synthetic arithmetic and official Snowflake documentation. **No connection to Snowflake and no live SQL execution.**

## Findings and resolutions

| Finding | Severity | Observed inconsistency / limitation | Offline disposition |
|---|---|---|---|
| SF-025 | P2 | Level 2 lesson used training query tag `snowflake_dbre_sre_level_02` while dedicated smoke script used `snowflake_dbre_sre_l2_runtime_smoke` | **FIXED**: tutorial tag aligned with smoke; both use `QUERY_HISTORY_BY_SESSION`, with cleanup of `QUERY_TAG` |
| SF-026 | P2 | Level 3 lesson used `QUERY_HISTORY_BY_USER(RESULT_LIMIT => 20)`, even though its smoke script and text recommended current-session isolation | **FIXED**: tutorial SQL now uses `QUERY_HISTORY_BY_SESSION(RESULT_LIMIT => 1000)` and clarifies the function's result limit and seven-day lookback |
| SF-027 | P1 | Level 6 described a database parameter result as an "effective retention" value, which could obscure account minimum and table-type effects | **FIXED**: explicitly labels the database parameter as configured/inherited and requires checking the account minimum, table type and actual historical point before recovery |
| SF-028 | P2 | No automatic cross-check required the lesson SQL to remain semantically aligned with the dedicated QA smoke scripts | **FIXED**: added `test_curriculum_consistency.py` for nine contract checks covering L1 fixtures, L2 query tagging, L3 arithmetic/history, L4 billing, L5 grants/audit, L6 retention and L7 triage |
| SF-029 | P3 | The lesson and smoke scripts intentionally use different isolated scratch table names for Levels 1 and 3 | **DOCUMENTED**, not a defect: separate exercises should not be mixed within a session or treated as shared state |

## Review scope and limitations

- Lesson and smoke SQL are **not executable interchangeably**; follow one approved course workflow and use one instructor-controlled empty scratch schema. Different table identifiers are intentional.
- Level 2's common tag is for training only. Query history can be truncated by the table function's `RESULT_LIMIT` *before* subsequent filtering. A lack of rows is not proof of successful query execution.
- Level 3 synthetic arithmetic: exactly 1,000 rows, sum **54,110**, 100 region-1 rows, sum **5,060**, from a Python calculation. It does **not** benchmark Snowflake.
- Level 4 Account Usage metrics have latency and require separately approved privileges; gross warehouse credits are not equal to final account billing.
- Level 5 exercises inspect roles and aggregated audit data only; a current user's role grants are not a complete account privilege inventory.
- Level 6 Time Travel recovery depends on creation, insertion and historical point timing, effective retention, table type and permissions. The read-only smoke must skip the historical SELECT if no approved lab object exists.
- Level 7 account-wide historic monitoring is not the same as the most recent session investigation.
- Static SQL safety checks are defense in depth, **not a full Snowflake SQL parser**. No independent reviewer has signed off.

## Exit status

**Offline cross-level consistency:** Corrections committed; automated CI required on final branch head before declaring PASS.  
**Actual V03 runtime:** USER-DEFERRED / NOT RUN (0/7 levels).  
**Independent V04 review:** PENDING, external human approval required.  
**Production V05:** NOT CERTIFIED. PR #43 remains draft.

## Snowflake references

- [Query history table functions](https://docs.snowflake.com/en/sql-reference/functions/query_history)
- [Warehouse Load History](https://docs.snowflake.com/en/sql-reference/account-usage/warehouse_load_history)
- [Metering Daily History](https://docs.snowflake.com/en/sql-reference/account-usage/metering_daily_history)
- [Login History](https://docs.snowflake.com/en/sql-reference/account-usage/login_history)
- [Snowflake Time Travel](https://docs.snowflake.com/en/user-guide/data-time-travel)
