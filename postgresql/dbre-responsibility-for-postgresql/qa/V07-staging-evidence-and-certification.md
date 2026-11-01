# PostgreSQL DBRE V07 — Independent Staging Evidence & Operational Certification Gate

**Document ID:** PG-DBRE-QA-V07 | **Status:** DRAFT — EVIDENCE COLLECTION NOT STARTED  
**Publication:** 2026-11-01 UTC | **Environments:** self-managed PostgreSQL, Amazon RDS/Aurora, Azure Flexible Server and Google Cloud SQL  
**Authority:** DBRE, APP, DATA, PLT, SEC and Change/Incident Management must independently accept actual evidence.

## 1. Objective and boundary

V01–V06 are source/documentation QA and a limited offline forecasting test, **not** evidence of operational readiness. V07 establishes a repeatable, independent per-environment proof package. It fails closed when any critical proof, isolation check, reviewer, business watermark or approved service-level objective is absent.

**No live data, credentials, PITR, slot, failover, fencing, disk exhaustion or application traffic were accessed/modified by preparing V07.** This track remains **NOT CERTIFIED FOR PRODUCTION**.

The offline gate script checks supplied metadata and outcomes; it **cannot** authenticate documents, approvals, actual database results or the person who supplied them. It only outputs BLOCKED or READY_FOR_INDEPENDENT_REVIEW, never CERTIFIED.

## 2. A separate record for each service/topology

Create an evidence package per real service/instance cluster, PostgreSQL version, cloud provider and recovery mode. Never use a single certification for all PostgreSQL environments.

| Required evidence | Source/owner |
|---|---|
| Service, provider, version, region, production/staging IDs | PLT/DBRE signed inventory |
| Business tier, approved RPO/RTO, owner & exception policy | APP/DATA and Change |
| Isolated restore target and test data classification | DBRE/SEC |
| Backup ID, complete WAL/timeline or managed last restorable point | DBRE/PLT |
| Last recoverable committed business marker, timestamp and data integrity | DATA |
| Failover/split-brain fencing, single writer and old-primary return (if scope) | PLT plus independent DBRE witness |
| Actual APP read/write, authentication, client endpoints and p95/p99 | APP |
| CDC subscriber/replica/slot state and no missing/duplicated records | DATA/DBRE |
| CPU/IO/WAL/storage runway and restore-capacity evidence | PLT/DBRE/FIN |
| Monitoring exporter, alert routing, access and PHI-free evidence | DBRE/SEC |
| Formal incident/change approvals and signed independent reviewers | SM + reviewers |

**Healthcare privacy:** evidence should contain fake record IDs/test markers only; do not store PHI, credentials, full SQL containing sensitive literals, patient keys or private network details in GitHub. Keep confidential logs in an approved access-controlled evidence system and link to it.

## 3. Evidence workstreams and promotion gates

| Gate ID | Required test | Baseline | Status |
|---|---|---|---|
| V01_STRUCTURE | Independently revalidate exact checked Git commit and local links/safety | [V01](V01-structure-link-safety-audit.md) | NOT_RUN |
| V02_SQL | Run version/provider-specific read-only SQL with restricted role and compare output | [V02](V02-sql-version-provider-compatibility.md) | NOT_RUN |
| V03_ALERTING | Capture exporter /metrics, missing-data and on-call routing tests; SEC review | [V03](V03-monitoring-alerting-security-review.md) | NOT_RUN |
| V04_INCIDENT_SAFETY | Verify locks, WAL slot, XID/MXID, safe abort and owner approvals in staging | [V04](V04-incident-runtime-safety-review.md) | NOT_RUN |
| V05_CAPACITY_FINOPS | Get actual per-node/shared-volume growth and provider billing; validate reserve | [V05](V05-capacity-growth-finops-review.md) | NOT_RUN |
| V06_PITR | Restore to isolated instance and prove base/WAL or provider restorable point | [V06](V06-DR-exercise-acceptance.md) | NOT_RUN |
| V06_FENCING | For HA-failover scope: independently fence old writer and prove only one new writer | [V06](V06-DR-exercise-acceptance.md) | NOT_RUN |
| V06_APP_ACCEPTANCE | APP/DATA confirm read/write + correctness, actual T_recovered and T_service | [V06](V06-backup-HA-DR-review.md) | NOT_RUN |
| V07_SECURITY | Independent SEC/PLT checks on isolation, credentials, logs, approvals and change | This guide | NOT_RUN |

