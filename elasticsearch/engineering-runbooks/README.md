# Elasticsearch Engineering Runbook Library

> **Canonical production-runbook candidate — documentation/static checks complete; operational validation pending.** The 15 procedures are suitable for structured engineering testing and review, but **not yet certified for execution against production**. Each runbook must be approved for the exact cluster version and deployment before being marked production validated. The leadership policy defines decision ownership; these runbooks define execution.

**Start here:** [Production readiness gates](PRODUCTION-READINESS.md) · [Runbook-by-runbook validation matrix](VALIDATION-MATRIX.md) · [Cluster test evidence template](templates/cluster-validation-record.md) · [Safe staging request payloads](templates/payloads/README.md)


**Status: DRAFT for peer review and nonproduction validation — not certified for production execution.**  
**Related leadership policy:** Elasticsearch Governance and Operational Ownership Policy v2.1 (maintained separately).  
**Owner:** DBRE/SRE for the runbook library; each page names its technical owner and collaborating teams.  
**Version baseline:** Elasticsearch 7.17-era REST API behavior where applicable. **7.17.x reached end of support on 2026-01-15**; upgrade planning and version-specific API verification are required for any cluster still on 7.17. These commands were **reviewed against official documentation but not executed on your clusters**.

## Before starting

- Use Basic Auth and a verified environment URL. With HTTPS, curl uses normal certificate verification through its trust store; no certificate-file argument is necessary. Apply least-privilege permissions. See [Basic Auth quickstart](templates/basic-auth-quickstart.md).
- Any commands that create/change/delete resources require an approved Jira ticket, maintenance window where needed, explicit go/no-go, operator and rollback owner. Never paste real credentials or sensitive document content into repository files.
- Diagnose read-only first. Cluster rescue, forced shard allocations, disk watermark bypass and destructive wildcard deletion are **not included** as copy-and-run examples.
- Documentation follows: **trigger → prechecks → approval/steps → stop conditions → validation → rollback/evidence**. See [Runbook template](templates/runbook-template.md) and [Jira template](templates/jira-maintenance-template.md).

## Runbook index

| # | Runbook | Lead | Priority |
|---|---|---|---|
| 01 | [Cluster health and incident troubleshooting](01-cluster-health-incidents.md) | DBRE/SRE | P1 |
| 02 | [Disk pressure and storage expansion](02-disk-pressure-capacity.md) | DBRE/SRE | P1 |
| 03 | [Oversized shard remediation and planned reindexing](03-oversized-shard-remediation.md) | DBRE/SRE | P1 |
| 04 | [Index creation and mapping changes](04-index-creation-mappings.md) | Data Engineering | P1 |
| 05 | [Reindexing, alias cutover and rollback](05-reindex-alias-cutover-rollback.md) | DBRE/SRE (operational execution) | P1 |
| 06 | [Data retention and ILM implementation](06-retention-ilm.md) | DBRE/SRE (implementation) | P1 |
| 07 | [Unused-index cleanup automation](07-unused-index-cleanup.md) | DBRE/SRE (automation, scheduling) | P1 |
| 08 | [Search and indexing performance troubleshooting](08-performance-troubleshooting.md) | DBRE/SRE (platform diagnosis) | P1 |
| 09 | [Snapshot, restore and disaster recovery](09-snapshot-restore-dr.md) | DBRE/SRE | P1 |
| 10 | [Cluster scaling and compute right-sizing](10-cluster-rightsizing.md) | DBRE/SRE | P2 |
| 11 | [Rolling upgrades and patching](11-rolling-upgrades.md) | DBRE/SRE | P2 |
| 12 | [Shard allocation and recovery troubleshooting](12-shard-allocation-recovery.md) | DBRE/SRE | P2 |
| 13 | [JVM, heap, cache and memory troubleshooting](13-jvm-heap-cache.md) | DBRE/SRE | P2 |
| 14 | [Index data growth analysis and capacity forecasting](14-data-growth-capacity-forecast.md) | Data Engineering (index growth) | P2 |
| 15 | [Elasticsearch cloud cost optimization and FinOps](15-cloud-cost-finops.md) | FinOps (cost reporting) | P2 |

## Change-control integration

Each change follows: **Request → Assess → Approve → Execute → Validate → Close**. Business Owner and Data Engineering jointly define retention; Index Owner verifies eligible cleanup; DBRE/SRE implements and operates cluster changes; Application Engineering tests user-facing search; FinOps analyzes costs. Apply the formally adopted policy to determine who can approve each action.

## Validation and adoption

1. Use [the validation matrix](VALIDATION-MATRIX.md) to choose a runbook and identify its read-only and controlled-test cases.
2. Use the [test evidence record](templates/cluster-validation-record.md) for your actual cluster, saving redacted outputs and approvals in Jira. Begin with read-only diagnostics even on production; test mutations on staging or under an independently authorized maintenance change.
3. Reconcile detected API/version differences with the exact deployed Elasticsearch patch version and provider documentation. Preserve the baseline and stop conditions.
4. Apply the [production readiness criteria](PRODUCTION-READINESS.md) **individually**; do not mark all runbooks approved from a single smoke test.
5. The docs-only CI workflow checks syntax and documentation conventions, not runtime API behavior, data correctness or recovery.

**Quality-control automation:** `python3 scripts/validate_runbooks.py` runs the offline static gate. It does not access Elasticsearch.

## Verification status and known limitations

- API shapes and links were desk-reviewed; **no live cluster execution, credentials, workload tests, staging verification or independent approval**.
- Existing runbooks in `elasticsearch/runbooks/` are preserved. This is a separate collection.
- For 7.17, consult version-specific archived documentation. APIs, behavior, and security options can differ in 8.x/9.x. Do not run newer-only APIs on 7.17.
- Do not infer that asynchronous task cancellation rolls back work. A force-merge task is not cancelable.
- The final production-ready version requires version-matched validation, accurate approval contacts, example output, peer review, and change-control signoff.

## Primary sources

- [Elastic REST API reference](https://www.elastic.co/docs/reference/elasticsearch/rest-apis)
- [Elastic basic authentication and HTTPS client security](https://www.elastic.co/docs/deploy-manage/security/httprest-clients-security)
- [Elastic end-of-life dates](https://www.elastic.co/support/eol)
- [FinOps Foundation framework](https://www.finops.org/framework/)
