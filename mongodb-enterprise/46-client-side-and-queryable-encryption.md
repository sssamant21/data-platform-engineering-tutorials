# 46 — Client Side and Queryable Encryption

Part 6 — Enterprise Security and Governance

**Baseline:** MongoDB 8.0 replica set, Node.js driver 6.x and compatible `mongodb-client-encryption` 6.x; pin exact patches and record the native library version.  
**Status:** Written; static review complete; live driver, encrypted-query and recovery validation pending.  
**Prerequisites:** Chapters 41–45, a separate authorized TLS/authenticated replica-set lab, Python 3, Node.js and approved native encryption dependencies.

## 1. What client-side encryption changes

Chapter 45 protects server storage. This chapter protects selected fields before the application sends them to MongoDB. A database client without the field-encryption configuration sees ciphertext for those fields; an authorized application can decrypt them.

The application remains a plaintext trust boundary. Protect its runtime identity, KMS permissions, memory, logs, exception reporting and outbound integrations. TLS and database authorization remain necessary. Encrypting a field does not authorize a user to see its decrypted value or prevent a permitted application from exporting it.

The lab uses synthetic identifiers, never real patient or financial data. It compares explicit CSFLE and explicit Queryable Encryption (QE), verifies raw ciphertext and authorized results, then adds an automatic-QE path for an authorized Enterprise deployment. KMS-backed recovery and range queries receive separate acceptance runbooks.

## 2. Choose the feature and query contract

| Approach | Query behavior | Design consequence |
|---|---|---|
| CSFLE deterministic | Equality through encryption of the predicate | Equal values produce equal ciphertext; consider frequency leakage |
| CSFLE randomized | Encrypt/decrypt; no ordinary equality search on the protected value | Prefer for fields that need no query |
| QE equality | Encrypted equality queries with associated state | Different architecture from deterministic CSFLE |
| QE range on 8.0 | Supported numeric/date range predicates with defined bounds/types | Driver/native-library and schema options must match |
| Automatic encryption | Driver analyzes supported operations and encrypts configured fields | Requires the supported query-analysis component and edition entitlement |
| Explicit encryption | Application calls encryption APIs for values/predicates | Every write/query path must apply the intended contract |

CSFLE and QE cannot share the same collection. This lab uses `csfle_records` and `qe_records`. An ordinary plaintext index is not a substitute for QE collection metadata. Do not assume regex, arbitrary aggregation, joins, sorting or updates on an encrypted field work as they do on plaintext.

This chapter stays on the 8.0 contract: equality and range. Do not import newer string-query features from current-version documentation into an 8.0 lab. The obsolete `rangePreview` algorithm is not an 8.0 migration strategy.

## 3. Compatibility and topology gates

| Capability | Gate for this chapter |
|---|---|
| Explicit CSFLE | Supported driver and native encryption package; Community or Enterprise |
| Explicit QE and automatic decryption | Supported MongoDB 8.0 replica set/sharded deployment; Community or Enterprise |
| Automatic encryption | Authorized Enterprise or supported Atlas deployment plus query analysis |
| QE topology | Replica set or sharded cluster; no standalone |
| Driver/native package | Matched 6.x packages; exact versions and Node/OS/architecture support reviewed |
| Range extension | Driver release supporting GA 8.0 range, native package at least 6.1.0 in the 6.x track |
| Query analysis | Approved `crypt_shared` library matching the reviewed platform/version contract |

The Chapter 45 standalone is **not** the QE target. Provision a separate disposable TLS-enabled MongoDB 8.0 replica set using the topology and access-control procedures from Chapters 26 and 41–42. This chapter accepts its existing connection string; it does not convert the retained standalone or mutate the sharded lab.

Record server patch/FCV, replica-set name, members, driver/native package, `libmongocrypt`, Node, OS and architecture. A successful npm install proves dependency installation, not server or encryption compatibility. An unavailable gate is blocked, not passed.

## 4. Customer master keys, data keys and key vaults

| Item | Location/purpose | Required recovery dependency |
|---|---|---|
| Customer master key (CMK) | KMS or this lab's private 96-byte local material | Usable provider key and authorized application identity |
| Data encryption key (DEK) | Wrapped `keyMaterial` in the key-vault document | Exact key-vault record and CMK access |
| DEK UUID | Referenced by ciphertext/schema | UUID must still resolve to its original usable key |
| `keyAltNames` | Human-readable lookup names | Unique partial index prevents duplicate aliases |
| QE metadata/state | Associated collections and indexes | Consistent backup with the encrypted user collection |
| Encryption schema/map | Trusted client configuration | Versioned, reviewed field/type/query contract |

The key vault is a MongoDB collection, not the external KMS. A backup of encrypted application records alone is incomplete. A key alias or UUID without the wrapped key document is also incomplete.

This lab's local KMS key is **96 raw bytes**, unlike Chapter 45's local storage key. Do not reuse a storage-encryption keyfile, a replica-set authentication keyfile or a TLS private key. Use a remote supported KMS and workload identity for a production deployment.

## 5. Prepare a private application workspace

