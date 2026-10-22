# Chapter 080 — Kafka Enterprise Automation, GitOps, CI/CD and Reliability Acceptance Capstone

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 16 — Automation, Terraform and CI/CD (5/5; capstone)  
**Primary platform:** Kubernetes + Strimzi Kafka in KRaft mode; Terraform-managed AWS/EKS/MSK where applicable  
**Prerequisites:** Chapters 001–079, particularly 076–079  
**Publication:** Published · **Live lab execution:** Pending · **Independent technical/security review:** Pending

> **Production safety:** All destructive KafkaTopic, KafkaNodePool, PVC, Terraform apply/destroy, MSK changes, secret rotation and failover activities are **Tabletop** until approved in an isolated disposable environment. Never assume a Git revert restores Kafka records, offsets, partition count or broker metadata. Publishing this chapter does not certify the pipeline or its labs.

## 1. Capstone mission and acceptance contract

Prove the enterprise delivery system is **safe, observable, reproducible and recoverable**. Integrate Terraform cloud infrastructure, GitLab/GitHub CI, OPA/Kyverno, supply-chain scanning, Argo CD/Flux GitOps, Strimzi operator reconciliation, Kafka KRaft quorum/ISR, authenticated EKS clients, change approvals, rollback limits, SLOs and compliance evidence.

The capstone is a **release-readiness assessment**, not a claim that production acceptance has occurred. Each required control needs a measured result, a reproducible evidence link, an accountable owner and independent review.

## 2. Architecture and responsibility boundaries

```text
Protected Git PR / CODEOWNERS / change ticket
                       |
         immutable commit + runner identity
                       |
  lint -> unit -> Terraform plan -> OPA/Kyverno
                       |
      secret/IaC/image/SBOM policy scans
                       |
       reviewed environment promotion
                       |
         +-------------+-------------+
         |                           |
Terraform AWS/EKS/MSK          Argo CD or Flux
         |                           |
    cloud resources           Strimzi CRs
                                     |
                             Strimzi operator
                                     |
                         Kafka KRaft brokers/PVCs
         +-------------+-------------+
                       |
           authenticated EKS clients
                       |
         ISR + client SLO + event ledger
                       |
         alerts, audit, incident runbooks
                       |
           independent SRE/security gate
```

**Ownership:** Terraform manages explicitly selected infrastructure; GitOps manages explicitly selected Kafka/KafkaNodePool/KafkaTopic/KafkaUser desired-state CRs; Strimzi manages generated workloads; Kafka manages durable records, partitions and offsets. Do not configure two reconcilers for the same field. Cloud MSK may replace Strimzi but requires its own IAM/network/operation checks.

## 3. Reference repository structure

```text
kafka-platform/
  terraform/
    modules/{network,eks,msk,observability}/
    envs/{lab,staging,production}/
  kubernetes/
    base/{kafka,nodepools,topics,users,clients}/
    overlays/{lab,staging,production}/
  gitops/{argocd,flux}/
  policies/{opa,kyverno}/
  ci/{validate.sh,plan-review.sh}/
  tests/{policy,kafka-smoke}/
  evidence/ch080/
```

Pin provider and runner versions; use isolated remote states, short-lived OIDC roles and immutable image digests. Exclude `*.tfstate`, `tfplan`, credentials, TLS private keys and kubeconfig files from Git and public CI artifacts.

## 4. Capstone prerequisites and gates

| Gate | Evidence | Stop condition |
|---|---|---|
| Change identity | PR, ticket, CODEOWNERS, immutable SHA | no approval or untrusted runner |
| Terraform | fmt/validate, backend controls, redacted plan | destroy/replace without review |
| GitOps ownership | diff, owner matrix, prune policy | controller conflict |
| Strimzi compatibility | operator/CRD/Kafka versions, CR conditions | unsupported or degraded |
| Kafka durability | KRaft quorum, RF/minISR, ISR/offline partitions | quorum/ISR risk |
| Security | TLS/SASL/IAM, KafkaUser ACL, secret scan, negative tests | broad access or secret leak |
| Supply chain | SBOM, image digest, scan exceptions | unreviewed critical exposure |
| Release SLO | ack success, P95/P99 latency, freshness, lag | customer impact |
| Correctness | unique acknowledged event IDs reconciled | unexplained missing events |
| Recovery | reversible rollback and stateful recovery | unproven abort path |
| Compliance | audit timeline, evidence retention and access | missing provenance |
| Independent review | platform/SRE/security signatures | any critical unsigned gate |

