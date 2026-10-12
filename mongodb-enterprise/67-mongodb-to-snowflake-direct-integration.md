# 67 — MongoDB to Snowflake Direct Integration

Part 9 — Specialized Data and Observability

**Audience:** Data Engineers, Developers, DBREs and SREs.  
**Goal:** Move MongoDB data directly into Snowflake, prove replay and deletion behavior, and define the production bootstrap/CDC recovery contract.  
**Baseline:** Retained authenticated TLS MongoDB 8.0 / FCV 8.0 replica set; Python 3.11+, pinned reviewed PyMongo 4.x and Snowflake Connector for Python releases; authorized Snowflake lab account with an existing warehouse. Record exact versions and account/cloud region.  
**Status:** Written; Python syntax and local contract checks complete; live MongoDB/Snowflake acceptance pending.  
**Prerequisites:** Chapters 27, 41–42, 49, 63–65; Snowflake roles, VARIANT, transactions and MERGE fundamentals.  
**Estimated time:** 90–120 minutes, excluding account provisioning.

## 1. Integration scope and acceptance contract

The integration path is MongoDB → extraction/integration worker → Snowflake. It does not require Elasticsearch as an intermediary. For the existing `pd_care_assesment` use case, confirm the exact deployed namespace spelling and ownership in your inventory; this tutorial uses only an isolated synthetic `assessments` collection.

A direct integration can still use durable staging, object storage or an event log. “Direct” describes the source-to-warehouse dependency, not an assurance that no transport components exist.

The lab implements a small controlled batch protocol. An application-owned immutable mutation log carries full document images, monotonically increasing per-document versions and explicit deletion tombstones. The fixture writer is stopped during export. This allows repeatable replay and stale-event tests without pretending that a normal collection scan is a consistent production CDC bootstrap.

Acceptance requires:

- Source identity and BSON-to-JSON mapping recorded.
- Six mutation records extracted and acknowledged into a raw Snowflake table.
- One latest record selected per source identity before MERGE.
- Two live documents and one tombstone with expected values.
- Duplicate batch replay leaves materialized state unchanged.
- A later stale record cannot resurrect deleted data.
- A conflicting equal-version record is rejected before publication.
- Cleanup limited to explicitly owned source and warehouse resources.

This is a custom teaching protocol. It does not claim to be a native managed MongoDB connector or a complete production CDC service.

## 2. Choose batch or CDC deliberately

| Pattern | Suitable requirement | Necessary evidence |
|---|---|---|
| Controlled frozen export | One-time migration or acceptance fixture | Writer freeze, exact namespace, complete count and checksum |
| Application mutation log/outbox | Writers own an explicit versioned change contract | Atomic source publication, immutable records, retention and ordering |
| MongoDB change streams | Database-originated ongoing changes | Supported source type, retained history, durable tokens, sink acknowledgement |
| Managed integration product | Supported connector lifecycle | Exact product/version, deployment support, delete/schema/recovery behavior |

A poll on `updatedAt` is not automatically complete CDC. Equal timestamps, clock skew, late updates and hard deletes need explicit treatment. Overlapping windows and deduplication can reduce some risks but do not create missing deletion events.

Chapter 64 defines change-stream acknowledgement and token handling. A resume token is opaque BSON, not a Snowflake sortable sequence. A production adapter must translate source ordering into a deliberate materialization contract while preserving the original token for restart.[1]

## 3. Identity, schema and deletion rules

Use a source identity tuple such as deployment, database, collection and document ID. Include tenant identity where the application requires it. Do not join unrelated collections solely on their `_id` string.

For this fixed-source lab, `SOURCE_KEY` is the ObjectId hex string. A production key must include the source namespace/deployment boundary. Preserve BSON types with an explicit schema contract:

| MongoDB value | Lab mapping | Production review |
|---|---|---|
| ObjectId | Lowercase hexadecimal string | Do not conflate with ordinary string IDs |
| Date | UTC ISO string | Validate timezone and precision |
| Integer version | JSON integer → NUMBER | Require positive integral values |
| Assessment fields | JSON object → VARIANT | Validate required fields and sensitive attributes |
| Decimal128, binary, mixed IDs | Not used in fixture | Define Extended JSON or typed conversion; reject accidental coercion |
| Delete | `deleted=true`, `doc=null` | Retain versioned tombstone until replay window is closed |