Create a fresh client-side workspace on Linux. Use a dedicated administrator for provisioning, and an application user restricted to the new lab database.

```bash
umask 077
mkdir mongodb-ch46
cd mongodb-ch46
mkdir scripts secrets evidence
export URI46='mongodb://LAB-HOST1:27017,LAB-HOST2:27017,LAB-HOST3:27017/?replicaSet=LAB-SET'
export CA46='/absolute/path/to/lab-ca.crt'
export ADMIN46='YOUR-LAB-ADMIN'
export DRIVER_VERSION46='YOUR-APPROVED-EXACT-6.X-PATCH'
export ENCRYPTION_VERSION46='YOUR-APPROVED-EXACT-6.X-PATCH'
```

Replace the nonsecret values. The URI must contain no username/password; credentials are prompted separately. Retain TLS hostname verification and use resolvable member names matching their certificates. The scripts below require a replica-set URI and reject credential-bearing URIs.

Review exact versions against the official driver compatibility/release notes and native package's supported Node/platform matrix, then install pins:

```bash
npm init -y
npm install --save-exact "mongodb@${DRIVER_VERSION46:?set exact approved patch}" \
  "mongodb-client-encryption@${ENCRYPTION_VERSION46:?set exact approved patch}"
npm ls mongodb mongodb-client-encryption
node --version
```

Keep `package-lock.json`; use `npm ci` to reproduce that installation. This is deliberately not an unpinned `latest` recipe. No dependency combination is declared runtime-tested by this authored chapter.

Create the private local KMS key without printing it:

```bash
python3 - <<'PY'
import os
import pathlib
import secrets
path = pathlib.Path('secrets/local-kms46.bin')
with path.open('xb') as handle:
    os.chmod(path, 0o600)
    handle.write(secrets.token_bytes(96))
print('Private 96-byte local KMS fixture created; content not displayed')
PY
```

The key stays on the application side. Do not mount it into MongoDB, commit it, print it, or place it in the evidence bundle. The database credentials, key-vault access and KMS access are independent controls even though this teaching lab uses one private local key.

## 6. Prompt for credentials without command-line secrets

Save `scripts/run46.py`. It prompts with `getpass` and supplies credentials to a new Node process through stdin. Passwords are not put in environment variables, command arguments or evidence. Provisioning also prompts for a new scoped application password.

```python
import getpass
import json
import os
import subprocess
import sys

MODES = {'setup', 'csfle', 'qe', 'automatic', 'badkey', 'recover', 'cleanup'}
if len(sys.argv) != 2 or sys.argv[1] not in MODES:
    raise SystemExit('usage: run46.py setup|csfle|qe|automatic|badkey|recover|cleanup')
mode = sys.argv[1]
admin = mode in {'setup', 'cleanup'}
username = os.environ.get('ADMIN46') if admin else 'ch46_app'
if not username:
    raise SystemExit('ADMIN46 is required for provisioning/cleanup')
credentials = {'username': username, 'password': getpass.getpass('Database password: ')}
if mode == 'setup':
    credentials['appPassword'] = getpass.getpass('Choose new ch46_app password: ')
    if not credentials['appPassword']:
        raise SystemExit('Empty application password rejected')
result = subprocess.run(['node', 'scripts/lab46.cjs', mode],
                        input=json.dumps(credentials), text=True)
raise SystemExit(result.returncode)
```

Run from the workspace root. Use an interactive terminal, not a logging wrapper that records stdin or plaintext inputs. The application necessarily holds these values in memory; this launcher is a lab credential transport, not a secret-management agent.

## 7. Write shared guards and field contracts

Save `scripts/contracts46.cjs`. It has no database dependency and can be tested offline.

```javascript
'use strict';
const fs = require('node:fs');
const assert = require('node:assert/strict');
const DB = 'mongodb_enterprise_tutorial_ch46';
const KEYVAULT = DB + '.__keyVault';
const QE_NS = DB + '.qe_records';

function checkURI(uri) {
  assert.equal(typeof uri, 'string', 'URI46 required');
  assert.ok(uri.startsWith('mongodb://'), 'use the dedicated replica-set lab URI');
  const authority = uri.slice('mongodb://'.length).split('/')[0];
  assert.ok(!authority.includes('@'), 'credentials must not be embedded in URI');
  const query = uri.includes('?') ? uri.slice(uri.indexOf('?') + 1) : '';
  const params = new URLSearchParams(query);
  assert.ok(params.get('replicaSet'), 'replicaSet URI option required');
  for (const [key] of params) {
    assert.equal(key.toLowerCase(), 'replicaset', 'only replicaSet is accepted in the lab URI query');
  }
  assert.ok(!params.has('authSource') && !params.has('authMechanism'),
    'authentication options are controlled by the lab client');
  return uri;
}
function localKey(path) {
  const stat = fs.lstatSync(path);
  assert.ok(stat.isFile() && !stat.isSymbolicLink(), 'regular private key file required');
  assert.equal(stat.uid, process.getuid(), 'key owner must match application process');
  assert.equal(stat.mode & 0o777, 0o600, 'key mode must be 0600');
  const key = fs.readFileSync(path);
  assert.equal(key.length, 96, 'local KMS key must be 96 raw bytes');
  return key;
}
function qeFields(keyId) {
  return {fields: [{path: 'patientCode', bsonType: 'string', keyId,
    queries: {queryType: 'equality', contention: 0}}]};
}
function ids(rows) { return rows.map(row => row._id).sort(); }
module.exports = {DB, KEYVAULT, QE_NS, checkURI, localKey, qeFields, ids};
```

