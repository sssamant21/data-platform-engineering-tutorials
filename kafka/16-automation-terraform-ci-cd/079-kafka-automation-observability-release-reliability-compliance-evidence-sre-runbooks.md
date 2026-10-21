# Chapter 079 — Kafka Automation Observability, Release Reliability, Compliance Evidence and SRE Runbooks

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 16 — Automation, Terraform and CI/CD (4/5)  
**Primary platform:** Kubernetes / Strimzi KRaft with Terraform, Argo CD/Flux and GitLab CI/CD; MSK integration where applicable  
**Prerequisites:** Chapters 001–078  
**Publication:** Published · **Live lab execution:** Pending · **Independent technical/security review:** Pending

> **Safety:** All examples are observation and review first. Never promote a production release, modify MSK/Kafka brokers, force GitOps reconciliation, expose pipeline secrets, remove compliance evidence or trigger failure injection without explicit approval. Release success is not equivalent to Kafka event correctness; preserve client acknowledgment and event-ID evidence.

## 1. Mission and learning objectives

Make Kafka automation observable and auditable. Correlate Git, CI/CD, Terraform, Argo/Flux, Strimzi, broker health and EKS client telemetry into release SLOs, actionable alerts, compliance evidence and incident runbooks. Ensure every production change can be reconstructed from immutable provenance and independently reviewed.

By completion, readers can define delivery SLIs, build deployment markers, detect unsafe changes and telemetry blind spots, measure recovery, reconstruct audit trails and enforce evidence-based promotion gates.

## 2. Release observability architecture

```text
Git commit + reviewed change ticket + approval
             |
GitLab CI / GitHub Actions stage metrics
             |
Terraform fmt / plan / policy / scan evidence
             |
Argo CD / Flux desired-state and drift events
             |
Strimzi CR conditions / reconciliation
             |
Kafka KRaft quorum / ISR / partitions / disk
             |
EKS producer and consumer telemetry
             |
synthetic event-ID reconciliation ledger
             |
Release SLO dashboard + alerts + on-call
             |
Audit evidence + RCA + independent signoff
```

A GitOps `Synced` or CI `Passed` status proves neither Kafka durability nor business processing success. Always include authenticated Kafka client smoke and event correctness.

## 3. Release event contract and cardinality

Capture UTC event time, Git SHA, pipeline ID, stage, environment, change ticket, actor/approver, tool versions, plan digest, policy result, deploy result, Kafka ISR and synthetic test reference. Keep sensitive ARNs, usernames, topic payloads and credentials out of public logs.

**Cardinality:** avoid per-Git-SHA and per-event-ID labels on long-lived Prometheus metrics; store high-cardinality identifiers in structured logs/traces or bounded event tables. Use low-cardinality labels such as environment, platform, pipeline stage and outcome.

Example structured event:

```json
{
  "timestamp_utc": "2026-10-21T00:00:00Z",
  "environment": "staging",
  "platform": "strimzi-kraft",
  "stage": "policy-validation",
  "outcome": "passed",
  "git_sha": "EXAMPLE_SHA",
  "pipeline_id": "EXAMPLE_PIPELINE_ID",
  "change_ticket": "EXAMPLE_CHANGE",
  "evidence_ref": "evidence/ch079/policy-result.json"
}
```

This is a schema example, not observed execution evidence.

## 4. Delivery SLIs and SLOs

| SLI | Definition | Caveat |
|---|---|---|
| Deployment frequency | successful production deployments per window | track real deployments, not pipeline starts |
| Change failure rate | production changes requiring rollback/incident / production changes | define attribution and denominator |
| Recovery time | incident declaration to restored Kafka client SLO | distinguish MTTR definitions |
| Pipeline success | required jobs passed / attempted valid runs | do not count skipped required gates |
| Policy compliance | releases satisfying required controls / attempted releases | missing evidence fails closed |
| Drift age | time unresolved significant drift remains | ignore only approved controller fields |
| Kafka availability | successful acknowledged synthetic produce / attempts | instrument application and Kafka errors |
| Consumer freshness | source event to downstream processing | account for clock skew |
| Data correctness | expected acknowledged IDs reconciled / expected IDs | duplicates and loss require separate counts |

