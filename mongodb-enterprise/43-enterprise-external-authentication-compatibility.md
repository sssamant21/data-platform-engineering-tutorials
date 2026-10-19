# 43 — Enterprise External Authentication Compatibility

**Status:** Written; static review complete; runtime lab validation pending  
**Part:** 6 — Enterprise Security and Governance  
**Goal:** Inventory actual authentication capabilities, reject incompatible integration plans, prove a scoped TLS/SCRAM control path and define provider-specific authentication, authorization and recovery acceptance.  
**Audience:** Developers, Data Engineers, DBREs, SREs and Platform Engineers  
**Time:** 90–120 minutes for the local compatibility lab; external-provider integration has a separate infrastructure-dependent schedule.  
**Baseline:** MongoDB 8.0 and mongosh; exact image/binary, platform, shell and application-driver versions must be recorded.  
**Deployment:** Retained `mongodb-ch41` standalone with Chapter 42's `requireTLS`, CA trust and SCRAM administrators. External integration requires an eligible Enterprise target and approved IdP/KDC/directory.  
**Prerequisites:** Chapters 41–42 cleanup complete; tested TLS administrator path; pinned image and original volumes; Bash/Docker/Compose/Node.js 18+; ownership of the disposable fixture. No tokens, directory passwords, keytabs or production secrets in tutorial files/evidence.

## 1. Compatibility is a set of independent gates

**Use case:** A team wants enterprise SSO for operators and short-lived workload identity for services. Its development image may be Community, its production target Enterprise, and its application driver may support a different identity flow than its shell. A successful LDAP directory bind or an IdP login page does not establish MongoDB compatibility or database authorization.

| Gate | Required evidence |
|---|---|
| Deployment/edition | Actual binary modules and deployment type, not image naming |
| Server version/platform | Exact release/patch, OS/architecture, supported mechanism/flow |
| Configured mechanism | Current server configuration and supported rollout plan |
| Client | Exact driver/shell version, mechanism, callback/human flow and dependencies |
| External provider | Trust, network access, identities, time, claims/tickets/directory mapping |
| Authorization | Exact MongoDB role/resource/actions and negative operation tests |
| Lifecycle/recovery | Expiry/refresh, revocation, outages, independent administrator and rollback |

This chapter executes local inventory, a compatibility-plan evaluator and a scoped TLS/SCRAM control exercise. It does **not** pretend that a Community container is an Enterprise server or that a mock JWT is a verified provider login. OIDC, Kerberos and LDAP integration remain not tested until the selected provider procedure runs on eligible infrastructure.

Do not replace the retained image or enable external mechanisms on the current lab as a compatibility probe. Edition migration and provider rollout need their own isolated target, reviewed configuration and acceptance.

## 2. Authentication mechanisms and deployment boundaries

| Mechanism | Typical identity | Self-managed baseline requirements | Authentication source |
|---|---|---|---|
| `SCRAM-SHA-256` | Local database user | Community or Enterprise; configured mechanism | User's authentication DB |
| `MONGODB-X509` | Certificate subject | Valid TLS/client PKI and registered subject; Chapters 41–42 apply | `$external` |
| `GSSAPI` | Kerberos principal | Enterprise, supported server/client platform and KDC/service setup | `$external` |
| `PLAIN` with LDAP | Directory identity | Enterprise directory integration; legacy review required | `$external` |
| `MONGODB-OIDC` workforce | Human/operator identity | Enterprise Linux, eligible release and supported interactive client flow | `$external` |
| `MONGODB-OIDC` workload | Programmatic identity | Enterprise Linux, eligible release and supported workload token acquisition | `$external` |

MongoDB's 8.0 OIDC guidance requires Enterprise and documents federation support from 7.0.11, with Linux as the supported server platform. This tutorial still gates its automated exercise on the **8.0 baseline** rather than claiming all historical versions or every client support the same flows. Inspect exact-release documentation before applying the material elsewhere.

Atlas has separate service configuration and compatibility rules. Atlas console SSO is not automatically database authentication, and Atlas-specific AWS-IAM setup cannot be copied into a self-managed server as though they were identical deployments. The executable evaluator below intentionally accepts only a self-managed target.

An advertised or configured mechanism is one observation. It does not prove entitlement, an IdP/KDC connection, a supported driver flow, role mapping or a working login.

## 3. Choose human and workload flows separately

| Need | Candidate path | Dependencies to review |
|---|---|---|
| Human SSO/MFA | OIDC workforce federation | IdP application, interactive supported flow, role/group claims, login/revocation policy |
| Noninteractive application | OAuth 2.0 workload federation using `MONGODB-OIDC` | Workload identity/token acquisition, audience/issuer, driver callback or documented provider flow, refresh |
| Existing Kerberos estate | `GSSAPI` | Realm, service principal, keytab/OS credential storage, DNS/time, ticket cache and client library |
| Existing LDAP deployment | Legacy `PLAIN`/LDAP assessment | Directory TLS, identity/group mapping, bind lifecycle, deprecation migration |
| Certificate-based service | x.509 | CA/private-key distribution, exact subject, renewal/revocation and scoped roles |
| Independent recovery administrator | Tested local SCRAM over TLS | Protected credential, narrow approved use and recovery reachability |

Do not require an interactive browser/MFA ceremony from a headless service. A driver that supports a workforce login does not necessarily implement the desired workload environment or token callback. A Kubernetes service account or cloud identity is not automatically a MongoDB identity until the documented token/trust/mapping path is configured and verified.

