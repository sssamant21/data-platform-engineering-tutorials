# Snowflake Accelerated DBRE/SRE — Validation Tracker

**Last authored:** 2026-10-30  
**Source:** seven-course onboarding request  
**Scope:** `snowflake/accelerated-dbre-sre/` only; canonical 90-chapter curriculum unchanged.

| Level | File | Authored | Markdown/static QA | Snowflake runtime lab | Independent tech review | Production certification |
|---|---|---|---|---|---|---|
| 1 | [Snowflake Fundamentals](level-01-snowflake-fundamentals.md) | DRAFT | V01/V02 automated PASS; independent review pending | NOT RUN | PENDING | NOT CERTIFIED |
| 2 | [Snowflake Administration Fundamentals](level-02-administration-fundamentals.md) | DRAFT | V01/V02 automated PASS; independent review pending | NOT RUN | PENDING | NOT CERTIFIED |
| 3 | [Snowflake Performance Tuning and Query Optimization](level-03-performance-query-optimization.md) | DRAFT | V01/V02 automated PASS; independent review pending | NOT RUN | PENDING | NOT CERTIFIED |
| 4 | [Snowflake Monitoring, Observability, and Cost Optimization](level-04-monitoring-observability-cost.md) | DRAFT | V01/V02 automated PASS; independent review pending | NOT RUN | PENDING | NOT CERTIFIED |
| 5 | [Snowflake Security, RBAC, and Governance](level-05-security-rbac-governance.md) | DRAFT | V01/V02 automated PASS; independent review pending | NOT RUN | PENDING | NOT CERTIFIED |
| 6 | [Snowflake Data Recovery and Disaster Recovery](level-06-data-recovery-disaster-recovery.md) | DRAFT | V01/V02 automated PASS; independent review pending | NOT RUN | PENDING | NOT CERTIFIED |
| 7 | [Snowflake Production Troubleshooting and Incident Response](level-07-production-incident-response.md) | DRAFT | V01/V02 automated PASS; independent review pending | NOT RUN | PENDING | NOT CERTIFIED |

## Initial V01/V02 CI gate

- **Automated static validation:** PASS — [GitHub Actions run #41061594991](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41061594991).
- **Reproducible command:** `python3 snowflake/accelerated-dbre-sre/validation/validate_courses.py`.
- **Technical audit:** [V01/V02 initial audit](validation/V01-V02-INITIAL-AUDIT.md).
- **Second-pass technical review:** [V02 findings SF-007–SF-012](validation/V02-SECOND-PASS-REVIEW.md).
- **Level 3–4 follow-on review:** [V02 findings SF-013–SF-017](validation/V02-LEVELS-03-04-REVIEW.md); [Level 3 smoke](validation/runtime/level-03-smoke.sql) and [Level 4 smoke](validation/runtime/level-04-smoke.sql) are prepared for **manual nonproduction** runtime testing.
- **Level 5–7 follow-on review:** [V02 findings SF-018–SF-024](validation/V02-LEVELS-05-07-REVIEW.md); [L5](validation/runtime/level-05-smoke.sql), [L6](validation/runtime/level-06-smoke.sql) and [L7](validation/runtime/level-07-smoke.sql) read-only smoke scripts are authored, **NOT RUN**.
- **SQL safety regression tests:** [test_validator.py](validation/test_validator.py), required by the [CI workflow](../../.github/workflows/snowflake-accelerated-static.yml). Latest revision's CI run must pass before V02 static verification is considered complete.
- **Test execution plan:** [Validation plan](validation/VALIDATION-PLAN.md); [Levels 1–2 smoke pack](validation/runtime/README.md).
- A CI PASS is an initial authoring/safety filter, not execution evidence or an independent security review.

## Latest verification boundary

- [Run #43 — passed](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41103967587) for the prior seven-course validator and regression-test revision.
- **Previous expanded CI check:** [Run #62 — PASS](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41105075877), for the Levels 1–4 revision. **Levels 5–7 expanded CI:** [Run #83 — PASS](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41106248957), commit `61197443f464b657af0fd5fae3528d59d6479f26`, including the read-only L5/L6/L7 smoke scripts and SQL safety regression tests.
- No Snowflake SQL has been executed; all seven runtime labs remain **NOT RUN**.
- **CLI preflight hardening (2026-10-30):** [Windows operator launcher](validation/run-training-preflight.ps1) defaults to read-only, verifies exact org/account locator/region/role/warehouse/database/schema against operator-approved values, and requires typed authorization before L1/L2. [Latest CI #134 — PASS](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41123715672), including PowerShell parse-only validation. **Script has not executed against Snowflake.**
- **Execution attempt (2026-10-30): BLOCKED — no connected Snowflake training session.** Level 1 and Level 2 actual SQL results and query IDs remain unavailable. Same-session query-history capture added to both smoke scripts. [Static CI run #111 — PASS](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41119260657) does not satisfy V03.
- **V03 readiness package:** [operator runbook](validation/V03-EXECUTION-RUNBOOK.md), [preflight blocker register](validation/V03-PREFLIGHT-STATUS.md), [offline evidence checker](validation/validate_runtime_evidence.py) and [blank NOT_RUN template](validation/V03-NOT-RUN-TEMPLATE.json). The new local evidence checks and regression tests are subject to a separate CI run. **No evidence has been submitted.**

## V03 mock execution safety evidence — 2026-10-30

- [Run #144 — PASS](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41124509495): 48 Python tests and a PowerShell mocked nonproduction preflight suite. The mock rejects incorrect account locator/organization/region, admin role, absent nonproduction owner attestation, missing L1 empty-scratch approval, missing L2 acceptance, and a simulated CLI connection error.
- No live Snowflake account was contacted by the mock tests. **All seven V03 runtime labs remain NOT RUN**, and no genuine query IDs exist.

## Validation gates
- **V01 Structure:** headings, all seven agenda totals = 60 minutes, README navigation, cross-links and status labels.
- **V02 Safety:** SQL syntax and least privilege; no live secrets, no destructive production operations, training account requirements explicit.
- **V03 Runtime:** execute labs with minimal roles in a training account; record actual outputs, account edition, query IDs and costs.
- **V04 Independent review:** Snowflake administrator and application/data-owner approval.
- **V05 Certification:** applicable enterprise SLOs, security controls, operational sign-off and periodic revalidation.

## Initial validation evidence
- Authored seven standalone lessons with objectives, 60-minute agenda, concepts, hands-on lab, expected outcomes, troubleshooting, quiz/answers and official docs.
- Automated CI verified structural checks, lesson durations, navigation, code fences and obvious unsafe-SQL/secret patterns. **No live Snowflake environment was accessed**.
- Do not count the courses as certified or claim runtime results from illustrative expected outputs.