Thresholds are environment-specific; do not invent production SLO targets. For example, a **proposed** change-failure-rate target must be approved and measured before being called achieved.

## 5. Pipeline and Terraform telemetry

Record job duration, runner queue time, retry count, policy scan status, toolchain versions, plan change actions, approval and deploy timing. Distinguish `skipped`, `manual`, `blocked` and `failed` states.

```bash
git rev-parse HEAD
terraform version
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
```

For approved backend access, store redacted plan summaries with SHA and provider lockfile hash. Raw plan JSON can contain sensitive values and must be access-controlled.

## 6. Argo CD/Flux and Strimzi observability

```bash
kubectl config current-context
kubectl get kafka,kafkanodepool -A
kubectl get pods -A -l strimzi.io/kind=Kafka
kubectl -n argocd get applications.argoproj.io
```

Track sync drift, reconciliation errors, observedGeneration, operator readiness and Kafka CR conditions. GitOps health does not replace Kafka quorum/ISR checks. Scope metric labels to avoid excessive Prometheus series.

## 7. Kafka broker and EKS client correlation

For each release marker, correlate KRaft controller quorum, under-replicated/offline partitions, broker CPU/network/disk, producer request errors/retries/acks, consumer lag/freshness and downstream processing.

Synthetic event ledger fields:

```text
run_id,event_id,git_sha,source_topic,partition,offset,ack_utc,
consumer_group,processed_utc,duplicate_count,status
```

A green release requires the expected acknowledged IDs to be observed and processed according to the application contract. Missing IDs must block promotion and trigger investigation.

## 8. Alerting and release gates

- Alert on sustained Kafka client SLO impact and ISR/offline partition risk, not only a failed CI job.
- Correlate alerts with deployment SHA and environment.
- Route Terraform destruction, secret exposure and security drift to dedicated responders.
- Require mandatory policy, scan, approval and smoke evidence before production promotion.
- Use scoped maintenance suppression without muting critical durability or security alerts.
- Test alert delivery in an approved isolated environment and record expected/observed routing.

## 9. Compliance control and evidence matrix

| Control | Evidence | Reviewer |
|---|---|---|
| Change authorization | ticket, PR approval, immutable SHA | change owner |
| Identity and least privilege | OIDC/IRSA role mapping, audit | security |
| Terraform safety | provider lockfile, plan summary, destroy gate | platform |
| GitOps safety | sync/diff, prune policy, owner map | platform |
| Kafka durability | quorum, RF/minISR, ISR/offline partitions | DBRE/SRE |
| Client correctness | synthetic ack/consume ledger, freshness | application owner |
| Supply-chain security | SBOM, vulnerability/secret scan, attestations | security |
| Incident readiness | on-call, alert delivery, runbooks, RTO/RPO | SRE |
| Independent acceptance | signed scorecard and exception register | independent reviewer |

Retain evidence according to approved organizational policy; avoid invented regulatory requirements. Encryption, access control, immutability where required and lifecycle cost must be reviewed.

## 10. Release failure, rollback and audit reconstruction

When a release fails, freeze further promotion, identify exact SHA and change scope, inspect Terraform/GitOps ownership, verify Kafka quorum/ISR and EKS client SLO, then revert **only reversible** workload changes. Kafka topic deletion, partition count increases, offset mutations and certain broker upgrades require a separate recovery plan.

An audit should reconstruct: who proposed, who approved, what plan/policy ran, what deployed, what Kafka clients observed, when rollback occurred, which data was affected and who signed off.

## 11. Twenty Kubernetes-first automation observability labs

### Lab 01 — Define release SLOs

**Procedure:** Set measurable pipeline success, change failure, recovery time, Kafka client and freshness objectives.

