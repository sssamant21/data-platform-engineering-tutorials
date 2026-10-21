# Chapter 076 — Kafka Infrastructure as Code with Terraform, GitOps and CI/CD Automation

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 16 — Automation, Terraform and CI/CD (1/5)  
**Primary platform:** Kubernetes + Strimzi Kafka (KRaft) with Amazon MSK as a managed-service alternative  
**Prerequisites:** Chapters 001–075, Terraform, Kubernetes, GitOps and AWS IAM  
**Publication:** Published · **Live labs:** Pending · **Independent technical/security review:** Pending

> **Safety:** This chapter is plan-first and non-destructive by default. Never run `terraform apply`/`destroy`, force-unlock remote state, prune Kafka CRs/PVCs, modify MSK brokers, expose IAM credentials or roll Kafka versions in production without a reviewed change. A Git revert does not reverse Kafka topic deletion, partition changes, offsets, metadata or storage. AWS resources may incur charges.

## 1. Mission and learning outcomes

Build a reliable Infrastructure-as-Code delivery model for Kafka: Terraform for cloud/platform infrastructure, GitOps for declarative Strimzi custom resources, and CI/CD for validation, approvals, progressive promotion and post-deploy acceptance. Distinguish **source-of-truth ownership**, **infrastructure lifecycle**, **Kafka data-plane state** and **application correctness**.

By completion, readers can design secure Terraform state, validate provider constraints and plans, enforce Kafka policy-as-code, sequence Strimzi CRDs/operator/cluster, automate EKS-to-MSK controls, prevent destructive changes and establish evidence-driven release gates.

## 2. Reference architecture and ownership

```text
                   Git PR / reviewed revision
                              |
                fmt / validate / lint / policy
                              |
                     Terraform plan
                              |
                 approval + change ticket
                              |
             +----------------+----------------+
             |                                 |
      Terraform cloud/VPC/EKS/MSK        GitOps Argo CD/Flux
             |                                 |
     AWS APIs and remote state         Strimzi Kafka CRs
                                               |
                                        Strimzi Operator
                                               |
                                    KafkaNodePool / Kafka
                                               |
                                  KRaft quorum + brokers
             +----------------+----------------+
                              |
                   TLS/IAM Kafka clients
                              |
                  ISR + SLO + event ledger
```

**Single owner rule:** Terraform may own EKS/MSK/network/IAM and operator installation if designed that way; GitOps owns selected Kafka/KafkaNodePool/KafkaTopic/KafkaUser resources; Strimzi owns generated workloads. Never configure Terraform and Argo/Flux to reconcile the same Kubernetes resource/fields independently.

## 3. Repository layout

```text
kafka-platform-iac/
  terraform/
    modules/
      network/
      eks/
      msk/
      observability/
    envs/
      lab/
      staging/
      production/
  kubernetes/
    base/
      kafka/
      nodepools/
      topics/
      users/
    overlays/
      lab/
      staging/
      production/
  gitops/
    argocd/
    flux/
  policies/
    terraform/
    kubernetes/
  ci/
    validate.sh
  tests/
    kafka-smoke/
  evidence/
    ch076/
```

Use separate AWS accounts, remote state and deployment roles for production when feasible. Keep provider lockfiles committed; never commit state, plan files containing sensitive values, kubeconfigs, tokens, passwords or certificates.

## 4. Terraform provider, state and version controls

Example **illustrative** provider constraints; validate currently supported provider versions and modules before adoption:

```hcl
terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
  }
}

variable "aws_region" {
  type = string
  validation {
    condition     = length(var.aws_region) > 0
    error_message = "AWS region must not be empty."
  }
}
```

Pin and upgrade versions through reviewed PRs. For remote S3 state, configure encryption, restricted IAM, versioning and a supported state locking mechanism for the chosen Terraform version. Validate backend semantics rather than copying obsolete lock-table patterns.

**Do not put Kafka credentials in Terraform outputs or state.** Even values marked `sensitive` may exist in state; use Secrets Manager/External Secrets and scoped access.

