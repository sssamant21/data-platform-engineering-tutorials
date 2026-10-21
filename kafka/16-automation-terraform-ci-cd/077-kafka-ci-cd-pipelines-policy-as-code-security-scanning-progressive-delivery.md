# Chapter 077 — Kafka CI/CD Pipelines, Policy-as-Code, Security Scanning and Progressive Delivery

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 16 — Automation, Terraform and CI/CD (2/5)  
**Primary platform:** Kubernetes / Strimzi KRaft; Amazon MSK infrastructure as an alternative  
**Prerequisites:** Chapters 001–076, GitLab CI or GitHub Actions, Kubernetes, Terraform and GitOps  
**Status:** Published · **Live lab execution:** Pending · **Independent technical/security review:** Pending

> **Safety:** Pipeline examples are validation-first and do not deploy or mutate production. Do not use privileged shared runners, static cloud credentials, `terraform apply`, destructive GitOps prune, unapproved broker upgrades, live fault injection or Kafka topic deletion. Treat Terraform plans and CI artifacts as potentially sensitive. A green pipeline is not proof of Kafka data correctness.

## 1. Mission and learning objectives

Design secure Kafka delivery pipelines with reproducible CI validation, IaC plan review, policy-as-code, software supply-chain scanning, progressive Kubernetes client delivery, Kafka-aware release gates and independent audit evidence.

By completion, readers can construct a fail-closed pipeline for Strimzi/KRaft and EKS-to-MSK workloads, test policy denials, preserve provenance, gate on ISR and client SLO, and safely abort releases.

## 2. Reference delivery architecture

```text
Developer PR / signed Git SHA
           |
      CODEOWNERS approval
           |
   lint + unit + schema checks
           |
 Terraform fmt/validate/plan
           |
 OPA/Kyverno + IaC/secret scans
           |
 SBOM + image digest + CVE policy
           |
 Staging GitOps / Strimzi reconciliation
           |
 Kafka KRaft quorum + ISR + EKS client smoke
           |
 Canary deployment / SLO gate
           |
 Security + platform production approval
           |
 Controlled promotion + audit + recovery
```

**Ownership:** Terraform owns approved infrastructure resources, GitOps owns selected Strimzi CRs, and Strimzi owns generated Kafka workloads. CI validates and promotes declared desired state; it must not independently reconcile the same resource fields.

## 3. Repository and evidence layout

```text
kafka-release/
  .gitlab-ci.yml
  .github/workflows/validate.yml
  terraform/envs/{lab,staging,production}/
  kubernetes/base/
  kubernetes/overlays/{lab,staging,production}/
  gitops/
  policies/opa/
  policies/kyverno/
  tests/policy/
  tests/kafka-smoke/
  evidence/ch077/
```

Choose **one primary CI orchestrator** per release and ensure equivalent gates if multiple systems coexist. Commit lockfiles and policy tests; exclude state files, tokens, kubeconfigs, TLS private keys, unredacted plans and synthetic credentials.

## 4. Identity and release provenance

Use short-lived OIDC federation to cloud roles or Kubernetes workload identity where supported. Require branch protections, CODEOWNERS, protected environments, least-privilege deploy roles, immutable Git SHA and pinned container image digests. Separate staging and production identities; no implicit access through EKS node roles.

**Supply-chain controls:** SBOM, signed build provenance where available, trusted base images, vulnerability scan with time-bound exceptions, dependency lockfiles and attestation verification. CVE severity alone does not establish exploitability; record context and remediation.

## 5. GitLab CI pipeline — validation-only baseline

```yaml
# .gitlab-ci.yml (illustrative; runner image/toolchain must be pinned)
stages:
  - lint
  - policy
  - security

terraform-validate:
  stage: lint
  script:
    - terraform -chdir=terraform/envs/lab fmt -check
    - terraform -chdir=terraform/envs/lab init -backend=false
    - terraform -chdir=terraform/envs/lab validate

opa-test:
  stage: policy
  script:
    - opa test policies/opa -v

secret-scan:
  stage: security
  script:
    - gitleaks detect --source . --no-git --redact
```

