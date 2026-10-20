# 50 — mongodump mongorestore and Logical Recovery

Part 7 — Backup Recovery and Disaster Recovery

**Baseline:** MongoDB 8.0; approved, separately versioned Database Tools.  
**Status:** Written; static review complete; live dump/restore validation pending.  
**Prerequisites:** Chapter 49 and the retained authenticated TLS standalone from Chapters 41–48.

## 1. Define the recovery claim

This lab creates deterministic customers and orders, takes a scoped logical backup while that fixture is idle, deletes twenty known orders, and restores the original dataset into a new database. It verifies documents, business totals, a unique index and collection validation before cleanup.

The retained `mongodb-ch41` server hosts both source and recovered namespaces. Namespace isolation is sufficient for this accidental-deletion exercise; it does **not** demonstrate recovery after host, storage, region or account loss. A production recovery drill needs a separately provisioned, isolated target and the complete Chapter 49 dependency set.

Do not run these commands against a production database. The guarded controller owns only this chapter's two named databases. It never restores over the source and never passes `--drop`.

## 2. Understand the logical backup boundary

Logical backup exports BSON documents with collection metadata and index definitions. Restore reconstructs the selected objects; index creation and document insertion consume CPU, storage and time. It does not reproduce the original physical layout or every deployment setting.

| Included in this lab | Outside this lab's artifact |
|---|---|
| Three ordinary collections and their documents | Server startup configuration, TLS keys and trust deployment |
| Collection options and index definitions | Storage-engine encryption keys and infrastructure |
| A run marker identifying the fixture | Database users/roles, because they are not requested |
| A verified idle source state | Writes performed after capture and arbitrary PITR history |

Do not substitute `mongoexport` JSON for a BSON backup contract. Do not assume field-encrypted or Queryable Encryption collections fit this workflow: current Tools documentation excludes these collections from `mongodump` support. Use a supported backup architecture for the exact encryption feature/version and preserve its key dependencies.

## 3. Choose a consistency strategy

| Source condition | Recovery design |
|---|---|
| Standalone or scoped database with all relevant writes stopped | Scoped dump, documented quiet interval and verified state |
| Independent replica set with supported writes during capture | Full `mongodump --oplog`, then full `mongorestore --oplogReplay` |
| Selective collection/database recovery | Restore a reviewed consistent scoped artifact into a fresh namespace |
| Sharded cluster | Coordinated release-specific backup procedure; Chapters 52/55 |

Without an appropriate consistency mechanism, different collections can reflect different times. Stopping just one writer while jobs, TTL expiration or other administrators continue to mutate the scope is insufficient. This lab has no TTL index and no background application writer; only the controller changes its fixture. Maintain that quiet boundary through dump completion and the post-dump baseline check.

The standalone has no replica-set oplog. Do not add `--oplog` to this lab's commands. A scoped `--db` dump cannot be converted into full replica-set oplog recovery by adding a replay flag later.

## 4. Prepare versions, workspace and access

Use Linux/Bash, Python 3, Docker and the retained Chapter 41 TLS deployment. Supply the same pinned `MONGO_IMAGE` digest used for that lab. Confirm the client image contains **both** Database Tools executables; if it does not, prepare an approved image containing compatible pinned Tools rather than installing an unreviewed latest version during recovery.

```bash
umask 077
mkdir mongodb-ch50
cd mongodb-ch50
mkdir scripts evidence artifacts
export LAB50_ROOT="$PWD"
export TLS50_ROOT='/absolute/path/to/mongodb-ch41'
test -n "${MONGO_IMAGE:?use the pinned Chapter 41 image}"
test -f "$TLS50_ROOT/pki/public/ca.crt"
docker run --rm "$MONGO_IMAGE" mongodump --version
docker run --rm "$MONGO_IMAGE" mongorestore --version
```

Record both exact tool versions, server version, FCV and image digest. Pin the same Tools release for capture/restore and use this same MongoDB 8.0 server for the teaching exercise. Cross-version migration requires a separate supported compatibility plan.

Clients use `mongo41:27017` on `mongodb-ch41_security41`; no host port is required. Mount only the public CA on clients. Check CA/leaf validity before starting. Never use invalid-certificate or hostname-bypass options.

Setup and restore use the retained `ch41_bootstrap` administrator with an interactive password prompt. This is an explicit teaching convenience on the owned disposable lab. Production capture should use a dedicated scoped identity; restore should use a separately approved identity and reviewed privileges. The chapter creates a read-only `ch50_dump` user for scoped capture and removes it at cleanup.

