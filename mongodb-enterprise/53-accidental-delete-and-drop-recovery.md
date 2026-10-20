# 53 — Accidental Delete and Drop Recovery

Part 7 — Backup Recovery and Disaster Recovery

**Baseline:** MongoDB 8.0; compatible pinned Database Tools; retained Chapter 41 authenticated TLS standalone.  
**Status:** Written; static review complete; live delete/drop recovery validation pending.  
**Prerequisites:** Chapters 49–52, an owned disposable fixture, protected artifacts and a quiet recovery scope.

## 1. Define two different repair contracts

Deleting documents leaves the collection's metadata in place. Dropping a collection removes the collection and its indexes/options. Recovering either incident requires a clean source of data and a decision about valid changes made after that source was captured.

This lab performs two sequential exercises in a new chapter database. First, restore an earlier backup into a candidate database and insert only twenty incident-confirmed missing orders, preserving a legitimate newer update and insert. Second, capture that repaired state, drop its orders collection, restore to a staging collection and promote the fully verified staging collection.

No command restores over another chapter's database. Source/candidate namespaces share the retained standalone, so this is logical repair isolation, not demonstrated host-loss disaster recovery. Ops Manager PITR is an alternative clean-source workflow in Section 14, not a prerequisite for this executable baseline.

## 2. Contain the incident and preserve evidence

For an actual incident, stop the offending writer/job, establish ownership, record the time and affected namespace, and preserve logs/audit/application acknowledgment evidence. Keep normal recovery access available. Choose a consistent clean point and restore it in isolation before modifying current data.

| Evidence | Why it matters |
|---|---|
| Namespace, collection UUID and affected IDs | Prevent repair of a replacement or unrelated collection |
| Delete/drop operation and first-bad boundary | Separate pre-incident clean state from corruption |
| Valid later writes | Avoid reverting legitimate updates or resurrecting intended deletions |
| Backup scope/cutoff and metadata | Establish what the candidate can recover |
| Reviewed repair plan and current-state digest | Detect changes between review and application |

Do not start with `mongorestore --drop`, a blind upsert or a full rollback of the live deployment. Neither replication nor journaling provides a general user-facing undo command for committed deletes. The recovery source must come from a supported retained backup/history or another independently verified authoritative system.

## 3. Decide what to merge and what to replace

| Situation | Repair strategy |
|---|---|
| Known erroneous deletion; survivors have valid newer changes | Insert only confirmed missing IDs; preserve survivors |
| Same ID has changed since backup | Review conflict; do not overwrite automatically |
| Missing ID might reflect an intentional deletion | Require business confirmation before resurrection |
| Collection dropped; no replacement exists | Restore data and metadata to staging, validate, then promote |
| Dropped collection was recreated and received new writes | Reconcile replacement identity/data; do not overwrite it |
| Database-wide/sharded corruption | Restore a coordinated clean deployment; reconcile/cut over under its runbook |

The fixed teaching policy permits IDs 81–100 because the lab's own incident action deleted exactly those orders. It preserves changed order 1 and newer order 101. In production, an ID being absent today is not by itself evidence that it should be reinserted.

## 4. Prepare a fresh workspace and clients

The retained source is `mongo41:27017` on `mongodb-ch41_security41`. Supply the pinned Chapter 41 image and valid public CA. Confirm both Tools binaries are present and record their exact versions. Do not change the server's authentication, TLS or configuration.

```bash
umask 077
mkdir mongodb-ch53
cd mongodb-ch53
mkdir scripts evidence artifacts
export LAB53_ROOT="$PWD"
export TLS53_ROOT='/absolute/path/to/mongodb-ch41'
test -n "${MONGO_IMAGE:?use the pinned Chapter 41 image}"
test -f "$TLS53_ROOT/pki/public/ca.crt"
docker run --rm "$MONGO_IMAGE" mongodump --version
docker run --rm "$MONGO_IMAGE" mongorestore --version
admin53() {
  docker run --rm -it --user "$(id -u):$(id -g)" \
    --network mongodb-ch41_security41 \
    -v "$TLS53_ROOT/pki/public:/trust:ro" \
    -v "$LAB53_ROOT/scripts:/scripts:ro" \
    -v "$LAB53_ROOT/evidence:/evidence" \
    --env ACTION53 "$MONGO_IMAGE" \
    mongosh 'mongodb://mongo41:27017/admin' --tls --tlsCAFile /trust/ca.crt \
    --username ch41_bootstrap --authenticationDatabase admin \
    --authenticationMechanism SCRAM-SHA-256 --password --file /scripts/control53.js
}
```

