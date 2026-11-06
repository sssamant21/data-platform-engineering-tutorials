# Chapter 08 Lab — PostgreSQL Persistence and Kubernetes Operator Review

**Runtime:** PostgreSQL 17 Docker image; optional read-only Kubernetes discovery.  
**Audience:** DBRE/SRE · **Duration:** ~22 minutes of a 60-minute lesson.  
**Status:** Authored; **not executed**. Expected outcomes are not evidence.

[Chapter 08](../../chapters/08-postgresql-on-kubernetes.md) · [Example CloudNativePG manifest](cluster-example.yaml) · [Course home](../../README.md)

## Safety and learning outcomes

The default path is **local, cost-free and Kubernetes-independent**. It demonstrates PostgreSQL persistence through a controlled container restart and evaluates an operator specification. It does **not** install a Kubernetes operator, create cloud resources, test HA, or certify backups. Optional Kubernetes commands are read-only, for an already-authorized non-production cluster.

At the end, learners should be able to identify a data volume, verify a durable marker after restart, inspect PostgreSQL observability signals, review a CloudNativePG Cluster manifest, and explain what additional evidence HA and PITR require.

## Instructor's 60-minute sequence

| Minutes | Topic |
|---|---|
| 0–10 | Architecture: operator, CRD, Pods, Services, PV/PVC/CSI |
| 10–20 | Primary/replica routing, fencing, storage and backup |
| 20–28 | Docker preflight and local PostgreSQL startup |
| 28–38 | Create data, inspect PostgreSQL and volume |
| 38–44 | Controlled restart and persistence check |
| 44–52 | Manifest review and optional Kubernetes read-only discovery |
| 52–60 | Incident worksheet, evidence and acceptance |

## 0. Prerequisites and identity guardrails

- Windows PowerShell with Docker Desktop in Linux-container mode, or equivalent Docker Engine with adapted commands.
- A free loopback host port `55438` and enough local disk space for a small PostgreSQL 17 lab.
- No Kubernetes cluster, `kubectl`, Helm, AWS account or cloud spending is required.
- This lab reserves container `pg-k8s-lab`, volume `pg_k8s_ch08_data`, database `appdb`.
- Use only synthetic data. Do not commit secrets, full query texts or personal data.

**Preflight:**

```powershell
docker version
docker info --format '{{.OSType}}'
docker ps -a --filter "name=pg-k8s-lab"
docker volume ls --filter "name=pg_k8s_ch08_data"
```

Expected: Docker server available and `linux` container mode. Container/volume queries should be empty for a first run.

**STOP if either lab name already exists:** inspect ownership and contents first. Never delete, overwrite or attach an unidentified volume. Choose alternate names and update every subsequent command consistently if necessary.

## 1. Start an isolated PostgreSQL 17 container

Run only for a new disposable lab:

```powershell
$labContext = docker context show
$labContainerId = docker run -d --name pg-k8s-lab --label dbre.training.track=postgresql-enterprise --label dbre.training.chapter=08 -e POSTGRES_PASSWORD=TrainingOnly_ChangeMe_123 -e POSTGRES_DB=appdb -p 127.0.0.1:55438:5432 -v pg_k8s_ch08_data:/var/lib/postgresql/data postgres:17
if ($LASTEXITCODE -ne 0 -or $labContainerId -notmatch '^[a-f0-9]{64} demonstration password is **not suitable for any real environment**. Port binding is limited to local loopback.

```powershell
docker ps --filter "name=pg-k8s-lab"
docker exec pg-k8s-lab pg_isready -U postgres -d appdb
docker inspect pg-k8s-lab --format '{{range .Mounts}}{{println .Name .Destination}}{{end}}'
```

Expected: running container, database accepting connections, and `pg_k8s_ch08_data` mounted at `/var/lib/postgresql/data`. First initialization may take a few seconds; check logs and retry readiness if necessary.

**Interpretation:** A Docker named volume is a *persistence analogy*, not a Kubernetes PVC or an independent backup.

## 2. Create a synthetic marker

Connect from PowerShell:

```powershell
docker exec -it pg-k8s-lab psql -U postgres -d appdb
```

In the `psql` prompt:

```sql
SELECT version();
SELECT current_database(), current_user;
SHOW data_directory;
SELECT pg_is_in_recovery();

