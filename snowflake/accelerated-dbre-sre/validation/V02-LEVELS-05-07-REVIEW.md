# V02 — Levels 5–7 Security, Recovery and Incident Response Review

**Date:** 2026-10-30  
**Branch:** `feature/snowflake-7-level-dbre-sre-20261030`  
**Scope:** Levels 5–7 short-course tutorials, manually executable read-only SQL smoke scripts, validator and regression tests.  
**Disposition:** Authored technical corrections; live Snowflake tests **NOT RUN**; independent security/DBRE/data-owner approval **PENDING**.

## Technical findings and remediation

| ID | Severity | Finding | Remediation | Review disposition |
|---|---|---|---|---|
| SF-018 | P2 | Level 5 `CURRENT_SECONDARY_ROLES()` description lacked return-value detail | Document JSON-encoded VARCHAR and its role-visibility implications | Authored; runtime pending |
| SF-019 | P2 | `SHOW GRANTS` was susceptible to misinterpretation as a full privilege inventory | Define no-argument behavior as current user's role grants, not all effective object privileges | Authored; runtime pending |
| SF-020 | P1 | Security audit labs could expose usernames or IPs; Account Usage login data is delayed | Add an optional **aggregate-only** LOGIN_HISTORY query, least-privilege prerequisites, up to 2h latency warning and redaction controls | Authored; security-owner review pending |
| SF-021 | P1 | Recovery tutorial could incorrectly equate configured retention with effective retention | Check `MIN_DATA_RETENTION_TIME_IN_DAYS` at account level and the database/table configured value; note table-type differences | Authored; runtime/edition review pending |
| SF-022 | P1 | Historical `AT(OFFSET => -60)` may fail if table was created too recently, does not exist or retention is disabled | Separate read-only readiness script, explicit gating, capture BLOCKED outcome rather than PASS | Authored; runtime pending |
| SF-023 | P2 | Incident smoke used a broad function without clearly separating current-session from historical account monitoring | Use `QUERY_HISTORY_BY_SESSION` for a least-privilege lab; separate optional historical ACCOUNT_USAGE aggregate and status/lag explanation | Authored; runtime pending |
| SF-024 | P1 | Validation did not cover Levels 5–7 runnable smoke scripts | Add L5–L7 scripts to static safety gate, mandatory content markers and regression tests for RBAC, Time Travel and disallowed cancellation | Automated check pending |

## Manual validation protocols

### Level 5: Security / RBAC
1. Use an approved non-admin training role; do not enable elevated secondary roles during the test.
2. Run [Level 5 smoke SQL](runtime/level-05-smoke.sql). Confirm `CURRENT_SECONDARY_ROLES()` returns the documented JSON-encoded value and `SHOW GRANTS` lists current-user roles.
3. Optional aggregated login outcome query requires **separately approved security-audit** privilege; do not export `USER_NAME`, `CLIENT_IP`, `ERROR_MESSAGE`, credentials or full query text.
4. Record the approximate 2h view latency and mark lack of entitlement as **BLOCKED**. An empty view is not a successful security audit.
5. Confirm no GRANT, REVOKE, USE ROLE or policy changes occurred.

### Level 6: Time Travel / Disaster Recovery
1. Use an approved training account, nonproduction database and scratch schema. Confirm table type, edition, configured retention and any effective account minimum.
2. Execute [Level 6 read-only readiness SQL](runtime/level-06-smoke.sql) where authorized; if `DBRE_SRE_LAB`/`DBRE_SRE_L6_RECOVERY` do not exist, stop that section and record **BLOCKED**.
3. If performing the optional historical query, ensure the table **and the two rows** existed before `CURRENT_TIMESTAMP() - 60s` and within effective Time Travel retention.
4. Capture actual row count, query ID, retention parameter evidence and any errors. Do not modify production data or perform failover in this smoke.
5. A separate disaster-recovery exercise must measure RPO/RTO, business acceptance, account objects, authentication/roles, warehouse readiness and data integrity.

### Level 7: Production incident response
1. Execute [Level 7 read-only smoke](runtime/level-07-smoke.sql) with a permitted training session. Verify query ID, elapsed time, queueing and error codes.
2. Optional account-level historical aggregate requires approved `SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY` access.
3. Confirm `EXECUTION_STATUS` uses `fail` in Account Usage while Information Schema functions use `failed_with_error`. Account Usage historical query data can lag about 45 minutes.
4. Complete two **tabletop** incident scenarios without cancelling any actual query or changing warehouse/data/security configuration.
5. Reviewer checks blameless impact statement, SLO evidence, escalation path, reversible mitigation, rollback plan and follow-up preventive actions.

## CI and validation scope

The static gate verifies seven 60-minute lessons; safety patterns and required structures; all seven smoke SQL scripts; Level 5–7 required markers; safe commands; link resolution and regression tests. The SQL guard intentionally is **not** a Snowflake SQL parser. It cannot confirm permission outcomes, syntax under a live account, costs or incident response effectiveness.

**Actual Snowflake runtime:** NOT RUN.  
**Independent review:** PENDING.  
**Production certification:** NOT CERTIFIED.  
**Merge policy:** Remain a draft until external reviewer and runtime evidence are recorded.

## Snowflake documentation checked

- https://docs.snowflake.com/en/sql-reference/functions/current_secondary_roles
- https://docs.snowflake.com/en/sql-reference/sql/show-grants
- https://docs.snowflake.com/en/sql-reference/account-usage/login_history
- https://docs.snowflake.com/en/sql-reference/sql/show-parameters
- https://docs.snowflake.com/en/sql-reference/parameters
- https://docs.snowflake.com/en/sql-reference/constructs/at-before
- https://docs.snowflake.com/en/user-guide/data-time-travel
- https://docs.snowflake.com/en/sql-reference/functions/query_history
- https://docs.snowflake.com/en/sql-reference/account-usage/query_history
