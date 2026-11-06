# Chapter 09 — Selecting the Right Enterprise PostgreSQL Architecture

**Learning path:** PostgreSQL Database Engineering (DBRE/SRE) — Enterprise Learning Path  
**Level:** Beginner to intermediate · **Time:** 60 minutes · **Publication status:** Authored, not runtime-verified or independently reviewed  
**Reference versions:** PostgreSQL 17 for the local lab; consult current AWS RDS and CloudNativePG compatibility documentation before selecting a production release.

[Course home](../README.md) · [Master TOC](../MASTER-TOC.md) · [Chapter 09 lab](../labs/chapter-09/README.md) · [Progress tracker](../STATUS-TRACKER.md)

## 1. Purpose and learning outcomes

The "best PostgreSQL platform" depends on the workload, operational team, security boundaries, service objectives, and organizational constraints. This chapter teaches a repeatable **architecture decision process**, not a universal ranking.

By the end, a DBRE/SRE should be able to:

1. Translate an application's requirements into non-negotiable gates and weighted preferences.
2. Compare **self-managed bare metal/VM**, **Amazon RDS for PostgreSQL**, and **operator-managed PostgreSQL on Kubernetes**.
3. Distinguish AWS **Multi-AZ DB instance** from **Multi-AZ DB cluster** deployments.
4. Identify primary ownership of backups, PITR, failover, patching, networking, and observability.
5. Document assumptions, unknowns, risks, acceptance evidence, and a defensible architecture decision.
6. Explain why backup configuration, replica presence, or a vendor's feature list does not prove an RPO/RTO objective.

**Boundary:** Amazon Aurora PostgreSQL-Compatible is a different engine architecture; it is outside the four candidates scored here. If Aurora is in scope, assess it as a separate candidate with its own constraints and cost model.

## 2. Teaching schedule (60 minutes)

| Time | Activity | Deliverable |
|---|---|---|
| 0–10 min | Workload discovery and business constraints | Requirement checklist |
| 10–22 min | Deployment patterns and responsibility boundaries | Platform comparison |
| 22–30 min | Hard gates, risk, evidence, and weighted scoring | Decision framework |
| 30–50 min | [Cost-free SQL architecture lab](../labs/chapter-09/README.md) | Reproducible decision matrix |
| 50–60 min | Architecture review, trade-offs and acceptance | Short architecture decision record (ADR) |

## 3. Start with requirements, not a favorite technology

Collect and document:

| Area | Questions to ask | Evidence source |
|---|---|---|
| Workload | OLTP, analytics, batch, mixed? Read/write ratio, QPS/TPS, burst pattern? | Application traces, production query metrics |
| Data model | Size now, growth per month, largest tables, partitioning, extensions? | Schema inventory, growth dashboards |
| Latency | p95/p99 application latency and network locality? | APM, representative load tests |
| Availability | SLO, allowed downtime, maintenance windows, dependencies? | Business owner/SRE |
| Recovery | RPO (acceptable data loss) and RTO (acceptable recovery duration)? | Business continuity owner |
| Compliance | Residency, encryption, audit, access controls, regulated-data scope? | Security/legal approvals |
| Networking | Private connectivity, cross-region dependencies, egress restrictions? | Network architecture |
| Team | 24×7 support, Kubernetes operator expertise, AWS account access, Linux DBA skills? | RACI and on-call roster |
| Change | Upgrade windows, extensions, rollback, schema release cadence? | Change management |
| Cost | Compute, storage, IOPS, backups, egress, licensing, support, labor? | Pricing inputs and FinOps |
| Portability | Exit strategy, migration complexity, managed-service limitations? | Architecture review |

Never derive RPO or RTO from the mere existence of replicas. A **recovery objective** is a requirement; an **observed recovery result** is measured during a controlled exercise.

## 4. Architecture patterns

### A. Self-managed PostgreSQL on bare metal or VMs

```text
Application → private endpoint / pooler → PostgreSQL primary
                                      └→ replica(s), if configured
DB/platform team: OS, storage, HA controller, WAL archive, backup, patching, observability
```

**Strengths:** deep configuration control, extension flexibility, custom hardware/storage topology, potentially good locality or compliance fit.

**Costs and risks:** team owns more layers: OS hardening, storage durability, HA/fencing, upgrades, replication slots, WAL retention, recovery testing, capacity, and on-call coverage. Replication alone does not solve split-brain or establish a safe promotion procedure.

### B. Amazon RDS for PostgreSQL — Multi-AZ DB instance deployment

```text
Application → RDS writer endpoint → primary DB instance
                                  → standby in another AZ (not a read endpoint)
```

**Strengths:** managed host/service operations, built-in deployment options for HA, automated backup capabilities, integration with AWS identity/networking/monitoring.

