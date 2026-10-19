# 64 — Change Streams Resume Tokens and CDC

Part 8 — Administration Deployment and Integration

**Baseline:** Healthy three-member Enterprise 8.0/FCV 8.0 TLS/SCRAM replica set retained from Chapter 60 or a fully accepted Chapter 62 native lab. Pin a reviewed compatible synchronous PyMongo 4.x release.  
**Status:** Written; Python syntax and mocked-consumer/SQLite helper tests complete; live CRUD, restart, replay, interruption and lifecycle acceptance pending.  
**Prerequisites:** Chapters 25–28 replication and consistency, Chapter 41 least privilege, Chapter 42 TLS, Chapter 63 client lifecycle and the accepted deployment/ownership packet.

## 1. Define the CDC acceptance contract

By the end, you should be able to:

- Choose collection, database or deployment watch scope.
- Explain event identity, resume position and application acknowledgement.
- Restart a CDC consumer without skipping unacknowledged events.
- Reproduce replay and prove sink idempotency.
- Distinguish temporary connectivity failure from lost change history.
- Define oplog headroom, CDC lag and reconciliation evidence.
- Plan bootstrap and recovery without a snapshot-to-stream gap.

### Operational model

CDC captures changes so downstream systems can maintain a derived dataset. Examples include search indexing, warehouse ingestion, cache invalidation and audit/event pipelines. A working database connection does not prove that the downstream dataset is current or complete.

Keep these positions separate:

| Position | Meaning | Owner |
|---|---|---|
| Source event | Change emitted by MongoDB | Database |
| Read position | Event fetched by the consumer | Driver |
| Sink acknowledgement | Event durably accepted downstream | Sink |
| Durable checkpoint | Safe position for process restart | Consumer |
| Materialized position | Event reflected in queryable downstream state | Downstream processor |

For asynchronous warehouse ingestion, upload success may only prove staging durability. Track application/materialization lag separately.

This chapter's lab builds a durable local event inbox. It does not pretend to be a full warehouse connector. Keeping event ingestion separate from state materialization makes the restart boundary observable.

## 2. Server and scope prerequisites

Change streams require a replica set or sharded cluster; they do not run on a standalone mongod. Connect through mongos for a sharded deployment. Collection, database and deployment watches have different lifecycle boundaries. The server manual describes supported scopes and exclusions.[1]

For production, use a narrow source identity with `find` and `changeStream` privileges on the required resource. Use a separate identity for downstream writes. Never broaden to cluster-wide permissions just to resolve a collection-level authorization error.

Record server version, FCV, topology, driver version, source namespace, pipeline version, options, downstream contract and checkpoint owner. Connect with a replica-set-aware URI and approved TLS settings. Supply secrets through your normal secret mechanism.

## 3. Event fields and tokens

Inspect actual events rather than assuming every operation has the same shape. Typical fields include `_id`, `operationType`, `ns`, `documentKey` and `clusterTime`; payload fields vary by operation.[3]

The event `_id` is the resume token, not the source document ID. Preserve its BSON representation. Treat it as an opaque position: do not parse it into a home-grown offset, sort token strings, truncate it, or invent a timestamp-based substitute.

The driver also exposes a resume token through the stream object. An idle poll can advance that token without returning a business event.[2] This is useful for keeping an idle consumer's durable position current, provided all preceding events have been acknowledged.

Store a checkpoint envelope with:

```json
{
  "schema_version": 1,
  "contract_id": "mongodb_enterprise_tutorial_ch64.orders.v1",
  "token": {"_data": "OPAQUE_SERVER_VALUE"},
  "saved_at": "UTC_TIME"
}
```

The illustration is not a usable token. Include deployment identity and an immutable scope/options fingerprint in a production checkpoint. Reject mismatches at startup.

## 4. Resume choices

| Option | Intended use | Recovery caution |
|---|---|---|
| `resumeAfter` / `resume_after` | Continue after a saved position | History must still exist |
| `startAfter` / `start_after` | Open after a position, including an invalidate event | Does not recover expired history |
| `startAtOperationTime` / `start_at_operation_time` | Start from a BSON timestamp | Requires retained history and deliberate boundary handling |

Use one start option. Preserve the original scope, pipeline and relevant options when resuming. `resumeAfter` cannot resume after invalidation; `startAfter` can create a new stream after invalidation.[1]

