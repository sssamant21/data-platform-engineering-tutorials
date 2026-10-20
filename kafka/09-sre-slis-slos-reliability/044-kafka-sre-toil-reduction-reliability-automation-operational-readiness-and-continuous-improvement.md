# Chapter 044 — Kafka SRE Toil Reduction, Reliability Automation, Operational Readiness and Continuous Improvement

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 09 — SRE, SLIs, SLOs and Reliability (4/5)  
**Primary platform:** Kubernetes + Strimzi Operator + Kafka KRaft  
**Prerequisites:** Chapters 001–043, especially Chapters 036–043  
**Status:** Published · **Live lab execution:** Pending · **Independent technical/security review:** Pending

> **Safety:** Default to read-only automation in a disposable Kubernetes environment. Automation must never silently restart Kafka brokers/controllers, delete PVCs, modify KafkaTopic/KafkaUser/Kafka CRs, reset consumer offsets, expose Secrets, disable TLS/ACLs or bypass GitOps approvals. Never claim toil reduction without baseline and post-change measurement. All execution and security acceptance remain Pending.

## 1. Mission and outcomes

Reduce recurring Kafka SRE toil safely while improving reliability. Build a measurable toil inventory, identify low-risk read-only automation, design Kubernetes CronJobs and GitOps gates, apply least-privilege RBAC, produce SLO/capacity/health reports, prevent unapproved mutations, verify idempotency and partial failure, and establish operational readiness and continuous improvement practices.

By the end, learners can distinguish toil from engineering investment, rank automation by safety and return, design bounded and auditable Kubernetes jobs, validate Kafka/KRaft safety preconditions, and operate a reliability improvement backlog with owners and measurable outcomes.

## 2. Automation architecture

```text
Tickets / on-call pages / recurring manual checks
                      |
                      v
          Toil inventory + risk ranking
                      |
                      v
             GitOps-reviewed source
          lint + policy + peer approval
                      |
                      v
      Kubernetes CronJob / CI scheduled job
       scoped ServiceAccount + pinned image
       timeout + concurrency limit + resources
                      |
            read-only collection
             /              \
 Kafka CR + KRaft CLI      Prometheus + logs
             \              /
              v            v
             Report + evidence
             status: PASS / FAIL / UNKNOWN
                      |
             Owner review + ticket
                      |
         Human-approved remediation only
```

**Automation boundary:** Observing health and recommending actions is not the same as being authorized to mutate production state. A fail-closed system returns UNKNOWN when telemetry is missing and blocks changes until a human can validate safety.

## 3. Toil classification and prioritization

| Task | Frequency | Risk | First automation step | Human gate |
|---|---|---|---|---|
| Kafka Ready and quorum inventory | Daily | Low | Read-only report | Review anomalies |
| Topic RF/minISR audit | Weekly | Medium | Compare desired/observed | Approve any change |
| PVC capacity forecast | Daily | Low | Metric trend + alert | Approve storage change |
| Certificate expiry review | Daily | Medium | Expiry metadata only | Security approval for rotation |
| SLO/error-budget report | Daily | Low | Validated PromQL + ledger | Owner review |
| Runbook/alert link hygiene | Weekly | Low | Static checks | Approve routing change |
| Broker rolling restart | Rare | High | Runbook recommendation | Mandatory change approval |
| PVC deletion, offset reset, ACL modification | Rare | Critical | Never automatic in this curriculum | Separate authorized process |

**Toil estimate:** Weekly toil hours = event count × average manual minutes / 60. Compare baseline and post-change measurements over equivalent periods. Include automation maintenance, false positives, review time and incident cost; estimated savings are not observed savings.

## 4. Kubernetes CronJob security contract

An approved inventory CronJob should use a dedicated ServiceAccount, namespace-scoped Roles where possible, read-only get/list permissions, a pinned minimal image, `concurrencyPolicy: Forbid`, bounded `activeDeadlineSeconds`, CPU/memory limits, no privileged mode, read-only root filesystem, restricted network egress, and a short job history. If KRaft CLI requires Kafka client network access, use an approved TLS/SASL client identity and ACLs; **do not mount broker private keys**.

### Illustrative CronJob manifest

The following is a **review template**, not a ready-to-run image. Replace the image with an approved pinned digest and supply a tested script in the image or reviewed ConfigMap.

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: kafka-sre-readonly-inventory
  namespace: kafka-lab