All quantitative targets must be approved for the environment. Never report an assumed target as a measured SLO.

## 5. Plan-only Terraform verification

```bash
terraform version
terraform -chdir=terraform/envs/lab fmt -check
terraform -chdir=terraform/envs/lab init -backend=false
terraform -chdir=terraform/envs/lab validate
```

For an **approved isolated backend**, a read-only planning workflow can use:

```bash
terraform -chdir=terraform/envs/lab init -lockfile=readonly
terraform -chdir=terraform/envs/lab plan -input=false -out=tfplan
terraform -chdir=terraform/envs/lab show -json tfplan > tfplan.json
```

`tfplan` and JSON may include sensitive values. Restrict access, redact summary and retain only as approved. Review `resource_changes[].change.actions` for delete/replace and inspect state ownership. **Do not apply** as part of this chapter.

## 6. Policy-as-code and security acceptance

Minimum fail-closed rules:

- Reject plaintext Kafka listeners, anonymous/wildcard administrative ACLs and unapproved network exposure.
- Reject unsafe RF/minISR for the declared fault domain and producer `acks` contract.
- Reject KafkaTopic deletion, KafkaNodePool/PVC pruning and unapproved broker/storage changes.
- Reject Terraform destroy/replace of stateful Kafka infrastructure without separate change control.
- Require secret scanning, image/SBOM policy, signed provenance where configured and protected approvals.
- Test **negative fixtures** (unsafe TLS, ACL, deletion and missing required fields); a policy that passes only good inputs is not accepted.

Do not use generic admission policies against unverified Strimzi CRD paths; test on the exact installed operator version.

## 7. GitOps and Strimzi reconciliation acceptance

```bash
kubectl config current-context
kubectl get crd | grep -E 'kafkas.kafka.strimzi.io|kafkanodepools.kafka.strimzi.io'
kubectl get kafka,kafkanodepool,kafkatopic,kafkauser -A
kubectl get pods,pvc -A -l strimzi.io/kind=Kafka
```

Inspect Argo CD/Flux diff, sync history, expected controller-managed fields, Strimzi `observedGeneration` and CR readiness. A healthy GitOps Application is not a Kafka health test. No automatic prune of stateful Kafka resources without independent authorization and recovery evidence.

## 8. Kafka durability and EKS client smoke

Record topic RF, minISR, leader/replica placement, current ISR, offline partitions, KRaft controller quorum, disk headroom and client authentication path. Synthetic smoke must:

1. Authenticate from an approved EKS workload identity over TLS.
2. Produce unique synthetic event IDs and wait for broker acknowledgments.
3. Capture topic, partition, offset and UTC acknowledgment timestamp.
4. Consume with an approved group and measure processing/freshness.
5. Reconcile expected acknowledged IDs with processed IDs, recording duplicates and gaps.
6. Correlate results with Git SHA, canary cohort, broker health and alert state.
7. Fail promotion on unexplained missing records or degraded ISR/quorum.

Kubernetes Pod readiness and CI success do not establish data correctness.

## 9. Progressive release and abort decision

Promote immutable Git SHA through lab -> staging -> approved production. At each stage require policy, scans, Terraform plan, GitOps reconciliation, Kafka durability, authenticated client smoke, error/latency/lag/freshness SLO and signed approval. A canary must be able to **stop** before full promotion.

**Rollback matrix:**

| Change | Normal rollback | Stateful warning |
|---|---|---|
| Client image/config | reviewed Git revert and rollout | verify client compatibility and event IDs |
| Alert rule | revert and re-test routing | alert gap may persist |
| KafkaUser/TLS policy | controlled restore | credential/cert rotation may need coordination |
| Topic retention | manual review | expired/deleted data not restored by Git |
| Partition increase | no automatic reverse | metadata and ordering change |
| KafkaNodePool/PVC | separate storage/quorum plan | data loss and unavailable brokers possible |
| Kafka/MSK upgrade | compatibility-specific recovery | downgrade may be unsupported |

