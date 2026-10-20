# 66 — GridFS Capped Collections and Workload Boundaries

Part 9 — Specialized Data and Observability

**Audience:** Developers, Data Engineers, DBREs and SREs.  
**Goal:** Verify large-file integrity and bounded-buffer rollover, then choose a storage model that fits the application's durability and recovery contract.  
**Baseline:** Retained authenticated TLS MongoDB 8.0 / FCV 8.0 replica set from Chapters 60–62; Python 3.11+ and a reviewed, pinned synchronous PyMongo 4.x release. Record exact versions. These features are Community-compatible; the lab does not validate Enterprise-only features.  
**Status:** Written; static syntax and synthetic fixture checks complete; live MongoDB acceptance pending.  
**Prerequisites:** Chapters 17, 24, 41–42, 49–56, 63 and 65; accepted deployment and ownership evidence.  
**Estimated time:** 60–90 minutes.

## 1. Define the workload contract

GridFS and capped collections solve different problems. GridFS stores a file as related metadata and chunk documents. A capped collection keeps a bounded, rolling set of documents. Neither feature turns MongoDB into an acknowledged message broker.

This lab uses a synthetic 17 MiB binary file and a small sequence-numbered diagnostic buffer. Acceptance requires a SHA-256 match after download, complete chunk sequencing, verified publication of a replacement file, explicit handling of a missing file, controlled upload abortion, observed rollover, detected consumer gaps and scoped cleanup.

| Requirement | Candidate | Decision boundary |
|---|---|---|
| Large binary content served through MongoDB | GridFS | Include file traffic in database capacity and backup planning |
| Small binary plus metadata in one atomic document | Ordinary BSON document | Entire encoded document must fit the BSON limit |
| Large externally served media, independent lifecycle | Object storage plus MongoDB metadata | Define object/publication consistency and recovery |
| Recent diagnostic ring with acceptable overwrite | Capped collection | Slow readers can lose history |
| Date-based cleanup and flexible indexing | Ordinary collection with TTL | Cleanup is asynchronous, not a fixed byte cap |
| Timestamped repeated measurements | Time series collection | Review Chapter 65's model and feature restrictions |
| Durable tasks, acknowledgements and replay | Reviewed queue/event-log design | Specify consumer offsets, retries and retention guarantees |

Object storage is an architectural alternative, not a claim that it is always cheaper or faster. Benchmark the actual file sizes, access patterns, network path and required recovery objectives.

## 2. GridFS structure and publication

A bucket named `assets` uses `assets.files` and `assets.chunks`. File metadata includes length, chunk size and upload time. Chunks carry the file identity and sequence number. Use the driver API to handle the storage protocol.[1][2]

A file upload spans multiple database operations. Do not treat its chunks, metadata and an application reference as one atomic transaction. GridFS does not support multi-document transactions.[1] A filename is a label, not a unique object identifier; store and retrieve immutable file IDs.

The application design in this chapter is:

1. Upload a new immutable file.
2. Download it and verify length and SHA-256.
3. Publish its ID through an ordinary application pointer document.
4. Keep the previous version until readers and recovery requirements permit deletion.

The pointer update is atomic as a single-document update; the overall workflow is not. If publication fails after upload, the new file can be unreferenced. If a client loses an acknowledgement, reconcile its retained file ID and pointer before retrying. A digest detects accidental content mismatch; authorization and a trusted digest source are separate concerns.

GridFS indexes and any application metadata indexes must be included in deployment acceptance. Avoid TTL on `assets.files`: deleting metadata alone does not implement complete file lifecycle cleanup. Retention workers should invoke the bucket delete API with an approved file ID and reconcile both collections afterward.

## 3. Capped collection boundaries

A capped collection is a rolling buffer constrained by configured byte capacity and optionally a maximum document count. Old documents are overwritten when limits are reached.[3] These limits do not reserve a fixed number of hours of history.

Use an append-only contract and stable document sizes. Concurrent writers do not provide a global insertion-order guarantee. Capped collections cannot be sharded, do not support transactional writes, and are outside Stable API V1.[3] Do not enable `apiStrict=True` and assume this lab remains supported.

A tailable cursor can wait for future writes, but it is not a durable checkpoint. A reader overtaken by rollover needs an explicit gap/recovery policy.[4] Natural order is not event-time order. The lab uses one writer and explicit sequence numbers to make the boundary observable.

## 4. Prepare the connection and recorded environment

