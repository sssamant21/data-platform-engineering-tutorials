# Chapter 08 — PostgreSQL on Kubernetes: Operators, Storage and Reliability

**Track:** PostgreSQL Database Engineering (DBRE/SRE) — Enterprise Learning Path  
**Audience:** DBRE/SRE and platform engineers · **Duration:** 60 minutes  
**Reference:** PostgreSQL 17 for local exercises; Kubernetes and operator APIs must be checked against the installed versions.  
**Publication status:** Authored; no Kubernetes cluster, PostgreSQL runtime, failover or restore exercise has been executed for this chapter.

[Course home](../README.md) · [Master TOC](../MASTER-TOC.md) · [Chapter 08 lab](../labs/chapter-08/README.md) · [Progress](../STATUS-TRACKER.md)

## Learning objectives

By the end of this lesson, engineers should be able to:

1. Explain how a PostgreSQL operator reconciles desired state with observed state in Kubernetes.
2. Distinguish Pods, StatefulSets, Services, PVCs, PVs, StorageClasses, CRDs and operator-specific Cluster resources.
3. Describe persistent-data and WAL durability concerns when a Pod or node is replaced.
4. Explain why a Kubernetes Deployment or StatefulSet by itself is **not** PostgreSQL HA or split-brain protection.
5. Identify primary/writer routing, replica/read routing, backup/PITR, TLS, secrets, scheduling, disruption and monitoring controls.
6. Conduct a safe, evidence-based review of a proposed operator-managed PostgreSQL workload.
7. Compare self-managed, RDS and Kubernetes ownership boundaries without claiming that one platform is universally superior.

## 60-minute instructor plan

| Time | Topic | Activity |
|---|---|---|
| 0–10 min | Kubernetes stateful workloads and PostgreSQL architecture | Trace request and storage paths |
| 10–20 min | Operator reconciliation, primary election and fencing | Discuss single-writer invariants |
| 20–30 min | Storage, backup, observability, security and upgrades | Evaluate an operator spec |
| 30–52 min | [Hands-on Chapter 08 lab](../labs/chapter-08/README.md) | Docker persistence exercise + manifest review |
| 52–60 min | Incident scenario, design review and acceptance | Document missing evidence |

## 1. Why PostgreSQL on Kubernetes is different

A containerized PostgreSQL process is still PostgreSQL. Kubernetes schedules processes and attaches storage; it does not inherently understand WAL, transaction durability, replica promotion, point-in-time recovery or primary fencing. A PostgreSQL-aware operator provides an API and reconciliation logic for many of those responsibilities, subject to the operator's supported feature set and configuration.

**Illustrative architecture (not a deployable HA guarantee):**

```text
                         Applications
                        /            \
               Writer endpoint    Read endpoint
                     |                 |
              +------+-----------------+------+
              | Kubernetes networking / DNS   |
              +------+-----------------+------+
                     |                 |
              Primary Pod        Replica Pod(s)
              PostgreSQL         PostgreSQL
                 |  WAL streaming    |
                 |------------------>|
                 |                   |
             Data/WAL PVC        Data/WAL PVC
                 |                   |
             PV / CSI            PV / CSI

Operator controller + CRD: observes, reconciles and manages lifecycle
Backup service/object store: separate recovery capability (when configured)
Metrics, logs, events: observability and incident evidence
```

An operator's services and labels are implementation-specific. The above is conceptual, not a promise of a particular Service name.

## 2. Kubernetes objects and operational meaning

| Object | Role | DBRE/SRE question |
|---|---|---|
| Namespace | Scope for API objects and access controls | Who can read secrets and modify the database resource? |
| CustomResourceDefinition (CRD) | Defines operator-specific API type | Which version/schema does the installed operator support? |
| Custom Resource / Cluster | Desired PostgreSQL topology | What happens if the resource is deleted or modified? |
| Operator controller | Reconciles desired and actual state | Is it healthy, version-compatible and permitted to operate? |
| Pod | Running PostgreSQL process | Where are readiness and graceful termination defined? |
| PersistentVolumeClaim (PVC) | Requests storage | Which StorageClass, reclaim policy, capacity and access mode apply? |
| PersistentVolume (PV) / CSI | Backing storage and attachment | Is storage durable, encrypted and correctly scoped to a zone? |
| Service | Stable application connection target | Does writer traffic always reach the current primary? |
| Secret / ServiceAccount | Credentials and Kubernetes identity | How are secrets rotated, RBAC and workload identity controlled? |
| NetworkPolicy | Allowed network traffic | Can only intended clients, operator and replication peers connect? |
| PodDisruptionBudget (PDB) | Restricts eligible voluntary evictions | Does it reflect the actual operator topology and maintenance strategy? |

