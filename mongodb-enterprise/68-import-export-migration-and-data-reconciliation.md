# 68 — Import Export Migration and Data Reconciliation

Part 9 — Specialized Data and Observability

**Audience:** Data Engineers, DBREs, SREs and Developers.  
**Goal:** Transfer a frozen synthetic collection, verify BSON types and metadata, detect equal-count corruption, and define a reversible application cutover.  
**Baseline:** Retained authenticated TLS MongoDB 8.0 / FCV 8.0 replica set; reviewed compatible Database Tools 100.x, mongosh, Python 3.11+ and pinned PyMongo 4.x. Record exact patch/tool versions; core exercises are Community-compatible.  
**Status:** Written; static command/script review and local digest checks complete; live migration acceptance pending.  
**Prerequisites:** Chapters 11, 17–20, 41–42, 49–56, 63–64 and 67; accepted lab deployment and ownership record.  
**Estimated time:** 90–120 minutes.

## 1. Define success before transferring data

A migration is complete when the intended data, types, collection options, indexes and application behavior are accepted at a declared consistency boundary. A successful tool exit or equal document count is insufficient.

The lab uses three databases on the retained cluster:

- `mongodb_enterprise_ch68_source`: frozen authoritative fixture.
- `mongodb_enterprise_ch68_json`: JSON import destination with deliberately recreated metadata.
- `mongodb_enterprise_ch68_bson`: BSON restore destination with restored collection metadata.

Using one cluster isolates data-transfer semantics. It does not validate a separate target deployment, cross-region connectivity, throughput or production cutover. Production requires those checks on the actual source and destination.

Acceptance includes three transferred documents, BSON type checks, unique index and validator checks, full canonical document digests, a same-count corruption drill, repair, source retention and scoped cleanup.

## 2. Select the transfer method

| Method | Intended purpose | Important boundary |
|---|---|---|
| mongoexport / mongoimport | Structured JSON or CSV exchange | Export is not a complete deployment backup; metadata needs separate handling |
| mongodump / mongorestore | Logical BSON data and metadata transfer | Review server/tool compatibility and consistency boundary |
| Supported snapshot/managed migration | Larger or lower-downtime movement | Prove supported deployment, storage, capture and recovery behavior |
| Application batch/CDC | Selective or transformed migration | Own schema, identities, deletes, ordering and checkpoint semantics |

Use canonical Extended JSON for the lab's structured transfer. CSV is useful for flat interchange but does not automatically preserve nested structures or BSON types. JSON transfer also does not recreate all source collection options and indexes.[1][2]

A BSON restore can carry collection metadata, but that is not the whole deployment configuration. Roles, application secrets, network controls, sharding placement and external dependencies need a separate inventory.[3][4] Chapter 50 covers logical recovery; Chapters 51–56 cover broader recovery architectures.

## 3. Freeze and consistency boundary

For this lab, create the fixture once and stop all writers to its source collection until reconciliation finishes. Use primary routing and acknowledged writes. There is no active TTL, capped rollover, collection rename or background application mutation in the fixture.

A primary read or majority read does not make an arbitrary moving export a point-in-time snapshot. For production choose one documented approach:

- Offline/frozen migration with measured outage and writer fencing.
- Supported consistent backup plus capture/replay to an explicit boundary.
- Supported live migration service with verified convergence and cutover criteria.
- Application-owned migration with demonstrated baseline/change overlap and deletion handling.

Do not append `--oplog` to a collection-filtered dump and assume it establishes a supported protocol. Replica-set oplog dump/replay has specific scope and restore restrictions; sharded consistency needs its own plan.[3][4] The optional BSON lab below deliberately uses a stopped collection without oplog replay.

## 4. Credentials, inventory and local workspace

Use Chapter 42's verified TLS/SCRAM connection. The source reader needs scoped read/list metadata permissions. Target transfer identities need the reviewed creation, insertion, index and restore permissions. Cleanup belongs to the lab administrator. Use separate production roles and approved service accounts.

