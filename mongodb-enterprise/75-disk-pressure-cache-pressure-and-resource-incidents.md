# 75 — Disk Pressure Cache Pressure and Resource Incidents

Part 10 — Troubleshooting and Production Projects

**Audience:** DBREs, SREs, Platform Engineers and on-call operators.  
**Goal:** Distinguish space exhaustion, storage performance, cache/memory pressure and CPU contention; capture bounded evidence and verify recovery without destructive shortcuts.  
**Baseline:** Retained authenticated TLS MongoDB 8.0 / FCV 8.0 replica set; exact recorded mongosh, Python 3.11+ and authorized host/Kubernetes monitoring access. Core lab is Community-compatible.  
**Status:** Written; syntax and offline resource-triage checks complete; live resource evidence and recovery acceptance pending.  
**Prerequisites:** Chapters 23–24, 29, 49–56, 61 and 69–74; member-to-volume inventory, capacity reserve, SLOs and recovery ownership.  
**Estimated time:** 60–90 minutes for bounded labs; incident response begins with user impact and available headroom.

## 1. Incident acceptance contract

High disk utilization and high cache occupancy are observations, not complete diagnoses. Record affected service/member/volume, UTC window, application errors/latency, growth and recent ingestion, index, backup or placement changes.

This chapter uses read-only resource observations, a modest owned MongoDB fixture and offline pressure scenarios. It deliberately does not fill a volume, exhaust memory, run compact/repair, delete database files or restart members to create an incident.

Acceptance requires correct resource identity/units, fresh evidence, a bounded data/query fixture, separation of logical and physical storage, triage that preserves unknown states, and a recovery packet covering service, replication and headroom.

## 2. Separate the resource failure modes

| Failure mode | Evidence | Initial action boundary |
|---|---|---|
| Filesystem capacity | Free/used bytes, inodes, growth and mount identity | Preserve write/recovery reserve; control avoidable growth |
| Storage performance | Latency, queueing, IOPS/throughput and device limits | Reduce competing demand or remediate proven device constraint |
| WiredTiger cache pressure | Cache/dirty bytes, eviction/read activity and application latency | Correlate working-set demand and storage behavior |
| Host/container memory | RSS/working set, limits, swap/OOM and other consumers | Distinguish DB cache from total process/node memory |
| CPU/throttling | Utilization, quota throttling, runnable work and query demand | Diagnose expensive work and scheduling limits |
| Replication/recovery impact | Member states, lag, history and backup boundary | Stop additional disruptive maintenance |

A disk can have substantial free space but insufficient IOPS. A cache can be highly occupied during normal operation. A container can hit its memory limit while the host has free RAM. Use member/process/volume identities from Chapter 69 to correlate these signals.

## 3. Immediate incident sequence

1. Confirm service impact and monitoring freshness; identify the constrained member/volume.
2. Assess remaining write/recovery reserve and time to breach using Chapter 70's growth/lead-time model.
3. Preserve logs, FTDC and recent resource snapshots through the restricted evidence procedure.
4. Review competing ingestion, index builds, backups, TTL and query demand.
5. Apply an already accepted bounded demand-control mitigation if required.
6. Select one evidence-supported resource action with owner, stop conditions and recovery path.
7. Verify application correctness, resource trend, replication and retained recovery history.

Do not remove WiredTiger files, journal, history store or oplog files from dbPath. They are database state, not disposable cleanup targets. Do not use `repair` as a general disk-pressure fix. If corruption or recovery failure is suspected, follow the supported recovery plan with preserved source evidence.

## 4. Read-only host and volume evidence

Set the actual data mount path from the recorded deployment configuration. Run from the authorized host/container context, not from an unrelated workstation.

```bash
export CH75_DATA_PATH='/recorded/data/mount'
df -h "$CH75_DATA_PATH"
df -i "$CH75_DATA_PATH"
```

Record mount/device, byte values, inode availability and UTC time. Human-readable output is for inspection; use bytes for calculations. A container mount must be mapped to the correct PVC/cloud volume. OS disk and database data disk may have different capacity/performance limits.

A bounded filesystem snapshot script:

```python
import os
import shutil
from datetime import datetime, timezone

path = os.environ["CH75_DATA_PATH"]
usage = shutil.disk_usage(path)
print({"utc": datetime.now(timezone.utc).isoformat(), "path": path,
       "total_bytes": usage.total, "used_bytes": usage.used,
       "free_bytes": usage.free})
```

Save as `ch75_filesystem.py`. It reports the filesystem backing that path, not MongoDB's logical collection size. Repeat at the approved cadence and compare only the same mount/device.

For Linux I/O/CPU evidence, use already installed authorized monitoring tools or the platform's existing telemetry. If available, a short `iostat -xz 1 5` and `vmstat 1 5` capture can help; the initial cumulative report differs from subsequent interval reports. Do not install packages or run unbounded recursive scans during a critical incident merely to obtain a familiar command.

Directory size scans can add I/O. Use existing file/volume inventory first; scope any required scan and record its impact. For deleted-but-open logs, verify the specific process/file and rotation policy with the host owner. Do not issue a cluster-wide restart to reclaim a suspected log without confirming identity and availability effects.

## 5. Member-local cache and execution evidence

Use Chapter 42's verified TLS/SCRAM observer and a recorded member endpoint. Collect two observations through Chapter 69's reset-safe sampler if rates are required.

```javascript
var status = db.getSiblingDB("admin").runCommand({ serverStatus: 1 });
if (status.ok !== 1) throw new Error("Resource observation failed");
var cache = status.wiredTiger && status.wiredTiger.cache;
printjson({ observedAt: new Date(), host: status.host, pid: status.pid,
  uptime: status.uptime, mem: status.mem, queues: status.queues,
  cache: cache && {
    configuredBytes: cache["maximum bytes configured"],
    usedBytes: cache["bytes currently in the cache"],
    dirtyBytes: cache["tracked dirty bytes in the cache"],
    pagesRead: cache["pages read into cache"],
    pagesWritten: cache["pages written from cache"]
  } });
```

Preserve missing fields rather than replacing them with zero. ServerStatus layouts and execution-queue fields are version-dependent. Use valid same-process deltas for cumulative page counters and current values for cache gauges.

WiredTiger cache is not total process memory: filesystem cache and other consumers also matter.[1] Compare configured cache against actual container limits/other processes and observed server memory-limit interpretation. Do not automatically increase cache size because occupancy is high.

On the 8.0 baseline, concurrency controls are dynamically managed; low available execution tickets alone do not prove overload. Correlate queued work, latency and demand rather than tuning internal concurrency parameters as an incident shortcut.[1]

## 6. Lab A — modest owned fixture and storage measurements

Create a fresh namespace through the authorized lifecycle identity. The fixture is bounded and not intended to stress a production-sized cache or disk.

```javascript
var labName = "mongodb_enterprise_ch75_resources";
var lab = db.getSiblingDB(labName);
function check(condition, message) { if (!condition) throw new Error(message); }
check(lab.getCollectionInfos().length === 0, "Namespace already exists");
check(db.hello().isWritablePrimary === true, "Expected writable primary");
lab.ownership.insertOne({ _id: "mongodb-enterprise-tutorial-ch75", createdAt: new Date() });
lab.items.createIndex({ seq: 1 }, { name: "seq_index", unique: true });
for (var batch = 0; batch < 5; batch++) {
  var rows = [];
  for (var offset = 0; offset < 1000; offset++) {
    var i = batch * 1000 + offset;
    rows.push({ _id: i, seq: i, value: i * 3, payload: "x".repeat(512) });
  }
  lab.items.insertMany(rows, { writeConcern: { w: "majority", wtimeout: 10000 } });
}
check(lab.items.countDocuments({}) === 5000, "Expected 5000 owned rows");
var statsBefore = lab.runCommand({ collStats: "items", scale: 1 });
check(statsBefore.ok === 1, "Collection stats failed");
printjson({ count: statsBefore.count, logicalBytes: statsBefore.size,
  allocatedStorageBytes: statsBefore.storageSize, indexBytes: statsBefore.totalIndexSize });
var rows = lab.items.find({ seq: { $gte: 4990 } }, { _id: 1, seq: 1, value: 1 })
  .sort({ seq: 1 }).limit(10).maxTimeMS(10000).toArray();
check(rows.length === 10 && rows[0].value === 14970 && rows[9].value === 14997,
      "Owned query correctness failed");
```