`contention: 0` is for the tiny controlled fixture, not a production tuning recommendation. Provision a workload-specific contention policy and use the same contract on reads/writes. Only `patientCode` is QE-encrypted here; `_id` and `label` are deliberately readable synthetic metadata.

## 8. Provision keys and separate encrypted collections

Save the following complete application as `scripts/lab46.cjs`. It implements the subsequent exercises through named modes. Review its scope before running `setup` or `cleanup`.

```javascript
'use strict';
const fs = require('node:fs');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const {MongoClient, ClientEncryption, Binary, BSON} = require('mongodb');
const {DB, KEYVAULT, QE_NS, checkURI, localKey, qeFields, ids} = require('./contracts46.cjs');
const {EJSON} = BSON;
const mode = process.argv[2];
const allowed = new Set(['setup', 'csfle', 'qe', 'automatic', 'badkey', 'recover', 'cleanup']);
const statePath = 'evidence/state46.json';
const equal = (a, b) => EJSON.stringify(a, {relaxed: false}) === EJSON.stringify(b, {relaxed: false});
const ciphertext = value => value instanceof Binary && value.sub_type === 6;

async function main() {
  assert.ok(allowed.has(mode), 'unknown mode');
  let input = '';
  for await (const chunk of process.stdin) input += chunk;
  const credentials = JSON.parse(input);
  assert.ok(credentials.username && credentials.password, 'credentials required');
  const uri = checkURI(process.env.URI46);
  assert.ok(process.env.CA46, 'CA46 required');
  const adminMode = mode === 'setup' || mode === 'cleanup';
  const base = {tls: true, tlsCAFile: process.env.CA46,
    auth: {username: credentials.username, password: credentials.password},
    authSource: adminMode ? 'admin' : DB, authMechanism: 'SCRAM-SHA-256',
    serverSelectionTimeoutMS: 10000, appName: 'chapter46-' + mode};
  const raw = new MongoClient(uri, base);
  const extraClients = [];
  try {
    await raw.connect();
    const hello = await raw.db('admin').command({hello: 1});
    assert.ok(hello.setName, 'dedicated replica set required');
    const lab = raw.db(DB);
    if (mode === 'setup') {
      assert.ok(!fs.existsSync(statePath), 'state already exists; inspect partial/previous run');
      const build = await raw.db('admin').command({buildInfo: 1});
      assert.match(build.version, /^8\.0\./, 'review installed server version');
      const fcv = (await raw.db('admin').command({getParameter: 1,
        featureCompatibilityVersion: 1})).featureCompatibilityVersion;
      assert.equal(fcv.version, '8.0', 'FCV 8.0 required');
      assert.ok(!fcv.targetVersion && !fcv.previousVersion, 'FCV transition refused');
      const existingUsers = await lab.command({usersInfo: 1});
      assert.equal(existingUsers.users.length, 0, 'pre-existing users refused');
      assert.equal((await lab.listCollections().toArray()).length, 0, 'pre-existing collections refused');
      const roleInfo = await lab.command({rolesInfo: 1, showBuiltinRoles: false});
      assert.equal(roleInfo.roles.length, 0, 'pre-existing custom roles refused');
      assert.ok(credentials.appPassword, 'application password required');
      const kmsProviders = {local: {key: localKey('secrets/local-kms46.bin')}};
      const ce = new ClientEncryption(raw, {keyVaultNamespace: KEYVAULT, kmsProviders});
      await lab.createCollection('__keyVault');
      await lab.collection('__keyVault').createIndex({keyAltNames: 1}, {
        unique: true, partialFilterExpression: {keyAltNames: {$exists: true}}
      });
      const csfleId = await ce.createDataKey('local', {keyAltNames: ['ch46-csfle']});
      const qeId = await ce.createDataKey('local', {keyAltNames: ['ch46-qe']});
      await lab.createCollection('csfle_records', {validator: {$jsonSchema: {
        bsonType: 'object', required: ['patientCode', 'note'], properties: {
          patientCode: {encrypt: {keyId: [csfleId], bsonType: 'string',
            algorithm: 'AEAD_AES_256_CBC_HMAC_SHA_512-Deterministic'}},
          note: {encrypt: {keyId: [csfleId], bsonType: 'string',
            algorithm: 'AEAD_AES_256_CBC_HMAC_SHA_512-Random'}}
        }
      }}});
      const encryptedFields = qeFields(qeId);
      await ce.createEncryptedCollection(lab, 'qe_records', {
        provider: 'local', createCollectionOptions: {encryptedFields}
      });
      await lab.command({createUser: 'ch46_app', pwd: credentials.appPassword,
        mechanisms: ['SCRAM-SHA-256'], roles: [{role: 'readWrite', db: DB}],
        customData: {owner: 'chapter46-local-encryption-lab'}});
      const user = (await lab.command({usersInfo: 'ch46_app'})).users[0];
      const collections = (await lab.listCollections().toArray())
        .map(c => ({name: c.name, uuid: c.info.uuid})).sort((a, b) => a.name.localeCompare(b.name));
      const state = {owner: 'chapter46-local-encryption-lab', setName: hello.setName,
        version: build.version, fcv, modules: build.modules, userId: user.userId,
        csfleId, qeId, encryptedFields, collections, createdAt: new Date()};
      fs.writeFileSync(statePath, EJSON.stringify(state, {relaxed: false}), {flag: 'wx', mode: 0o600});
      console.log(JSON.stringify({setup: 'complete', version: build.version,
        modules: build.modules, libmongocrypt: ClientEncryption.libmongocryptVersion,
        collectionNames: collections.map(c => c.name)}));
      return;
    }
    const state = EJSON.parse(fs.readFileSync(statePath, 'utf8'), {relaxed: false});
    assert.equal(state.owner, 'chapter46-local-encryption-lab');
    assert.equal(hello.setName, state.setName, 'wrong replica set');
    if (mode === 'cleanup') {
      const users = (await lab.command({usersInfo: 1})).users;
      assert.equal(users.length, 1, 'unexpected database identities');
      assert.equal(users[0].user, 'ch46_app');
      assert.ok(equal(users[0].userId, state.userId), 'user identifier mismatch');
      assert.equal(users[0].customData?.owner, state.owner);
      const roles = (await lab.command({rolesInfo: 1, showBuiltinRoles: false})).roles;
      assert.equal(roles.length, 0, 'unexpected custom roles');
      const collections = (await lab.listCollections().toArray())
        .map(c => ({name: c.name, uuid: c.info.uuid})).sort((a, b) => a.name.localeCompare(b.name));
      assert.ok(equal(collections, state.collections), 'collection ownership inventory mismatch');
      const keys = await lab.collection('__keyVault').find({}).toArray();
      assert.equal(keys.length, 2, 'unexpected key-vault records');
      assert.ok(keys.some(k => equal(k._id, state.csfleId)) && keys.some(k => equal(k._id, state.qeId)));
      assert.equal(process.env.DISPOSE46, 'owned-fixture-and-keys', 'explicit disposal scope required');
      await lab.command({dropUser: 'ch46_app'});
      await lab.dropDatabase();
      fs.renameSync(statePath, 'evidence/state46.disposed.json');
      console.log('Owned fixtures, QE state and key-vault records removed');
      return;
    }
    const masterKey = mode === 'badkey' ? crypto.randomBytes(96) : localKey('secrets/local-kms46.bin');
    const kmsProviders = {local: {key: masterKey}};
    const ce = new ClientEncryption(raw, {keyVaultNamespace: KEYVAULT, kmsProviders});
    const csfle = lab.collection('csfle_records');
    const deterministic = value => ce.encrypt(value, {keyId: state.csfleId,
      algorithm: 'AEAD_AES_256_CBC_HMAC_SHA_512-Deterministic'});
    const randomized = value => ce.encrypt(value, {keyId: state.csfleId,
      algorithm: 'AEAD_AES_256_CBC_HMAC_SHA_512-Random'});
    if (mode === 'csfle') {
      assert.equal(await csfle.countDocuments(), 0, 'fixture already populated');
      const a = await deterministic('SYN-001');
      const b = await deterministic('SYN-001');
      const note1 = await randomized('synthetic private note');
      const note2 = await randomized('synthetic private note');
      assert.deepEqual(a.buffer, b.buffer, 'deterministic ciphertext mismatch');
      assert.notDeepEqual(note1.buffer, note2.buffer, 'randomized ciphertext repeated');
      await csfle.insertMany([
        {_id: 'c1', patientCode: a, note: note1},
        {_id: 'c2', patientCode: b, note: note2}
      ]);
      const matches = await csfle.find({patientCode: await deterministic('SYN-001')}).toArray();
      assert.deepEqual(ids(matches), ['c1', 'c2']);
      for (const row of matches) {
        assert.ok(ciphertext(row.patientCode) && ciphertext(row.note));
        assert.equal(await ce.decrypt(row.patientCode), 'SYN-001');
        assert.equal(await ce.decrypt(row.note), 'synthetic private note');
      }
      let rejected = false;
      try { await csfle.insertOne({_id: 'plaintext-refused', patientCode: 'SYN-PLAIN', note: 'plain'}); }
      catch (error) { assert.equal(error.code, 121, 'require validation failure'); rejected = true; }
      assert.ok(rejected, 'plaintext write was accepted');
      assert.equal(await csfle.countDocuments({_id: 'plaintext-refused'}), 0);
      console.log(JSON.stringify({csfle: 'passed', ciphertextOnly: true,
        explicitEqualityMatches: 2, plaintextWriteCode: 121}));
      return;
    }
    if (mode === 'badkey') {
      const row = await csfle.findOne({_id: 'c1'});
      assert.ok(row && ciphertext(row.patientCode), 'existing encrypted fixture required');
      let failed = false;
      try { await ce.decrypt(row.patientCode); }
      catch (error) {
        assert.match(error.name, /Crypt/, 'require encryption-library failure, not database denial');
        failed = true;
        console.log(JSON.stringify({negativeTest: 'wrong local master key', errorClass: error.name}));
      }
      assert.ok(failed, 'unexpected decryption success');
      return;
    }
    const automatic = mode === 'automatic';
    const extraOptions = {};
    if (automatic) {
      assert.ok(state.modules?.includes('enterprise'), 'automatic path requires recorded Enterprise gate');
      assert.equal(process.env.AUTO_APPROVED46, 'yes', 'authorized automatic-encryption path required');
      assert.ok(process.env.CRYPT_SHARED46 && fs.statSync(process.env.CRYPT_SHARED46).isFile(),
        'approved crypt_shared file required');
      extraOptions.cryptSharedLibPath = process.env.CRYPT_SHARED46;
      extraOptions.cryptSharedLibRequired = true;
    }
    const encrypted = new MongoClient(uri, {...base, autoEncryption: {
      keyVaultNamespace: KEYVAULT, kmsProviders,
      encryptedFieldsMap: {[QE_NS]: state.encryptedFields},
      bypassQueryAnalysis: !automatic, extraOptions
    }});
    extraClients.push(encrypted);
    await encrypted.connect();
    const qe = encrypted.db(DB).collection('qe_records');
    const rawQE = lab.collection('qe_records');
    if (mode === 'qe') {
      assert.equal(await rawQE.countDocuments(), 0, 'QE fixture already populated');
      const payload = value => ce.encrypt(value, {keyId: state.qeId,
        algorithm: 'Indexed', contentionFactor: 0});
      await qe.insertMany([
        {_id: 'q1', patientCode: await payload('SYN-001'), label: 'first'},
        {_id: 'q2', patientCode: await payload('SYN-001'), label: 'second'},
        {_id: 'q3', patientCode: await payload('SYN-002'), label: 'third'}
      ]);
      const token = await ce.encrypt('SYN-001', {keyId: state.qeId,
        algorithm: 'Indexed', queryType: 'equality', contentionFactor: 0});
      const rows = await qe.find({patientCode: token}).toArray();
      assert.deepEqual(ids(rows), ['q1', 'q2']);
      assert.ok(rows.every(r => r.patientCode === 'SYN-001'), 'automatic decryption failed');
      const stored = await rawQE.find({_id: {$in: ['q1', 'q2', 'q3']}}).toArray();
      assert.equal(stored.length, 3);
      assert.ok(stored.every(r => ciphertext(r.patientCode)), 'raw protected field is not ciphertext');
      console.log(JSON.stringify({qeExplicit: 'passed', equalityMatches: 2,
        rawCiphertextRecords: 3, automaticDecryption: 'passed'}));
      return;
    }
    if (automatic) {
      assert.equal(await rawQE.countDocuments({_id: 'q-auto'}), 0, 'automatic fixture already exists');
      await qe.insertOne({_id: 'q-auto', patientCode: 'SYN-003', label: 'automatic'});
      const rows = await qe.find({patientCode: 'SYN-003'}).toArray();
      assert.deepEqual(ids(rows), ['q-auto']);
      assert.equal(rows[0].patientCode, 'SYN-003');
      assert.ok(ciphertext((await rawQE.findOne({_id: 'q-auto'})).patientCode));
      console.log(JSON.stringify({automaticQE: 'passed', rawCiphertext: true}));
      return;
    }
    if (mode === 'recover') {
      const row = await csfle.findOne({_id: 'c1'});
      assert.ok(row && ciphertext(row.patientCode));
      assert.equal(await ce.decrypt(row.patientCode), 'SYN-001');
      assert.equal(await ce.decrypt(row.note), 'synthetic private note');
      const token = await ce.encrypt('SYN-001', {keyId: state.qeId,
        algorithm: 'Indexed', queryType: 'equality', contentionFactor: 0});
      const rows = await qe.find({patientCode: token}).toArray();
      assert.deepEqual(ids(rows), ['q1', 'q2']);
      assert.ok(rows.every(r => r.patientCode === 'SYN-001'));
      console.log(JSON.stringify({freshProcessDecryption: 'passed', qeMatches: 2,
        backupRestoreAcceptance: 'not established by this restart check'}));
      return;
    }
    throw new Error('unhandled mode');
  } finally {
    for (const client of extraClients) await client.close();
    await raw.close();
  }
}
main().catch(error => {
  // Avoid dumping objects, command documents, URI or plaintext in normal lab output.
  console.error(JSON.stringify({status: 'failed', errorClass: error.name,
    code: typeof error.code === 'number' ? error.code : undefined}));
  process.exitCode = 1;
});
```