spec:
  schedule: "0 8 * * *"
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 2
  failedJobsHistoryLimit: 2
  jobTemplate:
    spec:
      activeDeadlineSeconds: 300
      backoffLimit: 1
      template:
        spec:
          serviceAccountName: kafka-sre-readonly
          restartPolicy: Never
          securityContext:
            runAsNonRoot: true
            seccompProfile:
              type: RuntimeDefault
          containers:
            - name: inventory
              image: registry.example.invalid/approved/kubectl@sha256:REPLACE_WITH_APPROVED_DIGEST
              command: ["/bin/sh", "-ec"]
              args:
                - |
                  kubectl -n kafka-lab get kafka,kafkanodepool,pods,pvc -o wide
              resources:
                requests:
                  cpu: 50m
                  memory: 64Mi
                limits:
                  cpu: 250m
                  memory: 256Mi
              securityContext:
                allowPrivilegeEscalation: false
                readOnlyRootFilesystem: true
                capabilities:
                  drop: ["ALL"]
```

Do not deploy this example until a compatible image, read-only ServiceAccount, NetworkPolicy, image signature, security context and command have been validated. A CronJob does not automatically have RBAC to list Kafka CRDs.

## 5. Example least-privilege namespace Role

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: kafka-sre-readonly
  namespace: kafka-lab
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: kafka-sre-readonly
  namespace: kafka-lab
rules:
  - apiGroups: ["kafka.strimzi.io"]
    resources: ["kafkas", "kafkanodepools", "kafkatopics"]
    verbs: ["get", "list"]
  - apiGroups: [""]
    resources: ["pods", "persistentvolumeclaims", "events"]
    verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: kafka-sre-readonly
  namespace: kafka-lab
subjects:
  - kind: ServiceAccount
    name: kafka-sre-readonly
    namespace: kafka-lab
roleRef:
  kind: Role
  name: kafka-sre-readonly
  apiGroup: rbac.authorization.k8s.io
```

Validate using `kubectl auth can-i list kafkas.kafka.strimzi.io -n kafka-lab --as=system:serviceaccount:kafka-lab:kafka-sre-readonly` and explicit negative tests for `patch`, `delete`, `secrets` and `pods/exec`. Impersonation tests require the operator's authorization and may be restricted.

## 6. Automation quality gates

| Gate | Requirement | Fail state |
|---|---|---|
| Authorization | explicit owner and namespace scope | BLOCK |
| Kafka safety | KRaft quorum and ISR verified before proposed changes | BLOCK |
| Monitoring | critical targets and freshness present | UNKNOWN/BLOCK |
| Idempotency | repeated dry-runs produce no unintended mutations | BLOCK |
| GitOps | reviewed commit, image digest and rollback plan | BLOCK |
| Secrets | no private keys or credentials in logs/artifacts | BLOCK |
| Runtime | timeout, resource limits, bounded retries | BLOCK |
| Audit | UTC timestamp, source revision, outcome and reviewer | BLOCK |

## 7. Twenty Kubernetes-first hands-on labs

### Lab 01 — Approve automation scope and safety

**Objective and procedure:** Record owner, risk classification, disposable Kubernetes context, allowed namespaces, change ticket, rollback, abort gates and explicit no-production-mutation policy.

**Evidence and acceptance:** Record approved cluster context, Kafka/Strimzi/Kubernetes versions, script/manifest Git SHA, exact command, expected and observed result, permissions, security review, rollback and owner. Mark **Pending** until executed. Prefer synthetic topics and no mutation to Kafka CRs.

### Lab 02 — Baseline Kafka/Strimzi/KRaft readiness

**Objective and procedure:** Inspect Kafka CR, KafkaNodePools, KRaft quorum, Pods, PVCs, Strimzi reconciliations, client SLO and monitoring freshness.

**Evidence and acceptance:** Record approved cluster context, Kafka/Strimzi/Kubernetes versions, script/manifest Git SHA, exact command, expected and observed result, permissions, security review, rollback and owner. Mark **Pending** until executed. Prefer synthetic topics and no mutation to Kafka CRs.

### Lab 03 — Inventory recurring Kafka operational toil

**Objective and procedure:** Collect representative tickets/pages for lag checks, broker readiness, topic audits, certificate expiry, PVC alerts and manual evidence gathering; classify by frequency, duration and risk.

