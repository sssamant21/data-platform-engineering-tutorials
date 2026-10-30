# Snowflake Levels 1–2 Runtime Smoke Pack

These SQL scripts are **manual, nonproduction acceptance tests** only. GitHub Actions does not run SQL or connect to Snowflake.

- [Level 1 smoke](level-01-smoke.sql): session context, VALUES data, scratch temporary table, 3-row insert, aggregation and PASS/FAIL assertion.
- [Level 2 smoke](level-02-smoke.sql): active context, warehouse and role visibility, query tag, 100 generated rows, tagged query history, tag cleanup.
- [Validation plan](../VALIDATION-PLAN.md): prerequisites, levels 1–7 acceptance, negative cases and evidence.
- [Evidence form](../RUNTIME-EVIDENCE-TEMPLATE.md): complete one per authorized execution.

## Execution procedure

1. Confirm the **training** Snowflake account, small approved warehouse, scratch schema, role and credit budget. Never run in production.
2. Open each script in Snowsight and review statements before executing.
3. Run Level 1 in a new session with CREATE TABLE privilege **only on the scratch schema**. The temporary table is dropped automatically when the session ends; if a name already exists, stop, do not overwrite.
4. Run Level 2 under an approved least-privilege role. If a SHOW command or query history is not visible, record the permission or visibility gap; don't escalate to ACCOUNTADMIN.
5. Record QUERY_ID, version/edition if available, actual rows, elapsed time, warehouse credit estimate, unexpected errors and reviewer sign-off.
6. Verify cleanup. Redact any identity, query text, credentials and sensitive results before posting evidence.

**Test status: NOT RUN.** Writing executable SQL and a CI static pass cannot establish Snowflake runtime behavior.