Run provisioning once:

```bash
python3 scripts/run46.py setup
```

The app receives `readWrite` only on this isolated database, including its key vault and QE state. Production designs should separate the DEK provisioner from the runtime application, grant runtime key-vault reads rather than unnecessary key creation/deletion, and scope data/QE-state privileges through a reviewed role. KMS authorization remains independent of MongoDB roles.

Setup refuses existing state, users, roles or collections. If it fails halfway, inspect the actual lab and partial key records before recovery. Do not delete unfamiliar collections, remove the guard or repeatedly generate new DEKs. The state file records collection UUIDs, user ID, key IDs and field policy; it contains references, not the master key.

## 9. Run explicit CSFLE and inspect ciphertext

```bash
python3 scripts/run46.py csfle
```

Expected assertions: equal deterministic values produce the same ciphertext; randomized notes differ; encrypted equality finds `c1` and `c2`; explicit decrypt recovers the known synthetic values. The ordinary raw client sees BSON binary subtype 6, not the original strings.

The collection validator uses CSFLE `encrypt` rules. The deliberate plaintext insert must fail with validation code `121`, and the refused `_id` must not exist afterward. This is a server enforcement check, not just a promise that the client usually encrypts.

Do not generalize the randomized-note test to equality search. Do not use low-cardinality deterministic fields such as a yes/no flag as a privacy design without analyzing leakage. Both field algorithms here use a lab DEK; production key granularity requires a documented tenant/user lifecycle.