The administrator is a convenience on this owned disposable lab. Production backup, review and repair should use separately approved identities and necessary scope. All commands prompt for secrets; never place passwords in URIs, arguments, environment variables or shell traces.

## 5. Define fixed backup and restore operations

These functions have explicit allowed artifact names. Run them only after their corresponding preflight succeeds. The baseline capture requires the fixture to be idle; this standalone workflow has no oplog replay.

```bash
capture53() {
  case "$1" in baseline53|predrop53) ;; *) return 1 ;; esac
  test ! -e "$LAB53_ROOT/artifacts/$1.archive.gz" || return 1
  docker run --rm -it --user "$(id -u):$(id -g)" \
    --network mongodb-ch41_security41 \
    -v "$TLS53_ROOT/pki/public:/trust:ro" \
    -v "$LAB53_ROOT/artifacts:/artifacts" "$MONGO_IMAGE" \
    mongodump --uri='mongodb://mongo41:27017/' --ssl --sslCAFile=/trust/ca.crt \
    --username=ch41_bootstrap --authenticationDatabase=admin \
    --authenticationMechanism=SCRAM-SHA-256 --db=mongodb_enterprise_tutorial_ch53 \
    --archive="/artifacts/$1.archive.gz" --gzip
}
candidate53() {
  docker run --rm -it --user "$(id -u):$(id -g)" \
    --network mongodb-ch41_security41 \
    -v "$TLS53_ROOT/pki/public:/trust:ro" \
    -v "$LAB53_ROOT/artifacts:/artifacts:ro" "$MONGO_IMAGE" \
    mongorestore --uri='mongodb://mongo41:27017/' --ssl --sslCAFile=/trust/ca.crt \
    --username=ch41_bootstrap --authenticationDatabase=admin \
    --authenticationMechanism=SCRAM-SHA-256 \
    --archive=/artifacts/baseline53.archive.gz --gzip --stopOnError \
    --nsInclude='mongodb_enterprise_tutorial_ch53.*' \
    --nsFrom='mongodb_enterprise_tutorial_ch53.*' \
    --nsTo='mongodb_enterprise_tutorial_ch53_candidate.*'
}
staging53() {
  docker run --rm -it --user "$(id -u):$(id -g)" \
    --network mongodb-ch41_security41 \
    -v "$TLS53_ROOT/pki/public:/trust:ro" \
    -v "$LAB53_ROOT/artifacts:/artifacts:ro" "$MONGO_IMAGE" \
    mongorestore --uri='mongodb://mongo41:27017/' --ssl --sslCAFile=/trust/ca.crt \
    --username=ch41_bootstrap --authenticationDatabase=admin \
    --authenticationMechanism=SCRAM-SHA-256 \
    --archive=/artifacts/predrop53.archive.gz --gzip --stopOnError \
    --nsInclude='mongodb_enterprise_tutorial_ch53.orders' \
    --nsFrom='mongodb_enterprise_tutorial_ch53.orders' \
    --nsTo='mongodb_enterprise_tutorial_ch53.stagingOrders53'
}
```

The candidate restores all fixture collections so its run marker can be checked. Staging restores only orders, using the existing source marker plus independently verified documents/metadata for ownership. None of these operations restores users/roles or passes `--drop`. Gzip is compression, not encryption.

## 6. Implement a pure insert-only reconciliation planner

Save as `scripts/reconcile53.cjs`. It validates the small teaching schema, rejects duplicate IDs/codes and refuses missing IDs outside the approved incident set. Conflicts and newer rows are reported, never replaced. Its digest binds the plan to both observed datasets.

