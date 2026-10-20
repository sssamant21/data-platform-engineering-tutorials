# 16 — Transactions Sessions and Retry Semantics

**Status:** Written; static review complete; runtime lab validation pending  
**Part:** 2 — Data Modeling and Application Development  
**Goal:** Execute an atomic transfer, demonstrate abort and isolation, and distinguish transaction retries from commit retries.  
**Audience:** Developers, Data Engineers, DBREs and SREs  
**Time:** 75–105 minutes  
**Baseline:** MongoDB 8.0 and mongosh; record exact server and shell versions.  
**Deployment:** Community-compatible replica set or sharded cluster. Standalone servers do not support this transaction lab.

## 1. Choose the smallest consistency boundary

A single-document update is atomic. Embedding related state can often satisfy an invariant with one conditional update. A multi-document transaction is useful when the invariant crosses documents or collections and partial completion is unacceptable.

This chapter transfers synthetic account points between two documents and records a ledger event. The required invariant is: both account balances and the ledger change together, or none change. A ledger identifier also prevents a caller from applying the same business event twice.

Transactions do not remove the need for schema design, indexes, bounded work or application error handling. They consume resources and can encounter write conflicts. Keep the business boundary small; do not use a transaction to hide an unbounded batch.

A session provides context for operations. Starting a session does not start a transaction. A session may have at most one open transaction at a time. The server begins transaction work on its first operation, rather than when the shell calls startTransaction.

## 2. Separate atomicity, durability and caller knowledge

| Concern | Mechanism in this lab | Limit |
|---|---|---|
| Atomic account and ledger changes | Multi-document transaction | External services are outside this boundary |
| Consistent transaction reads | Snapshot read concern | The snapshot can become stale relative to concurrent writers |
| Commit acknowledgement | Majority write concern | A one-member lab does not demonstrate redundant durability |
| Business duplicate protection | Unique ledger _id | Identifier reuse must also validate the payload |
| Uncertain commit outcome | Commit retry and reconciliation design | A network error does not prove the transaction failed |

Transaction read preference must be primary. Set transaction write concern on the transaction; do not attach separate write concern to individual operations inside it. In this lab, write concern applies to commit and abort. A write-concern timeout does not establish that nothing committed.

Use deployment defaults deliberately. The options below make the teaching contract explicit; production values require workload and availability requirements.

## 3. Prerequisites and connection context

Complete Chapters 05–06 and 12. Use a disposable replica set or a training deployment where you can create, read, update and drop this chapter's database. A user limited to the chapter database should not need cluster administration privileges for the transfer exercises.

For an existing replica set, use its approved primary-capable connection URI and authentication. Do not initiate or reconfigure an existing deployment. For a sharded deployment, connect through mongos and follow its transaction prerequisites.

Optional isolated local lab, with Docker installed:

```bash
docker run --name mongodb-ch16 --detach \
  --publish 127.0.0.1:27046:27017 \
  --memory 2g \
  mongo:8.0 \
  --replSet rs16 --bind_ip_all --wiredTigerCacheSizeGB 0.5

docker exec -it mongodb-ch16 mongosh \
  "mongodb://localhost:27017/?directConnection=true"
```

The container has no authentication and exposes a loopback-only host port. It is a disposable teaching environment. Pin an exact image tag or digest for repeatable evidence. The client commands below run inside the container, where the advertised localhost:27017 member address is reachable. A host client on port 27046 would need a different discovery/address design.

In mongosh, only for the newly created container:

```javascript
rs.initiate({
  _id: "rs16",
  members: [{ _id: 0, host: "localhost:27017" }]
});

const primaryDeadline16 = Date.now() + 30000;
while (!db.adminCommand({ hello: 1 }).isWritablePrimary &&
       Date.now() < primaryDeadline16) {
  sleep(250);
}
if (!db.adminCommand({ hello: 1 }).isWritablePrimary) {
  throw new Error("Primary election did not finish within 30 seconds");
}
```

Do not run rs.initiate on Atlas or an existing replica set. One member is sufficient to teach transactions; it does not validate failover or redundancy. Chapters 25–32 cover replica-set operations.

For either connection, record:

```javascript
const hello16 = db.adminCommand({ hello: 1 });
printjson({
  serverVersion: db.version(),
  replicaSet: hello16.setName || null,
  mongos: hello16.msg === "isdbgrid",
  writablePrimary: hello16.isWritablePrimary
});
if (!hello16.setName && hello16.msg !== "isdbgrid") {
  throw new Error("Use a replica set or mongos; this is a standalone server");
}
if (!hello16.isWritablePrimary) {
  throw new Error("Connect to the primary or mongos before continuing");
}
```

Record mongosh --version from the shell as well. Server version and shell version are separate.

## 4. Create an explicit fixture