**Boundaries:** application still owns schema/query design, database users/permissions, parameter choices, recovery policy and testing, security integration, capacity/cost decisions, and incident coordination. A Multi-AZ **DB instance** standby is not available for read scaling.

### C. Amazon RDS for PostgreSQL — Multi-AZ DB cluster deployment

```text
Application → writer endpoint → writer DB instance
            reader endpoint → two readable standby DB instances (separate AZs)
```

This deployment uses **one writer and two readable standby instances across three Availability Zones** and has a different replication and feature model from the Multi-AZ DB instance option. Read scaling, version/region support, pricing, limitations, parameter groups, and failover behavior must be checked for the exact configuration. **Do not treat a Multi-AZ DB cluster as an ordinary Multi-AZ DB instance plus a free reader.**

### D. Kubernetes with a PostgreSQL operator (CloudNativePG example)

```text
Application → operator-managed read/write Service → primary Pod + PVC
            → optional read-only Service → replica Pod(s) + PVC(s)
Kubernetes API ↔ PostgreSQL operator (reconciliation, failover coordination)
```

**Strengths:** declarative configuration, workload integration, Kubernetes-native observability and lifecycle operations, platform portability under appropriate conditions.

**Costs and risks:** requires mature Kubernetes, storage classes/CSI, topology-aware placement, secrets and network policy, operator lifecycle, backup plugins, fencing, and independent recovery exercises. **A PVC is not a backup**, and a healthy Pod is not proof of PostgreSQL recovery. CloudNativePG manages its own Pods/PVCs rather than requiring a conventional StatefulSet.

For CloudNativePG, backup APIs evolve: current documentation recommends **CNPG-I plugin-based** object-storage backup, while older in-core Barman options have been deprecated. Review the deployed operator's specific release documentation before using a manifest.

## 5. Responsibility matrix (illustrative; confirm your organization's RACI)

| Capability | Bare metal/VM | AWS RDS | Kubernetes + operator |
|---|---|---|---|
| OS and infrastructure patching | DB/platform team | AWS-managed service boundary | Kubernetes/platform team |
| PostgreSQL engine patch policy | DB/platform team | Customer schedules/configures supported RDS upgrades; AWS performs managed steps | DB/operator/platform team |
| Storage availability/capacity | DB/platform team | RDS service + customer sizing/limits | CSI/storage team + DB/operator team |
| PostgreSQL roles/schema/SQL | Application + DBRE | Application + DBRE | Application + DBRE |
| HA orchestration | Customer builds/tests | RDS deployment-dependent | Operator + platform; customer validates |
| Backups and PITR | Customer configures and tests | RDS capabilities + customer policy/tests | Operator/backup plugin + customer policy/tests |
| Security and audit | Shared customer teams | AWS/customer shared responsibility | Kubernetes/security/DBRE shared responsibility |
| RPO/RTO acceptance | Business sets, engineering measures | Business sets, engineering measures | Business sets, engineering measures |

RDS reduces host administration, not accountability for application correctness or recoverability.

## 6. Decision process: hard gates first

Use a **two-stage evaluation**:

1. **Hard gates:** mandatory residency, regulatory restrictions, supported extensions/version, network reachability, operational ownership, budget ceiling, approved provider, and ability to *demonstrate* required recovery behavior. An unknown gate is **unverified**, not automatically passed.
2. **Trade-off scores:** only among candidates that have passed the gates, compare reliability engineering, operations burden, performance fit, total cost, and portability. Each score needs evidence, owner, and a date.

A simple weighted score is useful for discussion, but cannot certify a platform. Weights and 1–5 ratings in the lab are **fictional teaching inputs**. In real selection, prefer measured workload benchmarks, a TCO model, documented controls, and an approved decision record.

### Example weighted criteria

| Criterion | Example weight | Interpretation |
|---|---:|---|
| Reliability/recovery fit | 30% | Architecture and demonstrated recovery ability |
| Operations/team fit | 25% | Ownership, on-call and automation maturity |
| Performance/scale fit | 15% | Benchmark, growth, locality and throughput |
| Total cost fit | 20% | Compute + storage + I/O + network + labor |
| Portability fit | 10% | Exit/migration effort and feature dependence |
| **Total** | **100%** | Adjust to business priorities |

A high score must **never override** a failed mandatory security, compliance, extension, or support gate.

## 7. Three illustrative scenarios

### Scenario A — General business OLTP application

- 200 GB initially, moderate write rate, p95 query target, availability objective and approved recovery targets.
- AWS is an approved hosting location; the team has mature RDS operations but limited PostgreSQL operator experience.
- **Candidate to validate:** RDS Multi-AZ DB instance, with Multi-AZ DB cluster separately considered if read scaling is important.
- **Not yet proven:** performance, actual failover/RPO/RTO, monthly TCO, extensions, and access-control requirements.