MongoDB's 8.0 guidance deprecates LDAP authentication and authorization and calls for migration to alternatives. Deprecation is not evidence that LDAP is already removed in that release, and this chapter does not predict a removal date. New designs should evaluate supported federation/certificate paths; an existing LDAP exception needs an owner and migration plan.

## 4. Preserve the TLS recovery baseline

Use **Bash** in the retained `mongodb-ch41` folder. Keep Chapter 42's server certificate and known-good TLS configuration; do not restore the plaintext Chapter 41 configuration.

```bash
dc41() { docker compose -p mongodb-ch41 -f compose.yaml "$@"; }
set -a
source .env
set +a
mkdir -p evidence-ch43
node --version
dc41 ps -a
docker image inspect "$MONGO_IMAGE" --format '{{json .RepoDigests}}'
docker run --rm -it --network mongodb-ch41_security41 -v "$PWD/pki/public:/trust:ro" "$MONGO_IMAGE" mongosh 'mongodb://mongo41:27017/admin' --tls --tlsCAFile /trust/ca.crt --quiet --username ch41_bootstrap --authenticationDatabase admin --authenticationMechanism SCRAM-SHA-256 --password
```

In **mongosh**, verify the known administrator and completed prior cleanup:

```javascript
const s43 = db.adminCommand({ connectionStatus: 1 });
if (s43.ok !== 1 || s43.authInfo.authenticatedUsers.length !== 1 ||
    s43.authInfo.authenticatedUsers[0].user !== "ch41_bootstrap" ||
    s43.authInfo.authenticatedUsers[0].db !== "admin") throw new Error("Wrong recovery administrator");
if (db.getSiblingDB("mongodb_enterprise_tutorial_ch42").getCollectionNames().length)
  throw new Error("Chapter 42 data cleanup incomplete");
const removed43 = db.getSiblingDB("$external").runCommand({ usersInfo:
  { user: "CN=events-reader,OU=Applications,O=Ch42Client,C=US", db: "$external" }, showCredentials: false });
if (removed43.ok !== 1 || removed43.users.length) throw new Error("Chapter 42 subject remains");
printjson({ recoveryAdministratorAvailable: true, identity: s43.authInfo });
```

Exit. Keep passwords at the prompt. Do not print full server configurations or fetch all parameters to discover capabilities: external-provider settings may contain sensitive values. The inventory below whitelists redacted fields.

## 5. Capture actual binary, platform and configured mechanisms

Save **`scripts/inventory43.js`**:

```javascript
const fs43 = require("fs");
function checkInventory43(ok, message) { if (!ok) throw new Error(message); }
const identity43 = db.adminCommand({ connectionStatus: 1 });
checkInventory43(identity43.ok === 1 && identity43.authInfo.authenticatedUsers.length === 1 &&
  identity43.authInfo.authenticatedUsers[0].user === "ch41_bootstrap" &&
  identity43.authInfo.authenticatedUsers[0].db === "admin", "Unexpected identity");
const build43 = db.adminCommand({ buildInfo: 1 });
const opts43 = db.adminCommand({ getCmdLineOpts: 1 });
const mechanisms43 = db.adminCommand({ getParameter: 1, authenticationMechanisms: 1 });
const fcv43 = db.adminCommand({ getParameter: 1, featureCompatibilityVersion: 1 });
checkInventory43([build43, opts43, mechanisms43, fcv43].every(x => x.ok === 1), "Inventory command failed");
const tls43 = opts43.parsed.net && opts43.parsed.net.tls;
checkInventory43(tls43 && tls43.mode === "requireTLS" &&
  opts43.parsed.security.authorization === "enabled", "TLS/access-control baseline changed");
const inventory43 = {
  schemaVersion: 1, deployment: "self-managed", at: new Date().toISOString(),
  image: process.env.MONGO_IMAGE43, version: build43.version,
  modules: build43.modules || [], serverOS: (build43.buildEnvironment || {}).target_os || "unknown",
  architecture: (build43.buildEnvironment || {}).target_arch || "unknown", shellVersion: version(),
  fcv: fcv43.featureCompatibilityVersion,
  authorizationEnabled: true, tlsMode: tls43.mode,
  configuredMechanisms: mechanisms43.authenticationMechanisms,
  recoveryIdentity: { user: "ch41_bootstrap", db: "admin", requestedMechanism: "SCRAM-SHA-256" }
};
checkInventory43(typeof inventory43.image === "string" && inventory43.image.includes("@sha256:"),
  "Pinned image reference required");
checkInventory43(Array.isArray(inventory43.configuredMechanisms), "Mechanism inventory missing");
// Redacted metadata only. Never write tokens, passwords, keytabs or complete options here.
fs43.writeFileSync("/evidence/inventory43.json", JSON.stringify(inventory43, null, 2) + "\n",
  { flag: "wx", mode: 0o644 });
printjson({ inventorySaved: true, version: inventory43.version, modules: inventory43.modules,
  serverOS: inventory43.serverOS, configuredMechanisms: inventory43.configuredMechanisms });
```

```bash
docker run --rm -it --network mongodb-ch41_security41 -e MONGO_IMAGE43="$MONGO_IMAGE" -v "$PWD/pki/public:/trust:ro" -v "$PWD/scripts:/scripts:ro" -v "$PWD/evidence-ch43:/evidence" "$MONGO_IMAGE" mongosh 'mongodb://mongo41:27017/admin' --tls --tlsCAFile /trust/ca.crt --quiet --file /scripts/inventory43.js --username ch41_bootstrap --authenticationDatabase admin --authenticationMechanism SCRAM-SHA-256 --password
```

