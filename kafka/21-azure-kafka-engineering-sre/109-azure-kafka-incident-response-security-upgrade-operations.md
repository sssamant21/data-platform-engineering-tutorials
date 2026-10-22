# Chapter 109 — Azure Kafka Incident Response, Security and Upgrade Operations

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 21 — Microsoft Azure Kafka Engineering & SRE (9/10)  
**Primary platform:** AKS/Kubernetes, Strimzi-managed Apache Kafka KRaft  
**Managed-service comparison:** Azure Event Hubs Kafka-compatible endpoint  
**Prerequisites:** Chapters 101–108, isolated AKS lab, monitoring, backups, incident response ownership  
**Publication:** Published after GitHub commit · **Live execution:** Pending · **Independent technical/security review:** Pending

> **Safety:** Never run destructive fault injection, certificate rotation, operator upgrades, broker upgrades or node drains against production from this tutorial. First verify active cluster context, change approval, version compatibility, recovery points, quorum health and rollback ownership. Preserve sanitized evidence; do not publish credentials, private keys, SAS tokens, healthcare records or sensitive event payloads.

## 1. Mission and outcomes

Develop repeatable on-call procedures for Kafka incidents on AKS, combining Kubernetes and Strimzi diagnostics with Kafka-specific evidence, Azure telemetry, security controls and upgrade safety gates. Compare responsibility boundaries with Azure Event Hubs.

**Outcomes:** classify incidents; collect reliable evidence; identify broker, controller, storage, network, security and client failures; rotate credentials safely; plan compatible rolling upgrades; rehearse rollback; and prove no unexplained loss of acknowledged synthetic events.

## 2. Operating model and responsibility boundary

```text
  AKS application clients (producers / consumers)
                 |
        TLS / SASL / ACL
                 |
    Strimzi Kafka KRaft cluster on AKS
    ├── Kafka brokers, leaders, ISR
    ├── KRaft controller quorum
    ├── KafkaNodePools, operator and CRDs
    ├── PVC / Azure disk / node pools
    └── Prometheus + Azure Monitor
                 |
         Incident command
  detection → triage → containment → recovery
           → reconciliation → RCA

  Event Hubs alternative:
  Azure-managed service plane + customer-owned
  clients, credentials, network and application behavior
```

For self-managed Kafka, the platform team owns broker/operator health, cluster upgrades and storage operations. For Event Hubs, Microsoft operates service infrastructure; the customer still owns client correctness, identities, access, network, tier selection, capacity, application monitoring and cutover design. Do not assume Event Hubs supports Kafka broker admin operations.

## 3. Incident severity and command structure

| Severity | Example | Immediate response |
|---|---|---|
| SEV-1 | Confirmed accepted-event loss, widespread unavailability or compromised production credentials | Incident commander, page owners, preserve evidence, freeze changes |
| SEV-2 | Sustained producer failures, ISR risk, major lag with retention threat | Declare incident, mitigate, monitor recovery |
| SEV-3 | Isolated client errors, capacity warning, noncritical telemetry gaps | Ticket, owner, bounded investigation |

Define a timeline with detection, acknowledgement, mitigation, recovery, event reconciliation and closure. Keep SLO impact and customer impact separate from raw infrastructure alarms.

## 4. Kubernetes-first incident preflight

```powershell
kubectl config current-context
kubectl auth can-i get pods -n kafka
kubectl get kafka,kafkanodepool,kafkatopic -n kafka
kubectl get pods -n kafka -o wide
kubectl get pvc -n kafka -o wide
kubectl get events -n kafka --sort-by=.lastTimestamp
kubectl get pdb -n kafka
kubectl get nodes -L topology.kubernetes.io/zone
az account show --query '{subscription:id,tenant:tenantId}' -o json
```

Use discovered namespace and resource names rather than assuming `kafka` or `lab-kafka` in real environments. Confirm `kubectl` permissions, telemetry timestamps, and Azure subscription before changing anything.

## 5. Kafka-specific triage

Correlate:
- **Broker:** offline/under-replicated partitions, ISR changes, request queues, fetch/produce errors, JVM pauses.
- **KRaft:** controller quorum health, metadata leader elections, catch-up lag and operator reconciliation status.
- **Client:** producer acknowledgements, retries, timeouts, consumer lag, rebalances, committed offsets and DLQ volume.
- **AKS:** pod scheduling, restarts/OOM, PDBs, CPU throttling, disk IOPS/latency, network and DNS.
- **Azure:** disk throttling, AKS infrastructure events, Azure Monitor logs, Event Hubs namespace throttling and authentication errors.

**Read-only evidence collection:**

```powershell
kubectl describe kafka -n kafka
kubectl describe pods -n kafka
kubectl logs -n kafka deployment/strimzi-cluster-operator --tail=200
kubectl get pods -n kafka -o yaml
```

The operator deployment name may differ: discover it before running the log command. Avoid indiscriminate full log dumps; redact sensitive values and cap evidence size.

## 6. Security operations

