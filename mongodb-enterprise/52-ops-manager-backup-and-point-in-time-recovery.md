# 52 — Ops Manager Backup and Point in Time Recovery

Part 7 — Backup Recovery and Disaster Recovery

**Baseline:** MongoDB Enterprise 8.0/FCV 8.0 and a compatible, approved Ops Manager/Agent release.  
**Status:** Written; static review complete; live Ops Manager backup/PITR validation pending.  
**Prerequisites:** Chapters 49–51, an authorized Ops Manager lab, dedicated source/recovery replica sets, TLS, backup storage and recovery credentials.

## 1. Define the managed recovery claim

This lab enables continuous backup for a dedicated replica set, waits for a completed base snapshot, makes a legitimate update and records its exact oplog barrier. It then deletes known rows and adds a later write. Ops Manager restores the clean barrier into a different, disposable managed replica set. Verification proves the legitimate update was replayed while the deletion and later write were excluded.

A completed snapshot alone cannot prove point-in-time recovery. The exercise must show a usable snapshot/replay chain, a selected point in an available recovery range and correct recovered application state. Backup job health and recovery success are separate observations.

Ops Manager is a licensed, versioned management platform with its own infrastructure. This chapter uses an already provisioned authorized lab; it does not pretend a standalone Docker server contains Ops Manager. Without that platform, mark the managed lab **blocked** and run only the offline cutoff-planning helper. Do not substitute Chapter 50's oplog dump for a managed PITR result.

## 2. Separate the control plane and recoverable data

| Component | Responsibility | Recovery dependency |
|---|---|---|
| Ops Manager application | Project configuration, job orchestration and restore requests | Application database, configuration and administrator access |
| MongoDB Agent backup function | Consistent capture and oplog collection | Correct host placement, compatibility, credentials and network |
| Backup daemons/services | Store-specific snapshot/restore processing | Capacity, health and supported failover design |
| Snapshot store | Retained base/incremental snapshot artifacts | Data and associated metadata, retrieval authorization |
| Oplog store | Captured history needed for supported PITR | Continuous available history through the selected cutoff |
| Recovery deployment | Isolated materialization and validation | Compatible server, storage, TLS, keys and application access |

For modern supported FCVs, consistent capture uses the storage-engine backup mechanism; do not describe every current backup as an initial-sync clone. Snapshot transfer paths depend on platform release and store configuration. Pin the deployed versions before designing their placement and capacity.

Ops Manager's application/store backups are a separate recovery responsibility. Losing the management plane, backing metadata or key access can make retained data operationally inaccessible. Document how to recover that plane independently from the protected application cluster.

## 3. Verify compatibility, entitlement and topology

Record exact Ops Manager, Agent, MongoDB and restore-utility versions, server edition/modules, FCV, operating systems and selected store types. Verify the installed release's compatibility matrix and system requirements for both managed servers and backing databases; these are different matrices.

Use a dedicated three-member source replica set named **`rs52`**, all data-bearing, with a healthy primary and majority available. Use a separate managed recovery replica set named **`rs52recovery`**, with different hosts and a reviewed disposable target ID. Provision its capacity to fit the complete restored deployment. Neither is the retained Chapter 41/51 standalone or Chapter 35 sharded cluster.

The source must contain no unrelated application data. The controller rejects database names outside `admin`, `config`, `local` and this chapter's fixture database. Administrative databases still contain sensitive identity/configuration data; the whole-deployment backup and restore scope must be approved.

Configure client/Agent/server TLS with valid DNS names and CA chains. Record recovery authentication and encryption/key dependencies. Do not disable TLS validation to solve connectivity problems. The exact automation configuration and certificates belong to this new lab.

## 4. Prepare backup stores and least-privilege operations

In the Ops Manager administration interface, verify the backup service is enabled and healthy. Review configured **Snapshot Storage**, **Oplog Storage** and backup daemon/service assignments. Use the supported store setup procedure for the installed release: MongoDB-backed, S3-compatible or filesystem configuration differs.