The file is deliberately redacted nonsecret inventory, readable for host-side evaluation. `wx` refuses to overwrite existing evidence. Archive a prior inventory under a distinct filename before a deliberate new capture. Do not modify the inventory to make the Community image appear Enterprise.

Enterprise builds can identify their module as `enterprise` or `subscription`. The module observation is not a license/entitlement check. `unknown` platform must be resolved from approved build/package evidence; never infer it from the operator's laptop OS.

## 6. Write a nonsecret integration plan

Save **`plan43.json`**. Replace exact client versions only after reviewing the installed clients. The supplied unreviewed values intentionally block readiness; these are candidates, not deployable server settings.

```json
{
  "schemaVersion": 1,
  "candidates": [
    {
      "id": "local-control", "flow": "scram", "credentialKind": "password",
      "driver": { "name": "mongosh", "version": "record-installed-version", "mechanisms": ["SCRAM-SHA-256"], "reviewed": false, "source": "https://www.mongodb.com/docs/mongodb-shell/" },
      "authorization": { "db": "mongodb_enterprise_tutorial_ch43", "collection": "events", "actions": ["find"], "reviewed": false },
      "dependenciesReviewed": false, "fallbackReviewed": false
    },
    {
      "id": "operator-sso", "flow": "oidc-workforce", "credentialKind": "interactive",
      "driver": { "name": "mongosh", "version": "record-installed-version", "mechanisms": ["MONGODB-OIDC"], "reviewed": false, "source": "https://www.mongodb.com/docs/v8.0/core/oidc/workforce/" },
      "authorization": { "db": "mongodb_enterprise_tutorial_ch43", "collection": "events", "actions": ["find"], "reviewed": false },
      "dependenciesReviewed": false, "fallbackReviewed": false,
      "provider": { "issuer": "https://idp.example.invalid", "audience": "mongodb-lab", "claimsReviewed": false }
    },
    {
      "id": "service-identity", "flow": "oidc-workload", "credentialKind": "callback",
      "driver": { "name": "application-driver", "version": "record-installed-version", "mechanisms": ["MONGODB-OIDC"], "reviewed": false, "source": "https://www.mongodb.com/docs/drivers/" },
      "authorization": { "db": "mongodb_enterprise_tutorial_ch43", "collection": "events", "actions": ["find"], "reviewed": false },
      "dependenciesReviewed": false, "fallbackReviewed": false,
      "provider": { "issuer": "https://idp.example.invalid", "audience": "mongodb-lab", "claimsReviewed": false }
    },
    {
      "id": "existing-directory", "flow": "ldap", "credentialKind": "password",
      "driver": { "name": "mongosh", "version": "record-installed-version", "mechanisms": ["PLAIN"], "reviewed": false, "source": "https://www.mongodb.com/docs/v8.0/tutorial/authenticate-nativeldap-activedirectory/" },
      "authorization": { "db": "mongodb_enterprise_tutorial_ch43", "collection": "events", "actions": ["find"], "reviewed": false },
      "dependenciesReviewed": false, "fallbackReviewed": false,
      "legacyOnly": true, "migrationPlanReviewed": false
    }
  ]
}
```

Optional candidates use flow `x509` with credential kind `certificate`, or `kerberos` with kind `ticket` and the appropriate mechanism/client evidence. Store secret material in its approved secret system, not this JSON. The provider's issuer/audience are metadata; JWT/access/refresh/ID tokens and credential contents must not appear here.

Review booleans record human review decisions backed by evidence. They are not automatic proof of a working login. Record the driver documentation, actual package version, flow support and dependency/recovery review separately before changing them.

## 7. Evaluate the plan without changing the server

Save **`scripts/evaluate43.js`** for **Node.js**, not mongosh. It implements this chapter's conservative baseline policy and outputs preflight findings only.