From Bash, set a credential-free URI and CA path for the retained lab. Substitute recorded hosts and replica set name. Database Tools use `--ssl` / `--sslCAFile`; do not copy mongosh's flag spelling indiscriminately.

```bash
export CH68_URI='mongodb://db1:27017,db2:27017,db3:27017/?replicaSet=rs0'
export CH68_CA='/path/to/lab-ca.pem'
export CH68_USER='ch68_lab_transfer'
export CH68_DIR="$PWD/ch68-transfer"
mkdir "$CH68_DIR"
mongoexport --version
mongoimport --version
mongodump --version
mongorestore --version
mongosh --version
```

Use a fresh local directory; if it exists, inspect ownership before reusing it. Each tool command prompts for its password when a username is supplied without a password. Keep secrets out of command arguments and URIs. Secure transfer artifacts and manifests according to their sensitivity. Production files can contain full application records even when logs are sanitized.

On Windows PowerShell, set `$env:CH68_URI`, `$env:CH68_CA`, `$env:CH68_USER` and `$env:CH68_DIR`; use an absolute path for the directory. The executable options are the same, but replace Bash continuations with PowerShell backticks or use one-line commands.

Record server/FCV, editions, source and target topology, tool versions, Python/driver versions, UTC start/end times, allowed namespaces and the writer-freeze owner. Review exact installed Tools documentation before running; do not infer compatibility from server major version alone.

## 5. Lab setup — three owned namespaces and typed fixture

Run in the connected mongosh session. All namespace checks occur before the fixture is created. If any database already has collections, stop; do not drop it to bypass the guard.

```javascript
var sourceName = "mongodb_enterprise_ch68_source";
var jsonName = "mongodb_enterprise_ch68_json";
var bsonName = "mongodb_enterprise_ch68_bson";
var owner = "mongodb-enterprise-tutorial-ch68";
for (var name of [sourceName, jsonName, bsonName]) {
  if (db.getSiblingDB(name).getCollectionInfos().length !== 0) {
    throw new Error("Existing namespace: " + name);
  }
}
if (!db.hello().isWritablePrimary) throw new Error("Expected writable primary");
var src = db.getSiblingDB(sourceName);
var jsonTarget = db.getSiblingDB(jsonName);
var bsonTarget = db.getSiblingDB(bsonName);
for (var name of [sourceName, jsonName, bsonName]) {
  db.getSiblingDB(name).ownership.insertOne({ _id: owner, createdAt: new Date() });
}
var validator = { $jsonSchema: {
  bsonType: "object",
  required: ["_id", "tenant", "externalId", "amount", "createdAt"],
  properties: {
    _id: { bsonType: "objectId" }, tenant: { bsonType: "string" },
    externalId: { bsonType: "string" }, amount: { bsonType: "decimal" },
    createdAt: { bsonType: "date" }
  }
} };
function createFixtureCollection(database) {
  var result = database.createCollection("records", {
    validator: validator, validationLevel: "strict", validationAction: "error"
  });
  if (result.ok !== 1) throw new Error("Collection creation failed");
  database.records.createIndex({ tenant: 1, externalId: 1 }, {
    unique: true, name: "tenant_external_unique"
  });
}
createFixtureCollection(src);
src.records.insertMany([
  { _id: ObjectId("680000000000000000000001"), tenant: "training", externalId: "A",
    amount: NumberDecimal("10.25"), createdAt: ISODate("2026-01-01T00:00:00Z"),
    counter: NumberLong("9007199254740993"), nested: { flags: [true, false] } },
  { _id: ObjectId("680000000000000000000002"), tenant: "training", externalId: "B",
    amount: NumberDecimal("20.50"), createdAt: ISODate("2026-01-02T00:00:00Z"),
    counter: NumberLong("9007199254740994"), optional: null },
  { _id: ObjectId("680000000000000000000003"), tenant: "training", externalId: "C",
    amount: NumberDecimal("30.75"), createdAt: ISODate("2026-01-03T00:00:00Z"),
    counter: NumberLong("9007199254740995"), nested: { flags: [] } }
], { writeConcern: { w: "majority", wtimeout: 10000 } });
if (src.records.countDocuments({}) !== 3) throw new Error("Expected three source rows");
printjson(src.records.aggregate([
  { $group: { _id: "$tenant", count: { $sum: 1 }, total: { $sum: "$amount" } } }
]).toArray());
```