### Scenario B — Strict on-premises residency

- Security policy prohibits the proposed public-cloud locations.
- **Hard gate:** RDS options are ineligible *under that policy*.
- Evaluate self-managed VMs and operator-managed Kubernetes **only if** storage durability, platform maturity, network boundaries and HA controls can be independently validated.

### Scenario C — Kubernetes-native service

- Application and platform teams have established Kubernetes SRE support and compatible persistent storage.
- CloudNativePG may align well with GitOps, but **operator familiarity is not sufficient**: prove single-writer behavior, fencing, backup/PITR, maintenance, and disaster recovery in staging.
- RDS may still be appropriate even when the application runs on Kubernetes; the database need not run in the same cluster.

## 8. Architecture decision record (ADR) template

Use this short format for each proposed deployment:

```text
ADR ID / date / owners:
Business capability and workload:
Assumptions and evidence links:
Mandatory requirements and gate results:
Candidates evaluated (include rejected candidates):
Performance benchmark and growth model:
HA/failover and single-writer safety design:
Backup, restore, PITR, retention, RPO/RTO evidence:
Security, compliance, networking, and secrets controls:
Operations RACI and 24x7 support:
TCO assumptions and cost sensitivity:
Migration/upgrade/rollback/exit plan:
Risks, unresolved items, owners and deadlines:
Decision, approvers, review date:
```

**Do not call an ADR "approved" until required application, DBRE, platform, security, and change-management reviewers have signed off.**

## 9. Hands-on lab and acceptance

In [Chapter 09 lab](../labs/chapter-09/README.md), use a **local PostgreSQL 17** container and session-scoped temporary tables to:

1. Confirm the database environment and inspect safe configuration signals.
2. Create a fictional workload's criteria weights and candidate assessment.
3. Reject candidates that fail hard gates before calculating weighted scores.
4. Review the baseline ranking and record assumptions.
5. Change the fictional residency and team-capability gates; rerun the ranking.
6. Produce a one-page ADR with required staging tests and open risks.

**Acceptance checklist:**

- [ ] Explain the differences among the four candidate architectures.
- [ ] Correctly state that a Multi-AZ DB instance standby is not a reader.
- [ ] Distinguish HA from backups/PITR and RPO/RTO validation.
- [ ] Reject failed/unknown hard gates before using preference scores.
- [ ] Capture the lab's reproducible baseline and second-scenario results.
- [ ] Include operational ownership, security, cost, and migration in the ADR.
- [ ] Mark lab execution as pending unless real sanitized evidence is retained.

## 10. Troubleshooting and guardrails

| Problem | Investigation | Safe response |
|---|---|---|
| Two platforms have similar scores | Examine sensitivity to weights, unknown inputs, actual TCO | Run controlled proof-of-concept; record uncertainty |
| Candidate fails compliance gate | Check exact data-location/approval requirement | Exclude candidate; do not "offset" with cost/performance |
| RPO/RTO unknown | Identify business owner and recovery scope | Mark **not verified** and schedule isolated recovery test |
| Read scaling assumed from standby | Confirm exact RDS Multi-AZ deployment type | Correct design and connection endpoints |
| Operator claims HA but storage is untested | Review CSI/PVC behavior, fencing, topology and backups | Require isolated failure and restore evidence |
| Extension/version mismatch | Check platform/engine support matrices | Reject or redesign; don't assume parity |
| Unclear cost | Model instance/compute, I/O, storage, backups, egress and labor | Keep TCO as an open risk |

**Production safety:** This chapter authorizes no deployment, failover, data movement, deletion, or resource creation in a cloud account. Any live test needs a separately approved change plan, known blast radius, and rollback.

## 11. Official references (reviewed 2026-11-02)

- [PostgreSQL 18: Continuous Archiving and PITR](https://www.postgresql.org/docs/18/continuous-archiving.html)
- [PostgreSQL 18: Monitoring Statistics](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [AWS: RDS Multi-AZ DB instance](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZSingleStandby.html)
- [AWS: RDS Multi-AZ DB cluster](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/multi-az-db-clusters-concepts.html)
- [AWS: Supported RDS Multi-AZ cluster engines and regions](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.RDS_Fea_Regions_DB-eng.Feature.MultiAZDBClusters.html)
- [CloudNativePG documentation](https://cloudnative-pg.io/docs/1.28/)
- [CloudNativePG backup architecture](https://cloudnative-pg.io/docs/1.28/backup/)
- [Kubernetes persistent volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)

**Next chapter:** [10 — Streaming Replication and High Availability](../MASTER-TOC.md). Its runtime exercises must be isolated, with explicit single-writer and recovery safety controls.
