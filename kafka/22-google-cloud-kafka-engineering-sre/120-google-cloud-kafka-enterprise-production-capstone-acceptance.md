# Chapter 120 — Google Cloud Kafka Enterprise Production Capstone and Acceptance

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 22 — Google Cloud Kafka Engineering & SRE (10/10)  
**Chapter:** 120 of 120 — final canonical chapter  
**Platforms:** GKE + Strimzi Kafka KRaft; Google Cloud Managed Service for Apache Kafka where verified  
**Prerequisites:** Chapters 001–119, isolated GCP lab, approved budget, documented access and security controls  
**Publication:** Published · **Live lab validation:** Pending · **Independent technical/security review:** Pending · **Runtime certification:** Not claimed

> **Critical distinction:** 120 chapters published is a documentation milestone, **not** evidence that 120 chapters' labs were executed or that any cluster is production certified. The final capstone is a proposed acceptance procedure requiring independently collected runtime evidence. Use synthetic data; do not run destructive failure drills or region cutovers in production.

## 1. Mission and success criteria

Demonstrate an auditable, end-to-end Kafka service operated from Kubernetes, including secure identity, topic and event contracts, reliable producers and consumers, observable SLOs, capacity headroom, multi-zone availability, backup and disaster recovery, change management and incident response.

**Exit criteria:** every mandatory gate has evidence; no unexplained loss of acknowledged events; no critical unresolved security finding; approved RPO/RTO achieved in a tested recovery; independent SRE, security and application-owner sign-off; explicit GO / CONDITIONAL GO / NO-GO decision.

## 2. Enterprise reference architecture

```text
Google Cloud organization / approved project / VPC
  GKE cluster: kafka-apps namespace
    ├── producer Job/Deployment (synthetic, version-pinned)
    ├── consumer Deployment + idempotent durable sink
    ├── durable DLQ and reconciliation ledger
    ├── workload identity + approved secret delivery
    └── Prometheus client telemetry / alert routing
                 |
             TLS + authorization
                 |
       Kafka backend selection
        ├── GKE Strimzi KRaft
        │    ├── controller quorum distributed across zones
        │    ├── brokers with verified rack-aware replicas
        │    └── CSI-backed storage and supported backup
        └── Google Cloud Managed Service for Apache Kafka
             └── service-supported APIs, identity, quotas, metrics
                 |
       consumer checkpoint and sink recovery
                 |
       off-cluster recovery / regional DR
                 |
       SLOs + audit evidence + on-call runbooks
```

Do not infer managed Kafka support for every Strimzi feature or Kafka Admin API. Document the actual service region, client versions, auth mechanism, exposed metrics, quotas, topic configs, backup and DR support.

## 3. Responsibility and dependency register

| Domain | Strimzi/GKE owner | Managed Kafka owner | Mandatory evidence |
|---|---|---|---|
| Broker/controller lifecycle | Kafka platform | Cloud provider | Supported release and health |
| GKE producer/consumer | App/platform | App/platform | Deployment and image digests |
| Network and identity | Platform/security | Shared | Positive and denied auth tests |
| Topic/data contract | Data owner | Data owner | Versioned topic/schema contract |
| Producer and sink correctness | App/data owner | App/data owner | Event-ID reconciliation |
| Storage and quotas | Kafka/platform | Shared | Capacity/limit inventory |
| Monitoring/SLOs | SRE | SRE + provider metrics | Tested alert delivery |
| Backup and DR | SRE/platform | Verify documented service capability | Measured restore, RPO/RTO |
| Change and incident response | SRE/security | SRE/provider | Runbook, timeline, approval |

## 4. Safe PowerShell preflight

```powershell
gcloud config get-value project
gcloud auth list
gcloud container clusters list
kubectl config current-context
kubectl get nodes -L topology.kubernetes.io/zone
kubectl get kafka,kafkanodepool,kafkatopic,kafkauser -n kafka
kubectl get pods,pvc,pdb -n kafka -o wide
kubectl get deployments -n kafka-apps
kubectl get networkpolicy -A
kubectl get events -n kafka --sort-by=.lastTimestamp
```