Runner images must contain pinned Terraform/OPA/Gitleaks binaries; the snippet deliberately omits production apply. Confirm Gitleaks flags for the pinned version. In production, protect jobs from `allow_failure: true` and ensure mandatory jobs are required for merge.

## 6. OPA policy example and tests

The following Rego illustrates a Kafka release input contract. **Input schema must be validated**, and missing fields should fail closed.

```rego
package kafka.release

default allow := false

allow if {
  input.tls_enabled == true
  input.replication_factor >= 3
  input.min_insync_replicas >= 2
  input.wildcard_admin_acl == false
  input.destructive_change == false
}

deny contains msg if {
  not allow
  msg := "Kafka release violates security, durability or destructive-change policy"
}
```

Test with approved OPA version and the following representative JSON:

```json
{
  "tls_enabled": true,
  "replication_factor": 3,
  "min_insync_replicas": 2,
  "wildcard_admin_acl": false,
  "destructive_change": false
}
```

**Negative test:** set `tls_enabled=false`, `min_insync_replicas=1` or `destructive_change=true`; the policy must deny. RF=3/minISR=2 are illustrative organizational defaults, not universal cluster guarantees; require fault-domain and client `acks` review.

## 7. Kyverno/admission control

Use Kyverno or Gatekeeper policies for Kubernetes resources with validated Strimzi CRD field paths. For example, require approved TLS listeners and disallow unauthorized wildcard KafkaUser ACLs. Pin Kyverno version and run `kyverno test` on fixtures before admission enforcement.

**Caution:** Do not deploy a generic untested policy that blocks the Strimzi operator from reconciling Kafka resources. Exemptions must be scoped, approved and expire.

## 8. Terraform plan review and destructive-change detection

```bash
terraform -chdir=terraform/envs/lab fmt -check
terraform -chdir=terraform/envs/lab init -backend=false
terraform -chdir=terraform/envs/lab validate
```

For an approved isolated environment with backend access, capture a reviewed `terraform plan -out=tfplan` and `terraform show -json tfplan`; restrict plan artifacts. CI should parse `resource_changes[].change.actions` and block delete/replace unless a separate approved maintenance gate is satisfied.

**Kafka-specific danger:** a plan may replace an MSK cluster, remove a KafkaTopic CR, change storage or broaden IAM. `prevent_destroy` is useful but does not replace policy and backup.

## 9. Progressive delivery for Kafka clients

Release client applications progressively: staging smoke -> small canary -> limited traffic -> full promotion. Gate each step on authenticated Kafka producer acknowledgments, consumer freshness/lag, request errors, Kafka ISR/under-replicated partitions and unique event-ID reconciliation.

A Kubernetes Deployment rollout `Available=True` is not sufficient. Canary workload metrics should distinguish Kafka protocol failures from application errors. Stop immediately on missing events, authorization regressions or ISR loss.

## 10. GitOps sync, prune and rollback safety

- Install CRDs/operator before Kafka and KafkaNodePool CRs.
- Sync KafkaTopic/KafkaUser only after Kafka readiness and policy validation.
- Use one owner per resource; never reconcile operator-generated PVCs/Pods directly.
- Treat prune of Kafka CRs, secrets and storage as a high-risk change.
- Revert only reversible application/manifest changes; Kafka data deletion, partition/offset changes and version upgrades require recovery planning.

## 11. Twenty Kubernetes-first CI/CD labs

### Lab 01 — Design Kafka pipeline stages

**Procedure:** Document lint, unit, IaC plan, policy, security, staging, smoke, approval and production.

**Expected evidence:** Git SHA, pinned tool versions, UTC time, approved environment, CI job ID, policy input/result, sanitized scan or Terraform plan, Kafka ISR/minISR, synthetic event IDs and client SLO when applicable, risk/abort, owner and reviewer. Mark **Pending** until executed. Production promotion, secret rotation, scaling and destructive actions remain **Tabletop** unless approved in disposable infrastructure.