**Evidence and acceptance:** Record approved cluster context, Kafka/Strimzi/Kubernetes versions, script/manifest Git SHA, exact command, expected and observed result, permissions, security review, rollback and owner. Mark **Pending** until executed. Prefer synthetic topics and no mutation to Kafka CRs.

### Lab 04 — Calculate toil baseline and prioritization

**Objective and procedure:** Estimate weekly toil hours, alert noise, failure recurrence and automation ROI; select low-risk read-only tasks first and document assumptions.

**Evidence and acceptance:** Record approved cluster context, Kafka/Strimzi/Kubernetes versions, script/manifest Git SHA, exact command, expected and observed result, permissions, security review, rollback and owner. Mark **Pending** until executed. Prefer synthetic topics and no mutation to Kafka CRs.

### Lab 05 — Build read-only health collection script

**Objective and procedure:** Capture Kafka Ready, KRaft quorum, Pod restarts, PVCs, Events and topic inventory without changing Kafka resources; sanitize output.

**Evidence and acceptance:** Record approved cluster context, Kafka/Strimzi/Kubernetes versions, script/manifest Git SHA, exact command, expected and observed result, permissions, security review, rollback and owner. Mark **Pending** until executed. Prefer synthetic topics and no mutation to Kafka CRs.

### Lab 06 — Create Kubernetes CronJob design for inventory

**Objective and procedure:** Design an approved read-only CronJob with scoped ServiceAccount, projected tokens, pinned image, concurrencyPolicy Forbid, history limits and resource bounds.

**Evidence and acceptance:** Record approved cluster context, Kafka/Strimzi/Kubernetes versions, script/manifest Git SHA, exact command, expected and observed result, permissions, security review, rollback and owner. Mark **Pending** until executed. Prefer synthetic topics and no mutation to Kafka CRs.

### Lab 07 — Validate CronJob RBAC with can-i

**Objective and procedure:** Test service account authorization for get/list on only necessary Kafka/KafkaNodePool/Pods/PVC/Events; prohibit Secrets, exec, patch, delete and wildcard privileges.

**Evidence and acceptance:** Record approved cluster context, Kafka/Strimzi/Kubernetes versions, script/manifest Git SHA, exact command, expected and observed result, permissions, security review, rollback and owner. Mark **Pending** until executed. Prefer synthetic topics and no mutation to Kafka CRs.

### Lab 08 — Design GitOps repository and promotion gates

**Objective and procedure:** Version manifests/scripts, lint YAML, pin image digests, require code review, policy-as-code, staging approval and auditable rollback.

**Evidence and acceptance:** Record approved cluster context, Kafka/Strimzi/Kubernetes versions, script/manifest Git SHA, exact command, expected and observed result, permissions, security review, rollback and owner. Mark **Pending** until executed. Prefer synthetic topics and no mutation to Kafka CRs.

### Lab 09 — Automate synthetic topic configuration checks

**Objective and procedure:** Compare KafkaTopic CR desired RF/minISR/retention and Kafka runtime metadata; report drift only and avoid changing live topic configuration.

**Evidence and acceptance:** Record approved cluster context, Kafka/Strimzi/Kubernetes versions, script/manifest Git SHA, exact command, expected and observed result, permissions, security review, rollback and owner. Mark **Pending** until executed. Prefer synthetic topics and no mutation to Kafka CRs.

### Lab 10 — Automate SLO and burn-rate reports

**Objective and procedure:** Generate synthetic service SLO availability, event-age, budget burn and missing-data status from validated Prometheus queries and ledger reconciliation.

**Evidence and acceptance:** Record approved cluster context, Kafka/Strimzi/Kubernetes versions, script/manifest Git SHA, exact command, expected and observed result, permissions, security review, rollback and owner. Mark **Pending** until executed. Prefer synthetic topics and no mutation to Kafka CRs.

### Lab 11 — Automate certificate expiry inventory safely

**Objective and procedure:** Inspect approved TLS certificate metadata/expiry without exporting private keys or Secret contents; alert owners before expiry.

**Evidence and acceptance:** Record approved cluster context, Kafka/Strimzi/Kubernetes versions, script/manifest Git SHA, exact command, expected and observed result, permissions, security review, rollback and owner. Mark **Pending** until executed. Prefer synthetic topics and no mutation to Kafka CRs.