**Expected evidence:** UTC time, Git SHA, CI job/pipeline ID, pinned versions, EKS context, release event, SLO baseline, policy and security outcomes, Kafka ISR/quorum, synthetic event IDs, expected/observed result, owner, abort/rollback and independent reviewer. Mark **Pending** until executed. Alert firing, incident drills, production release and rollback remain **Tabletop** without approved isolated infrastructure.

### Lab 02 — Build release event schema

**Procedure:** Capture Git SHA, pipeline/job IDs, actor, environment, change ticket and UTC timestamps.

**Expected evidence:** UTC time, Git SHA, CI job/pipeline ID, pinned versions, EKS context, release event, SLO baseline, policy and security outcomes, Kafka ISR/quorum, synthetic event IDs, expected/observed result, owner, abort/rollback and independent reviewer. Mark **Pending** until executed. Alert firing, incident drills, production release and rollback remain **Tabletop** without approved isolated infrastructure.

### Lab 03 — Instrument CI pipeline

**Procedure:** Export stage duration, pass/fail, retries, queue time and deployment frequency.

**Expected evidence:** UTC time, Git SHA, CI job/pipeline ID, pinned versions, EKS context, release event, SLO baseline, policy and security outcomes, Kafka ISR/quorum, synthetic event IDs, expected/observed result, owner, abort/rollback and independent reviewer. Mark **Pending** until executed. Alert firing, incident drills, production release and rollback remain **Tabletop** without approved isolated infrastructure.

### Lab 04 — Instrument Terraform lifecycle

**Procedure:** Record fmt/validate/plan policy results, provider versions and destructive-action count.

**Expected evidence:** UTC time, Git SHA, CI job/pipeline ID, pinned versions, EKS context, release event, SLO baseline, policy and security outcomes, Kafka ISR/quorum, synthetic event IDs, expected/observed result, owner, abort/rollback and independent reviewer. Mark **Pending** until executed. Alert firing, incident drills, production release and rollback remain **Tabletop** without approved isolated infrastructure.

### Lab 05 — Instrument Argo CD/Flux

**Procedure:** Track sync, health, drift, reconcile errors, resource ownership and prune decisions.

**Expected evidence:** UTC time, Git SHA, CI job/pipeline ID, pinned versions, EKS context, release event, SLO baseline, policy and security outcomes, Kafka ISR/quorum, synthetic event IDs, expected/observed result, owner, abort/rollback and independent reviewer. Mark **Pending** until executed. Alert firing, incident drills, production release and rollback remain **Tabletop** without approved isolated infrastructure.

### Lab 06 — Instrument Strimzi operator

**Procedure:** Track reconciliation duration/errors, CR observed generation, Kafka/NodePool conditions.

**Expected evidence:** UTC time, Git SHA, CI job/pipeline ID, pinned versions, EKS context, release event, SLO baseline, policy and security outcomes, Kafka ISR/quorum, synthetic event IDs, expected/observed result, owner, abort/rollback and independent reviewer. Mark **Pending** until executed. Alert firing, incident drills, production release and rollback remain **Tabletop** without approved isolated infrastructure.

### Lab 07 — Correlate Kafka broker health

**Procedure:** Join KRaft quorum, ISR, offline partitions, CPU/disk and leader skew to release SHA.

**Expected evidence:** UTC time, Git SHA, CI job/pipeline ID, pinned versions, EKS context, release event, SLO baseline, policy and security outcomes, Kafka ISR/quorum, synthetic event IDs, expected/observed result, owner, abort/rollback and independent reviewer. Mark **Pending** until executed. Alert firing, incident drills, production release and rollback remain **Tabletop** without approved isolated infrastructure.

### Lab 08 — Correlate EKS client telemetry

**Procedure:** Join producer errors/latency, consumer lag/freshness, rebalances and Pod events.

**Expected evidence:** UTC time, Git SHA, CI job/pipeline ID, pinned versions, EKS context, release event, SLO baseline, policy and security outcomes, Kafka ISR/quorum, synthetic event IDs, expected/observed result, owner, abort/rollback and independent reviewer. Mark **Pending** until executed. Alert firing, incident drills, production release and rollback remain **Tabletop** without approved isolated infrastructure.