Deleting the target row would discard its version barrier. A delayed old upsert could then recreate it. This lab keeps a tombstone in the state table and filters it out in a live-data view.

Schema changes must have a recorded version and compatibility policy. Null, missing and malformed are different states. A successful JSON parse does not prove that the business schema is valid.

## 4. Security, prerequisites and cost boundary

MongoDB extraction needs `find` on the owned mutation-log collection. Real change-stream extraction additionally needs the required `changeStream` privileges. Use a separate fixture writer for inserts and deletes and a separate lifecycle administrator for cleanup.

The Snowflake lab role needs USAGE on the existing database and warehouse and CREATE SCHEMA in that database. It owns the new lab schema and its tables/view. Production roles should separate raw landing, transformation and data access. Do not use ACCOUNTADMIN merely to avoid missing grants.

Use authorized network paths, verified MongoDB TLS, and a preconfigured Snowflake connection profile using the organization's approved authentication, such as key-pair or interactive authentication. Do not embed passwords, private keys or real assessment data in examples or logs. Mask/restrict raw sensitive payloads and define a retention owner for the landing table.

The script creates only one fresh schema in an existing lab database. It uses an existing warehouse and does not resize or create compute. Set warehouse budgets and auto-suspend through its normal owner. Snowflake execution can incur charges; record runtime, query history and warehouse settings in acceptance evidence.

## 5. Source lab — controlled immutable mutation fixture

Connect using Chapter 42's mongosh TLS/SCRAM procedure. Require an accepted replica set primary. Run this block once, with no concurrent fixture writer. The six mutations are inserted sequentially, then the current source state is established for reconciliation. This ordering is a fixture design, not an atomic production outbox implementation.

```javascript
var labName = "mongodb_enterprise_ch67_direct";
var lab = db.getSiblingDB(labName);
if (lab.getCollectionInfos().length !== 0) throw new Error("Namespace exists");
if (!db.hello().isWritablePrimary) throw new Error("Expected primary");
lab.ownership.insertOne({ _id: "mongodb-enterprise-tutorial-ch67", createdAt: new Date() });
var a = ObjectId("670000000000000000000001");
var b = ObjectId("670000000000000000000002");
var c = ObjectId("670000000000000000000003");
var mutations = [
  { _id: "e1", sourceId: a, version: 1, deleted: false,
    doc: { tenant: "training", score: 10, status: "open" } },
  { _id: "e2", sourceId: b, version: 1, deleted: false,
    doc: { tenant: "training", score: 20, status: "open" } },
  { _id: "e3", sourceId: a, version: 2, deleted: false,
    doc: { tenant: "training", score: 15, status: "complete" } },
  { _id: "e4", sourceId: c, version: 1, deleted: false,
    doc: { tenant: "training", score: 30, status: "open" } },
  { _id: "e5", sourceId: b, version: 2, deleted: true, doc: null },
  { _id: "e6", sourceId: c, version: 2, deleted: false,
    doc: { tenant: "training", score: 35, status: "complete" } }
];
for (var event of mutations) {
  lab.mutations.insertOne(event, { writeConcern: { w: "majority", wtimeout: 10000 } });
}
lab.assessments.insertMany([
  { _id: a, version: 2, tenant: "training", score: 15, status: "complete" },
  { _id: c, version: 2, tenant: "training", score: 35, status: "complete" }
], { writeConcern: { w: "majority", wtimeout: 10000 } });
if (lab.mutations.countDocuments({}) !== 6) throw new Error("Mutation count mismatch");
if (lab.assessments.countDocuments({}) !== 2) throw new Error("Live count mismatch");
printjson(lab.assessments.find().sort({ _id: 1 }).toArray());
```

Expected: six immutable mutations; live source identities A and C, versions 2, scores 15 and 35. Identity B is absent from current state and has a deletion record at version 2. Keep writers stopped until acceptance finishes.