Expected: three documents, exact Decimal128 total `61.50`, ObjectId identities, Date timestamps and 64-bit integer counters beyond JavaScript's exact Number range. Do not cast those counters to ordinary JavaScript Number for reconciliation.

## 6. Lab A — canonical JSON export and artifact manifest

Run from the system shell, not mongosh. This exports newline-delimited canonical Extended JSON and retains the source IDs.

```bash
mongoexport --uri="$CH68_URI" --ssl --sslCAFile="$CH68_CA" \
  --username="$CH68_USER" --authenticationDatabase=admin \
  --db=mongodb_enterprise_ch68_source --collection=records \
  --readPreference=primary --jsonFormat=canonical \
  --out="$CH68_DIR/records.canonical.json"
```

Require a successful exit and an exported count of three. Stop after a tool error; do not import a partial output file. Generate a byte-integrity manifest:

```python
import hashlib
import json
import os
from pathlib import Path

root = Path(os.environ["CH68_DIR"])
path = root / "records.canonical.json"
raw = path.read_bytes()
rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
if len(rows) != 3:
    raise RuntimeError("Expected three exported documents")
manifest = {"namespace": "mongodb_enterprise_ch68_source.records",
            "format": "canonical Extended JSON, newline-delimited",
            "documents": len(rows), "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "consistency": "owned synthetic fixture; writers stopped"}
(root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(manifest)
```

Save as `ch68_manifest.py` and run `python ch68_manifest.py`. The manifest checksum verifies those exact file bytes; it does not prove a moving source was captured consistently or that the destination has matching data. Verify the checksum again after transport and before import.

## 7. Lab B — recreate metadata and import JSON

Back in the same mongosh setup session, create the destination collection with the explicit source contract:

```javascript
createFixtureCollection(jsonTarget);
if (jsonTarget.records.countDocuments({}) !== 0) throw new Error("Expected empty JSON target");
```

Then import through the shell:

```bash
mongoimport --uri="$CH68_URI" --ssl --sslCAFile="$CH68_CA" \
  --username="$CH68_USER" --authenticationDatabase=admin \
  --db=mongodb_enterprise_ch68_json --collection=records \
  --type=json --mode=insert --stopOnError \
  --file="$CH68_DIR/records.canonical.json"
```

Expected: three imported documents, no failures. Do not add `--drop` or bypass validation. `--stopOnError` stops on an error but does not turn the whole import into an all-or-nothing transaction. Inspect partial state after failure.

Reimporting with insert mode can hit duplicate `_id` errors. Upsert mode can support an intentional repair by identity, but its replacement semantics must match the desired-state contract.[2] An import does not automatically delete destination-only documents.

## 8. Lab C — BSON archive transfer with metadata

This branch uses the same frozen source but a separate fresh destination. Do not confuse the JSON and BSON outputs or restore into the source namespace.

```bash
mongodump --uri="$CH68_URI" --ssl --sslCAFile="$CH68_CA" \
  --username="$CH68_USER" --authenticationDatabase=admin \
  --db=mongodb_enterprise_ch68_source --collection=records \
  --archive="$CH68_DIR/records.archive.gz" --gzip
```

Require successful completion, then restore only the included namespace under the new database name:

```bash
mongorestore --uri="$CH68_URI" --ssl --sslCAFile="$CH68_CA" \
  --username="$CH68_USER" --authenticationDatabase=admin \
  --archive="$CH68_DIR/records.archive.gz" --gzip --stopOnError \
  --nsInclude='mongodb_enterprise_ch68_source.records' \
  --nsFrom='mongodb_enterprise_ch68_source.records' \
  --nsTo='mongodb_enterprise_ch68_bson.records'
```

