# 41 — Users Roles and Least Privilege

**Status:** Written; static review complete; runtime lab validation pending  
**Part:** 6 — Enterprise Security and Governance  
**Goal:** Bootstrap an authenticated lab, separate identity/data/application accounts, prove collection-scoped privileges with positive and negative tests, rotate credentials and remove owned security objects safely.  
**Audience:** Developers, Data Engineers, DBREs, SREs and Platform Engineers  
**Time:** 120–150 minutes.  
**Baseline:** MongoDB 8.0 and mongosh; reuse Chapter 35's pinned image digest and record exact patch/shell versions.  
**Deployment:** New isolated standalone `mongodb-ch41` with access control enabled; independent of the retained Chapter 35 sharded cluster. Community-compatible.  
**Prerequisites:** Chapters 35–40 for image/workspace conventions; Docker/Compose and Bash; exclusive ownership of the new synthetic lab; a password manager or equivalent local secret handling. No production credentials or data.

## 1. Authentication and authorization answer different questions

**Use case:** A service must read and update event records without deleting them, changing indexes, managing identities or reading an unrelated collection. A reporting account needs read-only access to that same collection. The operator must prove these boundaries instead of assigning `readWrite` to the whole database and assuming it is sufficiently narrow.

Authentication establishes the user identity; authorization decides whether that identity can perform an action on a resource. A MongoDB user is identified by **username plus authentication database**. The database in the URI is not automatically the authentication database when `authSource` is supplied separately.

A privilege combines a resource and actions. Roles collect privileges and may inherit other roles. A user's effective privileges are the union of its assigned/inherited roles; adding a narrow role does not subtract privileges from a broader one. There is no custom deny privilege that overrides an existing grant.

Collection-scoped privileges do not implement tenant-row or field-level authorization. A writer with `update` on `events` can update permitted documents and fields within that resource; this lab's predicates are application behavior, not a server-side restriction to those predicates. Use application authorization, suitable data boundaries and schema controls for additional requirements.

## 2. Choose built-in roles deliberately

| Role family | Typical use | Review before granting |
|---|---|---|
| `read` / `readWrite` on one database | Database-wide application access | Broader collection access and operations than a narrowly scoped custom role |
| `dbAdmin` | Database administration | Not an application-data reader by itself; inspect actual granted actions |
| `userAdmin` | Identity/role administration for a database | Can delegate powerful access within its scope; treat as privileged |
| `clusterMonitor` | Cluster observation | Monitoring privileges are separate from application CRUD |
| `clusterAdmin` | Cluster administration | Broad topology/maintenance authority; not a default application role |
| `root` | Highly privileged bootstrap/break-glass account | Restrict access, use and retention; never place in application configuration |

Inspect the exact version's role definitions rather than inferring permissions from names. Database administration, user administration and application data access are distinct concerns. `userAdmin` is not harmless because it initially lacks a data-read privilege: its ability to grant roles can create access within its authorized scope.

The lab uses a root account only for bootstrap, inventory and final guarded teardown. Normal identity work uses a scoped identity administrator; fixture provisioning uses a separate data administrator; application tests use custom roles.

## 3. Identity and privilege contract

| Identity | Authentication DB | Granted roles | Intended responsibility |
|---|---|---|---|
| `ch41_bootstrap` | `admin` | `root` on `admin` | Owned lab bootstrap and final teardown |
| `ch41_identity` | `admin` | `userAdmin` on chapter DB | Manage chapter users/custom roles |
| `ch41_data` | `admin` | `readWrite` + `dbAdmin` on chapter DB | Provision/verify owned data and indexes |
| `ch41_reader` | Chapter DB | `Ch41EventReader` | `find` on `events` |
| `ch41_writer_v1` | Chapter DB | `Ch41EventWriter` | `find`, `insert`, `update` on `events` |
| `ch41_writer_v2` | Chapter DB | Same custom writer role | Replacement identity during rotation |

Chapter DB: `mongodb_enterprise_tutorial_ch41`. Other fixture DB: `mongodb_enterprise_tutorial_ch41_other`.

| Application operation | Reader | Writer |
|---|---|---|
| Read `events` | Allow | Allow |
| Insert/update `events` | Deny | Allow |
| Delete an event | Deny | Deny |
| Read `audit` in same database | Deny | Deny |
| Read other fixture database | Deny | Deny |
| Create an event index/drop collection | Deny | Deny |
| Grant roles/manage users | Deny | Deny |
| Run cluster `serverStatus` | Deny | Deny |

Every denied operation below must return **code 13, Unauthorized**. A DNS error, timeout, authentication failure, malformed request or missing collection is not a passing authorization test.

## 4. Create a separate authenticated lab

From the retained Chapter 35 directory, load its **nonsecret image reference**, then create a fresh sibling directory. Stop if the new directory already exists; inspect a prior run instead of overwriting its files.

```bash
set -a
source .env
set +a
test -n "$MONGO_IMAGE" || exit 1
mkdir ../mongodb-ch41 || exit 1
cd ../mongodb-ch41
mkdir scripts evidence-ch41
printf 'MONGO_IMAGE=%s\n' "$MONGO_IMAGE" > .env
dc41() { docker compose -p mongodb-ch41 -f compose.yaml "$@"; }
```