A source drop or recreation is a data-contract change. Do not interpret successful `startAfter` as proof that the old and new collections have equivalent contents.

## 5. The acknowledgement rule

**Persist a restart position only after every event preceding it is durably handled.**

| Crash boundary | Restart behavior | Required protection |
|---|---|---|
| Before sink write | Event is read again | Preserve old checkpoint |
| After sink write, before checkpoint | Event can replay | Idempotent sink |
| After checkpoint | Continue after acknowledged event | Durable checkpoint |
| Checkpoint before sink write | Event can be skipped | Forbidden ordering |

This is an application design rule. Change streams alone do not make a cross-system pipeline exactly once. A driver reconnect cannot resolve an application crash between two independent durable writes.

When the sink and checkpoint share one transactional store, consider committing event acceptance and offset together. Otherwise design for replay. For parallel workers, advance only across a contiguous acknowledged prefix; the fastest completed worker must not checkpoint past unfinished work.

## 6. Payload strategy

Decide whether downstream consumers need an event ledger, current document state, exact event-time images, or field-level deltas.

| Strategy | Suitable purpose | Operational concern |
|---|---|---|
| Preserve change event | Durable CDC inbox | Separate materializer required |
| Apply update descriptions | State reconstruction | Nested fields, arrays and removed fields need correct handling |
| Full-document lookup | Current-state projection | Extra source reads; null or later state possible |
| Pre/post images | Before/after requirements | Enablement, retention, storage and missing-image policy |

`fullDocument: "updateLookup"` can return a later majority-committed document, rather than the exact document at the triggering update.[1] Therefore this lab preserves raw events rather than using lookup output to claim exact historical reconstruction.

Define delete handling explicitly: a delete needs a downstream tombstone or removal path based on the document key. Filters that only inspect `fullDocument` can accidentally exclude deletes. Keep lifecycle events observable.

## 7. Prepare the retained cluster and owned fixture

Select the accepted Chapter 60/62 replica set. Record its retained ownership ID, set name, healthy members, Enterprise version, FCV and certificate identities. `RUN64` owns only the separate Chapter 64 fixture; it must not replace the retained cluster ownership ID. Verify the reviewed target through its supported management workflow before granting access or writing.

Create a separate application identity with `find` and `changeStream` privileges on the Chapter 64 database. Use an owner identity for fixture initialization and a diagnostic identity for cluster/FCV evidence. The consumer does not need source write or drop privileges. Retain the Chapter 63 database untouched.

```bash
umask 077
mkdir mongodb-ch64
cd mongodb-ch64
mkdir scripts evidence private
export RUN64="$(python3 -c 'import uuid; print(uuid.uuid4())')"
printf '%s\n' "$RUN64" > evidence/run64.txt
python3 -m venv .venv
. .venv/bin/activate
: "${PYMONGO64_VERSION:?pin a reviewed compatible synchronous PyMongo 4.x release}"
python3 -m pip install "pymongo==$PYMONGO64_VERSION"
python3 -m pip freeze > evidence/client-packages64.txt
python3 -c 'import sys, pymongo; print(sys.version); print(pymongo.version)' > evidence/client-runtime64.txt
```

Set `URI64` to a credential-free `mongodb://` seed-list URI with only the reviewed `replicaSet` query option. Set `APP64_USER`, `APP64_AUTHDB` and `CA64_FILE`. The consumer prompts for the SCRAM password and verifies certificates. Keep secrets out of arguments and evidence. This executable lab does not cover SRV, x509, async drivers or mongos; those require an adapted and separately accepted client factory.

For Windows, run the Bash setup in an approved Bash environment or translate it to PowerShell, preserving the same variables, directories and secret handling. Do not substitute a standalone localhost source to bypass the retained TLS baseline.

Connect mongosh as the reviewed fixture owner using a password prompt and certificate verification:

```bash
mongosh "$URI64" --tls --tlsCAFile "$CA64_FILE" \
  --username "$OWNER64_USER" --authenticationDatabase "$OWNER64_AUTHDB" --password
```

In mongosh, confirm `hello` identifies the reviewed writable replica set. Use your separate diagnostic identity to capture Enterprise version/FCV and member health where the fixture owner lacks those privileges. Initialize only a new fixture:

```javascript
const expectedSet = process.env.SET64;
const run64 = process.env.RUN64;
if (!expectedSet || !run64) throw new Error("SET64 and RUN64 required");
const hello64 = db.adminCommand({hello: 1});
if (hello64.setName !== expectedSet || !hello64.isWritablePrimary) {
  throw new Error("Reviewed writable replica set required");
}
const lab = db.getSiblingDB("mongodb_enterprise_tutorial_ch64");
if (lab.getCollectionNames().length !== 0) {
  throw new Error("New Chapter 64 database required; preserve existing data");
}
lab.markers.insertOne(
  {_id: "owner", chapter: 64, runId: run64},
  {writeConcern: {w: "majority", j: true, wtimeout: 3000}}
);
lab.createCollection("orders");
```

Set `SET64` to the reviewed actual set name before connecting; it must agree with the URI. Keep `RUN64` and the initialized fixture across every restart. The marker lives outside the watched collection, so it does not pollute event counts. The empty initial collection is deliberate: a watch does not emit a snapshot of existing documents.

## 8. Durable event consumer

Save this as `scripts/cdc_consumer.py`. The source watch API and option names follow PyMongo documentation.[2] The SQLite inbox, checkpoint envelope and injected failure are original lab implementation choices.

```python
import os
import getpass
import urllib.parse
import sqlite3
from datetime import datetime, timezone

from bson import json_util
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from pymongo.read_concern import ReadConcern

CONTRACT = "mongodb_enterprise_tutorial_ch64.orders.raw-events.v1"
CANONICAL = json_util.CANONICAL_JSON_OPTIONS

def encode(value):
    return json_util.dumps(value, json_options=CANONICAL, sort_keys=True)

def now():
    return datetime.now(timezone.utc).isoformat()

def main():
    # One consumer process per inbox. SQLite is a local lab store,
    # not a distributed checkpoint service.
    run_id = os.environ["RUN64"]
    uri = os.environ["URI64"]
    parsed = urllib.parse.urlsplit(uri)
    query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    if not (parsed.scheme == "mongodb" and parsed.netloc
            and parsed.username is None and parsed.password is None
            and parsed.path in ("", "/") and not parsed.fragment
            and set(query) == {"replicaSet"}
            and len(query["replicaSet"]) == 1 and query["replicaSet"][0]):
        raise ValueError("Credential-free replicaSet-only URI required")
    set_name = query["replicaSet"][0]
    if set_name != os.environ["SET64"]:
        raise ValueError("Reviewed set name differs")
    contract = {"id": CONTRACT, "runId": run_id, "setName": set_name,
                "scope": "collection", "pipeline": [], "optionsVersion": 1}
    sink = sqlite3.connect("private/cdc_inbox.sqlite")
    sink.execute("PRAGMA journal_mode=WAL")
    sink.execute("PRAGMA synchronous=FULL")
    sink.executescript("""
        CREATE TABLE IF NOT EXISTS events (
            token TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            received_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS checkpoint (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            envelope TEXT NOT NULL
        );
    """)
    row = sink.execute(
        "SELECT envelope FROM checkpoint WHERE id = 1"
    ).fetchone()
    saved = json_util.loads(row[0]) if row else None
    if saved and saved["contract"] != contract:
        raise RuntimeError("Checkpoint contract mismatch; refuse startup")

    def checkpoint(token):
        envelope = {
            "schema_version": 1,
            "contract": contract,
            "token": token,
            "saved_at": now(),
        }
        with sink:
            sink.execute(
                "INSERT INTO checkpoint VALUES (1, ?) "
                "ON CONFLICT(id) DO UPDATE SET envelope=excluded.envelope",
                (encode(envelope),),
            )

    options = {"max_await_time_ms": 1000, "batch_size": 100}
    if saved:
        options["resume_after"] = saved["token"]

    client = MongoClient(
        uri, username=os.environ["APP64_USER"],
        password=getpass.getpass("Chapter 64 application password: "),
        authSource=os.environ["APP64_AUTHDB"],
        tls=True, tlsCAFile=os.environ["CA64_FILE"],
        appname="chapter64-cdc-lab",
        serverSelectionTimeoutMS=10000,
        connectTimeoutMS=3000,
        socketTimeoutMS=10000,
    )
    try:
        client.admin.command("ping")
        hello = client.admin.command("hello")
        if hello.get("setName") != set_name or not hello.get("isWritablePrimary"):
            raise ValueError("Reviewed writable replica set required")
        source = client.get_database("mongodb_enterprise_tutorial_ch64",
                                     read_concern=ReadConcern("majority"))
        owner = source.markers.find_one({"_id": "owner"})
        if owner != {"_id": "owner", "chapter": 64, "runId": run_id}:
            raise ValueError("Fixture ownership differs")
        with source.orders.watch(**options) as stream:
            print("READY: watch open", flush=True)
            while stream.alive:
                event = stream.try_next()
                if event is not None:
                    key = encode(event["_id"])
                    with sink:
                        cursor = sink.execute(
                            "INSERT OR IGNORE INTO events VALUES (?, ?, ?)",
                            (key, encode(event), now()),
                        )
                    inserted = cursor.rowcount == 1
                    print(event["operationType"],
                          "accepted" if inserted else "replay-deduplicated",
                          flush=True)
                    # Deliberately crash AFTER durable acceptance and BEFORE
                    # checkpointing, only for a newly accepted event.
                    if inserted and os.getenv("CRASH_AFTER_SINK") == "1":
                        os._exit(42)
                    if event["operationType"] == "invalidate":
                        print("STOP: source invalidated; review lifecycle",
                              flush=True)
                        # Do not store an invalidate token as resume_after.
                        return 3

                # Safe here: sequential processing and committed sink writes.
                # With buffered/parallel work, this rule needs redesign.
                token = stream.resume_token
                if token is not None:
                    checkpoint(token)
    except KeyboardInterrupt:
        print("Stopped by operator", flush=True)
        return 0
    except PyMongoError as exc:
        # Driver handles its supported resumable cases. Surface remaining
        # errors for operator classification; never reset offsets to 'now'.
        print("STOP:", type(exc).__name__,
              "code=", getattr(exc, "code", None), flush=True)
        return 2
    finally:
        client.close()
        sink.close()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

The lab trades two transactions per event for visible replay. This is intentionally inefficient. A production implementation can transactionally combine inbox acceptance with checkpointing, batch commits, and use a shared store with fencing. Keep the correctness invariant unchanged.

The loop checkpoints idle polls to demonstrate high-watermark handling. In production, throttle unchanged token writes and measure checkpoint-store load. Stop immediately if checkpoint persistence fails.

## 9. Lab A — Observe CRUD events

Terminal A:

```bash
python3 scripts/cdc_consumer.py
```

Wait for `READY: watch open`. In Terminal B, mongosh:

```javascript
const lab = db.getSiblingDB("mongodb_enterprise_tutorial_ch64");
lab.orders.insertOne(
  {_id: "order-6401", status: "new", amount: 100},
  {writeConcern: {w: "majority"}}
);
lab.orders.updateOne(
  {_id: "order-6401"}, {$set: {status: "paid"}},
  {writeConcern: {w: "majority"}}
);
lab.orders.replaceOne(
  {_id: "order-6401"},
  {_id: "order-6401", status: "shipped", amount: 100},
  {writeConcern: {w: "majority"}}
);
lab.orders.deleteOne(
  {_id: "order-6401"}, {writeConcern: {w: "majority"}}
);
```

Expected: four accepted CRUD events on a fresh lab. Inspect actual operation types; MongoDB can represent some writes as replace events depending on the operation. Inspect the inbox with this separate script, `scripts/inspect_inbox.py`:

```python
import sqlite3
from bson import json_util

