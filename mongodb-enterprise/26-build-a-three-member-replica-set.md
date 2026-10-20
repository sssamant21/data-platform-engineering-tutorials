# 26 — Build a Three Member Replica Set

**Status:** Written; static review complete; runtime lab validation pending  
**Part:** 4 — Replication and High Availability  
**Goal:** Build an isolated three-data-member replica set, verify client discovery and majority writes, and confirm the fixture reaches both secondaries.  
**Audience:** DBREs, SREs, Developers and Platform Engineers  
**Time:** 90–120 minutes  
**Baseline:** MongoDB 8.0 image and mongosh, Docker Engine/Desktop with Compose v2; record exact versions and image digest.  
**Deployment:** Community-compatible disposable Docker lab with three WiredTiger members on one host. No authentication/TLS, no published host ports.

## 1. What this build proves

Chapter 25 inspected an existing set. This chapter creates a reproducible teaching topology with three voting data-bearing members. The lab verifies:

- Each member has separate persistent data storage.
- All members share one set name and reachable advertised hostnames.
- One member becomes primary and two become secondaries.
- A replica-set-aware client discovers the topology.
- A majority-acknowledged fixture eventually appears on both secondaries.

All three members share a Docker host. The lab does not prove host/zone redundancy, secure production deployment, failover acceptance or backup recovery. Chapters 28–32 develop failure behavior.

Do not put this unauthenticated topology on a public/shared production network. It uses an internal project network and exposes no host ports. Client commands run inside a member container where service names are resolvable. Production requires an explicit authentication/TLS and failure-domain design.

## 2. Network and storage contract

| Member | Advertised address | Member ID | Storage |
|---|---|---:|---|
| a | a:27017 | 0 | a-data and a-config named volumes |
| b | b:27017 | 1 | b-data and b-config named volumes |
| c | c:27017 | 2 | c-data and c-config named volumes |

Every mongod and the teaching client use the same network. A seed address only starts discovery; the client must reach all advertised addresses it may select.

Publishing a host port would not make a, b and c resolvable from Windows/host clients. This chapter avoids that mismatch by running mongosh through docker compose exec. Do not “fix” external discovery by casually changing replica-set configuration.

Each member owns its own data directory. Never mount the same /data/db volume into multiple running mongod processes.

## 3. Prerequisites and resource budget

Complete Chapters 05, 24 and 25. Run Docker locally on a disposable training machine. On Windows, use Docker Desktop's Linux containers and Compose v2. The Compose and mongosh commands below work from PowerShell; the file content is YAML, not a PowerShell script.

The project uses three 1 GiB container memory limits and 0.25 GiB WiredTiger caches. Allow additional memory for Docker, host OS and tools. These small teaching settings are not a production sizing recommendation.

Record:

```bash
docker version
docker compose version
docker info
```

Do not share raw docker info output if it contains internal environment details. Record relevant versions, architecture and resource limits.

Before starting, check for an existing project:

```bash
docker compose -p mongodb-ch26 ls
docker ps -a --filter label=com.docker.compose.project=mongodb-ch26
docker volume ls --filter label=com.docker.compose.project=mongodb-ch26
```

If prior chapter-26 resources exist, inspect their ownership/data first. Either continue that known lab or clean it up deliberately. Do not overwrite a set someone is using.

## 4. Save the complete Compose definition

Create a local working folder and save this as compose.yaml. Use the same folder for all following Compose commands.

```yaml
name: mongodb-ch26

x-member: &member
  image: mongo:8.0
  command:
    - mongod
    - --replSet
    - rs26
    - --bind_ip_all
    - --wiredTigerCacheSizeGB
    - "0.25"
    - --oplogSize
    - "128"
  mem_limit: 1g
  networks:
    - replica
  healthcheck:
    test:
      - CMD
      - mongosh
      - --quiet
      - --host
      - localhost
      - --eval
      - "quit(db.adminCommand({ping:1}).ok === 1 ? 0 : 1)"
    interval: 5s
    timeout: 5s
    retries: 20
    start_period: 10s

services:
  a:
    <<: *member
    volumes:
      - a-data:/data/db
      - a-config:/data/configdb
  b:
    <<: *member
    volumes:
      - b-data:/data/db
      - b-config:/data/configdb
  c:
    <<: *member
    volumes:
      - c-data:/data/db
      - c-config:/data/configdb

networks:
  replica:
    internal: true

volumes:
  a-data:
  a-config:
  b-data:
  b-config:
  c-data:
  c-config:
```