Save **`compose.yaml`**:

```yaml
services:
  mongo41:
    image: ${MONGO_IMAGE:?Set a pinned image digest}
    container_name: mongodb-ch41
    command: ["mongod", "--auth", "--bind_ip_all", "--port", "27017", "--wiredTigerCacheSizeGB", "0.25"]
    mem_limit: 1g
    networks: [security41]
    volumes:
      - data41:/data/db
      - config41:/data/configdb
      - ./scripts:/scripts:ro
networks:
  security41:
    internal: true
volumes:
  data41:
  config41:
```

```bash
dc41 config
dc41 up -d
dc41 ps -a
for i in {1..30}; do
  if docker exec mongodb-ch41 mongosh 'mongodb://127.0.0.1:27017/?serverSelectionTimeoutMS=1000' --quiet --eval 'if(db.adminCommand({ping:1}).ok!==1)quit(1);'; then
    break
  fi
  if [ "$i" -eq 30 ]; then exit 1; fi
  sleep 1
done
```

No host port is published; every client command runs inside this owned container and connects over loopback. Host/container administrators remain trusted. This lab does not enable TLS; user-management passwords need TLS when sent across a real network. Chapter 42 covers TLS/x.509. Do not retrofit access control into the eleven-member Chapter 35 deployment using this standalone procedure: replica sets/sharding also require supported internal member authentication and coordinated rollout.

`ping` establishes process readiness, not application access. Docker Compose must render the pinned digest, isolated network and separate volumes. A public `mongo` image does not establish Enterprise entitlement.

## 5. Bootstrap the first administrator and prove authentication state

Connect from the container's localhost interface while the new instance has no users or roles:

```bash
docker exec -it mongodb-ch41 mongosh 'mongodb://127.0.0.1:27017/admin' --quiet
```

In **mongosh**, create the first administrator. Use a unique lab password stored outside these scripts:

```javascript
const first41 = db.getSiblingDB("admin").runCommand({
  createUser: "ch41_bootstrap", pwd: passwordPrompt(),
  roles: [{ role: "root", db: "admin" }], mechanisms: ["SCRAM-SHA-256"]
});
if (first41.ok !== 1) throw new Error("Bootstrap failed; inspect existing state");
printjson({ bootstrapCreated: true });
```

Exit the shell. The localhost exception is for first-user/role bootstrap when no users or roles exist; it is not permanent localhost authorization bypass. Creating the first user ends this bootstrap opportunity. If the command reports a duplicate or authorization error, do not assume a fresh instance or disable access control to continue.

Reconnect as the bootstrap identity. Passwords are prompted; do not place them in URIs, command arguments, environment variables, source files or evidence output.

```bash
docker exec -it mongodb-ch41 mongosh 'mongodb://127.0.0.1:27017/admin' --quiet --username ch41_bootstrap --authenticationDatabase admin --authenticationMechanism SCRAM-SHA-256 --password
```

In **mongosh**:

```javascript
const status41 = db.adminCommand({ connectionStatus: 1 });
if (status41.ok !== 1 || status41.authInfo.authenticatedUsers.length !== 1 ||
    status41.authInfo.authenticatedUsers[0].user !== "ch41_bootstrap" ||
    status41.authInfo.authenticatedUsers[0].db !== "admin") throw new Error("Wrong identity");
const options41 = db.adminCommand({ getCmdLineOpts: 1 });
if (options41.ok !== 1 || options41.parsed.security.authorization !== "enabled")
  throw new Error("Access control not enabled");
printjson({ version: db.version(), shell: version(), identity: status41.authInfo,
  authorization: options41.parsed.security.authorization });
```

Save only the redacted version/identity results. Do not export `admin.system.users`, SCRAM verifier material or password transcripts as evidence.

## 6. Provision distinct administrators and synthetic data

In that authenticated bootstrap session, create both scoped administrators. Each call prompts for a different password:

```javascript
const application41 = "mongodb_enterprise_tutorial_ch41";
for (const [user, roles] of [
  ["ch41_identity", [{ role: "userAdmin", db: application41 }]],
  ["ch41_data", [{ role: "readWrite", db: application41 }, { role: "dbAdmin", db: application41 }]]
]) {
  const result = db.getSiblingDB("admin").runCommand({ createUser: user, pwd: passwordPrompt(),
    roles, mechanisms: ["SCRAM-SHA-256"], customData: { owner: "chapter41" } });
  if (result.ok !== 1) throw new Error("Administrator creation failed: " + user);
}
```

Save **`scripts/lib41.js`**:

```javascript
const name41 = "mongodb_enterprise_tutorial_ch41";
const otherName41 = "mongodb_enterprise_tutorial_ch41_other";
const app41 = db.getSiblingDB(name41);
const other41 = db.getSiblingDB(otherName41);
const wc41 = { w: 1, j: true, wtimeout: 10000 };
function check41(ok, message) { if (!ok) throw new Error(message); }
function equal41(a, b) { return EJSON.stringify(a) === EJSON.stringify(b); }
function identity41(user, authDB) {
  const result = db.adminCommand({ connectionStatus: 1 });
  check41(result.ok === 1, "Cannot inspect connection identity");
  const identities = result.authInfo.authenticatedUsers;
  check41(identities.length === 1 && identities[0].user === user && identities[0].db === authDB,
    "Unexpected authenticated identity");
  printjson({ authenticatedUser: identities[0] });
}
function denied41(label, database, command) {
  let response;
  try { response = database.runCommand(command); }
  catch (e) {
    check41(e.code === 13, label + " failed for a non-authorization reason: " + String(e));
    printjson({ test: label, denied: true, code: e.code, codeName: e.codeName });
    return;
  }
  check41(response.ok !== 1 && response.code === 13,
    label + " was allowed or failed for another reason");
  printjson({ test: label, denied: true, code: response.code, codeName: response.codeName });
}
function seeds41() {
  return Array.from({ length: 3 }, (_, i) => ({ _id: "seed-" + i, seq: i,
    revision: 1, payload: "training-" + i }));
}
function exact41(actual, expected) {
  check41(actual.length === expected.length, "Wrong record count");
  for (let i = 0; i < expected.length; i++) {
    for (const field of ["_id", "seq", "revision", "payload"]) {
      check41(actual[i][field] === expected[i][field], "Wrong fixture field " + field);
    }
  }
}
function readSeeds41() {
  const docs = app41.events.find({ _id: { $in: ["seed-0", "seed-1", "seed-2"] } })
    .sort({ seq: 1 }).maxTimeMS(5000).toArray();
  exact41(docs, seeds41());
  return docs;
}
function data41() {
  readSeeds41();
  const all = app41.events.find({}).maxTimeMS(5000).toArray();
  const permitted = ["seed-0", "seed-1", "seed-2", "probe-ch41_writer_v1", "probe-ch41_writer_v2"];
  check41(all.every(d => permitted.includes(d._id)) && new Set(all.map(d => d._id)).size === all.length,
    "Unexpected document/duplicate");
  for (const user of ["ch41_writer_v1", "ch41_writer_v2"]) {
    const probe = all.filter(d => d._id === "probe-" + user);
    if (probe.length) exact41(probe, [{ _id: "probe-" + user, seq: 100,
      revision: 1, payload: "owned-probe" }]);
  }
  const audit = app41.audit.find({}).toArray();
  check41(audit.length === 1 && audit[0]._id === "audit-sentinel" && audit[0].owner === "chapter41",
    "Audit fixture changed");
  return { events: all.length, seeds: 3, probes: all.length - 3, audit: 1 };
}
```

Save **`scripts/setup-data41.js`**, run using the bootstrap account for the cross-database fixture:

```javascript
load("/scripts/lib41.js");
identity41("ch41_bootstrap", "admin");
check41(app41.getCollectionNames().length === 0 && other41.getCollectionNames().length === 0,
  "Fixture namespace exists; inspect ownership before rerun");
for (const name of ["events", "audit", "control"]) check41(app41.createCollection(name).ok === 1,
  "Cannot create collection");
check41(other41.createCollection("sentinel").ok === 1, "Cannot create other fixture");
check41(app41.events.insertMany(seeds41(), { writeConcern: wc41 }).acknowledged, "Seed insert failed");
check41(app41.audit.insertOne({ _id: "audit-sentinel", owner: "chapter41" },
  { writeConcern: wc41 }).acknowledged, "Audit insert failed");
check41(other41.sentinel.insertOne({ _id: "foreign-sentinel", owner: "chapter41" },
  { writeConcern: wc41 }).acknowledged, "Other fixture insert failed");
const uuids = app41.getCollectionInfos().map(c => ({ name: c.name, uuid: c.info.uuid }));
const otherUUID = other41.getCollectionInfos({ name: "sentinel" })[0].info.uuid;
check41(app41.control.insertOne({ _id: "ownership", owner: "chapter41", uuids, otherUUID,
  at: new Date() }, { writeConcern: wc41 }).acknowledged, "Checkpoint failed");
printjson({ fixtureReady: true, data: data41() });
```

```bash
docker exec -it mongodb-ch41 mongosh 'mongodb://127.0.0.1:27017/admin' --quiet --file /scripts/setup-data41.js --username ch41_bootstrap --authenticationDatabase admin --authenticationMechanism SCRAM-SHA-256 --password
```

The standalone uses journaled `w:1`; this is not a majority-replicated durability lab. Keep data and identity provisioning outputs without recording prompted passwords. Failed/partial setup must be inspected rather than replayed blindly.

## 7. Create collection-scoped custom roles and users

Connect as the identity administrator, whose credentials live in `admin` even though it manages roles/users in the chapter DB:

```bash
docker exec -it mongodb-ch41 mongosh 'mongodb://127.0.0.1:27017/mongodb_enterprise_tutorial_ch41' --quiet --username ch41_identity --authenticationDatabase admin --authenticationMechanism SCRAM-SHA-256 --password
```

In **mongosh**:

```javascript
load("/scripts/lib41.js");
identity41("ch41_identity", "admin");
for (const [role, actions] of [
  ["Ch41EventReader", ["find"]],
  ["Ch41EventWriter", ["find", "insert", "update"]]
]) {
  check41(app41.runCommand({ createRole: role,
    privileges: [{ resource: { db: name41, collection: "events" }, actions }], roles: [] }).ok === 1,
    "Role creation failed: " + role);
}
for (const [user, role] of [["ch41_reader", "Ch41EventReader"], ["ch41_writer_v1", "Ch41EventWriter"]]) {
  check41(app41.runCommand({ createUser: user, pwd: passwordPrompt(),
    roles: [{ role, db: name41 }], mechanisms: ["SCRAM-SHA-256"],
    customData: { owner: "chapter41" } }).ok === 1, "User creation failed: " + user);
}
denied41("identity-admin cannot read application events", app41,
  { find: "events", filter: {}, maxTimeMS: 5000 });
denied41("identity-admin cannot grant admin root", app41,
  { grantRolesToUser: "ch41_writer_v1", roles: [{ role: "root", db: "admin" }] });
```

Use separate passwords for reader and writer. The identity administrator can grant powerful roles in the chapter database; keep its credential out of application deployments. The cross-database root-grant denial demonstrates its boundary, not an inability to escalate inside its own scope.

No wildcard database/collection resource or inherited role is added to the custom roles. `insert`/`update` permissions include more behavior than this small CRUD script exercises, including upsert requirements; review the full action definitions for the real service.

## 8. Reader: prove allowed reads and denied mutations

Save **`scripts/reader41.js`**:

```javascript
load("/scripts/lib41.js");
identity41("ch41_reader", name41);
printjson({ readAllowed: true, seeds: readSeeds41().length });
denied41("reader insert", app41, { insert: "events", documents: [{ _id: "unexpected-reader" }] });
denied41("reader update", app41, { update: "events", updates: [
  { q: { _id: "seed-0" }, u: { $set: { revision: 9 } } } ] });
denied41("reader delete", app41, { delete: "events", deletes: [{ q: { _id: "seed-0" }, limit: 1 }] });
denied41("reader same-db audit read", app41, { find: "audit", filter: {}, maxTimeMS: 5000 });
denied41("reader other-db read", other41, { find: "sentinel", filter: {}, maxTimeMS: 5000 });
denied41("reader index creation", app41, { createIndexes: "events", indexes: [{ key: { seq: 1 }, name: "unexpected_seq" }] });
denied41("reader collection drop", app41, { drop: "events" });
denied41("reader grant roles", app41, { grantRolesToUser: "ch41_reader", roles: [{ role: "readWrite", db: name41 }] });
denied41("reader cluster status", db.getSiblingDB("admin"), { serverStatus: 1 });
readSeeds41();
printjson({ readerContractPassed: true });
```

```bash
docker exec -it mongodb-ch41 mongosh 'mongodb://127.0.0.1:27017/mongodb_enterprise_tutorial_ch41' --quiet --file /scripts/reader41.js --username ch41_reader --authenticationDatabase mongodb_enterprise_tutorial_ch41 --authenticationMechanism SCRAM-SHA-256 --password
```

This script intentionally attempts collection drop and role grants in the disposable fixture. If they unexpectedly succeed, the test stops immediately; inspect excessive privileges and damaged state. Do not run these negative tests against valuable collections.

An identity can authenticate successfully and still be denied an operation. Conversely, a missing database in an authorized database listing is not a stronger denial test than an actual protected operation returning code 13.

## 9. Writer: prove scoped writes and prohibited administration

Save **`scripts/writer41.js`**. Pass the expected writer identity through a nonsecret environment variable.

```javascript
load("/scripts/lib41.js");
const user41 = process.env.TEST_USER41;
check41(["ch41_writer_v1", "ch41_writer_v2"].includes(user41), "Unexpected writer test identity");
identity41(user41, name41);
readSeeds41();
const marker41 = { _id: "probe-" + user41, seq: 100, revision: 1, payload: "owned-probe" };
const existing41 = app41.events.find({ _id: marker41._id }).maxTimeMS(5000).toArray();
if (existing41.length === 0) {
  check41(app41.events.insertOne(marker41, { writeConcern: wc41 }).acknowledged, "Insert not acknowledged");
} else {
  exact41(existing41, [marker41]);
  printjson({ note: "Existing verified marker; insert was exercised on an earlier run" });
}
const update41 = app41.events.updateOne({ _id: "seed-0", revision: 1 },
  { $set: { revision: 2 } }, { writeConcern: wc41 });
check41(update41.acknowledged && update41.matchedCount === 1, "Update uncertain/unmatched");
exact41(app41.events.find({ _id: "seed-0" }).maxTimeMS(5000).toArray(),
  [{ ...seeds41()[0], revision: 2 }]);
const reset41 = app41.events.updateOne({ _id: "seed-0", revision: 2 },
  { $set: { revision: 1 } }, { writeConcern: wc41 });
check41(reset41.acknowledged && reset41.matchedCount === 1, "Reset uncertain/unmatched");
denied41("writer delete", app41, { delete: "events", deletes: [{ q: { _id: "seed-0" }, limit: 1 }] });
denied41("writer audit read", app41, { find: "audit", filter: {}, maxTimeMS: 5000 });
denied41("writer other-db read", other41, { find: "sentinel", filter: {}, maxTimeMS: 5000 });
denied41("writer index creation", app41, { createIndexes: "events", indexes: [{ key: { seq: 1 }, name: "unexpected_seq" }] });
denied41("writer collection drop", app41, { drop: "events" });
denied41("writer all-user inventory", app41, { usersInfo: 1 });
denied41("writer role escalation", app41, { grantRolesToUser: user41, roles: [{ role: "readWrite", db: name41 }] });
denied41("writer cluster status", db.getSiblingDB("admin"), { serverStatus: 1 });
readSeeds41();
exact41(app41.events.find({ _id: marker41._id }).maxTimeMS(5000).toArray(), [marker41]);
printjson({ writerContractPassed: true, user: user41 });
```