## 5. Terraform plan-first workflow

```bash
terraform version
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
terraform providers
```

For an **approved disposable environment** with configured remote backend and read-only planning identity:

```bash
terraform init -lockfile=readonly
terraform plan -out=tfplan
terraform show -json tfplan > tfplan.json
```

The plan may contain sensitive information: restrict artifact access and retention, and never post full plan JSON publicly. `terraform init -backend=false` validates local configuration but cannot prove remote backend locking/access. A plan is not an apply, and drift is not automatically safe to reconcile.

## 6. Terraform AWS MSK example (illustrative, not deploy-ready)

```hcl
# Example only: VPC subnet IDs, security groups, KMS,
# supported broker type/Kafka version and monitoring
# must be supplied and reviewed before any apply.
resource "aws_msk_cluster" "example" {
  cluster_name           = "kafka-lab"
  kafka_version          = var.kafka_version
  number_of_broker_nodes = 3

  broker_node_group_info {
    instance_type   = var.broker_instance_type
    client_subnets  = var.private_subnet_ids
    security_groups = [var.kafka_security_group_id]

    storage_info {
      ebs_storage_info {
        volume_size = var.broker_volume_gib
      }
    }
  }

  encryption_info {
    encryption_in_transit {
      client_broker = "TLS"
      in_cluster    = true
    }
  }

  tags = {
    Environment = "lab"
    Owner       = "platform-sre"
  }

  lifecycle {
    prevent_destroy = true
  }
}
```

Variables and subnet/security group resources are intentionally omitted. The example is a **review target**, not a complete executable deployment. Check AWS provider/MSK schema, support for the selected Kafka version and cost before use. `prevent_destroy` helps guard Terraform destruction but does not replace IAM policy, backup or GitOps prune controls.

## 7. Strimzi GitOps reconciliation

Use GitOps for reviewed Strimzi CRs only after CRDs and operators are ready. Sequence:

1. Namespace/RBAC and admission policies.
2. Strimzi operator and CRDs (using one declared owner).
3. Kafka and KafkaNodePool KRaft cluster resources.
4. KafkaTopic and KafkaUser where supported.
5. Client application and authenticated smoke.
6. SLO/quorum/ISR and rollback gates.

Do not GitOps-manage operator-generated StatefulSets/Pods/PVCs. Disable or separately approve prune for stateful Kafka resources; inspect operator behavior and CRD compatibility before changes.

## 8. Policy-as-code gates

| Policy | Why it matters | Fail condition |
|---|---|---|
| No destructive plans | prevent MSK/Kafka/PVC loss | replace/destroy without approval |
| TLS and authentication | protect Kafka data | plaintext or anonymous listener |
| Kafka durability | protect acknowledged writes | unsafe RF/minISR |
| Namespace/RBAC | tenant isolation | wildcard admin |
| State and secrets | prevent credential disclosure | plaintext secrets in repo/state artifacts |
| Version matrix | prevent unsupported upgrades | unapproved provider/CRD/Kafka combination |
| Cost/quotas | control cloud spend | unapproved broker/storage expansion |
| Post-deploy client smoke | prove correctness | missing or duplicate synthetic event IDs |

Admission and CI checks complement, but do not replace, live Kafka client acceptance.

## 9. CI validation pipeline example

```yaml
# .gitlab-ci.yml — example; runner images and credentials must be pinned
stages:
  - validate
  - plan

terraform-validate:
  stage: validate
  script:
    - terraform -chdir=terraform/envs/lab fmt -check
    - terraform -chdir=terraform/envs/lab init -backend=false
    - terraform -chdir=terraform/envs/lab validate

terraform-plan:
  stage: plan
  when: manual
  script:
    - terraform -chdir=terraform/envs/lab init -lockfile=readonly
    - terraform -chdir=terraform/envs/lab plan -input=false
```

Use short-lived OIDC federation rather than static AWS keys, restricted runners, protected environments and approved deployment roles. The snippet assumes a Terraform-capable runner and an initialized approved backend. Production apply is deliberately absent.