Before enabling capture, confirm:

- Required stores can accept assignments and have sufficient capacity, retention and supported write/durability settings.
- Agent-to-server, Agent-to-Ops Manager and service-to-store connections use approved identities and trust.
- Object-store encryption, metadata, key access and regional placement satisfy the failure model.
- Restore operators can access the required recovery path without relying solely on the source host.
- Project roles permit the selected backup/restore operation; a database administrator role alone does not grant Ops Manager project authority.

Do not switch an existing store's connection to an empty database or bucket and assume its history moves automatically. Treat store migration, deletion protection and management-plane recovery as separate reviewed procedures.

This lab uses an authorized database lab administrator for fixture setup/verification. Agent credentials are platform-managed and must not be copied into scripts. Temporary restore/download links and generated restore commands can carry secrets; keep them out of Git, screenshots and general evidence files.

## 5. Enable continuous backup and record the actual policy

Open the dedicated project's deployment/Continuous Backup view, select **`rs52`** and enable backup using the installed release's workflow. Confirm the Agent backup function is enabled where required, its server access succeeds and the initial capture begins. Investigate a misconfigured or stopped job before proceeding.

From **Continuous Backup → Overview**, open the backup's settings and **Edit Snapshot Schedule**. Select supported schedule/retention values. A teaching policy can use a supported six-hour base schedule and seven days of PITR history, where the selected release/store supports those settings. Keep the actual saved settings as evidence; do not invent an unsupported field or value.

Record base/daily/weekly/monthly retention separately from **Allow point-in-time restores going back**. An on-demand snapshot does not enable continuous replay collection by itself. Increasing retention does not recreate history already expired or missing.

Record the job ID, project ID, source cluster ID, store assignments, region, actual policy and current recovery ranges. The visible restorable ranges, rather than the policy's desired number of days, govern point selection. A gap must remain visible in the recovery assessment.

## 6. Create the evidence workspace and fresh clients

Use the source and recovery connection details supplied by the lab's approved provisioning procedure. Both URIs must use the expected replica-set option and contain no credentials. Do not point either URI at the original production deployment.

```bash
umask 077
mkdir mongodb-ch52
cd mongodb-ch52
export LAB52_ROOT="$PWD"
mkdir scripts evidence
export SOURCE52_URI='mongodb://source52a.example.test:27017,source52b.example.test:27017,source52c.example.test:27017/admin?replicaSet=rs52'
export RECOVERY52_URI='mongodb://recovery52a.example.test:27017,recovery52b.example.test:27017,recovery52c.example.test:27017/admin?replicaSet=rs52recovery'
export CA52_FILE='/absolute/path/to/approved-lab-ca.crt'
export ADMIN52_USER='approved_lab_database_admin'
test -f "$CA52_FILE"
```

Replace the `.example.test` hostnames and username with the provisioned lab values. This chapter does not create a universal default Ops Manager password or publish guessed install commands.

Save Section 7's controller as `scripts/control52.js`. These clients require a supported installed `mongosh` and prompt for the secret:

```bash
source52() {
  TARGET52=source mongosh "$SOURCE52_URI" --tls --tlsCAFile "$CA52_FILE" \
    --username "$ADMIN52_USER" --authenticationDatabase admin \
    --authenticationMechanism SCRAM-SHA-256 --password \
    --file "$LAB52_ROOT/scripts/control52.js"
}
recovery52() {
  TARGET52=recovery mongosh "$RECOVERY52_URI" --tls --tlsCAFile "$CA52_FILE" \
    --username "$ADMIN52_USER" --authenticationDatabase admin \
    --authenticationMechanism SCRAM-SHA-256 --password \
    --file "$LAB52_ROOT/scripts/control52.js"
}
export ACTION52=setup
```

Use a fresh process for each action. Automation may manage recovery users/credentials; confirm the target's final approved administrator identity before validation. Use the reviewed authentication adapter if this lab uses x509 rather than weakening its authentication policy.