```javascript
"use strict";
const fs = require("fs");
const flows43 = {
  scram: { mechanism: "SCRAM-SHA-256", credential: "password", enterprise: false },
  x509: { mechanism: "MONGODB-X509", credential: "certificate", enterprise: false },
  kerberos: { mechanism: "GSSAPI", credential: "ticket", enterprise: true },
  ldap: { mechanism: "PLAIN", credential: "password", enterprise: true },
  "oidc-workforce": { mechanism: "MONGODB-OIDC", credential: "interactive", enterprise: true },
  "oidc-workload": { mechanism: "MONGODB-OIDC", credential: "callback", enterprise: true }
};
function fail43(message) { throw new Error(message); }
function rejectSecrets43(value) {
  if (!value || typeof value !== "object") return;
  for (const [key, item] of Object.entries(value)) {
    if (/^(password|pwd|accessToken|refreshToken|idToken|clientSecret|privateKey|keytabContents)$/i.test(key))
      fail43("Secret-bearing field is forbidden: " + key);
    rejectSecrets43(item);
  }
}
function evaluate43(inventory, plan) {
  rejectSecrets43(plan);
  if (inventory.schemaVersion !== 1 || plan.schemaVersion !== 1 || !Array.isArray(plan.candidates))
    fail43("Unsupported inventory/plan schema");
  if (!Array.isArray(inventory.modules) || !inventory.modules.every(x => typeof x === "string") ||
      !Array.isArray(inventory.configuredMechanisms) ||
      !inventory.configuredMechanisms.every(x => typeof x === "string")) fail43("Invalid capability arrays");
  const ids = plan.candidates.map(c => c && c.id);
  if (ids.some(id => typeof id !== "string" || !id.trim()) || new Set(ids).size !== ids.length)
    fail43("Candidate IDs must be nonempty and unique");
  const enterprise = inventory.modules.some(m => ["enterprise", "subscription"].includes(m.toLowerCase()));
  const results = plan.candidates.map(candidate => {
    const reasons = [], f = flows43[candidate.flow];
    if (!f) fail43("Unknown flow: " + candidate.flow);
    if (inventory.deployment !== "self-managed") reasons.push("Evaluator is scoped to self-managed deployments");
    if (!/^8\.0\.\d+$/.test(inventory.version || "")) reasons.push("Outside the exact 8.0 release baseline");
    if (!inventory.fcv || inventory.fcv.version !== "8.0" || inventory.fcv.targetVersion)
      reasons.push("FCV is not stable at 8.0");
    if (inventory.authorizationEnabled !== true || inventory.tlsMode !== "requireTLS")
      reasons.push("Required TLS/access-control baseline missing");
    if (!inventory.image || !inventory.image.includes("@sha256:")) reasons.push("Pinned image evidence missing");
    if (f.enterprise && !enterprise) reasons.push("Enterprise binary required; observed modules do not establish it");
    if (candidate.flow.startsWith("oidc-") && inventory.serverOS !== "linux")
      reasons.push("OIDC requires a documented Linux server target");
    if (inventory.serverOS === "unknown" || !inventory.serverOS) reasons.push("Resolve server platform evidence");
    if (!inventory.configuredMechanisms.includes(f.mechanism)) reasons.push("Mechanism is not currently configured");
    if (candidate.credentialKind !== f.credential) reasons.push("Credential flow mismatches the candidate");
    const driver = candidate.driver || {};
    if (driver.reviewed !== true || typeof driver.name !== "string" || !driver.name.trim() ||
        !/^\d+\.\d+\.\d+(?:[-+][\w.-]+)?$/.test(driver.version || "") ||
        !Array.isArray(driver.mechanisms) || !driver.mechanisms.includes(f.mechanism) ||
        !/^https:\/\/www\.mongodb\.com\/docs\//.test(driver.source || ""))
      reasons.push("Exact client/flow support and primary documentation not reviewed");
    const auth = candidate.authorization || {};
    if (auth.reviewed !== true || auth.db !== "mongodb_enterprise_tutorial_ch43" ||
        auth.collection !== "events" || JSON.stringify(auth.actions) !== '["find"]')
      reasons.push("The collection-scoped reader contract is not reviewed");
    if (candidate.dependenciesReviewed !== true) reasons.push("Provider/client dependencies not reviewed");
    if (candidate.fallbackReviewed !== true) reasons.push("Independent recovery path not reviewed");
    if (candidate.flow.startsWith("oidc-")) {
      const provider = candidate.provider || {};
      let issuerOK = false;
      try { const u = new URL(provider.issuer); issuerOK = u.protocol === "https:" &&
        !u.username && !u.password && !u.hash && !u.search && !u.hostname.endsWith(".invalid"); } catch (_) {}
      if (!issuerOK || typeof provider.audience !== "string" || !provider.audience.trim() ||
          provider.claimsReviewed !== true) reasons.push("Issuer/audience/claim mapping is unreviewed or a placeholder");
    }
    if (candidate.flow === "ldap" && (candidate.legacyOnly !== true || candidate.migrationPlanReviewed !== true))
      reasons.push("Deprecated LDAP requires a reviewed legacy exception and migration plan");
    return { id: candidate.id, flow: candidate.flow, requestedMechanism: f.mechanism,
      preflight: reasons.length ? "blocked" : "reviewed-prerequisites",
      reasons, integration: "not-tested" };
  });
  return { schemaVersion: 1, editionObservation: enterprise ? "enterprise-module-observed" : "enterprise-module-not-observed",
    results, deploymentAuthorized: false, note: "Preflight does not verify provider login, token validity or runtime authorization" };
}
module.exports = { evaluate43 };
if (require.main === module) {
  try {
    if (process.argv.length !== 4) fail43("Usage: node evaluate43.js inventory.json plan.json");
    const report = evaluate43(JSON.parse(fs.readFileSync(process.argv[2], "utf8")),
      JSON.parse(fs.readFileSync(process.argv[3], "utf8")));
    console.log(JSON.stringify(report, null, 2));
    if (report.results.some(r => r.preflight === "blocked")) process.exitCode = 2;
  } catch (e) { console.error(String(e)); process.exitCode = 1; }
}
```

```bash
node scripts/evaluate43.js evidence-ch43/inventory43.json plan43.json > evidence-ch43/preflight43.json
```

Exit code **2** means one or more candidates are blocked; code **1** means invalid input/evaluation failure; **0** means only that recorded prerequisites passed this policy. No exit code declares external integration tested or authorizes deployment. The default plan should be blocked. Review all reasons, including Community/Enterprise mismatch, and preserve the actual report.

The secret-field guard is a limited structural check, not a comprehensive secret scanner. Do not paste sensitive strings into arbitrary fields. The evaluator does not validate tokens, perform discovery, call a provider or configure mechanisms. It deliberately requires the chapter's read-only collection scope rather than acting as a general-purpose production policy engine.

## 8. Create a scoped TLS/SCRAM control fixture

This control exercise confirms that failures in an external plan are not confused with broken transport or an unavailable independent administrator. It does not impersonate a federated identity.

