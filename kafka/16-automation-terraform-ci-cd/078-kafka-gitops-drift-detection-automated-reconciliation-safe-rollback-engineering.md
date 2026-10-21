# Chapter 078 — Kafka GitOps Drift Detection, Automated Reconciliation and Safe Rollback Engineering

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 16 — Automation, Terraform and CI/CD (3/5)  
**Primary platform:** Kubernetes, Strimzi Kafka in KRaft mode, Argo CD/Flux; Terraform-managed AWS/EKS/MSK alternatives  
**Prerequisites:** Chapters 001–077, Kubernetes server-side apply, GitOps and Kafka durability  
**Publication:** Published · **Live labs:** Pending · **Independent technical/security review:** Pending

> **Safety:** GitOps self-heal, prune and rollback can be destructive for KafkaTopic, KafkaNodePool, PVC, Secrets and broker configuration. Use read-only inventory and isolated client-workload changes by default. Do not delete CRs, alter KRaft controller quorum, force-reconcile production or remove PVCs without reviewed backups, approvals and recovery. Git rollback does **not** reverse Kafka data/offset/partition mutations.

## 1. Mission and learning outcomes

Design drift detection and controlled reconciliation for Kafka infrastructure, differentiating Git desired state, Terraform state, Kubernetes objects, Strimzi-generated resources and Kafka's own durable metadata. Build safe self-heal boundaries, alerting, incident break-glass and rollback procedures that preserve Kafka correctness.

After this chapter, readers can interpret Argo CD/Flux drift, avoid controller ownership conflicts, protect KafkaTopic/NodePool/PVC resources, design policy gates, and verify Kafka quorum, ISR and client event correctness after recovery.

## 2. Reconciliation and ownership model

```text
Git reviewed desired state
   |                     Terraform state / cloud APIs
   |                             |
Argo CD or Flux            AWS/EKS/MSK resources
   |
Strimzi Kafka / KafkaNodePool / KafkaTopic / KafkaUser CRs
   |
Strimzi Cluster/Topic/User Operators
   |
generated StatefulSets / Pods / PVCs / Secrets
   |
Kafka KRaft metadata + partitions + consumer offsets
   |
authenticated EKS producer/consumer event ledger
```

**Single owner principle:** Terraform may own EKS/MSK/cloud infrastructure; GitOps may own selected Strimzi CRs; Strimzi owns generated workloads. Kafka runtime metadata, offsets and stored records are not safely rolled back by Git.

## 3. Drift classification

| Drift class | Example | Default action |
|---|---|---|
| Expected controller fields | status, resourceVersion, generated labels | narrowly normalize |
| Reversible client drift | EKS Deployment replica count/image digest | reviewed Git reconciliation |
| Configuration drift | topic retention, client quota, KafkaUser ACL | review impact and authorization |
| Security drift | TLS disabled, listener exposure, wildcard ACL | block and escalate |
| Stateful infrastructure drift | KafkaNodePool replicas, PVC, storage | freeze and assess quorum/data |
| Irreversible Kafka drift | partition increase, topic deletion, offset changes | recovery plan, not Git revert |
| Ownership conflict | Terraform and GitOps modify same object | assign one owner before reconciliation |

A healthy GitOps Application is not proof that Kafka is healthy; check KRaft quorum, ISR/offline partitions, authenticated producer/consumer and event-ID reconciliation.

## 4. Read-only Kubernetes/Strimzi drift inventory

```bash
kubectl config current-context
kubectl get crd | grep kafka.strimzi.io
kubectl get kafka,kafkanodepool,kafkatopic,kafkauser -A
kubectl get pods,pvc -A -l strimzi.io/kind=Kafka
kubectl -n kafka get kafka -o yaml
kubectl -n kafka get kafkanodepool -o yaml
kubectl -n argocd get applications.argoproj.io
```

Adapt namespaces and CRDs to installed operator version. Resource YAML can contain sensitive endpoints, principals and configuration; redact before sharing. Avoid `kubectl apply` and manual editing of operator-generated Pods/PVCs.

## 5. Argo CD drift inspection

```bash
argocd app list
argocd app get kafka-platform
argocd app diff kafka-platform
argocd app history kafka-platform
```

