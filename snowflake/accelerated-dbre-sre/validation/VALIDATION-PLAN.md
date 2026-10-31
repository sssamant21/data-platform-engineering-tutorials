# Snowflake Accelerated Track — Production-Grade Validation Plan

**Scope:** Seven 60-minute lessons in ../ (not the existing 90-chapter curriculum)  
**Tracking:** [STATUS.md](../STATUS.md)  
**Policy:** An authored or statically checked document is never represented as runtime validated or production certified.

## Severity rubric and exit criteria

| Severity | Example | Gate |
|---|---|---|
| P0 blocker | Embedded live secret or destructive production SQL presented as a lab | Must fix before merge |
| P1 blocker | Invalid SQL or unsafe access-control/recovery instruction | Must fix before runtime acceptance |
| P2 correction | Ambiguous expected result, poor role prerequisite, missing cleanup | Resolve or explicitly constrain |
| P3 enhancement | Better examples or pedagogy | Track for subsequent revision |

## Validation matrix

| Gate | What to validate | Evidence required | Status |
|---|---|---|---|
| V01 — Structure | 7 lessons, 60 minutes each, sections, navigation, Markdown fences | CI output; file inventory | PASS — initial run #41061594991 |
| V02 — Static safety / SQL review | No secrets, allowed SQL, official syntax, permissions, rollback/cleanup | Lint output + reviewed source links | Automated PASS, peer review pending |
| V03 — Lab runtime | Run examples in dedicated Snowflake training account with least-privilege role | Timestamp, query IDs, outputs, error codes, cleanup | NOT RUN |
| V04 — Independent review | DBRE, Snowflake admin, Security and Data Owner review | Review approval with identified reviewer | PENDING |
| V05 — Production acceptance | Workload SLOs, security policy, cost guardrails, RPO/RTO and operational procedures | Signed release checklist, retest cycle | NOT CERTIFIED |

## V01/V02 command

Run from repository root:
~~~bash
python3 snowflake/accelerated-dbre-sre/validation/validate_courses.py
~~~
A PASS proves only the checks implemented in the static script; it does **not** parse or execute SQL. CI lives in .github/workflows/snowflake-accelerated-static.yml.

## Sequencing update — runtime deferred by request

The seven curriculum lessons and [offline instructor assessment](INSTRUCTOR-OFFLINE-ACCEPTANCE.md) can be taught, reviewed for consistency, and completed as **draft instructional content** without a Snowflake account. Do not imply that offline quiz/tabletop exercises satisfy runtime V03 or human approval V04. The [V04/V05 independent-review handoff](V04-V05-REVIEWER-HANDOFF.md) is **prepared** but not signed.

**Resume V03 only later** with a separately verified nonproduction account, appropriate test approvals and a secure evidence store. All seven SQL lab statuses remain NOT RUN, and the PR remains draft.

## Offline answer-key acceptance (authoring gate only)

- [Instructor answer key and grading rubric](INSTRUCTOR-ANSWER-KEY-RUBRICS.md) covers all 35 knowledge questions and seven tabletop scenarios. Require a correct answer with reasoning for 2 points; keywords alone receive at most 1; unsafe reasoning is 0 and a mandatory remediation.
- Suggested offline comprehension checks: **8/10 per lesson** and **12/14 across the separate tabletop**, with **no critical safety errors**. Never combine these into a production certification score.
- [Offline answer-key regressions](test_instructor_answer_keys.py) check per-level counts, beginner explanations, rubric coverage and V03 deferral. Automated checks cannot replace an independent instructor, security or Snowflake administrator review.

## V03 detailed acceptance for Level 1

- Use a designated training Snowflake account, a small permitted warehouse and a scratch schema.
- Verify CURRENT_USER, CURRENT_ROLE, CURRENT_WAREHOUSE, CURRENT_DATABASE and CURRENT_SCHEMA reflect approved context.
- Verify the VALUES expression returns 3 rows.
- Use an instructor-controlled empty scratch schema; verify no table-name collision. A Snowflake TEMP table can shadow a permanent table name; no schema-level CREATE TABLE grant is needed for TEMP table creation.
- Verify CREATE TEMP TABLE and INSERT create 3 rows in the isolated session.
- Verify aggregation: EAST -> 2 orders / 170 sales, WEST -> 1 order / 80 sales.
- End session and confirm the temporary table lifecycle. Record precise query IDs and anonymized outputs.
- Negative test: under a role without USAGE on the scratch schema, confirm object access/creation is denied as applicable; **do not** expect Snowflake TEMP CREATE to require CREATE TABLE privilege. Do not escalate to an admin role.
- Query text, identifiers, credentials and screenshots must be reviewed for sensitive information before archival.

## V03 detailed acceptance for Level 2