CREATE TABLE IF NOT EXISTS public.chapter08_markers (
    marker_id TEXT PRIMARY KEY,
    marker_value TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO public.chapter08_markers (marker_id, marker_value)
VALUES ('persist-01', 'created-before-restart')
ON CONFLICT (marker_id) DO NOTHING;

SELECT marker_id, marker_value
FROM public.chapter08_markers
ORDER BY marker_id;
```

Expected: PostgreSQL 17, database `appdb`, nonempty data directory, `pg_is_in_recovery() = false`, and one marker row:

```text
 marker_id  |       marker_value
------------+----------------------------
 persist-01 | created-before-restart
```

The insert is idempotent; reruns do not overwrite the marker. Exit `psql` with `\q`.

## 3. Capture safe pre-restart observations

In PowerShell:

```powershell
docker exec pg-k8s-lab psql -U postgres -d appdb -c "SELECT pg_size_pretty(pg_database_size(current_database())) AS db_size;"
docker exec pg-k8s-lab psql -U postgres -d appdb -c "SELECT pg_current_wal_lsn() AS current_wal_lsn;"
docker exec pg-k8s-lab psql -U postgres -d appdb -c "SELECT state, count(*) FROM pg_stat_activity WHERE datname = current_database() GROUP BY state;"
```

Expected: nonempty size and WAL LSN, and environment-dependent session counts. These queries are observational, not proof of recoverability.

## 4. Controlled restart and persistence check

**Only restart after verifying the exact disposable container identity.** This interrupts connections briefly and must not be done to a shared database.

```powershell
if ((docker context show) -ne $labContext) { throw 'Docker context changed; STOP' }
$actualId = docker inspect pg-k8s-lab --format '{{.Id}}'
$chapterLabel = docker inspect pg-k8s-lab --format '{{index .Config.Labels "dbre.training.chapter"}}'
$trackLabel = docker inspect pg-k8s-lab --format '{{index .Config.Labels "dbre.training.track"}}'
$mount = docker inspect pg-k8s-lab --format '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}}{{end}}{{end}}'
if ($LASTEXITCODE -ne 0 -or $actualId -ne $labContainerId -or $chapterLabel -ne '08' -or $trackLabel -ne 'postgresql-enterprise' -or $mount -ne 'pg_k8s_ch08_data') { throw 'Identity or mount mismatch; STOP' }
docker restart pg-k8s-lab
docker exec pg-k8s-lab pg_isready -U postgres -d appdb
docker exec pg-k8s-lab psql -U postgres -d appdb -c "SELECT marker_id, marker_value FROM public.chapter08_markers;"
docker inspect pg-k8s-lab --format '{{range .Mounts}}{{println .Name .Destination}}{{end}}'
```

Expected: database becomes ready again, marker `persist-01` still exists, and the named volume remains attached. If readiness is checked before startup completes, retry after reviewing container logs.

**This proves only:** marker persistence across a controlled local restart. It does not establish HA, automatic failover, Kubernetes rescheduling, CSI storage correctness, PITR, RPO, RTO, or fencing.

## 5. Offline review of a CloudNativePG Cluster manifest

Open the [review-only YAML](cluster-example.yaml) from the repository. It is deliberately **not** a production configuration.

If you have checked out the repository locally and are in its root directory:

```powershell
Get-Content .\postgresql\postgresql-dbre-sre-enterprise-learning-path\labs\chapter-08\cluster-example.yaml
Select-String -Path .\postgresql\postgresql-dbre-sre-enterprise-learning-path\labs\chapter-08\cluster-example.yaml -Pattern 'apiVersion:|kind:|namespace:|instances:|storage:|size:|bootstrap:'
```

Expected: `apiVersion: postgresql.cnpg.io/v1`, `kind: Cluster`, `namespace: dbre-training`, `instances: 1`, `size: 1Gi`, and `bootstrap.initdb`. If the local checkout is unavailable, use the GitHub link instead.

### Review worksheet

| Concern | Example state | Missing enterprise control |
|---|---|---|
| HA | Single instance | Replicas, failure domains, failover/fencing validation |
| Storage | 1Gi, operator-default class | CSI performance, encryption, capacity, reclaim policy |
| Backup | Not configured | Independent backup, WAL archive and restore/PITR testing |
| Security | No explicit access policy | RBAC, TLS, Secrets, NetworkPolicy, rotation |
| Resources | No sizing | CPU/memory requests and limits, capacity review |
| Placement | No explicit topology | Anti-affinity, zone awareness, maintenance strategy |
| Monitoring | Not configured | PostgreSQL/operator/storage metrics and alerting |
| Upgrade | Not specified | Version compatibility, maintenance and recovery plan |

**Do not apply the manifest to production or an unknown cluster.** The PostgreSQL image version is operator-selected when not specified. Confirm operator/Kubernetes compatibility and actual image before running version-dependent SQL.

## 6. Optional read-only Kubernetes inventory

**Skip this step unless** you have an existing authorized non-production context. These commands do not mutate resources, but can reveal operational metadata. Do not commit raw output.

```powershell
kubectl config current-context
kubectl cluster-info
kubectl get crd clusters.postgresql.cnpg.io
kubectl get namespaces
```

Only if access to the named training namespace is approved:

```powershell
kubectl get clusters.postgresql.cnpg.io -n dbre-training
kubectl get pods -n dbre-training
kubectl get pvc -n dbre-training
kubectl get events -n dbre-training --sort-by=.metadata.creationTimestamp
```

Expected results depend on the environment. `NotFound` or `Forbidden` can be legitimate when the CRD/namespace is absent or RBAC denies access.

**STOP on:** unknown/production context, ownership uncertainty, absent CRD, or access denial. Do not install operators/CRDs, create namespaces, apply manifests, delete PVCs, drain nodes or force promotion for this lab.

## 7. Paper incident scenario (no disruption)

Scenario: the application writer endpoint times out after a node failure; the PostgreSQL Pod restarted and the PVC has attachment errors.

Write a short incident plan:

1. Record namespace, cluster identity, SLO impact and current primary.
2. Inspect operator conditions, Pod events, PVC/CSI errors, and writer endpoint routing.
3. Explain how to establish that only one writer is active and the former primary is fenced.
4. Check replica lag, WAL archive, backup freshness and independent restore evidence.
5. Identify DBRE, platform, storage and application owners and escalation order.
6. Define recovery acceptance: correct writer, successful application transaction, latency and consistency.
7. Explain why deleting a PVC or manually promoting a Pod is unsafe without an approved runbook.

## Acceptance evidence

- [ ] Docker and lab resource identity checked.
- [ ] PostgreSQL 17 and database name confirmed.
- [ ] Persistent volume mount observed.
- [ ] Marker created and read before restart.
- [ ] Marker read again after restart.
- [ ] Database size, WAL LSN and session statistics observed.
- [ ] Manifest reviewed and six or more missing enterprise controls identified.
- [ ] Optional Kubernetes discovery was authorized and read-only.
- [ ] Incident plan completed with fencing and restore considerations.
- [ ] Sanitized evidence and reviewer acknowledgement retained only after actual execution.

**Written expected results do not constitute runtime validation.**

## Troubleshooting

| Symptom | Safe investigation | Stop condition |
|---|---|---|
| Docker daemon unavailable | Start Docker Desktop, verify Linux mode | Do not target an unknown host |
| Container/volume exists | Inspect ownership and current data | Do not overwrite or remove |
| Port 55438 in use | Find an unused loopback port | Do not kill another service |
| Database not ready | `docker logs pg-k8s-lab`; retry readiness | Do not recreate the volume |
| Marker absent after restart | Check database, mount and logs | Do not fabricate evidence |
| YAML file not found | Verify checkout root; use GitHub link | No cluster action needed |
| `kubectl` missing | Skip optional exercise | Do not install tooling solely to satisfy this lab |
| CRD absent or RBAC denied | Escalate to platform owner | Do not install or bypass access |

## Optional cleanup (manual, destructive, local lab only)

Cleanup is **not** part of default execution. Deleting the volume permanently deletes the lab database. Preserve the original creation-session `$labContext` and `$labContainerId`; **STOP** if they are unavailable, if context/ID/labels/mounts differ, or if any other container consumes the volume. Do not remove unknown resources.

```powershell
if ((docker context show) -ne $labContext) { throw 'Context mismatch; no cleanup' }
$actualId = docker inspect pg-k8s-lab --format '{{.Id}}'
$chapterLabel = docker inspect pg-k8s-lab --format '{{index .Config.Labels "dbre.training.chapter"}}'
$trackLabel = docker inspect pg-k8s-lab --format '{{index .Config.Labels "dbre.training.track"}}'
$mount = docker inspect pg-k8s-lab --format '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}}{{end}}{{end}}'
if ($LASTEXITCODE -ne 0 -or $actualId -ne $labContainerId -or $chapterLabel -ne '08' -or $trackLabel -ne 'postgresql-enterprise' -or $mount -ne 'pg_k8s_ch08_data') { throw 'Ownership mismatch; no cleanup' }
$consumers = @(docker ps -aq --filter 'volume=pg_k8s_ch08_data')
if ($LASTEXITCODE -ne 0 -or $consumers.Count -ne 1 -or $consumers[0] -ne $labContainerId) { throw 'Unexpected volume consumers; no cleanup' }
# DESTRUCTIVE: execute only after explicit approval for this disposable lab.
docker stop $labContainerId
if ($LASTEXITCODE -ne 0) { throw 'Stop failed' }
docker rm $labContainerId
if ($LASTEXITCODE -ne 0) { throw 'Removal failed; preserve volume' }
docker volume rm pg_k8s_ch08_data
if ($LASTEXITCODE -ne 0) { throw 'Volume removal failed; inspect manually' }
docker inspect $labContainerId 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) { throw 'Container still exists' }
docker volume inspect pg_k8s_ch08_data 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) { throw 'Volume still exists' }
```

Retain sanitized evidence of original identity, context, mount, consumer check and post-removal absence. These instructions are source-reviewed, not runtime-validated. No Kubernetes cleanup is required because no Kubernetes resources were created.

## Official references

- [CloudNativePG documentation](https://cloudnative-pg.io/docs/)
- [Kubernetes Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
- [Kubernetes StatefulSets](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/)
- [Kubernetes Pod Disruptions](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)
- [PostgreSQL 17 Monitoring](https://www.postgresql.org/docs/17/monitoring-stats.html)
- [PostgreSQL 17 Continuous Archiving](https://www.postgresql.org/docs/17/continuous-archiving.html)
) { throw 'Container creation failed' }
# Retain $labContext and $labContainerId as original creation evidence.
```