Expected: three restored documents and source collection metadata/index definitions. Verify these explicitly rather than assuming they were applied. The ownership collection is not included in the archive; its independently created marker remains intact. Collection UUID equality is not an acceptance requirement for this new namespace.

If restore fails on incompatible metadata/index options, stop and record the exact error. Review the source/target versions and supported options before retrying into a fresh owned target. A filtered logical archive does not preserve deployment-wide recovery state.

## 9. Reconcile data, types and metadata

Install an exact reviewed PyMongo version in an isolated environment. Save this complete verifier as `ch68_verify.py`. It checks both destinations by default or a named owned destination on the command line. The URI, CA and username use the shell variables from Section 4; the password is prompted.

```python
import getpass
import hashlib
import os
import sys

from bson import json_util
from pymongo import MongoClient
from pymongo.read_concern import ReadConcern

SOURCE = "mongodb_enterprise_ch68_source"
TARGETS = {"mongodb_enterprise_ch68_json", "mongodb_enterprise_ch68_bson"}
OWNER = "mongodb-enterprise-tutorial-ch68"


def canonical(document):
    # Object-key order is ignored; array order and canonical BSON types are retained.
    return json_util.dumps(document, json_options=json_util.CANONICAL_JSON_OPTIONS,
                           sort_keys=True, separators=(",", ":"))


def snapshot(collection):
    # Bounded three-row fixture only; production needs streaming partition manifests.
    rows = list(collection.find().sort("_id", 1))
    encoded = [canonical(row) for row in rows]
    digest = hashlib.sha256("\n".join(encoded).encode("utf-8")).hexdigest()
    identities = {canonical(row["_id"]): canonical(row) for row in rows}
    return len(rows), digest, identities


def indexes(collection):
    # Compare ordered key patterns and options; omit server-local index version metadata.
    return {index["name"]: {
        "key": list(index["key"].items()),
        "options": {k: v for k, v in index.items() if k not in {"key", "name", "v", "ns"}}
    } for index in collection.list_indexes()}


selected = sys.argv[1:] or sorted(TARGETS)
if not selected or any(name not in TARGETS for name in selected):
    raise RuntimeError("Choose only named chapter-owned targets")
client = MongoClient(
    os.environ["CH68_URI"], username=os.environ["CH68_USER"],
    password=getpass.getpass("MongoDB verification password: "), authSource="admin",
    tls=True, tlsCAFile=os.environ["CH68_CA"],
    serverSelectionTimeoutMS=10000, socketTimeoutMS=30000,
)
try:
    source = client.get_database(SOURCE, read_concern=ReadConcern("majority"))
    if source.ownership.find_one({"_id": OWNER}) is None:
        raise RuntimeError("Source ownership missing")
    source_state = snapshot(source.records)
    if source_state[0] != 3:
        raise RuntimeError("Frozen source fixture changed")
    source_options = source.records.options()
    failed = False
    for name in selected:
        target = client.get_database(name, read_concern=ReadConcern("majority"))
        if target.ownership.find_one({"_id": OWNER}) is None:
            raise RuntimeError("Target ownership missing")
        target_state = snapshot(target.records)
        missing = sorted(set(source_state[2]) - set(target_state[2]))
        extra = sorted(set(target_state[2]) - set(source_state[2]))
        changed = sorted(key for key in set(source_state[2]) & set(target_state[2])
                         if source_state[2][key] != target_state[2][key])
        data_ok = source_state[:2] == target_state[:2]
        options_ok = source_options == target.records.options()
        indexes_ok = indexes(source.records) == indexes(target.records)
        print({"target": name, "source_count": source_state[0],
               "target_count": target_state[0], "source_sha256": source_state[1],
               "target_sha256": target_state[1], "missing_ids": missing,
               "extra_ids": extra, "changed_ids": changed,
               "data_ok": data_ok, "options_ok": options_ok, "indexes_ok": indexes_ok})
        failed = failed or not (data_ok and options_ok and indexes_ok)
    if failed:
        raise RuntimeError("Reconciliation failed: publication blocked")
finally:
    client.close()
print("PASS: complete fixture data and metadata reconciled")
```

