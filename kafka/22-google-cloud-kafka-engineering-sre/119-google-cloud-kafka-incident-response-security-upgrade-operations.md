# Chapter 119 — Google Cloud Kafka Incident Response, Security and Upgrade Operations

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 22 — Google Cloud Kafka Engineering & SRE (9/10)  
**Primary platform:** GKE + Strimzi Kafka KRaft  
**Managed alternative:** Google Cloud Managed Service for Apache Kafka  
**Prerequisites:** Chapters 111–118, isolated GKE/Kafka lab, baseline SLOs and approved maintenance process  
**Publication:** Published · **Live labs:** Pending · **Independent technical/security review:** Pending · **Runtime certification:** Not claimed

> **Safety:** Run fault injection, credential rotation, node maintenance and version upgrades only in a dedicated environment with approval. Never delete Kafka PVCs, force unclean elections or change controller quorum membership as a generic recovery step. Validate upgrade order and version compatibility using the exact installed Strimzi/Kafka/GKE releases and current official documentation.

## 1. Mission and learning outcomes

Lead a production-style Kafka incident, identify customer/provider responsibilities, contain security incidents, execute change-controlled Kafka/Strimzi/GKE upgrades, and verify recovery through SLOs and synthetic event-ID reconciliation. Establish rollback and stop criteria before any maintenance.

**Deliverables:** incident command structure, security control checklist, change plan, upgrade compatibility matrix, 20 labs, 12 failure scenarios, 8 runbooks and 100-point acceptance.

## 2. Incident ownership architecture

```text
Users / applications → producer/consumer metrics and event correctness
                                |
                     Kafka on Google Cloud
             ┌──────────────────┴──────────────────┐
        GKE + Strimzi                 Google managed Kafka
        SRE owns brokers              Provider owns broker lifecycle
        controller quorum             SRE owns clients, IAM/network,
        PVs, operator                 data contracts, incident liaison
             └──────────────────┬──────────────────┘
                  incident commander / on-call
                                |
          security · app owner · cloud networking · vendor
                                |
              timeline / mitigation / verification / RCA
```

Severity depends on user and data impact, not merely a single broker metric. Kafka cluster recovery is incomplete until accepted events are reconciled against durable sink outcomes.

## 3. Incident response lifecycle

1. **Detect:** alert on producer errors, lag age, offline partitions, ISR, quorum, disk pressure, DLQ and missing accepted IDs.
2. **Declare:** set severity, commander, technical lead, communications owner and incident channel.
3. **Contain:** pause risky deployments or bounded synthetic producers; preserve state and avoid destructive remediation.
4. **Diagnose:** compare Kafka, Strimzi, GKE, network, identity and sink evidence against healthy baseline.
5. **Mitigate:** use least-risk approved change, maintain quorum/ISR and preserve event data.
6. **Verify:** check service SLOs, consumer offsets, synthetic event reconciliation and security posture.
7. **Close:** document impact, timeline, root cause, contributing factors, follow-up owners and recurrence controls.

## 4. Safe PowerShell diagnostic baseline

```powershell
gcloud config get-value project
gcloud auth list
kubectl config current-context
kubectl get nodes -L topology.kubernetes.io/zone
kubectl get kafka,kafkanodepool,kafkatopic,kafkauser -n kafka
kubectl get pods -n kafka -o wide
kubectl get pvc -n kafka
kubectl get pdb -n kafka
kubectl get events -n kafka --sort-by=.lastTimestamp
kubectl get networkpolicy -n kafka
kubectl get deployments -n kafka-apps
```

Do not paste Secret values, authorization headers, patient data or unredacted certificate private keys into incident tickets. Preserve UTC timestamps and cluster context for every evidence item.

## 5. Security operating controls

| Control | Operational check | Evidence |
|---|---|---|
| Workload identity | GKE principal and permitted cloud APIs | Identity mapping |
| Kafka authentication | Verified backend-supported mechanism | Positive/negative client test |
| Kafka authorization | Least-privilege topic/group ACLs | Denied unauthorized action |
| TLS | Certificate trust, SAN and expiration | Sanitized certificate metadata |
| Secret management | Rotation ownership and revocation plan | Rotation audit |
| Network isolation | Namespace policy, egress and private endpoint | Connectivity test |
| Audit | Administrative change history | Change IDs |
| Supply chain | Pinned container image, vulnerability review | Image digest and scan |
| Recovery | Secure backup keys and least privilege | Restore evidence |

Google Cloud IAM roles do not automatically map to Kafka ACL permissions for every backend. For managed Kafka, verify documented service-specific identity and authorization behavior.

## 6. Credential rotation protocol