## 10. Promotion, drift and rollback

**Promotion:** immutable Git revision -> isolated lab -> staging -> approved production. Require signed/reviewed PR, policy scan, plan, Kafka ISR/minISR, security, EKS client SLO and rollback/recovery.

**Drift:** Terraform refresh identifies infrastructure drift; Argo/Flux reports GitOps drift; Strimzi reconciliation manages generated broker workloads. Classify which controller owns the resource before fixing drift.

**Rollback:** Git revert is appropriate only for reversible desired-state changes. Kafka data/offset/partition/metadata mutations and certain MSK upgrades need a documented recovery path, not a blind revert.

## 11. Twenty Kubernetes-first IaC and CI/CD labs

### Lab 01 — Approve automation architecture

**Procedure:** Define Kafka platform (Strimzi/MSK), environments, owners, RACI, risk and SLO.

**Evidence:** Git revision, Terraform/provider/Strimzi/Kafka/EKS versions, UTC time, environment, expected/observed plan or validation, ownership map, policy outcome, Kafka quorum/ISR and client event IDs where relevant, risk, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Any apply, upgrade, state mutation or destructive test remains **Tabletop** without an approved disposable environment.

### Lab 02 — Pin toolchain versions

**Procedure:** Record Terraform, provider, Strimzi, Kubernetes, Helm, Argo/Flux and Kafka versions.

**Evidence:** Git revision, Terraform/provider/Strimzi/Kafka/EKS versions, UTC time, environment, expected/observed plan or validation, ownership map, policy outcome, Kafka quorum/ISR and client event IDs where relevant, risk, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Any apply, upgrade, state mutation or destructive test remains **Tabletop** without an approved disposable environment.

### Lab 03 — Review remote Terraform state

**Procedure:** Inspect backend encryption, locking, access, retention and recovery procedures.

**Evidence:** Git revision, Terraform/provider/Strimzi/Kafka/EKS versions, UTC time, environment, expected/observed plan or validation, ownership map, policy outcome, Kafka quorum/ISR and client event IDs where relevant, risk, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Any apply, upgrade, state mutation or destructive test remains **Tabletop** without an approved disposable environment.

### Lab 04 — Separate environment states

**Procedure:** Check dev/stage/prod state boundaries and least-privilege deploy roles.

**Evidence:** Git revision, Terraform/provider/Strimzi/Kafka/EKS versions, UTC time, environment, expected/observed plan or validation, ownership map, policy outcome, Kafka quorum/ISR and client event IDs where relevant, risk, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Any apply, upgrade, state mutation or destructive test remains **Tabletop** without an approved disposable environment.

### Lab 05 — Validate Terraform provider constraints

**Procedure:** Check provider lockfile, plugin provenance, required_version and supported schemas.

**Evidence:** Git revision, Terraform/provider/Strimzi/Kafka/EKS versions, UTC time, environment, expected/observed plan or validation, ownership map, policy outcome, Kafka quorum/ISR and client event IDs where relevant, risk, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Any apply, upgrade, state mutation or destructive test remains **Tabletop** without an approved disposable environment.

### Lab 06 — Inspect EKS/Strimzi desired state

**Procedure:** Map Kubernetes namespace, operator, CRDs, Kafka and KafkaNodePools ownership.

**Evidence:** Git revision, Terraform/provider/Strimzi/Kafka/EKS versions, UTC time, environment, expected/observed plan or validation, ownership map, policy outcome, Kafka quorum/ISR and client event IDs where relevant, risk, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Any apply, upgrade, state mutation or destructive test remains **Tabletop** without an approved disposable environment.

### Lab 07 — Inspect MSK desired state

**Procedure:** Review VPC, subnets, security groups, broker config, encryption and monitoring.

**Evidence:** Git revision, Terraform/provider/Strimzi/Kafka/EKS versions, UTC time, environment, expected/observed plan or validation, ownership map, policy outcome, Kafka quorum/ISR and client event IDs where relevant, risk, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Any apply, upgrade, state mutation or destructive test remains **Tabletop** without an approved disposable environment.