Save **`scripts/lib43.js`**:

```javascript
const name43 = "mongodb_enterprise_tutorial_ch43";
const app43 = db.getSiblingDB(name43);
const wc43 = { w: 1, j: true, wtimeout: 10000 };
function check43(ok, message) { if (!ok) throw new Error(message); }
function equal43(a, b) { return EJSON.stringify(a) === EJSON.stringify(b); }
function identity43(user, authDB) {
  const s = db.adminCommand({ connectionStatus: 1 });
  check43(s.ok === 1 && s.authInfo.authenticatedUsers.length === 1 &&
    s.authInfo.authenticatedUsers[0].user === user && s.authInfo.authenticatedUsers[0].db === authDB,
    "Unexpected identity");
  printjson({ identity: s.authInfo.authenticatedUsers[0] });
}
function fixture43() {
  return Array.from({ length: 3 }, (_, i) => ({ _id: "compatibility-" + i, seq: i, status: "owned" }));
}
function verify43() {
  const docs = app43.events.find({}).sort({ seq: 1 }).maxTimeMS(5000).toArray();
  const expected = fixture43();
  check43(docs.length === 3, "Wrong fixture count");
  for (let i = 0; i < 3; i++) {
    for (const f of ["_id", "seq", "status"]) check43(docs[i][f] === expected[i][f], "Fixture mismatch");
  }
  return { count: docs.length, sum: docs.reduce((n, d) => n + d.seq, 0) };
}
function denied43(label, command) {
  let result;
  try { result = app43.runCommand(command); }
  catch (e) {
    check43(e.code === 13, label + " failed for a non-authorization reason: " + String(e));
    printjson({ label, denied: true, code: e.code }); return;
  }
  check43(result.ok !== 1 && result.code === 13, label + " allowed or wrong error");
  printjson({ label, denied: true, code: result.code });
}
```

Save **`scripts/setup43.js`**:

```javascript
load("/scripts/lib43.js");
identity43("ch41_bootstrap", "admin");
const users = app43.runCommand({ usersInfo: 1, showCredentials: false });
const roles = app43.runCommand({ rolesInfo: 1, showBuiltinRoles: false });
check43(users.ok === 1 && users.users.length === 0 && roles.ok === 1 && roles.roles.length === 0 &&
  app43.getCollectionNames().length === 0, "Chapter footprint exists; inspect before setup");
for (const collection of ["events", "audit", "control"]) check43(app43.createCollection(collection).ok === 1,
  "Cannot create fixture collection");
check43(app43.events.insertMany(fixture43(), { writeConcern: wc43 }).acknowledged, "Fixture insert failed");
check43(app43.audit.insertOne({ _id: "audit-sentinel", owner: "chapter43" },
  { writeConcern: wc43 }).acknowledged, "Audit insert failed");
check43(app43.runCommand({ createRole: "Ch43ControlReader", privileges: [
  { resource: { db: name43, collection: "events" }, actions: ["find"] }
], roles: [] }).ok === 1, "Control role creation failed");
check43(app43.runCommand({ createUser: "ch43_control", pwd: passwordPrompt(),
  mechanisms: ["SCRAM-SHA-256"], roles: [{ role: "Ch43ControlReader", db: name43 }],
  customData: { owner: "chapter43" } }).ok === 1, "Control user creation failed");
const created = app43.runCommand({ usersInfo: { user: "ch43_control", db: name43 }, showCredentials: false });
check43(created.ok === 1 && created.users.length === 1, "Control user missing");
check43(app43.control.insertOne({ _id: "ownership", owner: "chapter43", userId: created.users[0].userId,
  uuids: app43.getCollectionInfos().map(c => ({ name: c.name, uuid: c.info.uuid })), at: new Date() },
  { writeConcern: wc43 }).acknowledged, "Ownership checkpoint failed");
printjson({ controlFixtureReady: true, data: verify43() });
```

```bash
docker run --rm -it --network mongodb-ch41_security41 -v "$PWD/pki/public:/trust:ro" -v "$PWD/scripts:/scripts:ro" "$MONGO_IMAGE" mongosh 'mongodb://mongo41:27017/admin' --tls --tlsCAFile /trust/ca.crt --quiet --file /scripts/setup43.js --username ch41_bootstrap --authenticationDatabase admin --authenticationMechanism SCRAM-SHA-256 --password
```

The first prompt authenticates bootstrap; the script's password prompt creates a distinct control-user credential. Store it outside tutorial/evidence files. This standalone's `w:1,j:true` writes do not prove replica-set majority durability.

## 9. Verify transport and least-privilege control independently

Save **`scripts/control43.js`**:

```javascript
load("/scripts/lib43.js");
identity43("ch43_control", name43);
printjson({ allowedRead: verify43() });
denied43("control insert", { insert: "events", documents: [{ _id: "unexpected" }] });
denied43("control delete", { delete: "events", deletes: [{ q: { _id: "compatibility-0" }, limit: 1 }] });
denied43("control audit read", { find: "audit", filter: {}, maxTimeMS: 5000 });
denied43("control role grant", { grantRolesToUser: "ch43_control", roles: [{ role: "readWrite", db: name43 }] });
printjson({ tlsScramControlPassed: true, data: verify43() });
```