This intentionally weak demonstration password is **not suitable for any real environment**. Port binding is limited to local loopback.

```powershell
docker ps --filter "name=pg-k8s-lab"
docker exec pg-k8s-lab pg_isready -U postgres -d appdb
docker inspect pg-k8s-lab --format '{{range .Mounts}}{{println .Name .Destination}}{{end}}'
```

Expected: running container, database accepting connections, and `pg_k8s_ch08_data` mounted at `/var/lib/postgresql/data`. First initialization may take a few seconds; check logs and retry readiness if necessary.

**Interpretation:** A Docker named volume is a *persistence analogy*, not a Kubernetes PVC or an independent backup.

## 2. Create a synthetic marker

Connect from PowerShell:

```powershell
docker exec -it pg-k8s-lab psql -U postgres -d appdb
```

In the `psql` prompt:

```sql
SELECT version();
SELECT current_database(), current_user;
SHOW data_directory;
SELECT pg_is_in_recovery();

CREATE TABLE IF NOT EXISTS public.chapter08_markers (
    marker_id TEXT PRIMARY KEY,
    marker_value TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO public.chapter08_markers (marker_id, marker_value)
VALUES ('persist-01', 'created-before-restart')
ON CONFLICT (marker_id) DO NOTHING;

SELECT marker_id, marker_value
FROM public.chapter08_markers
ORDER BY marker_id;
```