### Lab 09 — Build synthetic event ledger

**Procedure:** Capture acknowledged IDs, partition/offset, consumer processing and duplicate/missing events.

**Expected evidence:** UTC time, Git SHA, CI job/pipeline ID, pinned versions, EKS context, release event, SLO baseline, policy and security outcomes, Kafka ISR/quorum, synthetic event IDs, expected/observed result, owner, abort/rollback and independent reviewer. Mark **Pending** until executed. Alert firing, incident drills, production release and rollback remain **Tabletop** without approved isolated infrastructure.

### Lab 10 — Build deployment dashboard

**Procedure:** Show release markers, SLO burn, Kafka health, CI failure, drift and alert ownership.

**Expected evidence:** UTC time, Git SHA, CI job/pipeline ID, pinned versions, EKS context, release event, SLO baseline, policy and security outcomes, Kafka ISR/quorum, synthetic event IDs, expected/observed result, owner, abort/rollback and independent reviewer. Mark **Pending** until executed. Alert firing, incident drills, production release and rollback remain **Tabletop** without approved isolated infrastructure.

### Lab 11 — Define release alert thresholds

**Procedure:** Separate actionable Kafka SLO impact from noisy pipeline retries or expected reconciliation.

**Expected evidence:** UTC time, Git SHA, CI job/pipeline ID, pinned versions, EKS context, release event, SLO baseline, policy and security outcomes, Kafka ISR/quorum, synthetic event IDs, expected/observed result, owner, abort/rollback and independent reviewer. Mark **Pending** until executed. Alert firing, incident drills, production release and rollback remain **Tabletop** without approved isolated infrastructure.

### Lab 12 — Exercise alert delivery

**Procedure:** In isolated tests verify routing, deduplication, on-call and runbook deep links.

**Expected evidence:** UTC time, Git SHA, CI job/pipeline ID, pinned versions, EKS context, release event, SLO baseline, policy and security outcomes, Kafka ISR/quorum, synthetic event IDs, expected/observed result, owner, abort/rollback and independent reviewer. Mark **Pending** until executed. Alert firing, incident drills, production release and rollback remain **Tabletop** without approved isolated infrastructure.

### Lab 13 — Build compliance control matrix

**Procedure:** Map access, change approval, secret scan, policy, retention and recovery evidence.

**Expected evidence:** UTC time, Git SHA, CI job/pipeline ID, pinned versions, EKS context, release event, SLO baseline, policy and security outcomes, Kafka ISR/quorum, synthetic event IDs, expected/observed result, owner, abort/rollback and independent reviewer. Mark **Pending** until executed. Alert firing, incident drills, production release and rollback remain **Tabletop** without approved isolated infrastructure.

### Lab 14 — Validate artifact provenance

**Procedure:** Pin runner image, SBOM, signed Git SHA, OIDC role, tool versions and CI artifacts.

**Expected evidence:** UTC time, Git SHA, CI job/pipeline ID, pinned versions, EKS context, release event, SLO baseline, policy and security outcomes, Kafka ISR/quorum, synthetic event IDs, expected/observed result, owner, abort/rollback and independent reviewer. Mark **Pending** until executed. Alert firing, incident drills, production release and rollback remain **Tabletop** without approved isolated infrastructure.

### Lab 15 — Protect evidence and PII

**Procedure:** Review log redaction, retention, encryption, access, tamper resistance and cost.

**Expected evidence:** UTC time, Git SHA, CI job/pipeline ID, pinned versions, EKS context, release event, SLO baseline, policy and security outcomes, Kafka ISR/quorum, synthetic event IDs, expected/observed result, owner, abort/rollback and independent reviewer. Mark **Pending** until executed. Alert firing, incident drills, production release and rollback remain **Tabletop** without approved isolated infrastructure.

### Lab 16 — Validate negative security evidence

**Procedure:** Capture denied unsafe Terraform, TLS/ACL, secret exposure and GitOps prune fixtures.

