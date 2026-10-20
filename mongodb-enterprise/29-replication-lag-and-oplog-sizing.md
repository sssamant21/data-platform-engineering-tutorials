# 29 — Replication Lag and Oplog Sizing

**Status:** Written; static review complete; runtime lab validation pending  
**Part:** 4 — Replication and High Availability  
**Goal:** Measure replication progress and retained history, recover a secondary after a bounded outage, calculate an oplog capacity proposal and verify a member-local resize.  
**Audience:** DBREs, SREs and Platform Engineers  
**Time:** 90–120 minutes  
**Baseline:** MongoDB 8.0 and mongosh; Docker/Compose project from Chapter 26. Record exact versions and image digest.  
**Deployment:** Owned disposable three-voting-data-member `rs26` on one host. Exercises are Community-compatible; they do not validate Enterprise-only features.  
**Prerequisites:** Chapters 25–28; all three members running, adequate disk space, no concurrent lab automation.

## 1. Lag and retained history answer different questions

Replication lag asks how far a member's applied progress trails the primary. The oplog window describes the history currently available on a particular member. A secondary may be behind while its missing history remains available, or be unable to catch up because required history has already disappeared.

Fetching entries and applying them are separate stages. Diagnose transport and apply capacity separately. A larger oplog provides more recovery time; it does not make a slow secondary apply faster.

| Observation | Operational question | Limitation |
|---|---|---|
| Primary/secondary applied optimes | How far behind is applied progress? | Primary's remote observations can be delayed |
| Direct member status | What progress does this member report locally? | Samples across hosts are not simultaneous |
| Oldest/newest source oplog entries | What history can this source supply? | Boundaries move during collection |
| Stable fixture read | Did this member apply the expected business state? | A successful read alone does not establish durability |
| CPU, disk latency, network, logs | Why is progress slow? | Correlation needs workload and time context |

Use timestamp seconds for a coarse lag indicator and the full BSON Timestamp for ordering. Two operations can share a second but have different increment values. Never label an unreachable member as healthy with zero lag.

**Use case:** A secondary is unavailable during host maintenance while ingestion continues. The operator must determine whether incremental catch-up is still plausible, whether it can finish within the recovery budget, and whether surviving members have enough capacity.

## 2. Recovery budget and sizing model

Choose a retention target from the longest credible interruption, repair time, catch-up time and a contingency allowance. Include CDC consumer outages where applicable. These are environment planning inputs, not MongoDB defaults.

For a sustained design oplog rate:

```text
required logical oplog bytes = design bytes/second × retention seconds × safety factor
backlog bytes ≈ incoming bytes/second × disconnected seconds
catch-up seconds ≈ backlog bytes / (apply bytes/second − incoming bytes/second)
```

The catch-up equation is a planning approximation using comparable workload-equivalent byte rates. It requires apply capacity greater than incoming work. Different operation mixes can invalidate a simple byte-rate comparison. If apply capacity is no greater than arrival rate, backlog cannot drain under that workload.

Worked example: design rate 8 MiB/s, four-hour retention target, factor 1.5:

```text
8 × 3600 × 4 × 1.5 = 172800 MiB = 168.75 GiB logical oplog capacity
```

For a 30-minute interruption at 8 MiB/s and effective apply capacity of 20 MiB/s, backlog is approximately 14400 MiB; drain time is approximately 1200 seconds. Add repair time and contingency to the budget. This example is not a sizing recommendation for your deployment.

Logical BSON bytes, compressed storage allocation and application payload bytes differ. Reserve disk for data growth, journal, logs, temporary work and oplog growth. Use observed busy-period rates across representative ingestion, updates and deletes; a short lab burst cannot establish a production percentile.

## 3. Prerequisites and independent client

Use the retained Chapter 26 project and its exact Compose definition. Do not recreate or remove its volumes. Keep a host terminal beside the independent client.

```bash
docker compose -p mongodb-ch26 ps
docker run --rm -it --network mongodb-ch26_replica mongo:8.0 mongosh "mongodb://a:27017,b:27017,c:27017/?replicaSet=rs26&readPreference=primary&serverSelectionTimeoutMS=5000"
```

The network name assumes Chapter 26's project. Use the approved image digest for reproducibility. This isolated lab publishes no additional ports. In authenticated environments, use approved TLS/authentication and permissions for status, local oplog inspection, scoped writes and `replSetResizeOplog`; no role grants or credentials are included here.