```javascript
const crypto = require('crypto');
function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === 'object') return Object.fromEntries(
    Object.keys(value).sort().map(key => [key, canonical(value[key])]));
  return value;
}
function hash(value) { return crypto.createHash('sha256')
  .update(JSON.stringify(canonical(value))).digest('hex'); }
function rows(input) {
  if (!Array.isArray(input)) throw new Error('rows must be an array');
  const ids = new Set(), codes = new Set();
  for (const row of input) {
    if (!row || Object.keys(row).sort().join(',') !== '_id,amountCents,code' ||
      !Number.isSafeInteger(row._id) || row._id < 1 ||
      !Number.isSafeInteger(row.amountCents) || row.amountCents < 0 ||
      typeof row.code !== 'string' || !row.code || ids.has(row._id) || codes.has(row.code))
      throw new Error('invalid or duplicate row');
    ids.add(row._id); codes.add(row.code);
  }
  return [...input].sort((x, y) => x._id - y._id);
}
function plan(baseline, current, allowedIds) {
  const old = rows(baseline), now = rows(current);
  if (!Array.isArray(allowedIds) || allowedIds.some(id =>
    !Number.isSafeInteger(id) || id < 1) || new Set(allowedIds).size !== allowedIds.length)
    throw new Error('invalid incident allowlist');
  const allow = new Set(allowedIds), index = new Map(now.map(row => [row._id, row]));
  const oldIds = new Set(old.map(row => row._id));
  const insert = [], conflicts = [];
  for (const row of old) {
    if (!index.has(row._id)) {
      if (!allow.has(row._id)) throw new Error('unapproved missing ID');
      if (now.some(existing => existing.code === row.code)) throw new Error('unique code collision');
      insert.push(row);
    } else if (hash(index.get(row._id)) !== hash(row)) conflicts.push(row._id);
  }
  const result = {baselineDigest: hash(old), currentDigest: hash(now),
    allowedIds: [...allowedIds].sort((a, b) => a - b), insert,
    preserveConflicts: conflicts, preserveNew: now.filter(row => !oldIds.has(row._id)).map(row => row._id)};
  return {...result, planDigest: hash(result)};
}
module.exports = {plan, hash, rows};
```

This planner is intentionally limited to plain integer-ID fixture documents. Production BSON types, nested fields, application versioning, references, tombstones and conflict policies require a suitable reviewed reconciliation implementation. Do not stringify arbitrary business data and assume this teaching policy applies.

## 7. Implement the guarded phase controller

Save as `scripts/control53.js`. The source uses a persistent marker and collection UUIDs; the candidate's logical-restore UUIDs are recorded only after its exact baseline is verified. Same-database staging promotion retains its newly restored UUID.