### Lab 12 — Automate PVC and broker capacity forecasts

**Objective and procedure:** Track filesystem use, IOPS, latency, retention growth, partition count and forecasts with headroom; separate PVC allocation from real use.

**Evidence and acceptance:** Record approved cluster context, Kafka/Strimzi/Kubernetes versions, script/manifest Git SHA, exact command, expected and observed result, permissions, security review, rollback and owner. Mark **Pending** until executed. Prefer synthetic topics and no mutation to Kafka CRs.

### Lab 13 — Automate alert and runbook hygiene checks

**Objective and procedure:** Validate PrometheusRule labels, owners, runbook URLs, alert receiver mapping, silence age and dead links; use test-only receivers.

**Evidence and acceptance:** Record approved cluster context, Kafka/Strimzi/Kubernetes versions, script/manifest Git SHA, exact command, expected and observed result, permissions, security review, rollback and owner. Mark **Pending** until executed. Prefer synthetic topics and no mutation to Kafka CRs.

### Lab 14 — Implement safe action classification

**Objective and procedure:** Classify actions as observe, recommend, human-approved or prohibited; enforce dry-run defaults and disallow Kafka broker restarts, PVC deletion or ACL changes.

**Evidence and acceptance:** Record approved cluster context, Kafka/Strimzi/Kubernetes versions, script/manifest Git SHA, exact command, expected and observed result, permissions, security review, rollback and owner. Mark **Pending** until executed. Prefer synthetic topics and no mutation to Kafka CRs.

### Lab 15 — Design remediation preconditions

**Objective and procedure:** For any future automated action require quorum/ISR, maintenance window, SLO burn, budget, owner approval, idempotency and rollback checks.

**Evidence and acceptance:** Record approved cluster context, Kafka/Strimzi/Kubernetes versions, script/manifest Git SHA, exact command, expected and observed result, permissions, security review, rollback and owner. Mark **Pending** until executed. Prefer synthetic topics and no mutation to Kafka CRs.

### Lab 16 — Test automation idempotency

**Objective and procedure:** Run inventory and reporting jobs repeatedly in lab; ensure no KafkaTopic/KafkaUser/Kafka CR spec drift and no duplicate tickets.

**Evidence and acceptance:** Record approved cluster context, Kafka/Strimzi/Kubernetes versions, script/manifest Git SHA, exact command, expected and observed result, permissions, security review, rollback and owner. Mark **Pending** until executed. Prefer synthetic topics and no mutation to Kafka CRs.

### Lab 17 — Test partial failure and retries

**Objective and procedure:** Simulate unavailable Prometheus or Kafka CLI in a test job, verify bounded retries, timeouts, explicit Unknown status and no destructive fallback.

**Evidence and acceptance:** Record approved cluster context, Kafka/Strimzi/Kubernetes versions, script/manifest Git SHA, exact command, expected and observed result, permissions, security review, rollback and owner. Mark **Pending** until executed. Prefer synthetic topics and no mutation to Kafka CRs.

### Lab 18 — Test audit evidence and secrets hygiene

**Objective and procedure:** Capture Git SHA, job image digest, namespace, UTC time, input version, output hash and redaction; prohibit tokens/keys in logs.

**Evidence and acceptance:** Record approved cluster context, Kafka/Strimzi/Kubernetes versions, script/manifest Git SHA, exact command, expected and observed result, permissions, security review, rollback and owner. Mark **Pending** until executed. Prefer synthetic topics and no mutation to Kafka CRs.

### Lab 19 — Build operational readiness scorecard

**Objective and procedure:** Assess runbooks, backups/restore drills, on-call, SLOs, monitoring, access, security, capacity, maintenance and rollback with owners and evidence.

**Evidence and acceptance:** Record approved cluster context, Kafka/Strimzi/Kubernetes versions, script/manifest Git SHA, exact command, expected and observed result, permissions, security review, rollback and owner. Mark **Pending** until executed. Prefer synthetic topics and no mutation to Kafka CRs.

### Lab 20 — Complete improvement cycle and signoff

**Objective and procedure:** Compare toil baseline to post-automation estimates, document residual risk, action backlog, dry-run demo, independent security review and 100-point rubric.