## 4. Ownership and readiness checks

Run in the independent mongosh client:

```javascript
const hosts29 = ["a:27017", "b:27017", "c:27017"];
const name29 = "mongodb_enterprise_tutorial_ch29";
const lab29 = db.getSiblingDB(name29);
const wc29 = { w: "majority", j: true, wtimeout: 10000 };
function check29(condition, message) {
  if (!condition) throw new Error(message);
}
function direct29(host) {
  check29(hosts29.includes(host), "Host outside owned lab");
  const connection = new Mongo("mongodb://" + host +
    "/?directConnection=true&serverSelectionTimeoutMS=5000");
  connection.setReadPref("secondaryPreferred");
  return connection;
}
function status29() {
  return db.adminCommand({ replSetGetStatus: 1 });
}
function healthy29(s) {
  return s.ok === 1 && s.set === "rs26" && s.members.length === 3 &&
    s.members.filter(m => m.health === 1 && m.stateStr === "PRIMARY").length === 1 &&
    s.members.filter(m => m.health === 1 && m.stateStr === "SECONDARY").length === 2;
}
function waitHealthy29(timeoutMs = 90000) {
  const end = Date.now() + timeoutMs;
  let last;
  while (Date.now() < end) {
    try { last = status29(); if (healthy29(last)) return last; }
    catch (error) { print(error.message); }
    sleep(1000);
  }
  printjson(last);
  throw new Error("Topology did not recover within observation budget");
}
const cfg29 = db.adminCommand({ replSetGetConfig: 1 }).config;
check29(cfg29._id === "rs26" && cfg29.members.length === 3 &&
  cfg29.members.every(m => hosts29.includes(m.host) && !m.arbiterOnly &&
    !m.hidden && Number(m.votes === undefined ? 1 : m.votes) === 1 &&
    Number(m.priority === undefined ? 1 : m.priority) > 0 &&
    Number(m.secondaryDelaySecs || 0) === 0), "Unexpected replica configuration");
check29(lab29.getCollectionNames().length === 0,
        "Chapter database already exists; review before rerunning");
const initial29 = waitHealthy29();
const primary29 = initial29.members.find(m => m.stateStr === "PRIMARY").name;
const secondary29 = initial29.members.find(m => m.stateStr === "SECONDARY").name;
printjson({ version: db.version(), primary: primary29, target: secondary29 });
```

Record server/mongosh/Docker/Compose versions, project ownership and image digest. The 90-second timeout is an observation budget, not an SLA. Verify free disk and host resource headroom before starting the workload.

## 5. Measure applied lag and member history

```javascript
function lag29() {
  const s = status29();
  const p = s.members.find(m => m.health === 1 && m.stateStr === "PRIMARY");
  check29(p && p.optime && p.optime.ts, "Primary progress unavailable");
  return s.members.map(m => ({
    host: m.name, state: m.stateStr, health: m.health,
    appliedOptime: m.optime,
    lagSeconds: m.health === 1 && m.optime && m.optime.ts
      ? Math.max(0, p.optime.ts.getHighBitsUnsigned() -
                    m.optime.ts.getHighBitsUnsigned()) : null,
    syncSource: m.syncSourceHost || null
  }));
}
function history29(host) {
  const conn = direct29(host);
  const local = conn.getDB("local");
  const stats = local.runCommand({ collStats: "oplog.rs" });
  check29(stats.ok === 1, "Oplog stats failed: " + host);
  const oplog = local.getCollection("oplog.rs");
  const first = oplog.find().sort({ $natural: 1 }).limit(1).toArray()[0];
  const last = oplog.find().sort({ $natural: -1 }).limit(1).toArray()[0];
  check29(first && last, "No oplog history available");
  const ss = conn.getDB("admin").runCommand({ serverStatus: 1 });
  check29(ss.ok === 1, "serverStatus failed");
  return {
    host, maxBytes: Number(stats.maxSize), logicalBytes: Number(stats.size),
    storageBytes: Number(stats.storageSize), oldest: first.ts, newest: last.ts,
    windowSeconds: last.ts.getHighBitsUnsigned() - first.ts.getHighBitsUnsigned(),
    minRetentionHours: Number(ss.oplogTruncation?.oplogMinRetentionHours || 0)
  };
}
printjson(lag29());
const beforeHistory29 = hosts29.map(history29);
printjson(beforeHistory29);
```