```javascript
const fs = require('fs');
const crypto = require('crypto');
const {plan, hash: jsonHash} = require('/scripts/reconcile53.cjs');
function plain(value) { return JSON.parse(EJSON.stringify(value, {relaxed: true})); }
function hash(value) { return jsonHash(plain(value)); }
const a = db.getSiblingDB('admin');
const S = 'mongodb_enterprise_tutorial_ch53';
const C = 'mongodb_enterprise_tutorial_ch53_candidate';
const source = db.getSiblingDB(S), candidate = db.getSiblingDB(C);
const path = '/evidence/state53.json';
const action = process.env.ACTION53;
const base = Array.from({length: 100}, (_, n) => ({
  _id: n + 1, code: `order-${n + 1}`, amountCents: (n + 1) * 10}));
const repaired = [...base.map(row => row._id === 1 ? {...row, amountCents: 1010} : row),
  {_id: 101, code: 'order-101', amountCents: 1010}];
const damaged = repaired.filter(row => row._id < 81 || row._id === 101);
const allow = Array.from({length: 20}, (_, n) => n + 81);
const validator = {$jsonSchema: {bsonType: 'object', required: ['_id', 'code', 'amountCents'],
  properties: {code: {bsonType: 'string'}, amountCents: {bsonType: 'number', minimum: 0}}}};
function check(value, message) { if (!value) throw new Error(message); }
function save(name, value) { fs.writeFileSync(`/evidence/${name}`,
  EJSON.stringify(value, {relaxed: false}), {flag: 'wx', mode: 0o600}); }
function stateWrite(state) { fs.writeFileSync(path,
  EJSON.stringify(state, {relaxed: false}), {mode: 0o600}); }
function uuid(d, name) { const info = d.getCollectionInfos({name})[0];
  check(info, 'collection absent'); return EJSON.stringify(info.info.uuid, {relaxed: false}); }
function empty(d) {
  check(d.getCollectionInfos().length === 0 && d.getUsers().users.length === 0 &&
    d.getRoles({showBuiltinRoles: false}).roles.length === 0, 'existing database objects');
}
function own(d, state, expectedNames, markerUUID) {
  check(hash(d.getCollectionInfos().map(i => i.name).sort()) === hash([...expectedNames].sort()),
    'unexpected collection set');
  const marker = d.marker.findOne({_id: 'owner'});
  check(marker && marker.runId === state.runId && marker.chapter === 53 &&
    d.marker.countDocuments({}) === 1, 'ownership marker mismatch');
  if (markerUUID) check(uuid(d, 'marker') === markerUUID, 'marker identity changed');
  check(d.getUsers().users.length === 0 &&
    d.getRoles({showBuiltinRoles: false}).roles.length === 0, 'unexpected users/roles');
}
function verifyOrders(d, name, expected, expectedUUID) {
  if (expectedUUID) check(uuid(d, name) === expectedUUID, 'orders identity changed');
  const collection = d.getCollection(name);
  const actual = collection.find().sort({_id: 1}).toArray();
  check(hash(actual) === hash(expected), 'exact document mismatch');
  const indexes = collection.getIndexes();
  check(indexes.length === 2 && indexes.some(i => i.name === 'code_unique53' &&
    i.unique === true && hash(i.key) === hash({code: 1})), 'unique index mismatch');
  const options = d.getCollectionInfos({name})[0].options;
  check(hash(options.validator) === hash(validator) && options.validationLevel === 'strict' &&
    options.validationAction === 'error', 'validator mismatch');
  return {count: actual.length, amountCents: actual.reduce((n, row) => n + row.amountCents, 0),
    digest: hash(actual), uuid: uuid(d, name)};
}
function sourceCheck(state, expected) {
  own(source, state, ['marker', 'orders'], state.markerUUID);
  return verifyOrders(source, 'orders', expected, state.ordersUUID);
}
function candidateCheck(state) {
  own(candidate, state, ['marker', 'orders'], state.candidateMarkerUUID);
  return verifyOrders(candidate, 'orders', base, state.candidateOrdersUUID);
}
const hello = a.runCommand({hello: 1});
const build = a.runCommand({buildInfo: 1});
const fcv = a.runCommand({getParameter: 1, featureCompatibilityVersion: 1});
check(hello.ok === 1 && !hello.setName && hello.msg !== 'isdbgrid', 'retained standalone required');
check(build.ok === 1 && build.version.startsWith('8.0.') && fcv.ok === 1 &&
  fcv.featureCompatibilityVersion.version === '8.0', '8.0 stable baseline required');
if (action === 'setup') {
  check(!fs.existsSync(path), 'state exists'); empty(source); empty(candidate);
  const state = {runId: crypto.randomUUID(), phase: 'base'};
  source.createCollection('orders', {validator, validationLevel: 'strict', validationAction: 'error'});
  source.createCollection('marker');
  source.orders.createIndex({code: 1}, {name: 'code_unique53', unique: true});
  source.orders.insertMany(base, {writeConcern: {w: 1, j: true}});
  source.marker.insertOne({_id: 'owner', runId: state.runId, chapter: 53},
    {writeConcern: {w: 1, j: true}});
  state.markerUUID = uuid(source, 'marker'); state.ordersUUID = uuid(source, 'orders');
  save('state53.json', state);
  save('baseline53.json', {runId: state.runId, serverVersion: build.version,
    fcv: fcv.featureCompatibilityVersion, result: sourceCheck(state, base)});
} else {
  const state = EJSON.parse(fs.readFileSync(path, 'utf8'));
  if (action === 'verify-base') {
    check(state.phase === 'base', 'wrong phase'); printjson(sourceCheck(state, base));
  } else if (action === 'delete-incident') {
    check(state.phase === 'base', 'wrong phase'); sourceCheck(state, base);
    source.orders.updateOne({_id: 1}, {$set: {amountCents: 1010}}, {writeConcern: {w: 1, j: true}});
    source.orders.insertOne(repaired[100], {writeConcern: {w: 1, j: true}});
    const result = source.orders.deleteMany({_id: {$in: allow}}, {writeConcern: {w: 1, j: true}});
    check(result.deletedCount === 20, 'unexpected deletion count');
    state.phase = 'damaged'; stateWrite(state);
    save('delete-incident53.json', {runId: state.runId, observedAt: new Date(),
      deletedIds: allow, result: sourceCheck(state, damaged)});
  } else if (action === 'preflight-candidate') {
    check(state.phase === 'damaged', 'wrong phase'); sourceCheck(state, damaged); empty(candidate);
    check(!state.candidateOrdersUUID, 'candidate already recorded');
  } else if (action === 'prepare-plan') {
    check(state.phase === 'damaged', 'wrong phase'); sourceCheck(state, damaged); candidateCheck(state);
    state.candidateMarkerUUID = uuid(candidate, 'marker');
    state.candidateOrdersUUID = uuid(candidate, 'orders'); stateWrite(state);
    const result = plan(plain(candidate.orders.find().toArray()), plain(source.orders.find().toArray()), allow);
    check(hash(result.insert.map(row => row._id)) === hash(allow) &&
      hash(result.preserveConflicts) === hash([1]) && hash(result.preserveNew) === hash([101]),
      'unexpected repair policy result');
    save('repair-plan53.json', {runId: state.runId, result}); printjson(result);
  } else if (action === 'approve-plan') {
    check(state.phase === 'damaged', 'wrong phase'); sourceCheck(state, damaged); candidateCheck(state);
    const saved = EJSON.parse(fs.readFileSync('/evidence/repair-plan53.json', 'utf8'));
    const current = plan(plain(candidate.orders.find().toArray()), plain(source.orders.find().toArray()), allow);
    check(saved.runId === state.runId && hash(saved.result) === hash(current), 'plan stale/changed');
    save('approval53.json', {runId: state.runId, planDigest: current.planDigest, observedAt: new Date()});
  } else if (action === 'apply-plan') {
    check(state.phase === 'damaged', 'wrong phase'); sourceCheck(state, damaged); candidateCheck(state);
    const saved = EJSON.parse(fs.readFileSync('/evidence/repair-plan53.json', 'utf8'));
    const approved = EJSON.parse(fs.readFileSync('/evidence/approval53.json', 'utf8'));
    const current = plan(plain(candidate.orders.find().toArray()), plain(source.orders.find().toArray()), allow);
    check(saved.runId === state.runId && approved.runId === state.runId &&
      hash(saved.result) === hash(current) && approved.planDigest === current.planDigest,
      'unapproved, stale or changed plan');
    source.orders.insertMany(current.insert, {ordered: true, writeConcern: {w: 1, j: true}});
    const result = sourceCheck(state, repaired); state.phase = 'repaired'; stateWrite(state);
    save('delete-repaired53.json', {runId: state.runId, observedAt: new Date(), result});
  } else if (action === 'verify-repaired') {
    check(state.phase === 'repaired', 'wrong phase'); printjson(sourceCheck(state, repaired));
  } else if (action === 'drop-incident') {
    check(state.phase === 'repaired', 'wrong phase'); sourceCheck(state, repaired);
    check(source.getName() === 'mongodb_enterprise_tutorial_ch53', 'unexpected source namespace; refuse incident drop');
    check(source.orders.drop({writeConcern: {w: 1, j: true}}), 'drop failed');
    own(source, state, ['marker'], state.markerUUID); state.phase = 'dropped'; stateWrite(state);
    save('drop-incident53.json', {runId: state.runId, observedAt: new Date(),
      droppedOrdersUUID: state.ordersUUID});
  } else if (action === 'preflight-staging') {
    check(state.phase === 'dropped' && !state.stagingUUID, 'wrong phase');
    own(source, state, ['marker'], state.markerUUID);
  } else if (action === 'verify-staging') {
    check(state.phase === 'dropped', 'wrong phase');
    own(source, state, ['marker', 'stagingOrders53'], state.markerUUID);
    const result = verifyOrders(source, 'stagingOrders53', repaired, state.stagingUUID);
    state.stagingUUID = result.uuid; stateWrite(state);
    save('staging-verified53.json', {runId: state.runId, observedAt: new Date(), result});
  } else if (action === 'promote-staging') {
    check(state.phase === 'dropped' && state.stagingUUID, 'verified staging required');
    own(source, state, ['marker', 'stagingOrders53'], state.markerUUID);
    verifyOrders(source, 'stagingOrders53', repaired, state.stagingUUID);
    const result = a.runCommand({renameCollection: `${S}.stagingOrders53`, to: `${S}.orders`,
      dropTarget: false, writeConcern: {w: 1, j: true}});
    check(result.ok === 1, 'promotion failed');
    state.ordersUUID = state.stagingUUID; state.phase = 'promoted'; stateWrite(state);
    save('drop-repaired53.json', {runId: state.runId, observedAt: new Date(),
      result: sourceCheck(state, repaired)});
  } else if (action === 'accept') {
    check(state.phase === 'promoted', 'wrong phase'); const result = sourceCheck(state, repaired);
    const validation = source.runCommand({validate: 'orders', full: true});
    check(validation.ok === 1 && validation.valid === true &&
      (!validation.errors || !validation.errors.length) &&
      (!validation.warnings || !validation.warnings.length), 'review storage validation');
    for (const [doc, code] of [
      [{_id: 'duplicate53', code: 'order-1', amountCents: 1}, 11000],
      [{_id: 'invalid53', code: 'invalid53', amountCents: -1}, 121]
    ]) {
      let denied = false;
      try { source.orders.insertOne(doc); }
      catch (error) { if (error.code !== code) throw error; denied = true; }
      check(denied, 'constraint unexpectedly accepted document');
    }
    sourceCheck(state, repaired);
    save('accepted53.json', {runId: state.runId, observedAt: new Date(), result, validation,
      duplicateRejected: true, validatorRejected: true});
  } else if (action === 'cleanup') {
    check(state.phase === 'promoted' && state.candidateOrdersUUID, 'completed lab required');
    const accepted = EJSON.parse(fs.readFileSync('/evidence/accepted53.json', 'utf8'));
    check(accepted.runId === state.runId, 'acceptance evidence mismatch');
    sourceCheck(state, repaired); candidateCheck(state);
    check(candidate.getName() === 'mongodb_enterprise_tutorial_ch53_candidate' &&
      source.getName() === 'mongodb_enterprise_tutorial_ch53',
      'unexpected owned database names; refuse cleanup');
    check(candidate.dropDatabase().ok === 1, 'candidate cleanup failed');
    check(source.dropDatabase().ok === 1, 'source cleanup failed');
    save('cleanup53.json', {runId: state.runId, observedAt: new Date(), completed: true});
  } else throw new Error('unknown ACTION53');
}
```