## 10. Run explicit Queryable Encryption equality

```bash
python3 scripts/run46.py qe
```

The application explicitly encrypts each `patientCode` insertion using `Indexed`. It separately creates an equality query token with `queryType: equality`. It sends those values through a QE-configured client with query analysis bypassed, while retaining automatic decryption and required QE operation handling.

Require exactly `q1` and `q2` for `SYN-001`, three raw ciphertext-bearing records, and the expected decrypted values. A normal plaintext query through the raw client is not an equivalent encrypted equality query. Do not compare a new QE insertion ciphertext directly with an old stored ciphertext to implement search.

Inspect the provisioned collection options, indexes and associated state using a protected administrator session. The saved setup inventory records the actual names and UUIDs; do not invent expected state names or copy/drop just the visible collection.

`bypassQueryAnalysis` is intentional for this explicit path. It does not mean “send plaintext safely.” Every sensitive value and predicate still needs the correct explicit API. A raw Binary payload accepted by the server is not proof that it represents the intended field/key/algorithm; verify the encrypted-client result contract.

## 11. Add automatic encryption on the approved Enterprise path

Complete the explicit controls first. Obtain the supported Automatic Encryption Shared Library through the approved Enterprise distribution process, verify platform/architecture and package provenance, and record its version and file digest. Keep runtime entitlement evidence separate from installation success.