Expect three healthy roles and nonnegative window values. Newly created or quiet sets may have very short populated windows even when their configured capacity is large. Primary status alone is not a complete view of each member's retained history.

## 6. Seed and reconcile deterministic state

```javascript
lab29.createCollection("events");
const events29 = lab29.events;
check29(events29.insertOne({ _id: "baseline", revision: 1 },
                          { writeConcern: wc29 }).acknowledged,
        "Baseline not acknowledged");
let expectedCount29 = 1;
function verify29(timeoutMs = 90000) {
  for (const host of hosts29) {
    const c = direct29(host).getDB(name29).events;
    const end = Date.now() + timeoutMs;
    let good = false;
    while (Date.now() < end) {
      good = c.countDocuments({}) === expectedCount29 &&
        c.countDocuments({ revision: 1 }) === expectedCount29 &&
        c.findOne({ _id: "baseline", revision: 1 }) !== null &&
        (expectedCount29 === 1 ||
          c.countDocuments({ _id: /^outage-/ }) === 1000);
      if (good) break;
      sleep(500);
    }
    check29(good, "Fixture failed to converge: " + host);
  }
}
verify29();
```

Exact count plus deterministic IDs and revision assertions detect partial or unexpected fixture state. Stable IDs let you reconcile errors without blindly replaying writes.

## 7. Failure exercise: one secondary misses a bounded burst

The trigger is a graceful stop of one validated secondary. The set retains two voting data members. Stop conditions include any other unhealthy member, primary change before the stop, write failure, or resource pressure. Stop no second member.

```javascript
const preStop29 = waitHealthy29();
check29(preStop29.members.find(m => m.name === primary29)?.stateStr === "PRIMARY",
        "Primary changed; reassess before outage");
check29(preStop29.members.find(m => m.name === secondary29)?.stateStr === "SECONDARY",
        "Target is no longer secondary");
verify29();
const savedTarget29 = direct29(secondary29).getDB("admin")
  .runCommand({ replSetGetStatus: 1 }).optimes.appliedOpTime.ts;
const source29 = direct29(primary29);
const startEntry29 = source29.getDB("local").getCollection("oplog.rs")
  .find().sort({ $natural: -1 }).limit(1).toArray()[0].ts;
const service29 = secondary29.split(":")[0];
print("STOP: docker compose -p mongodb-ch26 stop --timeout 60 " + service29);
print("RECOVER: docker compose -p mongodb-ch26 start " + service29);
```

Copy the generated stop command into the host terminal, then immediately return to the client. If shutdown escalates rather than completing gracefully, retain logs and report that outcome accurately. The exercise is bounded by document count, not a long unattended outage.

```javascript
const burstStarted29 = Date.now();
try {
  for (let batch = 0; batch < 10; batch++) {
    const docs = Array.from({ length: 100 }, (_, j) => ({
      _id: "outage-" + String(batch * 100 + j).padStart(4, "0"),
      revision: 1, payload: "x".repeat(4096)
    }));
    const result = events29.insertMany(docs, { writeConcern: wc29 });
    check29(result.acknowledged, "Batch not acknowledged");
    sleep(100);
  }
  check29(events29.countDocuments({ _id: /^outage-/ }) === 1000,
          "Burst count mismatch");
  expectedCount29 = 1001;
} catch (error) {
  print("WRITE FAILED; START THE STOPPED SERVICE NOW, THEN RECONCILE IDs");
  throw error;
}
const burstEnded29 = Date.now();
printjson({ burstMs: burstEnded29 - burstStarted29,
            primaryCount: events29.countDocuments({}), lastKnownTarget: savedTarget29 });
printjson(lag29());
```

Expected: the primary has 1001 documents; the stopped member is unavailable. Heartbeat status may take time to reflect the stop, so an early health=1 observation is not proof that it is reachable. Its recorded optime is historical. Do not query or label it as a live lagging secondary while it is stopped.

## 8. Measure generated logical oplog bytes

Restrict measurement to the chapter namespace and the entries after the recorded starting point:

```javascript
const totals29 = source29.getDB("local").getCollection("oplog.rs").aggregate([
  { $match: { ts: { $gt: startEntry29 }, ns: name29 + ".events", op: "i" } },
  { $group: { _id: null, entries: { $sum: 1 },
              bytes: { $sum: { $bsonSize: "$$ROOT" } } } }
]).toArray();
check29(totals29.length === 1 && Number(totals29[0].entries) === 1000,
        "Scoped oplog sample incomplete; do not calculate a rate");
const measuredBytes29 = Number(totals29[0].bytes);
const measuredSeconds29 = Math.max(0.001, (burstEnded29 - burstStarted29) / 1000);
printjson({ entries: totals29[0].entries, logicalBytes: measuredBytes29,
            observedBytesPerSecond: measuredBytes29 / measuredSeconds29 });
```