### Lab 02 — Pin CI runners and tools

**Procedure:** Record GitLab/GitHub runners, kubectl, Helm, Terraform, OPA, Trivy and Kafka clients.

**Expected evidence:** Git SHA, pinned tool versions, UTC time, approved environment, CI job ID, policy input/result, sanitized scan or Terraform plan, Kafka ISR/minISR, synthetic event IDs and client SLO when applicable, risk/abort, owner and reviewer. Mark **Pending** until executed. Production promotion, secret rotation, scaling and destructive actions remain **Tabletop** unless approved in disposable infrastructure.

### Lab 03 — Configure workload identity

**Procedure:** Use GitLab/GitHub OIDC federation or Kubernetes workload identity; avoid static AWS keys.

**Expected evidence:** Git SHA, pinned tool versions, UTC time, approved environment, CI job ID, policy input/result, sanitized scan or Terraform plan, Kafka ISR/minISR, synthetic event IDs and client SLO when applicable, risk/abort, owner and reviewer. Mark **Pending** until executed. Production promotion, secret rotation, scaling and destructive actions remain **Tabletop** unless approved in disposable infrastructure.

### Lab 04 — Protect production branches

**Procedure:** Require CODEOWNERS, security review, signed change provenance and protected environments.

**Expected evidence:** Git SHA, pinned tool versions, UTC time, approved environment, CI job ID, policy input/result, sanitized scan or Terraform plan, Kafka ISR/minISR, synthetic event IDs and client SLO when applicable, risk/abort, owner and reviewer. Mark **Pending** until executed. Production promotion, secret rotation, scaling and destructive actions remain **Tabletop** unless approved in disposable infrastructure.

### Lab 05 — Validate Terraform formatting

**Procedure:** Execute terraform fmt -check, init -backend=false and validate in an isolated module.

**Expected evidence:** Git SHA, pinned tool versions, UTC time, approved environment, CI job ID, policy input/result, sanitized scan or Terraform plan, Kafka ISR/minISR, synthetic event IDs and client SLO when applicable, risk/abort, owner and reviewer. Mark **Pending** until executed. Production promotion, secret rotation, scaling and destructive actions remain **Tabletop** unless approved in disposable infrastructure.

### Lab 06 — Scan IaC misconfigurations

**Procedure:** Run approved IaC scanners against Terraform, Helm and Kubernetes manifests.

**Expected evidence:** Git SHA, pinned tool versions, UTC time, approved environment, CI job ID, policy input/result, sanitized scan or Terraform plan, Kafka ISR/minISR, synthetic event IDs and client SLO when applicable, risk/abort, owner and reviewer. Mark **Pending** until executed. Production promotion, secret rotation, scaling and destructive actions remain **Tabletop** unless approved in disposable infrastructure.

### Lab 07 — Scan source secrets

**Procedure:** Run Gitleaks or equivalent against test fixture with redacted reporting.

**Expected evidence:** Git SHA, pinned tool versions, UTC time, approved environment, CI job ID, policy input/result, sanitized scan or Terraform plan, Kafka ISR/minISR, synthetic event IDs and client SLO when applicable, risk/abort, owner and reviewer. Mark **Pending** until executed. Production promotion, secret rotation, scaling and destructive actions remain **Tabletop** unless approved in disposable infrastructure.

### Lab 08 — Scan images and dependencies

**Procedure:** Review pinned image digest, CVEs, SBOM, exception expiry and provenance.

**Expected evidence:** Git SHA, pinned tool versions, UTC time, approved environment, CI job ID, policy input/result, sanitized scan or Terraform plan, Kafka ISR/minISR, synthetic event IDs and client SLO when applicable, risk/abort, owner and reviewer. Mark **Pending** until executed. Production promotion, secret rotation, scaling and destructive actions remain **Tabletop** unless approved in disposable infrastructure.

### Lab 09 — Evaluate OPA policy tests

**Procedure:** Run Rego policy against synthetic safe/unsafe Kafka release manifests.