These commands require a configured read-only Argo CD context. Review `OutOfSync`, `Degraded`, sync history and exact diff paths. Do not use global `ignoreDifferences` for TLS, ACLs, KafkaNodePool, topic retention or deletion; such rules can hide security drift. Selective ignore rules must be reviewed with Kubernetes managed-field semantics.

## 6. Flux drift inspection

```bash
flux get kustomizations -A
flux get helmreleases -A
flux logs --level=error
kubectl get kustomizations.kustomize.toolkit.fluxcd.io -A
```

Review `dependsOn`, health checks, prune settings, suspend state and controller reconciliation. Flux readiness describes declared-resource reconciliation, not Kafka data-plane correctness.

## 7. Terraform versus GitOps drift

Terraform plan detects differences between Terraform state/configuration and provider-observed infrastructure; Argo/Flux detects Git versus Kubernetes state; Strimzi continuously reconciles its CRs. Never configure multiple controllers to apply the same fields independently.

```bash
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
# For an approved, isolated environment with remote state:
# terraform plan -refresh-only  # read-only proposal; do not apply
```

A refresh-only plan can reveal drift but may expose sensitive attributes. Preserve a sanitized plan and do not update state without approval.

## 8. Guardrails for self-heal and prune

**Auto-reconcile candidates:** non-stateful EKS client Deployment labels/replicas where SLO-safe, selected ConfigMaps and alert definitions.

**Manual approval required:** Kafka/KafkaNodePool resource deletion, topic deletion/retention changes, PVC changes, listener/auth, KafkaUser ACLs, broker version upgrades, storage and Terraform replacements.

Implement admission/pipeline checks to reject destructive manifests, unsafe RF/minISR and unauthorized TLS/ACL changes. Protect Git branches and production environments with CODEOWNERS and security approval.

## 9. KRaft, ISR and Kafka correctness gates

Before and after any reconciliation:

1. Confirm Strimzi operator health and Kafka CR observed generation/conditions.
2. Confirm KRaft controller quorum is stable using the appropriate Kafka admin tool and credentials.
3. Check broker readiness, under-replicated/offline partitions, RF/minISR and disk headroom.
4. Validate authenticated EKS client producer acknowledgments and consumer freshness.
5. Reconcile unique synthetic event IDs; record duplicates/missing IDs.
6. Abort if quorum/ISR, authorization, latency, lag or correctness regresses.

Do not interpret Pod `Running` as a Kafka durability guarantee.

## 10. Emergency break-glass procedure

During a live incident, approved responders may temporarily suspend GitOps reconciliation to prevent unsafe reversion. Record who/why/when, Git SHA, impacted resources, exact temporary mutation, expiry and rollback. After stabilization, submit the corresponding reviewed Git change, verify drift, and resume reconciliation only after Kafka health and security gates pass.

Avoid long-lived drift or undocumented production changes.

## 11. Rollback decision matrix

| Change | Git revert sufficient? | Required validation |
|---|---|---|
| EKS client image/config | Often, if compatible | authenticated smoke, lag, event IDs |
| Alert rule | Usually | alarm routing and burn rate |
| KafkaUser ACL/TLS | Not necessarily | client auth, secret/cert lifecycle |
| KafkaTopic retention | Not for expired/deleted records | retention, data correctness |
| Partition count increase | No | metadata and ordering implications |
| KafkaNodePool/PVC | No generic revert | quorum, storage and backup |
| Kafka version upgrade | Often not safely downgradable | vendor compatibility/recovery |

## 12. Twenty Kubernetes-first drift and rollback labs

### Lab 01 — Map desired-state ownership

**Procedure:** Record Terraform, Argo CD/Flux, Strimzi, Kafka API and EKS application ownership.

**Expected evidence:** UTC timestamp, EKS context, Git SHA, Terraform/Argo/Flux/Strimzi version, exact resource owner, before/after diff, approved policy, Kafka quorum/ISR, synthetic event IDs, rollback/abort, owner and independent reviewer. Mark **Pending** until executed. KafkaTopic deletion, node-pool changes, PVC mutations and emergency production changes remain **Tabletop** without an approved isolated cluster.