These are guarded lab transitions, not an automatic general-purpose incident agent. Unknown collections, changed UUIDs or data mismatches stop the workflow. State/evidence files are private and must not be edited to bypass a failed guard. Commands involving multiple writes are not transactions on this standalone; partial failure requires inspection.

## 8. Capture and seal the clean baseline

```bash
export ACTION53=setup
admin53
capture53 baseline53
export ACTION53=verify-base
admin53
```

Maintain the fixture's quiet interval through capture and post-capture verification. Require successful Tools exit and a nonempty archive before sealing. Save this as `scripts/artifact53.py`:

```python
#!/usr/bin/env python3
import hashlib
import json
import pathlib
import sys

def fingerprint(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError('regular non-symlink archive required')
    digest = hashlib.sha256()
    size = 0
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
            size += len(block)
    if not size:
        raise ValueError('empty archive')
    return {'format': 1, 'file': path.name, 'bytes': size, 'sha256': digest.hexdigest()}

def main():
    try:
        if len(sys.argv) != 3 or sys.argv[1] not in ('seal', 'verify'):
            raise ValueError('usage: artifact53.py seal|verify baseline53|predrop53')
        if sys.argv[2] not in ('baseline53', 'predrop53'):
            raise ValueError('unknown artifact')
        archive = pathlib.Path('artifacts') / (sys.argv[2] + '.archive.gz')
        manifest = pathlib.Path('evidence') / (sys.argv[2] + '-manifest.json')
        actual = fingerprint(archive)
        if sys.argv[1] == 'seal':
            with manifest.open('x', encoding='utf-8') as output:
                json.dump(actual, output, indent=2)
        else:
            if manifest.is_symlink() or not manifest.is_file():
                raise ValueError('regular non-symlink manifest required')
            if json.loads(manifest.read_text(encoding='utf-8')) != actual:
                raise ValueError('artifact integrity mismatch')
        print('artifact bytes verified; recovery requires MongoDB/application validation')
        return 0
    except (OSError, ValueError, TypeError) as error:
        print(str(error), file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
```