This rate includes deliberate sleeps and client overhead. It demonstrates measurement mechanics, not maximum throughput or a sustained production rate. Net change in collection `size` is unsuitable once old entries are being truncated. Namespace-scoped measurement also excludes other production traffic.

Do not run broad oplog aggregation repeatedly on a busy production member. Use bounded intervals, approved monitoring and representative whole-cluster rate collection. If history vanished or the source changed, reject the sample rather than filling missing data with zero.

## 9. Check history overlap and recover

Use full timestamps to check whether the previously applied point still exists on the original source:

```javascript
const overlap29 = source29.getDB("local").getCollection("oplog.rs")
  .findOne({ ts: savedTarget29 });
printjson({ savedTarget: savedTarget29, exactPointRetained: overlap29 !== null,
            sourceHistory: history29(primary29) });
print("RECOVER NOW: docker compose -p mongodb-ch26 start " + service29);
```

Overlap is useful evidence, not a guarantee: actual source selection, rollback history and resources still matter. Absence requires further diagnosis; it is not enough by itself to authorize deleting a member's data.

Run the generated start command in the host terminal, then:

```javascript
const catchupStarted29 = Date.now();
waitHealthy29();
verify29();
printjson({ recoveryObservationMs: Date.now() - catchupStarted29,
            finalCount: expectedCount29, progress: lag29() });
```

Expected: one primary, two secondaries and matching 1001-document fixtures on every member. A fast recovery may hide any visible live lag; do not manufacture a lag claim. Record elapsed observation and convergence rather than calling it pure apply time.

If recovery fails, keep the other members running and inspect the target's logs and disk. Chapter 30 covers resync/member replacement. Do not clear volumes, enable failpoints or force reconfiguration to make this lab pass.

## 10. Sizing calculator and insufficient-capacity test

```javascript
function capacity29(rateMiBps, hours, factor) {
  check29(rateMiBps > 0 && hours > 0 && factor >= 1, "Invalid planning inputs");
  const requiredMiB = rateMiBps * hours * 3600 * factor;
  return { requiredMiB, requiredGiB: requiredMiB / 1024 };
}
function drain29(incomingMiBps, applyMiBps, outageSeconds) {
  check29(incomingMiBps > 0 && applyMiBps >= 0 && outageSeconds >= 0,
          "Invalid catch-up inputs");
  if (applyMiBps <= incomingMiBps) return { canDrain: false, seconds: null };
  return { canDrain: true,
           seconds: incomingMiBps * outageSeconds / (applyMiBps - incomingMiBps) };
}
check29(capacity29(8, 4, 1.5).requiredMiB === 172800, "Sizing arithmetic failed");
check29(drain29(8, 20, 1800).seconds === 1200, "Catch-up arithmetic failed");
check29(!drain29(8, 6, 1800).canDrain, "Unsafe capacity case incorrectly passed");
printjson({ proposal: capacity29(8, 4, 1.5), catchup: drain29(8, 20, 1800),
            insufficientCapacity: drain29(8, 6, 1800) });
```

The failure diagnosis is insufficient apply capacity. Corrective options include investigating storage/CPU/index work, controlling incoming ingestion or provisioning adequate capacity. Increasing retention can preserve recovery options but does not correct the deficit. The synthetic classifier validates arithmetic only; it does not benchmark a member.

## 11. Guarded member-local resize

This optional exercise changes only the recovered secondary, after all assertions pass. Record original settings first. Require at least 2 GiB of free host filesystem space for this small increment and normal workload headroom. Recheck role immediately before the command; if any check fails, omit the optional exercise and record why.

```bash
docker compose -p mongodb-ch26 exec a df -h /data/db
docker compose -p mongodb-ch26 exec b df -h /data/db
docker compose -p mongodb-ch26 exec c df -h /data/db
```

All volumes are on one host in this lab: these checks do not represent independent fault domains.

