# NN — [Operation title]

> **Status:** DRAFT / STAGING VALIDATED / PRODUCTION VALIDATED (scope-limited)  
> **Technical owner:** [DBRE/SRE or Data Engineering] · **Reviewers:** [Application, Data, Index Owner, FinOps, Business where applicable]  
> **Supported Elasticsearch patch versions tested:** [exact versions] · **Provider/deployment:** [self-managed or hosted]  
> **Last executed/tested:** [UTC date] · **Jira evidence:** [ticket] · **Next review:** [date]

## When to use

[Measurable trigger and business impact; conditions where this runbook must NOT be used]

## Execution guardrails

- Exact target cluster/UUID, environment, index/alias, operator permissions and maintenance approval.
- Read-only commands may be exercised with approved account and load considerations; changes require a separate change authority decision.
- Use Basic Auth with `curl --basic --user "$ES_USER"`; do not embed passwords or pass client/CA cert files. HTTPS must retain normal trust-store validation.
- Prohibited emergency shortcuts and operations requiring separate escalation.

## Prechecks / read-only diagnostics

[Baseline, expected result, interpretation, exit code and missing-permission escalation.]

```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  "$ES_URL/_cluster/health?pretty"
```

## Approved procedure

1. [Approved exact request JSON + index names; version-check and change-ticket ID]
2. [Go/no-go checklist: data backup/replay, disk headroom, service readiness, team approvals]
3. [Step-by-step execution with task-state checks, expected output, and decision branches]
4. [Validation and stabilization duration]

## Monitoring and stop-work conditions

[Concrete target thresholds and failure signals, page/escalation owner, incident transition]

## Success criteria and evidence

[Expected outputs, data reconciliation, SLO, cluster state, snapshots/recovery, charts, owner signoff]

## Rollback / recovery

[Reversible settings vs irreversible changes, exact rollback test and conditions, reindex post-write handling]

## Staging/production validation record

[Link to ../VALIDATION-MATRIX.md and templates/cluster-validation-record.md; test log, exact version, review, Jira]

## Official references

[Version-matched Elastic/vendor links and reviewed last date]