```bash
export CRYPT_SHARED46='/absolute/path/to/approved/mongo_crypt_v1.so'
export AUTO_APPROVED46='yes'
python3 scripts/run46.py automatic
```

This path requires the recorded Enterprise module gate and an explicit nonsecret selection. Reconfirm the deployed edition/version if the target has changed since setup. The code requires the requested shared library; it does not silently fall back to another query-analysis process.

The automatic client inserts a plaintext synthetic field at the application boundary, encrypts it before transmission, and automatically decrypts the equality result. The raw client must still see subtype-6 ciphertext. Require the `q-auto` result and raw-storage assertion together.

Use the local `encryptedFieldsMap` as reviewed trusted configuration. Depending only on remotely downloaded metadata expands the schema trust boundary. Version and deploy field policies with the application, and test unsupported predicates before rollout. Library loading success is not a query correctness test.

## 12. Test key dependency and fresh-process recovery

```bash
python3 scripts/run46.py badkey
python3 scripts/run46.py recover
```

The first command uses an unrelated fresh 96-byte local master key in a new process while leaving ciphertext and key-vault documents intact. It must fail to decrypt the existing CSFLE value with an encryption-library error. Database denial, missing data or an unavailable server is not the expected negative result.

The second command starts another process with the original master key and verifies both CSFLE decryption and QE equality results. This avoids treating a previously cached DEK as recovery evidence. It tests fresh-process key dependency; it is not a backup restore drill.

Also test, on disposable copies, missing key-vault records, inaccessible KMS identity and a missing local key file. Distinguish each failure from TLS/auth/database permission failures. Do not delete live DEKs to simulate failure or accept a plaintext fallback when encryption initialization fails.

## 13. Extend to range queries and review operator limits

The executable fixture proves equality only. For a separate 8.0 range lab, create a fresh collection and DEK with a field such as synthetic `age`, BSON `int`, `queryType: range`, and reviewed minimum/maximum bounds. Use BSON `Int32` values consistently rather than relying on ambiguous JavaScript numeric serialization.

