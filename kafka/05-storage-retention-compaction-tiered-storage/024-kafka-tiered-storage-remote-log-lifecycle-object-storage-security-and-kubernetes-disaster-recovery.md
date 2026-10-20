# Chapter 024 — Kafka Tiered Storage, Remote Log Lifecycle, Object Storage Security and Kubernetes Disaster Recovery

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 05 — Storage, Retention, Compaction and Tiered Storage (4/5)  
**Platform:** Kubernetes + Strimzi Operator + Kafka KRaft  
**Prerequisites:** Chapters 011–023; working Kafka lab, storage monitoring, and familiarity with retention/compaction  
**Audience:** Kafka SREs, DBREs, cloud storage engineers, security and disaster-recovery teams  
**Status:** Published · Live execution pending · Independent security review pending

> **Critical compatibility gate:** Apache Kafka tiered/remote log storage depends on Kafka release, a compatible `RemoteStorageManager` implementation, Strimzi support for the required broker configuration and plugin packaging, and the cloud/object-store provider. **There is no universal built-in S3/GCS/Azure plugin that can be assumed to work.** This chapter separates executable read-only Kubernetes labs from **conditional integration labs** that must remain Pending until a supported plugin and isolated bucket are provided. Never enable remote storage on production brokers or delete bucket objects as a lab shortcut.

## 1. Learning objectives

By the end you can:

1. Explain local versus remote Kafka log segment lifecycle and metadata.
2. Identify Kafka remote-log feature, plugin, broker and Strimzi compatibility requirements.
3. Distinguish local retention, total retention, remote-copy eligibility and compaction limitations.
4. Design least-privilege object storage, workload identity, encryption, audit and bucket isolation.
5. Plan read performance, object-store costs, failure domains and egress.
6. Define Kafka/Kubernetes recovery boundaries and why tiered storage is **not** a substitute for a DR backup.
7. Implement an isolated compatibility preflight and optional integration validation.
8. Diagnose remote-copy failures, object-store access issues, replay latency and metadata recovery.
9. Produce operational runbooks, a 100-point acceptance score and auditable evidence.

## 2. Reference architecture

```text
  Producers / Consumers
          |
  Kafka bootstrap Service
          |
  Strimzi-managed KRaft brokers (Kubernetes Pods)
          |
  Partition append-only logs
          |
   active local segment
          |
   rolled closed segment
          |
  remote log copy manager + plugin
          |
  Object-store API (private endpoint / TLS)
          |
  bucket/container with remote segment objects
          |
  remote metadata and retention/deletion lifecycle
          |
  consumer remote reads / recovery of eligible history

  Kafka metadata quorum, topic metadata, consumer offsets,
  security policy, object-store identity and broker PVCs
  remain separate dependencies that must be protected.
```

Remote segments supplement Kafka's local log storage. A remote segment object without the associated Kafka metadata, topic identity, access permissions and a compatible broker implementation is **not** a portable Kafka backup that can simply be mounted into a new cluster.

## 3. Kafka tiered-storage lifecycle

1. Producer writes to a partition leader's active local log.
2. Replication and ISR rules protect durability across brokers.
3. Segments roll and become candidates for offload, subject to remote-log configuration and plugin behavior.
4. Remote-log manager copies eligible closed segments and manages their metadata.
5. Local segments may become eligible for local deletion under the configured local retention policy.
6. Consumers requesting older retained offsets may fetch from remote storage.
7. Overall retention eventually makes remote history eligible for deletion.
8. Recovery depends on both Kafka cluster metadata and the remote-log implementation.

**Do not confuse** remote retention with object-store lifecycle rules. A bucket rule that deletes Kafka objects independently of Kafka's remote metadata management can corrupt remote-read availability.

## 4. Compatibility and release gates

Before enabling tiered storage, establish:

| Gate | Evidence required | No-go condition |
|---|---|---|
| Kafka broker version | Exact Kafka release and remote-log support matrix | Unsupported release |
| Strimzi version | Operator version, Kafka version, supported broker configuration and image customization | Required configuration filtered/unsupported |
| RemoteStorageManager | Provider implementation, artifact version, support policy and integrity provenance | No reviewed implementation |
| Remote metadata | Compatible metadata manager and upgrade/recovery procedure | Undefined metadata durability |
| Object storage | Isolated bucket, provider API, private endpoint, encryption | Shared production bucket |
| Workload identity | Approved Pod service account and least-privilege permissions | Static cloud credentials in manifests |
| Feature limits | Compaction, topic deletion, transactions and version-specific restrictions reviewed | Workload requires unsupported feature |
| Rollback | Documented reversibility and object-retention consequences | Unclear downgrade path |

**Version-specific note:** configuration names and feature maturity vary. Consult the **exact installed release** documentation for `remote.log.storage.system.enable`, `remote.storage.enable`, `local.retention.ms`, `local.retention.bytes` and provider-specific manager settings. These names are examples to validate, **not** a copy-paste universal configuration.

## 5. Retention semantics across tiers

| Concern | Local storage | Remote storage |
|---|---|---|
| Active segment | Always local for writes | Not a live-write target |
| Rolled segment | Candidate for local retention cleanup | Candidate for remote copy when supported |
| Replay latency | Typically local disk/network | Adds remote API, network and caching costs |
| Capacity | Broker PVCs, per-broker skew | Object count, bytes and provider quotas |
| Failure modes | CSI, disk, node, broker | IAM, endpoint, throttling, bucket policy, metadata |
| Deletion | Kafka segment lifecycle | Kafka remote-log lifecycle plus provider retention |
| Recovery | Replicas and supported storage recovery | Requires compatible Kafka remote metadata and credentials |

Local retention should never be shorter than the tested operational requirements for remote-copy completion and recovery. Kafka configuration validation can impose constraints between local and overall retention.

## 6. Tiered storage is not a backup or full disaster recovery

Remote segments do not independently protect:

- Kafka KRaft metadata quorum and cluster identity.
- Topic definitions, ACLs, quotas and operator/GitOps manifests.
- Consumer offsets, transaction state and application state.
- Object-store credentials, identity policies, encryption keys and private network access.
- Correlated cloud-region outages or provider account compromise.
- Producer source data not yet copied to remote storage.

For DR, design replication to an independent cluster/region, recoverable metadata and configuration, independently governed object storage, documented RPO/RTO, and restore/replay tests. Never claim zero RPO or seamless cross-region failover merely because remote log storage is configured.

## 7. Kubernetes-first lab prerequisites and stop conditions

The shared foundation uses namespace `kafka-lab`, Strimzi cluster `sre-kafka`, CLI Pod `kafka-cli`, bootstrap `sre-kafka-kafka-bootstrap:9092`.

```bash
kubectl config current-context
kubectl -n kafka-lab get kafka,kafkanodepool,pods,pvc -o wide
kubectl -n kafka-lab wait kafka/sre-kafka --for=condition=Ready --timeout=900s
kubectl -n kafka-lab get pod kafka-cli
mkdir -p evidence-ch24
```

**Stop** if the environment is production, the cluster lacks healthy RF3/ISR, no reviewed remote manager exists, or the bucket is not explicitly disposable. Labs A–F and J–L are safe metadata/design exercises; G–I are conditional and require approved integration infrastructure.

## 8. Lab A — Capture exact Kafka and Strimzi versions

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh --version \
  | tee evidence-ch24/kafka-client-version.txt

kubectl -n kafka-lab get kafka sre-kafka -o yaml \
  > evidence-ch24/kafka-cr.yaml
kubectl -n kafka-lab get kafkanodepool -o yaml \
  > evidence-ch24/nodepools.yaml
