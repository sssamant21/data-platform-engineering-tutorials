# 79 — Backup Restore and Disaster Recovery Project

Part 10 — Troubleshooting and Production Projects

**Audience:** DBREs, SREs, Platform Engineers and recovery owners.  
**Goal:** Restore an owned recovery point into an isolated namespace, reconcile data and metadata, quantify known post-backup loss, and evaluate a complete disaster-recovery acceptance packet.  
**Baseline:** Accepted retained MongoDB 8.0 / FCV 8.0 TLS/SCRAM replica set; exact recorded compatible Database Tools 100.x, mongosh and pinned reviewed PyMongo 4.x on Python 3.11+. Core logical lab is Community-compatible. Managed PITR/encryption/sharded recovery requires the accepted specialized procedures.  
**Status:** Written; syntax and offline recovery-boundary checks complete; live backup/restore and DR acceptance pending.  
**Prerequisites:** Chapters 49–56, 62, 68 and 76–78; recovery objectives, topology/key inventory, storage reserve and independent recovery access.  
**Estimated time:** 90–120 minutes for the bounded logical drill; separate full deployment recovery adds provisioning and redundancy acceptance.

## 1. Recovery contract and scope

A backup is useful only when the intended scope can be restored, validated and served within its recovery objectives. Backup-job completion and artifact checksum are necessary evidence but do not prove restored correctness.

The lab freezes a synthetic source database, captures a data/metadata manifest and logical archive, creates five later acknowledged records, then simulates an accidental deletion of ten original records. It restores the earlier point into a fresh destination and compares it to the pre-backup manifest.

This same-cluster namespace isolation proves logical recovery semantics. It does not simulate loss of the cluster/region, rebuild hosts or certify full disaster recovery. Those remain explicit project extensions using Chapters 51–56.

Acceptance requires a known consistent source boundary, intact archive, exact restored identities/types/values, restored schema/indexes, declared post-point loss, application checks and recorded RPO/RTO scope. Preserve the damaged source and original artifact until investigation and acceptance finish.

## 2. Recovery architecture decision

| Recovery method | Suitable scope | Required evidence |
|---|---|---|
| Frozen logical dump/restore | Controlled namespace/data recovery | Writer fence, BSON/metadata and exact reconciliation |
| Supported replica-set logical capture/replay | Appropriate whole-scope consistent recovery | Exact oplog restrictions, retained history and replay boundary |
| Supported filesystem/storage snapshot | Accepted consistent storage recovery | Snapshot protocol, journals/volumes, keys and startup verification |
| Ops Manager/managed PITR | Accepted supported managed backup deployment | Snapshot/oplog coverage, selected recovery time and isolated restore |
| Sharded DR | Coordinated cluster recovery | Config metadata/shards/routing and consistent recovery point |

Choose a supported exact-version protocol.[1][2][3] A collection/database-filtered archive plus an arbitrary oplog replay is not automatically a supported point-in-time recovery. This lab uses stopped writers and no active TTL/background data changes, with no oplog replay.

Encryption keys, authentication, network controls, automation/operator configuration, application routes and backup credentials are recovery dependencies. A logical data artifact is not a complete package of those dependencies. Review encrypted collections and tool support against the actual deployed features before using generic dump commands.

## 3. Fence, preserve and measure

For a real incident, establish the last known good state, incident/deletion boundary and business acknowledgement ledger. Fence affected writers through their authoritative owner before recovery publication. Preserve the source/logs/FTDC and avoid restoring over live data.

Record UTC timestamps for incident declaration, recovery start, artifact retrieval, target ready, restore completion, validation and application acceptance. RTO ends at the agreed usable service acceptance, not merely at tool exit. Include detection/provisioning/keys/routing under the declared objective scope.

The age of the selected recovery point at the incident is a conservative recovery-point-gap measure. Actual lost business operations require acknowledgement comparison; backup frequency alone cannot establish zero loss. Do not report exact RPO from a source timestamp without verifying recoverable coverage.

## 4. Owned fixture and frozen boundary

Use Chapter 42's verified TLS/SCRAM lifecycle connection to the retained primary. Run once with no other fixture writer. Source is `mongodb_enterprise_ch79_source`; target is `mongodb_enterprise_ch79_restored`.