Use a scoped lab administrator for the owned database. Required operations include collection/index creation, reads/writes, GridFS deletion and final database cleanup. Separate production uploader, downloader and lifecycle identities. GridFS authorization must account for both bucket collections and application metadata. Tenant metadata filters alone do not enforce access control.

Create an isolated virtual environment. Set `CH66_PYMONGO_VERSION` to the exact approved 4.x release from your compatibility review; do not install an unreviewed floating version.

```bash
python -m venv .venv-ch66
source .venv-ch66/bin/activate
python -m pip install "pymongo==${CH66_PYMONGO_VERSION:?set an approved exact version}"
python -m pip freeze
```

Windows PowerShell equivalents:

```powershell
py -m venv .venv-ch66
.\.venv-ch66\Scripts\Activate.ps1
if (-not $env:CH66_PYMONGO_VERSION) { throw 'Set an approved exact driver version' }
python -m pip install "pymongo==$env:CH66_PYMONGO_VERSION"
python -m pip freeze
```

Set `CH66_MONGO_URI` to the retained replica-set URI without credentials, for example `mongodb://db1:27017,db2:27017,db3:27017/?replicaSet=rs0`. Set `CH66_MONGO_USER` and `CH66_CA_FILE` through the approved local environment mechanism. The script prompts for the password. Do not disable certificate or hostname validation.

With an independently authorized observer, record server edition, patch, FCV, primary, shell version and UTC time. Use Chapter 42's mongosh connection. In that session:

```javascript
printjson({ server: db.version(), shell: version(), hello: db.hello() });
printjson(db.getSiblingDB("admin").runCommand({
  getParameter: 1, featureCompatibilityVersion: 1
}));
```

The script below requires a replica set and a fresh namespace. No failover or cluster configuration changes are needed. Retain evidence from failed stages and investigate before cleanup.

## 5. Complete lab script — setup and helpers

Save the Python blocks in Sections 5–11 consecutively as `ch66_lab.py`. The script prints nonsecret evidence and leaves its owned database for inspection. Section 13 supplies separate cleanup.

```python
import getpass
import hashlib
import io
import math
import os
import time
from datetime import datetime, timezone

import pymongo
from bson import ObjectId
from gridfs import GridFSBucket
from gridfs.errors import NoFile
from pymongo import MongoClient
from pymongo.write_concern import WriteConcern

DB_NAME = "mongodb_enterprise_ch66_specialized"
OWNER = "mongodb-enterprise-tutorial-ch66"
CHUNK_SIZE = 255 * 1024
FILE_SIZE = 17 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def fixture(size):
    # Deterministic synthetic bytes; this bounded lab allocates a 17 MiB payload.
    block = bytes(range(256)) * 4096
    return (block * math.ceil(size / len(block)))[:size]


def digest_stream(stream):
    sha = hashlib.sha256()
    size = 0
    while True:
        block = stream.read(64 * 1024)
        if not block:
            break
        sha.update(block)
        size += len(block)
    return size, sha.hexdigest()


client = MongoClient(
    os.environ["CH66_MONGO_URI"],
    username=os.environ["CH66_MONGO_USER"],
    password=getpass.getpass("MongoDB lab password: "),
    authSource="admin", tls=True,
    tlsCAFile=os.environ["CH66_CA_FILE"],
    serverSelectionTimeoutMS=10000, connectTimeoutMS=10000,
    socketTimeoutMS=30000, maxPoolSize=5,
)
client.admin.command("ping")
hello = client.admin.command("hello")
require(bool(hello.get("setName")), "Expected retained replica set")
require(hello.get("isWritablePrimary") is True, "Expected primary routing")
print({"driver": pymongo.version, "server": client.server_info()["version"],
       "replica_set": hello["setName"], "utc": datetime.now(timezone.utc).isoformat()})
lab = client.get_database(
    DB_NAME, write_concern=WriteConcern(w="majority", wtimeout=10000)
)
require(not lab.list_collection_names(), "Namespace exists: stop and investigate")
lab.ownership.insert_one({"_id": OWNER, "createdAt": datetime.now(timezone.utc)})
bucket = GridFSBucket(lab, bucket_name="assets", chunk_size_bytes=CHUNK_SIZE)
files = lab["assets.files"]
chunks = lab["assets.chunks"]
```

A socket timeout is not a total transfer deadline: a file comprises multiple operations. Production upload/download paths need an application deadline, bounded streaming and concurrency control. This fixture allocates memory deliberately; production handlers should stream from and to bounded file-like sources.

