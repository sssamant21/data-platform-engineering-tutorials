# Independent Review and Production Acceptance Handoff — V04 / V05

**Date prepared:** 2026-10-30  
**Package:** [Accelerated Snowflake curriculum](../README.md), seven 60-minute lessons.  
**Status:** **PREPARED FOR REVIEW; NO INDEPENDENT SIGN-OFF.** All Snowflake runtime labs V03 = **NOT RUN / USER-DEFERRED**. V05 = **NOT CERTIFIED**.

## V04 — Independent review criteria

| Workstream | Required independent reviewer | Evidence / decision required | State |
|---|---|---|---|
| Lesson technical accuracy | Snowflake administrator / senior DBRE | Verify current SQL syntax, results/limits, edition and privilege prerequisites in an authorized test account | PENDING |
| Runtime evidence | Snowflake administrator and DBRE test owner | Authenticate actual query IDs, expected vs actual rows, failures, cost and cleanup for each level | DEFERRED — no V03 outputs |
| Access and data safety | Security/IAM and data owner | Validate least privilege, synthetic data boundaries, aggregation/redaction and identity protection | PENDING |
| Performance and observability | Application/data engineering owner | Verify metrics definitions, queue semantics, historical latency, cost and coverage of critical use cases | PENDING |
| Time Travel/DR | Snowflake administrator and DR lead | Verify retention by edition/object type, tested rollback, RPO/RTO, recoverability and downstream dependencies | PENDING |
| Curriculum usability | Trainer plus a novice learner | Check navigation, exercises, answer keys and that seven independent 60-minute sessions fit the stated audience | PENDING |

**Review decision (to be completed by real reviewer):** `APPROVED / CHANGES_REQUESTED / BLOCKED`  
**Reviewer reference:** `[not provided]`  
**Evidence location:** `[approved private evidence store]`  
**Defects with owners:** `[not yet logged]`

A draft instructor artifact is not proof of external review. No placeholder above can be treated as an approval.

## V05 — Enterprise / production certification (separate and gated)

The following are *acceptance requirements*, **not achieved milestones**:

- [ ] V03 live exercises executed in the correct training account, with genuine query IDs and reviewed outputs.
- [ ] V04 independent Snowflake admin, DBRE, Security and Data Owner reviews approved and traceable.
- [ ] Business-critical workloads and datasets identified; SLO, traffic and change windows approved by application owners.
- [ ] Performance baselines established with representative data volumes, including queueing, query p95/p99 and tuning regression checks.
- [ ] Cost budgets and alerts validated; gross warehouse usage distinguished from billed account credits.
- [ ] RBAC governance, audit access, redaction, service-authentication and break-glass controls reviewed.
- [ ] Recovery/DR tabletop plus authorized restore/failover evidence; RPO/RTO objectives and data validation accepted.
- [ ] Incident escalation, communications, rollback owner and blameless RCA/action tracking tested.
- [ ] Security review of runtime evidence retention, secret handling and environment-specific account settings.
- [ ] Final production-release go/no-go signed by accountable stakeholders; retest date and version documented.

**Certification:** NOT CERTIFIED.  
**PR #43:** DRAFT. Do not automatically merge based on static CI or this checklist.

## Known limitations of completed offline work

- Automated checks verify Markdown/links, selected Snowflake SQL patterns and safety heuristics. They **do not** parse full Snowflake grammar.
- The offline V03 evidence checker validates a record's shape and expected values but cannot authenticate query IDs.
- PowerShell preflight CI uses a mocked `snow` command; it **does not** confirm real Snowflake CLI authentication or runtime safety.
- An operator signing into Snowsight does not establish that a configured CLI profile points to the **approved** training account.
- Independent approvals must come from authorized humans, not the assistant or a GitHub Actions job.

## When the user resumes V03

1. Open [V03 readiness tracker](V03-PREFLIGHT-STATUS.md); verify account/connection, role, warehouse, scratch schema and owner authorization.
2. Follow [the controlled execution runbook](V03-EXECUTION-RUNBOOK.md) starting with Level 1 and not automatically proceeding to Level 2.
3. Store actual sanitized outputs/query IDs privately and use the [offline evidence validator](validate_runtime_evidence.py) as an initial completeness check only.
4. Obtain independent reviewer acceptance before changing any runtime status in [STATUS.md](../STATUS.md).
5. Revisit V04 and V05 gates; retain not-certified status until approvals and actual testing are complete.