with sqlite3.connect("private/cdc_inbox.sqlite") as con:
    rows = con.execute(
        "SELECT payload FROM events ORDER BY rowid"
    ).fetchall()
    print("durable_events=", len(rows))
    for (payload,) in rows:
        event = json_util.loads(payload)
        print(event["operationType"], event.get("documentKey"),
              event.get("updateDescription"))
    saved = con.execute(
        "SELECT envelope FROM checkpoint WHERE id=1"
    ).fetchone()
    print("checkpoint_exists=", saved is not None)
```

```bash
python3 scripts/inspect_inbox.py
```

Acceptance: event tokens differ from source document IDs; delete retains document-key evidence; the checkpoint exists. Do not print full production events or tokens into broadly accessible logs.

## 10. Lab B — Restart with retained history

1. Stop Terminal A with Ctrl+C after processing the four events.
2. While the consumer is stopped, insert a new source document:

```javascript
db.getSiblingDB("mongodb_enterprise_tutorial_ch64").orders.insertOne(
  {_id: "order-6402", status: "new", amount: 200},
  {writeConcern: {w: "majority"}}
);
```

3. Restart `python3 scripts/cdc_consumer.py` using the same working directory.
4. Run `python3 scripts/inspect_inbox.py`.

Expected: the stopped-period insert is accepted; on a fresh sequential run, the inbox grows from four to five events. If it does not, check working directory, checkpoint contents, source URI and error output before blaming the source.

## 11. Lab C — Crash after sink acceptance

First stop the consumer cleanly. Keep the existing checkpoint and inbox.

Linux/macOS Terminal A:

```bash
CRASH_AFTER_SINK=1 python3 scripts/cdc_consumer.py
```

PowerShell Terminal A:

```powershell
$env:CRASH_AFTER_SINK = '1'
python3 scripts/cdc_consumer.py
```

After `READY`, insert in Terminal B:

```javascript
db.getSiblingDB("mongodb_enterprise_tutorial_ch64").orders.insertOne(
  {_id: "order-6403", status: "new", amount: 300},
  {writeConcern: {w: "majority"}}
);
```

Expected: process exits with code 42 after committing the event. The checkpoint still precedes that event.

Restart without failure injection:

```bash
python3 scripts/cdc_consumer.py
```

PowerShell:

```powershell
Remove-Item Env:CRASH_AFTER_SINK
python3 scripts/cdc_consumer.py
```

Expected: `insert replay-deduplicated`. The inbox remains at six distinct events for this exact lab sequence, then checkpointing advances. Replaying the event did not produce an additional row because its event token is the inbox primary key.

This proves event-inbox idempotency, not arbitrary business-action idempotency. Sending email or charging a card requires its own durable idempotency mechanism. Retain deduplication records for the entire allowed replay period.

## 12. Optional interruption and lifecycle exercises

### D — Temporary outage or election

Only after the required lab passes, use Chapter 28’s separately reviewed maintenance procedure with healthy electable secondaries and a maintenance identity. A network interruption requires its own bounded reviewed procedure. Never stop nodes or change networking just to satisfy required Chapter 64 acceptance. Keep writing a numbered sequence of test records before and after the interruption.

Record interruption start, database recovery time, consumer recovery time, errors, distinct inbox counts and missing IDs. A supported driver may recover internally; if it exits, restart from the saved checkpoint after restoring connectivity. Do not delete checkpoint state.

Acceptance: every acknowledged source test write reaches the inbox, duplicates do not increase distinct event count, and the consumer never silently starts at the current time. A single-member lab cannot demonstrate redundant-node failover.

### E — Lifecycle invalidation (optional destructive fixture test)

Perform only after completing the required drills, separately reviewing the fixture retirement and verifying the owner marker matches `RUN64`. Dropping the source destroys lab data and invalidates the collection watch.

```javascript
db.getSiblingDB("mongodb_enterprise_tutorial_ch64").orders.drop();
```

Expected: observe lifecycle events and the script's invalidation stop. The script deliberately requires operator review rather than automatically attaching to a replacement collection.

For a separate lifecycle exercise, capture the actual invalidate token and open a new watch with `start_after` using a reviewed contract. Do not reuse that token with `resume_after`. Recreating the collection does not rebuild a downstream dataset or recover deleted source state.

## 13. Expired history and rebuild

A resume token is not a backup. When required oplog history is gone, repeated retries cannot recreate the missing changes.

Do not force oplog rollover in a shared environment. An optional isolated drill can generate bounded writes until a saved position is older than the retained history; monitor disk and restore lab configuration afterward. Exact rollover timing depends on write volume and retention configuration.

Recovery runbook:

1. Stop advancement and preserve the failed checkpoint, error, contract and source identity.
2. Determine which downstream interval is incomplete and block freshness/completeness claims.
3. Choose a supported connector rebootstrap, consistent backfill plus buffered CDC, or paused-writer rebuild.
4. Build into a separate downstream generation.
5. Reconcile keys, deletes, counts and business aggregates at a defined boundary.
6. Drain changes, establish a new durable checkpoint and switch readers after validation.
7. Retain the prior generation for rollback according to policy.

Do not automatically remove the checkpoint and call `watch()` with no start option. That can restore apparent liveness while permanently skipping the missing interval.

### Snapshot plus CDC without a gap

Unsafe sequence: scan the source, then open a stream. Writes between those steps can be absent from both datasets.

For a low-complexity operational rebuild, pause and drain writers, establish a stream boundary while paused, capture the source dataset, finish loading the sink, then resume writes and apply buffered changes. Document outage duration and ensure oplog coverage for the entire process.

For an online rebuild, use a connector or design that explicitly coordinates snapshot boundaries, change buffering, merge ordering and deletes. Opening a stream before a non-transactional scan avoids one gap but introduces overlap: replaying an old event over a newer scanned document can regress state. A correct design needs consistent snapshot semantics or per-key/version reconciliation.

A timestamp alone does not prove correctness. Retained history, boundary inclusion, concurrent writes, delete handling and cutover validation must all be demonstrated.

## 14. Oplog and retention headroom

Measure the actual retained time window, especially during peak writes. With an appropriate monitoring identity:

```javascript
rs.printReplicationInfo()
```

In a sharded deployment, assess each shard through approved monitoring paths. The most constrained relevant shard can limit recovery.

Engineering planning rule:

```text
required history > tolerated consumer outage
                 + detection and repair time
                 + catch-up time
                 + operational margin