### Lab 02 — Capture immutable Git baseline

**Procedure:** Record commit SHA, Kustomize overlay, Helm chart and environment release manifest.

**Expected evidence:** UTC timestamp, EKS context, Git SHA, Terraform/Argo/Flux/Strimzi version, exact resource owner, before/after diff, approved policy, Kafka quorum/ISR, synthetic event IDs, rollback/abort, owner and independent reviewer. Mark **Pending** until executed. KafkaTopic deletion, node-pool changes, PVC mutations and emergency production changes remain **Tabletop** without an approved isolated cluster.

### Lab 03 — Inventory Strimzi CRDs

**Procedure:** Check Kafka, KafkaNodePool, KafkaTopic, KafkaUser schemas and installed operator version.

**Expected evidence:** UTC timestamp, EKS context, Git SHA, Terraform/Argo/Flux/Strimzi version, exact resource owner, before/after diff, approved policy, Kafka quorum/ISR, synthetic event IDs, rollback/abort, owner and independent reviewer. Mark **Pending** until executed. KafkaTopic deletion, node-pool changes, PVC mutations and emergency production changes remain **Tabletop** without an approved isolated cluster.

### Lab 04 — Review Argo CD diff

**Procedure:** Inspect Application desired/live differences, ignored fields and sync history.

**Expected evidence:** UTC timestamp, EKS context, Git SHA, Terraform/Argo/Flux/Strimzi version, exact resource owner, before/after diff, approved policy, Kafka quorum/ISR, synthetic event IDs, rollback/abort, owner and independent reviewer. Mark **Pending** until executed. KafkaTopic deletion, node-pool changes, PVC mutations and emergency production changes remain **Tabletop** without an approved isolated cluster.

### Lab 05 — Review Flux drift

**Procedure:** Inspect Kustomization reconciliation, health, dependencies and prune controls.

**Expected evidence:** UTC timestamp, EKS context, Git SHA, Terraform/Argo/Flux/Strimzi version, exact resource owner, before/after diff, approved policy, Kafka quorum/ISR, synthetic event IDs, rollback/abort, owner and independent reviewer. Mark **Pending** until executed. KafkaTopic deletion, node-pool changes, PVC mutations and emergency production changes remain **Tabletop** without an approved isolated cluster.

### Lab 06 — Inspect Strimzi conditions

**Procedure:** Collect Kafka and KafkaNodePool status, observedGeneration and reconciliation errors.

**Expected evidence:** UTC timestamp, EKS context, Git SHA, Terraform/Argo/Flux/Strimzi version, exact resource owner, before/after diff, approved policy, Kafka quorum/ISR, synthetic event IDs, rollback/abort, owner and independent reviewer. Mark **Pending** until executed. KafkaTopic deletion, node-pool changes, PVC mutations and emergency production changes remain **Tabletop** without an approved isolated cluster.

### Lab 07 — Review operator-generated objects

**Procedure:** Identify Pods, StatefulSets, PVCs and Secrets that GitOps must not own.

**Expected evidence:** UTC timestamp, EKS context, Git SHA, Terraform/Argo/Flux/Strimzi version, exact resource owner, before/after diff, approved policy, Kafka quorum/ISR, synthetic event IDs, rollback/abort, owner and independent reviewer. Mark **Pending** until executed. KafkaTopic deletion, node-pool changes, PVC mutations and emergency production changes remain **Tabletop** without an approved isolated cluster.

### Lab 08 — Classify harmless drift

**Procedure:** Separate Kubernetes defaults, status, timestamps and operator-managed metadata.

**Expected evidence:** UTC timestamp, EKS context, Git SHA, Terraform/Argo/Flux/Strimzi version, exact resource owner, before/after diff, approved policy, Kafka quorum/ISR, synthetic event IDs, rollback/abort, owner and independent reviewer. Mark **Pending** until executed. KafkaTopic deletion, node-pool changes, PVC mutations and emergency production changes remain **Tabletop** without an approved isolated cluster.

### Lab 09 — Classify dangerous drift

**Procedure:** Identify auth/TLS, ACL, listeners, RF/minISR, PVC, KafkaTopic and node-pool changes.