## 5. Define fresh authenticated clients

Save the controller from Section 6 as `scripts/control50.js` before invoking these functions. `ACTION50` selects a fixed controller action, never a namespace supplied by the operator.

```bash
admin50() {
  docker run --rm -it --user "$(id -u):$(id -g)" \
    --network mongodb-ch41_security41 \
    -v "$TLS50_ROOT/pki/public:/trust:ro" \
    -v "$LAB50_ROOT/scripts:/scripts:ro" \
    -v "$LAB50_ROOT/evidence:/evidence" \
    --env ACTION50 "$MONGO_IMAGE" \
    mongosh 'mongodb://mongo41:27017/admin' --tls --tlsCAFile /trust/ca.crt \
    --username ch41_bootstrap --authenticationDatabase admin \
    --authenticationMechanism SCRAM-SHA-256 --password \
    --file /scripts/control50.js
}
dump50() {
  docker run --rm -it --user "$(id -u):$(id -g)" \
    --network mongodb-ch41_security41 \
    -v "$TLS50_ROOT/pki/public:/trust:ro" \
    -v "$LAB50_ROOT/artifacts:/artifacts" "$MONGO_IMAGE" \
    mongodump --uri='mongodb://mongo41:27017/' --ssl --sslCAFile=/trust/ca.crt \
    --username=ch50_dump --authenticationDatabase=admin \
    --authenticationMechanism=SCRAM-SHA-256 \
    --db=mongodb_enterprise_tutorial_ch50 \
    --archive=/artifacts/fixture50.archive.gz --gzip
}
restore50() {
  docker run --rm -it --user "$(id -u):$(id -g)" \
    --network mongodb-ch41_security41 \
    -v "$TLS50_ROOT/pki/public:/trust:ro" \
    -v "$LAB50_ROOT/artifacts:/artifacts:ro" "$MONGO_IMAGE" \
    mongorestore --uri='mongodb://mongo41:27017/' --ssl --sslCAFile=/trust/ca.crt \
    --username=ch41_bootstrap --authenticationDatabase=admin \
    --authenticationMechanism=SCRAM-SHA-256 \
    --archive=/artifacts/fixture50.archive.gz --gzip --stopOnError \
    --nsInclude='mongodb_enterprise_tutorial_ch50.*' \
    --nsFrom='mongodb_enterprise_tutorial_ch50.*' \
    --nsTo='mongodb_enterprise_tutorial_ch50_recovered.*'
}
```

Database Tools use `--ssl`/`--sslCAFile`; `mongosh` uses the corresponding `--tls` flags. Tools prompt because username is supplied and password is omitted. Keep passwords out of command arguments, environment variables and URIs. Do not run with shell tracing enabled. Interactive setup uses `passwordPrompt()`.

Use archive/gzip on both sides. An archive is not a normal `tar` file. Single-quote wildcard namespace arguments so Bash cannot expand them.

## 6. Implement the owned fixture controller

The controller stores source collection UUIDs, the created user's ID and later recovered UUIDs in an exclusive local state file. The run marker and collection set prevent accidental cleanup of an unrelated database. Partial setup/restore failures require inspection; the controller intentionally refuses to adopt unknown existing objects.