```bash
docker exec -it -e TEST_USER41=ch41_writer_v1 mongodb-ch41 mongosh 'mongodb://127.0.0.1:27017/mongodb_enterprise_tutorial_ch41' --quiet --file /scripts/writer41.js --username ch41_writer_v1 --authenticationDatabase mongodb_enterprise_tutorial_ch41 --authenticationMechanism SCRAM-SHA-256 --password
```

If the update/reset is interrupted, inspect `seed-0` using a data administrator and compare every field before resetting a confirmed owned probe from revision 2 to 1. A timeout is an unknown outcome until reconciled. Do not overwrite arbitrary mismatches or repeatedly insert a marker without checking its existing state.

## 10. Prove administrator separation and unauthenticated denial

Run a data-administrator check in a fresh session:

```bash
docker exec -it mongodb-ch41 mongosh 'mongodb://127.0.0.1:27017/mongodb_enterprise_tutorial_ch41' --quiet --username ch41_data --authenticationDatabase admin --authenticationMechanism SCRAM-SHA-256 --password
```

In **mongosh**:

```javascript
load("/scripts/lib41.js");
identity41("ch41_data", "admin");
printjson({ dataVerified: data41() });
denied41("data-admin cannot inventory chapter users", app41, { usersInfo: 1 });
denied41("data-admin cannot grant roles", app41,
  { grantRolesToUser: "ch41_writer_v1", roles: [{ role: "readWrite", db: name41 }] });
denied41("data-admin cannot read other DB", other41, { find: "sentinel", filter: {}, maxTimeMS: 5000 });
denied41("data-admin lacks cluster monitoring", db.getSiblingDB("admin"), { serverStatus: 1 });
```

Exit, then run a client with **no credentials**:

```bash
docker exec mongodb-ch41 mongosh 'mongodb://127.0.0.1:27017/mongodb_enterprise_tutorial_ch41' --quiet --eval 'load("/scripts/lib41.js"); const s=db.adminCommand({connectionStatus:1}); check41(s.authInfo.authenticatedUsers.length===0,"Unexpected identity"); denied41("unauthenticated events read",app41,{find:"events",filter:{},maxTimeMS:5000});'
```

The unauthenticated read must fail with code 13 even from localhost now that a user exists. A successful `ping` without credentials is not evidence that application data is exposed.

Use an incorrect authentication database in a separate prompted connection for `ch41_reader`, for example `--authenticationDatabase admin`. It should fail authentication, normally code 18. Record the actual category and compare it with the successful chapter-authentication-DB connection. Do not count code 18 as the code-13 authorization result required by the role tests.

## 11. Revoke and restore access without changing the password

In a **fresh identity-administrator session**, revoke the old writer's only role:

```javascript
load("/scripts/lib41.js");
identity41("ch41_identity", "admin");
check41(app41.runCommand({ revokeRolesFromUser: "ch41_writer_v1",
  roles: [{ role: "Ch41EventWriter", db: name41 }] }).ok === 1, "Revoke failed");
```

Exit and authenticate as `ch41_writer_v1` again with its unchanged password. In **that fresh writer session**:

```javascript
load("/scripts/lib41.js");
identity41("ch41_writer_v1", name41);
denied41("authenticated writer with no roles cannot read", app41,
  { find: "events", filter: {}, maxTimeMS: 5000 });
```

Authentication succeeds but authorization fails. In a fresh identity-administrator session, restore the exact custom role:

```javascript
load("/scripts/lib41.js");
identity41("ch41_identity", "admin");
check41(app41.runCommand({ grantRolesToUser: "ch41_writer_v1",
  roles: [{ role: "Ch41EventWriter", db: name41 }] }).ok === 1, "Grant failed");
```

Exit and rerun `writer41.js` in a new v1 connection. A verified preexisting marker is accepted as a repeat test; it does not falsely claim a new insert. Fresh connections make the observed grant/revoke boundary explicit. Existing pools and distributed authorization-cache propagation need separate operational testing on the actual topology.

## 12. Rotate a service identity and then its password

Use **identity-admin** to create a second writer with a different password:

```javascript
load("/scripts/lib41.js");
identity41("ch41_identity", "admin");
check41(app41.runCommand({ createUser: "ch41_writer_v2", pwd: passwordPrompt(),
  roles: [{ role: "Ch41EventWriter", db: name41 }], mechanisms: ["SCRAM-SHA-256"],
  customData: { owner: "chapter41" } }).ok === 1, "Replacement identity creation failed");
```

Exit and test the replacement using a fresh session:

```bash
docker exec -it -e TEST_USER41=ch41_writer_v2 mongodb-ch41 mongosh 'mongodb://127.0.0.1:27017/mongodb_enterprise_tutorial_ch41' --quiet --file /scripts/writer41.js --username ch41_writer_v2 --authenticationDatabase mongodb_enterprise_tutorial_ch41 --authenticationMechanism SCRAM-SHA-256 --password
```

In a real service rollout: store the replacement secret in the supported secret manager, update consumers, establish fresh pools, verify real operations, then retire old access. This lab has no application deployment; record consumer cutover as not tested. Two accounts allow a controlled overlap; replacing a single password offers no simultaneous acceptance of the old/new password for new connections.

After the replacement tests pass, in **identity-admin**, revoke v1's role again. Confirm a fresh v1 session authenticates but cannot read, as in Section 11. Keep that retired account without roles until cleanup so authentication/authorization can be distinguished. Do not infer that password changes or role revocation instantly terminate every existing socket or in-flight operation.

Next, rotate v2's password using **identity-admin**:

```javascript
load("/scripts/lib41.js");
identity41("ch41_identity", "admin");
check41(app41.runCommand({ updateUser: "ch41_writer_v2", pwd: passwordPrompt(),
  mechanisms: ["SCRAM-SHA-256"] }).ok === 1, "Password update failed");
```

Exit. Attempt a fresh v2 connection using its **old password** at the prompt: authentication must fail, normally code 18. Then rerun `writer41.js` using the **new password**: it must pass. Save failure categories and successful identity/contract output without saving either password.

The update command deliberately omits `roles`; it changes the password/mechanism rather than replacing the privilege assignment. Supplying a `roles` array to user-update operations replaces that array, so an incomplete array can accidentally remove access. Preserve an independently tested administrator before identity/credential changes.

## 13. Review effective privileges and keep redacted evidence

In a fresh **identity-admin** session, inspect the chapter users and roles:

```javascript
load("/scripts/lib41.js");
identity41("ch41_identity", "admin");
const users41 = app41.runCommand({ usersInfo: [
  { user: "ch41_reader", db: name41 }, { user: "ch41_writer_v1", db: name41 },
  { user: "ch41_writer_v2", db: name41 }
], showPrivileges: true, showCredentials: false });
check41(users41.ok === 1 && users41.users.length === 3, "Incomplete user inventory");
for (const user of users41.users) {
  printjson({ user: user.user, db: user.db, userId: user.userId,
    roles: user.roles, inheritedRoles: user.inheritedRoles,
    inheritedPrivileges: user.inheritedPrivileges });
  const wanted = user.user === "ch41_reader" ? "Ch41EventReader" :
    user.user === "ch41_writer_v2" ? "Ch41EventWriter" : null;
  check41(wanted ? user.roles.length === 1 && user.roles[0].role === wanted && user.roles[0].db === name41 :
    user.roles.length === 0, "Unexpected direct role assignment");
  check41(user.inheritedPrivileges.every(p => p.resource.db === name41 &&
    p.resource.collection === "events" && p.actions.every(a =>
      (wanted === "Ch41EventReader" ? ["find"] : wanted === "Ch41EventWriter" ? ["find", "insert", "update"] : []).includes(a))),
    "Unexpected effective privilege");
}
for (const role of ["Ch41EventReader", "Ch41EventWriter"]) {
  const result = app41.runCommand({ rolesInfo: { role, db: name41 }, showPrivileges: true });
  check41(result.ok === 1 && result.roles.length === 1, "Role inventory failed");
  const definition = result.roles[0];
  check41(definition.roles.length === 0 && definition.privileges.length === 1,
    "Unexpected role inheritance/resource count");
  const privilege = definition.privileges[0];
  const expectedActions = role === "Ch41EventReader" ? ["find"] : ["find", "insert", "update"];
  check41(equal41(privilege.resource, { db: name41, collection: "events" }) &&
    equal41([...privilege.actions].sort(), [...expectedActions].sort()), "Role definition changed");
  printjson({ role, privileges: definition.privileges, inheritedRoles: definition.inheritedRoles });
}
```

Record the user identity/authentication DB, exact direct/inherited roles, collection resources, action sets, test outcomes, timestamp, version and rotation milestone. Avoid secrets, credential hashes and broad unredacted user exports. This inventory and negative testing are not an Enterprise audit-log configuration; audit facilities are covered separately.

Review application-account access after schema/deployment changes. Adding a new collection should require a deliberate role review instead of silently inheriting all-database access. Shared role changes affect every user inheriting that role; assess the blast radius before updating privileges.

## 14. Troubleshooting and operational failure modes