**Expected evidence:** UTC timestamp, EKS context, Git SHA, Terraform/Argo/Flux/Strimzi version, exact resource owner, before/after diff, approved policy, Kafka quorum/ISR, synthetic event IDs, rollback/abort, owner and independent reviewer. Mark **Pending** until executed. KafkaTopic deletion, node-pool changes, PVC mutations and emergency production changes remain **Tabletop** without an approved isolated cluster.

### Lab 10 — Test selective ignore rules

**Procedure:** Ensure ignoreDifferences excludes only approved fields, not security or data safety.

**Expected evidence:** UTC timestamp, EKS context, Git SHA, Terraform/Argo/Flux/Strimzi version, exact resource owner, before/after diff, approved policy, Kafka quorum/ISR, synthetic event IDs, rollback/abort, owner and independent reviewer. Mark **Pending** until executed. KafkaTopic deletion, node-pool changes, PVC mutations and emergency production changes remain **Tabletop** without an approved isolated cluster.

### Lab 11 — Inspect Terraform drift

**Procedure:** Run approved plan-only refresh and compare cloud state with GitOps resources.

**Expected evidence:** UTC timestamp, EKS context, Git SHA, Terraform/Argo/Flux/Strimzi version, exact resource owner, before/after diff, approved policy, Kafka quorum/ISR, synthetic event IDs, rollback/abort, owner and independent reviewer. Mark **Pending** until executed. KafkaTopic deletion, node-pool changes, PVC mutations and emergency production changes remain **Tabletop** without an approved isolated cluster.

### Lab 12 — Validate drift alerting

**Procedure:** Define persistent drift, reconciliation failures, ownership conflict and on-call routes.

**Expected evidence:** UTC timestamp, EKS context, Git SHA, Terraform/Argo/Flux/Strimzi version, exact resource owner, before/after diff, approved policy, Kafka quorum/ISR, synthetic event IDs, rollback/abort, owner and independent reviewer. Mark **Pending** until executed. KafkaTopic deletion, node-pool changes, PVC mutations and emergency production changes remain **Tabletop** without an approved isolated cluster.

### Lab 13 — Test fail-closed policy

**Procedure:** Reject destructive prune, wildcard ACL, plaintext listener and unapproved storage change.

**Expected evidence:** UTC timestamp, EKS context, Git SHA, Terraform/Argo/Flux/Strimzi version, exact resource owner, before/after diff, approved policy, Kafka quorum/ISR, synthetic event IDs, rollback/abort, owner and independent reviewer. Mark **Pending** until executed. KafkaTopic deletion, node-pool changes, PVC mutations and emergency production changes remain **Tabletop** without an approved isolated cluster.

### Lab 14 — Rehearse safe reconciliation

**Procedure:** Use isolated namespace to restore a reversible ConfigMap or client Deployment.

**Expected evidence:** UTC timestamp, EKS context, Git SHA, Terraform/Argo/Flux/Strimzi version, exact resource owner, before/after diff, approved policy, Kafka quorum/ISR, synthetic event IDs, rollback/abort, owner and independent reviewer. Mark **Pending** until executed. KafkaTopic deletion, node-pool changes, PVC mutations and emergency production changes remain **Tabletop** without an approved isolated cluster.

### Lab 15 — Rehearse Git rollback

**Procedure:** Revert only reversible client config and verify rollout and Kafka event correctness.

**Expected evidence:** UTC timestamp, EKS context, Git SHA, Terraform/Argo/Flux/Strimzi version, exact resource owner, before/after diff, approved policy, Kafka quorum/ISR, synthetic event IDs, rollback/abort, owner and independent reviewer. Mark **Pending** until executed. KafkaTopic deletion, node-pool changes, PVC mutations and emergency production changes remain **Tabletop** without an approved isolated cluster.

### Lab 16 — Rehearse KafkaTopic deletion hazard

**Procedure:** Tabletop CR deletion/prune and preservation of Kafka data/retention policies.