All remaining JavaScript runs in the same mongosh connection. The lab uses integer points, not financial accounting or a currency rounding policy.

```javascript
const labName16 = "mongodb_enterprise_tutorial_ch16";
const lab16 = db.getSiblingDB(labName16);
if (lab16.getCollectionNames().length !== 0) {
  throw new Error("Chapter database already exists; review it before resetting");
}
lab16.createCollection("accounts");
lab16.createCollection("ledger");
lab16.accounts.insertMany([
  { _id: "A", balance: Int32(100) },
  { _id: "B", balance: Int32(50) }
]);

function check16(condition, message) {
  if (!condition) throw new Error(message);
}
function balance16(account) {
  const found = lab16.accounts.findOne({ _id: account });
  if (!found) throw new Error("Missing account " + account);
  return Number(found.balance);
}
function assertState16(a, b, events) {
  check16(balance16("A") === a, "Unexpected A balance");
  check16(balance16("B") === b, "Unexpected B balance");
  check16(balance16("A") + balance16("B") === 150, "Point total changed");
  check16(lab16.ledger.countDocuments({}) === events, "Unexpected event count");
}
assertState16(100, 50, 0);
```

Precreating collections avoids making collection-creation compatibility part of this transaction lesson. The existing unique _id index on ledger supplies event identity.

## 5. Implement the transfer boundary

The function validates input, starts a transaction, checks any existing event, records the new event, conditionally debits the source and credits the destination. Any business failure before commit aborts the changes.

This is an explicit mongosh session example. It does not implement a production driver's complete transaction retry helper. A commit error is surfaced as uncertain and must be handled separately from a body failure.

```javascript
const session16 = db.getMongo().startSession({ causalConsistency: false });
const tx16 = session16.getDatabase(labName16);
const options16 = {
  readConcern: { level: "snapshot" },
  writeConcern: { w: "majority", wtimeout: 5000 }
};

function transfer16(eventId, from, to, amount) {
  if (typeof eventId !== "string" || eventId.length === 0 ||
      typeof from !== "string" || typeof to !== "string" ||
      from === to || !Number.isSafeInteger(amount) ||
      amount <= 0 || amount > 2147483647) {
    throw new Error("Invalid transfer input");
  }

  session16.startTransaction(options16);
  let phase = "body";
  let result;
  try {
    const existing = tx16.ledger.findOne({ _id: eventId });
    if (existing) {
      if (existing.from !== from || existing.to !== to ||
          Number(existing.amount) !== amount) {
        throw new Error("Event identifier reused with a different payload");
      }
      result = "already-applied";
    } else {
      tx16.ledger.insertOne({
        _id: eventId, from, to, amount: Int32(amount)
      });
      const debit = tx16.accounts.updateOne(
        { _id: from, balance: { $gte: amount } },
        { $inc: { balance: -amount } }
      );
      if (debit.modifiedCount !== 1) {
        throw new Error("Source missing or insufficient balance");
      }
      const credit = tx16.accounts.updateOne(
        { _id: to },
        { $inc: { balance: amount } }
      );
      if (credit.modifiedCount !== 1) {
        throw new Error("Destination account missing");
      }
      result = "applied";
    }
    phase = "commit";
    session16.commitTransaction();
    return result;
  } catch (error) {
    if (phase === "body") {
      try { session16.abortTransaction(); } catch (abortError) {
        print("Abort did not acknowledge: " + abortError.message);
      }
    } else {
      printjson({
        phase: "commit",
        outcome: "Requires commit retry or reconciliation",
        labels: error.errorLabels || [],
        message: error.message
      });
    }
    throw error;
  }
}
```

Do not translate every caught error into “transfer failed.” Once commit has been attempted, the caller may not know the outcome. The lab stops on unexpected commit errors; do not continue using the session until you resolve that outcome.

The replay check compares the whole business payload. Matching an identifier alone would silently accept a conflicting request. Concurrent callers can still race and encounter conflicts or duplicate-key errors; the unique index prevents duplicate ledger identity, while a production implementation needs tested retry/reconciliation behavior.

## 6. Successful commit and sequential replay

```javascript
check16(transfer16("T1", "A", "B", 10) === "applied", "First transfer failed");
assertState16(90, 60, 1);
check16(transfer16("T1", "A", "B", 10) === "already-applied",
        "Replay was not identified");
assertState16(90, 60, 1);
printjson(lab16.accounts.find().sort({ _id: 1 }).toArray());
printjson(lab16.ledger.find().toArray());
```

Expected balances are A=90 and B=60. The ledger contains one T1 event with amount 10. Replaying the same request produces no second debit.

Reject conflicting identity:

```javascript
let conflicting16 = false;
try {
  transfer16("T1", "A", "B", 11);
} catch (error) {
  conflicting16 = error.message.includes("different payload");
  print(error.message);
}
check16(conflicting16, "Conflicting replay was not rejected");
assertState16(90, 60, 1);
```