The ping healthcheck tests process connectivity, not primary election or replication readiness. Application readiness is checked separately below.

The image tag selects the 8.0 family and can resolve to a newer patch later. For repeatable evidence, capture the resolved digest and replace the tag with the approved exact tag/digest on future runs. All members must use the same chosen build for this initial lab.

The explicit config volumes avoid leaving image-declared anonymous volumes behind. Named volumes persist across ordinary down/up. The cleanup section removes only this project's owned volumes.

## 5. Validate and start the processes

```bash
docker compose -p mongodb-ch26 config
docker compose -p mongodb-ch26 pull
docker compose -p mongodb-ch26 up -d --wait --wait-timeout 120
docker compose -p mongodb-ch26 ps
docker image inspect mongo:8.0 --format '{{json .RepoDigests}}'
docker compose -p mongodb-ch26 exec a mongosh --version
```

Expected: three running/healthy services. --wait waits for the healthchecks, not replica-set readiness. If startup fails, inspect bounded logs:

```bash
docker compose -p mongodb-ch26 logs --tail 100 a b c
```

Stop and diagnose OOM, port binding, filesystem permissions or image incompatibility before initializing. Do not add restart loops to hide a crashing member.

## 6. Initialize once from one member

Open a direct connection inside member a:

```bash
docker compose -p mongodb-ch26 exec a mongosh "mongodb://localhost:27017/?directConnection=true"
```

The following JavaScript runs in that mongosh session:

```javascript
const hello26 = db.adminCommand({ hello: 1 });
if (hello26.setName) {
  throw new Error("This member already has a set configuration; inspect it, do not initiate again");
}
const initiated26 = rs.initiate({
  _id: "rs26",
  members: [
    { _id: 0, host: "a:27017", votes: 1, priority: 1 },
    { _id: 1, host: "b:27017", votes: 1, priority: 1 },
    { _id: 2, host: "c:27017", votes: 1, priority: 1 }
  ]
});
if (initiated26.ok !== 1) throw new Error("Replica-set initiation failed");
```

Run initiation only on this newly created a member. Do not run it separately on b and c. A startup --replSet name may be visible before initialization on some versions; if the guard stops, inspect replSetGetConfig to distinguish actual configuration from startup metadata rather than deleting volumes.

Wait for one primary and two healthy secondaries:

```javascript
const readinessDeadline26 = Date.now() + 90000;
let readiness26 = null;
while (Date.now() < readinessDeadline26) {
  const observed = db.adminCommand({ replSetGetStatus: 1 });
  const members = observed.members || [];
  if (observed.ok === 1 && members.length === 3 &&
      members.filter(m => m.stateStr === "PRIMARY" && m.health === 1).length === 1 &&
      members.filter(m => m.stateStr === "SECONDARY" && m.health === 1).length === 2) {
    readiness26 = observed;
    break;
  }
  sleep(1000);
}
if (!readiness26) throw new Error("Topology did not become ready within 90 seconds");
printjson(readiness26.members.map(m => ({
  id: m._id, name: m.name, state: m.stateStr, health: m.health
})));
```

Do not assume a is primary. Equal priorities leave election choice to the protocol. The direct connection remains tied to a regardless of its role.

Exit mongosh before the next connection:

```javascript
quit();
```

## 7. Verify replica-set-aware discovery

Open a seeded replica-set connection inside the same project network:

```bash
docker compose -p mongodb-ch26 exec a mongosh "mongodb://a:27017,b:27017,c:27017/?replicaSet=rs26&readPreference=primary&serverSelectionTimeoutMS=10000"
```

In this new shell:

```javascript
function check26(condition, message) {
  if (!condition) throw new Error(message);
}
const discovered26 = db.adminCommand({ hello: 1 });
check26(discovered26.setName === "rs26", "Wrong discovered set");
check26(discovered26.isWritablePrimary, "Client did not select primary");
check26(discovered26.hosts.length === 3, "Discovery did not expose three members");
printjson({
  version: db.version(), primary: discovered26.primary,
  selectedMember: discovered26.me, hosts: discovered26.hosts
});
const config26 = db.adminCommand({ replSetGetConfig: 1 }).config;
check26(config26.members.length === 3, "Wrong configured member count");
check26(config26.members.every(m =>
  m.arbiterOnly !== true &&
  (m.votes === undefined || Number(m.votes) === 1)),
  "Expected three voting data-bearing members");
printjson(config26);
```

A directConnection URI and a replicaSet URI serve different purposes. The first lets an operator inspect one chosen member; the second lets a driver discover/select members under the read policy.

## 8. Write and reconcile a majority-acknowledged fixture

Use a unique named database for this chapter. If it already contains data, inspect rather than replacing it.

```javascript
const labName26 = "mongodb_enterprise_tutorial_ch26";
const lab26 = db.getSiblingDB(labName26);
check26(lab26.getCollectionNames().length === 0,
        "Chapter database exists; review before rerunning fixture");
lab26.createCollection("events");
const events26 = lab26.events;
const concern26 = { w: "majority", j: true, wtimeout: 10000 };
const inserted26 = events26.insertMany([
  { _id: "event-0", seq: 0, revision: 0, payload: "Synthetic replica fixture" },
  { _id: "event-1", seq: 1, revision: 0, payload: "Synthetic replica fixture" },
  { _id: "event-2", seq: 2, revision: 0, payload: "Synthetic replica fixture" }
], { writeConcern: concern26 });
check26(inserted26.acknowledged, "Insert acknowledgement missing");
const updated26 = events26.updateOne(
  { _id: "event-0", revision: 0 }, { $set: { revision: 1 } },
  { writeConcern: concern26 }
);
check26(updated26.modifiedCount === 1, "Fixture update failed");
const deleted26 = events26.deleteOne(
  { _id: "event-2" }, { writeConcern: concern26 }
);
check26(deleted26.deletedCount === 1, "Fixture delete failed");
function validFixture26(rows) {
  return rows.length === 2 &&
    rows[0]._id === "event-0" && Number(rows[0].revision) === 1 &&
    rows[1]._id === "event-1" && Number(rows[1].revision) === 0;
}
const primaryRows26 = events26.find().sort({ seq: 1 }).toArray();
check26(validFixture26(primaryRows26), "Primary fixture mismatch");
printjson(primaryRows26);
```

Majority acknowledgement on three voting data members does not prove all three are current at every instant. Check each member explicitly next.

If an acknowledgement times out, retain operation identity and reconcile state before retrying. A timeout does not prove absence. Do not rerun the whole fixture creation on uncertain outcomes.

## 9. Verify each member through direct inspection

Run this from the primary shell, using separate direct Mongo connections. Every connection originates inside the project network.

```javascript
const memberEvidence26 = [];
for (const host of ["a", "b", "c"]) {
  const memberConnection = new Mongo(
    "mongodb://" + host + ":27017/?directConnection=true&serverSelectionTimeoutMS=5000"
  );
  memberConnection.setReadPref("secondaryPreferred");
  const memberAdmin = memberConnection.getDB("admin");
  const memberHello = memberAdmin.runCommand({ hello: 1 });
  check26(memberHello.setName === "rs26", "Member identity mismatch: " + host);
  const memberEvents = memberConnection.getDB(labName26).events;
  const deadline = Date.now() + 30000;
  let rows = [];
  while (Date.now() < deadline) {
    rows = memberEvents.find().sort({ seq: 1 }).toArray();
    if (validFixture26(rows)) break;
    sleep(500);
  }
  check26(validFixture26(rows), "Member fixture did not converge: " + host);
  memberEvidence26.push({
    host, primary: memberHello.isWritablePrimary,
    secondary: memberHello.secondary === true,
    rows: rows.map(r => ({ id: r._id, revision: r.revision }))
  });
}
printjson(memberEvidence26);
check26(memberEvidence26.filter(m => m.primary).length === 1,
        "Expected one observed primary");
check26(memberEvidence26.filter(m => m.secondary).length === 2,
        "Expected two observed secondaries");
```