Expected: PostgreSQL 17, database `appdb`, nonempty data directory, `pg_is_in_recovery() = false`, and one marker row:

```text
 marker_id  |       marker_value
------------+----------------------------
 persist-01 | created-before-restart
```

The insert is idempotent; reruns do not overwrite the marker. Exit `psql` with `\q`.

## 3. Capture safe pre-restart observations

In PowerShell:

```powershell
docker exec pg-k8s-lab psql -U postgres -d appdb -c "SELECT pg_size_pretty(pg_database_size(current_database())) AS db_size;"
docker exec pg-k8s-lab psql -U postgres -d appdb -c "SELECT pg_current_wal_lsn() AS current_wal_lsn;"
docker exec pg-k8s-lab psql -U postgres -d appdb -c "SELECT state, count(*) FROM pg_stat_activity WHERE datname = current_database() GROUP BY state;"
```

Expected: nonempty size and WAL LSN, and environment-dependent session counts. These queries are observational, not proof of recoverability.

## 4. Controlled restart and persistence check

**Only restart after verifying the exact disposable container identity.** This interrupts connections briefly and must not be done to a shared database.

```powershell
docker restart pg-k8s-lab
docker exec pg-k8s-lab pg_isready -U postgres -d appdb
docker exec pg-k8s-lab psql -U postgres -d appdb -c "SELECT marker_id, marker_value FROM public.chapter08_markers;"
docker inspect pg-k8s-lab --format '{{range .Mounts}}{{println .Name .Destination}}{{end}}'
```