The Strimzi resource commands require installed CRDs and apply only to Strimzi deployments. Verify Kubernetes context before any mutation. Preserve output with UTC timestamps and redact project-sensitive information.

## 5. Synthetic event acceptance contract

Use an immutable `event_id`, `aggregate_id`, `sequence`, `schema_version`, UTC timestamp and payload hash. Never use real patient data. Record successfully acknowledged IDs outside Kafka in an independent ledger. A consumer applies effects idempotently and commits offsets only after durable sink or approved durable quarantine.

```text
accepted_unique_ids = IDs of acknowledged producer records
resolved_unique_ids = unique sink-effect IDs UNION durable DLQ IDs
missing_ids = accepted_unique_ids MINUS resolved_unique_ids
duplicate_external_effects = sink effect counts above 1 per event_id
```

**Mandatory:** no unexplained missing accepted IDs; any DLQ IDs must be tracked as unresolved business outcomes; per-aggregate ordering must meet the documented contract. A zero consumer-lag metric alone is not evidence of correctness.

## 6. Infrastructure and security gates

- Verify controller majority survives the approved single-zone failure scenario and that broker replicas are distributed across intended zones.
- Confirm ISR, `acks=all`, replication and `min.insync.replicas` satisfy the chosen durability contract.
- Check PVC topology, free-space runway, disk latency, IOPS and throughput.
- Validate Kafka ACLs, GKE workload identity, TLS hostname/certificate chain, secret rotation and private network reachability.
- Deny unauthorized topic/group operations; retain audit evidence without leaking credentials.
- For managed Kafka, verify the service's actual capabilities and shared-responsibility boundaries rather than applying Strimzi assumptions.

## 7. Reliability and performance gates

Measure at steady state and controlled peak: producer acceptance, p95/p99 latency, retry rate, partition skew, consumer lag age, sink processing latency, DLQ volume, broker/controller health, storage saturation and GKE resource limits. Compare observed results against approved targets rather than generic Kafka benchmarks. Reconcile accepted IDs at the end of each test.

## 8. Disaster recovery and upgrade gates

Perform only approved, isolated failure tests. Validate restore of event data, topic configuration, authorization, application checkpoint, sink and keys. Measure actual RPO/RTO with independent timestamps and event-ID sets. Test fencing before regional promotion and avoid dual-active writers. Confirm Kafka/Strimzi/GKE upgrade compatibility and distinguish reversible application rollback from potentially irreversible metadata upgrades.

## 9. Twenty capstone labs

Every lab requires prerequisites, exact versioned command or manifest, expected result, observed result, timestamps, sanitized evidence, rollback, cleanup, reviewer and PASS/FAIL. The entries below are an acceptance execution register, **not claims of completed execution**.

