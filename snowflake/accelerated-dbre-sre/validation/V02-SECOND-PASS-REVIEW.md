# V02 Second-Pass Technical Review — 2026-10-30

**Scope:** Accelerated Snowflake DBRE/SRE Levels 1–7, standalone lesson SQL and two runtime smoke scripts.  
**Result:** Author-reviewed static corrections submitted; automated CI and independent review tracked separately.  
**Runtime:** **NOT RUN** — no authorized Snowflake account/connection used.  
**Safety:** This report does not assert production certification.

## Technical corrections

| Finding | Severity | Observed problem | Change |
|---|---|---|---|
| SF-007 | P1 | TEMP TABLE can shadow existing permanent/transient table of same name, even without CREATE OR REPLACE | Explicit empty instructor-controlled scratch schema and pre-run collision check in L1/L3 and runtime pack |
| SF-008 | P1 | L1 and runtime instructions incorrectly treated schema CREATE TABLE privilege as required for TEMP TABLE | Corrected prerequisites, smoke instructions and negative-test expectations |
| SF-009 | P2 | Level 2 QUERY_HISTORY_BY_USER may return extraneous sessions; outer WHERE filtering happens after RESULT_LIMIT | Use QUERY_HISTORY_BY_SESSION with explicit tag filter and higher RESULT_LIMIT |
| SF-010 | P2 | Level 2 SQL script claimed cleanup runs automatically after a failure | Corrected to manual separate ALTER SESSION UNSET QUERY_TAG |
| SF-011 | P1 | Previous static safety gate was line-based, missing dangerous multi-line statements | Normalize SQL statements and enforce a conservative lab command allowlist |
| SF-012 | P2 | Static gate lacked regression coverage | Add 15 Python stdlib regression tests in test_validator.py, make them mandatory in GitHub Actions |

## Documented verification sources

1. Snowflake temporary table naming conflicts and permissions:
   https://docs.snowflake.com/en/user-guide/tables-temp-transient
2. Query-history function arguments, session scope, RESULT_LIMIT, WHERE order and status values:
   https://docs.snowflake.com/en/sql-reference/functions/query_history
3. Account Usage query-history status and retention:
   https://docs.snowflake.com/en/sql-reference/account-usage/query_history
4. SHOW GRANTS with no arguments is equivalent to SHOW GRANTS TO USER current_user:
   https://docs.snowflake.com/en/sql-reference/sql/show-grants
5. Time Travel AT OFFSET limits:
   https://docs.snowflake.com/en/sql-reference/constructs/at-before
6. GENERATOR and its deterministic ROWCOUNT:
   https://docs.snowflake.com/en/sql-reference/functions/generator

## Automated quality controls

- [Static validator](validate_courses.py) checks the 7 lessons, navigation and core safety patterns.
- [Unit tests](test_validator.py) exercise safe SQL, comments, session tag operations and denial of DROP/ALTER WAREHOUSE/GRANT/unsafe INSERT/CREATE, including statements split across lines.
- [GitHub Actions workflow](../../../.github/workflows/snowflake-accelerated-static.yml) runs the static validator and regression tests on relevant changes.
- SQL linting is not a complete Snowflake SQL parser. It cannot establish grants, execution semantics, account edition support, cost or data correctness.

## Still open before production-grade certification

1. Execute Level 1 and Level 2 smoke scripts in a **dedicated training Snowflake account**, record query IDs, actual outputs, permission outcomes and cleanup.
2. Review L3–L7 examples with a Snowflake administrator and application/data owner; add executed runtime smoke suites for those lessons.
3. Test negative access scenarios in least-privilege roles without an elevated administrator session.
4. Verify warehouse cost/credit budget, time-travel retention, real incident observability, and disaster-recovery assumptions in the target environment.
5. Obtain independent technical and security review before merging/certifying.

**Decision:** Suitable for continued validation as draft documentation; **not production certified**.