The direct checks are bounded convergence observations. If roles change during sampling, recollect identity/status rather than interpreting inconsistent samples as a stable topology. No election is intentionally triggered here.

This verifies the small fixture on each member, not full database checksums or long-term lag acceptance. Close the shell after preserving evidence if proceeding to the failure exercise.

## 10. Failure exercise: wrong replica-set name

From the host terminal, use the same reachable seeds but the wrong expected set name:

```bash
docker compose -p mongodb-ch26 exec a mongosh "mongodb://a:27017,b:27017,c:27017/?replicaSet=wrong-rs26&serverSelectionTimeoutMS=2000" --quiet --eval "db.adminCommand({ping:1})"
```

Expected: connection/server-selection failure and nonzero exit. If it succeeds, inspect the URI/options before treating the exercise as valid.

Diagnosis: reachable mongod processes advertise rs26, while the client requested another set. The remedy is correcting the client configuration, not renaming the existing replica set.

```bash
docker compose -p mongodb-ch26 exec a mongosh "mongodb://a:27017,b:27017,c:27017/?replicaSet=rs26&serverSelectionTimeoutMS=10000" --quiet --eval "printjson(db.adminCommand({hello:1}))"
```

Expected: setName rs26 and a writable primary selected. Capture wrong/correct outcomes without introducing topology changes.

A real server-selection timeout can also come from DNS, network, TLS/auth, missing primary or inaccessible advertised addresses. A seed ping alone does not distinguish these cases.

## 11. Persistence check without a failure simulation

Named volumes preserve configuration and data across ordinary container replacement. This chapter records that design but does not stop/recreate all members to demonstrate an outage. Planned restarts and unplanned failover need the controlled procedures in later chapters.

Inspect owned resources:

```bash
docker compose -p mongodb-ch26 ps
docker volume ls --filter label=com.docker.compose.project=mongodb-ch26
docker network ls --filter label=com.docker.compose.project=mongodb-ch26
```

Keep the project and volumes if using it for Chapters 27–32. Record the image digest, configuration and fixture state so later exercises have a known starting point.

## 12. Troubleshooting

| Symptom | Evidence | Likely cause | Action |
|---|---|---|---|
| Containers healthy but no primary | Ping healthcheck versus rs status/config | Set not initiated or election/network issue | Inspect readiness separately |
| Init says already configured | replSetGetConfig, volume ownership | Reused persistent data | Continue known lab or deliberately reset owned resources |
| Discovery times out | Advertised hosts, DNS, setName | Client cannot resolve/reach members or wrong name | Correct connection environment/configuration |
| Member repeatedly restarts | Bounded logs, Docker state, memory events | OOM, permission or image issue | Fix process/resource cause before init |
| One secondary remains STARTUP/RECOVERING | Status and logs | Initial synchronization or connectivity problem | Observe/diagnose; do not force reconfig |
| Majority write fails | Health, role, concern error | Insufficient acknowledgers or timeout | Reconcile write identity and restore health |
| Secondary read rejected | Direct connection read preference | Primary-only default on secondary | Use deliberate secondary read policy |
| Host client cannot resolve a/b/c | URI and host DNS | Internal Docker discovery names | Run client inside project network or design external topology separately |

Do not use force reconfiguration as a generic solution to a teaching setup error. Preserve logs and configuration before deciding to reset an owned disposable project.

## 13. Production differences

Production deployment needs authentication between members, client authentication, TLS/certificates, routable stable DNS, firewall rules, independent failure domains, durable storage and reviewed backup/restore procedures.

Member resources must support steady traffic and recovery overlap. A single-host three-member lab multiplies local CPU/memory/storage demand without adding host resilience. Do not convert its container memory/cache settings into a production standard.