**Expected evidence:** UTC time, Git SHA, CI job/pipeline ID, pinned versions, EKS context, release event, SLO baseline, policy and security outcomes, Kafka ISR/quorum, synthetic event IDs, expected/observed result, owner, abort/rollback and independent reviewer. Mark **Pending** until executed. Alert firing, incident drills, production release and rollback remain **Tabletop** without approved isolated infrastructure.

### Lab 17 — Rehearse release SLO regression

**Procedure:** Tabletop failed canary, Kafka ISR/lag regression, abort and communications.

**Expected evidence:** UTC time, Git SHA, CI job/pipeline ID, pinned versions, EKS context, release event, SLO baseline, policy and security outcomes, Kafka ISR/quorum, synthetic event IDs, expected/observed result, owner, abort/rollback and independent reviewer. Mark **Pending** until executed. Alert firing, incident drills, production release and rollback remain **Tabletop** without approved isolated infrastructure.

### Lab 18 — Rehearse audit reconstruction

**Procedure:** Rebuild who approved what, exact commit, plan, deployment, smoke and rollback timeline.

**Expected evidence:** UTC time, Git SHA, CI job/pipeline ID, pinned versions, EKS context, release event, SLO baseline, policy and security outcomes, Kafka ISR/quorum, synthetic event IDs, expected/observed result, owner, abort/rollback and independent reviewer. Mark **Pending** until executed. Alert firing, incident drills, production release and rollback remain **Tabletop** without approved isolated infrastructure.

### Lab 19 — Rehearse incident RCA

**Procedure:** Document detection, blast radius, mitigation, contributing causes and corrective action.

**Expected evidence:** UTC time, Git SHA, CI job/pipeline ID, pinned versions, EKS context, release event, SLO baseline, policy and security outcomes, Kafka ISR/quorum, synthetic event IDs, expected/observed result, owner, abort/rollback and independent reviewer. Mark **Pending** until executed. Alert firing, incident drills, production release and rollback remain **Tabletop** without approved isolated infrastructure.

### Lab 20 — Independent release-readiness acceptance

**Procedure:** Score evidence completeness, live vs tabletop boundaries, reviewers and outstanding risk.

**Expected evidence:** UTC time, Git SHA, CI job/pipeline ID, pinned versions, EKS context, release event, SLO baseline, policy and security outcomes, Kafka ISR/quorum, synthetic event IDs, expected/observed result, owner, abort/rollback and independent reviewer. Mark **Pending** until executed. Alert firing, incident drills, production release and rollback remain **Tabletop** without approved isolated infrastructure.

## 12. Read-only evidence preflight

Save as `verify-ch79.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
echo '[1/9] Git revision'; git rev-parse HEAD
echo '[2/9] Kubernetes context'; kubectl config current-context
echo '[3/9] Kafka CRs'; kubectl get kafka -A
echo '[4/9] KafkaNodePools'; kubectl get kafkanodepool -A
echo '[5/9] Kafka Pods'; kubectl get pods -A -l strimzi.io/kind=Kafka
echo '[6/9] Argo CD applications (optional)'; kubectl -n argocd get applications.argoproj.io || true
echo '[7/9] Terraform version (optional)'; terraform version || true
echo '[8/9] Flux Kustomizations (optional)'; kubectl get kustomizations.kustomize.toolkit.fluxcd.io -A || true
echo '[9/9] EKS client Pods'; kubectl -n "${EKS_NS:-kafka-clients}" get pods -o wide
echo 'PASS: read-only inventory only.'
echo 'NOT PROVEN: CI telemetry, SLO, policy execution, event correctness or independent review.'
```

This script is Strimzi-oriented; mark irrelevant checks **Not Applicable** for MSK-only clusters. A zero exit code does not certify release reliability or compliance.

## 13. Twelve release observability failure scenarios

### Scenario 1 — CI jobs succeed but Kafka client SLO fails