## 7. Implement a guarded recovery fixture

The script stores its ownership marker and original UUIDs externally. Clean verification checks every order, the clean marker, index and validator. The exact marker insert timestamp is read from the primary's oplog after majority acknowledgment; wall-clock time is supplementary evidence.

```javascript
const fs = require('fs');
const crypto = require('crypto');
const a = db.getSiblingDB('admin');
const D = 'mongodb_enterprise_tutorial_ch52';
const d = db.getSiblingDB(D);
const target = process.env.TARGET52;
const action = process.env.ACTION52;
const root = process.env.LAB52_ROOT;
if (!root) throw new Error('LAB52_ROOT required');
const statePath = `${root}/evidence/state52.json`;
const base = Array.from({length: 100}, (_, n) => ({
  _id: n + 1, code: `order-${n + 1}`, amountCents: (n + 1) * 10}));
const clean = base.map(row => row._id === 1 ? {...row, amountCents: 1010} : row);
const later = {_id: 101, code: 'order-101', amountCents: 1010};
const damaged = [...clean.slice(0, 80), later];
const validator = {$jsonSchema: {bsonType: 'object',
  required: ['_id', 'code', 'amountCents'], properties: {
    code: {bsonType: 'string'}, amountCents: {bsonType: 'number', minimum: 0}}}};
function check(value, message) { if (!value) throw new Error(message); }
function eq(x, y) { return EJSON.stringify(x, {relaxed: true}) ===
  EJSON.stringify(y, {relaxed: true}); }
function save(name, value) {
  fs.writeFileSync(`${root}/evidence/${name}`, EJSON.stringify(value, {relaxed: false}),
    {flag: 'wx', mode: 0o600});
}
function uuidMap() { return Object.fromEntries(d.getCollectionInfos().map(i =>
  [i.name, EJSON.stringify(i.info.uuid, {relaxed: false})])); }
function marker(id, state) { return {_id: id, runId: state.runId, chapter: 52}; }
function verify(state, phase) {
  check(eq(d.getCollectionInfos().map(i => i.name).sort(), ['markers', 'orders']),
    'unexpected collections');
  const current = uuidMap();
  for (const name of ['markers', 'orders'])
    check(current[name] === state.uuids[name], 'physical collection identity mismatch');
  const expected = phase === 'base' ? base : phase === 'clean' ? clean : damaged;
  const actual = d.orders.find().sort({_id: 1}).toArray();
  check(eq(actual, expected), 'exact order reconciliation failed');
  const ids = phase === 'base' ? ['owner'] : phase === 'clean'
    ? ['clean', 'owner'] : ['bad', 'clean', 'owner'];
  check(eq(d.markers.find().sort({_id: 1}).toArray(), ids.map(id => marker(id, state))),
    'marker state mismatch');
  const indexes = d.orders.getIndexes();
  check(indexes.length === 2 && indexes.some(i => i.name === 'code_unique52'
    && i.unique === true && eq(i.key, {code: 1})), 'index mismatch');
  const options = d.getCollectionInfos({name: 'orders'})[0].options;
  check(eq(options.validator, validator) && options.validationLevel === 'strict'
    && options.validationAction === 'error', 'validator mismatch');
  const sum = actual.reduce((value, row) => value + row.amountCents, 0);
  check(sum === (phase === 'base' ? 50500 : phase === 'clean' ? 51500 : 34410),
    'business total mismatch');
  return {phase, count: actual.length, amountCents: sum, uuids: current,
    digest: crypto.createHash('sha256')
      .update(EJSON.stringify(actual, {relaxed: false})).digest('hex')};
}
const hello = a.runCommand({hello: 1});
check(hello.ok === 1 && hello.isWritablePrimary === true && hello.msg !== 'isdbgrid',
  'connect to the intended replica-set primary');
check(hello.setName === (target === 'source' ? 'rs52' :
  target === 'recovery' ? 'rs52recovery' : ''), 'unexpected target replica set');
const build = a.runCommand({buildInfo: 1});
const fcv = a.runCommand({getParameter: 1, featureCompatibilityVersion: 1});
check(build.ok === 1 && build.version.startsWith('8.0.') &&
  build.modules.includes('enterprise') && fcv.ok === 1 &&
  fcv.featureCompatibilityVersion.version === '8.0', 'Enterprise 8.0 stable baseline required');
const inventory = a.runCommand({listDatabases: 1, nameOnly: true});
check(inventory.ok === 1 && inventory.databases.every(x =>
  ['admin', 'config', 'local', D].includes(x.name)), 'dedicated lab deployment required');
if (action === 'setup') {
  check(target === 'source' && !fs.existsSync(statePath), 'fresh source/state required');
  check(d.getCollectionInfos().length === 0 && d.getUsers().users.length === 0 &&
    d.getRoles({showBuiltinRoles: false}).roles.length === 0, 'existing fixture objects');
  const state = {runId: crypto.randomUUID(), serverVersion: build.version};
  d.createCollection('orders', {validator, validationLevel: 'strict', validationAction: 'error'});
  d.createCollection('markers');
  d.orders.createIndex({code: 1}, {unique: true, name: 'code_unique52'});
  d.orders.insertMany(base, {writeConcern: {w: 'majority', j: true}});
  d.markers.insertOne(marker('owner', state), {writeConcern: {w: 'majority', j: true}});
  state.uuids = uuidMap();
  save('state52.json', state);
  save('baseline52.json', {runId: state.runId, observedAt: new Date(), result: verify(state, 'base')});
  print('Baseline ready. Wait for a completed Ops Manager snapshot before clean-update.');
} else {
  const state = EJSON.parse(fs.readFileSync(statePath, 'utf8'));
  check(build.version === state.serverVersion, 'exact server version differs');
  if (action === 'clean-update') {
    check(target === 'source', 'source action required'); verify(state, 'base');
    const update = d.orders.updateOne({_id: 1}, {$set: {amountCents: 1010}},
      {writeConcern: {w: 'majority', j: true}});
    check(update.modifiedCount === 1, 'clean update failed');
    d.markers.insertOne(marker('clean', state), {writeConcern: {w: 'majority', j: true}});
    const entry = db.getSiblingDB('local').oplog.rs.findOne({
      ns: `${D}.markers`, op: 'i', 'o._id': 'clean', 'o.runId': state.runId});
    check(entry && entry.ts, 'clean oplog barrier missing');
    save('clean52.json', {runId: state.runId, observedAt: new Date(),
      cleanTimestamp: entry.ts, result: verify(state, 'clean')});
    print('Select this exact cleanTimestamp using inclusive Oplog Timestamp restore.');
  } else if (action === 'damage') {
    check(target === 'source', 'source action required'); verify(state, 'clean');
    const removed = d.orders.deleteMany({_id: {$gte: 81, $lte: 100}},
      {writeConcern: {w: 'majority', j: true}});
    check(removed.deletedCount === 20, 'unexpected deletion count');
    d.orders.insertOne(later, {writeConcern: {w: 'majority', j: true}});
    d.markers.insertOne(marker('bad', state), {writeConcern: {w: 'majority', j: true}});
    const entry = db.getSiblingDB('local').oplog.rs.find({ns: `${D}.orders`,
      op: 'd', 'o._id': {$gte: 81, $lte: 100}}).sort({ts: 1}).limit(1).next();
    check(entry && entry.ts, 'deletion oplog boundary missing');
    save('incident52.json', {runId: state.runId, observedAt: new Date(),
      firstBadTimestamp: entry.ts, result: verify(state, 'damaged')});
    print('Source damaged: 81 rows, 34410 cents; later order 101 is outside clean recovery.');
  } else if (action === 'verify-source') {
    check(target === 'source', 'source action required'); printjson(verify(state, 'damaged'));
  } else if (action === 'verify-recovery') {
    check(target === 'recovery', 'recovery action required');
    const result = verify(state, 'clean');
    const validation = d.runCommand({validate: 'orders', full: true});
    check(validation.ok === 1 && validation.valid === true &&
      (!validation.errors || validation.errors.length === 0) &&
      (!validation.warnings || validation.warnings.length === 0), 'review storage validation');
    for (const [doc, code] of [
      [{_id: 'negative-duplicate52', code: 'order-1', amountCents: 1}, 11000],
      [{_id: 'negative-validator52', code: 'negative52', amountCents: -1}, 121]
    ]) {
      let rejected = false;
      try { d.orders.insertOne(doc); }
      catch (error) { if (error.code !== code) throw error; rejected = true; }
      check(rejected, 'constraint unexpectedly accepted insert; investigate');
    }
    verify(state, 'clean');
    save('recovered52.json', {runId: state.runId, observedAt: new Date(), result,
      validation, duplicateRejected: true, validatorRejected: true});
    print('Clean barrier restored, including update and excluding deletion/later write.');
  } else throw new Error('unknown ACTION52');
}
```