**Expected evidence:** UTC timestamp, EKS context, Git SHA, Terraform/Argo/Flux/Strimzi version, exact resource owner, before/after diff, approved policy, Kafka quorum/ISR, synthetic event IDs, rollback/abort, owner and independent reviewer. Mark **Pending** until executed. KafkaTopic deletion, node-pool changes, PVC mutations and emergency production changes remain **Tabletop** without an approved isolated cluster.

### Lab 17 — Rehearse KafkaNodePool drift

**Procedure:** Tabletop node-pool resize, quorum/ISR and storage consequences.

**Expected evidence:** UTC timestamp, EKS context, Git SHA, Terraform/Argo/Flux/Strimzi version, exact resource owner, before/after diff, approved policy, Kafka quorum/ISR, synthetic event IDs, rollback/abort, owner and independent reviewer. Mark **Pending** until executed. KafkaTopic deletion, node-pool changes, PVC mutations and emergency production changes remain **Tabletop** without an approved isolated cluster.

### Lab 18 — Validate Kafka health gate

**Procedure:** Check KRaft quorum, ISR/offline partitions, producer acknowledgments and lag.

**Expected evidence:** UTC timestamp, EKS context, Git SHA, Terraform/Argo/Flux/Strimzi version, exact resource owner, before/after diff, approved policy, Kafka quorum/ISR, synthetic event IDs, rollback/abort, owner and independent reviewer. Mark **Pending** until executed. KafkaTopic deletion, node-pool changes, PVC mutations and emergency production changes remain **Tabletop** without an approved isolated cluster.

### Lab 19 — Exercise emergency break-glass

**Procedure:** Document time-bound suspend, audit, repair, PR reconciliation and resumption.

**Expected evidence:** UTC timestamp, EKS context, Git SHA, Terraform/Argo/Flux/Strimzi version, exact resource owner, before/after diff, approved policy, Kafka quorum/ISR, synthetic event IDs, rollback/abort, owner and independent reviewer. Mark **Pending** until executed. KafkaTopic deletion, node-pool changes, PVC mutations and emergency production changes remain **Tabletop** without an approved isolated cluster.

### Lab 20 — Independent drift acceptance

**Procedure:** Review evidence, policy negatives, recovery, SLO, owner and security signoff.

**Expected evidence:** UTC timestamp, EKS context, Git SHA, Terraform/Argo/Flux/Strimzi version, exact resource owner, before/after diff, approved policy, Kafka quorum/ISR, synthetic event IDs, rollback/abort, owner and independent reviewer. Mark **Pending** until executed. KafkaTopic deletion, node-pool changes, PVC mutations and emergency production changes remain **Tabletop** without an approved isolated cluster.

## 13. Read-only preflight script

Save as `verify-ch78.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
echo '[1/10] Git revision'; git rev-parse HEAD
echo '[2/10] Kubernetes context'; kubectl config current-context
echo '[3/10] Strimzi CRDs'; kubectl get crd | grep -E 'kafkas.kafka.strimzi.io|kafkanodepools.kafka.strimzi.io' || true
echo '[4/10] Kafka CRs'; kubectl get kafka -A
echo '[5/10] NodePools'; kubectl get kafkanodepool -A
echo '[6/10] Topics'; kubectl get kafkatopic -A
echo '[7/10] Users'; kubectl get kafkauser -A
echo '[8/10] Kafka Pods'; kubectl get pods -A -l strimzi.io/kind=Kafka
echo '[9/10] Kafka PVCs'; kubectl get pvc -A -l strimzi.io/kind=Kafka
echo '[10/10] GitOps CRs (optional)'; kubectl get applications.argoproj.io -A || true
echo 'PASS: read-only inventory only.'
echo 'NOT PROVEN: diff correctness, quorum, ISR, client SLO, rollback or security review.'
```

Commands may be unavailable for an MSK-only environment or a different Strimzi CRD version; mark those checks **Not Applicable** with rationale rather than claiming pass.

## 14. Twelve drift and rollback failure scenarios

### Scenario 1 — Argo CD and Strimzi repeatedly overwrite fields

**Diagnosis:** Inspect managedFields, ownership, ignoreDifferences and operator-generated objects. Correlate Git SHA, GitOps diff/sync history, Terraform plan, Kubernetes managedFields, Strimzi CR status, KRaft quorum, Kafka ISR/minISR and authenticated EKS client event IDs. **Response:** Freeze unsafe self-heal/prune, preserve Kafka data and audit evidence, resolve ownership and use approved recovery. **Exit:** Stable desired state, healthy Kafka client SLO, reconciled event IDs and reviewer.