**Expected evidence:** Git SHA, pinned tool versions, UTC time, approved environment, CI job ID, policy input/result, sanitized scan or Terraform plan, Kafka ISR/minISR, synthetic event IDs and client SLO when applicable, risk/abort, owner and reviewer. Mark **Pending** until executed. Production promotion, secret rotation, scaling and destructive actions remain **Tabletop** unless approved in disposable infrastructure.

### Lab 10 — Evaluate Kyverno policy

**Procedure:** Validate deny for plaintext Kafka listener, unsafe replicas or wildcard authorization.

**Expected evidence:** Git SHA, pinned tool versions, UTC time, approved environment, CI job ID, policy input/result, sanitized scan or Terraform plan, Kafka ISR/minISR, synthetic event IDs and client SLO when applicable, risk/abort, owner and reviewer. Mark **Pending** until executed. Production promotion, secret rotation, scaling and destructive actions remain **Tabletop** unless approved in disposable infrastructure.

### Lab 11 — Review Terraform plan changes

**Procedure:** Flag create/replace/delete, AWS costs, IAM broadening, storage and cluster upgrades.

**Expected evidence:** Git SHA, pinned tool versions, UTC time, approved environment, CI job ID, policy input/result, sanitized scan or Terraform plan, Kafka ISR/minISR, synthetic event IDs and client SLO when applicable, risk/abort, owner and reviewer. Mark **Pending** until executed. Production promotion, secret rotation, scaling and destructive actions remain **Tabletop** unless approved in disposable infrastructure.

### Lab 12 — Validate Strimzi CRDs

**Procedure:** Check schema and version matrix before Kafka/KafkaNodePool/Topic/User deployment.

**Expected evidence:** Git SHA, pinned tool versions, UTC time, approved environment, CI job ID, policy input/result, sanitized scan or Terraform plan, Kafka ISR/minISR, synthetic event IDs and client SLO when applicable, risk/abort, owner and reviewer. Mark **Pending** until executed. Production promotion, secret rotation, scaling and destructive actions remain **Tabletop** unless approved in disposable infrastructure.

### Lab 13 — Validate GitOps sync order

**Procedure:** Review CRD/operator readiness, Kafka node pools, Kafka users/topics and client workloads.

**Expected evidence:** Git SHA, pinned tool versions, UTC time, approved environment, CI job ID, policy input/result, sanitized scan or Terraform plan, Kafka ISR/minISR, synthetic event IDs and client SLO when applicable, risk/abort, owner and reviewer. Mark **Pending** until executed. Production promotion, secret rotation, scaling and destructive actions remain **Tabletop** unless approved in disposable infrastructure.

### Lab 14 — Review destructive prune controls

**Procedure:** Protect Kafka CRs, PVCs, secrets and state from unreviewed automated deletion.

**Expected evidence:** Git SHA, pinned tool versions, UTC time, approved environment, CI job ID, policy input/result, sanitized scan or Terraform plan, Kafka ISR/minISR, synthetic event IDs and client SLO when applicable, risk/abort, owner and reviewer. Mark **Pending** until executed. Production promotion, secret rotation, scaling and destructive actions remain **Tabletop** unless approved in disposable infrastructure.

### Lab 15 — Implement staging promotion

**Procedure:** Pin Git SHA/image digest and require staging Kafka ISR/quorum and client smoke.

**Expected evidence:** Git SHA, pinned tool versions, UTC time, approved environment, CI job ID, policy input/result, sanitized scan or Terraform plan, Kafka ISR/minISR, synthetic event IDs and client SLO when applicable, risk/abort, owner and reviewer. Mark **Pending** until executed. Production promotion, secret rotation, scaling and destructive actions remain **Tabletop** unless approved in disposable infrastructure.

### Lab 16 — Implement synthetic Kafka smoke

**Procedure:** Produce acknowledged unique event IDs, consume and reconcile lag, duplicates and errors.