Audit Kubernetes RBAC, Strimzi KafkaUser permissions, listener TLS, certificate expiration, SASL credentials, Key Vault integration, NetworkPolicy and Azure identity assignments. Implement a **dual-credential/overlap window** when the mechanism supports it: issue new credential, deploy to a canary, validate auth and event correctness, roll clients, revoke old credential after confirmation, then monitor failures. Certificate rotation is not simply replacing a Secret: verify trust chain, application reload/restart behavior and broker/operator rotation semantics.

During suspected compromise, preserve audit trails, limit scope, revoke or rotate affected credentials using approved procedures, verify all impacted clients, and document containment.

## 7. Strimzi and Kafka upgrade engineering

Before any upgrade:
1. Record current Strimzi operator, Kafka broker, KRaft metadata and CRD versions.
2. Check the exact Strimzi-supported upgrade path, Kafka version compatibility, deprecations and required intermediate versions.
3. Confirm healthy controllers, brokers, ISR, PVCs, capacity and backups.
4. Validate CRD/manifests in a disposable environment; review GitOps drift and admission policies.
5. Test canary client compatibility and workload behavior at peak-like synthetic load.
6. Define change window, SLO thresholds, abort gates, owners and post-upgrade reconciliation.

**Important:** Rolling back Kafka binaries, metadata formats, CRDs or KRaft feature levels may be unsupported after irreversible transitions. Do not promise simple image-tag rollback. Prefer documented forward recovery or restore to an independently validated recovery point.

## 8. Kubernetes maintenance safety

Review PDBs, KafkaNodePool topology, AZ placement, controller quorum, broker ISR and recovery capacity before draining nodes. Change one failure domain at a time and monitor Kafka-specific health between operations. A Kubernetes Deployment becoming Ready does not prove partition availability or application correctness. Follow the installed Strimzi release's operator-managed rolling procedures; avoid ad hoc broker pod deletion as a routine upgrade method.

## 9. Event Hubs operational differences

Investigate Event Hubs via Azure Monitor metrics, namespace/tier quotas, network restrictions, Azure RBAC/SAS or supported OAuth authentication, client error codes and Microsoft service health. There is no customer-managed Kafka broker rolling upgrade or KRaft quorum to repair. Validate Kafka API compatibility and client configuration before blaming platform outages; involve Azure support when service-side evidence warrants escalation.

## 10. Hands-on labs (20)

For each lab, record prerequisites, change scope, expected alarms, actual evidence, rollback, event reconciliation and timestamped PASS/FAIL.

| # | Lab | Required evidence |
|---|---|---|
| 01 | Incident preflight and AKS context validation | Context, sanitized commands/metrics, outcome, rollback |
| 02 | Kafka and KafkaNodePool health inventory | Context, sanitized commands/metrics, outcome, rollback |
| 03 | KRaft quorum and ISR evidence capture | Context, sanitized commands/metrics, outcome, rollback |
| 04 | Producer/consumer impact baseline | Context, sanitized commands/metrics, outcome, rollback |
| 05 | Kubernetes events and pod log correlation | Context, sanitized commands/metrics, outcome, rollback |
| 06 | Prometheus and Azure Monitor timeline | Context, sanitized commands/metrics, outcome, rollback |
| 07 | SLO burn and severity classification | Context, sanitized commands/metrics, outcome, rollback |
| 08 | RBAC least-privilege review | Context, sanitized commands/metrics, outcome, rollback |
| 09 | KafkaUser ACL and credential review | Context, sanitized commands/metrics, outcome, rollback |
| 10 | TLS certificate expiration audit | Context, sanitized commands/metrics, outcome, rollback |
| 11 | Secret rotation rehearsal | Context, sanitized commands/metrics, outcome, rollback |
| 12 | NetworkPolicy connectivity investigation | Context, sanitized commands/metrics, outcome, rollback |
| 13 | Safe Strimzi version compatibility review | Context, sanitized commands/metrics, outcome, rollback |
| 14 | Operator upgrade dry-run planning | Context, sanitized commands/metrics, outcome, rollback |
| 15 | Kafka broker rolling-upgrade readiness | Context, sanitized commands/metrics, outcome, rollback |
| 16 | AKS node maintenance and PDB validation | Context, sanitized commands/metrics, outcome, rollback |
| 17 | Controlled single-broker disruption | Context, sanitized commands/metrics, outcome, rollback |
| 18 | Event Hubs throttling incident triage | Context, sanitized commands/metrics, outcome, rollback |
| 19 | Rollback and event-ID reconciliation | Context, sanitized commands/metrics, outcome, rollback |
| 20 | Incident postmortem and acceptance | Context, sanitized commands/metrics, outcome, rollback |

### Lab execution pattern

1. Establish healthy baseline: quorum, ISR, producer acknowledgements, consumer lag and event-ID reconciliation.
2. Record Kubernetes manifests and installed versions.
3. Execute one approved, bounded experiment in a disposable lab.
4. Capture detection, escalation, containment, recovery and verification timestamps.
5. Verify Kafka cluster health and independently reconcile accepted versus processed event IDs.
6. Revert lab-owned changes, record evidence and mark PASS/FAIL only after actual execution.

## 11. Failure scenarios (12)