### Scenario 2 — Flux reconciliation reports ready but brokers degraded

**Diagnosis:** Check Kafka CR status, KRaft quorum, ISR and client smoke independently. Correlate Git SHA, GitOps diff/sync history, Terraform plan, Kubernetes managedFields, Strimzi CR status, KRaft quorum, Kafka ISR/minISR and authenticated EKS client event IDs. **Response:** Freeze unsafe self-heal/prune, preserve Kafka data and audit evidence, resolve ownership and use approved recovery. **Exit:** Stable desired state, healthy Kafka client SLO, reconciled event IDs and reviewer.

### Scenario 3 — Terraform and GitOps both own a Kafka CR

**Diagnosis:** Assign single owner and migrate safely without destructive recreation. Correlate Git SHA, GitOps diff/sync history, Terraform plan, Kubernetes managedFields, Strimzi CR status, KRaft quorum, Kafka ISR/minISR and authenticated EKS client event IDs. **Response:** Freeze unsafe self-heal/prune, preserve Kafka data and audit evidence, resolve ownership and use approved recovery. **Exit:** Stable desired state, healthy Kafka client SLO, reconciled event IDs and reviewer.

### Scenario 4 — KafkaTopic disappears from Git

**Diagnosis:** Block prune, verify deletion policy and topic data preservation. Correlate Git SHA, GitOps diff/sync history, Terraform plan, Kubernetes managedFields, Strimzi CR status, KRaft quorum, Kafka ISR/minISR and authenticated EKS client event IDs. **Response:** Freeze unsafe self-heal/prune, preserve Kafka data and audit evidence, resolve ownership and use approved recovery. **Exit:** Stable desired state, healthy Kafka client SLO, reconciled event IDs and reviewer.

### Scenario 5 — KafkaNodePool drift requests broker deletion

**Diagnosis:** Freeze rollout; inspect quorum, RF/minISR, PVC and change approval. Correlate Git SHA, GitOps diff/sync history, Terraform plan, Kubernetes managedFields, Strimzi CR status, KRaft quorum, Kafka ISR/minISR and authenticated EKS client event IDs. **Response:** Freeze unsafe self-heal/prune, preserve Kafka data and audit evidence, resolve ownership and use approved recovery. **Exit:** Stable desired state, healthy Kafka client SLO, reconciled event IDs and reviewer.

### Scenario 6 — IgnoreDifferences hides TLS security drift

**Diagnosis:** Narrow ignored paths and audit listener/auth changes. Correlate Git SHA, GitOps diff/sync history, Terraform plan, Kubernetes managedFields, Strimzi CR status, KRaft quorum, Kafka ISR/minISR and authenticated EKS client event IDs. **Response:** Freeze unsafe self-heal/prune, preserve Kafka data and audit evidence, resolve ownership and use approved recovery. **Exit:** Stable desired state, healthy Kafka client SLO, reconciled event IDs and reviewer.

### Scenario 7 — Auto-sync reverts emergency incident fix

**Diagnosis:** Suspend safely, record break-glass change and reconcile Git before resuming. Correlate Git SHA, GitOps diff/sync history, Terraform plan, Kubernetes managedFields, Strimzi CR status, KRaft quorum, Kafka ISR/minISR and authenticated EKS client event IDs. **Response:** Freeze unsafe self-heal/prune, preserve Kafka data and audit evidence, resolve ownership and use approved recovery. **Exit:** Stable desired state, healthy Kafka client SLO, reconciled event IDs and reviewer.

### Scenario 8 — CRD schema upgrade rejects existing Kafka CR

**Diagnosis:** Pin compatibility, check conversion and stage operator rollout. Correlate Git SHA, GitOps diff/sync history, Terraform plan, Kubernetes managedFields, Strimzi CR status, KRaft quorum, Kafka ISR/minISR and authenticated EKS client event IDs. **Response:** Freeze unsafe self-heal/prune, preserve Kafka data and audit evidence, resolve ownership and use approved recovery. **Exit:** Stable desired state, healthy Kafka client SLO, reconciled event IDs and reviewer.