Expected: 5,000 correct rows and ten terminal values 14970–14997. The repetitive payload is compressible; do not extrapolate its storage ratio to real application data. `size`, `storageSize`, indexes and filesystem used/free bytes are different quantities.

## 7. Lab B — logical deletion is not guaranteed filesystem reclamation

Delete only the first half of this synthetic fixture, then verify the remaining application contract and compare storage observations. Production retention/deletion needs its own data-owner/recovery acceptance.

```javascript
var deleted = lab.items.deleteMany({ seq: { $lt: 2500 } }, {
  writeConcern: { w: "majority", wtimeout: 10000 }
});
check(deleted.deletedCount === 2500, "Owned delete count mismatch");
check(lab.items.countDocuments({}) === 2500, "Remaining count mismatch");
var statsAfter = lab.runCommand({ collStats: "items", scale: 1 });
check(statsAfter.ok === 1, "Post-delete stats failed");
printjson({ count: statsAfter.count, logicalBytes: statsAfter.size,
  allocatedStorageBytes: statsAfter.storageSize, indexBytes: statsAfter.totalIndexSize });
var remaining = lab.items.find({ seq: { $gte: 4990 } }, { _id: 1, seq: 1, value: 1 })
  .sort({ seq: 1 }).limit(10).maxTimeMS(10000).toArray();
check(remaining.length === 10 && remaining[0].value === 14970 &&
      remaining[9].value === 14997, "Remaining data contract changed");
```

Expected: exact logical count reduction with preserved terminal query results. Record actual storage/filesystem observations; do not assert that disk usage must fall by half or that any specific amount is reclaimed immediately. Reusable allocation, indexes, compression, checkpoints and other workload can affect physical measurements.

Rerun the read-only filesystem snapshot if authorized. This same-volume small lab may show negligible or noisy filesystem change. That is acceptable evidence of measurement limits, not a reason to fill the disk or run an intrusive reclamation command.

## 8. Lab C — offline pressure triage and failure cases

Save as `ch75_triage.py`. Inputs are already reviewed normalized evidence; thresholds are illustrative teaching choices. The helper flags supported risks and leaves incomplete evidence unresolved. It does not automatically identify a root cause or perform remediation.

```python
from dataclasses import dataclass, replace
from math import isfinite


@dataclass(frozen=True)
class Evidence:
    free_gib: float
    reserve_gib: float
    cache_used_gib: float
    cache_max_gib: float
    io_latency_ms: float
    io_latency_budget_ms: float
    service_affected: bool
    eviction_pressure_observed: bool
    memory_limit_breach_observed: bool
    cpu_throttling_observed: bool
    complete: bool = True


def triage(evidence):
    values = (evidence.free_gib, evidence.reserve_gib, evidence.cache_used_gib,
              evidence.cache_max_gib, evidence.io_latency_ms, evidence.io_latency_budget_ms)
    if not all(isfinite(value) and value >= 0 for value in values):
        raise ValueError("Invalid resource input")
    if evidence.cache_max_gib <= 0 or evidence.io_latency_budget_ms <= 0:
        raise ValueError("Missing positive cache/latency contract")
    for name in ("service_affected", "eviction_pressure_observed",
                 "memory_limit_breach_observed", "cpu_throttling_observed", "complete"):
        if not isinstance(getattr(evidence, name), bool):
            raise ValueError("Evidence flags must be explicit booleans")
    if not evidence.complete:
        return {"status": "unresolved_missing_evidence", "risks": []}
    risks = []
    if evidence.free_gib <= evidence.reserve_gib:
        risks.append("disk_reserve_breach")
    if evidence.io_latency_ms > evidence.io_latency_budget_ms:
        risks.append("storage_latency_budget_breach")
    if evidence.eviction_pressure_observed and evidence.service_affected:
        risks.append("cache_demand_investigation")
    if evidence.memory_limit_breach_observed:
        risks.append("memory_limit_incident")
    if evidence.cpu_throttling_observed and evidence.service_affected:
        risks.append("cpu_throttling_investigation")
    return {"status": "investigate" if risks else "no_flagged_risk_in_this_packet",
            "risks": risks, "cache_occupancy": evidence.cache_used_gib/evidence.cache_max_gib}


baseline = Evidence(200, 100, 9.5, 10, 2, 10, False, False, False, False)
assert triage(baseline)["risks"] == []  # 95% cache occupancy alone is not an incident.
cases = {
    "disk": (replace(baseline, free_gib=50), "disk_reserve_breach"),
    "io": (replace(baseline, io_latency_ms=30), "storage_latency_budget_breach"),
    "cache": (replace(baseline, service_affected=True, eviction_pressure_observed=True),
              "cache_demand_investigation"),
    "memory": (replace(baseline, memory_limit_breach_observed=True), "memory_limit_incident"),
    "cpu": (replace(baseline, service_affected=True, cpu_throttling_observed=True),
            "cpu_throttling_investigation"),
}
for name, (packet, expected) in cases.items():
    result = triage(packet)
    assert expected in result["risks"]
    print(name, result)
assert triage(replace(baseline, complete=False))["status"] == "unresolved_missing_evidence"
print("PASS: capacity/I/O/cache/memory/CPU scenarios and missing-evidence boundary")
```