This proves sequential replay behavior against the fixture. It does not prove concurrent retry behavior or recovery from network loss.

## 7. Failure exercise: abort after a debit

Use a destination that does not exist. The function inserts a ledger event and debits A before discovering the missing destination. Aborting must remove both intermediate changes.

```javascript
let missingDestination16 = false;
try {
  transfer16("T-missing", "A", "Z", 5);
} catch (error) {
  missingDestination16 = error.message.includes("Destination account missing");
  print(error.message);
}
check16(missingDestination16, "Expected missing-destination failure");
assertState16(90, 60, 1);
check16(lab16.ledger.findOne({ _id: "T-missing" }) === null,
        "Aborted ledger event survived");

let insufficient16 = false;
try {
  transfer16("T-insufficient", "A", "B", 200);
} catch (error) {
  insufficient16 = error.message.includes("insufficient balance");
}
check16(insufficient16, "Expected insufficient-balance rejection");
assertState16(90, 60, 1);
```

Diagnosis: the business invariant cannot be satisfied. Correct the account identifier or available points; retrying unchanged business input does not repair it. The conditional debit avoids a separate read-then-debit race for available balance.

Capture the failure message and post-abort account/ledger state. If either changes, stop and investigate the connection/session handling.

## 8. Observe transaction-local visibility

Read an intermediate update through the transaction's database and through the ordinary connection. Then abort.

```javascript
session16.startTransaction(options16);
try {
  tx16.accounts.updateOne({ _id: "A" }, { $inc: { balance: -1 } });
  check16(Number(tx16.accounts.findOne({ _id: "A" }).balance) === 89,
          "Transaction did not see its own write");
  check16(balance16("A") === 90,
          "Ordinary reader observed uncommitted balance");
} finally {
  session16.abortTransaction();
}
assertState16(90, 60, 1);
```

Expected transaction-local balance is 89; the ordinary reader sees the committed value 90. This demonstrates the fixture's uncommitted visibility boundary. It is not a complete concurrency/isolation benchmark, and changing readers or read concerns requires separate analysis.

## 9. Retry the right unit of work

| Evidence | Appropriate response | Incorrect shortcut |
|---|---|---|
| TransientTransactionError | Restart the whole transaction with a fresh snapshot, subject to a bounded retry policy | Resume halfway through the body |
| UnknownTransactionCommitResult | Retry commit for the same transaction as the driver protocol requires | Immediately execute the transfer body again |
| Invalid input, missing destination, insufficient balance | Return a business rejection; change input/state before another attempt | Treat as a transient server failure |
| Identifier already exists with another payload | Reject conflicting identity | Return success merely because the identifier exists |
| Timeout or connection error without clear outcome | Inspect labels and reconcile using durable event identity | Assume absence of acknowledgement means absence of commit |

Use the selected driver's documented transaction API. For example, the Node.js convenient transaction API includes retry handling and may invoke its callback more than once. The explicit shell function above deliberately exposes the phase distinction instead of claiming to reproduce that helper.

Production callbacks must tolerate replay. Do not send emails, call payment services or publish irreversible external events directly inside a callback that may be rerun. A transactional outbox can record a pending event alongside application data; a separate publisher needs its own delivery and deduplication policy.

Bound attempts and elapsed time, use appropriate backoff, and surface exhausted retries with enough identity to reconcile. A retry policy must respect request deadlines. Do not run parallel operations within one transaction/session; follow the driver's supported usage.

The following is a classification exercise only. It does not inject a real server or network fault:

```javascript
function retryUnit16(error, phase) {
  const labels = new Set(error.errorLabels || []);
  if (phase === "commit" && labels.has("UnknownTransactionCommitResult")) {
    return "retry-same-commit";
  }
  if (labels.has("TransientTransactionError")) {
    return "restart-transaction";
  }
  return phase === "commit" ? "reconcile-outcome" : "inspect-or-reject";
}
check16(retryUnit16({
  errorLabels: ["UnknownTransactionCommitResult"]
}, "commit") === "retry-same-commit", "Wrong commit retry classification");
check16(retryUnit16({
  errorLabels: ["TransientTransactionError"]
}, "body") === "restart-transaction", "Wrong body retry classification");
check16(retryUnit16({
  message: "Destination account missing"
}, "body") === "inspect-or-reject", "Business failure marked retryable");
```

Later resilience labs must validate actual application behavior during elections, connectivity faults and lost acknowledgements. Do not label this chapter's synthetic classifier as failover testing.

## 10. Troubleshooting