Run `python ch68_verify.py`. Expected: both targets have three rows, matching full digests, no missing/extra/changed IDs, and matching options/index contracts. The canonical representation makes Int64 and Decimal128 differences visible; the test is not just a comparison of display strings.

For production, document the normalization contract before hashing. Field-order significance, mixed ID types, numeric types and array ordering affect equality. Hashes are summaries; retain partition/identity-level diagnostics so a mismatch can be located.

## 10. Failure exercise — equal counts, unequal values

Corrupt one amount in the owned JSON target. This is still a valid Decimal128 and does not change its count, so a count-only migration check would miss it.

```javascript
var target = db.getSiblingDB("mongodb_enterprise_ch68_json");
var result = target.records.updateOne(
  { _id: ObjectId("680000000000000000000002") },
  { $set: { amount: NumberDecimal("999.00") } }
);
if (result.modifiedCount !== 1) throw new Error("Failure fixture did not change one row");
if (target.records.countDocuments({}) !== 3) throw new Error("Count unexpectedly changed");
```

Run `python ch68_verify.py mongodb_enterprise_ch68_json`. Expected: three rows on both sides, different digests, changed identity B, nonzero verifier exit and publication blocked. Record this expected failure; do not label the migration accepted yet.

Repair by reimporting the frozen desired-state file under `_id` upsert semantics:

```bash
mongoimport --uri="$CH68_URI" --ssl --sslCAFile="$CH68_CA" \
  --username="$CH68_USER" --authenticationDatabase=admin \
  --db=mongodb_enterprise_ch68_json --collection=records \
  --type=json --mode=upsert --upsertFields=_id --stopOnError \
  --file="$CH68_DIR/records.canonical.json"
```

Then rerun `python ch68_verify.py`. Both targets must pass. This repair replaces documents from an authoritative frozen fixture. It is unsafe as a blind production repair if the destination has valid newer writes. Fence writers or reconcile versions before using replacement imports.

Destination-only identities require a separate reviewed deletion policy. Source hard deletes during live migration require capture/tombstones or a complete closed-scope comparison; rerunning upserts does not propagate them.

## 11. Verify constraints and application behavior

Full data equality does not prove index/validator enforcement. For each owned target, try an invalid amount and a duplicate business key, then verify neither failed write changed the count.

```javascript
for (var name of ["mongodb_enterprise_ch68_json", "mongodb_enterprise_ch68_bson"]) {
  var target = db.getSiblingDB(name);
  var before = target.records.countDocuments({});
  var invalidRejected = false;
  try {
    target.records.insertOne({
      _id: ObjectId(), tenant: "training", externalId: "INVALID",
      amount: "10.25", createdAt: new Date()
    });
  } catch (error) {
    if (error.code !== 121) throw error;
    invalidRejected = true;
  }
  var duplicateRejected = false;
  try {
    target.records.insertOne({
      _id: ObjectId(), tenant: "training", externalId: "A",
      amount: NumberDecimal("1.00"), createdAt: new Date()
    });
  } catch (error) {
    if (error.code !== 11000) throw error;
    duplicateRejected = true;
  }
  if (!invalidRejected || !duplicateRejected || target.records.countDocuments({}) !== before) {
    throw new Error("Target constraint acceptance failed: " + name);
  }
  printjson({ target: name, validatorRejected: true, uniqueRejected: true });
}
```

Expected error codes: 121 for validation and 11000 for duplicate key. Rerun the verifier after these negative tests to confirm complete state remained intact.

On the actual migration target, test the application's connection identity, TLS, read/write privileges, representative predicates, update semantics, timeouts and latency. A same-cluster data-transfer fixture does not replace application acceptance on new hosts.