### Lab 08 — Run formatting validation

**Procedure:** Run terraform fmt -check, terraform validate and static policy checks.

**Evidence:** Git revision, Terraform/provider/Strimzi/Kafka/EKS versions, UTC time, environment, expected/observed plan or validation, ownership map, policy outcome, Kafka quorum/ISR and client event IDs where relevant, risk, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Any apply, upgrade, state mutation or destructive test remains **Tabletop** without an approved disposable environment.

### Lab 09 — Produce isolated Terraform plan

**Procedure:** Use a safe disposable workspace and capture a redacted plan with drift.

**Evidence:** Git revision, Terraform/provider/Strimzi/Kafka/EKS versions, UTC time, environment, expected/observed plan or validation, ownership map, policy outcome, Kafka quorum/ISR and client event IDs where relevant, risk, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Any apply, upgrade, state mutation or destructive test remains **Tabletop** without an approved disposable environment.

### Lab 10 — Review plan for destructive actions

**Procedure:** Flag replace/destroy, broker upgrades, PVC deletion, security exposure and costs.

**Evidence:** Git revision, Terraform/provider/Strimzi/Kafka/EKS versions, UTC time, environment, expected/observed plan or validation, ownership map, policy outcome, Kafka quorum/ISR and client event IDs where relevant, risk, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Any apply, upgrade, state mutation or destructive test remains **Tabletop** without an approved disposable environment.

### Lab 11 — Validate secret-free code

**Procedure:** Check no passwords, certificates, tokens or private keys in Git or state output.

**Evidence:** Git revision, Terraform/provider/Strimzi/Kafka/EKS versions, UTC time, environment, expected/observed plan or validation, ownership map, policy outcome, Kafka quorum/ISR and client event IDs where relevant, risk, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Any apply, upgrade, state mutation or destructive test remains **Tabletop** without an approved disposable environment.

### Lab 12 — Validate Kubernetes manifests

**Procedure:** Use server-side dry-run or installed CRD schema in disposable namespace.

**Evidence:** Git revision, Terraform/provider/Strimzi/Kafka/EKS versions, UTC time, environment, expected/observed plan or validation, ownership map, policy outcome, Kafka quorum/ISR and client event IDs where relevant, risk, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Any apply, upgrade, state mutation or destructive test remains **Tabletop** without an approved disposable environment.

### Lab 13 — Check GitOps source ownership

**Procedure:** Ensure Argo CD/Flux owns CRs, not generated Strimzi Pods or PVCs.

**Evidence:** Git revision, Terraform/provider/Strimzi/Kafka/EKS versions, UTC time, environment, expected/observed plan or validation, ownership map, policy outcome, Kafka quorum/ISR and client event IDs where relevant, risk, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Any apply, upgrade, state mutation or destructive test remains **Tabletop** without an approved disposable environment.

### Lab 14 — Validate deployment dependency order

**Procedure:** Confirm CRDs/operator before Kafka CRs, KafkaNodePools, users and topics.

**Evidence:** Git revision, Terraform/provider/Strimzi/Kafka/EKS versions, UTC time, environment, expected/observed plan or validation, ownership map, policy outcome, Kafka quorum/ISR and client event IDs where relevant, risk, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Any apply, upgrade, state mutation or destructive test remains **Tabletop** without an approved disposable environment.

### Lab 15 — Review policy-as-code

**Procedure:** Check admission/CI rules for TLS, IAM, RF/minISR, deletion and cost.

**Evidence:** Git revision, Terraform/provider/Strimzi/Kafka/EKS versions, UTC time, environment, expected/observed plan or validation, ownership map, policy outcome, Kafka quorum/ISR and client event IDs where relevant, risk, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Any apply, upgrade, state mutation or destructive test remains **Tabletop** without an approved disposable environment.

### Lab 16 — Validate promotion gates