## 10. Automation observability and audit

Record UTC change timeline, PR/ticket/approver, SHA, CI job ID, provider and operator versions, plan digest, policy/scan outcome, GitOps sync, Kafka quorum/ISR, EKS client event ledger, release markers, alert delivery and rollback/RCA.

Avoid high-cardinality Git SHA/event IDs as long-lived Prometheus labels; store these in structured logs or bounded audit tables. Restrict logs and artifacts containing sensitive identities or topic payloads.

## 11. Twenty enterprise acceptance labs

### Lab 01 — Approve capstone charter

**Objective and procedure:** Identify lab/stage/prod, Kafka business impact, owners, change board, SLO and recovery objectives.

**Expected validation:** Capture approved environment, UTC time, immutable SHA, pinned toolchain, expected/observed result, Kafka quorum/ISR or client SLO where applicable, negative-test result, sanitized evidence, rollback/abort decision and reviewer. **Status: Pending** until executed. Dangerous changes are **Tabletop** unless explicitly approved in a disposable cluster.

### Lab 02 — Pin versions and Git provenance

**Objective and procedure:** Capture Git SHA, Terraform providers, runner, Strimzi/KRaft, Kubernetes, Argo/Flux and Kafka clients.

**Expected validation:** Capture approved environment, UTC time, immutable SHA, pinned toolchain, expected/observed result, Kafka quorum/ISR or client SLO where applicable, negative-test result, sanitized evidence, rollback/abort decision and reviewer. **Status: Pending** until executed. Dangerous changes are **Tabletop** unless explicitly approved in a disposable cluster.

### Lab 03 — Audit Terraform state and IAM

**Objective and procedure:** Review encrypted remote state, locking, state access, environment isolation and OIDC trust.

**Expected validation:** Capture approved environment, UTC time, immutable SHA, pinned toolchain, expected/observed result, Kafka quorum/ISR or client SLO where applicable, negative-test result, sanitized evidence, rollback/abort decision and reviewer. **Status: Pending** until executed. Dangerous changes are **Tabletop** unless explicitly approved in a disposable cluster.

### Lab 04 — Inspect IaC plan safety

**Objective and procedure:** Validate fmt/init/validate, plan provenance, replace/destroy flags, cost and approvals.

**Expected validation:** Capture approved environment, UTC time, immutable SHA, pinned toolchain, expected/observed result, Kafka quorum/ISR or client SLO where applicable, negative-test result, sanitized evidence, rollback/abort decision and reviewer. **Status: Pending** until executed. Dangerous changes are **Tabletop** unless explicitly approved in a disposable cluster.

### Lab 05 — Verify single-controller ownership

**Objective and procedure:** Map Terraform cloud/EKS/MSK, GitOps CRs and Strimzi-generated workload boundaries.

**Expected validation:** Capture approved environment, UTC time, immutable SHA, pinned toolchain, expected/observed result, Kafka quorum/ISR or client SLO where applicable, negative-test result, sanitized evidence, rollback/abort decision and reviewer. **Status: Pending** until executed. Dangerous changes are **Tabletop** unless explicitly approved in a disposable cluster.

### Lab 06 — Validate CRD/operator dependencies

**Objective and procedure:** Check installed Strimzi CRDs, version compatibility, Kafka/KafkaNodePool reconciliation order.

**Expected validation:** Capture approved environment, UTC time, immutable SHA, pinned toolchain, expected/observed result, Kafka quorum/ISR or client SLO where applicable, negative-test result, sanitized evidence, rollback/abort decision and reviewer. **Status: Pending** until executed. Dangerous changes are **Tabletop** unless explicitly approved in a disposable cluster.

### Lab 07 — Review Kafka safety policies

**Objective and procedure:** Test RF/minISR, TLS, KafkaUser ACL, deletion/prune and storage policy negative fixtures.

**Expected validation:** Capture approved environment, UTC time, immutable SHA, pinned toolchain, expected/observed result, Kafka quorum/ISR or client SLO where applicable, negative-test result, sanitized evidence, rollback/abort decision and reviewer. **Status: Pending** until executed. Dangerous changes are **Tabletop** unless explicitly approved in a disposable cluster.

### Lab 08 — Validate secrets and supply chain