```javascript
waitHealthy29();
verify29();
const originalSize29 = history29(secondary29);
const resizeConn29 = direct29(secondary29);
const resizeAdmin29 = resizeConn29.getDB("admin");
check29(resizeAdmin29.runCommand({ hello: 1 }).secondary === true,
        "Resize target is no longer secondary");
const originalMiB29 = originalSize29.maxBytes / (1024 * 1024);
const proposedMiB29 = Math.ceil(originalMiB29) + 128;
check29(proposedMiB29 > 990, "Proposed size outside lab bounds");
check29(resizeAdmin29.runCommand({
  replSetResizeOplog: 1, size: Double(proposedMiB29)
}).ok === 1, "Resize command failed");
const resized29 = history29(secondary29);
check29(Math.abs(resized29.maxBytes / (1024 * 1024) - proposedMiB29) < 1,
        "Configured size did not match proposal");
printjson({ original: originalSize29, resized: resized29,
            otherMembers: hosts29.filter(h => h !== secondary29).map(history29) });
waitHealthy29();
verify29();
```

The command is applied individually to self-managed members; it is not a replicated configuration change and is not an Atlas command. A production rollout needs a per-member plan, with secondaries first, disk checks and automation/startup configuration reconciliation. Record command output and readiness after each member.

Resizing does not restore entries already removed. The requested limit also does not immediately populate a longer time window. Minimum retention and majority commit-point protection can allow growth beyond nominal capacity. Monitor actual disk use as well as configured size.

Minimum retention can be changed separately using `minRetentionHours`. It is deliberately not changed in this lab. A retention policy needs a disk-exhaustion model and clock synchronization review. Never shrink history while a dependent member, stream or backup still needs it.

## 12. Production monitoring and incident decisions

Track lag by member, role/state, sync source, retained window by potential source, logical generation rate, disk free space, disk latency/queueing, CPU, cache pressure and application latency/errors. Keep source and member labels so a fleet average cannot hide one failing secondary.

Example policy inputs—not default thresholds:

| Signal | Example decision |
|---|---|
| Applied lag exceeds application's stale-read budget | Investigate reads routed to that member |
| Backlog grows over successive samples | Compare apply capacity with incoming work |
| Retained history falls below repair/recovery target | Escalate recovery risk and revise capacity |
| Missing-history indicators in logs | Assess supported resync path and impact |
| Disk free time-to-exhaustion shorter than response time | Address growth/resource pressure promptly |
| CDC consumer approaches available history boundary | Recover consumer or plan a consistent rebuild |

Lag is not automatically lost data and is not itself an RPO measurement. Majority acknowledgements do not imply every member has applied a write. A quiet primary's newest oplog timestamp may be old even when the set is caught up; compare progress rather than using wall-clock age alone.

Initial sync needs its own capacity and history budget. Include long-running bulk jobs, update/delete amplification, topology changes and CDC outages in planning. Validate catch-up under representative traffic and across actual fault domains before approving production maintenance.

## 13. Troubleshooting

| Symptom | Evidence | Cause to check | Action |
|---|---|---|---|
| Unreachable target appears to have zero lag | Connectivity and health beside optime | Last-known progress treated as current | Report unavailable/unknown; recover target |
| Small time lag but fixture missing | Full timestamp and direct fixture query | Within-second differences or sample delay | Verify actual state and complete progress |
| Window short despite large configured size | Oldest/newest, logical bytes | Young set or limited write history | Observe over time; do not claim full retention |
| Backlog persists after restart | Apply progress, workload, resource metrics | Arrival rate exceeds effective apply capacity | Resolve bottleneck/control load |
| One resize leaves other members unchanged | Direct per-member stats | Command is member-local | Use reviewed per-member rollout |
| Size increase yields no old entries | Oldest boundary before/after | Expired history cannot be recreated | Diagnose supported recovery path |
| Rate query returns fewer entries | Namespace, boundaries, topology history | Truncation/source change/partial writes | Reject sample and reconcile |
| Disk grows past nominal limit | Retention policy, commit progress, disk trends | History protected beyond size limit | Review policy and capacity |
| Restarted target cannot catch up | Target logs, source history and sync source | Missing overlap or operational failure | Assess Chapter 30 recovery procedure |
| Resize returns Unauthorized | Authenticated identity and privileges | Missing cluster-management action | Use approved operator permissions |

```bash
docker compose -p mongodb-ch26 ps
docker compose -p mongodb-ch26 logs --tail 100 a b c
```

Preserve the failed operation and exact affected member. Avoid repeated restart cycles and unreviewed reconfiguration.

