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
- Session tag setting and unset must work; capture QUERY_TAG from Information Schema QUERY_HISTORY_BY_USER.
- GENERATOR(ROWCOUNT => 100) must return 100.
- Verify QUERY_HISTORY_BY_SESSION function is available with an active database context and proper permissions, and note its 7-day history versus Account Usage 365-day retention. Record that outer WHERE filtering occurs after the table function's RESULT_LIMIT.
- Capture query ID, status, measured elapsed time, warehouse, cost, account edition and any permission error.
- No warehouse resize or production SUSPEND permitted as part of the lab.

## V03 acceptance for Levels 3–7

- **L3:** [Level 3 smoke](runtime/level-03-smoke.sql) confirms 1,000 distinct sequential IDs, SUM(AMOUNT)=54,110, exactly 100 rows where REGION_ID=1 and regional sum=5,060; capture Query Profile without asserting this tiny data is a real tuning benchmark.
- **L4:** [Level 4 smoke](runtime/level-04-smoke.sql) validates permission-gated historical views and nonempty/empty behavior; warehouse `CREDITS_USED` is gross usage, not final billed credits. Compare account `METERING_DAILY_HISTORY.CREDITS_BILLED` if permitted; record Account Usage latency and the `fail` status convention.
- **L5:** CURRENT_SECONDARY_ROLES and SHOW GRANTS execute with a read-only role; access-denied scenario is documentation-only.
- **L6:** Retention scope and edition confirmed; optional permanent scratch table has a uniquely qualified location; Time Travel point is after table creation; cleanup requires data-owner approval.
- **L7:** QUERY_HISTORY function fields and visibility confirmed; tabletop exercises reviewed with app/incident owner.

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

**Next review target:** execute Level 1 and Level 2 in a training account; peer-review Level 3–7 SQL and safety constraints prior to runtime validation.