Use drivers that support replica-set discovery and retry semantics. Application timeouts, pools and write/read concerns should match the business contract. The next chapter isolates those concerns before failover experiments.

Operations such as adding members, replacing disks or changing votes require controlled configuration and recovery plans. This chapter initializes one owned empty topology; it does not authorize changing shared sets.

## 14. Cleanup or retain for the next labs

If retaining the project, leave the set running and document its state. Do not run the destructive volume cleanup below.

If finishing this disposable lab, capture evidence and connect to the primary-aware URI to drop only the chapter database:

```javascript
const cleanupLab26 = db.getSiblingDB("mongodb_enterprise_tutorial_ch26");
if (cleanupLab26.getName() !== "mongodb_enterprise_tutorial_ch26") {
  throw new Error("Refusing cleanup outside the Chapter 26 training database");
}
const dropResult26 = cleanupLab26.dropDatabase();
if (dropResult26.ok !== 1) throw new Error("Chapter 26 database cleanup failed");
if (cleanupLab26.getCollectionNames().length !== 0) {
  throw new Error("Chapter database cleanup incomplete");
}
```

Exit mongosh. From the same Compose folder:

```bash
docker compose -p mongodb-ch26 down --volumes
docker ps -a --filter label=com.docker.compose.project=mongodb-ch26
docker volume ls --filter label=com.docker.compose.project=mongodb-ch26
docker network ls --filter label=com.docker.compose.project=mongodb-ch26
```

down --volumes deletes this project's six named volumes, including replica-set configuration and all stored data. Use it only for this owned disposable project. It does not remove the image.

Expected: no chapter-project containers, volumes or network remain. Do not use docker system prune or delete unrelated volumes for chapter cleanup.

## 15. Acceptance and evidence

- [ ] Recorded Docker/Compose/server/shell versions and resolved image digest.
- [ ] Validated Compose and separate member storage with no host-published ports.
- [ ] Initiated the empty set once with three DNS member addresses.
- [ ] Observed one healthy primary and two healthy secondaries.
- [ ] Connected through a replica-set-aware URI and verified discovery.
- [ ] Verified majority-acknowledged insert/update/delete results.
- [ ] Confirmed final fixture on all three direct member connections.
- [ ] Reproduced wrong-set-name selection failure and corrected the URI.
- [ ] Recorded single-host/security limits without claiming production HA.
- [ ] Retained documented resources for later labs or completed scoped deletion.

**Evidence:** Compose file/config output, image digest/version inventory, readiness/config/status, discovery hello, application assertions, per-member results, wrong/correct URI outcomes and retention/cleanup decision. Runtime validation remains pending until this lab runs successfully.

## 16. Review questions

1. Why does a ping healthcheck not prove replication readiness?
2. Why must every client reach advertised member names after connecting to one seed?
3. Why must members have separate data volumes?
4. Why is a direct connection different from a replica-set-aware URI?
5. Why does majority acknowledgement not prove all three members applied the write?
6. What failure domain remains shared in this lab?
7. What does down --volumes destroy compared with ordinary down?
8. Which security/recovery requirements are needed before a production deployment?

## 17. Official references

- [MongoDB 8.0: deploy a replica set for testing](https://www.mongodb.com/docs/v8.0/tutorial/deploy-replica-set-for-testing/)
- [MongoDB 8.0: initiate a replica set](https://www.mongodb.com/docs/v8.0/reference/method/rs.initiate/)
- [MongoDB 8.0: replica-set configuration](https://www.mongodb.com/docs/v8.0/reference/replica-configuration/)
- [MongoDB 8.0: deploy with keyfile authentication](https://www.mongodb.com/docs/v8.0/tutorial/deploy-replica-set-with-keyfile-access-control/)
- [MongoDB 8.0: connection strings](https://www.mongodb.com/docs/v8.0/reference/connection-string/)

---

Previous: [Chapter 25 — Replica Set Architecture and Oplog](25-replica-set-architecture-and-oplog.md)  
Next: [Chapter 27 — Read Preference Read Concern and Write Concern](27-read-preference-read-concern-and-write-concern.md).