| # | Failure | Investigation and recovery objective |
|---|---|---|
| 1 | Broker pod CrashLoopBackOff | Confirm impact; correlate Kafka, Kubernetes and Azure evidence; contain; restore safely; reconcile events |
| 2 | KRaft quorum degradation | Confirm impact; correlate Kafka, Kubernetes and Azure evidence; contain; restore safely; reconcile events |
| 3 | ISR shrink and producer errors | Confirm impact; correlate Kafka, Kubernetes and Azure evidence; contain; restore safely; reconcile events |
| 4 | Consumer lag surge | Confirm impact; correlate Kafka, Kubernetes and Azure evidence; contain; restore safely; reconcile events |
| 5 | AKS node drain blocked by PDB | Confirm impact; correlate Kafka, Kubernetes and Azure evidence; contain; restore safely; reconcile events |
| 6 | Certificate expiration | Confirm impact; correlate Kafka, Kubernetes and Azure evidence; contain; restore safely; reconcile events |
| 7 | Kafka ACL authorization failure | Confirm impact; correlate Kafka, Kubernetes and Azure evidence; contain; restore safely; reconcile events |
| 8 | Secret rotation mismatch | Confirm impact; correlate Kafka, Kubernetes and Azure evidence; contain; restore safely; reconcile events |
| 9 | DNS/NetworkPolicy outage | Confirm impact; correlate Kafka, Kubernetes and Azure evidence; contain; restore safely; reconcile events |
| 10 | Disk pressure during rolling upgrade | Confirm impact; correlate Kafka, Kubernetes and Azure evidence; contain; restore safely; reconcile events |
| 11 | Strimzi CRD/version incompatibility | Confirm impact; correlate Kafka, Kubernetes and Azure evidence; contain; restore safely; reconcile events |
| 12 | Event Hubs authentication or throttling | Confirm impact; correlate Kafka, Kubernetes and Azure evidence; contain; restore safely; reconcile events |

For every scenario specify severity, expected detection, escalation, approved intervention, recovery gates and preventive action. Never simulate credential compromise with real credentials.

## 12. Production SRE runbooks (8)

| # | Runbook | Workflow |
|---|---|---|
| 1 | Sev-1 Kafka availability incident | Declare owner → assess impact → collect evidence → contain → approved change → validate correctness → close with RCA |
| 2 | KRaft quorum and broker recovery | Declare owner → assess impact → collect evidence → contain → approved change → validate correctness → close with RCA |
| 3 | Consumer lag and data correctness | Declare owner → assess impact → collect evidence → contain → approved change → validate correctness → close with RCA |
| 4 | TLS/credential compromise response | Declare owner → assess impact → collect evidence → contain → approved change → validate correctness → close with RCA |
| 5 | Strimzi operator upgrade | Declare owner → assess impact → collect evidence → contain → approved change → validate correctness → close with RCA |
| 6 | Kafka broker/version upgrade | Declare owner → assess impact → collect evidence → contain → approved change → validate correctness → close with RCA |
| 7 | AKS node pool maintenance | Declare owner → assess impact → collect evidence → contain → approved change → validate correctness → close with RCA |
| 8 | Event Hubs incident and escalation | Declare owner → assess impact → collect evidence → contain → approved change → validate correctness → close with RCA |

Runbooks must identify on-call escalation, change approval, blast-radius controls, read-only diagnostics, rollback authority, RPO/RTO implications, stakeholder communications and incident evidence retention.

## 13. Monitoring, compliance and operational evidence

Maintain dashboards for broker/controller health, ISR, producer p99 and error ratio, consumer lag, DLQ, Kubernetes resource pressure, cert expiry and Event Hubs throttling. Separate security audit events from application payloads; use retention, encryption, access review and redaction appropriate to organizational requirements. Use immutable incident IDs and a consistent timeline across UTC sources.

## 14. 100-point acceptance assessment

| Gate | Points |
|---|---:|
| Incident triage and severity management | 15 |
| Kafka broker/KRaft diagnostics | 15 |
| AKS, storage and network correlation | 10 |
| Identity, ACL, TLS and secret rotation | 15 |
| Strimzi/Kafka upgrade readiness | 15 |
| Node maintenance and recovery | 10 |
| Event Hubs managed-service response | 10 |
| Runbooks, rollback, reconciliation and evidence | 10 |
| **Total** | **100** |

**Proposed pass:** ≥85/100, no unexplained missing accepted IDs, no critical security findings, demonstrated incident recovery, verified upgrade compatibility and independent review. Publication is not runtime certification.

## 15. Evidence manifest

```yaml
chapter: 109
environment: isolated-aks-lab
aks_context: REPLACE
strimzi_version: REPLACE
kafka_version: REPLACE
controller_quorum_baseline: REPLACE
change_ticket: REPLACE
incident_id: REPLACE
lab_results: []
upgrade_path_review: pending
security_rotation_review: pending
event_reconciliation: pending
technical_review: pending
security_review: pending
runtime_certified: false
```

## 16. Next chapter

**Chapter 110 — Azure Kafka Enterprise Production Capstone and Acceptance.**