```javascript
const fs = require('fs');
const crypto = require('crypto');
const S = 'mongodb_enterprise_tutorial_ch50';
const T = 'mongodb_enterprise_tutorial_ch50_recovered';
const A = db.getSiblingDB('admin');
const statePath = '/evidence/state50.json';
const names = ['customers', 'marker', 'orders'];
const validator = {$jsonSchema: {bsonType: 'object',
  required: ['_id', 'customerId', 'amountCents', 'status'],
  properties: {customerId: {bsonType: 'number'},
    amountCents: {bsonType: 'number', minimum: 0},
    status: {enum: ['open', 'paid']}}}};
const orders = Array.from({length: 100}, (_, n) => ({
  _id: n + 1, customerId: n % 10 + 1, amountCents: (n + 1) * 100,
  status: n % 2 ? 'paid' : 'open'}));
const customers = Array.from({length: 10}, (_, n) => ({
  _id: n + 1, email: `customer${n + 1}@example.invalid`}));
function eq(a, b) {
  return EJSON.stringify(a, {relaxed: true}) === EJSON.stringify(b, {relaxed: true});
}
function check(ok, message) { if (!ok) throw new Error(message); }
function infos(name) { return db.getSiblingDB(name).getCollectionInfos(); }
function empty(name) {
  const d = db.getSiblingDB(name);
  check(infos(name).length === 0, `existing collections in ${name}`);
  check(d.getUsers().users.length === 0, `existing users in ${name}`);
  check(d.getRoles({showBuiltinRoles: false}).roles.length === 0,
    `existing roles in ${name}`);
}
function uuidMap(name) {
  return Object.fromEntries(infos(name).map(i => [i.name,
    EJSON.stringify(i.info.uuid, {relaxed: false})]));
}
function owned(name, state, expectedUUIDs) {
  const d = db.getSiblingDB(name);
  check(eq(infos(name).map(i => i.name).sort(), names), 'unexpected collection set');
  const marker = d.marker.findOne({_id: 'owner'});
  check(marker && marker.runId === state.runId && marker.chapter === 50,
    'ownership marker mismatch');
  check(d.marker.countDocuments({}) === 1, 'unexpected marker documents');
  if (expectedUUIDs) {
    const actual = uuidMap(name);
    for (const n of names) check(actual[n] === expectedUUIDs[n], 'UUID mismatch');
  }
  check(d.getUsers().users.length === 0, 'unexpected database users');
  check(d.getRoles({showBuiltinRoles: false}).roles.length === 0,
    'unexpected database roles');
  return d;
}
function verify(name, state, damaged = false) {
  const d = owned(name, state, name === S ? state.sourceUUIDs : state.targetUUIDs);
  const expected = damaged ? orders.slice(0, 80) : orders;
  check(eq(d.customers.find().sort({_id: 1}).toArray(), customers), 'customer mismatch');
  const actual = d.orders.find().sort({_id: 1}).toArray();
  check(eq(actual, expected), 'order document mismatch');
  const sum = actual.reduce((n, row) => n + row.amountCents, 0);
  check(sum === (damaged ? 324000 : 505000), 'business total mismatch');
  const indexes = d.customers.getIndexes();
  check(indexes.length === 2 && indexes.some(i => i.name === 'email_unique50'
    && i.unique === true && eq(i.key, {email: 1})), 'unique index mismatch');
  check(d.orders.getIndexes().length === 1, 'unexpected orders index');
  check(d.marker.getIndexes().length === 1, 'unexpected marker index');
  const options = d.getCollectionInfos({name: 'orders'})[0].options;
  check(eq(options.validator, validator) && options.validationLevel === 'strict'
    && options.validationAction === 'error', 'validator mismatch');
  return {database: name, orderCount: actual.length, amountCents: sum,
    customerCount: 10, documentDigest: crypto.createHash('sha256')
      .update(EJSON.stringify(actual, {relaxed: false})).digest('hex')};
}
function writeNew(path, value) {
  fs.writeFileSync(path, EJSON.stringify(value, {relaxed: false}),
    {flag: 'wx', mode: 0o600});
}
function userGuard(state) {
  const u = A.getUser('ch50_dump');
  check(u && eq(u.userId, state.dumpUserId), 'dump user identity mismatch');
  check(eq(u.roles, [{role: 'read', db: S}]), 'dump user roles changed');
}
const action = process.env.ACTION50;
const hello = A.runCommand({hello: 1});
check(hello.ok === 1 && !hello.setName && hello.msg !== 'isdbgrid',
  'this fixture expects the retained standalone');
if (action === 'setup') {
  check(!fs.existsSync(statePath), 'state already exists');
  empty(S); empty(T);
  check(!A.getUser('ch50_dump'), 'dump username already exists');
  const runId = crypto.randomUUID();
  const d = db.getSiblingDB(S);
  d.createCollection('customers');
  d.createCollection('orders', {validator, validationLevel: 'strict',
    validationAction: 'error'});
  d.createCollection('marker');
  d.customers.insertMany(customers, {writeConcern: {w: 1, j: true}});
  d.customers.createIndex({email: 1}, {name: 'email_unique50', unique: true});
  d.orders.insertMany(orders, {writeConcern: {w: 1, j: true}});
  d.marker.insertOne({_id: 'owner', runId, chapter: 50},
    {writeConcern: {w: 1, j: true}});
  print('Choose a new password for ch50_dump; keep it in your approved secret store.');
  A.createUser({user: 'ch50_dump', pwd: passwordPrompt(), roles: [{role: 'read', db: S}]});
  const state = {runId, sourceUUIDs: uuidMap(S), dumpUserId: A.getUser('ch50_dump').userId};
  writeNew(statePath, state);
  const build = A.runCommand({buildInfo: 1});
  const fcv = A.runCommand({getParameter: 1, featureCompatibilityVersion: 1});
  check(build.ok === 1 && fcv.ok === 1, 'inventory failed');
  writeNew('/evidence/baseline50.json', {runId, observedAt: new Date(),
    serverVersion: build.version, fcv: fcv.featureCompatibilityVersion,
    topology: 'standalone', writeConcern: {w: 1, j: true},
    result: verify(S, state)});
  print('Setup and baseline verified. Keep the fixture idle through capture.');
} else {
  const state = EJSON.parse(fs.readFileSync(statePath, 'utf8'));
  userGuard(state);
  if (action === 'verify-source') {
    printjson(verify(S, state));
  } else if (action === 'damage') {
    verify(S, state);
    const result = db.getSiblingDB(S).orders.deleteMany({_id: {$gte: 81, $lte: 100}},
      {writeConcern: {w: 1, j: true}});
    check(result.deletedCount === 20, 'unexpected deletion count');
    writeNew('/evidence/damage50.json', {runId: state.runId,
      observedAt: new Date(), result: verify(S, state, true)});
    print('Exactly twenty owned fixture orders deleted.');
  } else if (action === 'preflight-target') {
    verify(S, state, true); empty(T);
    check(!state.targetUUIDs, 'previous target already recorded');
    print('Recovered namespace empty; execute only the fixed restore50 wrapper.');
  } else if (action === 'verify-recovered') {
    verify(S, state, true);
    const result = verify(T, state);
    if (!state.targetUUIDs) {
      state.targetUUIDs = uuidMap(T);
      fs.writeFileSync(statePath, EJSON.stringify(state, {relaxed: false}), {mode: 0o600});
    }
    writeNew('/evidence/recovered50.json', {runId: state.runId,
      observedAt: new Date(), result});
    printjson(result);
  } else if (action === 'cleanup') {
    verify(S, state, true);
    check(state.targetUUIDs, 'verified target UUIDs required before cleanup');
    verify(T, state);
    check(T === 'mongodb_enterprise_tutorial_ch50_recovered' &&
      db.getSiblingDB(T).getName() === T, 'unexpected recovery target; refuse cleanup');
    check(db.getSiblingDB(T).dropDatabase().ok === 1, 'target cleanup failed');
    check(S === 'mongodb_enterprise_tutorial_ch50' &&
      db.getSiblingDB(S).getName() === S, 'unexpected source database; refuse cleanup');
    check(db.getSiblingDB(S).dropDatabase().ok === 1, 'source cleanup failed');
    check(A.dropUser('ch50_dump'), 'user cleanup failed');
    writeNew('/evidence/cleanup50.json', {runId: state.runId, observedAt: new Date(),
      sourceCollections: infos(S).length, targetCollections: infos(T).length,
      dumpUserAbsent: A.getUser('ch50_dump') === null});
    print('Owned fixture and dump user removed; evidence retained.');
  } else throw new Error('unknown ACTION50');
}
```