```bash
docker run --rm -it --network mongodb-ch41_security41 -v "$PWD/pki/public:/trust:ro" -v "$PWD/scripts:/scripts:ro" "$MONGO_IMAGE" mongosh 'mongodb://mongo41:27017/mongodb_enterprise_tutorial_ch43?serverSelectionTimeoutMS=5000&socketTimeoutMS=15000' --tls --tlsCAFile /trust/ca.crt --quiet --file /scripts/control43.js --username ch43_control --authenticationDatabase mongodb_enterprise_tutorial_ch43 --authenticationMechanism SCRAM-SHA-256 --password
```

The command explicitly requests SCRAM, and the identity's allowed mechanism is SCRAM-SHA-256. Record the successful login and code-13 denied operations separately from the external-plan report. A token/IdP failure cannot be reported as tested merely because this control succeeds.

After reviewing actual shell support, dependency and recovery evidence, you may update **only the `local-control` candidate** to its installed version and reviewed fields, then evaluate again. External candidates remain blocked unless their own recorded gates are satisfied; a successful local control does not fill in their review fields.

## 10. OIDC workforce integration acceptance runbook

Execute this section only on a separately prepared eligible **Enterprise Linux** target with an approved IdP and exact client support. It is a concrete provider acceptance sequence, not executed by the local evaluator:

1. Record the Enterprise binary, OS, exact version/FCV, target topology and known-good TLS/SCRAM recovery login.
2. Register the workforce application using the IdP's supported OIDC flow. Review redirect/interaction requirements, issuer, audience, subject/group claims and login/MFA policy.
3. Prepare the MongoDB provider configuration from the exact-release workforce procedure. Review provider identity/prefix and authorization mode explicitly; do not blindly copy a workload configuration.
4. Configure the supported MongoDB principal/role mapping. Database-managed and externally managed authorization have different object/mapping requirements; a successful IdP login does not create a least-privilege MongoDB role automatically.
5. Use the pinned supported human client to authenticate with `MONGODB-OIDC` and `$external`. Confirm actual mapped identity, intended reader resource and successful fixture read.
6. Attempt prohibited write, other-collection read and role grant on owned fixtures. Require code 13; authentication failures are not these authorization tests.
7. Test an unassigned identity and relevant wrong issuer/audience, expired credential and removed-group cases using the provider's approved test procedure. Never forge a JWT locally and call its payload claims proof of signature validity.
8. Measure refresh/relogin, IdP interruption, recovery administrator access and removal propagation using fresh and retained connections. Preserve redacted outcomes; close and retire provider-owned test identities/app registrations according to the approved lifecycle.

Record test status, identity mapping and observed latency/propagation boundaries. Browser login, MFA, tokens and IdP application creation are not exercised in the retained Community lab.

## 11. OIDC workload integration acceptance runbook

Workload federation uses programmatic identities and OAuth 2.0 access tokens. Select the exact driver's documented built-in provider environment or callback path; built-in support is not universal across clouds, workloads and drivers.

| Gate | Concrete evidence |
|---|---|
| Identity acquisition | Approved noninteractive identity/credential source; exact runtime environment |
| Token trust | Trusted issuer/signing discovery, expected audience, time/expiry handling and supported token type |
| Driver | Pinned package/version and documented callback/provider contract; no browser dependency |
| MongoDB mapping | Configured provider and least-privilege identity/role mapping |
| Refresh | Repeated operations past token lifetime, supported refresh/reacquisition and observed failure behavior |
| Revocation/outage | Identity/provider denial and independent recovery path; fresh versus retained sessions distinguished |

Use an owned fixture with the same read-only resource contract. Verify the actual authenticated identity, allowed read and denied write/cross-resource operation before exercising refresh/outage. Test wrong audience, untrusted issuer or unassigned workload through an approved provider test configuration; preserve server/client error categories without storing tokens.

Do not paste access tokens into connection-string examples, log callback arguments or print decoded token payloads as “verification.” Decoding is not signature/audience validation. The driver/server/provider must execute the supported trust path. Token-refresh behavior also depends on driver pooling and connection lifetime, so a one-time login cannot satisfy this section.

No workload OAuth login, refresh callback or cloud identity endpoint is contacted by the local compatibility lab. Keep those runtime rows not tested until the actual integration completes.

## 12. Kerberos and legacy LDAP compatibility runbooks

**Kerberos:** Record the eligible Enterprise server/client platform, supported Kerberos implementation, realm, service principal naming, DNS and clock synchronization. Verify the server's required service credential/keytab or platform credential store with restrictive access, and obtain a client ticket through the supported client environment. Register the intended Kerberos principal and scoped roles using the documented `$external` procedure. Perform a fresh `GSSAPI` login, identity/read verification and code-13 denied operations on owned fixtures. Test ticket expiry/renewal, wrong principal/realm and KDC interruption with the independent administrator available.

Do not show keytab contents or include ticket caches in evidence. Linux and Windows service-credential handling differ; the host platform and application client libraries must be reviewed separately. A principal string alone is not a provisioned service principal or a valid ticket.

**Legacy LDAP:** Inventory existing authentication and authorization paths separately. Review client `PLAIN` support over verified TLS, server-to-directory encrypted transport and CA trust, directory reachability, user mapping, group lookup, bind credential lifecycle and exact group-to-role authorization. Test one assigned identity and one unassigned identity, allowed/denied fixture operations, directory outage, credential rotation and removal propagation. LDAP bind success is not sufficient evidence of correct MongoDB privileges.

LDAP remains a legacy/deprecated choice on this baseline. Record an approved exception, migration destination, dependency owners, staged access/role comparison and cutover/recovery plan. Do not disable directory TLS to work around a trust error. A successful existing integration does not remove the need to plan for deprecation.