A real outbox requires publication of the business change and its mutation record atomically, or another independently verified capture mechanism. Independent sequential writes can leave missing or phantom changes during a crash. The lab's stopped fixture does not establish that production guarantee.

## 6. Worker environment and connection

Create an isolated Python environment. Pin exact reviewed versions in environment variables before installation.

```bash
python -m venv .venv-ch67
source .venv-ch67/bin/activate
python -m pip install "pymongo==${CH67_PYMONGO_VERSION:?set exact reviewed version}" \
  "snowflake-connector-python==${CH67_SNOWFLAKE_VERSION:?set exact reviewed version}"
python -m pip freeze
```

On Windows, use `py -m venv .venv-ch67`, activate `.\.venv-ch67\Scripts\Activate.ps1`, and substitute PowerShell `$env:CH67_PYMONGO_VERSION` / `$env:CH67_SNOWFLAKE_VERSION` in the pip command.

Set these nonsecret connection parameters through the approved environment mechanism:

| Variable | Value |
|---|---|
| `CH67_MONGO_URI` | Retained replica-set URI without credentials |
| `CH67_MONGO_USER` | Scoped extraction user |
| `CH67_CA_FILE` | Verified MongoDB CA path |
| `CH67_SF_CONNECTION` | Existing approved Snowflake connector connection profile name |
| `CH67_SF_DATABASE` | Existing authorized lab database |
| `CH67_SF_WAREHOUSE` | Existing authorized warehouse |

The Snowflake profile owns authentication and role selection. Validate that profile before the lab. The script prompts for MongoDB's password. Save Sections 7–10 consecutively as `ch67_direct.py`.

## 7. Extract and validate the source envelope

```python
import getpass
import hashlib
import json
import os
import re
import uuid

import pymongo
import snowflake.connector
from bson import ObjectId
from pymongo import MongoClient
from pymongo.read_concern import ReadConcern

SOURCE_DB = "mongodb_enterprise_ch67_direct"
OWNER = "mongodb-enterprise-tutorial-ch67"
SCHEMA = "CH67_MONGO_DIRECT_LAB"


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def ident(value):
    require(bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value)),
            "Use a simple unquoted lab identifier")
    return value.upper()


def normalize(event):
    require(isinstance(event["sourceId"], ObjectId), "Unsupported source ID type")
    version = event["version"]
    require(isinstance(version, int) and not isinstance(version, bool) and version > 0,
            "Version must be a positive integer")
    require(isinstance(event["deleted"], bool), "Deletion flag must be boolean")
    doc = event["doc"]
    if event["deleted"]:
        require(doc is None, "Tombstone must have null document")
    else:
        require(isinstance(doc, dict) and doc.get("tenant") == "training",
                "Fixture tenant/schema mismatch")
        require(isinstance(doc.get("score"), int) and not isinstance(doc["score"], bool),
                "Score must be integral")
        require(doc.get("status") in {"open", "complete"}, "Invalid status")
    envelope = {"source_key": str(event["sourceId"]), "version": version,
                "deleted": event["deleted"], "doc": doc}
    encoded = json.dumps(envelope, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return encoded, hashlib.sha256(encoded.encode("utf-8")).hexdigest()


mongo = MongoClient(
    os.environ["CH67_MONGO_URI"], username=os.environ["CH67_MONGO_USER"],
    password=getpass.getpass("MongoDB extraction password: "), authSource="admin",
    tls=True, tlsCAFile=os.environ["CH67_CA_FILE"],
    serverSelectionTimeoutMS=10000, socketTimeoutMS=30000, maxPoolSize=5,
)
mongo.admin.command("ping")
source = mongo.get_database(SOURCE_DB, read_concern=ReadConcern("majority"))
require(source.ownership.find_one({"_id": OWNER}) is not None, "Source ownership missing")
events = list(source.mutations.find().sort("_id", 1))
require(len(events) == 6, "Expected six frozen fixture events")
encoded_rows = [normalize(event) for event in events]
require(len({event["_id"] for event in events}) == 6, "Duplicate event identities")
source_live = {str(row["_id"]): (row["version"], row["score"])
               for row in source.assessments.find()}
require(len(source_live) == 2 and sum(v[1] for v in source_live.values()) == 50,
        "Source fixture reconciliation failed")
print({"driver": pymongo.version, "source_events": len(events),
       "source_live": len(source_live), "source_score_total": 50})
mongo.close()
```