**Procedure:** Compare immutable Git revision across lab/staging/prod with approvals.

**Evidence:** Git revision, Terraform/provider/Strimzi/Kafka/EKS versions, UTC time, environment, expected/observed plan or validation, ownership map, policy outcome, Kafka quorum/ISR and client event IDs where relevant, risk, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Any apply, upgrade, state mutation or destructive test remains **Tabletop** without an approved disposable environment.

### Lab 17 — Validate drift handling

**Procedure:** Classify Terraform drift vs GitOps reconciliation and avoid fighting controllers.

**Evidence:** Git revision, Terraform/provider/Strimzi/Kafka/EKS versions, UTC time, environment, expected/observed plan or validation, ownership map, policy outcome, Kafka quorum/ISR and client event IDs where relevant, risk, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Any apply, upgrade, state mutation or destructive test remains **Tabletop** without an approved disposable environment.

### Lab 18 — Design rollback and recovery

**Procedure:** Separate reversible manifest edits from irreversible Kafka state changes.

**Evidence:** Git revision, Terraform/provider/Strimzi/Kafka/EKS versions, UTC time, environment, expected/observed plan or validation, ownership map, policy outcome, Kafka quorum/ISR and client event IDs where relevant, risk, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Any apply, upgrade, state mutation or destructive test remains **Tabletop** without an approved disposable environment.

### Lab 19 — Plan post-deploy Kafka smoke

**Procedure:** Define KRaft quorum, ISR, authenticated produce/consume, lag and event IDs.

**Evidence:** Git revision, Terraform/provider/Strimzi/Kafka/EKS versions, UTC time, environment, expected/observed plan or validation, ownership map, policy outcome, Kafka quorum/ISR and client event IDs where relevant, risk, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Any apply, upgrade, state mutation or destructive test remains **Tabletop** without an approved disposable environment.

### Lab 20 — Independent pipeline acceptance

**Procedure:** Reconcile CI logs, approvals, security, evidence, rollback and reviewer.

**Evidence:** Git revision, Terraform/provider/Strimzi/Kafka/EKS versions, UTC time, environment, expected/observed plan or validation, ownership map, policy outcome, Kafka quorum/ISR and client event IDs where relevant, risk, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Any apply, upgrade, state mutation or destructive test remains **Tabletop** without an approved disposable environment.

## 12. Read-only local/Kubernetes verification script

Save as `verify-ch76.sh` and run only with a reviewed Terraform working directory and Kubernetes context.

```bash
#!/usr/bin/env bash
set -euo pipefail
: "${TF_DIR:?Set Terraform module directory}"
echo '[1/9] Terraform version'; terraform version
echo '[2/9] Terraform formatting'; terraform -chdir="$TF_DIR" fmt -check
echo '[3/9] Terraform init (no backend)'; terraform -chdir="$TF_DIR" init -backend=false
echo '[4/9] Terraform validation'; terraform -chdir="$TF_DIR" validate
echo '[5/9] Kubernetes context'; kubectl config current-context
echo '[6/9] Strimzi CRDs'; kubectl get crd | grep -E 'kafkas.kafka.strimzi.io|kafkanodepools.kafka.strimzi.io' || true
echo '[7/9] Operator'; kubectl get deploy -A | grep -i strimzi || true
echo '[8/9] Kafka CRs'; kubectl get kafka,kafkanodepool -A || true
echo '[9/9] Kafka workloads'; kubectl get pods -A -l strimzi.io/kind=Kafka || true
echo 'PASS: local configuration validation and read-only K8s inventory only.'
echo 'NOT PROVEN: remote state, Terraform plan safety, Kafka health, client SLO or security review.'
```

A successful local validation does not certify AWS IAM, backend security, plan correctness or Kafka durability. If `terraform init` cannot install providers in a restricted environment, record that as **Not Executed/Blocked**, not pass.

## 13. Twelve automation failure scenarios

### Scenario 1 — Terraform plan wants to replace MSK cluster