```javascript
var sourceName = "mongodb_enterprise_ch79_source";
var targetName = "mongodb_enterprise_ch79_restored";
var source = db.getSiblingDB(sourceName);
function check(condition, message) { if (!condition) throw new Error(message); }
check(source.getCollectionInfos().length === 0, "Source namespace exists");
check(db.getSiblingDB(targetName).getCollectionInfos().length === 0, "Target namespace exists");
check(db.hello().isWritablePrimary === true, "Expected writable primary");
source.ownership.insertOne({ _id: "mongodb-enterprise-tutorial-ch79", createdAt: new Date() });
check(source.createCollection("records", {
  validator: { $jsonSchema: { bsonType: "object",
    required: ["externalId", "amount", "createdAt"], properties: {
      externalId: { bsonType: "string" }, amount: { bsonType: "decimal" },
      createdAt: { bsonType: "date" }
    } } }, validationLevel: "strict", validationAction: "error"
}).ok === 1, "Collection setup failed");
source.records.createIndex({ externalId: 1 }, { unique: true, name: "external_unique" });
var rows = [];
for (var i = 0; i < 100; i++) {
  rows.push({ _id: i, externalId: "record-" + i, amount: NumberDecimal(String(i + 1)),
              createdAt: ISODate("2026-01-01T00:00:00Z") });
}
source.records.insertMany(rows, { writeConcern: { w: "majority", wtimeout: 10000 } });
source.barrier.insertOne({ _id: "frozen-backup", expectedCount: 100,
  expectedTotal: NumberDecimal("5050"), recordedAt: new Date() }, {
  writeConcern: { w: "majority", wtimeout: 10000 }
});
check(source.records.countDocuments({}) === 100, "Frozen source count mismatch");
printjson(source.barrier.findOne({ _id: "frozen-backup" }));
```

Expected: 100 typed records and Decimal128 sum 5050. Freeze source writes until both manifest and archive complete. This fixture is not a moving database snapshot. The target remains empty until the approved restore.

## 5. Worker environment and complete manifest verifier

Create a fresh absolute local evidence directory. Set `CH79_URI` to the normal credential-free replica-set URI, `CH79_USER` to the scoped transfer/verifier identity, `CH79_CA_FILE` to the accepted CA and `CH79_DIR` to that directory. Record exact Database Tools and pinned PyMongo versions. Tools prompt for passwords when the username is supplied without one.

Save the following as `ch79_manifest.py`. `capture` stores the original typed records/options/index contract; `verify` compares the restored target to that frozen manifest, never to the now-damaged source.

```python
import getpass
import hashlib
import json
import os
import sys
from pathlib import Path

from bson import json_util
from pymongo import MongoClient
from pymongo.read_concern import ReadConcern

SOURCE = "mongodb_enterprise_ch79_source"
TARGET = "mongodb_enterprise_ch79_restored"
OWNER = "mongodb-enterprise-tutorial-ch79"
root = Path(os.environ["CH79_DIR"])
mode = sys.argv[1] if len(sys.argv) == 2 else "verify"
if mode not in {"capture", "verify"}:
    raise ValueError("Choose capture or verify")


def canonical(value):
    return json_util.dumps(value, json_options=json_util.CANONICAL_JSON_OPTIONS,
                           sort_keys=True, separators=(",", ":"))


def snapshot(database):
    records = list(database.records.find().sort("_id", 1))
    encoded = [canonical(row) for row in records]
    indexes = {index["name"]: {"key": list(index["key"].items()),
        "options": {k: v for k, v in index.items() if k not in {"name", "key", "v", "ns"}}}
        for index in database.records.list_indexes()}
    return {"count": len(records), "records": encoded,
            "sha256": hashlib.sha256("\n".join(encoded).encode()).hexdigest(),
            "options": canonical(database.records.options()), "indexes": canonical(indexes)}


client = MongoClient(os.environ["CH79_URI"], username=os.environ["CH79_USER"],
    password=getpass.getpass("MongoDB recovery verification password: "), authSource="admin",
    tls=True, tlsCAFile=os.environ["CH79_CA_FILE"], serverSelectionTimeoutMS=10000,
    socketTimeoutMS=30000)
try:
    if mode == "capture":
        path = root / "frozen-manifest.json"
        if path.exists():
            raise RuntimeError("Do not overwrite original recovery manifest")
        database = client.get_database(SOURCE, read_concern=ReadConcern("majority"))
        if database.ownership.find_one({"_id": OWNER}) is None:
            raise RuntimeError("Source ownership missing")
        manifest = snapshot(database)
        if manifest["count"] != 100:
            raise RuntimeError("Expected frozen 100-row source")
        barrier = database.barrier.find_one({"_id": "frozen-backup"})
        if barrier is None:
            raise RuntimeError("Frozen source barrier missing")
        manifest["barrier"] = canonical(barrier)
        manifest["scope"] = SOURCE
        path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print({"captured_count": manifest["count"], "sha256": manifest["sha256"]})
    else:
        manifest = json.loads((root / "frozen-manifest.json").read_text())
        database = client.get_database(TARGET, read_concern=ReadConcern("majority"))
        if database.ownership.find_one({"_id": OWNER}) is None:
            raise RuntimeError("Restored ownership missing")
        actual = snapshot(database)
        for key in ("count", "records", "sha256", "options", "indexes"):
            if actual[key] != manifest[key]:
                raise RuntimeError("Restored acceptance mismatch: " + key)
        if canonical(database.barrier.find_one({"_id": "frozen-backup"})) != manifest["barrier"]:
            raise RuntimeError("Restored barrier mismatch")
        print("PASS: original typed data, metadata, indexes and barrier reconciled")
finally:
    client.close()
```