### Scenario 9 — PVC appears orphaned after node-pool change

**Diagnosis:** Do not delete; inspect retention, owner references and storage recovery. Correlate Git SHA, GitOps diff/sync history, Terraform plan, Kubernetes managedFields, Strimzi CR status, KRaft quorum, Kafka ISR/minISR and authenticated EKS client event IDs. **Response:** Freeze unsafe self-heal/prune, preserve Kafka data and audit evidence, resolve ownership and use approved recovery. **Exit:** Stable desired state, healthy Kafka client SLO, reconciled event IDs and reviewer.

### Scenario 10 — Git revert cannot undo partition increase

**Diagnosis:** Classify Kafka metadata change as irreversible; use recovery plan. Correlate Git SHA, GitOps diff/sync history, Terraform plan, Kubernetes managedFields, Strimzi CR status, KRaft quorum, Kafka ISR/minISR and authenticated EKS client event IDs. **Response:** Freeze unsafe self-heal/prune, preserve Kafka data and audit evidence, resolve ownership and use approved recovery. **Exit:** Stable desired state, healthy Kafka client SLO, reconciled event IDs and reviewer.

### Scenario 11 — Drift alert storms from status fields

**Diagnosis:** Tune diff normalization without suppressing security or readiness conditions. Correlate Git SHA, GitOps diff/sync history, Terraform plan, Kubernetes managedFields, Strimzi CR status, KRaft quorum, Kafka ISR/minISR and authenticated EKS client event IDs. **Response:** Freeze unsafe self-heal/prune, preserve Kafka data and audit evidence, resolve ownership and use approved recovery. **Exit:** Stable desired state, healthy Kafka client SLO, reconciled event IDs and reviewer.

### Scenario 12 — Reconciliation completes but clients lose events

**Diagnosis:** Trace producer ack, consumer offsets, ISR and synthetic event ledger. Correlate Git SHA, GitOps diff/sync history, Terraform plan, Kubernetes managedFields, Strimzi CR status, KRaft quorum, Kafka ISR/minISR and authenticated EKS client event IDs. **Response:** Freeze unsafe self-heal/prune, preserve Kafka data and audit evidence, resolve ownership and use approved recovery. **Exit:** Stable desired state, healthy Kafka client SLO, reconciled event IDs and reviewer.

## 15. Eight production runbooks

### Runbook A — GitOps drift incident

**Trigger/response:** Classify diff, identify owner, suspend destructive sync, validate Kafka and restore Git. **No-go:** unapproved prune/destroy, degraded quorum/ISR, unknown Kafka data loss, hidden TLS/ACL drift, unreviewed PVC deletion or unsafe Git rollback. **Exit:** Reconciled ownership, audited Git desired state, Kafka health, authenticated client correctness and independent signoff.

### Runbook B — Terraform versus GitOps ownership conflict

**Trigger/response:** Freeze both controllers, reconcile state, assign one owner and review migration. **No-go:** unapproved prune/destroy, degraded quorum/ISR, unknown Kafka data loss, hidden TLS/ACL drift, unreviewed PVC deletion or unsafe Git rollback. **Exit:** Reconciled ownership, audited Git desired state, Kafka health, authenticated client correctness and independent signoff.

### Runbook C — Strimzi reconciliation failure

**Trigger/response:** Inspect CR conditions, operator logs, schema and Kafka quorum/ISR. **No-go:** unapproved prune/destroy, degraded quorum/ISR, unknown Kafka data loss, hidden TLS/ACL drift, unreviewed PVC deletion or unsafe Git rollback. **Exit:** Reconciled ownership, audited Git desired state, Kafka health, authenticated client correctness and independent signoff.

### Runbook D — Unsafe KafkaTopic prune

**Trigger/response:** Block deletion, inspect policy/finalizers, preserve topic data and audit. **No-go:** unapproved prune/destroy, degraded quorum/ISR, unknown Kafka data loss, hidden TLS/ACL drift, unreviewed PVC deletion or unsafe Git rollback. **Exit:** Reconciled ownership, audited Git desired state, Kafka health, authenticated client correctness and independent signoff.