Inventory consumers, producers, Kafka Connect and administration clients. Prepare replacement credentials in an approved secret store, distribute through the configured delivery mechanism, validate a canary client, roll clients safely, verify authentication and event correctness, revoke old credentials, and monitor for failures. Use overlapping validity only when supported and approved. Never commit credentials or client private keys to Git.

## 7. Upgrade strategy and compatibility gates

Build a matrix for the **current and target** GKE Kubernetes version, Strimzi operator version, Kafka version, KRaft metadata version, CRD schemas, CSI driver, TLS/cert-manager integration, JMX exporters and Kafka client versions. Check the official Strimzi-supported upgrade path, including any intermediate versions.

**Order is release-dependent:** do not blindly upgrade Kubernetes, Strimzi, Kafka and KRaft metadata in one change. Separate operator and broker changes when the compatibility matrix requires it. Do not finalize Kafka metadata-version upgrades until rollback consequences are understood.

## 8. Change-control run sequence

```text
approve scope / freeze conflicting changes
  → capture backup and recovery checkpoints
  → record quorum, ISR, disk and SLO baseline
  → review compatibility and release notes
  → stage upgrade and run smoke tests
  → canary and rolling change where supported
  → pause at each broker/controller health gate
  → verify clients, offsets and event-ID reconciliation
  → complete change record and monitor soak window
```

**Stop conditions:** loss of required controller quorum, sustained ISR degradation, critical disk pressure, widespread auth failure, unbounded consumer lag, unexpected data-integrity gaps or exhausted error budget. A version downgrade may be unsupported; the rollback plan must specify supported recovery or forward-fix paths.

## 9. GKE node maintenance

Review PodDisruptionBudgets, zone placement, broker/controller capacity, PVC topology, available resources and pending Pod scheduling. Avoid simultaneous disruption of controller majority or replica availability. Kubernetes voluntary eviction protections do not prevent involuntary node/zone failures. Verify Kafka and application health after each approved node operation.

## 10. Managed Kafka provider escalation

For Google Cloud Managed Service for Apache Kafka, do not attempt Strimzi broker commands or Kubernetes node operations against provider-managed infrastructure. Collect cluster ID, region, impact window, service metrics, quotas, client errors, request IDs and affected synthetic event IDs. Follow Google Cloud support procedures and document the provider/customer boundary. Confirm service-managed upgrade behavior from current product documentation.

## 11. Hands-on labs (20)

Every lab requires preconditions, exact approved commands or manifest, expected and observed result, evidence, rollback and PASS/FAIL. Publication does not imply lab execution.

| # | Lab | Evidence |
|---|---|---|
| 01 | Confirm GKE context and incident scope | Timestamped incident/change evidence, health gate and rollback |
| 02 | Inventory Kafka and Strimzi versions | Timestamped incident/change evidence, health gate and rollback |
| 03 | Inventory security principals and ACLs | Timestamped incident/change evidence, health gate and rollback |
| 04 | Verify broker TLS certificate expiry | Timestamped incident/change evidence, health gate and rollback |
| 05 | Review GKE workload identity bindings | Timestamped incident/change evidence, health gate and rollback |
| 06 | Inspect Kubernetes NetworkPolicies | Timestamped incident/change evidence, health gate and rollback |
| 07 | Capture Kafka ISR and controller baseline | Timestamped incident/change evidence, health gate and rollback |
| 08 | Capture producer and consumer SLO baseline | Timestamped incident/change evidence, health gate and rollback |
| 09 | Exercise incident severity classification | Timestamped incident/change evidence, health gate and rollback |
| 10 | Practice read-only incident evidence collection | Timestamped incident/change evidence, health gate and rollback |
| 11 | Validate credential rotation in staging | Timestamped incident/change evidence, health gate and rollback |
| 12 | Test unauthorized client denial | Timestamped incident/change evidence, health gate and rollback |
| 13 | Review Kafka upgrade compatibility matrix | Timestamped incident/change evidence, health gate and rollback |
| 14 | Dry-run Strimzi operator change review | Timestamped incident/change evidence, health gate and rollback |
| 15 | Validate broker rolling upgrade gates | Timestamped incident/change evidence, health gate and rollback |
| 16 | Validate GKE node maintenance gates | Timestamped incident/change evidence, health gate and rollback |
| 17 | Test consumer reconnect and recovery | Timestamped incident/change evidence, health gate and rollback |
| 18 | Test change abort and rollback decision | Timestamped incident/change evidence, health gate and rollback |
| 19 | Exercise provider escalation for managed Kafka | Timestamped incident/change evidence, health gate and rollback |
| 20 | Run incident closure and evidence audit | Timestamped incident/change evidence, health gate and rollback |