**Expected evidence:** Git SHA, pinned tool versions, UTC time, approved environment, CI job ID, policy input/result, sanitized scan or Terraform plan, Kafka ISR/minISR, synthetic event IDs and client SLO when applicable, risk/abort, owner and reviewer. Mark **Pending** until executed. Production promotion, secret rotation, scaling and destructive actions remain **Tabletop** unless approved in disposable infrastructure.

### Lab 17 — Define progressive delivery gate

**Procedure:** Use canary client deployment, latency/error/lag thresholds and controlled traffic.

**Expected evidence:** Git SHA, pinned tool versions, UTC time, approved environment, CI job ID, policy input/result, sanitized scan or Terraform plan, Kafka ISR/minISR, synthetic event IDs and client SLO when applicable, risk/abort, owner and reviewer. Mark **Pending** until executed. Production promotion, secret rotation, scaling and destructive actions remain **Tabletop** unless approved in disposable infrastructure.

### Lab 18 — Exercise safe abort logic

**Procedure:** Simulate failing policy/SLO evidence and ensure pipeline refuses production promotion.

**Expected evidence:** Git SHA, pinned tool versions, UTC time, approved environment, CI job ID, policy input/result, sanitized scan or Terraform plan, Kafka ISR/minISR, synthetic event IDs and client SLO when applicable, risk/abort, owner and reviewer. Mark **Pending** until executed. Production promotion, secret rotation, scaling and destructive actions remain **Tabletop** unless approved in disposable infrastructure.

### Lab 19 — Review rollback and recovery

**Procedure:** Distinguish reversible Deployment/Git changes from Kafka topic/partition/data mutations.

**Expected evidence:** Git SHA, pinned tool versions, UTC time, approved environment, CI job ID, policy input/result, sanitized scan or Terraform plan, Kafka ISR/minISR, synthetic event IDs and client SLO when applicable, risk/abort, owner and reviewer. Mark **Pending** until executed. Production promotion, secret rotation, scaling and destructive actions remain **Tabletop** unless approved in disposable infrastructure.

### Lab 20 — Perform independent release acceptance

**Procedure:** Check approval, signed artifacts, logs, audit, SLO and security reviewer.

**Expected evidence:** Git SHA, pinned tool versions, UTC time, approved environment, CI job ID, policy input/result, sanitized scan or Terraform plan, Kafka ISR/minISR, synthetic event IDs and client SLO when applicable, risk/abort, owner and reviewer. Mark **Pending** until executed. Production promotion, secret rotation, scaling and destructive actions remain **Tabletop** unless approved in disposable infrastructure.

## 12. Read-only pipeline preflight script

Save as `verify-ch77.sh` in the repo root:

```bash
#!/usr/bin/env bash
set -euo pipefail
: "${TF_DIR:?Set reviewed Terraform module directory}"
echo '[1/9] Git revision'; git rev-parse HEAD
echo '[2/9] Terraform version'; terraform version
echo '[3/9] Terraform format'; terraform -chdir="$TF_DIR" fmt -check
echo '[4/9] Terraform init'; terraform -chdir="$TF_DIR" init -backend=false
echo '[5/9] Terraform validate'; terraform -chdir="$TF_DIR" validate
echo '[6/9] OPA version'; opa version
echo '[7/9] OPA policy tests'; opa test policies/opa -v
echo '[8/9] Kubernetes context'; kubectl config current-context
echo '[9/9] Kafka CR inventory'; kubectl get kafka,kafkanodepool -A
echo 'PASS: local validation and read-only Kubernetes inventory only.'
echo 'NOT PROVEN: image scan, live Kafka SLO, production approval or security acceptance.'
```

Requires pinned binaries and existing policy test directory. A successful preflight does not prove scan execution, network reachability or Kafka data correctness.

## 13. Twelve pipeline and delivery failure scenarios

### Scenario 1 — CI runner exposes static credentials

**Diagnosis:** Revoke and rotate, isolate runner, switch to short-lived identity. Correlate CI job identity and artifacts, Git SHA, policy fixtures, Terraform plan, GitOps sync, Strimzi conditions, Kafka ISR/minISR and EKS client event IDs. **Response:** Freeze unsafe promotion, preserve sanitized evidence, contain credential exposure, restore least privilege and use approved recovery. **Exit:** Corrected fail-closed gate, healthy Kafka client SLO, RCA and reviewer.