**Evidence and acceptance:** Record approved cluster context, Kafka/Strimzi/Kubernetes versions, script/manifest Git SHA, exact command, expected and observed result, permissions, security review, rollback and owner. Mark **Pending** until executed. Prefer synthetic topics and no mutation to Kafka CRs.

## 8. Read-only verification script

Save as `verify-ch44.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
CLUSTER=sre-kafka
BS=sre-kafka-kafka-bootstrap:9092
BIN=/opt/kafka/bin
echo '[1/10] Context'; kubectl config current-context
echo '[2/10] Kafka Ready'
kubectl -n "$NS" wait "kafka/$CLUSTER" --for=condition=Ready --timeout=120s
echo '[3/10] Kafka and NodePools'
kubectl -n "$NS" get kafka,kafkanodepool -o wide
echo '[4/10] Kafka Pods and PVCs'
kubectl -n "$NS" get pods,pvc -o wide
echo '[5/10] Kubernetes Events'
kubectl -n "$NS" get events --sort-by=.metadata.creationTimestamp
echo '[6/10] CronJob inventory'
kubectl -n "$NS" get cronjobs -o wide
echo '[7/10] Read-only RBAC'
kubectl -n "$NS" get serviceaccounts,roles,rolebindings
echo '[8/10] Kafka metric configuration'
kubectl -n "$NS" get kafka "$CLUSTER" -o jsonpath='{.spec.kafka.metricsConfig}{"\n"}'
echo '[9/10] NetworkPolicies'
kubectl -n "$NS" get networkpolicy
echo '[10/10] KRaft quorum'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-metadata-quorum.sh" --bootstrap-server "$BS" describe --status
echo 'PASS: read-only Kafka SRE automation inventory.'
echo 'NOT PROVEN: CronJob execution, RBAC enforcement, toil savings, readiness or security acceptance.'
```

Run `chmod +x verify-ch44.sh && ./verify-ch44.sh | tee evidence-ch44/preflight.txt`. The internal 9092 bootstrap convention is disposable-lab only; secure tests must use approved TLS/SASL and scoped Kafka ACLs.

## 9. Twelve troubleshooting scenarios

### Scenario 1 — Automation silently mutates Kafka CR

**Detect:** Compare GitOps desired state, Kubernetes audit/events, CronJob logs, Kafka CR generation, KRaft quorum, ISR, Prometheus targets and automation evidence. **Diagnose:** Verify RBAC, service account, image digest, timeouts, retries, missing data, idempotency and action authorization. **Recover:** Stop or disable only chapter-owned automation through approved GitOps; do not roll back unrelated Kafka state. **Verify:** Repeat dry-run, inspect absence of unauthorized mutations and document owner/security signoff.

### Scenario 2 — CronJob uses wildcard cluster-admin RBAC

**Detect:** Compare GitOps desired state, Kubernetes audit/events, CronJob logs, Kafka CR generation, KRaft quorum, ISR, Prometheus targets and automation evidence. **Diagnose:** Verify RBAC, service account, image digest, timeouts, retries, missing data, idempotency and action authorization. **Recover:** Stop or disable only chapter-owned automation through approved GitOps; do not roll back unrelated Kafka state. **Verify:** Repeat dry-run, inspect absence of unauthorized mutations and document owner/security signoff.

### Scenario 3 — CronJob overlap creates duplicate incidents

**Detect:** Compare GitOps desired state, Kubernetes audit/events, CronJob logs, Kafka CR generation, KRaft quorum, ISR, Prometheus targets and automation evidence. **Diagnose:** Verify RBAC, service account, image digest, timeouts, retries, missing data, idempotency and action authorization. **Recover:** Stop or disable only chapter-owned automation through approved GitOps; do not roll back unrelated Kafka state. **Verify:** Repeat dry-run, inspect absence of unauthorized mutations and document owner/security signoff.

### Scenario 4 — Monitoring outage interpreted as healthy zero

**Detect:** Compare GitOps desired state, Kubernetes audit/events, CronJob logs, Kafka CR generation, KRaft quorum, ISR, Prometheus targets and automation evidence. **Diagnose:** Verify RBAC, service account, image digest, timeouts, retries, missing data, idempotency and action authorization. **Recover:** Stop or disable only chapter-owned automation through approved GitOps; do not roll back unrelated Kafka state. **Verify:** Repeat dry-run, inspect absence of unauthorized mutations and document owner/security signoff.