**Key distinction:** A StatefulSet can provide stable identity and PVC templates, but it does **not** by itself configure PostgreSQL replication, promote replicas, prevent two writers or ensure recoverability. Some PostgreSQL operators manage Pods directly rather than exposing a user-managed StatefulSet. Do not assume a StatefulSet will exist.

## 3. Operator-managed PostgreSQL

This chapter uses **CloudNativePG** as a concrete reference operator. Alternatives have different CRDs, capabilities and operational support contracts. Always consult the exact installed operator release and Kubernetes compatibility matrix.

A typical operator lifecycle is:

1. The platform team installs the operator and CRDs after security and compatibility review.
2. An authorized DBRE declares a PostgreSQL Cluster resource in a namespace.
3. The operator bootstraps the primary, provisions/attaches storage and manages instances.
4. It maintains replica topology, connection endpoints and lifecycle operations within its supported behavior.
5. The team monitors reconciliation, replication, storage, backup and application SLOs.
6. Changes go through a reviewed GitOps/change process with tested rollback or recovery plans.

**Never manually promote or restart database Pods as a casual repair step.** Uncoordinated interventions can cause data loss, divergent timelines or application disruption.

### Illustrative CloudNativePG manifest

The [lab includes a standalone example manifest](../labs/chapter-08/cluster-example.yaml) for **review only**. It is intentionally minimal and has one instance, so it is **not HA**, does **not** configure backups, and should not be applied to production. The installed operator chooses the PostgreSQL image when no `imageName` is specified; verify the resulting PostgreSQL major version before relying on any version-specific SQL examples.

```yaml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: pg-training
  namespace: dbre-training
spec:
  instances: 1
  storage:
    size: 1Gi
  bootstrap:
    initdb:
      database: app
      owner: app
```

This YAML is not a complete enterprise configuration. A real design also needs storage class, backup and recovery, TLS, application secrets, topology/anti-affinity, resource requests and limits, upgrade strategy, monitoring, RBAC, network policy, and data-retention decisions.

## 4. Storage, durability and failure domains

### Persistent volumes

A Pod's writable container filesystem is not the PostgreSQL data durability boundary. Production databases need suitable persistent storage, correct mount paths, tested reattachment behavior, capacity alerts and an understood reclaim policy.

- Check `kubectl get storageclass` and the PVC's `storageClassName`, `accessModes` and `volumeMode`.
- Verify the underlying CSI driver's volume provisioning, attach/detach, zone affinity and recovery semantics.
- Do not assume a PVC is a backup: deletion, corruption, operator error or regional outage can affect primary data and replicas.
- `ReadWriteOnce` does not inherently guarantee one PostgreSQL writer across all failure modes. Single-writer enforcement needs PostgreSQL/operator-aware fencing.
- Plan WAL space, disk IOPS/throughput, free capacity, filesystem behavior and noisy-neighbor risks.

### WAL and recovery

PostgreSQL records changes in WAL before affected data pages are made durable. A backup strategy must cover base backups and WAL archiving (or a verified equivalent) for point-in-time recovery. Physical replication alone is **not** a substitute for independent, restorable backups.

For any claimed RPO/RTO, test an isolated restore and record:
- chosen restore point and recovery source;
- time to start and complete recovery;
- application-level validation and acceptable data loss;
- ownership, approval and rollback conditions.

## 5. High availability and single-writer correctness

A multi-instance configuration may provide replicas, but availability is conditional on healthy storage, networking, controller behavior, replica currency, application connection retry, and safe fencing of an unreachable former primary.

**Critical questions:**
- Can an isolated former primary continue accepting writes?
- How is promotion authorized and how is the previous writer fenced?
- Are writes acknowledged synchronously or asynchronously? What data-loss exposure remains?
- Can a promoted replica accept the application workload at its new endpoint?
- Are connection pools prepared for DNS and TCP reconnection?
- What happens if the operator controller is unavailable during an incident?
- Does the topology span failure domains, and is storage topology compatible?

A PDB reduces **some voluntary disruptions**; it does not protect against involuntary node failures or guarantee database availability. For production, test node maintenance and failover only in an approved staging environment.

## 6. Backup, security and observability

### Backup and restore

Define an operator-supported backup method for the installed version. Confirm storage access, object-store permissions, WAL archive retention, restore tooling, immutable/offsite controls as appropriate, and successful isolated restores. The operator's supported backup integrations may evolve; never copy a historical CRD snippet without checking version-specific documentation.

### Security

- Enforce least-privilege namespace RBAC and operator permissions.
- Store credentials in an approved secret manager; do not commit plaintext passwords.
- Use TLS for application connections and replication where supported/required.
- Restrict ingress and egress using NetworkPolicies with a compatible CNI.
- Control container image provenance, admission policies and patch cadence.
- Audit who can modify the Cluster CRD, backups, PVCs and Secrets.

