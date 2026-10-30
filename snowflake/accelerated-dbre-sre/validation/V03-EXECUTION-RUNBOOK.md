# V03 — Nonproduction Snowflake Execution and Evidence Runbook

**State: NOT RUN — readiness materials only.** Audience: approved training account operator, Snowflake administrator and independent DBRE/SRE reviewer. Never execute in production or with real customer/patient data.

## Go / no-go preflight

| Control | Required |
|---|---|
| Account | Owner-confirmed TRAINING, STAGING or SANDBOX Snowflake account |
| Identity | Approved individual/automation identity and least-privilege non-admin role |
| Compute | Approved XS/Small warehouse, credit and time budget |
| Namespace | Dedicated, instructor-confirmed empty scratch schema and no object-name collisions |
| Authorization | Data-owner approval and change/test ticket for DDL or data changes |
| Privacy | Query text, credentials, actual account identifiers and user/IP/PHI never committed |
| Reviewer | Independent technical reviewer and private evidence store |
| Revision | Exact 40-character Git commit SHA used for execution |

**A TEMP table can shadow an existing permanent table of the same name.** An unused-looking name alone is not sufficient. Verify that the instructor controls the scratch schema and it is empty.

## Manual execution from Windows PowerShell

Snowflake CLI is optional. Snowsight can also run the training SQL. The connection alias used below must already exist and be confirmed to target a NONPRODUCTION account; the repository does not create credentials or connections.

~~~powershell
# Verify the CLI is available.
snow --version

# Confirm the active context before executing any training SQL.
snow sql --connection dbre-training --local-only --query "SELECT CURRENT_ROLE(), CURRENT_WAREHOUSE(), CURRENT_DATABASE(), CURRENT_SCHEMA();"

# With account and scratch namespace verified and authorization recorded:
snow sql --connection dbre-training --local-only --enhanced-exit-codes --filename snowflake/accelerated-dbre-sre/validation/runtime/level-01-smoke.sql

# After Level 1 acceptance, run the Level 2 script with its approved role:
snow sql --connection dbre-training --local-only --enhanced-exit-codes --filename snowflake/accelerated-dbre-sre/validation/runtime/level-02-smoke.sql
~~~

### Windows fail-closed preflight launcher (preferred)

An optional [PowerShell launcher](run-training-preflight.ps1) checks the *actual connected account locator*, role, warehouse, database and scratch schema against explicit operator-supplied expected values. By default it performs **read-only preflight only**. It never stores passwords or evidence, blocks administrator roles and requires an explicit typed confirmation before running the Level 1 or Level 2 SQL file.

~~~powershell
# Replace every SAMPLE_* placeholder with the authorized training account's values.
$base = 'snowflake/accelerated-dbre-sre/validation/run-training-preflight.ps1'
$expected = @{
  Connection = 'dbre-training'
  ExpectedAccountLocator = 'SAMPLE_ACCOUNT_LOCATOR'
  ExpectedOrganization = 'SAMPLE_ORGANIZATION'
  ExpectedRegion = 'SAMPLE_REGION'
  ExpectedRole = 'SAMPLE_LAB_ROLE'
  ExpectedWarehouse = 'SAMPLE_XS_WAREHOUSE'
  ExpectedDatabase = 'SAMPLE_TRAINING_DATABASE'
  ExpectedSchema = 'SAMPLE_EMPTY_SCRATCH_SCHEMA'
  ApprovedNonProductionAccount = $true
}

# First invocation only verifies context; no lab DDL or INSERT is executed.
& $base @expected -Mode Preflight

# After owner confirmation of the EMPTY scratch schema and change/test approval:
& $base @expected -Mode Level1 -ScratchSchemaVerifiedEmpty -ApprovalReference 'SAMPLE_APPROVED_TICKET'

# Run Level 2 only AFTER an independent reviewer has accepted Level 1 evidence:
& $base @expected -Mode Level2 -Level1Accepted -ApprovalReference 'SAMPLE_APPROVED_TICKET'
~~~

The approved account locator is the value of `CURRENT_ACCOUNT()`, not necessarily the organization-qualified account name. The launcher also matches `CURRENT_ORGANIZATION_NAME()` and `CURRENT_REGION()` to reduce the risk of connecting to an unintended account with a similar locator. Ask the account owner for the exact locator and case-sensitive context values. **The PowerShell script itself has not been run against Snowflake or tested under a local PowerShell interpreter here.** It is an optional safeguard and does not replace independent review or prevent connection configuration changes between the preflight and SQL execution.