### Scenario 5 — Kafka quorum unknown but remediation proceeds

**Detect:** Compare GitOps desired state, Kubernetes audit/events, CronJob logs, Kafka CR generation, KRaft quorum, ISR, Prometheus targets and automation evidence. **Diagnose:** Verify RBAC, service account, image digest, timeouts, retries, missing data, idempotency and action authorization. **Recover:** Stop or disable only chapter-owned automation through approved GitOps; do not roll back unrelated Kafka state. **Verify:** Repeat dry-run, inspect absence of unauthorized mutations and document owner/security signoff.

### Scenario 6 — Topic drift script confuses desired and observed state

**Detect:** Compare GitOps desired state, Kubernetes audit/events, CronJob logs, Kafka CR generation, KRaft quorum, ISR, Prometheus targets and automation evidence. **Diagnose:** Verify RBAC, service account, image digest, timeouts, retries, missing data, idempotency and action authorization. **Recover:** Stop or disable only chapter-owned automation through approved GitOps; do not roll back unrelated Kafka state. **Verify:** Repeat dry-run, inspect absence of unauthorized mutations and document owner/security signoff.

### Scenario 7 — Certificate inventory exposes private keys

**Detect:** Compare GitOps desired state, Kubernetes audit/events, CronJob logs, Kafka CR generation, KRaft quorum, ISR, Prometheus targets and automation evidence. **Diagnose:** Verify RBAC, service account, image digest, timeouts, retries, missing data, idempotency and action authorization. **Recover:** Stop or disable only chapter-owned automation through approved GitOps; do not roll back unrelated Kafka state. **Verify:** Repeat dry-run, inspect absence of unauthorized mutations and document owner/security signoff.

### Scenario 8 — PVC forecast ignores actual filesystem usage

**Detect:** Compare GitOps desired state, Kubernetes audit/events, CronJob logs, Kafka CR generation, KRaft quorum, ISR, Prometheus targets and automation evidence. **Diagnose:** Verify RBAC, service account, image digest, timeouts, retries, missing data, idempotency and action authorization. **Recover:** Stop or disable only chapter-owned automation through approved GitOps; do not roll back unrelated Kafka state. **Verify:** Repeat dry-run, inspect absence of unauthorized mutations and document owner/security signoff.

### Scenario 9 — Retry storm overloads Kafka API or Prometheus

**Detect:** Compare GitOps desired state, Kubernetes audit/events, CronJob logs, Kafka CR generation, KRaft quorum, ISR, Prometheus targets and automation evidence. **Diagnose:** Verify RBAC, service account, image digest, timeouts, retries, missing data, idempotency and action authorization. **Recover:** Stop or disable only chapter-owned automation through approved GitOps; do not roll back unrelated Kafka state. **Verify:** Repeat dry-run, inspect absence of unauthorized mutations and document owner/security signoff.

### Scenario 10 — Alert hygiene job creates alert storm

**Detect:** Compare GitOps desired state, Kubernetes audit/events, CronJob logs, Kafka CR generation, KRaft quorum, ISR, Prometheus targets and automation evidence. **Diagnose:** Verify RBAC, service account, image digest, timeouts, retries, missing data, idempotency and action authorization. **Recover:** Stop or disable only chapter-owned automation through approved GitOps; do not roll back unrelated Kafka state. **Verify:** Repeat dry-run, inspect absence of unauthorized mutations and document owner/security signoff.

### Scenario 11 — GitOps rollback reverts unrelated production changes

**Detect:** Compare GitOps desired state, Kubernetes audit/events, CronJob logs, Kafka CR generation, KRaft quorum, ISR, Prometheus targets and automation evidence. **Diagnose:** Verify RBAC, service account, image digest, timeouts, retries, missing data, idempotency and action authorization. **Recover:** Stop or disable only chapter-owned automation through approved GitOps; do not roll back unrelated Kafka state. **Verify:** Repeat dry-run, inspect absence of unauthorized mutations and document owner/security signoff.

### Scenario 12 — Toil savings claimed without measured baseline

**Detect:** Compare GitOps desired state, Kubernetes audit/events, CronJob logs, Kafka CR generation, KRaft quorum, ISR, Prometheus targets and automation evidence. **Diagnose:** Verify RBAC, service account, image digest, timeouts, retries, missing data, idempotency and action authorization. **Recover:** Stop or disable only chapter-owned automation through approved GitOps; do not roll back unrelated Kafka state. **Verify:** Repeat dry-run, inspect absence of unauthorized mutations and document owner/security signoff.

