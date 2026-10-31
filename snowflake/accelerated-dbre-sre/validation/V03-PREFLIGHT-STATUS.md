# V03 Runtime Validation Readiness — 2026-10-30

**Live Snowflake execution:** NOT RUN. **Latest attempt:** 2026-10-30, no connected Snowflake provider/session available in this chat; zero SQL executed and zero actual query IDs captured. **Production certification:** NOT CERTIFIED.

## Prepared controls

| Requirement | Status |
|---|---|
| Seven manual SQL smoke scripts | Authored; static safety gates previously passed |
| V03 nonproduction execution runbook | Authored: [V03 execution guide](V03-EXECUTION-RUNBOOK.md) |
| Blank evidence template | Authored as NOT_RUN only |
| Offline evidence checker | Added, pending/subject to GitHub Actions regression gate |
| Evidence gate regression tests | Added, pending/subject to GitHub Actions regression gate |
| Local raw output hygiene | Runtime evidence directory git-ignored; never commit unredacted outputs |
| Authorized Snowflake training connection | NOT AVAILABLE in this ChatGPT session |
| Approving owner/test ticket | NOT VERIFIED |
| Independent DBA/security reviewer | PENDING |
| Actual query IDs, outputs and credit costs | NOT AVAILABLE |

## Manual go/no-go criteria

To advance any level to V03 runtime evidence acceptance: authorized training/staging account, least-privilege role, approved test warehouse and scratch schema, owner-approved DDL scope, actual query IDs and outcomes, cleanup evidence, external reviewer verification, and recorded account edition/feature limitations.

The offline JSON checker explicitly produces READY_FOR_INDEPENDENT_REVIEW, not certification. This avoids treating self-reported results as authenticated query execution.

**Review decision:** V03 tooling prepared. **User requested deferral of all live runtime validation on 2026-10-30** to finish other authoring/review materials first. Do not attempt further Snowflake connection setup in this phase. Runtime and certification remain NOT RUN / NOT CERTIFIED. PR #43 remains DRAFT.

## Official reference

- [Snowflake CLI execution](https://docs.snowflake.com/en/developer-guide/snowflake-cli/command-reference/sql-commands/sql)

## Level 1 / Level 2 execution checkpoint (2026-10-30)

- **Requested:** execute Level 1 against authorized Snowflake training, capture actual query IDs/results, then Level 2.
- **Connectivity check:** no Snowflake connector tools/session are connected to the assistant; Snowflake plugin is available for user connection but not installed/connected. No credentials were requested or handled.
- **Outcome:** **BLOCKED — connection absent**, not a SQL failure or a lab PASS. No production or training account queried.
- **CLI context pinning:** The V03 launcher now explicitly passes the expected role, warehouse, database and schema for preflight and lesson commands. Positive Level 1/Level 2 execution confirmation paths are exercised only against the mocked `snow` function. CI verification is tracked separately; **no live execution is implied**.
- **Improved identity check:** The PowerShell preflight requires `CURRENT_ORGANIZATION_NAME()`, `CURRENT_REGION()` and `CURRENT_ACCOUNT()` as well as exact role/warehouse/database/schema. The comparison is to an **operator-attested** approved training account, not an independently authenticated environment classification. [CI run #134 — PASS](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41123715672) (syntax-only PowerShell check and Python tests).
- **Additional Windows preflight:** [run-training-preflight.ps1](run-training-preflight.ps1) is a *local operator-executed* safety helper with default read-only mode, explicit account/role/context verification, no admin role, and typed confirmation before running L1/L2. It is **NOT RUNTIME TESTED**. `--local-only` restricts remote SQL-source directives only; it does not prevent live database execution.
- **Improvement committed:** [Level 1 SQL](runtime/level-01-smoke.sql) and [Level 2 SQL](runtime/level-02-smoke.sql) now capture recent same-session `QUERY_ID`, `EXECUTION_STATUS` and timing without exposing raw query text. [V03 runbook](V03-EXECUTION-RUNBOOK.md) explains secure evidence handling.
- **Latest static-only CI:** [Run #111 — PASS](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41119260657), includes validator and offline evidence regression tests; it is **not** runtime execution.
- **Next action:** user connects authorized nonproduction Snowflake provider, or an approved operator executes scripts in a training account and provides sanitized results and query IDs for independent review.

## Mocked PowerShell integration gate — 2026-10-30

- [CI run #144: PASS](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41124509495).
- [test-training-preflight.ps1](test-training-preflight.ps1) installs a local PowerShell mock of the Snowflake CLI command before invoking the operator launcher.
- Verified: matching nonproduction account passes read-only preflight; wrong account locator/organization/region, administrative role, missing owner attestation, missing L1 scratch-schema sign-off, missing L2 acceptance, and a simulated query failure all fail closed. **Zero live Snowflake calls**.
- The simulated CLI failure leaves a nonzero `LASTEXITCODE`, which the test runner now clears after confirming expected refusal behavior. This is test harness bookkeeping only.
- **Actual V03 execution remains BLOCKED:** Snowflake plugin is available but not connected. The assistant cannot access the operator's Windows machine or Snowflake CLI configuration.