kubectl -n kafka-lab get pods -o wide \
  > evidence-ch24/pods.txt
kubectl -n kafka-lab get deploy -o wide \
  > evidence-ch24/operators.txt
```

The Kafka CLI version is **not sufficient evidence** of the broker version; inspect the Kafka CR, broker image digest and supported Kafka version in the installed Strimzi release.

**Acceptance:** compatibility matrix includes Kafka broker version, Strimzi operator version, plugin implementation/version, remote metadata manager and upgrade support.

## 9. Lab B — Read-only storage and replica baseline

```bash
kubectl -n kafka-lab get pvc -o wide \
  | tee evidence-ch24/pvc-baseline.txt
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 describe --status \
  | tee evidence-ch24/kraft-quorum.txt
kubectl -n kafka-lab get events --sort-by=.lastTimestamp \
  > evidence-ch24/events.txt
```

Collect actual per-broker filesystem free bytes, local log bytes, ISR and partition leader metrics from the installed monitoring stack. PVC capacity alone does not measure available disk.

**Acceptance:** broker/PVC baseline and current recovery headroom documented; no remote feature toggles.

## 10. Lab C — Build an object-store threat model

Identify threats and mitigations:

| Threat | Control |
|---|---|
| Stolen broker credentials | Workload identity, short-lived credentials, scoped service account |
| Bucket overwrite/deletion | Least-privilege write/delete permissions, independent backup and change review |
| Public exposure | Block public access, private endpoint, network egress controls |
| Data exfiltration | TLS, IAM conditions, audit logs, encryption and egress monitoring |
| Encryption-key loss | KMS key ownership, rotation and recovery plan |
| Unbounded object count | Quotas, request-rate monitoring, object-size forecasting |
| Unreviewed lifecycle deletion | Bucket lifecycle policy review; never bypass Kafka retention metadata |
| Cross-environment contamination | Separate bucket/prefix, identities, accounts/projects |

**Acceptance:** signed-off threat model with owner, cloud account, bucket classification and audit retention.

## 11. Lab D — Design a Kubernetes workload identity

Example **illustrative** Pod service-account mapping:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: kafka-remote-storage
  namespace: kafka-lab
  annotations:
    # Provider-specific annotation goes here only after security review.
    # Do not put access keys or secrets into annotations.
    sre.example.com/purpose: remote-log-storage-lab
```

Do not apply this service account to Kafka brokers blindly: Strimzi-supported service account customization and identity injection are release-specific. Validate the exact operator's Pod template/identity mechanism. For EKS use IRSA or EKS Pod Identity as supported; for AKS use workload identity; for GKE use Workload Identity Federation.

**Acceptance:** a documented broker-to-bucket identity chain and denied-access tests in an isolated environment. No embedded cloud credentials.

## 12. Lab E — Create a remote storage cost and capacity model

Estimate:

```text
remote_ingest_bytes_per_day
  ≈ sustained_ingest_bytes_per_second × 86400 × copy_factor

remote_retained_bytes
  ≈ remote_ingest_bytes_per_day × remote_retention_days

monthly_cost
  ≈ object_storage_GB_month
   + PUT/GET/LIST requests
   + remote reads / data transfer / egress
   + encryption/KMS requests
   + observability and recovery overhead
```

**Example:** 8 MiB/s sustained, one remote copy per eligible segment, 30-day remote retention:

```text
8 MiB/s × 86400 ≈ 675 GiB/day
675 GiB/day × 30 ≈ 19.8 TiB remote logical footprint
```

This is a **planning estimate**, not an exact bill. Segment duplication, retries, metadata, compression, replication implementation and provider billing can change the outcome.

**Acceptance:** forecast includes per-request pricing, cache miss ratio, cross-zone/region egress and worst-case recovery read traffic.

## 13. Lab F — Review a conditional integration manifest

The following is **illustrative only** and intentionally not a complete deployable Kafka CR:

```yaml
# PSEUDOCONFIG — do not apply without release/plugin validation
kafka:
  config:
    remote.log.storage.system.enable: true
    # RemoteStorageManager classpath and plugin-specific settings
    # must be validated against the exact Kafka/Strimzi releases.
topic:
  config:
    remote.storage.enable: true
    # local.retention.ms / local.retention.bytes require
    # explicit relationship checks against total retention.
```

**Acceptance:** a reviewed actual configuration artifact, pinned image/plugin digests, Strimzi-compatible image build procedure and rollback plan. **No unverified remote-manager class name or public image tag is supplied.**

## 14. Lab G — Conditional disposable bucket and identity setup

**Prerequisite:** approved cloud sandbox and reviewed remote-log implementation.

1. Provision an isolated object-store bucket/container via your organization's Terraform/GitOps modules.
2. Enable encryption, block public access, audit logs and private connectivity.
3. Create a least-privilege workload identity for Kafka broker Pods.
4. Verify denied access from unrelated namespaces and principals.
5. Record bucket ID, region, lifecycle controls and deletion protections.
6. Confirm no production topic or cluster points at the test bucket.

**Acceptance:** policy tests, audit events, approved infrastructure change and clean-room isolation. If the prerequisites are absent, record **Not Executed**.

## 15. Lab H — Conditional remote log integration and offload

**Prerequisite:** successful Lab G and a validated Kafka/Strimzi/plugin compatibility matrix.

1. Deploy the reviewed remote manager with a pinned Kafka broker image.
2. Configure remote storage through supported Strimzi mechanisms.
3. Create a **new disposable topic** with supported remote-storage settings and RF3/minISR2.
4. Produce deterministic keyed/unkeyed events and record offsets.
5. Roll a segment through supported topic settings and controlled append traffic.
6. Observe plugin remote-copy success metrics and remote metadata.
7. Confirm objects exist in the isolated bucket and their access is restricted.
8. Verify the broker and KafkaTopic remain Ready with full ISR.

**Acceptance:** object inventory, remote metadata, broker/plugin logs, copy latency, event IDs and end offsets. A bucket object by itself does not prove Kafka can read it.

## 16. Lab I — Conditional remote-read and recovery validation

**Prerequisite:** remote offload proven in Lab H, approved local retention policy and nonproduction cluster.

1. Capture exact partition earliest/latest offsets and event checksums.
2. Wait for eligible local segments to be removed by Kafka's normal retention process; do **not** delete local files.
3. Read older retained offsets through a new consumer group.
4. Validate payload IDs and checksums against pre-offload evidence.
5. Inject an **application consumer Pod restart**, not broker/PVC deletion.
6. Re-read remote-backed history and measure p95/p99 latency.
7. Simulate object-store access denial **only through approved sandbox IAM policy controls**.
8. Restore access, verify Kafka errors clear and record recovery duration.

**Acceptance:** verified remote reads, no missing/duplicate logical records in the test window, security audit trail and measured recovery. If no local retention expiry occurred, remote-read proof remains Pending.

## 17. Lab J — DR tabletop: region outage and metadata loss

Scenario: the primary region fails while historical segments exist in remote object storage.

Assess:

- Is the bucket in the same region, or independently replicated?
- Is KRaft metadata recoverable and cluster identity preserved?
- Are consumer offsets, topic configurations and ACLs recoverable?
- Does the remote manager support the intended cross-cluster/region recovery workflow?
- Can encryption keys and workload identity be restored independently?
- What data exists only in local active segments and therefore falls within RPO risk?
- What are measured RTO/RPO and replay validation criteria?

**Acceptance:** a recovery architecture diagram, dependency matrix, explicit unsupported scenarios and a test plan. Never assume remote segment objects can be attached to a different Kafka cluster.

## 18. Lab K — Observability and alert mapping

Monitor:

- Remote segment copy success/failure rate, bytes and latency.
- Remote read latency, cache misses, request throttling and errors.
- Remote-log metadata manager health and backlog.
- Local disk free bytes, segment counts and log-start movement.
- Kafka ISR, offline partitions, leader availability and consumer event age.
- Object-store bucket size, request counts, IAM denials, KMS failures and egress cost.
- Kubernetes broker Pod health, CSI events, PVC pressure and network policies.

Metric names depend on Kafka release, plugin and exporter. Record actual metric labels rather than inventing a universal Prometheus expression.

**Acceptance:** dashboard/alert inventory with source, owner, severity, SLO threshold and incident routing.

## 19. Lab L — Automated read-only compatibility preflight

Save `verify-ch24.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
CLUSTER=sre-kafka
BS=sre-kafka-kafka-bootstrap:9092
BIN=/opt/kafka/bin

echo '[1/6] Kubernetes context and cluster'
kubectl config current-context
kubectl -n "$NS" wait "kafka/$CLUSTER" --for=condition=Ready --timeout=120s

echo '[2/6] Kafka CR version and node pools'
kubectl -n "$NS" get kafka "$CLUSTER" \
  -o jsonpath='{.spec.kafka.version}{"\n"}'
kubectl -n "$NS" get kafkanodepool -o wide

echo '[3/6] Kafka CLI version (not broker proof)'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-topics.sh" --version

echo '[4/6] Metadata quorum'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-metadata-quorum.sh" \
  --bootstrap-server "$BS" describe --status

echo '[5/6] PVC and broker Pod inventory'
kubectl -n "$NS" get pvc -o wide
kubectl -n "$NS" get pods -o wide

echo '[6/6] Topic CRD API versions'
kubectl get crd kafkatopics.kafka.strimzi.io \
  -o jsonpath='{.spec.versions[*].name}{"\n"}'

echo 'PASS: read-only baseline. Remote manager compatibility, offload, reads, IAM and DR are NOT tested.'
```

```bash
chmod +x verify-ch24.sh
./verify-ch24.sh | tee evidence-ch24/metadata-preflight.txt
```

**Important:** this script verifies only Kubernetes/Kafka metadata accessibility. It does not install a plugin, provision a bucket, test remote copies or establish disaster-recovery readiness.

## 20. Ten production failure scenarios

### 20.1 Remote manager incompatible with broker version

**Signal:** broker startup errors or remote storage initialization failure.

**Diagnose:** pinned Kafka/plugin versions, classpath, Strimzi configuration support.

**Mitigate:** revert only through documented supported rollout; preserve broker and metadata state.

### 20.2 Object-store IAM denied

**Signal:** 403/permission errors on remote writes/reads.

**Diagnose:** workload identity binding, bucket policy, KMS permissions, audit logs.

**Mitigate:** restore least-privilege permissions, verify remote-copy backlog.

### 20.3 Object-store throttling

**Signal:** 429/503 responses, increased remote-read latency.

**Diagnose:** request rate, concurrency, retry/backoff and provider limits.

**Mitigate:** bounded retries, rate control, capacity planning and alerting.

### 20.4 Local retention outruns remote copy

**Signal:** missing historical offsets or remote-copy backlog.

**Diagnose:** copy success metadata, segment eligibility, local retention.

**Mitigate:** stop unsafe policy changes and restore a supported retention/copy relationship; evaluate data loss.

### 20.5 Bucket lifecycle deletes Kafka objects independently

**Signal:** remote-read failures despite retained Kafka offsets.

**Diagnose:** bucket lifecycle/audit events and remote metadata references.

**Mitigate:** halt external deletion, recover from independent backup if possible, correct governance.

### 20.6 KMS key unavailable

**Signal:** object decrypt/access failures.

**Diagnose:** KMS grants, key status, region and identity.

**Mitigate:** restore authorized key access; do not disable encryption as a shortcut.

### 20.7 Network partition to object store