No background writer or TTL index exists in this fixture. Keep its scope idle except for these actions. Each phase refuses unexpected prior state and saves evidence exclusively. If a phase partially fails, inspect ownership and actual data; do not rerun blindly or change expected totals to match a failure.

## 8. Complete the base snapshot before replay-only changes

```bash
export ACTION52=setup
source52
```

In Ops Manager, inspect the source's Continuous Backup job. Wait until a full usable base snapshot is completed after fixture setup. Request an on-demand snapshot if supported by the installed workflow; record its ID, completion, source cluster and timestamp. Do not proceed during initial capture.

Review Agent/job errors, store capacity and the displayed recovery range. Confirm the baseline snapshot represents the fixture before the clean update. Preserve the selected snapshot record; later scheduled captures must not obscure which base/replay chain the restore actually used.

Do not claim an initial-snapshot completion from a scheduled timestamp or a backup-enabled toggle. Completion and subsequent recovery availability require actual platform observations.

## 9. Create the clean barrier and later incident

```bash
export ACTION52=clean-update
source52
```

Inspect `clean52.json`: 100 orders and **51,500 cents**, with `cleanTimestamp` encoded as `{"$timestamp":{"t":...,"i":...}}`. The legitimate change adds 1,000 cents to order 1 after the base snapshot. Record both timestamp seconds and increment; omitting the increment loses operation ordering within a second.