### Runbook E — KafkaNodePool or PVC drift

**Trigger/response:** Freeze changes, assess quorum, brokers, storage and data recovery. **No-go:** unapproved prune/destroy, degraded quorum/ISR, unknown Kafka data loss, hidden TLS/ACL drift, unreviewed PVC deletion or unsafe Git rollback. **Exit:** Reconciled ownership, audited Git desired state, Kafka health, authenticated client correctness and independent signoff.

### Runbook F — Emergency break-glass change

**Trigger/response:** Time-bound suspend, approval, audit, operational repair and Git reconciliation. **No-go:** unapproved prune/destroy, degraded quorum/ISR, unknown Kafka data loss, hidden TLS/ACL drift, unreviewed PVC deletion or unsafe Git rollback. **Exit:** Reconciled ownership, audited Git desired state, Kafka health, authenticated client correctness and independent signoff.

### Runbook G — Rollback after client regression

**Trigger/response:** Revert safe workload changes, verify TLS/auth, lag and event IDs. **No-go:** unapproved prune/destroy, degraded quorum/ISR, unknown Kafka data loss, hidden TLS/ACL drift, unreviewed PVC deletion or unsafe Git rollback. **Exit:** Reconciled ownership, audited Git desired state, Kafka health, authenticated client correctness and independent signoff.

### Runbook H — Independent drift recovery acceptance

**Trigger/response:** Verify signed evidence, SLO, policy coverage, ownership and reviewer. **No-go:** unapproved prune/destroy, degraded quorum/ISR, unknown Kafka data loss, hidden TLS/ACL drift, unreviewed PVC deletion or unsafe Git rollback. **Exit:** Reconciled ownership, audited Git desired state, Kafka health, authenticated client correctness and independent signoff.

## 16. Evidence bundle

```text
evidence-ch78/
  ownership-map.md
  git-baseline.md
  strimzi-crd-inventory.md
  argocd-diff-history.md
  flux-drift-health.md
  strimzi-conditions.md
  generated-resources.md
  expected-drift.md
  security-drift.md
  ignore-rules.md
  terraform-refresh-plan.md
  drift-alerts.md
  policy-negative-tests.md
  safe-reconciliation.md
  reversible-rollback.md
  topic-prune-tabletop.md
  nodepool-drift-tabletop.md
  kafka-health-smoke.csv
  break-glass-audit.md
  independent-acceptance.md
  scorecard.md
```

Every artifact needs UTC time, tool versions, Git revision, expected/observed result, **Live** vs **Tabletop**, sanitized output, owner, abort/rollback and independent reviewer.

## 17. 100-point drift and recovery assessment

| Domain | Points | Critical |
|---|---:|---|
| Ownership model and GitOps/Terraform drift detection | 20 | Yes |
| Stateful Kafka safety and prune prevention | 20 | Yes |
| Security drift and fail-closed policy | 15 | Yes |
| Reconciliation, break-glass and audit | 15 | Yes |
| Kafka quorum/ISR, SLO and event correctness | 20 | Yes |
| Independent technical/security review | 10 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with every critical gate independently evidenced. **Automatic Fail:** fabricated live tests, hidden security drift, destructive KafkaTopic/PVC prune, unreviewed node-pool change, lost ISR without abort, unexplained missing events or absent independent review.

## 18. References and next chapter

**References:** [Strimzi](https://strimzi.io/documentation/), [Argo CD Diffing](https://argo-cd.readthedocs.io/en/stable/user-guide/diffing/), [Flux](https://fluxcd.io/flux/), [Terraform](https://developer.hashicorp.com/terraform/docs), [Kubernetes Server-Side Apply](https://kubernetes.io/docs/reference/using-api/server-side-apply/), [Apache Kafka](https://kafka.apache.org/documentation/).

**Next:** Chapter 079 — Kafka Automation Observability, Release Reliability, Compliance Evidence and SRE Runbooks.

---

**Verification boundary:** Publication proves document availability only. Live drift tests, Argo/Flux reconciliation, rollback, Kafka smoke and independent technical/security review remain Pending.