Expected: database becomes ready again, marker `persist-01` still exists, and the named volume remains attached. If readiness is checked before startup completes, retry after reviewing container logs.

**This proves only:** marker persistence across a controlled local restart. It does not establish HA, automatic failover, Kubernetes rescheduling, CSI storage correctness, PITR, RPO, RTO, or fencing.

## 5. Offline review of a CloudNativePG Cluster manifest

Open the [review-only YAML](cluster-example.yaml) from the repository. It is deliberately **not** a production configuration.

If you have checked out the repository locally and are in its root directory:

```powershell
Get-Content .\postgresql\postgresql-dbre-sre-enterprise-learning-path\labs\chapter-08\cluster-example.yaml
Select-String -Path .\postgresql\postgresql-dbre-sre-enterprise-learning-path\labs\chapter-08\cluster-example.yaml -Pattern 'apiVersion:|kind:|namespace:|instances:|storage:|size:|bootstrap:'
```

Expected: `apiVersion: postgresql.cnpg.io/v1`, `kind: Cluster`, `namespace: dbre-training`, `instances: 1`, `size: 1Gi`, and `bootstrap.initdb`. If the local checkout is unavailable, use the GitHub link instead.

### Review worksheet

| Concern | Example state | Missing enterprise control |
|---|---|---|
| HA | Single instance | Replicas, failure domains, failover/fencing validation |
| Storage | 1Gi, operator-default class | CSI performance, encryption, capacity, reclaim policy |
| Backup | Not configured | Independent backup, WAL archive and restore/PITR testing |
| Security | No explicit access policy | RBAC, TLS, Secrets, NetworkPolicy, rotation |
| Resources | No sizing | CPU/memory requests and limits, capacity review |
| Placement | No explicit topology | Anti-affinity, zone awareness, maintenance strategy |
| Monitoring | Not configured | PostgreSQL/operator/storage metrics and alerting |
| Upgrade | Not specified | Version compatibility, maintenance and recovery plan |

**Do not apply the manifest to production or an unknown cluster.** The PostgreSQL image version is operator-selected when not specified. Confirm operator/Kubernetes compatibility and actual image before running version-dependent SQL.

## 6. Optional read-only Kubernetes inventory

**Skip this step unless** you have an existing authorized non-production context. These commands do not mutate resources, but can reveal operational metadata. Do not commit raw output.