Run `python ch79_manifest.py capture`. The bounded 100-row manifest may contain full data; protect it like the backup. Production manifests need streaming partitions and restricted diagnostics rather than loading an entire deployment into memory.

## 6. Backup archive and integrity seal

With writers still stopped, run from Bash/system shell:

```bash
mongodump --version
mongorestore --version
mongodump --uri="$CH79_URI" --ssl --sslCAFile="$CH79_CA_FILE" \
  --username="$CH79_USER" --authenticationDatabase=admin \
  --db=mongodb_enterprise_ch79_source --readPreference=primary \
  --archive="$CH79_DIR/source.archive.gz" --gzip
```

Require a successful exit and the expected scoped collections. Do not add unrelated admin/local/config namespaces. Preserve tool output and source versions with the artifact.

Seal both immutable files after completion:

```python
import hashlib
import json
import os
from pathlib import Path

root = Path(os.environ["CH79_DIR"])
seal = {}
for name in ("source.archive.gz", "frozen-manifest.json"):
    path = root / name
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    seal[name] = {"bytes": path.stat().st_size, "sha256": digest.hexdigest()}
path = root / "artifact-seal.json"
if path.exists():
    raise RuntimeError("Do not overwrite artifact seal")
path.write_text(json.dumps(seal, indent=2), encoding="utf-8")
print(seal)
```

Save as `ch79_seal.py` and run once. Recompute/compare both digests after retrieval before restore. A checksum mismatch blocks restore acceptance; retrieve another verified artifact rather than replacing the expected digest with the damaged file's value. A checksum establishes byte integrity, not semantic consistency or completeness.

## 7. Failure drill — later acknowledged writes and owned deletion

After backup/seal success, create five acknowledged later records, then simulate accidental deletion only within the owned source. Retain the damaged source for loss comparison.

```javascript
var source = db.getSiblingDB("mongodb_enterprise_ch79_source");
check(source.ownership.findOne({ _id: "mongodb-enterprise-tutorial-ch79" }) !== null,
      "Ownership missing");
var later = [];
for (var i = 100; i < 105; i++) {
  later.push({ _id: i, externalId: "record-" + i, amount: NumberDecimal(String(i + 1)),
               createdAt: new Date() });
}
source.records.insertMany(later, { writeConcern: { w: "majority", wtimeout: 10000 } });
source.incidentEvidence.insertOne({ _id: "post-backup-acks", ids: [100, 101, 102, 103, 104],
  acknowledgedAt: new Date() }, { writeConcern: { w: "majority", wtimeout: 10000 } });
var deletion = source.records.deleteMany({ _id: { $gte: 0, $lt: 10 } }, {
  writeConcern: { w: "majority", wtimeout: 10000 }
});
check(deletion.deletedCount === 10, "Owned incident delete mismatch");
check(source.records.countDocuments({}) === 95, "Damaged source count mismatch");
source.incidentEvidence.insertOne({ _id: "incident-declared", declaredAt: new Date(),
  removedIds: [0,1,2,3,4,5,6,7,8,9] });
print("Owned incident declared; preserve source and begin timed isolated recovery");
```

Expected: damaged source has 95 records. The selected frozen archive contains the ten removed original records but excludes the five later acknowledged records. Restoring that archive is not zero-loss recovery of the latest business state.