### Lab execution protocol

1. Verify isolated project, cluster context, change authority and budget.
2. Capture broker/controller/consumer baseline and accepted synthetic event IDs.
3. Execute one controlled scenario or change rehearsal.
4. Verify security, Kafka ISR/quorum, client health, lag and sink correctness.
5. Stop and revert if any critical gate fails.
6. Record evidence, reviewer sign-off and unresolved limitations.

## 12. Failure scenarios (12)

| # | Scenario | Containment and recovery |
|---|---|---|
| 1 | Controller quorum unavailable | Declare impact, isolate layer, preserve evidence, mitigate, reconcile and review |
| 2 | Broker ISR degradation | Declare impact, isolate layer, preserve evidence, mitigate, reconcile and review |
| 3 | Producer authorization outage | Declare impact, isolate layer, preserve evidence, mitigate, reconcile and review |
| 4 | TLS certificate expired | Declare impact, isolate layer, preserve evidence, mitigate, reconcile and review |
| 5 | Secret rotation breaks clients | Declare impact, isolate layer, preserve evidence, mitigate, reconcile and review |
| 6 | Consumer lag and DLQ spike | Declare impact, isolate layer, preserve evidence, mitigate, reconcile and review |
| 7 | Operator reconciliation stuck | Declare impact, isolate layer, preserve evidence, mitigate, reconcile and review |
| 8 | Kafka version incompatibility | Declare impact, isolate layer, preserve evidence, mitigate, reconcile and review |
| 9 | GKE node drain stalls | Declare impact, isolate layer, preserve evidence, mitigate, reconcile and review |
| 10 | Persistent volume unavailable | Declare impact, isolate layer, preserve evidence, mitigate, reconcile and review |
| 11 | Managed Kafka service degradation | Declare impact, isolate layer, preserve evidence, mitigate, reconcile and review |
| 12 | Post-upgrade missing accepted events | Declare impact, isolate layer, preserve evidence, mitigate, reconcile and review |

Each scenario requires severity, blast radius, timeline, owner, expected alert, actual observations, stop criteria, communications, recovery verification and preventive action.

## 13. SRE runbooks (8)

| # | Runbook | Workflow |
|---|---|---|
| 1 | Kafka SEV1 incident command | Impact → evidence → authorization → safe change → verify SLO/data → RCA |
| 2 | Authentication and ACL incident | Impact → evidence → authorization → safe change → verify SLO/data → RCA |
| 3 | TLS and secret rotation | Impact → evidence → authorization → safe change → verify SLO/data → RCA |
| 4 | Strimzi operator upgrade | Impact → evidence → authorization → safe change → verify SLO/data → RCA |
| 5 | Kafka broker rolling upgrade | Impact → evidence → authorization → safe change → verify SLO/data → RCA |
| 6 | GKE node maintenance | Impact → evidence → authorization → safe change → verify SLO/data → RCA |
| 7 | Managed Kafka provider escalation | Impact → evidence → authorization → safe change → verify SLO/data → RCA |
| 8 | Rollback and post-incident review | Impact → evidence → authorization → safe change → verify SLO/data → RCA |

Runbooks must include an incident commander, on-call contacts, safe read-only commands, change approval, rollback authority, escalation and evidence retention.

## 14. 100-point incident/change acceptance

| Gate | Points |
|---|---:|
| Incident command and severity handling | 15 |
| Evidence collection and diagnostics | 15 |
| Identity, TLS and least privilege | 15 |
| Credential rotation and security response | 10 |
| Upgrade compatibility and change gates | 15 |
| GKE/Strimzi rolling maintenance | 10 |
| Event reconciliation and SLO verification | 15 |
| Independent review and audit trail | 5 |
| **Total** | **100** |

**Proposed pass:** ≥85/100 with no critical security finding, approved change/rollback, preserved Kafka durability, zero unexplained missing accepted IDs and independent review. Publishing this chapter does not certify runtime readiness.

## 15. Evidence manifest

```yaml
chapter: 119
environment: isolated-gke-kafka-operations
backend: REPLACE_STRIMZI_OR_MANAGED
gke_version: REPLACE
strimzi_version: REPLACE
kafka_version: REPLACE
target_versions: []
incident_scenarios: []
security_tests: []
change_approvals: []
upgrade_compatibility_matrix: []
controller_quorum_healthy: null
isr_healthy: null
missing_accepted_ids: null
observed_slo: null
lab_results: []
technical_review: pending
security_review: pending
runtime_certified: false
```

## 16. Next chapter

**Chapter 120 — Google Cloud Kafka Enterprise Production Capstone and Acceptance.**