```powershell
kubectl config current-context
kubectl cluster-info
kubectl get crd clusters.postgresql.cnpg.io
kubectl get namespaces
```

Only if access to the named training namespace is approved:

```powershell
kubectl get clusters.postgresql.cnpg.io -n dbre-training
kubectl get pods -n dbre-training
kubectl get pvc -n dbre-training
kubectl get events -n dbre-training --sort-by=.metadata.creationTimestamp
```

Expected results depend on the environment. `NotFound` or `Forbidden` can be legitimate when the CRD/namespace is absent or RBAC denies access.

**STOP on:** unknown/production context, ownership uncertainty, absent CRD, or access denial. Do not install operators/CRDs, create namespaces, apply manifests, delete PVCs, drain nodes or force promotion for this lab.

## 7. Paper incident scenario (no disruption)

Scenario: the application writer endpoint times out after a node failure; the PostgreSQL Pod restarted and the PVC has attachment errors.

Write a short incident plan:

1. Record namespace, cluster identity, SLO impact and current primary.
2. Inspect operator conditions, Pod events, PVC/CSI errors, and writer endpoint routing.
3. Explain how to establish that only one writer is active and the former primary is fenced.
4. Check replica lag, WAL archive, backup freshness and independent restore evidence.
5. Identify DBRE, platform, storage and application owners and escalation order.
6. Define recovery acceptance: correct writer, successful application transaction, latency and consistency.
7. Explain why deleting a PVC or manually promoting a Pod is unsafe without an approved runbook.

## Acceptance evidence

- [ ] Docker and lab resource identity checked.
- [ ] PostgreSQL 17 and database name confirmed.
- [ ] Persistent volume mount observed.
- [ ] Marker created and read before restart.
- [ ] Marker read again after restart.
- [ ] Database size, WAL LSN and session statistics observed.
- [ ] Manifest reviewed and six or more missing enterprise controls identified.
- [ ] Optional Kubernetes discovery was authorized and read-only.
- [ ] Incident plan completed with fencing and restore considerations.
- [ ] Sanitized evidence and reviewer acknowledgement retained only after actual execution.

**Written expected results do not constitute runtime validation.**

## Troubleshooting

| Symptom | Safe investigation | Stop condition |
|---|---|---|
| Docker daemon unavailable | Start Docker Desktop, verify Linux mode | Do not target an unknown host |
| Container/volume exists | Inspect ownership and current data | Do not overwrite or remove |
| Port 55438 in use | Find an unused loopback port | Do not kill another service |
| Database not ready | `docker logs pg-k8s-lab`; retry readiness | Do not recreate the volume |
| Marker absent after restart | Check database, mount and logs | Do not fabricate evidence |
| YAML file not found | Verify checkout root; use GitHub link | No cluster action needed |
| `kubectl` missing | Skip optional exercise | Do not install tooling solely to satisfy this lab |
| CRD absent or RBAC denied | Escalate to platform owner | Do not install or bypass access |

## Optional cleanup (manual, destructive, local lab only)

Cleanup is **not** part of default execution. After confirming the exact disposable container/volume names and retaining any evidence, the following can remove lab resources. The volume removal permanently deletes the training database.

```powershell
# Only after manually confirming this container and volume belong to this disposable lab:
docker stop pg-k8s-lab
docker rm pg-k8s-lab
# DESTRUCTIVE: deletes this lab's PostgreSQL data:
docker volume rm pg_k8s_ch08_data
```

Do not automate these commands against unknown resources. There is no Kubernetes cleanup because no Kubernetes resources were created.

## Official references

- [CloudNativePG documentation](https://cloudnative-pg.io/docs/)
- [Kubernetes Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
- [Kubernetes StatefulSets](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/)
- [Kubernetes Pod Disruptions](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)
- [PostgreSQL 17 Monitoring](https://www.postgresql.org/docs/17/monitoring-stats.html)
- [PostgreSQL 17 Continuous Archiving](https://www.postgresql.org/docs/17/continuous-archiving.html)