```

Example: a 4-hour outage budget, 1-hour repair, 2-hour catch-up and 1-hour margin require more than 8 hours of demonstrated peak-load history. This is a planning example, not a MongoDB default or universal threshold.

If backlog is 1.2 million events, arrival is 2,000 events/s and sustainable processing is 3,000 events/s, net drain is 1,000 events/s and ideal catch-up is about 20 minutes. If processing does not exceed arrival, the backlog cannot drain. Validate with observed throughput, retries and sink constraints.

### Observability and alerting

| Signal | Operational interpretation | Action |
|---|---|---|
| Last successful poll | Connectivity/liveness | Investigate prolonged silence |
| Last acknowledged event | Business progress on active sources | Compare with source activity |
| Durable checkpoint age | Restart-position health | Check checkpoint failures |
| Source-to-inbox latency | Ingestion delay | Inspect consumer and source |
| Inbox-to-materialized latency | Downstream delay | Inspect sink jobs |
| Retention headroom | Time left before recovery becomes uncertain | Escalate before exhaustion |
| Replay/deduplication rate | Retry or crash activity | Inspect recovery loops |
| Queue size and oldest age | Backpressure | Bound buffers and repair bottleneck |
| Resume/lifecycle errors | Possible completeness interruption | Classify and stop unsafe advancement |

Idle source event age is not sufficient evidence of failure. Use successful polls, durable idle tokens and a controlled synthetic heartbeat where appropriate. Keep heartbeat writes outside business transformations and account for their source cost.

Use event timestamps for approximate latency, with synchronized clocks. Do not assign precise lag to opaque tokens using undocumented decoding logic. Establish service-specific SLOs for freshness, maximum restart age and reconciliation completeness.

## 15. Troubleshooting

| Symptom | Check first | Response |
|---|---|---|
| Watch unsupported | Topology and collection type | Use supported deployment/source |
| Authorization failure | Resource-scoped find/changeStream privileges | Correct role; avoid blanket admin |
| No events | Source URI, scope, writes, filter, readiness | Produce one controlled lab write |
| Duplicate delivery | Crash boundary and sink acknowledgement | Use durable idempotency |
| Missing stopped-period changes | Start option and checkpoint directory | Preserve evidence; reconcile gap |
| Resume failure | History, lifecycle, contract/version changes | Classify before retry |
| Null lookup document | Concurrent deletes and lookup strategy | Apply reviewed tombstone/reconciliation policy |
| Consumer memory growth | Sink throughput and unbounded buffering | Bound queue; stop unsafe checkpoints |
| High source load | Stream count, broad scope, document lookups | Profile and reduce unnecessary work |
| Checkpoint mismatch | Namespace, deployment, pipeline version | Refuse reuse; migrate deliberately |

Do not classify every `OperationFailure` as history loss. Record the actual code, labels and redacted message. Permissions, unsupported options and invalid pipelines need different fixes. Exhausted resumable recovery should use bounded backoff and jitter, plus alerting; permanent failures should not loop forever.

### Production design review

- One fenced owner per logical checkpoint, or an explicitly coordinated partitioning scheme.
- Per-key ordering preserved where downstream state depends on order.
- Durable checkpoint store survives pod replacement; local container files do not suffice.
- Stream contract and source deployment identity verified before resume.
- Filtered events and deletes handled according to a written contract.
- Poison events block advancement or move to a durable, auditable recovery path.
- Event acceptance and downstream application measured separately.
- Retention coverage tested under peak load and extended outages.
- Snapshot/rebuild and reconciliation procedures exercised.
- Event payloads protected with encryption, access control and retention limits.

For Kubernetes, avoid restarting every consumer merely because the sink is temporarily slow. Readiness, liveness and freshness represent different conditions. Restart storms can amplify replay and pool pressure.

## 16. Acceptance record

| Test | Required evidence | Result |
|---|---|---|
| Topology readiness | Supported source and versions recorded | PASS / FAIL |
| CRUD capture | Four operations observed in fresh lab | PASS / FAIL |
| Restart catch-up | Stopped-period write captured | PASS / FAIL |
| Crash/replay | Exit 42, duplicate suppressed, checkpoint advances | PASS / FAIL |
| Interruption | Numbered source writes reconciled | PASS / FAIL / NOT RUN |
| Lifecycle (optional) | Invalidation surfaced without silent continuation | PASS / FAIL / NOT RUN |
| History loss plan | Rebuild and reconciliation owners named | PASS / FAIL |
| Bootstrap review | Gap and overlap handling explained | PASS / FAIL |
| Observability | Liveness, durability and materialization separated | PASS / FAIL |

Attach redacted event metadata, counts, checkpoint-save times, version evidence, errors and recovery durations. Do not mark unexecuted drills PASS.

### Cleanup

Stop all consumer processes. Remove the failure-injection environment variable. Verify the fixture owner marker and retained cluster identity before any retirement. If the source collection still exists, drop only `mongodb_enterprise_tutorial_ch64.orders` after retaining lab evidence. Delete local SQLite inbox/WAL/SHM files only after the connection is closed and the lab results are recorded. Do not drop the entire database if other exercises use it.

### Review questions

1. Why is saving the read position before sink acknowledgement unsafe?
2. Which crash boundary causes replay, and what makes replay safe?
3. Why does an idle source need liveness evidence beyond event age?
4. Why can a valid token become unusable after a long outage?
5. Why does `startAfter` not repair an expired-history gap?
6. Why can an online snapshot plus buffered changes still regress state?
7. What additional evidence is needed to claim downstream materialization?

**Answer guide:** acknowledgement ordering; durable event/business idempotency; successful polls and safe idle checkpointing; finite retained history; lifecycle continuation differs from history recovery; snapshot overlap and per-key ordering; sink application position and reconciliation.

## 17. References and validation status

1. [MongoDB Manual — Change Streams](https://www.mongodb.com/docs/manual/changestreams/): topology, scope, resume behavior, lifecycle and document lookup. Select the documentation version matching your deployment.
2. [PyMongo — Monitor Data with Change Streams](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/monitoring-and-logging/change-streams/): watch API, options and driver token handling.
3. [MongoDB Manual — Change Stream Events](https://www.mongodb.com/docs/manual/reference/change-events/): operation-specific event schemas.

Documentation reviewed on 2026-10-11. The checkpoint ordering, SQLite inbox, drills, capacity examples and acceptance criteria are operational teaching designs. Python blocks were syntax-checked during authoring. A mocked-driver test using actual SQLite verified the acceptance-before-checkpoint crash boundary, restart token selection, replay deduplication, idle checkpoint advancement and contract mismatch rejection. These checks do not validate BSON round trips, actual server tokens, TLS, driver reconnection or live change delivery. Live MongoDB drills were not executed in the authoring environment; execute the acceptance lab on your retained authorized replica set before adopting the pattern.

**Chapter completion:** Written; static syntax and mocked-consumer/SQLite checks complete. Runtime acceptance remains pending until the retained pinned-driver lab is executed and its evidence recorded.

Previous: [Chapter 63 — Drivers Connection Pools Timeouts and Retries](63-drivers-connection-pools-timeouts-and-retries.md).

Next: [Chapter 65 — Time Series Collections and Retention](65-time-series-collections-and-retention.md).