## 12. Production migration and cutover runbook

Use a concrete scope and owner for each phase:

| Phase | Required evidence | Stop condition |
|---|---|---|
| Inventory | Source/target versions, namespaces, schema/indexes, users, TTL, storage and app dependencies | Unsupported versions or unowned scope |
| Baseline transfer | Manifest, supported consistency protocol, transfer duration and errors | Partial output or undocumented capture boundary |
| Reconciliation | Partition counts, typed digests, duplicates, constraints and app queries | Unexplained missing/extra/changed data |
| Change convergence | Ordered replay, deletes, checkpoint and lag | Lost history or lag exceeding cutover budget |
| Writer fence | Old writer disabled, queues drained, final boundary recorded | Any unaccounted writer still active |
| Routing change | Explicit connection/config change, refreshed pools and verification | Clients still writing both deployments |
| Post-cutover | Acknowledged writes/reads, replication, resource health and new backup | Integrity failure or agreed budget breached |
| Source retirement | Recovery retention elapsed and destination recovery proven | Source still needed for accepted recovery |

For an offline migration, measure the full outage: writer fence, final transfer, index construction, reconciliation, routing and application acceptance. Do not estimate solely from file copy time. For online migration, retained source history and target catch-up speed must support the largest expected outage and replay burst.

Rollback before destination writes can route back to the retained fenced source after verification. Once the destination accepts new writes, routing back alone can lose those writes. Define reverse synchronization or controlled recovery/reconciliation before cutover; do not claim a simple DNS change is a complete rollback.

Keep the old deployment fenced and recoverable until the acceptance period and backup/restore drill finish. Define the point where rollback becomes a new migration. Record who can reopen writers and how split-brain application access is prevented.

## 13. Capacity, security and observability

Transfer throughput is bounded by source read I/O, network, target writes, indexes and replication. More workers can worsen foreground latency. Set concurrency and abort budgets from measured source/target capacity, not an arbitrary maximum.

Budget space for source/target data, archive/export files, indexes, replication and temporary staging. Index creation and failed retries can extend the maintenance window. Review TTL before restore: old timestamps can become immediately eligible for cleanup and disappear before acceptance.

Monitor source query latency, CPU/cache/I/O, network, target insertion errors, index build progress, replication lag, disk growth and tool exit status. Collect manifest count/checksum plus per-partition reconciliation. Do not place credentials or unrestricted application payloads in progress dashboards.

A transfer artifact is sensitive data. Apply encryption, access control, retention and disposal requirements. Save only necessary diagnostic identities; full document mismatch output may expose business data. The lab verifier prints only synthetic IDs and digests.

## 14. Troubleshooting

| Symptom | Evidence | Likely cause | Corrective action and verification |
|---|---|---|---|
| Tool connection fails | Exact tool version, TLS error and endpoint | Flag/version mismatch, CA/name or auth issue | Verify accepted connection without weakening TLS |
| JSON values import as strings | Canonical export and target BSON types | Plain JSON/CSV coercion | Correct encoding/mapping; rerun isolated typed reconciliation |
| Import stops halfway | Exit status, accepted count and first error | Duplicate, validation or transport failure | Reconcile partial state; choose fresh target or deliberate idempotent repair |
| Equal counts but wrong values | Typed digest and changed IDs | Transformation or stale/corrupt target | Block publication; reconcile authoritative closed scope |
| Target lacks indexes/validator | Collection options and index inventory | Metadata omitted by JSON path | Recreate reviewed contract; test enforcement |
| Restore metadata rejected | Error, source/target versions and options | Unsupported options or incompatible tools | Review supported compatibility; restore fresh isolated scope |
| Old rows disappear after restore | TTL policies and event dates | Active expiration | Restore isolated with reviewed TTL policy; reconcile before publication |
| Upsert repair leaves extra rows | Source/target identity sets | Upsert does not delete destination-only rows | Apply reviewed delete/tombstone policy |
| Destination changes after reconciliation | Writer identities and boundary timestamps | Writers not fenced | Reestablish consistency boundary and repeat checks |
| Cutover rollback loses writes | Target acknowledgements and retained source state | New writes absent on old source | Reconcile/reverse-sync before routing back |