Run `python ch75_triage.py`. Expected: high occupancy alone is unflagged; each supported risk is reported; incomplete evidence is unresolved. “No flagged risk” is restricted to this packet and model, not a universal healthy-cluster decision.

## 9. Recovery branches and action boundaries

| Finding | Supported action direction | Required post-check |
|---|---|---|
| Data volume near reserve | Bound avoidable ingestion; expand/migrate through approved storage owner | Actual filesystem expansion, reserve/growth and application writes |
| Log volume growth | Verify destination, rotation, shipping and file/process identity | New log writes, retained evidence and reclaimed space where applicable |
| I/O constraint | Reduce competing demand or remediate device throughput/IOPS limit | Latency/queue trend plus service and replication improvement |
| Query-driven cache demand | Correct expensive scan/payload/concurrency from Chapter 73 | Same results with reduced work and improved application metrics |
| Container OOM/limit issue | Review effective limits, cache and total consumers through operator/IaC | Stable memory, no new OOM, accepted role/failure-mode load |
| CPU throttling | Review quota, expensive workload and placement | Throttling/demand/service evidence under representative load |
| Replication/history risk | Restore catch-up capacity and reduce conflicting work | Member acceptance and retained recovery history |

Choose a bounded action with expected effect and stop conditions. Preserve original settings and authoritative configuration owner. Expansion must include the actual filesystem/PVC/cloud lifecycle; changing a desired size alone does not prove usable capacity increased.

Restarting can create cold-cache demand, elections or recovery I/O. It does not repair an undersized device or uncontrolled ingestion. If a restart is required for a verified cause, use Chapter 71's quorum/maintenance gates and accepted sequential recovery procedure.

## 10. Reclamation and durability boundaries

`compact` is a specific storage maintenance operation with version, member-role and performance considerations.[2] Do not run it during a capacity incident merely because logical documents were deleted. Estimate reclaimable space and maintenance headroom through the exact installed-version procedure; preserve backups and service/recovery acceptance.

Logical deletion, hiding an index, dropping an index and releasing a volume have distinct effects. A hidden index remains maintained. Removing required data or constraints is not a storage optimization under the original application contract.

History-store or journal growth may reflect workload/snapshot/checkpoint/durability behavior.[1] Identify contributing operations and supported retention/configuration semantics. Removing those files can destroy recovery state. Do not weaken write concern or durability to reduce resource usage during an incident.

Initial sync/member replacement can be a separately planned recovery/reclamation path, but it needs source history, healthy redundancy, adequate storage and full acceptance from Chapter 30. Never resync multiple members concurrently as a disk cleanup shortcut.

## 11. Kubernetes and cloud resource correlation

Distinguish pod memory limit, host memory, process RSS, filesystem cache and WiredTiger cache. Inspect OOM/restart events and effective cgroup limits alongside MongoDB observations. Verify node/PVC placement, capacity and I/O performance characteristics from the actual cloud resource.

CPU requests are scheduling inputs; limits/quotas can constrain runtime. A higher host CPU count does not prove the container has that quota. A PVC expansion request does not prove the filesystem is resized or that the disk has the required IOPS.