**Objective and procedure:** Review OIDC identity, Gitleaks, IaC scanner, image digest, SBOM, CVE exceptions and artifact retention.

**Expected validation:** Capture approved environment, UTC time, immutable SHA, pinned toolchain, expected/observed result, Kafka quorum/ISR or client SLO where applicable, negative-test result, sanitized evidence, rollback/abort decision and reviewer. **Status: Pending** until executed. Dangerous changes are **Tabletop** unless explicitly approved in a disposable cluster.

### Lab 09 — Audit CI required gates

**Objective and procedure:** Confirm no skipped/allow-failure security job, protected environment and approver separation.

**Expected validation:** Capture approved environment, UTC time, immutable SHA, pinned toolchain, expected/observed result, Kafka quorum/ISR or client SLO where applicable, negative-test result, sanitized evidence, rollback/abort decision and reviewer. **Status: Pending** until executed. Dangerous changes are **Tabletop** unless explicitly approved in a disposable cluster.

### Lab 10 — Inspect GitOps drift and alerting

**Objective and procedure:** Capture Argo/Flux diff, expected controller fields, drift age, reconciliation failures and owners.

**Expected validation:** Capture approved environment, UTC time, immutable SHA, pinned toolchain, expected/observed result, Kafka quorum/ISR or client SLO where applicable, negative-test result, sanitized evidence, rollback/abort decision and reviewer. **Status: Pending** until executed. Dangerous changes are **Tabletop** unless explicitly approved in a disposable cluster.

### Lab 11 — Verify KRaft quorum and ISR

**Objective and procedure:** Review controller quorum, partition replicas, under-replicated/offline partitions and broker headroom.

**Expected validation:** Capture approved environment, UTC time, immutable SHA, pinned toolchain, expected/observed result, Kafka quorum/ISR or client SLO where applicable, negative-test result, sanitized evidence, rollback/abort decision and reviewer. **Status: Pending** until executed. Dangerous changes are **Tabletop** unless explicitly approved in a disposable cluster.

### Lab 12 — Validate EKS client connectivity

**Objective and procedure:** Test approved identity, TLS, DNS, ACL, broker metadata and authenticated client readiness.

**Expected validation:** Capture approved environment, UTC time, immutable SHA, pinned toolchain, expected/observed result, Kafka quorum/ISR or client SLO where applicable, negative-test result, sanitized evidence, rollback/abort decision and reviewer. **Status: Pending** until executed. Dangerous changes are **Tabletop** unless explicitly approved in a disposable cluster.

### Lab 13 — Reconcile synthetic event ledger

**Objective and procedure:** Design producer acknowledgments, consumer processed IDs, lag, duplicates and missing events.

**Expected validation:** Capture approved environment, UTC time, immutable SHA, pinned toolchain, expected/observed result, Kafka quorum/ISR or client SLO where applicable, negative-test result, sanitized evidence, rollback/abort decision and reviewer. **Status: Pending** until executed. Dangerous changes are **Tabletop** unless explicitly approved in a disposable cluster.

### Lab 14 — Exercise canary gates

**Objective and procedure:** Plan staging/canary latency, error, freshness, ISR and correctness abort thresholds.

**Expected validation:** Capture approved environment, UTC time, immutable SHA, pinned toolchain, expected/observed result, Kafka quorum/ISR or client SLO where applicable, negative-test result, sanitized evidence, rollback/abort decision and reviewer. **Status: Pending** until executed. Dangerous changes are **Tabletop** unless explicitly approved in a disposable cluster.

### Lab 15 — Rehearse safe rollback

**Objective and procedure:** Revert a reversible client config in isolated lab; document Kafka metadata/data limits.

**Expected validation:** Capture approved environment, UTC time, immutable SHA, pinned toolchain, expected/observed result, Kafka quorum/ISR or client SLO where applicable, negative-test result, sanitized evidence, rollback/abort decision and reviewer. **Status: Pending** until executed. Dangerous changes are **Tabletop** unless explicitly approved in a disposable cluster.

### Lab 16 — Rehearse unsafe prune prevention

**Objective and procedure:** Tabletop KafkaTopic, KafkaNodePool and PVC deletion denial with evidence.