## 8. Restore isolated target

Record recovery start and verify the target still has no collections through the lifecycle connection. Confirm artifact digests, versions, destination identity and free capacity before the command.

```bash
mongorestore --uri="$CH79_URI" --ssl --sslCAFile="$CH79_CA_FILE" \
  --username="$CH79_USER" --authenticationDatabase=admin \
  --archive="$CH79_DIR/source.archive.gz" --gzip --stopOnError \
  --nsInclude='mongodb_enterprise_ch79_source.*' \
  --nsFrom='mongodb_enterprise_ch79_source.*' \
  --nsTo='mongodb_enterprise_ch79_restored.*'
```

Require successful tool exit and restored scoped metadata/indexes.[2] No `--drop`, restore into source, validation bypass or arbitrary oplog replay is used. The archived ownership/barrier records establish target fixture provenance.

If restore fails, preserve its output and partial target state. Do not rerun into that target blindly and interpret duplicate-key errors as harmless. Inspect exact scope, then use a separately owned fresh destination or reviewed cleanup/retry decision. Stop-on-error is not an all-or-nothing restore transaction.

## 9. Reconcile and test restored application behavior

Run `python ch79_manifest.py verify`. It compares the original pre-backup typed documents and metadata, not the current source. Require all checks before routing any application.

Through the lifecycle/accepted application test identity:

```javascript
var target = db.getSiblingDB("mongodb_enterprise_ch79_restored");
check(target.records.countDocuments({}) === 100, "Restored count mismatch");
check(target.records.countDocuments({ _id: { $gte: 0, $lt: 10 } }) === 10,
      "Deleted original records not recovered");
check(target.records.countDocuments({ _id: { $gte: 100, $lt: 105 } }) === 0,
      "Selected point unexpectedly includes later writes");
var sum = target.records.aggregate([{ $group: { _id: null, amount: { $sum: "$amount" } } }]).toArray();
check(sum.length === 1 && sum[0].amount.toString() === "5050", "Restored amount total mismatch");
var read = target.records.findOne({ externalId: "record-9" });
check(read && read._id === 9 && read.amount.toString() === "10", "Restored query contract failed");
var invalidRejected = false;
try { target.records.insertOne({ _id: 1000, externalId: "invalid", amount: "10", createdAt: new Date() }); }
catch (error) { if (error.code !== 121) throw error; invalidRejected = true; }
var duplicateRejected = false;
try { target.records.insertOne({ _id: 1001, externalId: "record-9", amount: NumberDecimal("10"), createdAt: new Date() }); }
catch (error) { if (error.code !== 11000) throw error; duplicateRejected = true; }
check(invalidRejected && duplicateRejected && target.records.countDocuments({}) === 100,
      "Restored constraint enforcement failed");
```

Expected: deleted originals recovered, five later writes absent, total 5050, validator/unique failures rejected without count changes. Rerun the manifest verifier after negative tests to confirm full state remains intact.

Do not copy the five later records into the target and then claim the archive recovered them. A merge from retained source/another durable ledger is a separate data-recovery step with its own provenance, conflict/version handling and acceptance record.

## 10. RPO/RTO and known loss acceptance

Record the selected recoverable boundary, incident declaration and actual service acceptance time. The lab's five excluded acknowledged records are a known loss set for publication of this earlier point. Business acceptance must explicitly permit that boundary or select a recovery method that retains/replays them.

Save this offline model as `ch79_objectives.py`. Times are seconds relative to one synthetic timeline; it does not replace actual UTC/monotonic observations.