The verification compares the entire ordered customer/order documents, not only counts. Monetary values are integer cents within safe JavaScript numeric range. There is no timestamp-based mutation during capture. UUIDs on logical restore are expected to change; `--preserveUUID` is deliberately absent.

## 7. Create and verify the idle source

```bash
export ACTION50=setup
admin50
export ACTION50=verify-source
admin50
```

Inspect `evidence/baseline50.json`: 100 orders, ten customers and total **505,000 cents**. Independently review the controller and verify that no other process writes either chapter database. Do not reuse an existing source or state file; a failed setup needs inspection and an explicit cleanup plan for partial owned objects.

The created dump user has `read` on the source database only. It cannot perform the deletion or restore into the recovered database. For whole-deployment backups, review the built-in `backup` role and exact supported scope rather than expanding this teaching user silently.

## 8. Capture the archive and record completion

Run each command only after the preceding command succeeds. Retain the actual Tools output/exit status in protected evidence through your approved terminal capture process; never record interactive passwords.

```bash
test ! -e artifacts/fixture50.archive.gz
date -u +'%Y-%m-%dT%H:%M:%SZ' > evidence/dump-start50.txt
dump50
date -u +'%Y-%m-%dT%H:%M:%SZ' > evidence/dump-end50.txt
test -s artifacts/fixture50.archive.gz
export ACTION50=verify-source
admin50
```