This extracts only six known records into memory. Production workers need bounded batches, streaming, an immutable manifest, checksum, source scope and explicit checkpoint ownership. Majority reads on a moving scan are not a complete snapshot-plus-CDC protocol.

## 8. Create fresh Snowflake landing and state objects

The script refuses to replace an existing lab schema. Snowflake DDL is outside the materialization transaction. Do not add `CREATE OR REPLACE` to make a rerun succeed.

```python
sf_database = ident(os.environ["CH67_SF_DATABASE"])
sf_warehouse = ident(os.environ["CH67_SF_WAREHOUSE"])
sf = snowflake.connector.connect(connection_name=os.environ["CH67_SF_CONNECTION"])
cur = sf.cursor()
cur.execute(f"USE DATABASE {sf_database}")
cur.execute(f"USE WAREHOUSE {sf_warehouse}")
cur.execute("SELECT CURRENT_VERSION(), CURRENT_ROLE(), CURRENT_WAREHOUSE()")
print({"snowflake_environment": cur.fetchone()})
cur.execute(f"CREATE SCHEMA {SCHEMA} COMMENT='mongodb-enterprise-tutorial-ch67'")
cur.execute(f"USE SCHEMA {SCHEMA}")
cur.execute("ALTER SESSION SET QUERY_TAG='mongodb-enterprise-ch67'")
cur.execute("ALTER SESSION SET ERROR_ON_NONDETERMINISTIC_MERGE=TRUE")
cur.execute("""CREATE TABLE OWNERSHIP (OWNER VARCHAR)""")
cur.execute("INSERT INTO OWNERSHIP VALUES (%s)", (OWNER,))
cur.execute("""CREATE TABLE RAW_EVENTS (
  BATCH_ID VARCHAR, EVENT_ID VARCHAR, ENVELOPE VARIANT,
  CONTENT_SHA VARCHAR, LANDED_AT TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP()
)""")
cur.execute("""CREATE TABLE ASSESSMENT_STATE (
  SOURCE_KEY VARCHAR, SOURCE_VERSION NUMBER(38,0), IS_DELETED BOOLEAN,
  DOCUMENT VARIANT, CONTENT_SHA VARCHAR, APPLIED_AT TIMESTAMP_LTZ
)""")
cur.execute("""CREATE TABLE BATCH_AUDIT (
  BATCH_ID VARCHAR, INPUT_ROWS NUMBER, COMMITTED_AT TIMESTAMP_LTZ
)""")
cur.execute("""CREATE VIEW ASSESSMENTS_LIVE AS
  SELECT SOURCE_KEY, SOURCE_VERSION, DOCUMENT
  FROM ASSESSMENT_STATE WHERE IS_DELETED = FALSE""")
```

No PRIMARY KEY declaration is used as a deduplication mechanism. Standard Snowflake table uniqueness is not enforced like MongoDB's unique index.[2] The lab requires one materialization worker and explicit source/target duplicate checks.

## 9. Land raw events and materialize with a version barrier

The following parameterized inserts deliberately suit a six-event acceptance fixture. High-volume production ingestion should review staged files with COPY or an appropriate streaming mechanism, including load-error handling, file manifests and materialization lag.[3][4] Transport success alone does not prove that the live view is current.