## 10. Eight production SRE runbooks

### Runbook A — Automation job failure and safe retry

1. Establish automation owner, incident scope, change ID and safe-stop authority.
2. Confirm Kafka Ready, KRaft quorum, ISR and Kubernetes resource health independently.
3. Inspect CronJob status, RBAC, script revision, logs and Prometheus freshness.
4. Stop unsafe or repeated automation through approved GitOps, preserving evidence.
5. Restore read-only behavior, validate idempotency and reject unauthorized changes.
6. Reconcile intended versus actual Kafka/Kubernetes state and SLO impact.
7. Record corrective actions, security review, rollback and readiness owner.

### Runbook B — KRaft and Kafka readiness report discrepancy

1. Establish automation owner, incident scope, change ID and safe-stop authority.
2. Confirm Kafka Ready, KRaft quorum, ISR and Kubernetes resource health independently.
3. Inspect CronJob status, RBAC, script revision, logs and Prometheus freshness.
4. Stop unsafe or repeated automation through approved GitOps, preserving evidence.
5. Restore read-only behavior, validate idempotency and reject unauthorized changes.
6. Reconcile intended versus actual Kafka/Kubernetes state and SLO impact.
7. Record corrective actions, security review, rollback and readiness owner.

### Runbook C — GitOps drift and configuration approval

1. Establish automation owner, incident scope, change ID and safe-stop authority.
2. Confirm Kafka Ready, KRaft quorum, ISR and Kubernetes resource health independently.
3. Inspect CronJob status, RBAC, script revision, logs and Prometheus freshness.
4. Stop unsafe or repeated automation through approved GitOps, preserving evidence.
5. Restore read-only behavior, validate idempotency and reject unauthorized changes.
6. Reconcile intended versus actual Kafka/Kubernetes state and SLO impact.
7. Record corrective actions, security review, rollback and readiness owner.

### Runbook D — CronJob RBAC and token exposure

1. Establish automation owner, incident scope, change ID and safe-stop authority.
2. Confirm Kafka Ready, KRaft quorum, ISR and Kubernetes resource health independently.
3. Inspect CronJob status, RBAC, script revision, logs and Prometheus freshness.
4. Stop unsafe or repeated automation through approved GitOps, preserving evidence.
5. Restore read-only behavior, validate idempotency and reject unauthorized changes.
6. Reconcile intended versus actual Kafka/Kubernetes state and SLO impact.
7. Record corrective actions, security review, rollback and readiness owner.

### Runbook E — SLO report missing-data investigation

1. Establish automation owner, incident scope, change ID and safe-stop authority.
2. Confirm Kafka Ready, KRaft quorum, ISR and Kubernetes resource health independently.
3. Inspect CronJob status, RBAC, script revision, logs and Prometheus freshness.
4. Stop unsafe or repeated automation through approved GitOps, preserving evidence.
5. Restore read-only behavior, validate idempotency and reject unauthorized changes.
6. Reconcile intended versus actual Kafka/Kubernetes state and SLO impact.
7. Record corrective actions, security review, rollback and readiness owner.

### Runbook F — Capacity forecast and PVC risk

1. Establish automation owner, incident scope, change ID and safe-stop authority.
2. Confirm Kafka Ready, KRaft quorum, ISR and Kubernetes resource health independently.
3. Inspect CronJob status, RBAC, script revision, logs and Prometheus freshness.
4. Stop unsafe or repeated automation through approved GitOps, preserving evidence.
5. Restore read-only behavior, validate idempotency and reject unauthorized changes.
6. Reconcile intended versus actual Kafka/Kubernetes state and SLO impact.
7. Record corrective actions, security review, rollback and readiness owner.

### Runbook G — Alert/runbook hygiene regression

1. Establish automation owner, incident scope, change ID and safe-stop authority.
2. Confirm Kafka Ready, KRaft quorum, ISR and Kubernetes resource health independently.
3. Inspect CronJob status, RBAC, script revision, logs and Prometheus freshness.
4. Stop unsafe or repeated automation through approved GitOps, preserving evidence.
5. Restore read-only behavior, validate idempotency and reject unauthorized changes.
6. Reconcile intended versus actual Kafka/Kubernetes state and SLO impact.
7. Record corrective actions, security review, rollback and readiness owner.