If the dump fails, stop. A nonempty partial archive is not accepted. Label it failed, preserve logs and choose a fresh artifact filename/workspace for a new attempt. Do not overwrite the successful baseline artifact later with the damaged source.

After successful capture, save the integrity helper from Section 9 and seal the artifact. The dump's completion timestamp is an observed operational milestone. This quiet fixture represents the same deterministic state throughout capture; that does not make every live database dump an exact global cutoff.

## 9. Seal and verify artifact bytes

Save as `scripts/artifact50.py`. It uses a fixed archive filename, rejects symbolic links and creates the manifest exclusively. The manifest detects accidental byte changes; protect it separately if the threat model includes an attacker rewriting both artifact and manifest.

```python
#!/usr/bin/env python3
import hashlib
import json
import pathlib
import sys

def fingerprint(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError('archive must be a regular, non-symlink file')
    size = 0
    digest = hashlib.sha256()
    with path.open('rb') as source:
        while True:
            block = source.read(1024 * 1024)
            if not block:
                break
            size += len(block)
            digest.update(block)
    if size == 0:
        raise ValueError('empty archive')
    return {'format': 1, 'file': 'fixture50.archive.gz',
            'bytes': size, 'sha256': digest.hexdigest()}

def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ('seal', 'verify'):
        print('usage: artifact50.py seal|verify artifacts-directory', file=sys.stderr)
        return 1
    root = pathlib.Path(sys.argv[2])
    archive = root / 'fixture50.archive.gz'
    manifest = root / 'manifest50.json'
    try:
        actual = fingerprint(archive)
        if sys.argv[1] == 'seal':
            with manifest.open('x', encoding='utf-8') as output:
                json.dump(actual, output, indent=2)
        else:
            if manifest.is_symlink() or not manifest.is_file():
                raise ValueError('manifest must be a regular, non-symlink file')
            expected = json.loads(manifest.read_text(encoding='utf-8'))
            if expected != actual:
                raise ValueError('artifact integrity mismatch')
        print('artifact bytes verified; BSON validity and recoverability require restore')
        return 0
    except (OSError, ValueError, TypeError) as error:
        print(str(error), file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
```

```bash
python3 scripts/artifact50.py seal artifacts
python3 scripts/artifact50.py verify artifacts
```

Gzip compresses; it does not encrypt. Restrict artifact access, use approved encrypted storage and transport, and preserve decryption access for its retention period. A checksum pass does not validate BSON, backup scope or business correctness.

## 10. Inject a controlled logical deletion

Verify the sealed archive before modifying the source:

```bash
python3 scripts/artifact50.py verify artifacts
date -u +'%Y-%m-%dT%H:%M:%SZ' > evidence/incident50.txt
export ACTION50=damage
admin50
```

The action first checks the original fixture and ownership. It deletes only IDs 81–100, then verifies **80 orders** and **324,000 cents**. Customers, indexes, validator and run marker remain intact. A second `damage` action refuses because the source no longer matches the original baseline.

Do not “fix” a mismatch by changing the expected values. Investigate foreign writes, partial execution or an incorrect target. The source remains damaged until cleanup; recovery is demonstrated in the separate namespace.

## 11. Restore into the empty recovered namespace

```bash
export ACTION50=preflight-target
admin50
python3 scripts/artifact50.py verify artifacts
date -u +'%Y-%m-%dT%H:%M:%SZ' > evidence/restore-start50.txt
restore50
date -u +'%Y-%m-%dT%H:%M:%SZ' > evidence/restore-end50.txt
export ACTION50=verify-recovered
admin50
```

Stop on any unsuccessful command. There must be no concurrent creator/writer between target preflight and restore. `--stopOnError` limits continuing after document errors; restore is not a transaction and may leave partial objects. Do not retry blindly into that partial database. Inspect the failure, confirm ownership of every created object, and reset only the disposable recovery namespace under an explicit reviewed cleanup plan.

Selective restore filters the source namespace and maps its collections to the recovered database. It does not update the damaged source. No oplog replay occurs. This archive contains ordinary fixture collections only; no `admin` credentials are restored.

## 12. Validate recovery and constraints