- Use non-admin monitoring and training roles. Verify SHOW WAREHOUSES and SHOW ROLES visibility under least privilege.
- SHOW GRANTS must list roles for the current user (not arbitrary role privileges).
- Session tag setting and unset must work; capture QUERY_TAG from Information Schema QUERY_HISTORY_BY_SESSION and its actual QUERY_ID.
- GENERATOR(ROWCOUNT => 100) must return 100.
- Verify QUERY_HISTORY_BY_SESSION function is available with an active database context and proper permissions, and note its 7-day history versus Account Usage 365-day retention. Record that outer WHERE filtering occurs after the table function's RESULT_LIMIT.
- Capture query ID, status, measured elapsed time, warehouse, cost, account edition and any permission error.
- No warehouse resize or production SUSPEND permitted as part of the lab.

## V03 acceptance for Levels 3–7

- **L3:** [Level 3 smoke](runtime/level-03-smoke.sql) confirms 1,000 distinct sequential IDs, SUM(AMOUNT)=54,110, exactly 100 rows where REGION_ID=1 and regional sum=5,060; capture Query Profile without asserting this tiny data is a real tuning benchmark.
- **L4:** [Level 4 smoke](runtime/level-04-smoke.sql) validates permission-gated historical views and nonempty/empty behavior; warehouse `CREDITS_USED` is gross usage, not final billed credits. Compare account `METERING_DAILY_HISTORY.CREDITS_BILLED` if permitted; record Account Usage latency and the `fail` status convention.
- **L5:** [Level 5 smoke](runtime/level-05-smoke.sql) confirms `CURRENT_SECONDARY_ROLES()` returns JSON-encoded text, `SHOW GRANTS` enumerates current-user roles, and optional aggregated `ACCOUNT_USAGE.LOGIN_HISTORY` is read with a permitted security-audit role; view latency can reach two hours. No raw user/IP/error-message export. Denied-access scenario remains documentation-only.
- **L6:** [Level 6 smoke](runtime/level-06-smoke.sql) checks `MIN_DATA_RETENTION_TIME_IN_DAYS` at account scope plus database/table `DATA_RETENTION_TIME_IN_DAYS`, supported table type and edition, and historical `AT(OFFSET => -60)` only on a previously approved lab object. Historical point must follow creation, fall within effective retention and be older than insertion. No object creation or recovery in the smoke; cleanup requires data-owner approval for any optional writable course lab.
- **L7:** [Level 7 smoke](runtime/level-07-smoke.sql) captures permitted current-session `QUERY_HISTORY_BY_SESSION` fields and optional aggregated `ACCOUNT_USAGE.QUERY_HISTORY` under an approved monitoring role. Distinguish `failed_with_error` (Information Schema) from `fail` (Account Usage) and account-history lag. Tabletop exercises reviewed with app/incident owner.

## Security, cost and change-management requirements

- Dedicated nonproduction account and minimal roles; no sample patient or real customer records.
- Avoid copying raw SQL text, bind values, names or secrets into CI artifacts or incident comments.
- Allowlist warehouse sizes and max credits for runtime testing; record warehouse resume, suspend and cumulative credits.
- Any GRANT/REVOKE, ALTER WAREHOUSE, DROP, DML recovery, failover or production change requires explicit approval and rollback plan.
- For recovery exercises, test RPO/RTO and data integrity on designated nonproduction objects.
- Revalidate documentation whenever Snowflake changes feature availability or SQL syntax.

## Technical sources reviewed (2026-10-30)

- https://docs.snowflake.com/en/sql-reference/functions/query_history
- https://docs.snowflake.com/en/sql-reference/account-usage/query_history
- https://docs.snowflake.com/en/sql-reference/account-usage
- https://docs.snowflake.com/en/sql-reference/sql/show-grants
- https://docs.snowflake.com/en/sql-reference/functions/current_secondary_roles
- https://docs.snowflake.com/en/sql-reference/sql/show-parameters
- https://docs.snowflake.com/en/sql-reference/functions/generator

## V03 readiness and attestation

- [V03 execution runbook](V03-EXECUTION-RUNBOOK.md) gives a safe operator procedure for running the seven SQL smoke scripts only with explicit authorization in a training account.
- [V03 preflight status](V03-PREFLIGHT-STATUS.md) identifies missing account access, approval, live output and reviewer evidence.
- [Offline evidence checker](validate_runtime_evidence.py) validates operator-submitted JSON locally. The checker does **not authenticate** QUERY_ID values or grant runtime acceptance by itself; at best it reports READY_FOR_INDEPENDENT_REVIEW.
- [Blank NOT_RUN template](V03-NOT-RUN-TEMPLATE.json) must remain empty in Git. Real query outputs and evidence must be kept in an approved secure repository outside GitHub.
- [Evidence regression tests](test_runtime_evidence.py) are synthetic unit tests, not live Snowflake execution.

**Deferred validation backlog:** obtain an approved nonproduction Snowflake connection and reviewer; when resumed, execute Level 1 then Level 2, collect actual query IDs/results and continue through Levels 3–7. Do not treat this as a prerequisite for offline teaching.