### Scenario 2 — Pipeline passes but policy file was skipped

**Diagnosis:** Require fail-closed policy job, pinned version and immutable test evidence. Correlate CI job identity and artifacts, Git SHA, policy fixtures, Terraform plan, GitOps sync, Strimzi conditions, Kafka ISR/minISR and EKS client event IDs. **Response:** Freeze unsafe promotion, preserve sanitized evidence, contain credential exposure, restore least privilege and use approved recovery. **Exit:** Corrected fail-closed gate, healthy Kafka client SLO, RCA and reviewer.

### Scenario 3 — OPA allows wildcard ACL

**Diagnosis:** Inspect Rego input schema, missing-field defaults and negative tests. Correlate CI job identity and artifacts, Git SHA, policy fixtures, Terraform plan, GitOps sync, Strimzi conditions, Kafka ISR/minISR and EKS client event IDs. **Response:** Freeze unsafe promotion, preserve sanitized evidence, contain credential exposure, restore least privilege and use approved recovery. **Exit:** Corrected fail-closed gate, healthy Kafka client SLO, RCA and reviewer.

### Scenario 4 — Kyverno denies safe Kafka manifests

**Diagnosis:** Inspect CRD paths, namespace exclusions, match semantics and policy version. Correlate CI job identity and artifacts, Git SHA, policy fixtures, Terraform plan, GitOps sync, Strimzi conditions, Kafka ISR/minISR and EKS client event IDs. **Response:** Freeze unsafe promotion, preserve sanitized evidence, contain credential exposure, restore least privilege and use approved recovery. **Exit:** Corrected fail-closed gate, healthy Kafka client SLO, RCA and reviewer.

### Scenario 5 — Terraform plan proposes MSK replacement

**Diagnosis:** Freeze release, inspect ForceNew and drift; require dedicated change. Correlate CI job identity and artifacts, Git SHA, policy fixtures, Terraform plan, GitOps sync, Strimzi conditions, Kafka ISR/minISR and EKS client event IDs. **Response:** Freeze unsafe promotion, preserve sanitized evidence, contain credential exposure, restore least privilege and use approved recovery. **Exit:** Corrected fail-closed gate, healthy Kafka client SLO, RCA and reviewer.

### Scenario 6 — GitOps sync prunes KafkaTopic or PVC

**Diagnosis:** Suspend prune, preserve data and investigate resource ownership. Correlate CI job identity and artifacts, Git SHA, policy fixtures, Terraform plan, GitOps sync, Strimzi conditions, Kafka ISR/minISR and EKS client event IDs. **Response:** Freeze unsafe promotion, preserve sanitized evidence, contain credential exposure, restore least privilege and use approved recovery. **Exit:** Corrected fail-closed gate, healthy Kafka client SLO, RCA and reviewer.

### Scenario 7 — Strimzi CRDs are incompatible

**Diagnosis:** Pin operator/CRD/Kafka versions and validate schema before apply. Correlate CI job identity and artifacts, Git SHA, policy fixtures, Terraform plan, GitOps sync, Strimzi conditions, Kafka ISR/minISR and EKS client event IDs. **Response:** Freeze unsafe promotion, preserve sanitized evidence, contain credential exposure, restore least privilege and use approved recovery. **Exit:** Corrected fail-closed gate, healthy Kafka client SLO, RCA and reviewer.

### Scenario 8 — Canary Pods healthy but Kafka produce fails

**Diagnosis:** Check auth, advertised brokers, topic ACL, ISR and acknowledged event IDs. Correlate CI job identity and artifacts, Git SHA, policy fixtures, Terraform plan, GitOps sync, Strimzi conditions, Kafka ISR/minISR and EKS client event IDs. **Response:** Freeze unsafe promotion, preserve sanitized evidence, contain credential exposure, restore least privilege and use approved recovery. **Exit:** Corrected fail-closed gate, healthy Kafka client SLO, RCA and reviewer.