**Diagnosis:** Check release marker, producer ack, consumer freshness, ISR and event ledger. Correlate immutable Git SHA, pipeline telemetry, Terraform plan/policy, GitOps sync, Strimzi CR conditions, Kafka ISR/quorum, EKS client SLO and event-ID ledger. **Response:** Freeze unsafe promotion, contain security exposure, preserve sanitized audit trail and apply reviewed recovery. **Exit:** Corrected release gate, measured or explicitly tabletop SLO recovery, RCA and independent reviewer.

### Scenario 2 — Release dashboard misses a deployment

**Diagnosis:** Check pipeline event emission, labels, timestamps and ingestion errors. Correlate immutable Git SHA, pipeline telemetry, Terraform plan/policy, GitOps sync, Strimzi CR conditions, Kafka ISR/quorum, EKS client SLO and event-ID ledger. **Response:** Freeze unsafe promotion, contain security exposure, preserve sanitized audit trail and apply reviewed recovery. **Exit:** Corrected release gate, measured or explicitly tabletop SLO recovery, RCA and independent reviewer.

### Scenario 3 — High-cardinality metrics overload monitoring

**Diagnosis:** Bound Git SHA labels, move unique IDs to logs/traces and enforce retention. Correlate immutable Git SHA, pipeline telemetry, Terraform plan/policy, GitOps sync, Strimzi CR conditions, Kafka ISR/quorum, EKS client SLO and event-ID ledger. **Response:** Freeze unsafe promotion, contain security exposure, preserve sanitized audit trail and apply reviewed recovery. **Exit:** Corrected release gate, measured or explicitly tabletop SLO recovery, RCA and independent reviewer.

### Scenario 4 — Terraform policy result absent

**Diagnosis:** Fail closed; inspect CI dependencies, plan provenance and mandatory jobs. Correlate immutable Git SHA, pipeline telemetry, Terraform plan/policy, GitOps sync, Strimzi CR conditions, Kafka ISR/quorum, EKS client SLO and event-ID ledger. **Response:** Freeze unsafe promotion, contain security exposure, preserve sanitized audit trail and apply reviewed recovery. **Exit:** Corrected release gate, measured or explicitly tabletop SLO recovery, RCA and independent reviewer.

### Scenario 5 — GitOps shows synced while Strimzi degraded

**Diagnosis:** Inspect Kafka CR conditions, operator reconcile errors, quorum and ISR. Correlate immutable Git SHA, pipeline telemetry, Terraform plan/policy, GitOps sync, Strimzi CR conditions, Kafka ISR/quorum, EKS client SLO and event-ID ledger. **Response:** Freeze unsafe promotion, contain security exposure, preserve sanitized audit trail and apply reviewed recovery. **Exit:** Corrected release gate, measured or explicitly tabletop SLO recovery, RCA and independent reviewer.

### Scenario 6 — Secret appears in pipeline logs

**Diagnosis:** Contain artifact access, revoke/rotate, redact and security escalation. Correlate immutable Git SHA, pipeline telemetry, Terraform plan/policy, GitOps sync, Strimzi CR conditions, Kafka ISR/quorum, EKS client SLO and event-ID ledger. **Response:** Freeze unsafe promotion, contain security exposure, preserve sanitized audit trail and apply reviewed recovery. **Exit:** Corrected release gate, measured or explicitly tabletop SLO recovery, RCA and independent reviewer.

### Scenario 7 — Compliance audit cannot reconstruct approval

**Diagnosis:** Check immutable commit, approver, environment protection and ticket linkage. Correlate immutable Git SHA, pipeline telemetry, Terraform plan/policy, GitOps sync, Strimzi CR conditions, Kafka ISR/quorum, EKS client SLO and event-ID ledger. **Response:** Freeze unsafe promotion, contain security exposure, preserve sanitized audit trail and apply reviewed recovery. **Exit:** Corrected release gate, measured or explicitly tabletop SLO recovery, RCA and independent reviewer.

### Scenario 8 — Alerts flood during expected reconciliation