| Range acceptance case | Required result |
|---|---|
| Insert values 20, 40 and 60 | Raw fields encrypted; authorized reads recover exact integer values |
| Query `>= 20` and `< 60` | Exactly the 20 and 40 fixtures |
| Endpoint equality/bounds | Documented inclusive/exclusive behavior verified |
| Out-of-bounds/wrong BSON type | Rejection attributed to the actual type/range contract |
| Unsupported regex/sort/update shape | Verified rejection or documented supported behavior; no assumed plaintext semantics |
| Raw client | Ciphertext visible; plaintext predicate not treated as equivalent |

For automatic range queries, configure the matching trusted map and supported library, then issue supported predicates. For explicit range queries, use the driver's `Range` value-encryption options and `encryptExpression` query construction with the same bounds/type/sparsity policy. Do not reuse an equality token or `rangePreview` API.

Changing bounds, query type or encrypted fields requires a reviewed migration, often fresh collection/state and re-encryption. Do not patch a client's map while retaining incompatible old ciphertext and assume the server will repair it. Test reads/writes across old/new application versions before cutover.

## 14. Production KMS, backup and rotation runbooks

Replace the lab local provider with a supported remote KMS configuration and workload identity. Review provider endpoint, key policy, credential acquisition, TLS and audit trails. An AWS/Azure/GCP field-encryption provider is not the Chapter 45 server-side KMIP integration; they protect different key hierarchies and have different clients.

| Drill | Evidence required |
|---|---|
| KMS allowed identity | Fresh process obtains/decrypts DEK and verifies content/query results |
| KMS denied identity | Same ciphertext/vault readable but decryption denied; no fallback |
| KMS outage | Fresh-process failure/recovery, timeout budget and application handling |
| Database-only access | Ciphertext visible; no accidental master-key/KMS permission grant |
| Backup restore | Consistent data, key vault, QE state/indexes, policy and provider key references |
| Historical restore | Old ciphertext still decrypts with retained dependencies after rotation |

Restore into an isolated replica set with equivalent supported versions. Restore the encrypted user collections **and associated QE state consistently**, plus the required key-vault records and schema/map. Re-establish authorized KMS access separately. Run known content, equality and range contracts from a fresh application process and record recovery time including key authorization. Never count a restored document total alone as encryption recovery acceptance.

Use the official backup/restore limitations for QE and the chosen tooling before designing exports or snapshots. Dumping through an encryption-enabled application can expose plaintext; retain ciphertext through a reviewed backup path and protect every export. Namespace or schema changes can break recovery even when key bytes survived.

`rewrapManyDataKey` changes how stored DEKs are wrapped under a KMS master key; it does not rewrite every application field under a new DEK. A new DEK lifecycle needs a separate re-encryption/migration design. Rotating a provider key version and replacing the local 96-byte file are not interchangeable procedures.

Before any rotation, preserve recoverable key-vault backups and provider access, define rollback based on actual completed state, test fresh processes and historical ciphertext, and retain prior keys for required backups. Do not delete a DEK or disable its wrapping key until all dependent data and retention obligations are resolved.

## 15. Test guards, troubleshoot and measure overhead

Save `scripts/test_contracts46.cjs`:

```javascript
'use strict';
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const assert = require('node:assert/strict');
const {checkURI, localKey, qeFields, ids} = require('./contracts46.cjs');
assert.equal(checkURI('mongodb://a:27017,b:27017/?replicaSet=lab'),
  'mongodb://a:27017,b:27017/?replicaSet=lab');
for (const uri of ['mongodb://user:password@a/?replicaSet=lab', 'mongodb://a/',
  'mongodb://a/?replicaSet=lab&tlsInsecure=true',
  'mongodb://a/?replicaSet=lab&TLSINSECURE=true',
  'mongodb://a/?replicaSet=lab&tls=false',
  'mongodb://a/?replicaSet=lab&authSource=admin']) assert.throws(() => checkURI(uri));
const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'synthetic-ch46-'));
try {
  const file = path.join(dir, 'test.key');
  fs.writeFileSync(file, Buffer.alloc(96), {mode: 0o600});
  assert.equal(localKey(file).length, 96);
  fs.chmodSync(file, 0o644); assert.throws(() => localKey(file));
  fs.chmodSync(file, 0o600); fs.writeFileSync(file, Buffer.alloc(32));
  assert.throws(() => localKey(file));
  const link = path.join(dir, 'link'); fs.symlinkSync(file, link);
  assert.throws(() => localKey(link));
} finally { fs.rmSync(dir, {recursive: true, force: true}); }
assert.deepEqual(qeFields('synthetic-key-id').fields[0].queries,
  {queryType: 'equality', contention: 0});
assert.deepEqual(ids([{_id: 'q2'}, {_id: 'q1'}]), ['q1', 'q2']);
console.log('PASS: URI/key guards and equality contract; no database or encryption runtime exercised');
```

```bash
node scripts/test_contracts46.cjs
```