```python
MERGE_SQL = """
MERGE INTO ASSESSMENT_STATE t
USING (
  SELECT ENVELOPE:source_key::VARCHAR AS SOURCE_KEY,
         ENVELOPE:version::NUMBER(38,0) AS SOURCE_VERSION,
         ENVELOPE:deleted::BOOLEAN AS IS_DELETED,
         ENVELOPE:doc AS DOCUMENT, CONTENT_SHA
  FROM RAW_EVENTS
  WHERE BATCH_ID = %s
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY ENVELOPE:source_key::VARCHAR
    ORDER BY ENVELOPE:version::NUMBER(38,0) DESC, EVENT_ID DESC
  ) = 1
) s ON t.SOURCE_KEY = s.SOURCE_KEY
WHEN MATCHED AND s.SOURCE_VERSION > t.SOURCE_VERSION THEN UPDATE SET
  SOURCE_VERSION=s.SOURCE_VERSION, IS_DELETED=s.IS_DELETED,
  DOCUMENT=s.DOCUMENT, CONTENT_SHA=s.CONTENT_SHA, APPLIED_AT=CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN INSERT
  (SOURCE_KEY, SOURCE_VERSION, IS_DELETED, DOCUMENT, CONTENT_SHA, APPLIED_AT)
VALUES
  (s.SOURCE_KEY, s.SOURCE_VERSION, s.IS_DELETED, s.DOCUMENT,
   s.CONTENT_SHA, CURRENT_TIMESTAMP())
"""


def scalar(sql, parameters=()):
    cur.execute(sql, parameters)
    return cur.fetchone()[0]


def materialize(batch_id, records):
    # Explicit transaction covers raw acceptance, MERGE and audit together.
    cur.execute("BEGIN")
    try:
        for event_id, encoded, sha in records:
            cur.execute("""INSERT INTO RAW_EVENTS (BATCH_ID, EVENT_ID, ENVELOPE, CONTENT_SHA)
              SELECT %s, %s, PARSE_JSON(%s), %s""",
                        (batch_id, event_id, encoded, sha))
        # Reject conflicting same-version states anywhere in retained raw history.
        conflicts = scalar("""SELECT COUNT(*) FROM (
          SELECT ENVELOPE:source_key::VARCHAR, ENVELOPE:version::NUMBER(38,0)
          FROM RAW_EVENTS GROUP BY 1, 2 HAVING COUNT(DISTINCT CONTENT_SHA) > 1
        )""")
        require(conflicts == 0, "Conflicting equal-version payloads: rollback and investigate")
        duplicate_target = scalar("""SELECT COUNT(*) FROM (
          SELECT SOURCE_KEY FROM ASSESSMENT_STATE GROUP BY 1 HAVING COUNT(*) > 1
        )""")
        require(duplicate_target == 0, "Target identity duplicates: stop publication")
        cur.execute(MERGE_SQL, (batch_id,))
        cur.execute("""INSERT INTO BATCH_AUDIT
          SELECT %s, %s, CURRENT_TIMESTAMP()""", (batch_id, len(records)))
        cur.execute("COMMIT")
    except Exception:
        cur.execute("ROLLBACK")
        raise


def state():
    cur.execute("""SELECT SOURCE_KEY, SOURCE_VERSION, IS_DELETED,
      DOCUMENT:score::NUMBER, CONTENT_SHA
      FROM ASSESSMENT_STATE ORDER BY SOURCE_KEY""")
    return cur.fetchall()


batch_id = "ch67-" + uuid.uuid4().hex
records = [(event["_id"], encoded, sha)
           for event, (encoded, sha) in zip(events, encoded_rows)]
materialize(batch_id, records)
initial_state = state()
require(len(initial_state) == 3, "Expected three states including tombstone")
require(sum(1 for row in initial_state if row[2]) == 1, "Expected one tombstone")
warehouse_live = {row[0]: (int(row[1]), int(row[3]))
                  for row in initial_state if not row[2]}
require(warehouse_live == source_live, "Source/warehouse identity and value mismatch")
require(scalar("SELECT COUNT(*) FROM ASSESSMENTS_LIVE") == 2, "Live view count wrong")
print({"stage": "initial_materialization", "batch_id": batch_id,
       "raw_rows": scalar("SELECT COUNT(*) FROM RAW_EVENTS"),
       "state_rows": len(initial_state), "live_rows": 2, "score_total": 50})
```