**Expected validation:** Capture approved environment, UTC time, immutable SHA, pinned toolchain, expected/observed result, Kafka quorum/ISR or client SLO where applicable, negative-test result, sanitized evidence, rollback/abort decision and reviewer. **Status: Pending** until executed. Dangerous changes are **Tabletop** unless explicitly approved in a disposable cluster.

### Lab 17 — Rehearse drift break-glass

**Objective and procedure:** Tabletop suspension, audit, emergency repair, Git reconciliation and safe resume.

**Expected validation:** Capture approved environment, UTC time, immutable SHA, pinned toolchain, expected/observed result, Kafka quorum/ISR or client SLO where applicable, negative-test result, sanitized evidence, rollback/abort decision and reviewer. **Status: Pending** until executed. Dangerous changes are **Tabletop** unless explicitly approved in a disposable cluster.

### Lab 18 — Validate release observability

**Objective and procedure:** Correlate immutable SHA, pipeline telemetry, Terraform plan, GitOps sync, Kafka and client SLO.

**Expected validation:** Capture approved environment, UTC time, immutable SHA, pinned toolchain, expected/observed result, Kafka quorum/ISR or client SLO where applicable, negative-test result, sanitized evidence, rollback/abort decision and reviewer. **Status: Pending** until executed. Dangerous changes are **Tabletop** unless explicitly approved in a disposable cluster.

### Lab 19 — Reconstruct audit and incident timeline

**Objective and procedure:** Collect approval, policy, scans, deploy, alert, incident, mitigation, recovery and RCA.

**Expected validation:** Capture approved environment, UTC time, immutable SHA, pinned toolchain, expected/observed result, Kafka quorum/ISR or client SLO where applicable, negative-test result, sanitized evidence, rollback/abort decision and reviewer. **Status: Pending** until executed. Dangerous changes are **Tabletop** unless explicitly approved in a disposable cluster.

### Lab 20 — Obtain independent acceptance

**Objective and procedure:** Complete 100-point rubric, record critical failures, open remediation and SRE/security signoff.

**Expected validation:** Capture approved environment, UTC time, immutable SHA, pinned toolchain, expected/observed result, Kafka quorum/ISR or client SLO where applicable, negative-test result, sanitized evidence, rollback/abort decision and reviewer. **Status: Pending** until executed. Dangerous changes are **Tabletop** unless explicitly approved in a disposable cluster.

## 12. Read-only acceptance preflight

Save as `verify-ch80.sh`. Requires Terraform and kubectl plus an approved Strimzi context; **no deployment occurs**.

```bash
#!/usr/bin/env bash
set -euo pipefail
: "${TF_DIR:?Set existing Terraform module path}"
echo '[1/10] Git revision'; git rev-parse HEAD
echo '[2/10] Terraform version'; terraform version
echo '[3/10] Terraform formatting'; terraform -chdir="$TF_DIR" fmt -check
echo '[4/10] Terraform init without backend'; terraform -chdir="$TF_DIR" init -backend=false
echo '[5/10] Terraform validate'; terraform -chdir="$TF_DIR" validate
echo '[6/10] Kubernetes context'; kubectl config current-context
echo '[7/10] Kafka CRs'; kubectl get kafka -A
echo '[8/10] Node pools'; kubectl get kafkanodepool -A
echo '[9/10] Topics and users'; kubectl get kafkatopic,kafkauser -A
echo '[10/10] Kafka Pods'; kubectl get pods -A -l strimzi.io/kind=Kafka
echo 'PASS: local IaC validation and read-only Strimzi inventory only.'
echo 'NOT PROVEN: remote state, CI policy, security scan, quorum/ISR, event correctness or independent review.'
```

For MSK-only environments, replace Strimzi inventory with approved read-only AWS MSK and EKS checks; document **Not Applicable** rather than claiming Strimzi validation. `init -backend=false` may still install providers and modify local `.terraform` cache, but does not touch remote backend state.

## 13. Twelve integrated failure scenarios

### Scenario 01 — CI passed despite skipped mandatory policy

**Diagnosis:** Fail closed; audit needs/rules/allow_failure and branch protection. Cross-check Git SHA, CI identity, Terraform plan/state, GitOps diff, Strimzi CR conditions, Kafka KRaft quorum/ISR and synthetic client event IDs. **Response:** Freeze unsafe promotion, preserve data and sanitized audit trail, contain any identity exposure, and use an approved runbook. **Exit:** Restored Kafka client SLO, verified event correctness, RCA and independent review.

