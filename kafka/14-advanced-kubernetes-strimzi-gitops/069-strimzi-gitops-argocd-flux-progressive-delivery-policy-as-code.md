# Chapter 069 — Strimzi GitOps, Argo CD/Flux, Progressive Delivery and Policy-as-Code

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 14 — Advanced Kubernetes, Strimzi and GitOps (4/5)  
**Primary platform:** Kubernetes + Strimzi Operator + Kafka KRaft  
**Prerequisites:** Chapters 001–068, especially 066–068  
**Status:** Published · **Live labs:** Pending · **Independent technical/security review:** Pending

> **Safety:** Use approved disposable namespaces and synthetic Kafka topics. Do not enable automated pruning, self-healing, Kafka upgrades, broker restarts, CRD replacement, listener exposure, PVC deletion or secret rotation against production without explicit change approval. Git revert does not undo irreversible Kafka metadata, partition or storage changes.

## 1. Mission and learning objectives

Design and operate GitOps delivery for Strimzi-managed Kafka with Argo CD or Flux. Establish ownership boundaries, declarative configuration, release-specific CRD validation, progressive environment promotion, policy-as-code, observability, drift detection, change approval and safe rollback.

At completion, the reader can implement a reviewable Kafka GitOps repository, reason about Strimzi reconciliation, prevent dangerous pruning, validate policy gates and produce independent evidence for a controlled production release.

## 2. Architecture and ownership

```text
 Pull request -> CI schema/security/policy tests -> approved Git revision
                                   |
                           Argo CD / Flux
                                   |
                         Strimzi custom resources
                 Kafka / KafkaNodePool / KafkaTopic / KafkaUser
                                   |
                           Strimzi Operators
                                   |
              brokers, controllers, PVCs, Services, Secrets
                                   |
                       Kafka health and client SLOs
                                   |
                    monitoring + audit + change evidence
```

**Ownership contract:** GitOps manages reviewed Strimzi CRs and related user-owned policies. Strimzi manages its generated resources. Do not directly Git-manage operator-generated Kafka workloads or overwrite generated Secrets. Record field ownership and operator status before enabling automated sync.

## 3. Repository layout

```text
kafka-gitops/
  operator/
    release-lock.yaml
    crds/
    install/
  base/
    kafka/
    nodepools/
    topics/
    users/
    networkpolicies/
    monitoring/
  overlays/
    lab/
    staging/
    production/
  argocd/
    applications/
  flux/
    sources/
    kustomizations/
  policies/
    gatekeeper/
    kyverno/
    conftest/
  tests/
    schema/
    security/
    smoke/
  evidence/
    release-template.md
```

Pin exact Kafka/Strimzi/Kubernetes/GitOps versions, source revisions, image digests and CRD schemas. Choose Argo CD **or** Flux as the owner of a given resource set; avoid dual reconciliation of the same objects.

## 4. Sync ordering and readiness

A safe logical dependency sequence:

1. Validate release matrix and Kubernetes capacity.
2. Install/upgrade Strimzi CRDs and Operator with approved migration plan.
3. Wait for operator readiness and verify watched namespaces.
4. Reconcile Kafka/KafkaNodePool CRs.
5. Verify KRaft controller quorum, broker readiness, ISR/minISR and PVCs.
6. Reconcile KafkaTopic/KafkaUser and supporting security controls.
7. Run authenticated client smoke, dashboards and acceptance checks.
8. Promote the exact reviewed revision to the next environment.

Argo CD sync waves and Flux `dependsOn` express ordering but **do not automatically prove Kafka durability**. Add explicit external acceptance gates before production promotion.

## 5. Argo CD reference Application

Illustrative manifest only; validate controller version, project RBAC and path:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: kafka-platform-lab
  namespace: argocd
spec:
  project: kafka-platform
  source:
    repoURL: https://github.com/EXAMPLE/kafka-gitops.git
    targetRevision: PINNED_REVIEWED_COMMIT
    path: overlays/lab
  destination:
    server: https://kubernetes.default.svc
    namespace: kafka-lab
  syncPolicy:
    syncOptions:
      - CreateNamespace=false
      - PruneLast=true