## 15. Acceptance record and owned cleanup

| Check | Evidence |
|---|---|
| Versions and connection | Exact server/FCV, tools, shell, driver, topology and CA policy |
| Source freeze | Owned scope, stopped writer and UTC boundary |
| Artifact | Three canonical JSON lines, byte checksum and successful tool exits |
| JSON transfer | Three typed documents, recreated validator/index |
| BSON transfer | Three documents, restored metadata/index |
| Reconciliation | Matching typed digests and no missing/extra/changed IDs |
| Failure/repair | Equal counts fail after amount corruption; pass after scoped upsert repair |
| Enforcement | Expected validation and uniqueness errors; unchanged final state |
| Cleanup | Ownership checked for all three databases; absence verified |

Save nonsecret evidence before cleanup. Remove only the owned lab databases through the retained mongosh session. All ownership checks precede the first drop.

```javascript
var names = ["mongodb_enterprise_ch68_source", "mongodb_enterprise_ch68_json",
             "mongodb_enterprise_ch68_bson"];
for (var name of names) {
  if (db.getSiblingDB(name).ownership.findOne({
    _id: "mongodb-enterprise-tutorial-ch68"
  }) === null) throw new Error("Ownership missing: " + name);
}
for (var name of names) {
  if (db.getSiblingDB(name).dropDatabase().ok !== 1) throw new Error("Drop failed: " + name);
  if (db.getSiblingDB(name).getCollectionInfos().length !== 0) {
    throw new Error("Cleanup left collections: " + name);
  }
}
print("PASS: three chapter-owned databases removed");
```

Transfer artifacts remain in the exact `CH68_DIR` directory until their evidence/retention policy permits removal. Inspect its path and contents before deleting it; never issue broad cleanup against the parent workspace. Retained cluster, operator resources and other chapter data remain under their existing lifecycle.

Review questions:

1. Why is export success not a complete migration acceptance test?
2. Which information must be recreated after a JSON import?
3. Why does canonical Extended JSON matter for Int64 and Decimal128?
4. What does a file checksum prove that a document digest does not, and vice versa?
5. Why is a moving majority-read scan not automatically a consistent baseline?
6. What happens to destination-only documents during an upsert import?
7. How does rollback change after the new target accepts writes?

## 16. Official references and validation status

1. [MongoDB Database Tools — mongoexport](https://www.mongodb.com/docs/database-tools/mongoexport/).
2. [MongoDB Database Tools — mongoimport](https://www.mongodb.com/docs/database-tools/mongoimport/).
3. [MongoDB Database Tools — mongodump](https://www.mongodb.com/docs/database-tools/mongodump/).
4. [MongoDB Database Tools — mongorestore](https://www.mongodb.com/docs/database-tools/mongorestore/).
5. [PyMongo — bson.json_util](https://pymongo.readthedocs.io/en/stable/api/bson/json_util.html).

Documentation reviewed on 2026-10-11. The frozen fixture, reconciliation contract, negative tests and cutover gates are teaching designs. Python/JavaScript syntax and shell command structure were checked; local digest tests demonstrated that equal counts with changed typed values fail reconciliation. Those checks do not execute Database Tools, TLS/authentication, metadata restore, BSON round trips or a live migration. No live MongoDB/tool acceptance was performed in the authoring environment.

**Chapter completion:** Written and statically reviewed. Runtime validation remains pending until the authorized fixture transfer, reconciliation, repair and cleanup are executed and recorded.

Previous: [Chapter 67 — MongoDB to Snowflake Direct Integration](67-mongodb-to-snowflake-direct-integration.md).  
Next: Chapter 69 — Metrics Logs FTDC and Dashboard Design.