## 6. Lab A — upload, reconstruct and verify

```python
payload = fixture(FILE_SIZE)
expected_sha = hashlib.sha256(payload).hexdigest()
file_id = bucket.upload_from_stream(
    "synthetic.bin", io.BytesIO(payload),
    metadata={"owner": OWNER, "sha256": expected_sha, "revision": 1},
)
meta = files.find_one({"_id": file_id})
require(meta is not None and meta["length"] == FILE_SIZE, "File length mismatch")
expected_chunks = math.ceil(FILE_SIZE / CHUNK_SIZE)
chunk_rows = list(chunks.find({"files_id": file_id}, {"n": 1}).sort("n", 1))
require(len(chunk_rows) == expected_chunks, "Chunk count mismatch")
require([row["n"] for row in chunk_rows] == list(range(expected_chunks)),
        "Chunk sequence is incomplete")
with bucket.open_download_stream(file_id) as download:
    actual_size, actual_sha = digest_stream(download)
require((actual_size, actual_sha) == (FILE_SIZE, expected_sha),
        "Round-trip integrity failed")
print({"stage": "round_trip", "file_id": str(file_id), "bytes": actual_size,
       "chunks": expected_chunks, "sha256": actual_sha})
print({"files_indexes": list(files.list_indexes()),
       "chunks_indexes": list(chunks.list_indexes())})
require(any(list(index["key"].items()) == [("files_id", 1), ("n", 1)]
            and index.get("unique") is True for index in chunks.list_indexes()),
        "Required unique chunk index absent")
```

Expected: `17825792` bytes, `69` chunks, and identical SHA-256 digests. Capture the actual index inventory; do not drop driver-required indexes during tuning. File download verifies more than a metadata row or successful upload response.

## 7. Lab B — replacement publication and reader overlap

Upload a small second revision with the same filename, verify it and publish by ID. This demonstrates why name-based lookup is an insufficient identity contract.

```python
lab.asset_pointer.insert_one({"_id": "training-asset", "file_id": file_id, "revision": 1})
revision2 = b"chapter-66 verified revision two\n"
sha2 = hashlib.sha256(revision2).hexdigest()
file_id2 = bucket.upload_from_stream(
    "synthetic.bin", io.BytesIO(revision2),
    metadata={"owner": OWNER, "sha256": sha2, "revision": 2},
)
with bucket.open_download_stream(file_id2) as download:
    require(digest_stream(download) == (len(revision2), sha2), "Revision 2 invalid")
require(files.count_documents({"filename": "synthetic.bin"}) == 2,
        "Expected two versions sharing one filename")
result = lab.asset_pointer.update_one(
    {"_id": "training-asset", "file_id": file_id, "revision": 1},
    {"$set": {"file_id": file_id2, "revision": 2}},
)
require(result.modified_count == 1, "Publication lost compare-and-set race")
pointer = lab.asset_pointer.find_one({"_id": "training-asset"})
require(pointer["file_id"] == file_id2, "Published ID mismatch")
with bucket.open_download_stream(pointer["file_id"]) as download:
    require(digest_stream(download) == (len(revision2), sha2), "Published content invalid")
require(files.count_documents({"_id": file_id}) == 1,
        "Previous version must remain for overlapping readers")
print({"stage": "publication", "revision": pointer["revision"],
       "current_id": str(file_id2), "previous_retained": True})
```

If the compare-and-set fails, inspect the pointer and resolve publication ownership. Do not blindly overwrite a newer version. In production, retain the previous file until an agreed grace period or reader reference policy is satisfied. A long-running reader may still need its chunks.

## 8. Lab C — missing file and aborted upload

First request a fresh, nonexistent ID and verify the expected failure. Then explicitly abort a partially written upload. No process crash or network fault is simulated by this exercise.

```python
missing_id = ObjectId()
missing_rejected = False
try:
    with bucket.open_download_stream(missing_id) as download:
        download.read(1)
except NoFile:
    missing_rejected = True
require(missing_rejected, "Expected NoFile for nonexistent ID")

aborted_id = ObjectId()
upload = bucket.open_upload_stream_with_id(
    aborted_id, "aborted.bin", metadata={"owner": OWNER}
)
try:
    upload.write(b"x" * (CHUNK_SIZE * 2 + 1))
    upload.abort()
except Exception:
    # Best-effort abort can itself fail; preserve the ID for reconciliation.
    try:
        upload.abort()
    except Exception:
        pass
    raise
require(files.count_documents({"_id": aborted_id}) == 0,
        "Aborted upload left file metadata")
require(chunks.count_documents({"files_id": aborted_id}) == 0,
        "Aborted upload left chunks")
print({"stage": "failure_recovery", "missing_file_rejected": True,
       "aborted_id": str(aborted_id), "abort_reconciled": True})
```