## 14. Cleanup and settings restoration

Start any stopped service first. Full readiness and fixture convergence are required before cleanup. If the optional resize was executed, restore only its original size on the same member. Shrink is permitted here only for the owned small fixture after all members converge and no streams/backups depend on this lab history.

```javascript
waitHealthy29();
verify29();
// Execute this block only if Section 11 actually resized the member.
check29(resizeAdmin29.runCommand({
  replSetResizeOplog: 1, size: Double(originalMiB29)
}).ok === 1, "Original size restoration failed");
check29(Math.abs(history29(secondary29).maxBytes - originalSize29.maxBytes) < 1024 * 1024,
        "Original configured size not restored");
waitHealthy29();
verify29();
```

If Section 11 was omitted, skip that entire restoration block. Minimum retention was not changed. Reduced configured size does not guarantee filesystem space reclamation; no compact operation is performed.

Then remove only the chapter database:

```javascript
check29(events29.countDocuments({}) === 1001, "Unexpected final fixture state");
check29(lab29.getName() === "mongodb_enterprise_tutorial_ch29",
        "Refusing cleanup outside the Chapter 29 training database");
check29(lab29.dropDatabase().ok === 1, "Chapter cleanup failed");
check29(lab29.getCollectionNames().length === 0, "Chapter database not empty");
waitHealthy29();
```

If writes failed, reconcile stable IDs and recover topology before adapting cleanup; do not bypass final assertions. Retain Chapter 26 volumes for Chapter 30. No votes, priorities, FCV, image or delay settings changed.

## 15. Acceptance and evidence

- [ ] Recorded versions, image digest, ownership, member config and resource headroom.
- [ ] Collected applied progress and member-local history before the exercise.
- [ ] Seeded and verified baseline on every member.
- [ ] Stopped only a validated secondary and preserved its last-known timestamp.
- [ ] Reconciled all 1000 bounded burst inserts with majority acknowledgement.
- [ ] Measured exactly 1000 scoped oplog entries and stated rate limitations.
- [ ] Captured overlap evidence without treating it as a catch-up guarantee.
- [ ] Restarted the same service and verified 1001-document convergence everywhere.
- [ ] Checked sizing/drain arithmetic and insufficient-capacity classification.
- [ ] Recorded optional resize execution or omission, and restored settings if changed.
- [ ] Restored full topology before scoped cleanup.

**Evidence:** versions/config, before/after status, timestamps/windows, generated stop/start commands, logs, fixture assertions, scoped BSON-byte totals, sizing inputs, optional resize results and cleanup. Runtime validation remains pending until executed. This one-host lab does not establish production throughput, fault-domain resilience or a recovery SLA.

## 16. Review questions

1. Why does a larger oplog not fix insufficient apply capacity?
2. Why should an offline member's lag be reported as unavailable or historical?
3. How can two members share timestamp seconds but still differ in progress?
4. Why can a newly enlarged oplog still have a short populated history window?
5. Which workloads should inform the design generation rate?
6. What happens to the drain estimate when arrival rate reaches apply capacity?
7. Why must resizing and verification happen on each intended member?
8. What recovery dependencies must be checked before shrinking retention?

## 17. Official references

- [MongoDB 8.0: replica-set oplog](https://www.mongodb.com/docs/v8.0/core/replica-set-oplog/)
- [MongoDB 8.0: replSetGetStatus](https://www.mongodb.com/docs/v8.0/reference/command/replSetGetStatus/)
- [MongoDB 8.0: check replica-set status](https://www.mongodb.com/docs/v8.0/tutorial/check-replica-set-status/)
- [MongoDB 8.0: change oplog size](https://www.mongodb.com/docs/v8.0/tutorial/change-oplog-size/)
- [MongoDB 8.0: replSetResizeOplog](https://www.mongodb.com/docs/v8.0/reference/command/replSetResizeOplog/)
- [MongoDB 8.0: $bsonSize](https://www.mongodb.com/docs/v8.0/reference/operator/aggregation/bsonSize/)
- [MongoDB 8.0: resync a replica-set member](https://www.mongodb.com/docs/v8.0/tutorial/resync-replica-set-member/)

---

Previous: [Chapter 28 — Elections Stepdown and Planned Maintenance](28-elections-stepdown-and-planned-maintenance.md)  
Next: [Chapter 30 — Initial Sync Resync and Member Replacement](30-initial-sync-resync-and-member-replacement.md).