### Scenario 02 — Terraform plan proposes MSK replacement

**Diagnosis:** Freeze, review ForceNew/drift, approved migration and state integrity. Cross-check Git SHA, CI identity, Terraform plan/state, GitOps diff, Strimzi CR conditions, Kafka KRaft quorum/ISR and synthetic client event IDs. **Response:** Freeze unsafe promotion, preserve data and sanitized audit trail, contain any identity exposure, and use an approved runbook. **Exit:** Restored Kafka client SLO, verified event correctness, RCA and independent review.

### Scenario 03 — GitOps and Terraform fight over a Kafka CR

**Diagnosis:** Suspend conflicting writers, assign one owner and reconcile safely. Cross-check Git SHA, CI identity, Terraform plan/state, GitOps diff, Strimzi CR conditions, Kafka KRaft quorum/ISR and synthetic client event IDs. **Response:** Freeze unsafe promotion, preserve data and sanitized audit trail, contain any identity exposure, and use an approved runbook. **Exit:** Restored Kafka client SLO, verified event correctness, RCA and independent review.

### Scenario 04 — Strimzi reconciles but KRaft quorum unhealthy

**Diagnosis:** Inspect controller quorum, Kafka CR conditions, node pools and storage. Cross-check Git SHA, CI identity, Terraform plan/state, GitOps diff, Strimzi CR conditions, Kafka KRaft quorum/ISR and synthetic client event IDs. **Response:** Freeze unsafe promotion, preserve data and sanitized audit trail, contain any identity exposure, and use an approved runbook. **Exit:** Restored Kafka client SLO, verified event correctness, RCA and independent review.

### Scenario 05 — GitOps prune removes topic manifest

**Diagnosis:** Block deletion, verify topic operator behavior and data preservation. Cross-check Git SHA, CI identity, Terraform plan/state, GitOps diff, Strimzi CR conditions, Kafka KRaft quorum/ISR and synthetic client event IDs. **Response:** Freeze unsafe promotion, preserve data and sanitized audit trail, contain any identity exposure, and use an approved runbook. **Exit:** Restored Kafka client SLO, verified event correctness, RCA and independent review.

### Scenario 06 — NodePool update threatens PVC/ISR

**Diagnosis:** Freeze scaling, assess quorum/minISR, backup and maintenance approval. Cross-check Git SHA, CI identity, Terraform plan/state, GitOps diff, Strimzi CR conditions, Kafka KRaft quorum/ISR and synthetic client event IDs. **Response:** Freeze unsafe promotion, preserve data and sanitized audit trail, contain any identity exposure, and use an approved runbook. **Exit:** Restored Kafka client SLO, verified event correctness, RCA and independent review.

### Scenario 07 — TLS/ACL policy incorrectly permits wildcard

**Diagnosis:** Review policy input and negative fixture; contain exposure. Cross-check Git SHA, CI identity, Terraform plan/state, GitOps diff, Strimzi CR conditions, Kafka KRaft quorum/ISR and synthetic client event IDs. **Response:** Freeze unsafe promotion, preserve data and sanitized audit trail, contain any identity exposure, and use an approved runbook. **Exit:** Restored Kafka client SLO, verified event correctness, RCA and independent review.

### Scenario 08 — Pipeline artifact exposes secrets

**Diagnosis:** Revoke, rotate, quarantine logs/state and escalate security. Cross-check Git SHA, CI identity, Terraform plan/state, GitOps diff, Strimzi CR conditions, Kafka KRaft quorum/ISR and synthetic client event IDs. **Response:** Freeze unsafe promotion, preserve data and sanitized audit trail, contain any identity exposure, and use an approved runbook. **Exit:** Restored Kafka client SLO, verified event correctness, RCA and independent review.

### Scenario 09 — Canary Pods ready but Kafka acks fail

**Diagnosis:** Inspect advertised brokers, IAM/SASL/TLS, ISR and client retries. Cross-check Git SHA, CI identity, Terraform plan/state, GitOps diff, Strimzi CR conditions, Kafka KRaft quorum/ISR and synthetic client event IDs. **Response:** Freeze unsafe promotion, preserve data and sanitized audit trail, contain any identity exposure, and use an approved runbook. **Exit:** Restored Kafka client SLO, verified event correctness, RCA and independent review.