Diagnosis for missing content: verify deployment, database, bucket, file ID and publication state before treating the error as data loss. Keep the file ID in error records, with appropriate access controls. Repair a broken pointer only after validating the intended target file.

An application crash can leave chunks without a completed file record. The abort test does not prove crash cleanup. A production reconciliation worker must distinguish abandoned uploads from still-running uploads using application-owned upload leases, age budgets and fencing. Never delete every chunk with no current metadata row while writers are active. On ambiguous completion, check the retained ID and verify a download before deciding to publish or clean up.

## 9. Lab D — deterministic document-limit rollover

Use a generous byte cap and a small document cap, then insert serially. This isolates count-based rollover from byte-based variability.

```python
lab.create_collection("diagnostic_ring", capped=True, size=1024 * 1024, max=5)
ring = lab.diagnostic_ring
for seq in range(12):
    ring.insert_one({"_id": seq, "seq": seq, "message": "synthetic", "owner": OWNER})
retained = list(ring.find({}, {"_id": 0, "seq": 1}).sort("$natural", 1))
require([row["seq"] for row in retained] == [7, 8, 9, 10, 11],
        "Unexpected serial-writer rollover")
options = next(lab.list_collections(filter={"name": "diagnostic_ring"}))["options"]
require(options["capped"] is True and options["max"] == 5, "Capped options mismatch")
last_consumed = 2
available = list(ring.find({"seq": {"$gt": last_consumed}}).sort("seq", 1))
require(available[0]["seq"] > last_consumed + 1, "Expected an observable gap")
print({"stage": "rollover", "retained": [row["seq"] for row in retained],
       "last_consumed": last_consumed, "first_available": available[0]["seq"],
       "missing_range": [3, 6]})
```

Expected: only sequences 7–11 remain; a reader checkpointed at 2 has lost 3–6. The writer's majority acknowledgement does not promise that the collection will retain those entries until every consumer has read them.

Corrective action depends on the workload. For best-effort diagnostics, emit a gap marker and continue with an explicitly recorded loss range. For business events, reconcile from an authoritative durable source or change the storage design. Increasing capacity cannot recover overwritten entries.

## 10. Lab E — byte-limit rollover

This separate fixture has no document cap. Do not assert an exact retained count: encoded size, allocation and server behavior affect it. Instead prove bounded overwrite and survival of the latest serial write.

```python
lab.create_collection("byte_ring", capped=True, size=65536)
byte_ring = lab.byte_ring
for seq in range(100):
    byte_ring.insert_one({"_id": seq, "seq": seq, "payload": "x" * 4096})
byte_rows = list(byte_ring.find({}, {"seq": 1}).sort("$natural", 1))
require(0 < len(byte_rows) < 100, "Expected byte-limited rollover")
require(byte_rows[-1]["seq"] == 99, "Newest serial write missing")
require(byte_ring.find_one({"_id": 0}) is None, "Oldest write was not overwritten")
stats = lab.command("collStats", "byte_ring")
print({"stage": "byte_rollover", "retained_count": len(byte_rows),
       "first_seq": byte_rows[0]["seq"], "last_seq": byte_rows[-1]["seq"],
       "size": stats.get("size"), "storageSize": stats.get("storageSize"),
       "maxSize": stats.get("maxSize")})
```

Do not equate configured data capacity with total filesystem use: indexes, replication and other database data also consume storage. Approximate retention is usable capacity divided by encoded incoming bytes/second. At 2 MiB/s, a 1 GiB buffer gives roughly 512 seconds before accounting for overhead and bursts. A ten-minute consumer outage would exceed that estimate.

## 11. Lab F — deliberate consumer-gap recovery record

The lab has no durable event source for overwritten diagnostic entries. Its recovery is an explicit loss record, not reconstructed history.