**Diagnosis:** Inspect ForceNew attributes, provider/version drift and approved change scope. Correlate Git revision, Terraform plan/state, AWS MSK operations, Argo/Flux sync, Strimzi reconciliation, Kafka quorum/ISR, EKS TLS/IAM client errors and synthetic event IDs. **Response:** Stop unsafe automation, protect Kafka data and credentials, escalate and apply reviewed recovery. **Exit:** Proven SLO, sanitized evidence, RCA and independent reviewer.

### Scenario 2 — Terraform state lock contention

**Diagnosis:** Check active runner, lock owner and safe recovery; never force-unlock blindly. Correlate Git revision, Terraform plan/state, AWS MSK operations, Argo/Flux sync, Strimzi reconciliation, Kafka quorum/ISR, EKS TLS/IAM client errors and synthetic event IDs. **Response:** Stop unsafe automation, protect Kafka data and credentials, escalate and apply reviewed recovery. **Exit:** Proven SLO, sanitized evidence, RCA and independent reviewer.

### Scenario 3 — Secrets appear in Terraform state

**Diagnosis:** Contain exposure, rotate credentials and restrict state access. Correlate Git revision, Terraform plan/state, AWS MSK operations, Argo/Flux sync, Strimzi reconciliation, Kafka quorum/ISR, EKS TLS/IAM client errors and synthetic event IDs. **Response:** Stop unsafe automation, protect Kafka data and credentials, escalate and apply reviewed recovery. **Exit:** Proven SLO, sanitized evidence, RCA and independent reviewer.

### Scenario 4 — GitOps and Terraform fight over same CR

**Diagnosis:** Assign single owner per resource, reconcile field ownership and remove conflict. Correlate Git revision, Terraform plan/state, AWS MSK operations, Argo/Flux sync, Strimzi reconciliation, Kafka quorum/ISR, EKS TLS/IAM client errors and synthetic event IDs. **Response:** Stop unsafe automation, protect Kafka data and credentials, escalate and apply reviewed recovery. **Exit:** Proven SLO, sanitized evidence, RCA and independent reviewer.

### Scenario 5 — Strimzi CRD unavailable during sync

**Diagnosis:** Check operator installation order, schema and readiness. Correlate Git revision, Terraform plan/state, AWS MSK operations, Argo/Flux sync, Strimzi reconciliation, Kafka quorum/ISR, EKS TLS/IAM client errors and synthetic event IDs. **Response:** Stop unsafe automation, protect Kafka data and credentials, escalate and apply reviewed recovery. **Exit:** Proven SLO, sanitized evidence, RCA and independent reviewer.

### Scenario 6 — Argo CD reports healthy but Kafka ISR degraded

**Diagnosis:** Gate on Kafka quorum, ISR, client correctness, not GitOps status alone. Correlate Git revision, Terraform plan/state, AWS MSK operations, Argo/Flux sync, Strimzi reconciliation, Kafka quorum/ISR, EKS TLS/IAM client errors and synthetic event IDs. **Response:** Stop unsafe automation, protect Kafka data and credentials, escalate and apply reviewed recovery. **Exit:** Proven SLO, sanitized evidence, RCA and independent reviewer.

### Scenario 7 — MSK change blocked by API state

**Diagnosis:** Inspect AWS operation, cluster version, cooldown and support constraints. Correlate Git revision, Terraform plan/state, AWS MSK operations, Argo/Flux sync, Strimzi reconciliation, Kafka quorum/ISR, EKS TLS/IAM client errors and synthetic event IDs. **Response:** Stop unsafe automation, protect Kafka data and credentials, escalate and apply reviewed recovery. **Exit:** Proven SLO, sanitized evidence, RCA and independent reviewer.

### Scenario 8 — CI role has broad production permissions

**Diagnosis:** Restrict IAM/Kubernetes RBAC, isolate environments and require approval. Correlate Git revision, Terraform plan/state, AWS MSK operations, Argo/Flux sync, Strimzi reconciliation, Kafka quorum/ISR, EKS TLS/IAM client errors and synthetic event IDs. **Response:** Stop unsafe automation, protect Kafka data and credentials, escalate and apply reviewed recovery. **Exit:** Proven SLO, sanitized evidence, RCA and independent reviewer.