Source deduplication precedes MERGE because multiple source matches can create ambiguous updates or duplicate inserts.[5] The tie-breaker is safe here only because conflicting equal-version content is rejected first. Arbitrarily sorting event IDs is not a substitute for source ordering.

The history-wide conflict scan is intentionally small and exhaustive. At production scale, use indexed/bounded contract state or an appropriately designed ingestion ledger; do not copy this full raw-table scan into every high-volume batch.

## 10. Failure and replay acceptance

Replay the same records under the same batch ID. This lab allows duplicate raw rows and repeated audit entries while keeping the state stable. Raw landing idempotency and state materialization idempotency are distinct contracts.

```python
materialize(batch_id, records)
require(state() == initial_state, "Replay changed materialized content/version")
require(scalar("SELECT COUNT(*) FROM RAW_EVENTS") == 12, "Expected retained raw replay")

# A late version-1 upsert for B must not defeat its version-2 tombstone.
stale_encoded, stale_sha = normalize(events[1])
materialize("stale-" + uuid.uuid4().hex, [("late-e2", stale_encoded, stale_sha)])
require(state() == initial_state, "Stale replay resurrected deleted state")

# Equal-version different data is a contract breach, not a valid new update.
conflicting = dict(events[2])
conflicting["doc"] = {"tenant": "training", "score": 999, "status": "complete"}
bad_encoded, bad_sha = normalize(conflicting)
raw_before = scalar("SELECT COUNT(*) FROM RAW_EVENTS")
bad_batch = "conflict-" + uuid.uuid4().hex
rejected = False
try:
    materialize(bad_batch, [("bad-e3", bad_encoded, bad_sha)])
except RuntimeError as error:
    require("Conflicting equal-version" in str(error), "Unexpected failure")
    rejected = True
require(rejected, "Conflicting mutation was not rejected")
require(scalar("SELECT COUNT(*) FROM RAW_EVENTS") == raw_before,
        "Failed transaction left raw records")
require(scalar("SELECT COUNT(*) FROM BATCH_AUDIT WHERE BATCH_ID=%s", (bad_batch,)) == 0,
        "Failed batch was marked committed")
require(state() == initial_state, "Failed batch changed materialized state")
print({"stage": "replay_and_failure", "raw_rows": raw_before,
       "replay_stable": True, "stale_blocked": True, "conflict_rolled_back": True})
cur.close()
sf.close()
print("PASS: lab assertions completed; save evidence before owned cleanup")
```

Run `python ch67_direct.py`. Expected raw count is 6 after initial load, 12 after replay and 13 after the stale record. The conflicting record is rolled back. Expected current state remains A/version 2/score 15, B/version 2/deleted, C/version 2/score 35.

This script does not claim distributed exactly-once delivery. A source checkpoint would be advanced only after the warehouse transaction is known committed. If the commit acknowledgement is lost, reconnect and reconcile the batch/audit identity before deciding to resume. For an automated production worker, enforce one owner/lease and an idempotent durable commit ledger rather than this lab's intentionally duplicate audit rows.

## 11. Production bootstrap plus change streams

For a moving production source, define one supported bootstrap protocol and prove there is no snapshot-to-stream gap. A general design review must cover:

1. Establishing a retained stream boundary before a long initial scan.
2. Durably buffering changes while the scan proceeds.
3. Producing a supported consistent baseline or a reconciliation protocol that resolves scan/change overlap.
4. Applying buffered mutations in correct per-identity order.
5. Verifying deletion handling and baseline-to-stream convergence before publishing.

Opening a stream and then running an arbitrary `find()` is not, by itself, proof of consistency. A fuzzy scan needs an overlap/reconciliation algorithm; a point-in-time scan needs a supported snapshot protocol and resources. Oplog history must outlive bootstrap, outages and catch-up. History loss requires a deliberate rebuild rather than silently opening at “now.”[1]

If change streams provide update deltas, implement nested path/array changes and removed fields correctly. If you use `fullDocument` lookup, account for the fact that it can represent a later document state. It is not automatically an exact image for that update event. Define what deletes, invalidations and collection recreation mean to downstream state.