| # | Lab | Acceptance evidence |
|---|---|---|
| 01 | Confirm GCP project, budget and GKE context | Timestamped outputs, pass/fail, reviewer and rollback |
| 02 | Record Strimzi, Kafka and GKE version matrix | Timestamped outputs, pass/fail, reviewer and rollback |
| 03 | Verify broker and controller zone distribution | Timestamped outputs, pass/fail, reviewer and rollback |
| 04 | Inspect quorum, ISR and replication | Timestamped outputs, pass/fail, reviewer and rollback |
| 05 | Validate PVC, capacity and disk latency | Timestamped outputs, pass/fail, reviewer and rollback |
| 06 | Verify managed Kafka feature compatibility | Timestamped outputs, pass/fail, reviewer and rollback |
| 07 | Validate workload identity and authentication | Timestamped outputs, pass/fail, reviewer and rollback |
| 08 | Test Kafka topic/group least privilege | Timestamped outputs, pass/fail, reviewer and rollback |
| 09 | Verify TLS, network isolation and secret rotation | Timestamped outputs, pass/fail, reviewer and rollback |
| 10 | Deploy version-pinned synthetic producer | Timestamped outputs, pass/fail, reviewer and rollback |
| 11 | Validate acks, idempotence and ordering | Timestamped outputs, pass/fail, reviewer and rollback |
| 12 | Deploy idempotent consumer and durable sink | Timestamped outputs, pass/fail, reviewer and rollback |
| 13 | Validate poison event quarantine and DLQ | Timestamped outputs, pass/fail, reviewer and rollback |
| 14 | Reconcile accepted event IDs end-to-end | Timestamped outputs, pass/fail, reviewer and rollback |
| 15 | Verify metrics coverage and alert delivery | Timestamped outputs, pass/fail, reviewer and rollback |
| 16 | Measure load, p99 latency and lag | Timestamped outputs, pass/fail, reviewer and rollback |
| 17 | Rehearse broker/zone failure in isolated lab | Timestamped outputs, pass/fail, reviewer and rollback |
| 18 | Execute backup/restore and measure RPO/RTO | Timestamped outputs, pass/fail, reviewer and rollback |
| 19 | Run incident and rollback tabletop | Timestamped outputs, pass/fail, reviewer and rollback |
| 20 | Conduct independent acceptance and evidence audit | Timestamped outputs, pass/fail, reviewer and rollback |

### Lab execution workflow

1. Obtain change approval and confirm isolated cluster, budget, owner and safety stop conditions.
2. Record version, image digest, GCP region, topology and baseline SLOs.
3. Generate a bounded synthetic event set and independently record acknowledgements.
4. Execute exactly one approved lab or failure scenario; collect metrics, logs and checkpoints.
5. Verify Kafka health, client authentication, sink durability and event-ID reconciliation.
6. Measure recovery and cost impact; revert lab-only changes.
7. Attach redacted evidence and require an independent reviewer to sign off.

## 10. Twelve incident and failure scenarios

| # | Scenario | Required decision |
|---|---|---|
| 1 | GKE node disruption | Detect → contain → recover → reconcile → assess SLO/RPO/RTO → RCA |
| 2 | KRaft quorum degradation | Detect → contain → recover → reconcile → assess SLO/RPO/RTO → RCA |
| 3 | Broker ISR loss | Detect → contain → recover → reconcile → assess SLO/RPO/RTO → RCA |
| 4 | Disk IOPS or PVC exhaustion | Detect → contain → recover → reconcile → assess SLO/RPO/RTO → RCA |
| 5 | Producer authentication failure | Detect → contain → recover → reconcile → assess SLO/RPO/RTO → RCA |
| 6 | TLS certificate expiry | Detect → contain → recover → reconcile → assess SLO/RPO/RTO → RCA |
| 7 | Consumer rebalance storm | Detect → contain → recover → reconcile → assess SLO/RPO/RTO → RCA |
| 8 | Poison record and DLQ backlog | Detect → contain → recover → reconcile → assess SLO/RPO/RTO → RCA |
| 9 | Schema incompatibility | Detect → contain → recover → reconcile → assess SLO/RPO/RTO → RCA |
| 10 | Managed Kafka quota/service incident | Detect → contain → recover → reconcile → assess SLO/RPO/RTO → RCA |
| 11 | Regional DR cutover with fencing | Detect → contain → recover → reconcile → assess SLO/RPO/RTO → RCA |
| 12 | Post-upgrade missing accepted events | Detect → contain → recover → reconcile → assess SLO/RPO/RTO → RCA |

For every scenario, document severity, blast radius, alert detection time, owner, escalation, stop criteria, recovery timeline, evidence and preventive controls. Do not perform production chaos tests as part of curriculum acceptance.

## 11. Eight production runbooks