### Scenario 10 — Consumer freshness degrades without alerts

**Diagnosis:** Check telemetry gaps, group lag, event IDs and alert routing. Cross-check Git SHA, CI identity, Terraform plan/state, GitOps diff, Strimzi CR conditions, Kafka KRaft quorum/ISR and synthetic client event IDs. **Response:** Freeze unsafe promotion, preserve data and sanitized audit trail, contain any identity exposure, and use an approved runbook. **Exit:** Restored Kafka client SLO, verified event correctness, RCA and independent review.

### Scenario 11 — Git revert cannot undo partition/offset change

**Diagnosis:** Invoke stateful recovery, reconcile records and consumer positions. Cross-check Git SHA, CI identity, Terraform plan/state, GitOps diff, Strimzi CR conditions, Kafka KRaft quorum/ISR and synthetic client event IDs. **Response:** Freeze unsafe promotion, preserve data and sanitized audit trail, contain any identity exposure, and use an approved runbook. **Exit:** Restored Kafka client SLO, verified event correctness, RCA and independent review.

### Scenario 12 — Audit cannot prove who approved release

**Diagnosis:** Block production promotion; reconstruct provenance and protected approvals. Cross-check Git SHA, CI identity, Terraform plan/state, GitOps diff, Strimzi CR conditions, Kafka KRaft quorum/ISR and synthetic client event IDs. **Response:** Freeze unsafe promotion, preserve data and sanitized audit trail, contain any identity exposure, and use an approved runbook. **Exit:** Restored Kafka client SLO, verified event correctness, RCA and independent review.

## 14. Eight production runbooks

### Runbook A — Release incident command

**Trigger and actions:** Freeze promotion, declare severity, preserve SHA/evidence, page Kafka/platform/security owners. **Stop/rollback criteria:** Kafka ISR/quorum loss, missing acknowledged events, security exposure, unreviewed state mutation or missing approval. **Exit evidence:** UTC incident timeline, affected SHA/environment, observed recovery, audit artifacts and reviewer signoff.

### Runbook B — Terraform state and destructive plan

**Trigger and actions:** Stop apply, inspect locking/plan, state backup, cost and independent approval. **Stop/rollback criteria:** Kafka ISR/quorum loss, missing acknowledged events, security exposure, unreviewed state mutation or missing approval. **Exit evidence:** UTC incident timeline, affected SHA/environment, observed recovery, audit artifacts and reviewer signoff.

### Runbook C — GitOps/Strimzi reconciliation outage

**Trigger and actions:** Inspect diff, owner, operator logs, CR status, quorum and ISR. **Stop/rollback criteria:** Kafka ISR/quorum loss, missing acknowledged events, security exposure, unreviewed state mutation or missing approval. **Exit evidence:** UTC incident timeline, affected SHA/environment, observed recovery, audit artifacts and reviewer signoff.

### Runbook D — Security policy or credential compromise

**Trigger and actions:** Fail closed, revoke/rotate, audit access and document containment. **Stop/rollback criteria:** Kafka ISR/quorum loss, missing acknowledged events, security exposure, unreviewed state mutation or missing approval. **Exit evidence:** UTC incident timeline, affected SHA/environment, observed recovery, audit artifacts and reviewer signoff.

### Runbook E — Canary or Kafka SLO breach

**Trigger and actions:** Stop rollout, assess producer acks, lag, ISR, event IDs and safe client rollback. **Stop/rollback criteria:** Kafka ISR/quorum loss, missing acknowledged events, security exposure, unreviewed state mutation or missing approval. **Exit evidence:** UTC incident timeline, affected SHA/environment, observed recovery, audit artifacts and reviewer signoff.

### Runbook F — KafkaTopic/NodePool/PVC data risk

**Trigger and actions:** Suspend prune, protect storage, evaluate Kafka metadata and recovery. **Stop/rollback criteria:** Kafka ISR/quorum loss, missing acknowledged events, security exposure, unreviewed state mutation or missing approval. **Exit evidence:** UTC incident timeline, affected SHA/environment, observed recovery, audit artifacts and reviewer signoff.