### Scenario 9 — Consumer lag spikes during promotion

**Diagnosis:** Inspect rebalance, throughput, partitions and downstream processing. Correlate CI job identity and artifacts, Git SHA, policy fixtures, Terraform plan, GitOps sync, Strimzi conditions, Kafka ISR/minISR and EKS client event IDs. **Response:** Freeze unsafe promotion, preserve sanitized evidence, contain credential exposure, restore least privilege and use approved recovery. **Exit:** Corrected fail-closed gate, healthy Kafka client SLO, RCA and reviewer.

### Scenario 10 — SBOM or image scan is stale

**Diagnosis:** Rebuild from pinned digest, update vulnerability data and review exceptions. Correlate CI job identity and artifacts, Git SHA, policy fixtures, Terraform plan, GitOps sync, Strimzi conditions, Kafka ISR/minISR and EKS client event IDs. **Response:** Freeze unsafe promotion, preserve sanitized evidence, contain credential exposure, restore least privilege and use approved recovery. **Exit:** Corrected fail-closed gate, healthy Kafka client SLO, RCA and reviewer.

### Scenario 11 — Rollback leaves Kafka state inconsistent

**Diagnosis:** Apply recovery runbook for irreversible topic/partition/offset changes. Correlate CI job identity and artifacts, Git SHA, policy fixtures, Terraform plan, GitOps sync, Strimzi conditions, Kafka ISR/minISR and EKS client event IDs. **Response:** Freeze unsafe promotion, preserve sanitized evidence, contain credential exposure, restore least privilege and use approved recovery. **Exit:** Corrected fail-closed gate, healthy Kafka client SLO, RCA and reviewer.

### Scenario 12 — Production release bypasses approval

**Diagnosis:** Contain deployment, audit identities, restore branch protections and review. Correlate CI job identity and artifacts, Git SHA, policy fixtures, Terraform plan, GitOps sync, Strimzi conditions, Kafka ISR/minISR and EKS client event IDs. **Response:** Freeze unsafe promotion, preserve sanitized evidence, contain credential exposure, restore least privilege and use approved recovery. **Exit:** Corrected fail-closed gate, healthy Kafka client SLO, RCA and reviewer.

## 14. Eight production runbooks

### Runbook A — CI identity or secret compromise

**Trigger/response:** Revoke tokens, inspect runner logs, rotate secrets and audit AWS/K8s permissions. **No-go:** bypassed required checks, leaked secrets, unreviewed destroy/prune, lost Kafka ISR, unsafe IAM policy, unsupported rollback or missing event correctness. **Exit:** Protected pipeline, reconciled Git/IaC ownership, healthy Kafka and independent approval.

### Runbook B — Policy-as-code gate failure

**Trigger/response:** Reproduce pinned policy input, fix rule or manifest and preserve negative tests. **No-go:** bypassed required checks, leaked secrets, unreviewed destroy/prune, lost Kafka ISR, unsafe IAM policy, unsupported rollback or missing event correctness. **Exit:** Protected pipeline, reconciled Git/IaC ownership, healthy Kafka and independent approval.

### Runbook C — Unsafe Terraform plan

**Trigger/response:** Block promotion, review destructive actions, state, costs and recovery. **No-go:** bypassed required checks, leaked secrets, unreviewed destroy/prune, lost Kafka ISR, unsafe IAM policy, unsupported rollback or missing event correctness. **Exit:** Protected pipeline, reconciled Git/IaC ownership, healthy Kafka and independent approval.

### Runbook D — GitOps reconciliation conflict

**Trigger/response:** Identify Terraform/Argo/Flux/Strimzi ownership, suspend unsafe sync and recover. **No-go:** bypassed required checks, leaked secrets, unreviewed destroy/prune, lost Kafka ISR, unsafe IAM policy, unsupported rollback or missing event correctness. **Exit:** Protected pipeline, reconciled Git/IaC ownership, healthy Kafka and independent approval.