```

No automated sync or prune is enabled here. For production, define AppProject namespace/repo restrictions, manual approval, resource allowlists, deletion protection, safe health checks and release rollback. `PruneLast` changes ordering; it does **not** make deletion safe.

## 6. Flux reference Kustomization

```yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: kafka-lab
  namespace: flux-system
spec:
  interval: 10m
  sourceRef:
    kind: GitRepository
    name: kafka-platform
  path: ./overlays/lab
  prune: false
  wait: true
  timeout: 10m
```

This example presumes a separately approved `GitRepository` object. A production design must define `dependsOn`, explicit health checks, RBAC and admission controls. `prune: false` avoids automatic deletion but does not replace lifecycle ownership.

## 7. Policy-as-code: required controls

| Policy | Deny or review condition | Evidence |
|---|---|---|
| Kafka version | unsupported Kafka/Strimzi pairing | signed compatibility matrix |
| KafkaNodePool quorum | unsafe controller voter count/change | quorum review |
| Kafka listener | plaintext or unapproved external exposure | listener inventory |
| KafkaUser ACL | wildcard admin/cross-tenant scope | ACL matrix |
| Storage | deleteClaim, shrink, PVC deletion risk | storage change plan |
| Resource limits | missing capacity/ephemeral/disk budget | sizing worksheet |
| Placement | missing fault-domain spread | zone/rack review |
| Git provenance | unsigned/unreviewed source revision | PR and artifact attestation |
| Secrets | plaintext credential in manifests | secret scanning |
| Change safety | no rollback, RTO or abort criteria | release charter |

Kyverno, Gatekeeper and OPA/Conftest can enforce different subsets of these controls; some checks require external Kafka metrics and **cannot** be proven from YAML alone.

## 8. CI validation pipeline sketch

```bash
set -euo pipefail
git diff --check
git status --short
kubectl config current-context
kubectl api-resources | grep -E 'kafka|Kafka'
# Render overlays with the pinned toolchain, then validate against installed CRDs:
kubectl apply --dry-run=server -f rendered-lab.yaml
# Run approved policy and secret scans using pinned CI tool versions.
# Publish a redacted diff and require review before any sync.
```

`rendered-lab.yaml` is an output from the repository's rendering process, not a bundled file. Server-side dry-run validates Kubernetes admission/schema but cannot verify Kafka controller quorum, ISR, client authentication or application SLOs.

## 9. Progressive delivery for stateful Kafka

Kafka is not a stateless Deployment. Promotion must distinguish:

- **Manifest-only reversible changes:** labels or monitoring settings, where operator behavior is understood.
- **Rolling changes:** broker resources, listeners, Kafka configuration and operator versions; gate on ISR, quorum and latency.
- **Potentially irreversible changes:** Kafka metadata/storage upgrades, partition count, data retention effects and some PVC operations.
- **Credential/ACL changes:** require staged trust and explicit client compatibility.
- **Topic/user lifecycle:** protect data ownership and retention; do not let automatic pruning delete production resources.

Promote from lab to staging to production only with measured canary/synthetic client checks and owner approval. Do not use generic traffic-splitting canary language to imply Kafka broker changes are automatically safe.

## 10. Drift, health and rollback

GitOps status `Healthy` means the controller's resource health checks passed; it does not mean Kafka clients can produce/consume or that KRaft quorum is healthy. Cross-check Strimzi Kafka conditions, broker ISR, disk and authenticated smoke.

Rollback sequence: freeze unsafe sync; identify the last approved Git revision; inspect Kafka's actual state; decide if configuration revert is supported; restore or recover with a reviewed procedure; verify durability and client SLO; close with RCA.

## 11. Twenty Kubernetes-first GitOps labs

### Lab 01 — Approve GitOps operating charter

**Procedure:** Define platform ownership, source-of-truth, change approvals, RTO, rollback and policy exceptions.

**Evidence and pass criteria:** Capture Git commit, exact Strimzi/Kafka/Kubernetes/Argo-or-Flux versions, UTC command, rendered desired state, installed CRD validation, policy result, operator reconciliation, quorum/ISR, security, rollback/abort and reviewer. Mark **Pending** until executed. Prune, drift injection, rolling restart and upgrade drills are tabletop without approved disposable infrastructure.

### Lab 02 — Inventory Strimzi and GitOps versions

**Procedure:** Capture Kafka/Strimzi/Kubernetes, Argo CD or Flux, CRDs and Git revision.

**Evidence and pass criteria:** Capture Git commit, exact Strimzi/Kafka/Kubernetes/Argo-or-Flux versions, UTC command, rendered desired state, installed CRD validation, policy result, operator reconciliation, quorum/ISR, security, rollback/abort and reviewer. Mark **Pending** until executed. Prune, drift injection, rolling restart and upgrade drills are tabletop without approved disposable infrastructure.

### Lab 03 — Map resource ownership

**Procedure:** Distinguish Git-owned Kafka/NodePool/Topic/User CRs from operator-managed workloads and Secrets.

**Evidence and pass criteria:** Capture Git commit, exact Strimzi/Kafka/Kubernetes/Argo-or-Flux versions, UTC command, rendered desired state, installed CRD validation, policy result, operator reconciliation, quorum/ISR, security, rollback/abort and reviewer. Mark **Pending** until executed. Prune, drift injection, rolling restart and upgrade drills are tabletop without approved disposable infrastructure.

### Lab 04 — Design repo hierarchy

**Procedure:** Create operator, base, environment overlays, policy and evidence structure.

**Evidence and pass criteria:** Capture Git commit, exact Strimzi/Kafka/Kubernetes/Argo-or-Flux versions, UTC command, rendered desired state, installed CRD validation, policy result, operator reconciliation, quorum/ISR, security, rollback/abort and reviewer. Mark **Pending** until executed. Prune, drift injection, rolling restart and upgrade drills are tabletop without approved disposable infrastructure.

### Lab 05 — Pin operator and image provenance

**Procedure:** Review digest/signature, SBOM, chart version and compatible CRD release.

**Evidence and pass criteria:** Capture Git commit, exact Strimzi/Kafka/Kubernetes/Argo-or-Flux versions, UTC command, rendered desired state, installed CRD validation, policy result, operator reconciliation, quorum/ISR, security, rollback/abort and reviewer. Mark **Pending** until executed. Prune, drift injection, rolling restart and upgrade drills are tabletop without approved disposable infrastructure.

### Lab 06 — Validate CRD installation order

**Procedure:** Plan operator CRDs before KafkaNodePool/Kafka resources and check readiness.

**Evidence and pass criteria:** Capture Git commit, exact Strimzi/Kafka/Kubernetes/Argo-or-Flux versions, UTC command, rendered desired state, installed CRD validation, policy result, operator reconciliation, quorum/ISR, security, rollback/abort and reviewer. Mark **Pending** until executed. Prune, drift injection, rolling restart and upgrade drills are tabletop without approved disposable infrastructure.

### Lab 07 — Build Argo CD sync waves

**Procedure:** Review hook/sync-wave strategy, health, prune, resource ownership and rollback.

**Evidence and pass criteria:** Capture Git commit, exact Strimzi/Kafka/Kubernetes/Argo-or-Flux versions, UTC command, rendered desired state, installed CRD validation, policy result, operator reconciliation, quorum/ISR, security, rollback/abort and reviewer. Mark **Pending** until executed. Prune, drift injection, rolling restart and upgrade drills are tabletop without approved disposable infrastructure.

### Lab 08 — Build Flux dependencies

**Procedure:** Review Kustomization dependsOn, healthChecks, source reconciliation and failure behavior.

**Evidence and pass criteria:** Capture Git commit, exact Strimzi/Kafka/Kubernetes/Argo-or-Flux versions, UTC command, rendered desired state, installed CRD validation, policy result, operator reconciliation, quorum/ISR, security, rollback/abort and reviewer. Mark **Pending** until executed. Prune, drift injection, rolling restart and upgrade drills are tabletop without approved disposable infrastructure.

### Lab 09 — Review server-side dry run

**Procedure:** Render manifests, validate against installed CRDs and capture schema failures.

**Evidence and pass criteria:** Capture Git commit, exact Strimzi/Kafka/Kubernetes/Argo-or-Flux versions, UTC command, rendered desired state, installed CRD validation, policy result, operator reconciliation, quorum/ISR, security, rollback/abort and reviewer. Mark **Pending** until executed. Prune, drift injection, rolling restart and upgrade drills are tabletop without approved disposable infrastructure.

### Lab 10 — Validate KafkaNodePool policy

**Procedure:** Require controller quorum, broker replicas, storage, resources and topology constraints.

**Evidence and pass criteria:** Capture Git commit, exact Strimzi/Kafka/Kubernetes/Argo-or-Flux versions, UTC command, rendered desired state, installed CRD validation, policy result, operator reconciliation, quorum/ISR, security, rollback/abort and reviewer. Mark **Pending** until executed. Prune, drift injection, rolling restart and upgrade drills are tabletop without approved disposable infrastructure.

### Lab 11 — Validate listener security policy

**Procedure:** Deny plaintext/public listener without approved exception; require TLS/auth.

**Evidence and pass criteria:** Capture Git commit, exact Strimzi/Kafka/Kubernetes/Argo-or-Flux versions, UTC command, rendered desired state, installed CRD validation, policy result, operator reconciliation, quorum/ISR, security, rollback/abort and reviewer. Mark **Pending** until executed. Prune, drift injection, rolling restart and upgrade drills are tabletop without approved disposable infrastructure.

### Lab 12 — Validate KafkaUser ACL policy

**Procedure:** Deny wildcard administrative permissions and unapproved tenant cross-access.

**Evidence and pass criteria:** Capture Git commit, exact Strimzi/Kafka/Kubernetes/Argo-or-Flux versions, UTC command, rendered desired state, installed CRD validation, policy result, operator reconciliation, quorum/ISR, security, rollback/abort and reviewer. Mark **Pending** until executed. Prune, drift injection, rolling restart and upgrade drills are tabletop without approved disposable infrastructure.

### Lab 13 — Validate storage policy

**Procedure:** Block PVC deletion, unsafe deleteClaim, unsupported shrink and unreviewed expansion.

**Evidence and pass criteria:** Capture Git commit, exact Strimzi/Kafka/Kubernetes/Argo-or-Flux versions, UTC command, rendered desired state, installed CRD validation, policy result, operator reconciliation, quorum/ISR, security, rollback/abort and reviewer. Mark **Pending** until executed. Prune, drift injection, rolling restart and upgrade drills are tabletop without approved disposable infrastructure.

### Lab 14 — Review secret management

**Procedure:** Use External Secrets or approved encrypted references; never commit raw credentials.

**Evidence and pass criteria:** Capture Git commit, exact Strimzi/Kafka/Kubernetes/Argo-or-Flux versions, UTC command, rendered desired state, installed CRD validation, policy result, operator reconciliation, quorum/ISR, security, rollback/abort and reviewer. Mark **Pending** until executed. Prune, drift injection, rolling restart and upgrade drills are tabletop without approved disposable infrastructure.

### Lab 15 — Plan progressive promotion

**Procedure:** Stage lab to staging to production with signed evidence and manual approval.

**Evidence and pass criteria:** Capture Git commit, exact Strimzi/Kafka/Kubernetes/Argo-or-Flux versions, UTC command, rendered desired state, installed CRD validation, policy result, operator reconciliation, quorum/ISR, security, rollback/abort and reviewer. Mark **Pending** until executed. Prune, drift injection, rolling restart and upgrade drills are tabletop without approved disposable infrastructure.

### Lab 16 — Review maintenance health gates

**Procedure:** Inspect KRaft quorum, ISR/minISR, URP, disk, client SLO and operator readiness.

**Evidence and pass criteria:** Capture Git commit, exact Strimzi/Kafka/Kubernetes/Argo-or-Flux versions, UTC command, rendered desired state, installed CRD validation, policy result, operator reconciliation, quorum/ISR, security, rollback/abort and reviewer. Mark **Pending** until executed. Prune, drift injection, rolling restart and upgrade drills are tabletop without approved disposable infrastructure.

### Lab 17 — Review drift detection

**Procedure:** Simulate only in disposable cluster; observe Strimzi reconciliation and GitOps diff.

**Evidence and pass criteria:** Capture Git commit, exact Strimzi/Kafka/Kubernetes/Argo-or-Flux versions, UTC command, rendered desired state, installed CRD validation, policy result, operator reconciliation, quorum/ISR, security, rollback/abort and reviewer. Mark **Pending** until executed. Prune, drift injection, rolling restart and upgrade drills are tabletop without approved disposable infrastructure.

### Lab 18 — Review rollback constraints

**Procedure:** Separate Git manifest revert from irreversible Kafka metadata/storage changes.

**Evidence and pass criteria:** Capture Git commit, exact Strimzi/Kafka/Kubernetes/Argo-or-Flux versions, UTC command, rendered desired state, installed CRD validation, policy result, operator reconciliation, quorum/ISR, security, rollback/abort and reviewer. Mark **Pending** until executed. Prune, drift injection, rolling restart and upgrade drills are tabletop without approved disposable infrastructure.

### Lab 19 — Review observability and audit

**Procedure:** Correlate Git commit, Argo/Flux sync, Strimzi reconciliation, alerts and incident timeline.

**Evidence and pass criteria:** Capture Git commit, exact Strimzi/Kafka/Kubernetes/Argo-or-Flux versions, UTC command, rendered desired state, installed CRD validation, policy result, operator reconciliation, quorum/ISR, security, rollback/abort and reviewer. Mark **Pending** until executed. Prune, drift injection, rolling restart and upgrade drills are tabletop without approved disposable infrastructure.

### Lab 20 — Complete change acceptance

**Procedure:** Score evidence, negative policy tests, rollout safety and independent review.

**Evidence and pass criteria:** Capture Git commit, exact Strimzi/Kafka/Kubernetes/Argo-or-Flux versions, UTC command, rendered desired state, installed CRD validation, policy result, operator reconciliation, quorum/ISR, security, rollback/abort and reviewer. Mark **Pending** until executed. Prune, drift injection, rolling restart and upgrade drills are tabletop without approved disposable infrastructure.

## 12. Read-only verification script

Save as `verify-ch69.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
echo '[1/10] Context'; kubectl config current-context
echo '[2/10] CRDs'; kubectl get crd | grep -E 'kafkas.kafka.strimzi.io|kafkanodepools.kafka.strimzi.io'
echo '[3/10] Kafka'; kubectl -n "$NS" get kafka,kafkanodepool -o wide
echo '[4/10] Operator'; kubectl get deploy -A | grep -i strimzi || true
echo '[5/10] Pods'; kubectl -n "$NS" get pods -o wide
echo '[6/10] PVCs'; kubectl -n "$NS" get pvc -o wide
echo '[7/10] NetworkPolicy'; kubectl -n "$NS" get networkpolicy
echo '[8/10] Argo CD Applications (if CRD installed)'
if kubectl get crd applications.argoproj.io >/dev/null 2>&1; then kubectl get applications.argoproj.io -A; else echo 'Argo CD CRD not installed'; fi
echo '[9/10] Flux Kustomizations (if CRD installed)'
if kubectl get crd kustomizations.kustomize.toolkit.fluxcd.io >/dev/null 2>&1; then kubectl get kustomizations.kustomize.toolkit.fluxcd.io -A; else echo 'Flux CRD not installed'; fi
echo '[10/10] Events'; kubectl -n "$NS" get events --sort-by=.metadata.creationTimestamp
echo 'PASS: read-only Kubernetes/GitOps inventory only.'
echo 'NOT PROVEN: safe GitOps sync, Kafka quorum, client SLO, policy enforcement or independent review.'
```

Run `chmod +x verify-ch69.sh && ./verify-ch69.sh | tee evidence-ch69/preflight.txt`. This script inventories resources and does not certify production release safety.

## 13. Twelve GitOps failure scenarios

### Scenario 1 — CRD not found during sync

**Diagnosis:** Review dependency ordering, operator readiness and target CRD API version. Correlate Git revision, rendered manifest, CRD schema, Argo/Flux status, Strimzi conditions, Kafka KRaft quorum, ISR/minISR, PVCs and client smoke. **Response:** Freeze unsafe reconciliation/pruning, preserve data, restore reviewed source of truth and execute owner-approved recovery. **Exit:** Measured or explicitly tabletop result, sanitized evidence, rollback and independent signoff.

### Scenario 2 — Argo CD reports OutOfSync forever

**Diagnosis:** Inspect operator-managed fields, normalization, ownership and compare options. Correlate Git revision, rendered manifest, CRD schema, Argo/Flux status, Strimzi conditions, Kafka KRaft quorum, ISR/minISR, PVCs and client smoke. **Response:** Freeze unsafe reconciliation/pruning, preserve data, restore reviewed source of truth and execute owner-approved recovery. **Exit:** Measured or explicitly tabletop result, sanitized evidence, rollback and independent signoff.

### Scenario 3 — Flux Kustomization stalled

**Diagnosis:** Inspect dependsOn, health checks, source revision and reconciliation events. Correlate Git revision, rendered manifest, CRD schema, Argo/Flux status, Strimzi conditions, Kafka KRaft quorum, ISR/minISR, PVCs and client smoke. **Response:** Freeze unsafe reconciliation/pruning, preserve data, restore reviewed source of truth and execute owner-approved recovery. **Exit:** Measured or explicitly tabletop result, sanitized evidence, rollback and independent signoff.

### Scenario 4 — KafkaNodePool change triggers unexpected roll

**Diagnosis:** Inspect CR diff, operator conditions, ISR and maintenance policy. Correlate Git revision, rendered manifest, CRD schema, Argo/Flux status, Strimzi conditions, Kafka KRaft quorum, ISR/minISR, PVCs and client smoke. **Response:** Freeze unsafe reconciliation/pruning, preserve data, restore reviewed source of truth and execute owner-approved recovery. **Exit:** Measured or explicitly tabletop result, sanitized evidence, rollback and independent signoff.

### Scenario 5 — Prune threatens Kafka or PVC resources

**Diagnosis:** Halt sync; review prune protection, resource lifecycle and backup. Correlate Git revision, rendered manifest, CRD schema, Argo/Flux status, Strimzi conditions, Kafka KRaft quorum, ISR/minISR, PVCs and client smoke. **Response:** Freeze unsafe reconciliation/pruning, preserve data, restore reviewed source of truth and execute owner-approved recovery. **Exit:** Measured or explicitly tabletop result, sanitized evidence, rollback and independent signoff.

### Scenario 6 — Git revert does not restore broker metadata

**Diagnosis:** Review irreversible Kafka state, version compatibility and recovery plan. Correlate Git revision, rendered manifest, CRD schema, Argo/Flux status, Strimzi conditions, Kafka KRaft quorum, ISR/minISR, PVCs and client smoke. **Response:** Freeze unsafe reconciliation/pruning, preserve data, restore reviewed source of truth and execute owner-approved recovery. **Exit:** Measured or explicitly tabletop result, sanitized evidence, rollback and independent signoff.

### Scenario 7 — Policy engine blocks safe change

**Diagnosis:** Inspect schema, constraints, exception workflow and policy tests. Correlate Git revision, rendered manifest, CRD schema, Argo/Flux status, Strimzi conditions, Kafka KRaft quorum, ISR/minISR, PVCs and client smoke. **Response:** Freeze unsafe reconciliation/pruning, preserve data, restore reviewed source of truth and execute owner-approved recovery. **Exit:** Measured or explicitly tabletop result, sanitized evidence, rollback and independent signoff.

### Scenario 8 — Unsafe listener passes review

**Diagnosis:** Inspect rendered manifests, environment overlay, policy admission and approval. Correlate Git revision, rendered manifest, CRD schema, Argo/Flux status, Strimzi conditions, Kafka KRaft quorum, ISR/minISR, PVCs and client smoke. **Response:** Freeze unsafe reconciliation/pruning, preserve data, restore reviewed source of truth and execute owner-approved recovery. **Exit:** Measured or explicitly tabletop result, sanitized evidence, rollback and independent signoff.

### Scenario 9 — Secrets appear in Git diff

**Diagnosis:** Revoke/rotate exposed credential and preserve sanitized audit. Correlate Git revision, rendered manifest, CRD schema, Argo/Flux status, Strimzi conditions, Kafka KRaft quorum, ISR/minISR, PVCs and client smoke. **Response:** Freeze unsafe reconciliation/pruning, preserve data, restore reviewed source of truth and execute owner-approved recovery. **Exit:** Measured or explicitly tabletop result, sanitized evidence, rollback and independent signoff.

### Scenario 10 — Operator version incompatible with CRD

**Diagnosis:** Check pinned release matrix, installed CRDs and upgrade order. Correlate Git revision, rendered manifest, CRD schema, Argo/Flux status, Strimzi conditions, Kafka KRaft quorum, ISR/minISR, PVCs and client smoke. **Response:** Freeze unsafe reconciliation/pruning, preserve data, restore reviewed source of truth and execute owner-approved recovery. **Exit:** Measured or explicitly tabletop result, sanitized evidence, rollback and independent signoff.

### Scenario 11 — Rolling change breaches minISR

**Diagnosis:** Pause; inspect broker ISR, quorum, storage and client SLO. Correlate Git revision, rendered manifest, CRD schema, Argo/Flux status, Strimzi conditions, Kafka KRaft quorum, ISR/minISR, PVCs and client smoke. **Response:** Freeze unsafe reconciliation/pruning, preserve data, restore reviewed source of truth and execute owner-approved recovery. **Exit:** Measured or explicitly tabletop result, sanitized evidence, rollback and independent signoff.

### Scenario 12 — GitOps Healthy but Kafka clients fail

**Diagnosis:** Verify TLS/auth, advertised listeners, producer/consumer smoke and business SLO. Correlate Git revision, rendered manifest, CRD schema, Argo/Flux status, Strimzi conditions, Kafka KRaft quorum, ISR/minISR, PVCs and client smoke. **Response:** Freeze unsafe reconciliation/pruning, preserve data, restore reviewed source of truth and execute owner-approved recovery. **Exit:** Measured or explicitly tabletop result, sanitized evidence, rollback and independent signoff.

## 14. Eight production runbooks

### Runbook A — Argo CD/Flux sync failure

**Trigger/response:** Inspect source revision, dependency order, controller logs, health and retry approval. **No-go:** unknown Git provenance, unsafe prune, lost KRaft quorum, minISR breach, leaked secrets, unsupported rollback or missing change approval. **Exit:** Reconciled source revision, healthy operator/Kafka, authenticated client smoke, RCA and independent approval.

### Runbook B — CRD and operator upgrade conflict

**Trigger/response:** Validate version matrix, freeze sync, inspect conversion and recovery. **No-go:** unknown Git provenance, unsafe prune, lost KRaft quorum, minISR breach, leaked secrets, unsupported rollback or missing change approval. **Exit:** Reconciled source revision, healthy operator/Kafka, authenticated client smoke, RCA and independent approval.

### Runbook C — Strimzi drift or field ownership conflict

**Trigger/response:** Review CR desired state, operator-generated resources and diff exclusions. **No-go:** unknown Git provenance, unsafe prune, lost KRaft quorum, minISR breach, leaked secrets, unsupported rollback or missing change approval. **Exit:** Reconciled source revision, healthy operator/Kafka, authenticated client smoke, RCA and independent approval.

### Runbook D — Unsafe prune/deletion risk

**Trigger/response:** Stop automated sync, preserve PVC/data, audit approvals and restore desired state. **No-go:** unknown Git provenance, unsafe prune, lost KRaft quorum, minISR breach, leaked secrets, unsupported rollback or missing change approval. **Exit:** Reconciled source revision, healthy operator/Kafka, authenticated client smoke, RCA and independent approval.

### Runbook E — Kafka rolling change SLO breach

**Trigger/response:** Check quorum, ISR, disk and client latency; stop rollout and follow approved recovery. **No-go:** unknown Git provenance, unsafe prune, lost KRaft quorum, minISR breach, leaked secrets, unsupported rollback or missing change approval. **Exit:** Reconciled source revision, healthy operator/Kafka, authenticated client smoke, RCA and independent approval.

### Runbook F — Policy-as-code denial/exception

**Trigger/response:** Review failed constraints, exception expiry, risk owner and audit trail. **No-go:** unknown Git provenance, unsafe prune, lost KRaft quorum, minISR breach, leaked secrets, unsupported rollback or missing change approval. **Exit:** Reconciled source revision, healthy operator/Kafka, authenticated client smoke, RCA and independent approval.

### Runbook G — Secret exposure through GitOps

**Trigger/response:** Contain, revoke, rotate, redact evidence and notify security. **No-go:** unknown Git provenance, unsafe prune, lost KRaft quorum, minISR breach, leaked secrets, unsupported rollback or missing change approval. **Exit:** Reconciled source revision, healthy operator/Kafka, authenticated client smoke, RCA and independent approval.

### Runbook H — Independent GitOps release acceptance

**Trigger/response:** Reconcile revision, health, security, smoke, rollback and signoff. **No-go:** unknown Git provenance, unsafe prune, lost KRaft quorum, minISR breach, leaked secrets, unsupported rollback or missing change approval. **Exit:** Reconciled source revision, healthy operator/Kafka, authenticated client smoke, RCA and independent approval.

## 15. SLI/SLO and change acceptance

| Signal | Why it matters | Gate |
|---|---|---|
| Git revision and signature | provenance | approved immutable source |
| Argo/Flux sync status | desired-state delivery | no failed sync |
| Strimzi reconciliation status | operator acceptance | Kafka Ready and no reconcile errors |
| KRaft controller quorum | metadata availability | quorum healthy |
| Broker ISR/minISR | durability | no unsafe under-replication |
| PVC free space/IOPS | storage safety | approved headroom |
| TLS/SASL and ACL | client security | least-privilege smoke |
| Producer/consumer SLO | business availability | no sustained regression |
| Policy violations | governance | zero unapproved exceptions |
| Rollback evidence | recovery confidence | approved reversible path or recovery plan |

Define thresholds from measured baselines, business SLOs and fault budget, not universal values.

## 16. Evidence package

```text
evidence-ch69/
  charter-raci-approval.md
  version-crd-gitops-matrix.md
  resource-ownership.md
  repository-structure.md
  operator-image-provenance.md
  crd-sync-order.md
  argocd-sync-policy.md
  flux-dependencies.md
  rendered-manifest-server-dry-run.md
  kafkanodepool-policy-tests.md
  listener-security-policy-tests.md
  kafkauser-acl-policy-tests.md
  pvc-lifecycle-policy-tests.md
  secrets-scanning.md
  lab-staging-prod-promotion.md
  kraft-isr-disk-client-gates.md
  drift-ownership-review.md
  rollback-feasibility.md
  gitops-audit-observability.md
  independent-change-acceptance.md
  readiness-scorecard.md