The lab's integer version is supplied by its mutation contract. Do not invent this version by parsing resume tokens or comparing their string forms. For raw change streams, a serialized materializer can assign durable per-key ordering from its accepted event sequence, provided bootstrap, replay, ownership and checkpoint semantics preserve that order. Cross-collection atomic business reporting requires another explicit contract.

Time series sources from Chapter 65 cannot simply use Chapter 64's change-stream adapter. Review collection-type support and choose an upstream capture or approved alternate extraction path. The Snowflake live view must have a declared freshness SLA independent of mere source connectivity.

## 12. Observability, reconciliation and recovery

| Signal | What it establishes |
|---|---|
| Source retained-history window | Whether the saved CDC position remains recoverable |
| Source-read, durable-landing and materialized positions | Which pipeline boundary is lagging |
| Batch manifest count/checksum and landing errors | Whether transport accepted the intended payload |
| Source-key duplicates and equal-version conflicts | Whether identity/version assumptions remain valid |
| Tombstone count and stale mutation rejection | Whether delete replay protection is active |
| Live row count and field totals per closed scope | Whether materialized business state matches the source contract |
| Warehouse runtime, queueing and bytes scanned | Whether compute or full-table work controls latency/cost |
| Checkpoint age, worker lease and reconciliation drift | Whether a stopped or competing worker needs recovery |

Counts alone can match while values differ. Compare identities, versions and selected field totals over a closed source scope. For large datasets, reconcile partitioned manifests and digests under an explicit canonicalization scheme; BSON conversion must be stable before comparing checksums.

Recover raw landing, materialized state, tombstone barriers and source checkpoints as a coordinated logical system. A warehouse restore to an older point paired with a newer source token can skip changes. Resetting the token without retaining tombstone/version history can reintroduce old state. Document the recovery point and replay horizon.

If a worker crashes after warehouse commit but before source checkpoint persistence, replay should be safe. If it checkpoints before durable acceptance, changes can be lost. Chapter 64's acknowledgement ordering still applies even when Snowflake is the sink.

Before enabling scheduled execution, rehearse: failed source authentication; transient Snowflake outage; failure before COMMIT; lost commit acknowledgement; duplicate delivery; late older versions; hard deletes; schema rejection; expired source history; and complete rebuild into a fresh target. The script executes only duplicate/stale/conflict drills; the remaining cases are pending operational acceptance.

## 13. Troubleshooting

| Symptom | Evidence | Cause to test | Corrective action and verification |
|---|---|---|---|
| Source collection appears empty | Deployment, database, collection and role | Wrong scope or grants | Verify exact inventory and scoped read; do not broaden blindly |
| Scores/counts differ | Per-identity source/target comparison | Incomplete extraction or wrong schema | Stop publication; reconcile frozen scope and rejected records |
| Deleted document returns | Tombstone version and late mutation | Version barrier discarded | Restore barrier, replay correct order and verify stale rejection |
| MERGE errors or inserts duplicates | Source key multiplicity, target duplicates | Source not deduplicated | Reject conflicts; select one valid latest state per identity |
| Raw rows grow on replay | Batch/event identities and load policy | Landing contract allows duplicates | Track raw versus materialized idempotency separately |
| Equal-version conflict | Canonical payload digest and writer history | Version reused for different content | Quarantine contract violation; correct upstream version owner |
| Successful ingestion but stale reports | Landing/materialized positions and query history | Transformation failed or lagged | Recover materializer; verify live view at the agreed source boundary |
| Source token no longer resumes | Token envelope, scope and retained oplog | History expired or source lifecycle changed | Rebuild from supported baseline; reconcile before publication |
| Warehouse permission failure | Role, schema/warehouse grants and query ID | Missing scoped privileges | Apply reviewed least-privilege grants; rerun isolated acceptance |
| Recovered target misses changes | Restore point and saved source checkpoint | Inconsistent recovery boundaries | Align baseline/token and replay retained changes |

## 14. Evidence and scoped cleanup