### Runbook E — Security scan critical finding

**Trigger/response:** Triage CVE/secret/IaC impact, document time-limited exception or fix. **No-go:** bypassed required checks, leaked secrets, unreviewed destroy/prune, lost Kafka ISR, unsafe IAM policy, unsupported rollback or missing event correctness. **Exit:** Protected pipeline, reconciled Git/IaC ownership, healthy Kafka and independent approval.

### Runbook F — Canary SLO regression

**Trigger/response:** Stop rollout, verify Kafka ISR, latency, lag and event IDs, revert safe changes. **No-go:** bypassed required checks, leaked secrets, unreviewed destroy/prune, lost Kafka ISR, unsafe IAM policy, unsupported rollback or missing event correctness. **Exit:** Protected pipeline, reconciled Git/IaC ownership, healthy Kafka and independent approval.

### Runbook G — Kafka release incident

**Trigger/response:** Trace deployment SHA, auth/network, broker health, client offsets and recovery. **No-go:** bypassed required checks, leaked secrets, unreviewed destroy/prune, lost Kafka ISR, unsafe IAM policy, unsupported rollback or missing event correctness. **Exit:** Protected pipeline, reconciled Git/IaC ownership, healthy Kafka and independent approval.

### Runbook H — Independent CI/CD acceptance

**Trigger/response:** Verify provenance, policy coverage, approvals, rollback and signed evidence. **No-go:** bypassed required checks, leaked secrets, unreviewed destroy/prune, lost Kafka ISR, unsafe IAM policy, unsupported rollback or missing event correctness. **Exit:** Protected pipeline, reconciled Git/IaC ownership, healthy Kafka and independent approval.

## 15. Evidence bundle

```text
evidence-ch77/
  pipeline-architecture.md
  pinned-runners-tools.md
  oidc-workload-identity.md
  branch-protections.md
  terraform-validation.md
  iac-scan.md
  secret-scan.md
  image-sbom-cve.md
  opa-policy-positive-negative.md
  kyverno-policy-tests.md
  terraform-plan-review.md
  strimzi-schema-matrix.md
  gitops-sync-order.md
  destructive-prune-guard.md
  staging-promotion.md
  kafka-event-ledger.csv
  canary-slo.md
  abort-negative-test.md
  rollback-recovery.md
  independent-release-signoff.md
  scorecard.md
```

Each artifact needs UTC time, pinned versions, Git SHA, expected/observed result, **Live** vs **Tabletop**, sanitized logs, owner, abort/rollback and independent reviewer.

## 16. 100-point CI/CD security and reliability assessment

| Domain | Points | Critical |
|---|---:|---|
| Identity, provenance and branch protection | 20 | Yes |
| Terraform/schema and destructive-change gates | 20 | Yes |
| OPA/Kyverno policy and negative tests | 20 | Yes |
| Security scanning, SBOM and secrets | 15 | Yes |
| Canary SLO, Kafka ISR and event correctness | 15 | Yes |
| Rollback, incident runbooks and audit | 5 | Yes |
| Independent technical/security review | 5 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 and all critical gates independently evidenced. **Automatic Fail:** fabricated live evidence, bypassed policy, credential exposure, unsafe destroy/prune, unexplained missing Kafka events or absent independent review.

## 17. References and next chapter

**References:** [GitLab CI/CD](https://docs.gitlab.com/ci/), [OPA](https://www.openpolicyagent.org/docs), [Kyverno](https://kyverno.io/docs/), [Terraform](https://developer.hashicorp.com/terraform/docs), [Strimzi](https://strimzi.io/documentation/), [Argo CD](https://argo-cd.readthedocs.io/), [Apache Kafka](https://kafka.apache.org/documentation/).

**Next:** Chapter 078 — Kafka GitOps Drift Detection, Automated Reconciliation and Safe Rollback Engineering.

---

**Verification boundary:** Chapter publication proves document availability only. Live CI job execution, OPA/Kyverno tests, image/secret scanning, canary Kafka client SLO and independent technical/security review remain Pending.