**Diagnosis:** Use scoped suppression, correlation and duration while retaining critical ISR alerts. Correlate immutable Git SHA, pipeline telemetry, Terraform plan/policy, GitOps sync, Strimzi CR conditions, Kafka ISR/quorum, EKS client SLO and event-ID ledger. **Response:** Freeze unsafe promotion, contain security exposure, preserve sanitized audit trail and apply reviewed recovery. **Exit:** Corrected release gate, measured or explicitly tabletop SLO recovery, RCA and independent reviewer.

### Scenario 9 — Change failure rate appears artificially low

**Diagnosis:** Audit denominator, rolled-back changes, incident tagging and missing events. Correlate immutable Git SHA, pipeline telemetry, Terraform plan/policy, GitOps sync, Strimzi CR conditions, Kafka ISR/quorum, EKS client SLO and event-ID ledger. **Response:** Freeze unsafe promotion, contain security exposure, preserve sanitized audit trail and apply reviewed recovery. **Exit:** Corrected release gate, measured or explicitly tabletop SLO recovery, RCA and independent reviewer.

### Scenario 10 — Evidence retention expires before audit

**Diagnosis:** Review storage lifecycle, legal retention, backup and immutable copies. Correlate immutable Git SHA, pipeline telemetry, Terraform plan/policy, GitOps sync, Strimzi CR conditions, Kafka ISR/quorum, EKS client SLO and event-ID ledger. **Response:** Freeze unsafe promotion, contain security exposure, preserve sanitized audit trail and apply reviewed recovery. **Exit:** Corrected release gate, measured or explicitly tabletop SLO recovery, RCA and independent reviewer.

### Scenario 11 — Rollback marker exists but event IDs missing

**Diagnosis:** Treat as data correctness incident; verify offsets, ack and replay. Correlate immutable Git SHA, pipeline telemetry, Terraform plan/policy, GitOps sync, Strimzi CR conditions, Kafka ISR/quorum, EKS client SLO and event-ID ledger. **Response:** Freeze unsafe promotion, contain security exposure, preserve sanitized audit trail and apply reviewed recovery. **Exit:** Corrected release gate, measured or explicitly tabletop SLO recovery, RCA and independent reviewer.

### Scenario 12 — Independent review absent at release gate

**Diagnosis:** Block promotion and assign accountable security/platform approvers. Correlate immutable Git SHA, pipeline telemetry, Terraform plan/policy, GitOps sync, Strimzi CR conditions, Kafka ISR/quorum, EKS client SLO and event-ID ledger. **Response:** Freeze unsafe promotion, contain security exposure, preserve sanitized audit trail and apply reviewed recovery. **Exit:** Corrected release gate, measured or explicitly tabletop SLO recovery, RCA and independent reviewer.

## 14. Eight production runbooks

### Runbook A — Release SLO breach

**Trigger/response:** Stop promotion, inspect change SHA, Kafka ISR, EKS client SLO and event correctness. **No-go:** missing approval/policy evidence, credential exposure, unreviewed destroy/prune, lost ISR, unexplained missing events or unreviewed rollback. **Exit:** Healthy Kafka, authenticated client correctness, complete audit trail and independent signoff.

### Runbook B — Pipeline/observability blind spot

**Trigger/response:** Inspect telemetry ingestion, pipeline event schema, dashboards and alert routing. **No-go:** missing approval/policy evidence, credential exposure, unreviewed destroy/prune, lost ISR, unexplained missing events or unreviewed rollback. **Exit:** Healthy Kafka, authenticated client correctness, complete audit trail and independent signoff.

### Runbook C — Terraform/GitOps compliance gate failure

**Trigger/response:** Reproduce policy fixture, freeze unsafe changes and preserve sanitized evidence. **No-go:** missing approval/policy evidence, credential exposure, unreviewed destroy/prune, lost ISR, unexplained missing events or unreviewed rollback. **Exit:** Healthy Kafka, authenticated client correctness, complete audit trail and independent signoff.

### Runbook D — Strimzi reconciliation regression