```python
from dataclasses import dataclass, replace
from math import isfinite


@dataclass(frozen=True)
class RecoveryEvidence:
    recovery_point: float
    incident_declared: float
    service_accepted: float
    rpo_budget_seconds: float
    rto_budget_seconds: float
    known_excluded_acknowledged: int
    loss_explicitly_accepted: bool
    data_metadata_verified: bool
    dependencies_verified: bool


def evaluate(packet):
    times = (packet.recovery_point, packet.incident_declared, packet.service_accepted,
             packet.rpo_budget_seconds, packet.rto_budget_seconds)
    if not all(isfinite(value) and value >= 0 for value in times):
        raise ValueError("Invalid timeline/objective")
    if not packet.recovery_point <= packet.incident_declared <= packet.service_accepted:
        raise ValueError("Invalid recovery timeline order")
    if not isinstance(packet.known_excluded_acknowledged, int) or isinstance(packet.known_excluded_acknowledged, bool) or packet.known_excluded_acknowledged < 0:
        raise ValueError("Invalid known-loss count")
    for name in ("loss_explicitly_accepted", "data_metadata_verified", "dependencies_verified"):
        if not isinstance(getattr(packet, name), bool):
            raise ValueError("Explicit reviewed evidence required")
    gap = packet.incident_declared - packet.recovery_point
    duration = packet.service_accepted - packet.incident_declared
    reasons = []
    if gap > packet.rpo_budget_seconds: reasons.append("recovery_point_gap_exceeds_budget")
    if duration > packet.rto_budget_seconds: reasons.append("recovery_duration_exceeds_budget")
    if packet.known_excluded_acknowledged and not packet.loss_explicitly_accepted:
        reasons.append("known_loss_not_accepted")
    if not packet.data_metadata_verified: reasons.append("data_metadata_unverified")
    if not packet.dependencies_verified: reasons.append("dependencies_unverified")
    return {"decision": "accepted_for_declared_scope" if not reasons else "blocked",
            "point_gap_seconds": gap, "recovery_seconds": duration,
            "known_excluded_acknowledged": packet.known_excluded_acknowledged, "reasons": reasons}


baseline = RecoveryEvidence(0, 10, 40, 15, 45, 5, True, True, True)
assert evaluate(baseline)["decision"] == "accepted_for_declared_scope"
for name, packet in {
    "loss": replace(baseline, loss_explicitly_accepted=False),
    "rpo": replace(baseline, rpo_budget_seconds=5),
    "rto": replace(baseline, rto_budget_seconds=20),
    "metadata": replace(baseline, data_metadata_verified=False),
    "dependency": replace(baseline, dependencies_verified=False),
}.items():
    result = evaluate(packet)
    assert result["decision"] == "blocked"
    print(name, result)
assert sum(range(1,101)) == 5050 and sum(range(101,106)) == 515
assert 5050 - sum(range(1,11)) + 515 == 5510
print("PASS: objectives, known loss and fixture boundaries checked")
```

Expected: synthetic baseline accepted only under its declared objectives/loss approval; each failure case blocks. The point gap is 10 seconds and recovery duration 30 seconds. A backup timestamp without verified coverage remains an unknown recovery boundary, not a precise loss measurement.

## 11. Full disaster-recovery extension

To certify deployment disaster recovery, execute the previously accepted Chapter 54/55 architecture into a separately isolated deployment and complete these stages:

| Stage | Required evidence |
|---|---|
| Source fence | Old writers/routes disabled; no dual-primary application access |
| Provision | Supported versions, fresh owned storage, network/TLS and resource capacity |
| Dependencies | Encryption/key access, secrets, roles, certificates, operator/management and backup retrieval |
| Restore | Consistent supported source point and exact scope/metadata |
| Redundancy | Healthy target members/config servers/shards and accepted catch-up/history |
| Application | Fresh intended identity, representative reads/writes and concern correctness |
| Routing | Explicit connection/config change; client pools refreshed; old deployment remains fenced |
| Continued protection | New backup/restore acceptance, monitoring and lifecycle ownership |

Do not copy live dbPath files or restore config-server metadata independently and assume a coherent sharded cluster. Managed PITR recovery must record selected time, retained coverage and actual restored boundary from Chapter 52. Mark all extensions not run when the accepted deployment/procedure is unavailable.

Rollback before target writes can use the retained accepted source if its state/risk is appropriate. Once the target accepts new business writes, routing back alone can lose them. Define reverse synchronization or controlled reconciliation before failback; DR recovery is not a DNS-only procedure.

## 12. Troubleshooting and stop conditions