**Signal:** copy/read timeouts while local broker is healthy.

**Diagnose:** DNS, private endpoint, egress policy, TLS, proxy and routing.

**Mitigate:** restore connectivity, monitor backlog and consumer SLO.

### 20.8 Cross-region failover lacks metadata

**Signal:** remote objects exist but new Kafka cluster cannot locate/read them.

**Diagnose:** metadata manager recovery and supported cluster identity model.

**Mitigate:** execute tested DR workflow; do not import raw objects manually.

### 20.9 Remote read storm causes unexpected cost

**Signal:** GET and egress charges spike after consumer replay.

**Diagnose:** cache hit ratio, replay groups, data locality and fetch size.

**Mitigate:** schedule/throttle replay within business RTO and budget.

### 20.10 Plugin upgrade breaks remote segment access

**Signal:** read errors after broker upgrade.

**Diagnose:** plugin serialization/metadata compatibility, version matrix, rollback support.

**Mitigate:** halt rollout, preserve artifacts, restore tested compatible release.

## 21. Troubleshooting matrix

| Symptom | Kafka evidence | Kubernetes/cloud evidence | Unsafe shortcut |
|---|---|---|---|
| Offload not happening | Segment eligibility, copy errors | Pod/plugin logs, IAM | Delete local segments |
| Remote reads fail | Remote metadata, fetch errors | Bucket/KMS policy | Make bucket public |
| Read latency high | Remote fetch/cache metrics | Network, object-store p99 | Ignore consumer SLO |
| Broker restart fails | Classpath/plugin errors | Strimzi reconciliation | Patch running broker image |
| History missing | Earliest offsets, retention | Lifecycle audit logs | Reset consumer to latest |
| Disk remains high | Local retention and copy backlog | PVC free bytes | Remove log files |
| DR restore blocked | Metadata/cluster identity | Bucket region and KMS | Mount remote objects as PVC |
| Costs spike | Remote request volume | Provider billing | Disable monitoring |

## 22. Six production runbooks

### Runbook A — Remote-copy backlog

1. Capture broker ISR, local disk headroom and remote-copy metrics.
2. Confirm remote manager/plugin health and supported configuration.
3. Inspect object-store latency, IAM and throttling.
4. Protect local retention window while copy is degraded.
5. Restore service via approved configuration/infrastructure changes.
6. Verify copied offsets and update alerts/capacity plan.

### Runbook B — Remote-read incident

1. Identify impacted topics, offsets, consumer groups and RTO.
2. Compare local/remote availability and metadata state.
3. Inspect IAM, KMS, private endpoint and object-store audit logs.
4. Restore authorized connectivity without broadening public access.
5. Re-read deterministic checksums and measure latency.
6. Reconcile consumers and record data integrity evidence.

### Runbook C — Object-store security incident

1. Contain compromised identity and preserve audit logs.
2. Identify exposed bucket/prefix, encryption keys and affected data.
3. Rotate/revoke credentials through supported workload identity mechanisms.
4. Validate broker access and object integrity.
5. Coordinate data governance and incident reporting.
6. Implement preventive IAM, network and monitoring controls.

### Runbook D — Local disk pressure with tiering

1. Verify local disk utilization, ISR and write availability.
2. Check segment roll, remote-copy backlog and retention relationships.
3. Prevent unreviewed retention reduction and manual file deletion.
4. Expand storage or manage ingest through approved change.
5. Validate offload progress and free-space recovery.
6. Update capacity and copy-lag alert thresholds.

### Runbook E — Tiered-storage upgrade/rollback

1. Capture Kafka, Strimzi, plugin and metadata-manager versions.
2. Review compatibility, artifact digests and rollback restrictions.
3. Test remote copy/read across versions in a disposable cluster.
4. Roll out gradually with Kafka health and remote-read gates.
5. Halt/recover if integrity or SLO checks fail.
6. Retain audit evidence and compatibility test results.