```python
lab.consumer_recovery.insert_one({
    "_id": "training-reader", "old_checkpoint": last_consumed,
    "missing_from": 3, "missing_to": 6,
    "policy": "best_effort_diagnostics_accept_recorded_gap",
    "new_checkpoint": 11, "recordedAt": datetime.now(timezone.utc),
})
recovery = lab.consumer_recovery.find_one({"_id": "training-reader"})
require(recovery["missing_from"] == 3 and recovery["missing_to"] == 6,
        "Gap evidence missing")
print({"stage": "gap_record", "policy": recovery["policy"],
       "new_checkpoint": recovery["new_checkpoint"]})
client.close()
print("PASS: lab assertions completed; retain namespace until evidence is saved")
```

Run the assembled script once:

```bash
python ch66_lab.py
```

Expected stages: round trip, publication, failure recovery, document rollover, byte rollover and gap record. An exception stops execution; do not rerun against the partially populated database. Diagnose and then clean up or use a newly owned namespace consistently throughout the script.

### Optional tailable-cursor drill

For a live-tail exercise, create a separate sufficiently sized capped fixture and seed it before opening the cursor. Use PyMongo `CursorType.TAILABLE_AWAIT` with a bounded `max_await_time_ms` and an application deadline. Append serial sequence numbers from a second process. Verify delivery, idle waiting, disconnect/reopen behavior and loss detection after deliberate rollover.[4]

Do not treat an empty poll as terminal stream exhaustion or `cursor.alive` as proof of future delivery. On cursor death, reconnect from an application checkpoint and check whether the required sequence remains available. This optional drill is a design exercise; it is not included in the script's passed stages or runtime acceptance until separately executed.

## 12. Production operations, retention and recovery

| Area | GridFS | Capped diagnostics |
|---|---|---|
| Capacity | File bytes, chunk count, indexes, replicas, temporary old/new versions | Encoded write rate, burst size, indexes and desired reader outage budget |
| Concurrency | Bound transfers and memory; monitor pool waits | Benchmark serialized-write behavior before choosing for busy producers |
| Authorization | Protect metadata, chunks, pointers and tenant-specific access | Separate writers/readers; restrict collection lifecycle operations |
| Retention | Delete through bucket API; verify references and reader grace | Overwrite follows capacity/count, not elapsed time |
| Observability | Upload/download failures, digests, unreferenced files, stale uploads | Earliest/latest sequence, retained count, write rate and consumer lag |
| Recovery | Restore consistent bucket collections plus application references; download/hash verify | Restore cannot recreate entries already overwritten before backup |

For GridFS backup acceptance, recover `assets.files`, `assets.chunks` and application pointer metadata from a consistent recovery point. Reconcile file lengths, chunk sequence and end-to-end digests. Do not restore just one side of the bucket and declare success. Test representative large files, not only metadata queries.

A deletion worker should record its intent, ensure the ID is not the current published version, apply reader policy, call `bucket.delete(file_id)` and verify absence of both metadata and chunks. Interrupted deletes require reconciliation. In the owned lab, after saving upload evidence, the previous revision can be deleted through the same bucket API; the full namespace cleanup below also removes all owned fixtures.

Avoid changing a production collection to capped as a casual tuning fix. Conversion or downsizing can discard data and alter application semantics. A controlled replacement requires a new namespace, copied/reconciled data where appropriate, producer/consumer routing changes and a tested recovery plan. Retention settings alone are not a rollback for already overwritten data.

GridFS sharding needs a separate review of both collections, chunk indexes, file identity distribution and driver compatibility. Capped collections cannot be sharded.[3] Do not copy a generic shard key from an ordinary business collection into either workload without a supported design.

## 13. Troubleshooting and owned cleanup

| Symptom | Evidence | Likely cause | Action and verification |
|---|---|---|---|
| Filename returns unexpected content | All matching file IDs, revisions and pointer | Multiple revisions share a label | Resolve by immutable ID; download and hash |
| GridFS download fails | ID, metadata, chunk sequence, error and recovery point | Wrong bucket or incomplete/corrupt file | Verify routing; recover consistent file data; hash before publication |
| Upload result uncertain | Retained ID, file record and download result | Lost acknowledgement or interruption | Reconcile before retry or delete; preserve active-upload fencing |
| Storage grows despite file TTL | Files/chunks counts and lifecycle configuration | Metadata-only deletion left chunks | Replace TTL with reviewed bucket lifecycle reconciliation |
| New revision exists but users see old one | Pointer revision and compare-and-set result | Publication failed or application cache stale | Verify pointer ownership and refresh client contract |
| Capped reader skips entries | Checkpoint, earliest sequence and producer rate | Consumer overtaken by rollover | Record gap; reconcile authoritative source or accept declared diagnostic loss |
| Capped capacity change did not recover history | Available sequence range and policy history | Overwrite already occurred | Restore only from a source that retained missing data |
| Concurrent tail order differs | Writer identities and explicit sequence contract | No global insertion-order guarantee | Define an ordering owner or use an appropriate event log |
| Operations fail under strict API | Driver ServerApi settings and server error | Capped collections outside Stable API V1 | Review client policy; do not silently weaken shared clients |