| Symptom | Evidence | Cause to test | Action and verification |
|---|---|---|---|
| Backup complete, archive corrupt | Byte seal and transport/storage history | Artifact damage | Retrieve verified artifact; keep original expected digest |
| Restore rows correct but schema wrong | Frozen options/index manifest | Metadata skipped/incompatible | Review supported versions/options; restore fresh scope and test enforcement |
| Restored count matches, values differ | Typed records/digest and IDs | Wrong point/transform or corrupt state | Block publication and reconcile original manifest |
| Later writes absent | Acknowledgement ledger and selected boundary | Expected older recovery point | Declare loss or recover from supported retained history/source separately |
| Target TTL deletes recovered rows | Active policies and old timestamps | Retention not reviewed | Restore isolated under reviewed policy; reconcile before publication |
| Tool finished inside RTO but app late | Provision/auth/routing/validation timeline | Tool duration substituted for service recovery | Measure agreed full boundary and fix dependencies |
| Encryption/auth fails after restore | Key/role/certificate dependency inventory | Data-only artifact incomplete | Recover accepted dependencies and test fresh app access |
| Partial restore errors | Exit/log and accepted rows/indexes | Incompatible metadata or duplicate target | Preserve state; use reviewed fresh target/cleanup decision |
| Sharded query wrong after recovery | Config/shard/routing consistency evidence | Incoherent recovery scope | Follow coordinated Chapter 55 recovery and reconcile |
| Failback would lose target writes | New acknowledgements and source divergence | No reverse-sync plan | Reconcile before any route reversal |

## 13. Acceptance evidence and owned cleanup

| Item | Required evidence |
|---|---|
| Frozen boundary | 100 records, barrier, stopped writers and exact scope |
| Artifact | Successful tool exit, versions and immutable file seals |
| Incident | Ten deleted originals and five later acknowledgements explicitly recorded |
| Restore | Fresh isolated namespace and successful scoped restore |
| Validation | Exact typed records/options/index/barrier plus query/constraint checks |
| Objectives | Actual selected boundary/service timeline and declared known-loss decision |
| DR extension | Full deployment/dependency/routing/redundancy stages passed/failed/not run |

Preserve the original archive/manifest and damaged source until acceptance and investigation close. After saving evidence, the lifecycle identity checks both ownership markers before cleanup:

```javascript
function check(condition, message) { if (!condition) throw new Error(message); }
var names = ["mongodb_enterprise_ch79_source", "mongodb_enterprise_ch79_restored"];
for (var name of names) {
  check(db.getSiblingDB(name).ownership.findOne({ _id: "mongodb-enterprise-tutorial-ch79" }) !== null,
        "Ownership missing: " + name);
}
check(db.getSiblingDB(names[0]).records.countDocuments({}) === 95, "Source incident state needs review");
check(db.getSiblingDB(names[1]).records.countDocuments({}) === 100, "Target acceptance needs review");
for (var name of names) {
  check(db.getSiblingDB(name).dropDatabase().ok === 1, "Owned cleanup failed: " + name);
  check(db.getSiblingDB(name).getCollectionInfos().length === 0, "Collections remain: " + name);
}
print("PASS: chapter-owned recovery namespaces removed");
```

Partial setup/restore requires separate exact-state review rather than bypassing these full-project guards. Local archive/manifest/evidence retention follows the recovery policy; inspect the exact owned directory before deletion. Retain the original cluster/volumes, keys, credentials, management and other chapter data under existing ownership.

Review questions:

1. What does archive checksum prove that restore reconciliation does not, and vice versa?
2. Why should restored data be compared with the frozen manifest instead of the damaged source?
3. Why are five later acknowledged records not recovered by this earlier archive?
4. What marks the end of an agreed RTO measurement?
5. Which dependencies are absent from a data-only backup?
6. Why does namespace isolation not certify regional disaster recovery?
7. How do target writes change the failback decision?
8. Which evidence proves metadata and application constraints survived recovery?

## 14. Official references and validation status

1. [MongoDB Database Tools — mongodump](https://www.mongodb.com/docs/database-tools/mongodump/).
2. [MongoDB Database Tools — mongorestore](https://www.mongodb.com/docs/database-tools/mongorestore/).
3. [MongoDB 8.0 — Backup Methods](https://www.mongodb.com/docs/v8.0/core/backups/).

Documentation reviewed on 2026-10-12. The frozen manifest, failure fixture, known-loss model and objective gates are teaching designs. Python/JavaScript/shell syntax and actual offline recovery-objective/fixture checks were executed. Those checks do not validate live BSON restore, metadata enforcement, actual artifact integrity, timing, key/deployment recovery or DR routing. No live backup/restore or disaster event was executed in the authoring environment.

**Chapter completion:** Written and statically reviewed; offline recovery-boundary acceptance complete. Runtime validation remains pending until authorized backup, isolated restore, reconciliation, objective review and cleanup evidence are recorded.

Previous: [Chapter 78 — HA Failover and Application Resilience Project](78-ha-failover-and-application-resilience-project.md).  
Next: Chapter 80 — Production Readiness and Final Acceptance Project.