| # | Runbook | Mandatory workflow |
|---|---|---|
| 1 | SEV1 incident command | Impact → read-only diagnosis → approved action → verify event correctness → close/RCA |
| 2 | Kafka quorum and ISR restoration | Impact → read-only diagnosis → approved action → verify event correctness → close/RCA |
| 3 | Client identity/TLS recovery | Impact → read-only diagnosis → approved action → verify event correctness → close/RCA |
| 4 | Producer and consumer reliability | Impact → read-only diagnosis → approved action → verify event correctness → close/RCA |
| 5 | Persistent storage capacity incident | Impact → read-only diagnosis → approved action → verify event correctness → close/RCA |
| 6 | Backup/DR failover and failback | Impact → read-only diagnosis → approved action → verify event correctness → close/RCA |
| 7 | Upgrade change and rollback | Impact → read-only diagnosis → approved action → verify event correctness → close/RCA |
| 8 | Final production acceptance decision | Impact → read-only diagnosis → approved action → verify event correctness → close/RCA |

Runbooks must identify decision authority, communication owner, safe commands, rollback or forward-recovery path, provider escalation, evidence retention and exit criteria.

## 12. Final 100-point acceptance scorecard

| Gate | Points | Mandatory? |
|---|---:|---|
| Architecture, version and ownership inventory | 10 | Yes |
| Kubernetes and Kafka health / HA topology | 15 | Yes |
| IAM, TLS, ACLs, secrets and network security | 15 | Yes |
| Producer/consumer event correctness | 20 | Yes |
| Observability, alerts and SLO evidence | 10 | Yes |
| Capacity, performance and FinOps | 10 | Yes |
| Backup, DR and measured RPO/RTO | 10 | Yes |
| Incident/change operations and rollback | 5 | Yes |
| Independent evidence and approvals | 5 | Yes |
| **Total** | **100** | |

**Proposed decision:** GO only at ≥90/100 with all mandatory gates passed, no critical unresolved security issues, zero unexplained missing acknowledged events, tested DR within approved objectives and independent sign-off. CONDITIONAL GO requires written risk acceptance for noncritical gaps. Otherwise NO-GO.

## 13. Audit-ready evidence manifest

```yaml
curriculum: kafka-administration-sre-platform-engineering
chapter: 120
documentation_published_chapters: 120
documentation_total_chapters: 120
lab_validation_status: pending
environment: isolated-gke-kafka-capstone
gcp_project: REDACTED
region: REPLACE
backend: REPLACE_STRIMZI_OR_MANAGED
kafka_version: REPLACE
strimzi_version: REPLACE_IF_APPLICABLE
gke_version: REPLACE
client_image_digests: []
compatibility_matrix: []
security_tests: []
producer_accepted_unique_ids: null
sink_resolved_unique_ids: null
durable_dlq_unique_ids: null
missing_accepted_ids: null
duplicate_external_effects: null
observed_slos: {}
observed_rpo_seconds: null
observed_rto_seconds: null
failure_scenarios: []
lab_results: []
acceptance_score: null
decision: NOT_ASSESSED
technical_reviewer: pending
security_reviewer: pending
application_owner: pending
runtime_certified: false
```

## 14. Curriculum completion and next phase

**Documentation milestone:** 120/120 canonical chapters published, subject to a separate repository-wide completeness and link audit.

**Validation milestone:** Not complete. Execute labs, validate manifests and commands, inspect version compatibility, test failure scenarios and preserve evidence.

**Certification milestone:** Not complete. Require independent review, signed acceptance scorecard and measured runtime recovery/correctness before describing any environment as production ready.

### Recommended QA campaign

1. Inventory all 120 chapter files and detect missing/duplicate chapter numbers.
2. Validate README and STATUS links, headings and common chapter structure.
3. Lint YAML, shell and PowerShell examples in safe isolated runners.
4. Verify current Kafka, Strimzi, GKE and managed Kafka compatibility.
5. Execute bounded labs chapter by chapter, collect PASS/FAIL and remediate defects.
6. Run end-to-end capstone and independent security/SRE acceptance.
7. Publish an evidence-backed validation report distinct from publication status.

**End of Chapter 120 — end of the 120-chapter curriculum publication sequence.**
