# V01 / V02 Initial Technical Audit — 2026-10-30

**Scope:** Snowflake accelerated DBRE/SRE Levels 1–7, branch feature/snowflake-7-level-dbre-sre-20261030.  
**Status:** Initial source verification + editorial remediation complete; automated V01/V02 static CI passed; independent peer review outstanding.  
**Not performed:** No credentials or live Snowflake session available; no SQL execution, warehouse operations, actual performance test, or production acceptance.

## Verified authoring inventory
- Seven 60-minute standalone lesson drafts (420 minutes total).
- README, STATUS, troubleshooting, expected results, official docs, safety sections and quizzes.
- Source SQL uses scratch objects or read-only monitoring except controlled session tagging and optional lab-only data generation.
- No obvious embedded passwords, private keys or AWS access key strings found in initial textual scan.
- Relative links and code-fence balance checked with repository reads at authoring time.

## Findings and remediation
| ID | Severity | Finding | Remediation | Status |
|---|---|---|---|---|
| SF-001 | P2 | Level 1 CREATE OR REPLACE could conceal accidental repeat or replacement | Use CREATE TEMP TABLE with distinctive name; fail rather than overwrite | Remediated |
| SF-002 | P2 | Level 3 repeated SEQ4 expressions may not describe correlated synthetic fields | Derive fields from one ROW_NUMBER sequence; specify 1,000/100 expected rows | Remediated |
| SF-003 | P2 | Level 4 query-history statuses differ between Account Usage and Information Schema | Document explicit difference; use fail for Account Usage | Remediated |
| SF-004 | P1 | Level 6 permanent training table and offset timing needed explicit retention/cleanup safeguards | Clarify offset after INSERT, unique lab name, no OR REPLACE, owner-approved cleanup | Remediated in documentation; runtime pending |
| SF-005 | P1 | No runtime verification or proof of least-privilege/edition behavior | Add evidence template and V03 plan; leave all levels NOT RUN | Open |
| SF-006 | P2 | Authoring validation previously not repeatable in CI | Add stdlib validator and GitHub Actions gate | PASS — GitHub Actions run #41061594991 |

## Important documentation distinctions
- Information Schema QUERY_HISTORY can cover the last 7 days and uses statuses including failed_with_error; Account Usage QUERY_HISTORY retains about 365 days and uses success/fail/incident.
- QUERY_HISTORY Account Usage latency can be about 45 minutes; WAREHOUSE_LOAD_HISTORY can be up to about 3 hours.
- SHOW GRANTS with no extra clause lists roles granted to the current user, not every grant on an arbitrary object.
- Snowflake CURRENT_SECONDARY_ROLES() is documented and returns a JSON-encoded VARCHAR.
- A small synthetic table does not demonstrate meaningful performance improvements at production scale.

## Validation disposition
**Documentation:** V01/V02 automated static CI PASS; subject to independent technical review.  
**Live labs:** BLOCKED / NOT RUN (no authorized connection).  
**Production certification:** NOT CERTIFIED. Do not merge solely because the static linter passes.  
**Next:** verify automated CI then run Level 1–2 with a restricted training role; record evidence, fix any runtime findings and continue sequentially.

## Verified CI execution

- Workflow: [Snowflake accelerated curriculum static validation](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41061594991)
- Result: **success**, job `validate-snowflake-accelerated`, including checkout and static gate step.
- Level 1–2 runtime smoke scripts are prepared but **not executed**.