**Trigger/response:** Review CR conditions, operator logs, quorum, ISR and safe rollback. **No-go:** missing approval/policy evidence, credential exposure, unreviewed destroy/prune, lost ISR, unexplained missing events or unreviewed rollback. **Exit:** Healthy Kafka, authenticated client correctness, complete audit trail and independent signoff.

### Runbook E — CI secret or artifact compromise

**Trigger/response:** Restrict access, revoke credentials, rotate and notify security. **No-go:** missing approval/policy evidence, credential exposure, unreviewed destroy/prune, lost ISR, unexplained missing events or unreviewed rollback. **Exit:** Healthy Kafka, authenticated client correctness, complete audit trail and independent signoff.

### Runbook F — Audit evidence reconstruction

**Trigger/response:** Collect immutable SHA, approvals, plan, policy, deployment, smoke and RCA. **No-go:** missing approval/policy evidence, credential exposure, unreviewed destroy/prune, lost ISR, unexplained missing events or unreviewed rollback. **Exit:** Healthy Kafka, authenticated client correctness, complete audit trail and independent signoff.

### Runbook G — Kafka release incident and recovery

**Trigger/response:** Establish timeline, protect data, revert reversible changes and validate event ledger. **No-go:** missing approval/policy evidence, credential exposure, unreviewed destroy/prune, lost ISR, unexplained missing events or unreviewed rollback. **Exit:** Healthy Kafka, authenticated client correctness, complete audit trail and independent signoff.

### Runbook H — Independent SRE/compliance acceptance

**Trigger/response:** Check controls, SLO, signed evidence, pending risks and reviewer approval. **No-go:** missing approval/policy evidence, credential exposure, unreviewed destroy/prune, lost ISR, unexplained missing events or unreviewed rollback. **Exit:** Healthy Kafka, authenticated client correctness, complete audit trail and independent signoff.

## 15. Evidence bundle

```text
evidence-ch79/
  release-slos.md
  event-schema.json
  pipeline-metrics.md
  terraform-plan-policy.md
  gitops-drift-metrics.md
  strimzi-reconciliation.md
  kafka-broker-correlation.md
  eks-client-correlation.md
  synthetic-event-ledger.csv
  release-dashboard.md
  alert-routing.md
  alert-delivery-test.md
  compliance-control-matrix.md
  supply-chain-provenance.md
  evidence-retention-security.md
  negative-policy-evidence.md
  release-slo-regression-tabletop.md
  audit-reconstruction.md
  incident-rca.md
  independent-acceptance.md
  scorecard.md
```

Every artifact needs UTC timestamp, immutable Git revision, exact tool versions, expected/observed result, **Live** vs **Tabletop**, sanitized output, owner, risk/rollback and independent reviewer.

## 16. 100-point release reliability and compliance assessment

| Domain | Points | Critical |
|---|---:|---|
| Pipeline, Terraform and GitOps telemetry | 20 | Yes |
| Kafka broker/client SLO and event correctness | 20 | Yes |
| Alerting, incident correlation and runbooks | 15 | Yes |
| Change provenance and compliance controls | 20 | Yes |
| Security evidence, retention and negative tests | 15 | Yes |
| Independent technical/security review | 10 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with every critical gate independently evidenced. **Automatic Fail:** fabricated live evidence, missing approvals, exposed secrets, bypassed mandatory security gate, unexplained Kafka data loss or absent independent review.

## 17. References and next chapter

**References:** [GitLab CI/CD](https://docs.gitlab.com/ci/), [Argo CD](https://argo-cd.readthedocs.io/), [Flux](https://fluxcd.io/flux/), [Strimzi](https://strimzi.io/documentation/), [Prometheus](https://prometheus.io/docs/), [Terraform](https://developer.hashicorp.com/terraform/docs), [Apache Kafka](https://kafka.apache.org/documentation/).

**Next:** Chapter 080 — Kafka Enterprise Automation, GitOps, CI/CD and Reliability Acceptance Capstone.

---

**Verification boundary:** Publication proves document availability only. Live CI/observability metrics, alert delivery, Kafka client SLO, compliance reconstruction and independent technical/security review remain Pending.