### Scenario 9 — Drift detection proposes PVC deletion

**Diagnosis:** Freeze plan/prune, preserve data and audit ownership. Correlate Git revision, Terraform plan/state, AWS MSK operations, Argo/Flux sync, Strimzi reconciliation, Kafka quorum/ISR, EKS TLS/IAM client errors and synthetic event IDs. **Response:** Stop unsafe automation, protect Kafka data and credentials, escalate and apply reviewed recovery. **Exit:** Proven SLO, sanitized evidence, RCA and independent reviewer.

### Scenario 10 — Provider upgrade changes plan unexpectedly

**Diagnosis:** Review lockfile, schema migrations, release notes and state backup. Correlate Git revision, Terraform plan/state, AWS MSK operations, Argo/Flux sync, Strimzi reconciliation, Kafka quorum/ISR, EKS TLS/IAM client errors and synthetic event IDs. **Response:** Stop unsafe automation, protect Kafka data and credentials, escalate and apply reviewed recovery. **Exit:** Proven SLO, sanitized evidence, RCA and independent reviewer.

### Scenario 11 — Rollback restores Git but not Kafka data

**Diagnosis:** Classify irreversible partition/metadata/storage changes and invoke recovery. Correlate Git revision, Terraform plan/state, AWS MSK operations, Argo/Flux sync, Strimzi reconciliation, Kafka quorum/ISR, EKS TLS/IAM client errors and synthetic event IDs. **Response:** Stop unsafe automation, protect Kafka data and credentials, escalate and apply reviewed recovery. **Exit:** Proven SLO, sanitized evidence, RCA and independent reviewer.

### Scenario 12 — Pipeline passes but clients cannot authenticate

**Diagnosis:** Inspect EKS identity, TLS/IAM/SCRAM, ACL and event ledger. Correlate Git revision, Terraform plan/state, AWS MSK operations, Argo/Flux sync, Strimzi reconciliation, Kafka quorum/ISR, EKS TLS/IAM client errors and synthetic event IDs. **Response:** Stop unsafe automation, protect Kafka data and credentials, escalate and apply reviewed recovery. **Exit:** Proven SLO, sanitized evidence, RCA and independent reviewer.

## 14. Eight production runbooks

### Runbook A — Terraform plan or state incident

**Trigger/response:** Stop apply, inspect state/lock, review drift and restore approved plan. **No-go:** unreviewed destroy/prune, force-unlock, credential exposure, lost ISR, unapproved AWS cost, unsupported upgrade or unknown data correctness. **Exit:** Reviewed desired state, healthy Kafka, authenticated client smoke, stable state ownership and signoff.

### Runbook B — GitOps/Strimzi reconciliation failure

**Trigger/response:** Check CRD/operator readiness, ownership, Kafka CR conditions and safe sync. **No-go:** unreviewed destroy/prune, force-unlock, credential exposure, lost ISR, unapproved AWS cost, unsupported upgrade or unknown data correctness. **Exit:** Reviewed desired state, healthy Kafka, authenticated client smoke, stable state ownership and signoff.

### Runbook C — MSK IaC change incident

**Trigger/response:** Inspect AWS operation, VPC/IAM/config changes, ISR and EKS clients. **No-go:** unreviewed destroy/prune, force-unlock, credential exposure, lost ISR, unapproved AWS cost, unsupported upgrade or unknown data correctness. **Exit:** Reviewed desired state, healthy Kafka, authenticated client smoke, stable state ownership and signoff.

### Runbook D — Secret leakage in CI/state

**Trigger/response:** Revoke/rotate, quarantine artifacts, audit access and security escalation. **No-go:** unreviewed destroy/prune, force-unlock, credential exposure, lost ISR, unapproved AWS cost, unsupported upgrade or unknown data correctness. **Exit:** Reviewed desired state, healthy Kafka, authenticated client smoke, stable state ownership and signoff.