```

Each artifact requires exact versions, UTC time, Git revision, expected/observed result, **Live** vs **Tabletop**, sanitized evidence, owner, abort/rollback and independent reviewer.

## 17. 100-point GitOps release assessment

| Domain | Points | Critical |
|---|---:|---|
| GitOps architecture, ownership and provenance | 20 | Yes |
| CRD/operator sync ordering and reconciliation | 15 | Yes |
| Argo CD/Flux policy and drift controls | 15 | Yes |
| KafkaNodePool, TLS/ACL, PVC policy-as-code | 20 | Yes |
| Progressive promotion, quorum/ISR/client SLO | 15 | Yes |
| Rollback, incident runbooks and evidence | 10 | Yes |
| Independent technical/security review | 5 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with all critical gates independently evidenced. **Automatic Fail:** fabricated live GitOps evidence, unsafe automatic prune, secret leakage, unsupported Kafka rollback, unreviewed controller change, production SLO breach without abort or absent independent review.

## 18. References and next chapter

**References:** [Strimzi Documentation](https://strimzi.io/documentation/), [Argo CD](https://argo-cd.readthedocs.io/), [Flux](https://fluxcd.io/flux/), [Kubernetes Documentation](https://kubernetes.io/docs/), [Apache Kafka Documentation](https://kafka.apache.org/documentation/).

**Next:** Chapter 070 — Advanced Strimzi GitOps Production Operations and Kubernetes Reliability Acceptance Capstone.

---

**Verification boundary:** Publication proves document availability only. Live Argo/Flux reconciliation, policy denial tests, staged rollout, measured Kafka SLO and independent technical/security review remain Pending.