```bash
python3 scripts/artifact53.py seal baseline53
python3 scripts/artifact53.py verify baseline53
```

The manifest detects byte changes, not malicious replacement of both manifest and archive. Retain it independently under the integrity policy. If capture failed, mark its artifact failed and use a fresh workspace after correcting the cause; do not seal a partial archive merely because it exists.

## 9. Delete known rows and restore a candidate

```bash
python3 scripts/artifact53.py verify baseline53
export ACTION53=delete-incident
admin53
export ACTION53=preflight-candidate
admin53
candidate53
export ACTION53=prepare-plan
admin53
```

Require each prior command to succeed. The incident action performs the legitimate update/insert and the erroneous deletion in a controlled sequence. The damaged source has 81 rows/34,410 cents. The candidate is the earlier 100-row/50,500-cent baseline.

The prepared plan must contain exactly twenty insert documents, preserve-conflict ID `[1]` and preserve-new ID `[101]`. Candidate metadata/ownership is verified before its UUIDs are adopted. Do not merge the entire candidate or replace the current source with it: that would lose the legitimate 1,000-cent update and order 101.

## 10. Review and apply only confirmed missing documents

Read `evidence/repair-plan53.json`. Review affected IDs, exact insert documents, source/candidate digests, preserved conflicts and preserved newer IDs. Confirm this matches the recorded incident and business repair intent before executing the approval action.