| Check | Expected result |
|---|---|
| Source fixture | Six mutations; two current documents; score total 50 |
| Initial materialization | Six raw rows; three states; one tombstone; two live rows |
| Replay | Twelve raw rows; same materialized values/versions |
| Stale mutation | Thirteen raw rows; B remains deleted at version 2 |
| Conflicting equal version | Rejected; raw count and state unchanged; no committed bad-batch audit |
| Security/version inventory | Exact drivers, server/FCV, Snowflake role/account/warehouse and approved auth |
| Cleanup | Both ownership checks and absence verification |

Save nonsecret worker output and relevant Snowflake query IDs before cleanup. Do not expose connection profiles or credentials. In the same authorized Snowflake context, verify the lab marker, then drop only the owned schema. Execute these statements one at a time; stop if the marker does not return exactly the expected owner.

```sql
-- USE DATABASE <your recorded existing lab database>;
SELECT OWNER FROM CH67_MONGO_DIRECT_LAB.OWNERSHIP;
-- Expected single row: mongodb-enterprise-tutorial-ch67
DROP SCHEMA CH67_MONGO_DIRECT_LAB;
SHOW SCHEMAS LIKE 'CH67_MONGO_DIRECT_LAB';
-- Expected no matching schema.
```

The existing database and warehouse remain under their original owners. MongoDB cleanup through the accepted mongosh TLS session:

```javascript
var labName = "mongodb_enterprise_ch67_direct";
var lab = db.getSiblingDB(labName);
if (lab.ownership.findOne({ _id: "mongodb-enterprise-tutorial-ch67" }) === null) {
  throw new Error("Ownership missing: investigate before cleanup");
}
if (lab.dropDatabase().ok !== 1) throw new Error("Owned source cleanup failed");
if (db.getSiblingDB(labName).getCollectionInfos().length !== 0) {
  throw new Error("Source cleanup left collections");
}
print("PASS: chapter-owned source database removed");
```

If schema creation succeeded but ownership-table creation failed, inspect the schema comment, creation history and failed query evidence before applying manual cleanup. Do not bypass ownership checks by replacing existing objects. Local scripts and virtual environments may be retained for rerun; a rerun requires fresh owned source and target namespaces.

Review questions:

1. Why must direct integration still define transport and checkpoint boundaries?
2. Why does `updatedAt` polling miss hard deletes?
3. How does a tombstone prevent delayed resurrection?
4. Why must conflicting equal-version records be rejected before deduplication?
5. What does a successful raw landing establish, and what remains unproven?
6. How can a recovered warehouse and a saved source token become inconsistent?
7. What additional evidence is needed for a moving-source bootstrap?

## 15. Official references and validation status

1. [MongoDB 8.0 — Change Streams](https://www.mongodb.com/docs/v8.0/changeStreams/).
2. [Snowflake — Constraints Overview](https://docs.snowflake.com/en/sql-reference/constraints-overview).
3. [Snowflake — COPY INTO table](https://docs.snowflake.com/en/sql-reference/sql/copy-into-table).
4. [Snowflake — Using the Python Connector](https://docs.snowflake.com/en/developer-guide/python-connector/python-connector-example) and [INSERT](https://docs.snowflake.com/en/sql-reference/sql/insert).
5. [Snowflake — MERGE](https://docs.snowflake.com/en/sql-reference/sql/merge) and [PARSE_JSON](https://docs.snowflake.com/en/sql-reference/functions/parse_json).

Documentation reviewed on 2026-10-11. The immutable-log fixture, version/tombstone protocol, single-worker assumption and failure drills are teaching designs. Python and JavaScript blocks were syntax-checked; a local model checked replay, stale-version suppression and equal-version conflict behavior. These checks do not execute Snowflake SQL or validate MongoDB extraction, driver authentication, warehouse transactions, network failures or live CDC. No live MongoDB/Snowflake acceptance was performed in the authoring environment.

**Chapter completion:** Written and statically reviewed. Runtime validation remains pending until the authorized lab and cleanup are executed with recorded evidence.

Previous: [Chapter 66 — GridFS Capped Collections and Workload Boundaries](66-gridfs-capped-collections-and-workload-boundaries.md).  
Next: Chapter 68 — Import Export Migration and Data Reconciliation.