Wait until Ops Manager's restorable range includes this exact point, and record the observed range/job status. Keep the fixture idle while doing so. Then inject the controlled deletion:

```bash
date -u +'%Y-%m-%dT%H:%M:%SZ' > evidence/incident-declared52.txt
export ACTION52=damage
source52
```

Source now has 81 orders and **34,410 cents**: IDs 81–100 were removed, while later order 101 was added. `incident52.json` records the earliest deletion timestamp. The selected clean barrier must precede it. The later legitimate write is intentionally omitted by the clean-point recovery and would need separate reconciliation in a real incident.

Continue collecting backup history and wait until the platform range also covers the incident. Do not stop capture immediately after issuing the deletion and assume the chain is complete.

## 10. Validate the requested cutoff before submitting restore

Ops Manager's **date/time** PITR selection excludes operations at the selected time, whereas **Oplog Timestamp** selection includes the exact entered timestamp. This lab uses the latter and enters the clean marker's `t` and `i`. Do not round it to a wall-clock second or select the first bad operation itself.

Save as `scripts/cutoff52.py`. It assesses a declared selection against one observed continuous range, requiring the exact clean barrier. It does not query Ops Manager or certify the evidence supplied by the operator.

```python
#!/usr/bin/env python3
import json
import sys

FIELDS = {'format', 'kind', 'run_id', 'source_cluster_id', 'target_cluster_id',
          'snapshot_id', 'selection', 'selected', 'clean', 'first_bad',
          'range_start', 'range_end', 'range_verified'}

def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError('duplicate field')
        result[key] = value
    return result

def stamp(value):
    if not isinstance(value, dict) or set(value) != {'t', 'i'}:
        raise ValueError('timestamp requires t and i')
    for key in ('t', 'i'):
        if type(value[key]) is not int or not 0 <= value[key] <= 4294967295:
            raise ValueError('timestamp components must be uint32 integers')
    return value['t'], value['i']

def evaluate(data):
    if not isinstance(data, dict) or set(data) != FIELDS:
        raise ValueError('missing or unknown fields')
    if type(data['format']) is not int or data['format'] != 1:
        raise ValueError('unsupported format')
    if data['kind'] not in ('synthetic', 'drill') or data['selection'] != 'oplog_inclusive':
        raise ValueError('unsupported kind/selection')
    for key in ('run_id', 'source_cluster_id', 'target_cluster_id', 'snapshot_id'):
        if not isinstance(data[key], str) or not data[key].strip():
            raise ValueError('identity fields required')
    if data['source_cluster_id'] == data['target_cluster_id']:
        raise ValueError('restore target must differ from source')
    if type(data['range_verified']) is not bool:
        raise ValueError('range_verified must be boolean')
    selected, clean, bad, start, end = [stamp(data[k]) for k in
        ('selected', 'clean', 'first_bad', 'range_start', 'range_end')]
    if start > end or clean >= bad:
        raise ValueError('range or clean/incident ordering invalid')
    checks = {'exact_clean_barrier': selected == clean,
              'before_first_bad': selected < bad,
              'within_observed_range': start <= selected <= end,
              'range_verified': data['range_verified']}
    return {'kind': data['kind'], 'run_id': data['run_id'], 'checks': checks,
            'claim': 'planning_only' if data['kind'] == 'synthetic'
                     else 'declared_selection_only',
            'declared_selection_valid': all(checks.values())}

def main():
    try:
        if len(sys.argv) != 2:
            raise ValueError('usage: cutoff52.py plan.json')
        with open(sys.argv[1], encoding='utf-8') as source:
            data = json.load(source, object_pairs_hook=pairs)
        result = evaluate(data)
        print(json.dumps(result, indent=2))
        return 0 if result['declared_selection_valid'] else 2
    except (OSError, ValueError, TypeError) as error:
        print(str(error), file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
```