Cloud burst credits, per-volume limits and VM aggregate throughput can all constrain a database. Compare the observed workload to the documented actual provisioned configuration, not to a different disk tier's advertised performance.

For operator-managed deployments, implement changes in the accepted resource/IaC path. Verify desired configuration, controller reconciliation and actual MongoDB service behavior before closing the incident.

## 12. Recovery verification and prevention

Recovery evidence must show correct application reads/writes, restored latency/error objectives, stable resource trend, member roles/replication and history/backup readiness. Use a representative observation window including the triggering batch pattern where possible.

Record what changed and what remains uncertain. A free-space improvement after pausing ingestion is not proof of a permanent capacity fix. A cache drop after restart is not proof that the working-set problem is resolved.

Prevention actions can include query/concurrency controls, retention ownership, volume growth forecasts, tested expansion lead time, log rotation/shipper recovery, resource-limit inventory and failure-mode capacity tests. Each action needs an owner and acceptance metric rather than a generic “monitor closely.”

## 13. Troubleshooting matrix

| Symptom | Evidence | Cause to test | Corrective action and verification |
|---|---|---|---|
| High disk percentage but normal latency | Free bytes/reserve/growth | Future capacity risk rather than current I/O incident | Forecast reserve crossing and remediation lead time |
| Free disk but reads/writes slow | Device latency, queues and limits | Throughput/IOPS bottleneck | Remediate proven constraint; verify service/replication |
| Cache nearly full | Eviction/I/O and service metrics | Normal occupancy or working-set pressure | Investigate correlated pressure, not occupancy alone |
| Host has RAM but pod OOMs | Container limits/events and process consumers | Effective cgroup constraint | Correct accepted limits/cache/placement and verify recovery |
| Delete succeeded but filesystem same | Logical/allocated/index/volume bytes | Reusable allocation or other growth | Preserve measurement distinction; review supported maintenance separately |
| Logs deleted but space not recovered | Exact open file/process and rotation | Deleted-but-open file | Follow owner-approved reopen/restart; verify identity and availability |
| History store grows | Snapshot/workload and exact server evidence | Retained older versions/workload | Review supported cause/retention; never remove the file |
| CPU idle but query queues grow | Throttling, I/O, locks and client concurrency | Non-CPU boundary or quota mismatch | Locate actual bottleneck; bound conflicting demand |
| Expansion requested but volume unchanged | Controller/cloud/PVC/filesystem states | Incomplete lifecycle step | Finish supported expansion and verify actual usable capacity |
| Pressure improves but lag remains | Secondary catch-up/history and resources | Recovery backlog | Stop further maintenance until replication accepted |

## 14. Acceptance and owned cleanup

| Check | Required evidence |
|---|---|
| Scope/time | Affected service/member/volume, UTC window and actual versions |
| Physical evidence | Free/used bytes, inode state, I/O context and correct volume identity |
| Cache/memory | Member/process samples plus host/container limits and pressure evidence |
| Fixture | 5,000 rows and terminal values 14970–14997 |
| Deletion drill | 2,500 removed, 2,500 retained, terminal query preserved; actual storage observations |
| Triage | Actual offline risk/missing-evidence cases passed |
| Recovery | Service correctness/latency, resources, replication and recoverability accepted |

Save nonsecret observations, then clean only the owned MongoDB fixture through the lifecycle identity:

```javascript
var labName = "mongodb_enterprise_ch75_resources";
var lab = db.getSiblingDB(labName);
if (labName !== "mongodb_enterprise_ch75_resources" || lab.getName() !== labName) {
  throw new Error("Refusing cleanup outside Chapter 75 database");
}
check(lab.ownership.findOne({ _id: "mongodb-enterprise-tutorial-ch75" }) !== null,
      "Ownership missing");
check(lab.items.countDocuments({}) === 2500, "Reconcile expected lab state before cleanup");
check(lab.dropDatabase().ok === 1, "Owned cleanup failed");
check(db.getSiblingDB(labName).getCollectionInfos().length === 0, "Collections remain");
print("PASS: chapter-owned resource fixture removed");
```