### Runbook H — Operational readiness audit and improvement review

1. Establish automation owner, incident scope, change ID and safe-stop authority.
2. Confirm Kafka Ready, KRaft quorum, ISR and Kubernetes resource health independently.
3. Inspect CronJob status, RBAC, script revision, logs and Prometheus freshness.
4. Stop unsafe or repeated automation through approved GitOps, preserving evidence.
5. Restore read-only behavior, validate idempotency and reject unauthorized changes.
6. Reconcile intended versus actual Kafka/Kubernetes state and SLO impact.
7. Record corrective actions, security review, rollback and readiness owner.

## 11. Operational readiness scorecard

| Dimension | Minimum evidence | Status |
|---|---|---|
| Ownership/on-call | RACI, backup and handoff | Pending |
| Kafka safety | quorum, ISR, durability runbooks | Pending |
| Monitoring | targets, SLOs, alerts and no-data handling | Pending |
| Automation | RBAC, dry-run, idempotency and audit | Pending |
| Security | TLS/ACL, secret hygiene, image provenance | Pending |
| Capacity | PVC and broker headroom forecast | Pending |
| Recovery | backup/restore and rollback drill evidence | Pending |
| Change management | GitOps approvals, exception expiry | Pending |
| Toil improvement | measured before/after hours and incident outcomes | Pending |

The scorecard is a starting template, not a statement of production readiness. Missing critical evidence means **Not Ready**.

## 12. Evidence package

```text
evidence-ch44/
  approval-and-safety.md
  preflight.txt
  version-and-context.md
  toil-baseline.csv
  toil-roi-prioritization.md
  readonly-health-script.sh
  cronjob-security-review.md
  rbac-positive-negative-tests.md
  gitops-promotion-gates.md
  topic-drift-report.md
  slo-burn-report.md
  certificate-expiry-report.md
  pvc-capacity-forecast.md
  alert-runbook-hygiene.md
  automation-action-classification.md
  remediation-preconditions.md
  idempotency-tests.md
  partial-failure-retry-tests.md
  audit-and-secrets-review.md
  readiness-scorecard.md
  continuous-improvement-backlog.csv
  assessor-signoff.md
```

Each artifact must record exact version, UTC timestamp, owner, source revision, expected/observed result, redaction, rollback and reviewer. Do not fabricate successful automation runs.

## 13. 100-point enterprise reliability automation assessment

| Domain | Points | Critical |
|---|---:|---|
| Scope, safety, approval and toil baseline | 10 | Yes |
| Kafka/KRaft/ISR baseline and health reporting | 10 | Yes |
| Kubernetes CronJob design and least-privilege RBAC | 15 | Yes |
| GitOps promotion, dry-run and rollback | 15 | Yes |
| SLO, topic, certificate and capacity reporting | 15 | Yes |
| Idempotency, retries and partial failure | 10 | Yes |
| Secret hygiene, audit and image provenance | 10 | Yes |
| Operational readiness and continuous improvement | 10 | Yes |
| Independent reviewer and evidence quality | 5 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with all critical gates evidenced. **Automatic Fail:** unapproved Kafka mutations, wildcard privileges, exposed Secrets, unsafe automated broker/PVC operations, false green on missing data, fabricated toil savings or absent independent review.

## 14. Cleanup, references and next chapter

Remove only chapter-owned synthetic CronJobs, test ServiceAccounts, Roles and temporary reports through approved GitOps. Preserve redacted evidence. Do not delete Kafka PVCs, production offsets, shared monitoring stores or operator-managed Secrets.

**References:** [Google SRE Book — Eliminating Toil](https://sre.google/sre-book/eliminating-toil/), [Google SRE Workbook](https://sre.google/workbook/), [Kubernetes CronJobs](https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/), [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/), [Strimzi documentation](https://strimzi.io/documentation/), [Kafka documentation](https://kafka.apache.org/documentation/).

**Next:** Chapter 045 — Kafka Enterprise Reliability, SLO Governance and SRE Operational Readiness Capstone.

---

**Verification boundary:** GitHub publication establishes only document availability. Live CronJob execution, RBAC testing, toil measurement, security review and independent acceptance remain Pending.