This synthetic example is for offline arithmetic/ordering validation only. Save it as `evidence/synthetic-plan52.json`:

```json
{
  "format": 1,
  "kind": "synthetic",
  "run_id": "planning-only-52",
  "source_cluster_id": "synthetic-source",
  "target_cluster_id": "synthetic-target",
  "snapshot_id": "synthetic-base",
  "selection": "oplog_inclusive",
  "selected": {"t": 1791712800, "i": 2},
  "clean": {"t": 1791712800, "i": 2},
  "first_bad": {"t": 1791712800, "i": 3},
  "range_start": {"t": 1791712700, "i": 0},
  "range_end": {"t": 1791712900, "i": 10},
  "range_verified": true
}
```

```bash
python3 scripts/cutoff52.py evidence/synthetic-plan52.json
```

Exit 0 means declared inputs pass; exit 2 means a valid plan fails a check; exit 1 means invalid input. A synthetic pass always says `planning_only`.

For the real drill, create a separate `drill-plan52.json` with actual IDs, `kind: drill`, exact marker timestamps and one actual available continuous range. Set `range_verified` only after reviewing its source evidence. If the UI shows only wall-clock endpoints, do not invent an increment: verify the selected oplog point is accepted by the installed platform and obtain its supported range representation. Keep gap, wrong-target, excluded-barrier and unverified-range tests separate from the live plan.

## 11. Restore to a different disposable managed cluster

Before submitting, verify the recovery target's project/cluster ID, replica-set name, hostnames, storage paths, version, isolation and disposable ownership. It must have no ordinary application clients and no valuable existing data. Record the approval/change reference and before-state inventory.