| Symptom | Evidence to collect | Likely cause | Corrective action |
|---|---|---|---|
| Transaction numbers unsupported | hello response, connection URI shape | Standalone connection | Use an approved replica set or mongos |
| Primary requirement error | hello, read preference | Secondary connection/read preference | Use primary-capable routing |
| Missing destination abort | Ledger identity, matched/modified counts | Invalid business identifier | Correct input; verify no partial state |
| Write conflict | Error labels, concurrent operations | Another writer changed transaction state | Apply driver's bounded transaction retry policy |
| Commit acknowledgement lost | Phase, labels, event identifier | Network interruption or acknowledgement uncertainty | Follow commit retry protocol and reconcile |
| Transaction expires | Duration, operation count, server diagnostics | Transaction body too slow | Shorten boundary and remove external waits |
| Authorization failure | User roles, namespace, failing command | Insufficient database privileges | Grant only required training/app privileges |
| Replay conflicts | Existing ledger payload vs request | Identifier reused incorrectly | Reject conflict and repair identity generation |

Do not log credentials or complete sensitive documents. Record event IDs, operation phase, error codes/labels, duration and sanitized deployment context.

## 11. Production design and limits

- Index transaction filters so the boundary does not scan large collections. This fixture uses _id lookups.
- Keep point or money representation consistent. Real currency requires an explicit exact numeric and rounding policy; a JavaScript double is not that policy.
- Use stable caller-provided operation identity across retries. Decide retention carefully: deleting deduplication evidence can allow old requests to be applied again.
- Measure aborts, conflicts, retry counts, elapsed time and commit acknowledgement latency.
- A majority acknowledgement on a single-member replica set is not a high-availability guarantee.
- Consider collection/shard placement and supported operations before adopting cross-shard transactions.
- Resolve uncertain outcomes before reporting final business success/failure. A subsequent stale read can mislead reconciliation.
- Set application timeouts and pool limits coherently with retry budgets. Do not increase server transaction lifetime as the first response to slow application work.
- Benchmark realistic contention. This small fixture proves state assertions when run; it does not establish throughput or latency objectives.

## 12. Cleanup

End the session after all successful exercises and known aborts:

```javascript
session16.endSession();
assertState16(90, 60, 1);
if (lab16.getName() !== "mongodb_enterprise_tutorial_ch16") {
  throw new Error("Refusing cleanup outside the Chapter 16 training database");
}
const cleanupResult16 = lab16.dropDatabase();
if (!cleanupResult16.ok) throw new Error("Chapter 16 database cleanup failed");
```

If an unexpected commit error occurred, resolve its outcome before cleanup so evidence is not erased. Drop only this named training database.

For the optional disposable container, exit mongosh and run:

```bash
docker stop mongodb-ch16
docker rm --volumes mongodb-ch16
```

The volume option removes this container's anonymous volumes. No shared deployment or other lab containers are touched.

## 13. Acceptance and evidence

- [ ] Recorded exact server/shell versions and replica-set or mongos context.
- [ ] Initial A/B balances were 100/50 and ledger was empty.
- [ ] Committed T1 produced 90/60 and one ledger record.
- [ ] Identical replay changed no balances; conflicting replay was rejected.
- [ ] Missing destination and insufficient points aborted without partial state.
- [ ] Transaction saw its uncommitted balance while the ordinary reader saw the committed balance.
- [ ] Explained whole-transaction retry versus same-transaction commit retry.
- [ ] Captured sanitized output before ending the session and scoped cleanup.

**Evidence:** topology/version output, assertions, ledger document, failure messages, visibility results and cleanup outcome. Runtime validation remains pending until these commands are run on the stated deployment. Syntax review alone does not establish transactional behavior.

## 14. Review questions

1. Which invariant would let you replace this transaction with a single-document update?
2. Why is a stable ledger identifier necessary even when writes are atomic?
3. Why must a replay compare payload as well as identifier?
4. Which error means retry the whole transaction, and which means retry commit?
5. Why can an email inside a retried transaction callback be sent twice?
6. What does this one-member fixture fail to prove about durability and availability?
7. What evidence is needed before declaring an uncertain commit unsuccessful?

## 15. Official references

- [MongoDB 8.0: Session.startTransaction](https://www.mongodb.com/docs/v8.0/reference/method/Session.startTransaction/)
- [MongoDB 8.0: Session.commitTransaction](https://www.mongodb.com/docs/v8.0/reference/method/Session.commitTransaction/)
- [MongoDB 8.0: Session.abortTransaction](https://www.mongodb.com/docs/v8.0/reference/method/Session.abortTransaction/)
- [MongoDB 8.0: transaction production considerations](https://www.mongodb.com/docs/v8.0/core/transactions-production-consideration/)
- [Node.js driver: transactions and retry behavior](https://www.mongodb.com/docs/drivers/node/current/crud/transactions/)

---

Previous: [Chapter 15 — Pagination and API Query Design](15-pagination-and-api-query-design.md)  
Next: [Chapter 17 — Single Field and Compound Indexes](17-single-field-and-compound-indexes.md).