Read `evidence/recovered50.json` and compare its order digest with `baseline50.json`. Expected recovered values are 100 orders, ten customers and 505,000 cents; the source still has 80 orders/324,000 cents. The controller checks the unique index and exact validator/options as well as documents.

For additional live behavior validation, save this as `scripts/constraints50.js` and run it using a fresh administrator client with the same TLS/network/mount options as `admin50`, replacing its `--file` path:

```javascript
const fs = require('fs');
const state = EJSON.parse(fs.readFileSync('/evidence/state50.json', 'utf8'));
const d = db.getSiblingDB('mongodb_enterprise_tutorial_ch50_recovered');
const marker = d.marker.findOne({_id: 'owner'});
if (!marker || marker.runId !== state.runId || !state.targetUUIDs)
  throw new Error('verified chapter target required');
for (const name of ['customers', 'marker', 'orders']) {
  const info = d.getCollectionInfos({name})[0];
  if (!info || EJSON.stringify(info.info.uuid, {relaxed: false}) !== state.targetUUIDs[name])
    throw new Error('target collection identity changed');
}
for (const [collection, document, code] of [
  ['customers', {_id: 'negative50-duplicate', email: 'customer1@example.invalid'}, 11000],
  ['orders', {_id: 'negative50-invalid', customerId: 1, amountCents: -1, status: 'open'}, 121]
]) {
  let observed = false;
  try { d.getCollection(collection).insertOne(document); }
  catch (error) { if (error.code !== code) throw error; observed = true; }
  if (!observed) throw new Error(`expected rejection ${code}; inspect unexpected insert`);
}
if (d.customers.countDocuments({}) !== 10 || d.orders.countDocuments({}) !== 100)
  throw new Error('unexpected post-test document counts');
fs.writeFileSync('/evidence/constraints50.json', JSON.stringify({
  runId: state.runId, observedAt: new Date().toISOString(),
  duplicateRejected: true, validatorRejected: true
}), {flag: 'wx', mode: 0o600});
print('Duplicate and invalid document rejected; counts unchanged.');
```

```bash
docker run --rm -it --user "$(id -u):$(id -g)" \
  --network mongodb-ch41_security41 \
  -v "$TLS50_ROOT/pki/public:/trust:ro" \
  -v "$LAB50_ROOT/scripts:/scripts:ro" \
  -v "$LAB50_ROOT/evidence:/evidence" "$MONGO_IMAGE" \
  mongosh 'mongodb://mongo41:27017/admin' --tls --tlsCAFile /trust/ca.crt \
  --username ch41_bootstrap --authenticationDatabase admin \
  --authenticationMechanism SCRAM-SHA-256 --password \
  --file /scripts/constraints50.js
```

If either insert unexpectedly succeeds, stop and investigate; do not hide the accepted invalid data. Re-run the full recovered verification through a fresh workspace/evidence filename after resolving the problem. Production acceptance should also check views, validators, index options, reference integrity and application queries appropriate to its actual dataset.

## 13. Understand full replica-set oplog recovery

The following is a **separate runbook pattern**, not a command to execute against the retained standalone. Use a dedicated owned replica set and an empty isolated compatible target, with reviewed TLS, credentials, whole-instance scope and additional replay privileges.

```bash
# Set these to reviewed replica-set URIs with no passwords and valid TLS names.
: "${SOURCE_RS_URI:?dedicated replica-set source URI required}"
: "${TARGET_RS_URI:?isolated replica-set target URI required}"
: "${CA_FILE:?trusted CA file required}"
test ! -e full-rs50.archive.gz
mongodump --uri="$SOURCE_RS_URI" --ssl --sslCAFile="$CA_FILE" \
  --username=backup_operator --authenticationDatabase=admin \
  --archive=full-rs50.archive.gz --gzip --oplog
mongorestore --uri="$TARGET_RS_URI" --ssl --sslCAFile="$CA_FILE" \
  --username=replay_operator --authenticationDatabase=admin \
  --archive=full-rs50.archive.gz --gzip --oplogReplay --stopOnError
```

Full oplog recovery must use the full supported capture and restore scope. Do not add `--db`, `--collection`, namespace filters or namespace remapping to this replay workflow. Replay requires privileges beyond the ordinary restore role; provision the narrowly controlled recovery identity according to the exact Tools documentation, then revoke it after the approved operation.