| Symptom | Investigation | Closure evidence |
|---|---|---|
| Native dependency cannot load | Package majors, Node ABI, OS/architecture, native prerequisites | Exact reviewed install and successful client initialization |
| QE rejected on server | Standalone, wrong version, incompatible collection | Supported replica set and fresh compatible collection |
| Shared library cannot load | Path, architecture, dependencies, entitlement | Approved library plus actual automatic operation |
| DEK not found | Vault namespace, key UUID, MongoDB read permission | Original matching record accessible |
| DEK unwrap fails | Local key mismatch or KMS authorization/key state | Fresh-process original-key/provider recovery |
| Equality returns wrong/empty set | Predicate encryption, query type, field map, data key | Expected fixture IDs and decrypted content |
| Plaintext write accepted | Validator absent/weakened, wrong collection | Server-side enforcement or explicit controlled write-path policy verified |
| Cleanup refused | Changed UUIDs, new collections/users/keys | Investigate ownership; do not remove guards |

Keep driver command monitoring, APM and application error reporting from recording plaintext values, tokens or KMS credentials. QE also limits/redacts some server diagnostics, so plan application-side latency/throughput measurements without logging sensitive payloads.

Measure client CPU/memory, cryptographic initialization, KMS latency, pool pressure, metadata growth, read/write latency and contention under an equivalent workload. The three-record exercise proves a query contract, not production capacity or leakage resistance. Schedule documented QE state maintenance/compaction according to workload and the deployed version; ordinary plaintext-index housekeeping is not sufficient.

## 16. Cleanup, acceptance and review questions

Before cleanup, verify the owned fixture's content and archive sanitized acceptance notes. Resolve whether any retained ciphertext/backup still needs these DEKs and the local master key. The following command intentionally disposes of **all data, key-vault records and QE state in this isolated chapter database** after matching the saved collection UUIDs, user ID and key IDs:

```bash
export DISPOSE46='owned-fixture-and-keys'
python3 scripts/run46.py cleanup
unset DISPOSE46 AUTO_APPROVED46
```

The administrator performs deletion; the application user is removed first. Cleanup refuses unexpected identities, roles, collections or key records. Do not run it on a shared key vault or a database whose ownership inventory changed. Inspect partial failures before further actions.

Retain the local master key only as long as authorized recovery dependencies remain; then use the appropriate secret/storage disposal procedure. Do not claim that deleting a local file securely erases snapshots or SSD history. The TLS replica set itself remains under its separate provisioning/disposal scope.

| Acceptance item | Required observation | Authored chapter status |
|---|---|---|
| Compatibility | Exact driver/native versions, supported replica set and TLS/auth | Runtime pending |
| CSFLE | Deterministic equality, randomized difference, raw ciphertext, explicit decrypt | Runtime pending |
| Enforcement | CSFLE plaintext refusal code 121 and no refused document | Runtime pending |
| QE explicit | Expected IDs, automatic decryption and raw ciphertext | Runtime pending |
| Automatic QE | Authorized Enterprise/library gate and actual encrypted insert/query | Separate runtime path pending |
| Key dependency | Wrong key fails; fresh original-key process reads expected content | Runtime pending |
| Range | Bound/type/operator matrix on a separate compatible collection | Separate extension pending |
| Remote KMS/recovery | Fresh identity, outage/denial, consistent restore and historical key tests | Integration pending |
| Cleanup | Owned data/state/DEKs/user removed without touching other labs | Runtime pending |
| Helpers | URI/key guards and deterministic fixture-ID checks | Offline tests only |

Review questions:

1. Why does a storage-encrypted server not replace field encryption at the application boundary?
2. Which credentials let a database reader decrypt data, and which only let it read ciphertext?
3. Why is a QE insertion payload different from its equality query token?
4. What must accompany ciphertext in a recoverable backup?
5. What does rewrapping a DEK change, and what does it leave unchanged?
6. Why must key failure be tested in a new application process?

## 17. References and next chapter

- [Choosing QE versus CSFLE](https://www.mongodb.com/docs/v8.0/core/queryable-encryption/about-qe-csfle/)
- [CSFLE server-side schema enforcement](https://www.mongodb.com/docs/v8.0/core/csfle/reference/server-side-schema/)
- [Compatibility](https://www.mongodb.com/docs/v8.0/core/queryable-encryption/reference/compatibility/)
- [Explicit Queryable Encryption](https://www.mongodb.com/docs/v8.0/core/queryable-encryption/fundamentals/manual-encryption/)
- [Encrypted fields and enabled queries](https://www.mongodb.com/docs/v8.0/core/queryable-encryption/fundamentals/encrypt-and-query/)
- [Supported operations](https://www.mongodb.com/docs/v8.0/core/queryable-encryption/reference/supported-operations/)
- [QE limitations and backup constraints](https://www.mongodb.com/docs/v8.0/core/queryable-encryption/reference/limitations/)
- [Node.js 6.x in-use encryption](https://www.mongodb.com/docs/drivers/node/v6.x/security/encrypt-fields/)
- [Node.js 6.x release notes](https://www.mongodb.com/docs/drivers/node/v6.x/reference/release-notes/)
- [Driver 6.20 ClientEncryption API reference](https://mongodb.github.io/node-mongodb-native/6.20/classes/ClientEncryption.html)

Next: [**Chapter 47 — Secrets Rotation and Access Review**](47-secrets-rotation-and-access-review.md).