### Runbook G — Break-glass and drift repair

**Trigger and actions:** Record time-bound exception, patch only approved scope, merge Git and resume. **Stop/rollback criteria:** Kafka ISR/quorum loss, missing acknowledged events, security exposure, unreviewed state mutation or missing approval. **Exit evidence:** UTC incident timeline, affected SHA/environment, observed recovery, audit artifacts and reviewer signoff.

### Runbook H — Enterprise acceptance and RCA

**Trigger and actions:** Reconstruct timeline, score critical gates, track risks and obtain independent signatures. **Stop/rollback criteria:** Kafka ISR/quorum loss, missing acknowledged events, security exposure, unreviewed state mutation or missing approval. **Exit evidence:** UTC incident timeline, affected SHA/environment, observed recovery, audit artifacts and reviewer signoff.

## 15. Acceptance evidence package

```text
evidence-ch080/
  01-charter-slo-raci.md
  02-pinned-versions-git-sha.md
  03-terraform-state-iam.md
  04-terraform-plan-policy.md
  05-resource-ownership.md
  06-strimzi-compatibility.md
  07-policy-positive-negative.md
  08-secrets-sbom-supply-chain.md
  09-ci-required-gates.md
  10-gitops-drift.md
  11-kraft-isr.md
  12-eks-auth-connectivity.md
  13-synthetic-event-ledger.csv
  14-canary-slo.md
  15-reversible-rollback.md
  16-stateful-prune-tabletop.md
  17-break-glass-tabletop.md
  18-release-telemetry.md
  19-audit-incident-rca.md
  20-independent-signoff.md
  scorecard.md
```

Each artifact records UTC time, version, exact command/configuration, environment, expected and observed result, **Live** versus **Tabletop**, owner, sanitization, abort/rollback and independent reviewer. Empty placeholders are **Pending**, not passes.

## 16. 100-point enterprise reliability assessment

| Domain | Points | Critical |
|---|---:|---|
| Terraform state, IAM, versioning and plan safety | 15 | Yes |
| GitOps/Strimzi ownership, drift and prune safety | 15 | Yes |
| CI/CD policy, scans, provenance and approvals | 20 | Yes |
| Kafka quorum, ISR, client SLO and event correctness | 20 | Yes |
| Canary, rollback, break-glass and incident runbooks | 15 | Yes |
| Compliance, audit and observability evidence | 10 | Yes |
| Independent SRE/platform/security acceptance | 5 | Yes |
| **Total** | **100** | |

**Pass:** at least 85/100 **and** independently evidenced passing status for every critical gate, including representative live tests. **Automatic fail:** fabricated execution evidence, leaked secrets, bypassed mandatory controls, destructive KafkaTopic/PVC action without authorization, unreviewed controller conflict, degraded Kafka ISR without abort, unexplained missing acknowledged events, or missing independent review.

**Current acceptance status: Pending / Not Ready.** No live CI run, EKS-to-Kafka smoke, Terraform plan, canary or security assessment is claimed.

## 17. Final part checklist and transition

- Chapters 076–079 provide Terraform/IaC, CI/CD policy/security, GitOps drift/rollback and release observability.
- Chapter 080 integrates those controls into a single evidence-driven enterprise gate.
- **Part 16 is fully published (076–080).** Publication does not mean labs are runtime-certified.
- Open risks, live lab execution and independent technical/security review remain tracked separately.

**References:** [Terraform](https://developer.hashicorp.com/terraform/docs), [Strimzi](https://strimzi.io/documentation/), [Argo CD](https://argo-cd.readthedocs.io/), [Flux](https://fluxcd.io/flux/), [GitLab CI/CD](https://docs.gitlab.com/ci/), [OPA](https://www.openpolicyagent.org/docs), [Kyverno](https://kyverno.io/docs/), [Apache Kafka](https://kafka.apache.org/documentation/).

**Next:** Chapter 081 — Kafka Capacity Planning, Workload Forecasting and Reliability-Aware Scaling, beginning Part 17 — Capacity Planning, Performance and FinOps.

---

**Verification boundary:** Chapter publication confirms document availability only. Live integrated labs, policy negative tests, Kafka client correctness, release drills and independent technical/security review remain Pending.