The local lab creates no KDC principals, keytabs, directory bind identities or LDAP group roles. These runbooks define required tests on prepared infrastructure, not simulated success.

## 13. Migration, recovery and acceptance matrix

For an existing integration change, inventory current principal-to-role mappings and compare old/new effective resources/actions before cutover. Test replacement identities on owned fixtures, then update consumers and establish fresh pools. Retire old access only after verifying consumer use and keeping an independently tested administrator.

| Failure dimension | Test/observe | Recovery requirement |
|---|---|---|
| IdP/KDC/directory unavailable | New login, refresh and existing-connection behavior | Document service impact; verified independent administrator |
| Provider signing/key rotation | Supported trust/discovery refresh and valid new credentials | Approved trust overlap and rollback procedure |
| Group/role membership removed | Fresh login plus retained-pool behavior | Measured propagation; avoid promising instant disconnection |
| Wrong mapping grants excess access | Effective roles and negative operations | Stop cutover, correct mapping, assess unintended access |
| Mechanism configuration removes SCRAM | Before/after mechanism list and recovery test | Preserve approved recovery mechanism until replacement is tested |
| TLS/name trust fails | CA/SAN/actual endpoints | Restore valid trust/name configuration; no bypass flags |

Record **pass**, **fail** or **not tested** separately for binary compatibility, client review, provider login, authorization, refresh/revocation, outage/recovery and cleanup. Preflight readiness is not an external-runtime pass.

A public Community image's blocked Enterprise candidate is a useful correct finding. It is not a failed attempt to enable a feature, and no server change is required to manufacture a different result.

## 14. Troubleshooting by failure layer

| Symptom | Inspect first | Likely layer/action |
|---|---|---|
| Enterprise-only mechanism absent/ineligible | Actual modules, build/version, configured mechanisms | Edition/configuration gate; choose eligible target |
| OIDC target is non-Linux | Server build OS and exact support docs | Platform compatibility; do not infer from shell capability |
| TLS connection fails | Chain/SAN/host/clock | Repair transport trust before identity changes |
| Authentication fails/code 18 | Requested mechanism/source, provider principal/claims/ticket, logs | Identity/configuration/trust problem; not missing CRUD privilege |
| Unauthorized/code 13 after login | Actual resource/action and effective roles | Mapping/least-privilege problem; grant only reviewed scope |
| Headless workload opens browser | Client flow/callback/environment selection | Wrong human/workload path |
| Token refresh fails after initial success | Driver lifecycle, expiry/acquisition and provider reachability | One-time login did not validate lifecycle |
| Kerberos principal cannot obtain/use ticket | Realm/SPN, DNS/time, client cache/service credential | Fix KDC/client integration before MongoDB role changes |
| LDAP bind works but DB access fails | Group lookup/user mapping and effective MongoDB roles | Authentication and authorization mappings differ |
| Candidate marked blocked with review booleans false | Actual unreviewed gates and source/package evidence | Complete review; do not toggle values just to obtain exit 0 |

Preserve redacted first useful errors and timestamps. Avoid printing tokens, complete provider configuration, passwords or credential files. A `ping` or decoded-token display cannot replace identity/read/denial evidence.

## 15. Cleanup the local control fixture and retain TLS

Save **`scripts/cleanup43.js`** and execute as the TLS/SCRAM bootstrap user:

```javascript
load("/scripts/lib43.js");
identity43("ch41_bootstrap", "admin");
const owned = app43.control.findOne({ _id: "ownership" });
const options = db.adminCommand({ getCmdLineOpts: 1 });
check43(options.ok === 1 && options.parsed.security.authorization === "enabled" &&
  options.parsed.net.tls.mode === "requireTLS", "TLS/access-control baseline changed");
check43(owned && owned.owner === "chapter43" && owned.uuids.length === 3, "Missing ownership record");
const collections = app43.getCollectionInfos();
check43(collections.length === 3 && collections.every(c => ["events", "audit", "control"].includes(c.name)),
  "Unexpected collection footprint");
for (const c of collections) {
  const saved = owned.uuids.find(x => x.name === c.name);
  check43(saved && equal43(saved.uuid, c.info.uuid), "Owned collection replaced");
}
check43(app43.control.countDocuments({}) === 1, "Unexpected control records");
verify43();
const audit = app43.audit.find({}).toArray();
check43(audit.length === 1 && audit[0]._id === "audit-sentinel" && audit[0].owner === "chapter43",
  "Audit fixture changed");
const users = app43.runCommand({ usersInfo: 1, showCredentials: false });
check43(users.ok === 1 && users.users.length === 1, "Unexpected user inventory");
const user = users.users[0];
check43(user.user === "ch43_control" && equal43(user.userId, owned.userId) &&
  user.customData && user.customData.owner === "chapter43" && user.roles.length === 1 &&
  user.roles[0].role === "Ch43ControlReader" && user.roles[0].db === name43,
  "Control user replaced/changed");
const roles = app43.runCommand({ rolesInfo: 1, showBuiltinRoles: false, showPrivileges: true });
check43(roles.ok === 1 && roles.roles.length === 1 && roles.roles[0].role === "Ch43ControlReader",
  "Unexpected custom role inventory");
const role = roles.roles[0];
check43(role.roles.length === 0 && role.privileges.length === 1 &&
  equal43(role.privileges[0].resource, { db: name43, collection: "events" }) &&
  equal43(role.privileges[0].actions, ["find"]), "Control role changed");
check43(app43.runCommand({ dropUser: "ch43_control" }).ok === 1, "Control user drop failed");
check43(app43.runCommand({ dropRole: "Ch43ControlReader" }).ok === 1, "Control role drop failed");
check43(app43.dropDatabase().ok === 1, "Scoped data drop failed");
const afterUsers = app43.runCommand({ usersInfo: 1 });
const afterRoles = app43.runCommand({ rolesInfo: 1, showBuiltinRoles: false });
check43(afterUsers.ok === 1 && afterUsers.users.length === 0 && afterRoles.ok === 1 &&
  afterRoles.roles.length === 0 && app43.getCollectionNames().length === 0, "Cleanup incomplete");
printjson({ localControlCleanupComplete: true, externalProviderConfigurationChanged: false });
```