Use **Continuous Backup → Overview → source deployment → Restore or Download**. Select **Oplog Timestamp**, enter the clean `t` and increment, and confirm the point lies in an offered recovery range. Then choose the option to restore to another cluster. Select the reviewed **`rs52recovery`** target in the correct project and recheck its immutable cluster ID before submitting.

Automated restore removes the target's existing data. It is not a selective merge and is not permission to restore onto the source. Use only the dedicated disposable target authorized by this lab. Capture job ID, selected cutoff, source/target IDs, submitted time and delivery mode without recording credential-bearing URLs.

Monitor Restore History and Agent/automation progress until the operation completes or fails. A request accepted by the UI/API is not a completed restore. Retain failure details and use a reviewed fresh-target/reset workflow for retries; do not assume the delivery system retries safely or leaves no partial state.

If the restored target's automation changes authentication settings, follow the final target's approved identity procedure. Preserve authentication and TLS on its application-facing deployment. Do not bootstrap a new user by disabling security.

## 12. Validate the restored point and application contract

```bash
export ACTION52=verify-recovery
recovery52
export ACTION52=verify-source
source52
```

Review `recovered52.json` against `clean52.json`. The expected recovered state is:

| Observation | Clean PITR target | Damaged source |
|---|---:|---:|
| Orders | 100 | 81 |
| Amount cents | 51,500 | 34,410 |
| Order 1 amount | 1,010 | 1,010 |
| Orders 81–100 | Present | Absent |
| Later order 101 | Absent | Present |
| `clean` marker | Present | Present |
| `bad` marker | Absent | Present |

The clean-update presence distinguishes PITR from merely recovering the earlier base snapshot, whose total was 50,500 cents. The deletion and later marker absence establish the intended barrier for this fixture. Exact document digest, UUIDs, indexes, validator, storage validation and live rejection tests provide additional checks.

Validate the recovery replica set's member health, majority availability and approved authentication through fresh clients. Run the application's actual read/write smoke contract on an owned test scope before cutover. This tutorial has no production application cutover; label its elapsed time as managed lab recovery acceptance, not demonstrated production RTO.

## 13. Understand the manual restore path and MBRU

Automated delivery is the primary path here. If an unmanaged target requires manual recovery, follow the installed release's full procedure and generated restore instructions. Preserve `restoreInfo.txt`, which describes version, engine, timestamps, startup options and encryption dependencies. Verify the utility download's trusted origin/version and artifact integrity.

The MongoDB Backup Restore Utility (MBRU) obtains/applies the needed replay history in the manual PITR workflow. It is not `mongorestore --oplogReplay`, and copying snapshot files alone does not finish that workflow. Generated timestamp/identity parameters must come from this restore job, never from another cluster's example.

The documented manual path includes temporary recovery processing with authentication unavailable to MBRU. If that path is necessary, confine it to the isolated recovery host/network with no application ingress, preserve required TLS verification, and restore final authentication before exposure. Do not copy generic no-authentication commands into an application-facing server. Treat generated API keys and URLs as secrets under the recovery credential-handling procedure.

Manual recovery also requires the release-specific replication initialization, recovery and final restart stages. Do not edit `local` replication metadata or invent startup flags from memory. This chapter intentionally uses managed delivery to avoid presenting a partial manual sequence as a complete recoverable procedure.

Encrypted restores require the matching key/KMIP access and the documented post-restore handling. Snapshot-store encryption and the server's encrypted storage engine are separate controls. Follow the exact Ops Manager cipher/version instructions in addition to Chapter 45; do not assume TLS or a downloadable archive replaces them.

## 14. Monitor recovery ranges and rehearse gaps

| Observation | Operational response |
|---|---|
| Snapshot fails or initial capture incomplete | Inspect source/Agent access, capacity and service/store health |
| Oplog collection falls behind | Measure latest usable cutoff and source oplog window; repair collection path |
| Gap in restorable ranges | Select another valid clean point or declare objective failure; no bridging assumption |
| Source rollback/election | Inspect backup state and platform reconciliation; verify the resulting ranges |
| Store/key unavailable | Recover access without abandoning integrity/authorization controls |
| Restore job fails | Preserve diagnostics; validate/reset only the owned disposable target |
| Green job but wrong documents | Investigate cutoff semantics, IDs and actual replay chain |