If interrupted before deletion, inspect the owned count/state and resume the missing acceptance step before cleanup. Keep database engine files, logs/FTDC, deployment resources and other chapter data under their original lifecycle. Local scripts/evidence follow the recorded lab retention policy.

Review questions:

1. How do filesystem capacity and storage-performance incidents differ?
2. Why does cache occupancy alone not establish pressure?
3. Why must container limits be compared with total memory consumers?
4. What does logical deletion fail to guarantee about filesystem bytes?
5. Why can a restart worsen recovery resource demand?
6. Which evidence proves a requested expansion actually completed?
7. Why do compact/member resync need their own maintenance acceptance?
8. What proves incident recovery beyond a single improved resource gauge?

## 15. DBRE/SRE extension — Kubernetes resource emergency and recovery gates

This extension defines operational controls for real incidents. It does **not** authorize filling a disk, evicting MongoDB pods, deleting diagnostic files, compacting collections or forcing replica-set elections.

### 15.1 Incident command and risk priorities

| Priority | Evidence | Action boundary |
|---|---|---|
| Protect customer correctness and write availability | Application errors/timeouts, acknowledged write outcomes, primary state, quorum | Coordinate incident commander and DBRE; avoid unreviewed restarts or write concern changes |
| Preserve recoverability | Oplog time span, secondary catch-up, backup freshness, restore-test status | Stop overlapping maintenance; do not remove recovery artifacts |
| Preserve remaining storage headroom | Exact PVC/device free bytes, inodes, growth, maintenance reserve, expansion lead time | Limit avoidable ingestion through an approved service mechanism; escalate capacity expansion |
| Isolate performance bottleneck | IO latency/queues, throttling, WiredTiger eviction, CPU and memory pressure | Treat occupancy as context, not automatic remediation |
| Restore telemetry and evidence | Collector freshness, logs, FTDC, pod restart history | Capture bounded artifacts; do not delete FTDC to make space |

Record incident ID, severity, affected tenant/service, member/shard/volume mapping, UTC window, on-call owner, incident commander, changes in flight and communication cadence.

### 15.2 Kubernetes-specific read-only triage

Use the existing authorized namespace and RBAC. The following commands are **examples only**; set `NS` and `POD` to verified values, and confirm your context before use.

```bash
kubectl config current-context
kubectl -n "$NS" get pod "$POD" -o wide
kubectl -n "$NS" describe pod "$POD"
kubectl -n "$NS" get pvc -o wide
kubectl -n "$NS" get events --sort-by=.lastTimestamp
kubectl -n "$NS" top pod "$POD" --containers
```

The metrics-server-backed `kubectl top` may be unavailable or insufficient for IO and filesystem evidence. Correlate container memory working set and limits, OOMKilled/restart reason, CPU throttling from an approved metrics backend, node pressure, storage-class capabilities, PVC/PV identity, CSI controller events and underlying cloud volume metrics. Do not infer database free bytes from PVC requested capacity alone.

For StatefulSets/operators, inspect the **authoritative custom resource/GitOps source** and storage expansion support. Verify whether the storage class allows expansion, whether filesystem growth needs a pod restart, and whether that restart is safe for current quorum/replication. Never delete a PVC or recreate a StatefulSet as a generic expansion fix.

### 15.3 Safe storage expansion runbook

1. Verify the constrained filesystem and member identity, cloud volume ID, physical used/free bytes and predicted reserve breach.
2. Confirm storage class/driver expansion support, quota and device performance limits, commercial approval, change owner and backup/recovery readiness.
3. Review one-member-at-a-time constraints, pod disruption budgets, topology and current election/lag state.
4. Change the **authoritative** resource specification under an approved change; record requested and observed capacity.
5. Watch PVC/controller/filesystem resize status and any required controlled filesystem action. Do not assume a successful API patch means usable bytes increased.
6. Verify filesystem free bytes **inside the MongoDB container**, actual IO latency, application latency/error SLO, replica health and history headroom.
7. Roll back only through a supported path. Many volume systems do **not** support shrinking; plan forward recovery/migration instead of promising an inverse resize.

If the expansion cannot finish before reserve exhaustion, escalate to the incident commander for workload-specific containment with an explicit data-integrity review.

### 15.4 Memory/cache/CPU incident decision tree