```bash
docker run --rm -it --network mongodb-ch41_security41 -v "$PWD/pki/public:/trust:ro" -v "$PWD/scripts:/scripts:ro" "$MONGO_IMAGE" mongosh 'mongodb://mongo41:27017/admin' --tls --tlsCAFile /trust/ca.crt --quiet --file /scripts/cleanup43.js --username ch41_bootstrap --authenticationDatabase admin --authenticationMechanism SCRAM-SHA-256 --password
```

Attempt a fresh control-user login: authentication should fail after removal. Confirm a fresh TLS/SCRAM bootstrap login remains available and the server still requires TLS. Preserve the redacted inventory/plan/report and exact test results.

The local exercise made no external provider/claim/mechanism configuration change and created no `$external` user. Provider runbook cleanup, if independently executed, must retire its exact owned principals, role mappings, app registration and credentials with dependency-owner coordination. It is not covered by dropping the local fixture.

If setup/cleanup was interrupted, inspect recorded `userId`, UUIDs and remaining objects first. Missing ownership or replacement objects require investigation; do not replay completed drops, delete volumes, alter Chapter 35 or remove the retained recovery administrator.

## 16. Acceptance checklist and review questions

- [ ] Recorded pinned image, actual modules, version/FCV, server OS, shell and configured mechanisms.
- [ ] Verified the retained `requireTLS` and independent SCRAM administrator path.
- [ ] Preserved redacted inventory without secrets or complete provider settings.
- [ ] Evaluated the nonsecret plan; incompatible/unreviewed candidates remain blocked with explicit reasons.
- [ ] Distinguished workforce interaction from noninteractive workload acquisition and exact client support.
- [ ] Identified LDAP deprecation and required legacy exception/migration ownership.
- [ ] Local scoped control identity reads exactly three fixture events; denied operations return code 13.
- [ ] Compatibility review, provider login, authorization, refresh/removal and outage recovery are separate statuses.
- [ ] OIDC/Kerberos/LDAP runtime gates remain not tested unless their prepared-infrastructure runbooks actually execute.
- [ ] Removed the owned control user/role/data; fresh control login fails and TLS administrator remains usable.

**Evidence:** Actual build/platform/mechanism inventory, source/client review, nonsecret plan and evaluator reasons, local identity/read/code-13 results, provider-specific acceptance matrix and cleanup. Tokens/keytabs/passwords are never evidence attachments. Static evaluation does not satisfy runtime validation, and an IdP-independent control pass does not validate an external integration.

**Review questions:**

1. Why is an Enterprise-looking image name insufficient edition evidence?
2. What does a configured mechanism leave unproved?
3. How do workforce and workload identity flows differ operationally?
4. Why must server platform and application client support be checked separately?
5. Why is LDAP deprecation different from immediate removal?
6. Why does token decoding not prove token validation?
7. What distinguishes successful external authentication from correct MongoDB authorization?
8. What lifecycle tests are missing from a one-time login?
9. Why must an independent administrator remain tested during rollout?
10. Why can the evaluator never report deployment authorized or integration tested?

## 17. References and next chapter

- [MongoDB 8.0: OIDC/OAuth 2.0 compatibility](https://www.mongodb.com/docs/v8.0/core/oidc/security-oidc/)
- [MongoDB 8.0: workforce federation](https://www.mongodb.com/docs/v8.0/core/oidc/workforce/)
- [MongoDB 8.0: configure workforce federation](https://www.mongodb.com/docs/v8.0/core/oidc/workforce/configure-oidc/)
- [MongoDB 8.0: workforce authorization](https://www.mongodb.com/docs/v8.0/core/oidc/workforce/database-user-workforce/)
- [MongoDB 8.0: workload federation](https://www.mongodb.com/docs/v8.0/core/oidc/workload/)
- [MongoDB 8.0: Kerberos](https://www.mongodb.com/docs/v8.0/core/kerberos/)
- [MongoDB 8.0: native LDAP/Active Directory](https://www.mongodb.com/docs/v8.0/tutorial/authenticate-nativeldap-activedirectory/)
- [MongoDB 8.0: LDAP deprecation and alternatives](https://www.mongodb.com/docs/v8.0/core/LDAP-deprecation/)
- [Chapter 41 — Users Roles and Least Privilege](41-users-roles-and-least-privilege.md)
- [Chapter 42 — TLS Certificates and x509 Authentication](42-tls-certificates-and-x509-authentication.md)

Next: [**Chapter 44 — Enterprise Audit Configuration and Analysis**](44-enterprise-audit-configuration-and-analysis.md).

Previous: [Chapter 42 — TLS Certificates and x509 Authentication](42-tls-certificates-and-x509-authentication.md).