**Important distinction:** A service whose approved recovery design is *PITR-only* records recovery_mode=pitr-only and excludes V06_FENCING from the mechanical test list. This **does not** approve an HA/failover claim; architecture owner and reviewers must verify that scope. Any HA/failover service requires actual independent fencing and single writer evidence.

## 4. Recovery timeline and acceptance

Capture all times in canonical UTC (YYYY-MM-DDTHH:MM:SSZ), from a trustworthy clock:

- T_failure: agreed simulated business outage.
- T_latest_commit: newest demonstrably recovered committed business transaction/marker.
- T_isolation: independently verified old-writer fencing (HA).
- T_restore_ready: PostgreSQL startup, WAL replay and endpoint readiness.
- T_app_accept: APP/DATA accepted full authentication, transactions, data, downstream services and critical performance.

**Observed RPO data-loss window** = T_failure − T_latest_commit, with uncertainty clearly represented. **Observed RTO** = T_app_accept − T_failure. APP/data acceptance must not be replaced by green DB status or an assumed zero-traffic lag. An unknown recovery watermark means RPO is UNKNOWN and fails the gate.

### Example only

Synthetic outage 10:00 UTC, recovered marker 09:55 UTC, business acceptance 11:10 UTC: RPO window 300 seconds and RTO 4,200 seconds. With illustrative approved RPO 1,800s and RTO 7,200s, both are under target. **This is arithmetic, not a performed restore.**

## 5. Certification states and independence

| State | Meaning | Allowed outcome |
|---|---|---|
| NOT_RUN | No actual execution evidence | BLOCKED |
| BLOCKED | Missing approvals, source or safety prerequisites | BLOCKED |
| TABLETOP_PASS | Design was reviewed, no real recovery executed | Cannot satisfy staging runtime requirement |
| STAGING_FAIL | Actual test failed | BLOCKED |
| STAGING_PASS | Witnessed staging execution with proof | Eligible for independent review only |
| READY_FOR_INDEPENDENT_REVIEW | Offline metadata checks pass | Must authenticate every record externally |
| APPROVED BY CHANGE AUTHORITY | Human approval of validated exact environment, scope, test evidence | Organizational process only, never issued by script |
| PRODUCTION_CERTIFIED | Formal external organizational designation | **Not issued by this documentation or utility** |

Executor and independent reviewers must be different people. DBRE, APP, DATA, PLT, SEC and SM reviewers are distinct in the template. Signatures stored as URLs/labels in JSON are merely claims; a reviewer must authenticate identity, evidence provenance, log timestamps and that tests ran on the named environment.

### Nonnegotiable stop conditions

1. Same source and restore target, or any possibility of test traffic writing to production.
2. Incomplete WAL/history, invalid backup chain or cloud restorable point not verified.
3. Unfenced old writer when promotion is in scope; no independent witness.
4. Lost-data estimate greater than RPO or no data watermark.
5. RTO exceeded, APP/data reconciliation incomplete or client endpoints broken.
6. Missing SEC/APP/DATA/SM approvals; reviewer equals executor.
7. Sensitive data leaked to logs/tickets, unclear legal hold or security-policy bypass.
8. Stale vendor/provider service state, old evidence from different topology/version or unapproved recovery method.

## 6. Offline evidence validator and handoff workflow

Files:
- [V07-evidence-template.json](V07-evidence-template.json): **all results default NOT_RUN/PENDING** and blank proof fields.
- [V07-evidence-gate.mjs](V07-evidence-gate.mjs): Node.js 18+ offline validator, read-only file input, no connectors/DB/HTTP; explicit RPO/RTO checks, reviewer independence, source-target isolation and proof link syntax.

From the repo root:

~~~~bash
node postgresql/dbre-responsibility-for-postgresql/qa/V07-evidence-gate.mjs --self-test
node postgresql/dbre-responsibility-for-postgresql/qa/V07-evidence-gate.mjs postgresql/dbre-responsibility-for-postgresql/qa/V07-evidence-template.json
~~~~

Expected: synthetic self-tests PASS. The **unfilled template must return BLOCKED and exit code 2**. Only when a filled, approved evidence package meets its requirements can the gate return READY_FOR_INDEPENDENT_REVIEW. This is **not** proof the URLs or approvals are authentic; physical review is still mandatory. Never commit filled confidential evidence files or identifiers to this public repository. Store approved actual evidence in restricted systems.