### Runbook E — Unsafe destroy/prune prevention

**Trigger/response:** Freeze automation, preserve PVC/Kafka state and require reviewed recovery. **No-go:** unreviewed destroy/prune, force-unlock, credential exposure, lost ISR, unapproved AWS cost, unsupported upgrade or unknown data correctness. **Exit:** Reviewed desired state, healthy Kafka, authenticated client smoke, stable state ownership and signoff.

### Runbook F — Failed progressive deployment

**Trigger/response:** Stop promotion, check SLO/quorum/ISR, revert only safe changes. **No-go:** unreviewed destroy/prune, force-unlock, credential exposure, lost ISR, unapproved AWS cost, unsupported upgrade or unknown data correctness. **Exit:** Reviewed desired state, healthy Kafka, authenticated client smoke, stable state ownership and signoff.

### Runbook G — Post-deploy Kafka client outage

**Trigger/response:** Trace DNS, TLS/IAM/ACL, Kafka ISR, group lag and synthetic event IDs. **No-go:** unreviewed destroy/prune, force-unlock, credential exposure, lost ISR, unapproved AWS cost, unsupported upgrade or unknown data correctness. **Exit:** Reviewed desired state, healthy Kafka, authenticated client smoke, stable state ownership and signoff.

### Runbook H — Independent automation acceptance

**Trigger/response:** Review plan provenance, policy checks, signed approval, recovery and signoff. **No-go:** unreviewed destroy/prune, force-unlock, credential exposure, lost ISR, unapproved AWS cost, unsupported upgrade or unknown data correctness. **Exit:** Reviewed desired state, healthy Kafka, authenticated client smoke, stable state ownership and signoff.

## 15. Evidence bundle

```text
evidence-ch76/
  architecture-raci.md
  pinned-toolchain.md
  remote-state-security.md
  environment-isolation.md
  provider-lockfile.md
  strimzi-ownership.md
  msk-terraform-review.md
  fmt-validate-policy.md
  redacted-plan-review.md
  destructive-action-gate.md
  secrets-scan.md
  crd-schema-validation.md
  gitops-ownership.md
  deployment-dependencies.md
  policy-as-code.md
  promotion-approvals.md
  drift-analysis.md
  rollback-recovery.md
  kafka-client-smoke.md
  independent-acceptance.md
  scorecard.md
```

Each artifact requires UTC time, exact toolchain versions, Git revision, expected/observed result, **Live** vs **Tabletop**, sanitized output, owner, risk/rollback and independent reviewer.

## 16. 100-point automation reliability assessment

| Domain | Points | Critical |
|---|---:|---|
| Terraform state, provider and environment isolation | 20 | Yes |
| Kafka/Strimzi/MSK resource ownership and dependencies | 20 | Yes |
| CI validation, policy and secret protection | 20 | Yes |
| Progressive promotion, drift and rollback safety | 20 | Yes |
| Kafka SLO, quorum/ISR and client correctness | 15 | Yes |
| Independent technical/security review | 5 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 and all critical gates independently evidenced. **Automatic Fail:** fabricated live evidence, leaked credentials/state, unapproved destructive plan, Terraform/GitOps ownership conflict causing data loss, lost ISR without abort or missing independent review.

## 17. References and next chapter

**References:** [Terraform Documentation](https://developer.hashicorp.com/terraform/docs), [Strimzi](https://strimzi.io/documentation/), [Argo CD](https://argo-cd.readthedocs.io/), [Flux](https://fluxcd.io/flux/), [Amazon MSK](https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html), [Kubernetes](https://kubernetes.io/docs/).

**Next:** Chapter 077 — Kafka CI/CD Pipelines, Policy-as-Code, Security Scanning and Progressive Delivery.

---

**Verification boundary:** Chapter publication proves document availability only. Live Terraform plans, CI policy runs, GitOps reconciliation, Kafka client smoke and independent technical/security review remain Pending.