### Monitoring

Monitor at three layers:

| Layer | Example signals |
|---|---|
| PostgreSQL | connections, locks, transactions, query latency, WAL, replication lag, autovacuum |
| Operator | reconciliation failures, Cluster conditions, role changes, backup failures |
| Kubernetes/storage | Pod restarts, OOM kills, CPU throttling, PVC capacity, volume errors, node pressure |

An operator-reported healthy state is not enough: combine it with actual application SLOs and independent restore evidence.

## 7. Deployment comparison

| Responsibility | Bare metal | AWS RDS | Kubernetes + operator |
|---|---|---|---|
| Host OS and kernel | Platform/DB team | AWS | Kubernetes platform team |
| PostgreSQL process lifecycle | DBRE/HA tooling | AWS-managed with customer configuration | Operator + DBRE |
| Primary promotion | DBRE/HA tooling | RDS feature-dependent | Operator-specific |
| Storage provisioning | Platform/DB | RDS | CSI/PVC/platform |
| Backup policy and restore tests | DBRE | Customer defines/validates RDS capabilities | DBRE/operator/backup integration |
| Application schema and query tuning | App + DBRE | App + DBRE | App + DBRE |
| Cost and capacity accountability | Organization | Organization | Organization |

**Architecture selection:** Kubernetes is reasonable when the organization already has a mature operator, storage, GitOps, security and on-call platform. RDS may be simpler when a managed service fits the workload. The correct choice follows measurable requirements, not a blanket "Kubernetes is more scalable" claim.

## 8. Lab and assessment

Complete [Chapter 08 lab](../labs/chapter-08/README.md). The default exercise is cost-free and uses local Docker/PostgreSQL for persistence and SQL diagnostics plus offline review of the operator manifest. Optional Kubernetes steps are **read-only** and only for an existing authorized non-production cluster; no operator install, cluster creation, namespace creation or cloud spend is required.

### Incident review exercise

An application reports write failures after a Kubernetes node becomes unreachable. The primary Pod is missing, a replica is healthy, and the operator has issued a role transition event.

Write a short incident plan:
1. Verify namespace, operator, Cluster conditions and application impact.
2. Check which endpoint routes writers and whether a former primary could still accept writes.
3. Measure replica currency and WAL/backup status.
4. Escalate before any manual promotion, Pod deletion or PVC changes.
5. Verify a single writer, application transaction correctness and connection recovery.
6. Retain timeline, evidence, measured impact and follow-up actions.

### Acceptance checklist

- [ ] Correctly explain all Kubernetes object types above.
- [ ] Explain why a StatefulSet alone is not PostgreSQL HA.
- [ ] Distinguish a persistent volume from an independently verified backup.
- [ ] Identify operator/cluster version assumptions and manifest omissions.
- [ ] Execute the local persistence and PostgreSQL observability steps, if available.
- [ ] Complete the offline operator-spec review.
- [ ] Describe fencing, RPO/RTO and safe maintenance conditions.
- [ ] Save sanitized evidence and reviewer notes **only when actual exercises are performed**.

**No runtime certification is implied by authored documentation.**

## 9. Troubleshooting guide

| Symptom | Evidence to gather | Guardrail |
|---|---|---|
| Cluster resource unknown | CRDs, API version, operator install status | Do not install CRDs without platform approval |
| Pod Pending | events, PVC state, StorageClass, quotas | Do not delete PVC to "fix" scheduling |
| Volume mount errors | CSI events, zone/node attachment | Escalate to storage owner |
| Read-only SQL on writer endpoint | primary role, endpoint routing, failover events | Do not force a promotion |
| Unexpected WAL growth | replication, archive status, slots, retention | Do not delete WAL files manually |
| Backup failures | backup resource status, storage permissions, archive errors | Do not claim recoverability without restore |
| App connection resets | Service endpoint changes, pool retries, DNS | Coordinate app retry and idempotency strategy |

## 10. Official references

- [CloudNativePG documentation](https://cloudnative-pg.io/docs/)
- [CloudNativePG bootstrap concepts](https://cloudnative-pg.io/docs/devel/bootstrap/)
- [Kubernetes StatefulSets](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/)
- [Kubernetes Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
- [Kubernetes Disruptions and PDBs](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)
- [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [PostgreSQL 18: Monitoring Database Activity](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [PostgreSQL 18: Continuous Archiving and PITR](https://www.postgresql.org/docs/18/continuous-archiving.html)

**Documentation note (2026-11-02):** Review the installed CloudNativePG release's versioned documentation rather than assuming that a development-branch example matches a deployed operator.