Save nonsecret lab output before cleanup. Connect through the Chapter 42 mongosh TLS/SCRAM procedure and run this separate block. It drops only the named chapter database after verifying ownership.

```javascript
var labName = "mongodb_enterprise_ch66_specialized";
var lab = db.getSiblingDB(labName);
if (labName !== "mongodb_enterprise_ch66_specialized" || lab.getName() !== labName) {
  throw new Error("Refusing cleanup outside Chapter 66 database");
}
if (lab.ownership.findOne({ _id: "mongodb-enterprise-tutorial-ch66" }) === null) {
  throw new Error("Ownership missing: investigate before cleanup");
}
var result = lab.dropDatabase();
if (result.ok !== 1) throw new Error("Owned database cleanup failed");
if (db.getSiblingDB(labName).getCollectionInfos().length !== 0) {
  throw new Error("Cleanup left collections");
}
print("PASS: chapter-owned database removed");
```

Leave the retained cluster, operator resources and other chapter data under their existing lifecycle. Local `ch66_lab.py` and the virtual environment are reusable lab assets; remove them only when no longer needed. A rerun requires an empty owned database and fresh file IDs.

## 14. Acceptance record and review

| Check | Required evidence |
|---|---|
| Environment | Exact server/FCV, topology, Python and pinned driver version |
| GridFS integrity | 17825792 bytes, 69 contiguous chunks, equal SHA-256 |
| Publication | Two same-name versions; verified revision 2 pointer; previous retained |
| Failure handling | NoFile observed; explicit abort left no metadata/chunks |
| Document rollover | Retained sequence 7–11; gap 3–6 detected |
| Byte rollover | Oldest absent, latest 99 present, retained count below 100 |
| Recovery policy | Gap record explicitly accepts diagnostic loss |
| Cleanup | Ownership check, scoped drop and absence verification |

Record passed, failed or not run for each check. Capture errors and partial state if the script fails. Optional tailing, production load, interruption during upload, actual failover and restore acceptance remain separate requirements.

Review questions:

1. Why is a filename insufficient as a published object identity?
2. What happens if an upload succeeds but the pointer update fails?
3. Why is a scan for chunks without file metadata unsafe while uploaders are active?
4. Which data must a GridFS restore recover together?
5. Why does majority acknowledgement not prevent capped consumer loss?
6. What determines a capped buffer's approximate time window?
7. When would an ordinary TTL collection or an external durable log better satisfy the workload?

## 15. Official references and validation status

1. [MongoDB 8.0 — GridFS](https://www.mongodb.com/docs/v8.0/core/gridfs/).
2. [PyMongo — Store Large Files](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/crud/gridfs/) and [GridFS API](https://pymongo.readthedocs.io/en/stable/api/gridfs/grid_file.html). Check APIs against the exact pinned driver.
3. [MongoDB 8.0 — Capped Collections](https://www.mongodb.com/docs/v8.0/core/capped-collections/).
4. [MongoDB 8.0 — Tailable Cursors](https://www.mongodb.com/docs/v8.0/core/tailable-cursors/).

Documentation reviewed on 2026-10-11. The version-publication protocol, deterministic payload, consumer loss record and acceptance budgets are operational teaching designs. Python and JavaScript blocks were syntax-checked; local checks verified payload size, digest reproducibility, chunk arithmetic and expected serial sequence windows. These checks do not exercise MongoDB, GridFS driver behavior, authentication, abort cleanup, capped allocation or backup recovery. No live MongoDB or mongosh validation was performed in the authoring environment.

**Chapter completion:** Written and statically reviewed. Runtime acceptance remains pending until the retained authorized lab is executed and evidence recorded.

Previous: [Chapter 65 — Time Series Collections and Retention](65-time-series-collections-and-retention.md).  
Next: Chapter 67 — MongoDB to Snowflake Direct Integration.