```bash
export ACTION53=approve-plan
admin53
export ACTION53=apply-plan
admin53
export ACTION53=verify-repaired
admin53
```

The approval file binds the selected plan digest. Immediately before application, the controller recomputes the plan and verifies current source/candidate state and UUIDs. Keep all writers frozen between these checks and insertion; digest checks cannot remove that race by themselves.

The controller uses insert-only writes. Duplicate IDs/code conflicts fail rather than overwriting survivors. Ordered insertion is not an atomic batch on this standalone. If insertion partially fails, freeze, preserve logs and reconcile exact inserted IDs before preparing a new reviewed plan; the phase checks intentionally refuse blind retry.

Expected repaired source is **101 rows / 52,510 cents**, with order 1 amount 1,010 and order 101 present. The baseline candidate remains unchanged. A same-dataset plan recomputation yields the same digest; changed current data invalidates the prior approval.

## 11. Capture the repaired state before a drop

The original baseline archive does not contain the valid newer update or order 101. Therefore the second exercise takes a separate clean artifact after repair.

```bash
export ACTION53=verify-repaired
admin53
capture53 predrop53
export ACTION53=verify-repaired
admin53
python3 scripts/artifact53.py seal predrop53
python3 scripts/artifact53.py verify predrop53
export ACTION53=drop-incident
admin53
```

Keep the fixture idle throughout capture. Require successful capture, unchanged verified source and sealed artifact before drop. The drop guard checks the current marker, orders UUID, entire dataset and metadata. It removes **only** the owned `orders` collection and records its former UUID.

The marker remains, so the source database is still identifiable. A collection with the same name created after the drop is a different recovery situation: the preflight/collection-set guard must reject it rather than drop or overwrite it.

## 12. Validate staging and promote without overwriting

```bash
export ACTION53=preflight-staging
admin53
python3 scripts/artifact53.py verify predrop53
staging53
export ACTION53=verify-staging
admin53
export ACTION53=promote-staging
admin53
export ACTION53=accept
admin53
```

Staging restore must create only `stagingOrders53` alongside the existing marker. Verification requires all 101 repaired documents, index and validator, then records the staging UUID. Promotion uses a **same-database** rename with `dropTarget: false`. Any newly created destination is a failure, not permission to overwrite it.

Freeze all source writers/creators through promotion and acceptance. Rename changes namespace availability and can affect cursors/change-stream consumers; coordinate reconnection/resume behavior for real applications. The restored collection has a new logical-restore UUID, which remains through this same-database promotion. Do not assume it retains the dropped collection's original identity.

Acceptance verifies storage and rejects an invalid document and a duplicate code. If either is accepted or a restore leaves partial objects, stop and investigate. Do not bypass validation, omit index restoration or force a duplicate-key result into apparent success.

## 13. Compare expected recovery states and timings

| Phase | Orders | Amount cents | Valid newer writes |
|---|---:|---:|---|
| Baseline backup/candidate | 100 | 50,500 | Not yet present |
| Deleted source | 81 | 34,410 | Order 1 update and order 101 present |
| Insert-only repaired source | 101 | 52,510 | Preserved |
| Dropped source | Collection absent | Not queryable | Available in pre-drop artifact |
| Staging/promoted source | 101 | 52,510 | Recovered from pre-drop artifact |

