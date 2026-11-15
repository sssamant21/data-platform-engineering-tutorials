# Production readiness and operator safety standard

**Status: Production-execution candidates; not yet cluster-validated or approved.** This library becomes the canonical reference **after** each runbook passes version-matched execution testing and stakeholder approvals. A merged Markdown file is not, by itself, an authorization to change production.

## Mandatory preflight, for every use
1. Identify cluster URL, exact environment, cluster name/UUID, ES version, service/data owners and Jira ticket. Confirm GET / returns the intended cluster. Run only with least-privilege authorization and interactive Basic Auth (no password in command history).
2. Match this runbook to the deployed Elasticsearch **version and deployment type** (self-managed versus hosted provider). Official current-version API docs are not proof of 7.17 compatibility. Capture curl version and installed CLI prerequisites.
3. Check impact, traffic, node health, worst-node storage headroom, shard recovery, snapshot/restore readiness and relevant application/ingestion dependencies. This check should not itself change cluster state.
4. For mutations, record the actual reviewed JSON request body (not a sample), exact names (never a wildcard or managed system index), risk assessment, approvers, maintenance window, go/no-go thresholds, on-call lead, and specific recovery strategy.
5. Execute **read-only prechecks first**. Never run example PUT, DELETE, POST restore, ILM, reindex or aliases commands on production just to test the documentation.
6. Monitor the agreed signals during any approved change; capture task IDs and complete responses, not just an HTTP 2xx. Stop/escalate when results differ from expectations.
7. Obtain Data Engineering validation of data correctness and Application validation of search behavior where relevant. Record before/after metrics and approval in Jira.

## Basic Auth and TLS
- Use `curl --fail-with-body --silent --show-error --basic --user "$ES_USER" "$ES_URL/..."` (PowerShell: `curl.exe`).
- No client certificate or CA certificate file is required as a curl argument in this environment. **For HTTPS, leave normal server certificate verification enabled.** If curl reports a trust problem, fix the trust configuration; do not use `-k` or `--insecure`.
- An interactive password prompt is suitable for a human operator. Automation must use an approved secrets mechanism and privilege scoping.
- Curl command `--fail-with-body` requires a recent curl; older clients can use `--fail`. Save redacted failure details.

## Risk classification and stopping rules
| Operation | Minimum required safety review |
|---|---|
| Read-only inspection | Verify target, permitted scope, credentials, API load impact, no patient/secret data captured |
| Index/ILM settings, index creation | Mapping/settings contract, owner approval, data/app tests, capacity and rollback |
| Reindex, alias change, shard remediation | Double-storage headroom, source updates/catch-up, verified data parity, rollback after new writes |
| Index deletion / retention expiry | Data+Business retention policy, exact Index Owner authorization, exception and hold checks, restore feasibility |
| Snapshot restore | Compatible snapshot, isolated rename target, resource headroom, RPO/RTO, source/target version and recovered writes |
| Cluster resize / upgrade | Provider-specific supported procedure, quorum/failure-domain design, staged testing, rollback realism |
| Finance optimization | FinOps evaluation plus Data/Business and DBRE approvals, no reduction of durability without review |

## Promotion to production-approved
- All validation-matrix tests for the runbook passed, with executed command and redacted outputs attached to Jira.
- No unresolved Sev-1/Sev-2 correctness or data loss findings; gaps are fixed and retested.
- Version(s), deployment type, date, tested scenario, operator and independent reviewer are recorded.
- DBRE/SRE signs operational safety; Data Engineering and Business Owner sign retention/data changes, Index Owner signs deletion eligibility; Application Engineering accepts search impacts; FinOps reviews material cost impact.
- Manager/change authority approves any required high-risk production maintenance. Reviewers may sign off on runbooks independently of scheduling a particular change.
- Mark the individual runbook **Production validated for ES [exact version], deployment [type]**; retain a restricted scope if only one scenario was tested. Revalidate when ES version, provider, major topology, or API contract changes.

## Strictly excluded shortcuts
No wildcard production deletion, no force-allocating stale primary without separately approved data-loss procedure, no disk watermark bypass as capacity fix, no blind force merge during active writes, no cluster-wide cache clear as generic remedy, no unsupported downgrade, no alias reversal after destination-only writes without verified replay.

See [validation matrix](VALIDATION-MATRIX.md), [test record](templates/cluster-validation-record.md), and [Jira template](templates/jira-maintenance-template.md).