- **High WiredTiger cache occupancy without eviction/read IO or SLO impact:** observe trend; do not restart or reduce cache automatically.
- **Eviction pressure with read IO latency and rising query P99:** inspect working set, query plans, disk limits and workload changes; choose scoped query/load remediation.
- **Container OOM or memory-limit breach:** correlate WiredTiger cache, other mongod allocations, sidecars, container limit and node eviction; propose sizing change with headroom and one-member-at-a-time safety.
- **CPU throttling with high application latency:** confirm quota throttling and expensive operations before changing CPU limits/requests.
- **Disk latency/IOPS saturation despite free bytes:** diagnose storage tier/limits and noisy workload; adding capacity alone may not resolve throughput.

Each branch requires a before/after measurement, owner, stop condition and documented service/recovery verification.

### 15.5 Incident evidence manifest and offline gate

Save as `ch75-incident.json`:

```json
{
  "chapter": 75,
  "incident_id": "NOT_ASSIGNED",
  "incident_commander": "NOT_ASSIGNED",
  "dbre_owner": "NOT_ASSIGNED",
  "platform_owner": "NOT_ASSIGNED",
  "member_volume_identity_verified": false,
  "monitoring_fresh": false,
  "application_slo_recorded": false,
  "replica_and_recovery_health_recorded": false,
  "physical_capacity_and_inodes_recorded": false,
  "io_cache_memory_cpu_correlated": false,
  "capacity_reserve_and_lead_time_recorded": false,
  "change_and_rollback_approved": false,
  "post_recovery_service_verified": false,
  "post_recovery_storage_verified": false,
  "evidence_references": []
}
```

Save as `ch75_incident_gate.py`:

```python
import json
from pathlib import Path

p = json.loads(Path("ch75-incident.json").read_text(encoding="utf-8"))
checks = (
    "member_volume_identity_verified", "monitoring_fresh",
    "application_slo_recorded", "replica_and_recovery_health_recorded",
    "physical_capacity_and_inodes_recorded", "io_cache_memory_cpu_correlated",
    "capacity_reserve_and_lead_time_recorded", "change_and_rollback_approved",
    "post_recovery_service_verified", "post_recovery_storage_verified",
)
missing = [key for key in checks if p.get(key) is not True]
for key in ("incident_id", "incident_commander", "dbre_owner", "platform_owner"):
    if not isinstance(p.get(key), str) or not p[key].strip() or p[key].startswith("NOT_"):
        missing.append(key)
if not isinstance(p.get("evidence_references"), list) or not p["evidence_references"]:
    missing.append("evidence_references")
if missing:
    raise SystemExit("NOT ACCEPTED: " + ", ".join(missing))
print("PASS: incident evidence declarations complete; independently verify artifacts")
```

Run `python ch75_incident_gate.py`. The untouched template must fail. The gate checks declarations only; it cannot prove real storage expansion, safe failover or recovery. Record **NOT RUN** for any unexecuted lab, and obtain independent review before closing the production incident.

---

## 16. Official references and validation status

1. [MongoDB 8.0 — WiredTiger Storage Engine](https://www.mongodb.com/docs/v8.0/core/wiredtiger/).
2. [MongoDB 8.0 — compact](https://www.mongodb.com/docs/v8.0/reference/command/compact/).
3. [MongoDB 8.0 — serverStatus](https://www.mongodb.com/docs/v8.0/reference/command/serverStatus/).

Documentation reviewed on 2026-10-12. The bounded fixture, normalized triage flags and reserve/latency examples are teaching designs. Python/JavaScript and shell syntax plus actual offline triage/invalid-input assertions were checked. These checks do not validate live disk/cache behavior, exact server fields, Kubernetes/cloud limits, reclamation, expansion or production recovery. No resource exhaustion or live remediation was executed in the authoring environment.

**Chapter completion:** Written and statically reviewed; offline triage acceptance complete. Runtime validation remains pending until the authorized resource observations, fixture/deletion checks and owned cleanup are executed with evidence.

Previous: [Chapter 74 — Connection Authentication and TLS Troubleshooting](74-connection-authentication-and-tls-troubleshooting.md).  
Next: Chapter 76 — Replication Elections and Sharding Troubleshooting.