Set alerts for backup errors, stale usable recovery points, store saturation and restore failures. A scheduled policy and green process do not alone demonstrate RPO compliance.

For a negative drill, choose a timestamp outside the observed range and verify the platform rejects it before destructive delivery. Do not create a real gap by disabling shared Agents or deleting store history. Collector interruption tests require a separately owned platform scope and an explicit outage/recovery plan.

## 15. Measure objectives and preserve evidence

The evidence package includes the recovery contract, exact compatibility inventory, policy/store assignments, completed snapshot, actual restorable ranges, clean/first-bad timestamps, source/target IDs, restore job history and restored application checks. Keep all observations tied to one run ID.

Measure RTO from the declared incident boundary through validated application acceptance, including provisioning, delivery, replay and credentials/keys. Record detection delay and intermediate timings separately. Use Chapter 49's evaluator with real source evidence; do not infer RTO from UI job duration alone.

Recovery-point age is measured relative to the chosen clean point and incident definition. For this corruption scenario, later legitimate order 101 is intentionally excluded, not silently recovered. In a real incident, identify and replay/reconcile valid post-cutoff operations through a separate approved process.

Do not claim zero RPO from successful majority writes or a clean barrier restore. The complete acknowledged operation set, failure domain and retention/replay availability determine the recovery claim.

## 16. Acceptance and cleanup without deleting history

Accept the managed lab only after actual completed capture, verified inclusive cutoff in a valid range, successful delivery to the different target, exact clean state and live data/constraint/replica-set checks. Offline helper success is planning validation only. Without Ops Manager, retain the blocked reason and leave runtime acceptance pending.

Archive the protected evidence and decide retention for the lab deployment/artifacts. Use the installed release's documented stop/unmanage/decommission workflows for the dedicated resources, reviewing IDs before changes. Do not remove shared Agents, daemons, backing databases, buckets or key versions.

Stopping a backup and terminating it have different history consequences: a stop ceases new capture while retained artifacts follow their policy; termination can delete retained snapshots. Review the exact release's behavior before selecting either. Tutorial cleanup does not authorize terminating an unrelated job or purging a shared store.

If keeping the source/recovery deployments for Chapter 53, leave their authentication/TLS intact and record their current phase. Source remains damaged and target is clean; do not pretend both are reset. If decommissioning, use the provisioning system's owned-resource cleanup after recording data/backup retention decisions. No generic database-drop or whole-store deletion command is supplied.

## 17. References and next chapter

- [Ops Manager MongoDB compatibility matrix](https://www.mongodb.com/docs/ops-manager/current/reference/mongodb-compatibility/)
- [Ops Manager system requirements](https://www.mongodb.com/docs/ops-manager/current/core/requirements/)
- [Backup process](https://www.mongodb.com/docs/ops-manager/current/core/backup-overview/)
- [Backup preparations and retention](https://www.mongodb.com/docs/ops-manager/current/core/backup-preparations/)
- [Edit snapshot schedule and backup settings](https://www.mongodb.com/docs/ops-manager/current/tutorial/edit-backup/)
- [Restore overview](https://www.mongodb.com/docs/ops-manager/current/tutorial/nav/restore-overview/)
- [Replica-set restore and timestamp semantics](https://www.mongodb.com/docs/ops-manager/current/tutorial/restore-replica-set/)
- [Previous: Chapter 51 — Consistent Snapshots and Restore Validation](51-consistent-snapshots-and-restore-validation.md)

Use documentation for the installed Ops Manager release rather than assuming that the moving `current` documentation matches it.

Next: [**Chapter 53 — Accidental Delete and Drop Recovery**](53-accidental-delete-and-drop-recovery.md).