| Symptom | Collect | Interpretation/action |
|---|---|---|
| Authentication failed/code 18 | Username, auth DB, mechanism, fresh-connection test | Wrong password, auth source, mechanism or restriction; do not fix with broader roles |
| Unauthorized/code 13 | Actual command resource/action, effective privileges, identity | Missing grant or wrong resource; add only the reviewed permission |
| App unexpectedly passes a denied operation | Direct/inherited roles and exact test command | Excess privilege; stop test and assess any unintended mutation |
| `ping` succeeds anonymously | Protected read result | Ping alone is not a data-access test |
| New password works but old pool still runs | Pool/session lifecycle and new-connection evidence | Rotation is not guaranteed immediate socket termination |
| Role revoked but another role still permits access | Union of direct/inherited grants | Remove unintended broader grant; a narrow role does not override it |
| Identity admin cannot read events | Its scoped `userAdmin` role | Expected separation; use approved data-admin account for fixture work |
| User-update loses permissions | Before/after roles arrays and update command | Roles replacement may have omitted an assignment |
| First-user bootstrap fails | Existing users/roles, actual authorization state | Localhost exception may be closed; use known administrator |
| Writer revision probe remains at 2 | Exact seed fields, timeout/reset response | Reconcile known owned probe before rerunning; do not ignore mismatch |

For a confirmed interrupted writer probe, use **data-admin**, inspect `seed-0` and verify its fields match `seeds41()[0]` except revision 2. Then reset it with predicate `{_id:"seed-0",revision:2}` and journaled write concern; confirm acknowledgement and run `data41()`. Any other state is a failed fixture gate requiring investigation.

A real lockout recovery procedure depends on deployment, topology, internal authentication and approved administrative access. Preserve the independent administrator and recovery plan before changes; do not respond to a role error by restarting valuable deployments without authorization.

## 15. Guarded cleanup and retained authenticated environment

The normal cleanup removes chapter application users/custom roles and both synthetic data databases. It preserves the three lab administrators, authenticated server and volumes for Chapter 42. Application identity removal is explicit: dropping data alone is not a user/role-retirement procedure.

Save **`scripts/cleanup41.js`**, execute as **bootstrap** only after recording all tests:

```javascript
load("/scripts/lib41.js");
identity41("ch41_bootstrap", "admin");
const owned = app41.control.findOne({ _id: "ownership" });
check41(owned && owned.owner === "chapter41" && owned.uuids.length === 3,
  "Ownership checkpoint missing");
const collections = app41.getCollectionInfos();
check41(collections.length === 3 && collections.every(c => ["events", "audit", "control"].includes(c.name)),
  "Unexpected collection footprint");
for (const c of collections) {
  const saved = owned.uuids.find(x => x.name === c.name);
  check41(saved && equal41(saved.uuid, c.info.uuid), "Owned collection replaced");
}
check41(app41.control.countDocuments({}) === 1, "Unexpected control records");
const otherCollections = other41.getCollectionInfos();
check41(otherCollections.length === 1 && otherCollections[0].name === "sentinel" &&
  equal41(otherCollections[0].info.uuid, owned.otherUUID), "Other fixture replaced");
const sentinel = other41.sentinel.find({}).toArray();
check41(sentinel.length === 1 && sentinel[0]._id === "foreign-sentinel" && sentinel[0].owner === "chapter41",
  "Other fixture changed");
printjson({ verifiedData: data41() });
const users = app41.runCommand({ usersInfo: 1, showCredentials: false });
check41(users.ok === 1 && users.users.every(u =>
  ["ch41_reader", "ch41_writer_v1", "ch41_writer_v2"].includes(u.user) &&
  u.customData && u.customData.owner === "chapter41"), "Unexpected user; stop cleanup");
for (const u of users.users) {
  const expectedRole = u.user === "ch41_reader" ? "Ch41EventReader" : "Ch41EventWriter";
  check41(u.roles.length <= 1 && u.roles.every(r => r.db === name41 && r.role === expectedRole),
    "User assignment changed; investigate");
}
const roles = app41.runCommand({ rolesInfo: 1, showBuiltinRoles: false, showPrivileges: true });
check41(roles.ok === 1 && roles.roles.length === 2 && roles.roles.every(r =>
  ["Ch41EventReader", "Ch41EventWriter"].includes(r.role)), "Unexpected custom roles");
for (const r of roles.roles) {
  const actions = r.role === "Ch41EventReader" ? ["find"] : ["find", "insert", "update"];
  check41(r.roles.length === 0 && r.privileges.length === 1 &&
    equal41(r.privileges[0].resource, { db: name41, collection: "events" }) &&
    equal41([...r.privileges[0].actions].sort(), [...actions].sort()), "Role privileges changed");
}
for (const u of users.users) check41(app41.runCommand({ dropUser: u.user }).ok === 1, "User drop failed");
for (const r of roles.roles) check41(app41.runCommand({ dropRole: r.role }).ok === 1, "Role drop failed");
const remainingUsers = app41.runCommand({ usersInfo: 1 });
const remainingRoles = app41.runCommand({ rolesInfo: 1, showBuiltinRoles: false });
check41(remainingUsers.ok === 1 && remainingUsers.users.length === 0, "Chapter users remain");
check41(remainingRoles.ok === 1 && remainingRoles.roles.length === 0, "Custom roles remain");
check41(app41.getName() === "mongodb_enterprise_tutorial_ch41" &&
  other41.getName() === "mongodb_enterprise_tutorial_ch41_other",
  "Refusing cleanup outside Chapter 41 owned databases");
check41(app41.dropDatabase().ok === 1 && other41.dropDatabase().ok === 1, "Scoped data drop failed");
check41(app41.getCollectionNames().length === 0 && other41.getCollectionNames().length === 0,
  "Fixture collections remain");
printjson({ cleanupComplete: true, retainedAdministrators: ["ch41_bootstrap", "ch41_identity", "ch41_data"] });
```