### Runbook F — Regional DR exercise

1. Define scenario, RPO/RTO, dependencies and isolation boundaries.
2. Validate metadata, object store, KMS and identity recovery.
3. Rebuild a supported independent Kafka environment.
4. Restore/replay using a documented supported workflow.
5. Verify offsets, checksums, consumer state and security controls.
6. Record measured RPO/RTO, gaps and assessor signoff.

## 23. Evidence and acceptance checklist

```text
evidence-ch24/
  environment-approval.md
  kafka-client-version.txt
  kafka-cr.yaml
  nodepools.yaml
  pods.txt
  pvc-baseline.txt
  kraft-quorum.txt
  compatibility-matrix.md
  remote-manager-artifact-provenance.md
  object-store-threat-model.md
  workload-identity-review.md
  cost-forecast.md
  integration-manifest-review.md
  bucket-iam-audit.md
  offload-observation.md
  remote-read-checksums.md
  recovery-rpo-rto.md
  observability-mapping.md
  metadata-preflight.txt
  incident-review.md
  security-review.md
  assessor-signoff.md
```

- [ ] Approved disposable Kubernetes cluster and storage account.
- [ ] Exact Kafka, Strimzi, plugin and metadata-manager compatibility reviewed.
- [ ] KRaft quorum, broker PVC and ISR baseline captured.
- [ ] IAM, encryption, audit, network and KMS threat model approved.
- [ ] Remote/local retention and deletion semantics documented.
- [ ] Capacity, request and egress costs estimated.
- [ ] Conditional remote offload validated or marked Not Executed.
- [ ] Conditional remote read and recovery validated or marked Not Executed.
- [ ] DR RPO/RTO tested or explicitly marked tabletop-only.
- [ ] Independent security and operational review recorded.

## 24. Assessment — 100 points

| Domain | Points | Execution requirement |
|---|---:|---|
| Kafka/Strimzi/plugin compatibility matrix | 10 | Reviewed evidence |
| Local/remote lifecycle and retention explanation | 10 | Technical review |
| Kubernetes storage and KRaft baseline | 10 | Live preflight |
| Object-store security and workload identity | 10 | Reviewed threat model |
| Capacity and cloud-cost forecast | 10 | Documented calculations |
| Remote manager integration and offload | 10 | **Live conditional lab** |
| Remote read, checksums and failure recovery | 10 | **Live conditional lab** |
| DR dependency/RPO/RTO validation | 10 | Tested exercise |
| Observability and metadata preflight | 10 | Evidence |
| Incident runbooks and independent review | 10 | Assessor signoff |
| **Total** | **100** | |

**Pass:** ≥85/100, no critical security or data-integrity violations, and live integration/remote-read gates completed for a tiered-storage production-readiness claim. Without a supported plugin or bucket, score only completed sections and mark integration **Pending**; do not grant execution credit for tabletop work.

## 25. Cleanup and next chapter

If conditional labs were executed, clean up **only** approved disposable topics and cloud resources using the reviewed Strimzi and IaC teardown sequence. Retain sanitized audit evidence, ensure object lifecycle and Kafka remote metadata are consistent, and confirm no production cluster references the bucket. Never manually remove broker log segments or PVCs.

**References:** [Apache Kafka documentation](https://kafka.apache.org/documentation/), [Apache Kafka KIP-405](https://cwiki.apache.org/confluence/display/KAFKA/KIP-405%3A+Kafka+Tiered+Storage), [Strimzi documentation](https://strimzi.io/documentation/), [Kubernetes Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/).

**Next:** Chapter 025 — Kafka Storage Reliability, Retention, Compaction and Tiered Storage Kubernetes SRE Capstone.

---

**Verification boundary:** Publication proves chapter availability. It does not prove remote-log compatibility, object-store integration, security controls, data integrity, DR capability or production acceptance.