Record incident declaration, candidate retrieval/restore, review, apply/promotion and application acceptance times. Report each repair's elapsed time separately. A restore-completed timestamp does not include reconciliation, metadata validation or safe resumption of writers.

This lab's controlled updates provide a known business contract. For a real incident, compare acknowledged operations and all dependent entities, then assess recovery-point age/RPO and RTO using Chapter 49's definitions. Restoring rows does not automatically establish zero data loss across the application.

## 14. Use PITR or physical recovery as the candidate source

When the desired clean state is between snapshots, use Chapter 52's managed recovery workflow to a separate deployment. Choose the exact pre-bad boundary under the platform's inclusive/exclusive semantics, and validate the candidate before extracting affected data.

A full clean-point restore can recover dropped metadata and transaction-consistent state, but it may intentionally exclude valid later writes. Reconcile those writes before cutover or perform a reviewed scoped merge from the candidate. Do not apply a full oplog-replay restore with namespace remapping; Chapter 50 explains that restriction.

For replica sets/shards, coordinate the actual topology and transaction boundaries. A transaction spanning multiple collections requires recovery/reconciliation of its whole business effect. Restoring one collection alone can leave references inconsistent. Do not infer a consistent sharded candidate from independently selected shard timestamps.

If there is no usable pre-incident recovery source, state that limitation plainly. Disk free space, a large oplog or a surviving replica that already applied the deletion is not proof of an undo path. Preserve evidence and pursue authoritative upstream reconstruction under a separately reviewed plan.

## 15. Common failure modes and safeguards

| Failure | Safe next step |
|---|---|
| Candidate lacks known rows | Check backup scope/cutoff and actual restore contents |
| Current ID differs from candidate | Preserve it and review the conflict |
| Missing ID outside confirmed incident set | Stop automatic repair; obtain business decision |
| Digest or UUID changed after review | Freeze writers; produce a new reviewed plan |
| Partial insert/restore/promotion | Preserve evidence; inspect exact current state before retry |
| Destination collection recreated | Reconcile replacement; never silently overwrite |
| Counts match but totals/metadata fail | Compare complete documents, references, indexes and validators |
| Auth/TLS failure | Correct identity/trust/name; retain security controls |

Do not assume `--stopOnError` rolls back already inserted documents. Avoid multiple concurrent restores into the same collection. Do not use blanket upserts, `--drop`, `dropTarget: true` or validator bypass as a shortcut to complete recovery.

Before returning application traffic, review ownership/permissions, query behavior, foreign references, consumers and application health. Retain rollback evidence and the previously validated candidate until the change is accepted under its retention policy.

## 16. Acceptance and guarded cleanup

Acceptance requires two successful captures, sealed artifacts, incident evidence, verified baseline candidate, reviewed insert-only plan/approval, preserved newer writes, verified staging metadata, non-overwriting promotion and final live data/storage/constraint checks. Static/helper tests cannot satisfy these runtime requirements.

Once acceptance evidence is reviewed, clean only this controller's completed fixture:

```bash
export ACTION53=cleanup
admin53
```

Cleanup requires the final promoted phase, matching acceptance run ID, exact source/candidate documents and stored UUIDs. Changed objects stop it. No chapter-created user exists to remove; the retained administrator and TLS/server configuration are unchanged. Verify independent administrator access after cleanup.

Partial lab failures require inspected, explicit owned-object cleanup rather than weakening guards. Retain artifacts, plans and evidence under the lab policy. Do not expire production recovery artifacts or keys to tidy an exercise.

## 17. References and next chapter

- [MongoDB 8.0 deleteMany](https://www.mongodb.com/docs/v8.0/reference/method/db.collection.deletemany/)
- [MongoDB 8.0 collection drop](https://www.mongodb.com/docs/v8.0/reference/method/db.collection.drop/)
- [MongoDB 8.0 renameCollection](https://www.mongodb.com/docs/v8.0/reference/command/renameCollection/)
- [mongorestore options and limitations](https://www.mongodb.com/docs/database-tools/mongorestore/)
- [Previous: Chapter 52 — Ops Manager Backup and Point in Time Recovery](52-ops-manager-backup-and-point-in-time-recovery.md)

Next: [**Chapter 54 — Replica Set Disaster Recovery**](54-replica-set-disaster-recovery.md).