The `--local-only` CLI option **does not execute SQL offline**. It blocks `!source` and `!load` from fetching remote HTTP(S) files; all SQL statements still execute against the connected Snowflake account. Do not treat this flag as a nonproduction safety control. <https://docs.snowflake.com/en/developer-guide/snowflake-cli/command-reference/sql-commands/sql>

The name "dbre-training" is a placeholder for a *preapproved nonproduction connection*. Do not automate these commands against unknown or production aliases. Review the SQL before running. Do not redirect raw CLI output to a shared log. If a Level 2 SQL worksheet stops before ALTER SESSION UNSET QUERY_TAG, execute the cleanup in the **same session**, or document session termination and cleanup.

Later levels use separate files under [runtime/](runtime/README.md). Level 3 creates a temporary table in the scratch schema. Levels 4–7 are read-only by design. Level 6 historical reads require a pre-existing, specifically approved training table and verified retention. Optional monitoring/security views require separate account-usage grants; record missing permissions as BLOCKED.

## Required evidence per level

| Level | Required test IDs |
|---|---|
| 1 | session_context, sample_values, temporary_table, aggregates, assertion, session_cleanup |
| 2 | session_context, role_visibility, generated_rows, tagged_history, tag_cleanup |
| 3 | session_context, namespace_check, generated_table, assertion, query_profile, session_cleanup |
| 4 | warehouse_metering, warehouse_load, query_failures, billing_history |
| 5 | role_context, show_grants, show_roles |
| 6 | account_retention, database_retention |
| 7 | session_context, recent_query_history, tabletop |

Optional test IDs: Level 5 login_history; Level 6 table_retention and time_travel; Level 7 account_query_history. If data is absent or access denied, record BLOCKED rather than PASS.

For Levels 1–3, record **actual** numeric outcomes. Level 1 expects three sample rows; EAST 2/170 and WEST 1/80. Level 2 expects 100 generated rows and confirmed query-tag cleanup. Level 3 expects 1,000 rows, 1,000 unique IDs, total 54,110, region 1 count 100, region 1 total 5,060. These numbers are proposed expectations, **not execution evidence**.

## Offline evidence gate

The [blank evidence template](V03-NOT-RUN-TEMPLATE.json) is intentionally marked NOT_RUN and contains no query IDs. After approved execution, create a copy in a **private secure workspace**, not GitHub. Fill in the execution timestamp in UTC, git revision SHA, sanitized role/account/warehouse aliases, approval reference, query IDs, test outcomes, actual numeric assertions, manual cleanup attestation, and redaction confirmation.

~~~powershell
python snowflake/accelerated-dbre-sre/validation/validate_runtime_evidence.py --input C:\SecureLabEvidence\level-01-evidence.json
~~~

### Query-ID capture and verification

Both Level 1 and Level 2 SQL files now end with a **same-session** `QUERY_HISTORY_BY_SESSION` query, returning query IDs, query type, execution status and timing **without exporting QUERY_TEXT**. The operator must match these IDs to the statements just executed and record the actual numeric results. A query-history row or shaped UUID alone does not prove the expected result, and the CLI may use another session for a separate `snow sql` invocation. The history query is last in the SQL file for this reason. If it fails due to permissions or context, mark evidence **BLOCKED** rather than invent IDs.

The offline checker rejects missing evidence, privileged identities, production classification, missing tests, incorrect arithmetic and unexpected sensitive fields. Its best possible outcome is **READY_FOR_INDEPENDENT_REVIEW**. It cannot authenticate Snowflake query IDs or grant V03 PASS, V04 approval or V05 certification. The reviewer must independently match query IDs and the documented results inside Snowflake and sign off using [the evidence form](RUNTIME-EVIDENCE-TEMPLATE.md).

## Mock-only regression coverage

The [PowerShell mock preflight tests](test-training-preflight.ps1) run under GitHub Actions and check nonproduction account matching and failure-to-proceed controls **without real Snowflake access**. [CI run #144](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41124509495) passed. Mock results are not proof of Snowflake connectivity or SQL result correctness. See [V03 readiness blocker tracker](V03-PREFLIGHT-STATUS.md).

## Official CLI docs

- https://docs.snowflake.com/en/developer-guide/snowflake-cli/command-reference/sql-commands/sql
- https://docs.snowflake.com/en/developer-guide/snowflake-cli/connecting/configure-connections
- https://docs.snowflake.com/en/user-guide/tables-temp-transient

**Status on authoring:** No connected Snowflake training account was available to execute any of these tests. All seven V03 execution gates remain NOT RUN.