```bash
docker exec -it mongodb-ch41 mongosh 'mongodb://127.0.0.1:27017/admin' --quiet --file /scripts/cleanup41.js --username ch41_bootstrap --authenticationDatabase admin --authenticationMechanism SCRAM-SHA-256 --password
dc41 ps -a
```

Attempt a **fresh** reader connection after cleanup: it should fail authentication because that user was removed. Then verify bootstrap still authenticates. Existing connection/session behavior is outside this fresh-login check.

Cleanup permits a missing v2 account after an interrupted rotation, but refuses unexpected users/roles, replacement UUIDs or changed data. If the cleanup is interrupted after some users/roles are removed, inspect the recorded results and remaining objects; do not replay a script whose original preconditions no longer hold. If setup never wrote ownership, manually inspect the exact partial footprint before any scoped removal.

Keep this lab for Chapter 42. Do not use `down -v`, global pruning or changes to Chapter 35 as normal cleanup. If eventually disposing of the entire owned security lab, verify its Compose project, containers and exact volumes first, and retain required evidence/secret-retirement records.

## 16. Acceptance checklist, evidence and review questions

- [ ] Separate pinned-image standalone lab starts with access control enabled and no published port.
- [ ] First admin created through initial localhost bootstrap; fresh authenticated identity verified.
- [ ] Identity/data administrators have only the documented scoped assignments.
- [ ] Exact seeds, audit and other-database fixtures created and ownership UUIDs recorded.
- [ ] Custom roles have one collection resource, exact actions and no inherited roles.
- [ ] Reader permits events reads; all prohibited operations return code 13.
- [ ] Writer insert/update/read-back/reset passes; prohibited delete/admin/cross-resource operations return code 13.
- [ ] Anonymous protected read denied; wrong-authentication-DB test classified separately.
- [ ] Revocation permits authentication but denies protected read; restored role passes fresh test.
- [ ] v2 contract passes; v1 retired to no roles; old v2 password fails fresh login and new one passes.
- [ ] Effective role/privilege inventory matches the contract; no credential material saved.
- [ ] Owned users/roles/data removed; removed user cannot log in; bootstrap remains usable.

**Evidence:** Image/version inventory, redacted connection identities and authorization state, scoped administrator/role definitions, fixture/UUID inventory, actual positive results and code-13 negative results, code-18 authentication failures, revoke/grant/rotation milestone outputs, effective privileges and cleanup. Capture timestamps and failed assertions. Live application cutover, TLS, distributed cache/pool behavior and Enterprise audit logging remain separate gates.

**Review questions:**

1. What distinguishes authentication code 18 from authorization code 13?
2. Why does a user identity include an authentication database?
3. Why can a narrow role not cancel a broader inherited grant?
4. Why is `userAdmin` still privileged without an initial data-read action?
5. What does collection scope leave unprotected about tenants and fields?
6. Why must denied tests verify the actual error category?
7. Why are fresh connections important when checking rotation and revocation?
8. What is the benefit and risk of overlapping v1/v2 service accounts?
9. What can a user-update `roles` array accidentally replace?
10. Why remove users/custom roles explicitly rather than only dropping fixture data?

## 17. References and next chapter

- [MongoDB 8.0: localhost exception](https://www.mongodb.com/docs/v8.0/core/localhost-exception/)
- [MongoDB 8.0: createUser](https://www.mongodb.com/docs/v8.0/reference/method/db.createUser/)
- [MongoDB 8.0: createRole](https://www.mongodb.com/docs/v8.0/reference/method/db.createRole/)
- [MongoDB 8.0: built-in roles](https://www.mongodb.com/docs/v8.0/reference/built-in-roles/?deployment-type=self)
- [MongoDB 8.0: privilege actions](https://www.mongodb.com/docs/v8.0/reference/privilege-actions/)
- [MongoDB 8.0: connectionStatus](https://www.mongodb.com/docs/v8.0/reference/command/connectionStatus/)
- [MongoDB 8.0: updateUser](https://www.mongodb.com/docs/v8.0/reference/command/updateUser/)
- [Chapter 40 — Scaling and Sharding Acceptance Lab](40-scaling-and-sharding-acceptance-lab.md)

Next: **[Chapter 42 — TLS Certificates and x509 Authentication](42-tls-certificates-and-x509-authentication.md)**.

Previous: [Chapter 40 — Scaling and Sharding Acceptance Lab](40-scaling-and-sharding-acceptance-lab.md).
