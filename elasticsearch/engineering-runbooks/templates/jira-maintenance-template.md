# Jira template — Elasticsearch engineering maintenance/change

**Summary:** [Environment] [Cluster] [Specific operation] — [business outcome]  
**Request type:** Cluster health / Disk capacity / Shard remediation / New index or mapping / Reindex and alias cutover / Retention ILM / Index cleanup / Performance / Backup restore DR / Scaling / Upgrade / Shard allocation / Heap cache / Growth forecast / FinOps  
**Requestor & service owner:** [names/teams]  
**Business Owner / Data Engineering / Index Owner:** [who provides requirements and approves data scope]

## Required information

- Environment, cluster UUID/name, Elasticsearch version, affected index/alias names, data classification:
- Business impact, intended outcome and affected applications/pipelines:
- Current baseline and expected change (size, shards, latency, query/ingest rates, storage, cost):
- Maintenance window/time zone, customer impact, notification and escalation contacts:
- Risk and recovery/rollback plan, snapshot/replay/restore readiness:
- Planned exact execution steps and approved JSON payload file(s), peer reviewer:
- Preconditions, go/no-go, stop thresholds and monitor/incident commander:
- Data and Application validation plan and acceptance criteria:
- FinOps review/financial approval as applicable:
- Change Authority approval where required:

## Mandatory approval / closure evidence

- Business + Data approval for retention changes; Index Owner verified deletion scope; DBRE technical safety review; Application approval if search behavior affected; FinOps cost review where material.
- Timeline, commands executed (secrets redacted), task IDs, index/alias state before and after, dashboards, data reconciliation, outcomes, rollback actions and sign-off.
- Follow-up owner and date; attach final production validated runbook revision.

**Workflow:** Submit → Assess → Approve → Execute → Validate → Close. Emergency handling follows the company's approved emergency change policy.