### JSON evidence schema

Top-level keys: schema_version, context, tests[], recovery, fencing (if ha-failover), objectives, reviewers. Context includes isolated source/target identity, provider, PG version, executor, full 40-char Git SHA and change-ticket HTTPS URL. Each required test includes STAGING_PASS, HTTPS proof URL, UTC executed timestamp and executor ID. Recovery requires backup/WAL/restore-point and a DATA business watermark; fencing requires independent old-primary and single-writer proof. Reviewers require approved decisions and evidence links. The script validates formats/completeness, **not** reality.

**Security limitation:** HTTP(S) proof URLs are syntactically checked only. No token signatures, role permissions, actual file contents or evidence timestamps are cryptographically validated. A fabricated but internally consistent package may reach READY_FOR_INDEPENDENT_REVIEW; therefore no automatic certification action may be driven from the script.

## 7. Provider-specific execution tracks

| Deployment | Target and staging evidence | Provider-specific blocker |
|---|---|---|
| Self-managed PG14–18 | Isolation, complete base+WAL history, pg_verifybackup, PITR, independent fencing, pg_rewind/rebuild | Host/OS topology, stale timeline, cluster ID, independent writer fencing |
| AWS RDS PostgreSQL | Approved PITR creates separate instance, RDS last restorable point, Multi-AZ/roles/clients | AWS security group/subnet/parameter group, restored backup settings |
| Amazon Aurora PostgreSQL | PITR creates new cluster, writer/reader, cluster endpoints, backup and failover | Cluster shared storage, instance layout and endpoints; differs from RDS |
| Azure Flexible Server | PITR creates new server; network, credentials, HA and app connectivity | HA may need explicit enablement; region/network/backup limits |
| Google Cloud SQL PostgreSQL | PITR new instance, provider IAM/network and data verification | Service edition, default PITR enablement, new endpoint/HA |

Provider-native HA may not expose self-managed fencing mechanics. Record the provider's actual failover writer-uniqueness guarantees and witnessed behavior rather than inventing a local fencing command. If evidence is unavailable, BLOCKED pending provider/PLT/SEC approval; do not claim HA certification from a PITR-only test.

## 8. Review cadence, drift and recertification

**Per major change:** reevaluate on engine major upgrade, HA topology/region/replica/pooler change, changed backup/archival mechanism/retention, secrets, encryption or application service-level target, new CDC dependency, or material data growth.

Suggested cadence: daily backup/replication check, monthly isolated restore smoke test, quarterly DR tabletop, periodic full witnessed failover based on business tier. The business owner determines frequency; do not mark past evidence fresh merely because the document date is current.

Record evidence ID, service identity, Git SHA, timestamps, owner and expiration next-review date, immutable change ticket and failure escalation. If a critical prerequisite regresses, status reverts to BLOCKED / certification review required.

## 9. Current actual evidence register

| Area | Runtime proof | Independent acceptance |
|---|---|---|
| SQL compatibility per provider | NOT_RUN | Pending |
| Exporter/Grafana on-call paging | NOT_RUN | Pending |
| Incident locks/WAL/vacuum safety | NOT_RUN | Pending |
| Capacity time series and cloud billing | NOT_RUN | Pending |
| Isolated base backup and PITR | NOT_RUN | Pending |
| Old primary independent fencing | NOT_RUN | Pending |
| APP/DATA RPO/RTO and correctness | NOT_RUN | Pending |
| SEC/PLT and change/incident approvals | NOT_RUN | Pending |

**V07 completion:** Certification workflow, evidence template and offline checks published. **Operational certification NOT GRANTED.**

## Sources

- [PostgreSQL continuous WAL archiving, PITR, timelines](https://www.postgresql.org/docs/18/continuous-archiving.html)
- [PostgreSQL pg_rewind requirements](https://www.postgresql.org/docs/18/app-pgrewind.html)
- [PostgreSQL warm standby and failover](https://www.postgresql.org/docs/18/warm-standby.html)
- [AWS RDS PITR](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_PIT.html)
- [Aurora PostgreSQL PITR](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-pitr.html)
- [Azure PostgreSQL Flexible Server HA and PITR](https://learn.microsoft.com/en-us/azure/postgresql/high-availability/concepts-high-availability)
- [Cloud SQL PostgreSQL PITR](https://cloud.google.com/sql/docs/postgres/backup-recovery/pitr)