The captured oplog covers the dump interval, not an indefinitely continuing stream. Replay does not establish arbitrary PITR after dump completion. Avoid unsupported DDL/FCV changes during capture, verify the required oplog interval remains available and inspect all capture/replay errors. A hand-selected oplog limit or copied `local.oplog.rs` is not a safe substitute for a designed recovery chain.

Do not apply this recipe to `mongos` or use independent shard dumps as a consistent whole-cluster recovery. Use the release-specific coordinated procedure in the sharded recovery lab.

## 14. Measure loss and elapsed recovery

The deliberate deletion is the incident. The backup predates it, and no legitimate fixture writes occurred between capture and deletion. Verify that all baseline IDs reappear in the recovered namespace; the intentionally deleted set contains twenty orders totaling **181,000 cents**.

Record incident, restore start/end and application acceptance times. The end of `mongorestore` is not the service-restored time. In this lab, acceptance requires full recovered verification, both constraint rejections and a reviewed application query contract. There is no application cutover, so label the result **namespace recovery elapsed time**, not production service RTO.

Chapter 49's evaluator can assess a real declared drill timeline after its flags are backed by evidence. Do not fill in zero RPO merely because all fixture documents were recovered. Distinguish recovered baseline operations from recovery-point age, and retain the actual quiet interval/cutoff reasoning. A future source write after capture is outside this archive.

## 15. Troubleshoot logical recovery

| Symptom | Check and response |
|---|---|
| TLS trust/name error | Correct CA, SAN, server name and certificate validity; preserve TLS verification |
| Authentication failure | User, auth database, mechanism and secret; use a fresh process |
| Authorization failure | Actual source/target privileges and requested scope; do not grant root reflexively |
| Namespace filter matches nothing | Source namespace, archive contents and literal quoted pattern |
| Duplicate key/validation error | Nonempty target, incompatible metadata or unexpected artifact; inspect partial restore |
| Archive read/gzip failure | Matching flags, tool compatibility, size/checksum and transfer completion |
| Counts pass but application fails | Whole documents, references, metadata, encrypted dependencies and query behavior |
| Restore exceeds objective | Separate transfer, insertion, index build and validation bottlenecks |

Avoid `--noIndexRestore`, `--bypassDocumentValidation` or validation bypasses to force a green result. If a migration intentionally requires changed metadata, design and validate that transformation separately. More parallel workers can increase source/target contention; measure before changing defaults.

`--drop` drops collections represented in the restore, not every unrelated collection in the destination. Restoring `admin` with it can replace credentials and lock out operators. A partial failure can leave a mixed state. Prefer a fresh isolated target and explicit validated cutover for operational recovery.

## 16. Acceptance and guarded cleanup

Acceptance requires exact version inventory, maintained quiet capture boundary, successful dump and restore exit statuses, unchanged sealed archive, verified damaged source, exact restored documents/totals, restored metadata, live constraint rejection and reviewed evidence. These are instructions for the learner; this chapter remains runtime pending until actually executed.

After review, remove only the controller-owned source/recovered databases and the created dump user:

```bash
export ACTION50=cleanup
admin50
```

Cleanup requires the verified target UUIDs and original source UUIDs. Unknown objects, changed roles, user replacement or changed documents make it refuse. Preserve evidence and investigate rather than weakening ownership checks. Partial cleanup may require manual completion after checking the remaining object's identity.

Retain the local archive/state/evidence under the lab's retention decision. Archive access can disclose the fixture and metadata; gzip does not protect it. This chapter never changes the retained server's configuration or other chapter databases. Independently verify ordinary administrator access remains available after cleanup.

## 17. References and next chapter

- [mongodump options](https://www.mongodb.com/docs/database-tools/mongodump/)
- [mongodump behavior and access](https://www.mongodb.com/docs/database-tools/mongodump/mongodump-behavior/)
- [mongorestore options](https://www.mongodb.com/docs/database-tools/mongorestore/)
- [mongorestore behavior and required access](https://www.mongodb.com/docs/database-tools/mongorestore/mongorestore-behavior-access-usage/)
- [MongoDB 8.0 logical backup and restore](https://www.mongodb.com/docs/v8.0/tutorial/backup-and-restore-tools/)
- [Previous: Chapter 49 — Backup Architecture RPO and RTO](49-backup-architecture-rpo-and-rto.md)

Next: [**Chapter 51 — Consistent Snapshots and Restore Validation**](51-consistent-snapshots-and-restore-validation.md).
