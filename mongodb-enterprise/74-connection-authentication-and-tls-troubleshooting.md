# 74 — Connection Authentication and TLS Troubleshooting

Part 10 — Troubleshooting and Production Projects

**Audience:** DBREs, SREs, Platform Engineers and Developers.  
**Goal:** Distinguish naming/network, TLS, topology selection, authentication and authorization failures; reproduce controlled client failures and verify recovery with fresh connections.  
**Baseline:** Retained authenticated TLS MongoDB 8.0 / FCV 8.0 three-member SCRAM replica set; exact recorded mongosh, OpenSSL and pinned reviewed synchronous PyMongo 4.x on Python 3.11+. Core lab is Community-compatible. External authentication/x509 requires separate provider/version acceptance.  
**Status:** Written; syntax and offline diagnostic-contract checks complete; live TLS/authentication/authorization acceptance pending.  
**Prerequisites:** Chapters 6, 27, 41–43, 47, 63 and 69–71; accepted CA, member hostnames, replica-set inventory and independent recovery administrator.  
**Estimated time:** 60–90 minutes.

## 1. Locate the failed layer

A driver can report a server-selection timeout when the underlying failure is TLS or an unreachable discovered hostname. Preserve the outer error, sanitized underlying cause, UTC time, client/runtime version and intended endpoint. Do not assume every timeout means slow MongoDB queries.

| Layer | Required evidence | Successful check proves |
|---|---|---|
| Name resolution | Actual runtime resolver and SRV/TXT where used | Name resolved under that resolver |
| TCP reachability | Runtime-to-member route, port, policy and timeout | A transport connection can be opened |
| TLS | CA chain, hostname/SAN, validity, client/server policy | Verified encrypted peer relationship |
| Topology | Replica set name, advertised member addresses and roles | Driver can discover/select the intended server |
| Authentication | Identity, authSource, mechanism and fresh session | Identity accepted by the selected authentication system |
| Authorization | Exact requested namespace/action and granted roles | The identity can perform that action |
| Application operation | Actual query/write concern and outcome | The required application contract works |

Run diagnostics from the application's network/runtime context. A successful laptop connection does not prove an EKS/AKS pod can resolve or reach advertised member names.

The lab creates only an owned database and two scoped users. It deliberately tests wrong password, wrong authentication database, denied write and an unrelated CA. It does not alter server TLS, rotate production certificates, change network policy or stop members.

## 2. Incident evidence and safe sequencing

Record the affected service, deployment/member scope, failure start, recent secret/certificate/network/operator changes and whether fresh sessions or only existing sessions fail. Preserve the independent administrative recovery path before changing access configuration.

Start with configuration consistency: correct environment/URI, complete seed list, replica set name, authSource, mechanism, CA path and runtime secret mount/version. A missing file is a local configuration error, not a server certificate rejection.

Use credential-free URIs and password prompts or the approved secret mechanism. If credentials are embedded in a URI, reserved characters require correct percent encoding; passing username/password separately avoids that class of construction errors.[1] Never paste credential-bearing URIs or private keys into tickets.

Do not resolve trust failures by enabling invalid-certificate/hostname options. Repair the chain, endpoint name, certificate or client trust distribution and test the original verification policy.[1][2]

## 3. Naming, reachability and discovery

For a standard replica-set URI, all advertised member hostnames needed by the driver must be resolvable/reachable from the client. Seed connectivity alone is insufficient. For an SRV URI, inspect SRV/TXT and the resolver used by the actual container/host; do not apply standard-URI assumptions blindly.

A read-only local resolver/TCP probe for one recorded endpoint:

```python
import os
import socket

host = os.environ["CH74_MEMBER_HOST"]
port = int(os.environ.get("CH74_MEMBER_PORT", "27017"))
print({"resolved_addresses": sorted({row[4][0] for row in socket.getaddrinfo(host, port)})})
with socket.create_connection((host, port), timeout=5):
    print("PASS: TCP endpoint reachable; TLS/auth/topology not yet validated")
```

Save as `ch74_network.py` and run from the authorized client runtime. A denied/timeout connection needs routing, firewall/security group, Kubernetes policy and listener evidence; do not change every network boundary at once.

Use `directConnection=true` only for an intentional recorded single-member diagnostic. It bypasses normal discovery and failover behavior; making a direct connection succeed does not repair the replica-set-aware application's topology.[1]

## 4. Verified TLS probe

Set `CH74_MEMBER_HOST`, `CH74_MEMBER_PORT` and `CH74_CA_FILE` to the recorded certificate hostname, port and trusted CA bundle. Run through the approved client context:

```bash
openssl s_client -connect "${CH74_MEMBER_HOST}:${CH74_MEMBER_PORT:-27017}" \
  -servername "$CH74_MEMBER_HOST" -CAfile "$CH74_CA_FILE" \
  -verify_hostname "$CH74_MEMBER_HOST" -verify_return_error </dev/null
```

Require a successful verification result and retain the sanitized certificate chain/validity evidence. This probe can wait on network failure; use the platform's bounded command runner or interrupt it at the recorded diagnostic deadline. It does not authenticate SCRAM or establish database privileges.

Check SAN names, issuer/intermediate chain, validity dates, server/client clocks, accepted protocols and client CA distribution. Connecting by IP when the certificate names only DNS endpoints can correctly fail hostname verification. Fix the intended endpoint/certificate contract rather than bypassing it.

If the server requires a TLS client certificate, this basic command and the SCRAM script below need the already approved client certificate/key parameters. A TLS client certificate used for transport is not automatically MongoDB x509 authentication. x509 authentication has a separate identity/$external contract; see Chapter 42.

## 5. Lab setup — owned users and data

Use the retained independent lifecycle administrator through Chapter 42's TLS/SCRAM procedure. Run once. Both users are created in `admin`; their roles apply only to the lab database. Passwords are prompted and never printed.

```javascript
var labName = "mongodb_enterprise_ch74_access";
var lab = db.getSiblingDB(labName);
var admin = db.getSiblingDB("admin");
var owner = "mongodb-enterprise-tutorial-ch74";
if (lab.getCollectionInfos().length !== 0) throw new Error("Lab namespace exists");
if (admin.getUser("ch74_reader") || admin.getUser("ch74_writer")) {
  throw new Error("Lab user name already exists");
}
if (!db.hello().isWritablePrimary) throw new Error("Expected writable primary");
lab.ownership.insertOne({ _id: owner, createdAt: new Date() });
lab.items.insertOne({ _id: "probe", value: 1 }, {
  writeConcern: { w: "majority", wtimeout: 10000 }
});
admin.createUser({ user: "ch74_reader", pwd: passwordPrompt(),
  roles: [{ role: "read", db: labName }], customData: { owner: owner },
  mechanisms: ["SCRAM-SHA-256"] });
admin.createUser({ user: "ch74_writer", pwd: passwordPrompt(),
  roles: [{ role: "readWrite", db: labName }], customData: { owner: owner },
  mechanisms: ["SCRAM-SHA-256"] });
printjson({ readerRoles: admin.getUser("ch74_reader").roles,
            writerRoles: admin.getUser("ch74_writer").roles });
```

Record the exact credential versions in the lab secret mechanism. Preserve the original administrator session and an independently tested fresh administrative connection. Do not use the scoped writer to clean up users or grant itself access.

SCRAM authentication verifies identity; role grants determine permitted actions.[3] A user located in `admin` does not thereby have administrative privileges.

## 6. Worker parameters and unrelated CA fixture

Set these nonsecret parameters through the approved environment mechanism:

| Variable | Value |
|---|---|
| `CH74_URI` | Credential-free replica-set-aware URI with recorded set name and member seeds |
| `CH74_CA_FILE` | Original verified CA bundle |
| `CH74_BAD_CA_FILE` | Unrelated valid lab CA certificate from the isolated fixture below |
| `CH74_MEMBER_HOST` / `CH74_MEMBER_PORT` | Recorded endpoint for network/TLS probes |

Install an exact reviewed PyMongo release in an isolated virtual environment. Create a fresh local directory `ch74-ca-fixture`; stop if it already exists. Generate an unrelated certificate only for the client-side negative test:

```bash
mkdir ch74-ca-fixture
openssl req -x509 -newkey rsa:2048 -sha256 -nodes -days 1 \
  -keyout ch74-ca-fixture/unrelated.key.pem \
  -out ch74-ca-fixture/unrelated.ca.pem \
  -subj '/CN=ch74-unrelated-lab-ca' \
  -addext 'basicConstraints=critical,CA:TRUE'
```

Use an OpenSSL release supporting `-addext`. Restrict access to the generated private key; it is a disposable local fixture and must never be installed as a production trust root. Set `CH74_BAD_CA_FILE` to the absolute certificate path. The private key is not used by MongoDB or uploaded anywhere.

If your approved lab uses another unrelated valid CA, record its provenance and use that instead. A broken/missing PEM cannot demonstrate server trust rejection.

## 7. Complete fresh-connection failure runner

Save as `ch74_access.py`. Each mode creates a fresh client and forces an operation; MongoClient construction alone does not prove successful connection/authentication. The negative cases are limited to owned users. Run them once, inspect the actual error and correct the original configuration before rerunning the healthy baseline.

```python
import getpass
import os
import sys
from pathlib import Path

from pymongo import MongoClient
from pymongo.errors import OperationFailure, ServerSelectionTimeoutError
from pymongo.write_concern import WriteConcern

DB = "mongodb_enterprise_ch74_access"
MODES = {"baseline", "wrong_password", "wrong_auth_source", "denied_write", "wrong_ca"}
mode = sys.argv[1] if len(sys.argv) == 2 else "baseline"
if mode not in MODES:
    raise ValueError("Choose one recorded lab mode")
username = "ch74_reader" if mode == "denied_write" else "ch74_writer"
password = getpass.getpass("Password for " + username + ": ")
if mode == "wrong_password":
    password += "-intentional-ch74-invalid"
ca = os.environ["CH74_BAD_CA_FILE"] if mode == "wrong_ca" else os.environ["CH74_CA_FILE"]
if not Path(ca).is_file():
    raise RuntimeError("CA file missing; this is not a server TLS negative test")
auth_source = DB if mode == "wrong_auth_source" else "admin"
client = MongoClient(
    os.environ["CH74_URI"], username=username, password=password,
    authSource=auth_source, authMechanism="SCRAM-SHA-256", tls=True, tlsCAFile=ca,
    serverSelectionTimeoutMS=5000, connectTimeoutMS=3000, socketTimeoutMS=5000,
    maxPoolSize=2,
)
try:
    try:
        client.admin.command("ping")
        lab = client.get_database(DB, write_concern=WriteConcern(w="majority", wtimeout=5000))
        if lab.ownership.find_one({"_id": "mongodb-enterprise-tutorial-ch74"}) is None:
            raise RuntimeError("Owned fixture marker missing")
        item = lab.items.find_one({"_id": "probe"})
        if item is None or item["value"] != 1:
            raise RuntimeError("Owned read contract failed")
        if mode == "denied_write":
            # Setting the existing value avoids data change even if grants are accidentally broad.
            lab.items.update_one({"_id": "probe"}, {"$set": {"value": 1}})
            raise RuntimeError("Reader write unexpectedly permitted")
        if mode != "baseline":
            raise RuntimeError("Negative connection mode unexpectedly succeeded")
        changed = lab.items.update_one({"_id": "probe", "value": 1}, {"$set": {"value": 2}})
        if changed.modified_count != 1:
            raise RuntimeError("Write probe failed; reconcile owned document")
        restored = lab.items.update_one({"_id": "probe", "value": 2}, {"$set": {"value": 1}})
        if restored.modified_count != 1 or lab.items.find_one({"_id": "probe"})["value"] != 1:
            raise RuntimeError("Restoration failed; reconcile owned document")
        print("PASS: fresh verified TLS/SCRAM read/write and restoration")
    except OperationFailure as error:
        expected = 13 if mode == "denied_write" else 18
        if mode not in {"wrong_password", "wrong_auth_source", "denied_write"} or error.code != expected:
            raise
        print({"expected_failure_mode": mode, "code": error.code,
               "classification": "authorization" if expected == 13 else "authentication"})
    except ServerSelectionTimeoutError:
        if mode != "wrong_ca":
            raise
        # Outer error alone is not sufficient evidence of TLS root cause.
        print("OBSERVED: wrong-CA mode timed out selecting a server; confirm certificate-verification cause in restricted diagnostics")
finally:
    client.close()
```

Run sequentially:

```bash
python ch74_access.py baseline
python ch74_access.py wrong_password
python ch74_access.py wrong_auth_source
python ch74_access.py denied_write
python ch74_access.py wrong_ca
python ch74_access.py baseline
```

Expected: healthy baselines pass; wrong password/authSource produce authentication code 18; reader write produces authorization code 13. The wrong-CA mode commonly surfaces a selection timeout with a certificate-verification cause. Its printed outer timeout is only an observation; confirm the underlying chain-verification failure in sanitized restricted driver/TLS evidence before marking that drill passed.

Do not classify an unrelated firewall/DNS failure during wrong-CA mode as successful TLS rejection. The immediately surrounding healthy baseline and verified local CA fixture support diagnosis but do not replace underlying-cause evidence.

An interrupted baseline can leave value 2. Inspect the owned document through the lifecycle identity, confirm no concurrent writer and restore it to 1 before retrying. A timed-out write can have an ambiguous outcome; no unconditional replay is implied.

## 8. Diagnosis, repair and fresh-session verification

| Drill | Diagnosis | Corrective action | Verification |
|---|---|---|---|
| Wrong password | TLS/topology accepted, SCRAM identity rejected | Restore actual owned secret version | Fresh baseline read/write passes |
| Wrong authSource | User belongs to admin, client authenticates in lab DB | Restore admin authSource | Fresh identity accepted; roles unchanged |
| Reader denied write | Authentication/read succeeded, action unauthorized | Use intended scoped writer for write workload | Reader still denied; writer baseline passes |
| Wrong CA | Peer chain cannot be validated with unrelated CA | Restore original verified CA bundle | Fresh baseline and TLS verification pass |
| Discovered host unreachable | Seeds reachable but advertised names unusable | Correct DNS/routes/advertised-endpoint design | Normal replica-set discovery and selected role accepted |

Do not grant readWrite to the reader just to remove an intentional denial. A correct least-privilege denial is successful control behavior. For a real incident, verify the intended role/action resource before changing grants.

After secret or certificate rotation, test new connections, not only an already authenticated pooled session. Review which processes consumed the new secret/CA/certificate and restart/reload them through the authoritative owner as required by that component. Avoid simultaneous disruptive changes across members.

## 9. External authentication and x509 boundaries

External authentication mechanisms have provider/service, time, DNS, certificate and deployment dependencies beyond SCRAM. Review the exact supported server/client/platform combination from Chapter 43 before attempting a fix.

For x509, distinguish TLS client certificate acceptance from database identity authorization. The certificate identity and `$external` authentication database must match the approved user/role contract. Do not substitute the SCRAM admin authSource example for that mechanism.

For directory/federated/Kerberos-style systems, collect provider availability, time synchronization, principal/realm and mapping evidence through the provider's owner. Never print tickets/tokens, client private keys or provider credentials. Provider recovery and local break-glass access remain separate accepted runbooks.

## 10. Timeout and pool triage

| Setting/signal | Boundary | Operational caution |
|---|---|---|
| connectTimeoutMS | Establishing a connection | Increasing it does not fix blocked routes or bad trust |
| serverSelectionTimeoutMS | Finding an eligible server | Underlying TLS/topology failures can appear here |
| socketTimeoutMS | Network send/receive timing | Write outcome can be ambiguous after timeout |
| Pool checkout wait | Client connection availability | Correct credentials do not resolve saturated/blocked pools |
| Operation deadline | Driver-supported overall operation budget | Check exact pinned driver semantics and application retries |

Separate source error classification from mitigation. Increasing deadlines or maxPoolSize can worsen connection storms and demand. Use Chapter 63's client lifecycle and Chapter 73's query boundary evidence before changing them.

The lab's few-second budgets bound individual diagnostics; they are not a production recommendation. Reconcile application SLA, retries, concerns, cancellation and total request deadline before adopting new timeout values.

## 11. Offline incident-classification contract

Save as `ch74_classify.py`. This helper requires explicit evidence of the failed layer. A selection timeout with no underlying cause remains unknown rather than being labeled “network.”

```python

def classify(kind, code=None, verified_tls_failure=False):
    if kind == "local_missing_ca":
        return "client_configuration"
    if kind == "dns_failure":
        return "name_resolution"
    if kind == "tcp_failure":
        return "transport"
    if kind == "operation_failure" and code == 18:
        return "authentication"
    if kind == "operation_failure" and code == 13:
        return "authorization"
    if kind == "selection_timeout" and verified_tls_failure:
        return "tls_verification"
    return "unresolved_collect_underlying_evidence"


assert classify("operation_failure", 18) == "authentication"
assert classify("operation_failure", 13) == "authorization"
assert classify("local_missing_ca") == "client_configuration"
assert classify("selection_timeout") == "unresolved_collect_underlying_evidence"
assert classify("selection_timeout", verified_tls_failure=True) == "tls_verification"
assert classify("dns_failure") == "name_resolution"
assert classify("tcp_failure") == "transport"
print("PASS: evidence-based classification preserves unresolved timeout state")
```

Run `python ch74_classify.py`. This is a diagnostic teaching contract, not a complete automatic exception parser. Actual incidents need sanitized underlying driver/server evidence and fresh-session verification.

## 12. Production incident checklist

Record intended connection identity/scope, actual runtime network, exact versions, last known good configuration and error/UTC bounds. Verify DNS/TCP/TLS/topology before changing credentials. Verify authentication before altering roles. Compare old/new sessions after rotations.

For operator-managed systems, identify whether certificate/secret configuration belongs to the operator resource, secret manager, application deployment or external authority. A hand edit to generated files can be reverted or diverge from the accepted source of truth.

Stop changes when the independent recovery path fails, another member is degraded, or the cause remains unverified. Preserve logs and FTDC through Chapter 69's restricted capture procedure. Never clear historical evidence to make access appear recovered.

Close only when the intended application read/write contract, concern semantics, verified TLS, discovery/failover routing and monitoring are accepted. A successful OpenSSL probe or ping alone is an incomplete closure criterion.

## 13. Troubleshooting matrix

| Symptom | Evidence | Cause to test | Action and verification |
|---|---|---|---|
| Seed connects, app cannot select primary | Advertised hosts/set name and runtime routes | Discovery endpoints unavailable | Repair endpoint design; verify normal topology selection |
| Certificate verified elsewhere, pod fails | Mounted CA, runtime trust and clock | Stale/missing trust or name mismatch | Fix application trust distribution and test fresh session |
| Local PEM error | File path, permissions and PEM parse | Missing/malformed client configuration | Repair file/mount; distinguish from server rejection |
| Authentication fails after rotation | Secret version, authSource/mechanism and fresh session | Wrong credentials or client stale secret | Restore intended version; verify new connections |
| Authentication passes, command denied | Action/resource and scoped roles | Missing intended grant or correct least-privilege denial | Review contract; grant only required resource action if appropriate |
| IP URI fails TLS | Certificate SAN and intended hostname | Endpoint name not covered | Use approved hostname or reissue correct certificate |
| Existing sessions work, fresh fail | Rotation timeline and credential/CA loading | Pool masks configuration problem | Test fresh clients and roll configuration through owner |
| Timeout without clear cause | Sanitized nested errors, routes/TLS/topology | Selection hides underlying failure | Keep unresolved classification until evidence identifies layer |
| Write timed out | Stable operation identity and target state | Acknowledgement lost after write | Reconcile before retry; apply accepted idempotency design |
| External auth fails broadly | Provider status, time and mappings | Provider/dependency failure | Coordinate provider runbook; preserve independent recovery access |

## 14. Acceptance record and owned cleanup

| Check | Expected evidence |
|---|---|
| Identity/network | Actual runtime, member seeds/advertised names, replica-set and resolver |
| TLS | Verified chain/name/validity with original CA; unrelated CA rejected for verified cause |
| Healthy baseline | Fresh writer read/write and value restored to 1 |
| Wrong password/authSource | Expected code 18 and recovery on corrected fresh session |
| Authorization | Reader can read but code 13 on write; roles remain scoped |
| Classification | Unknown timeout preserved until underlying evidence exists |
| Recovery | Final fresh baseline plus intended app routing/concern contract |
| Cleanup | Both user markers and database ownership checked; users/data removed |

Save nonsecret evidence. Through the independent lifecycle administrator, check all ownership markers before removing anything. Restore probe value 1 after any interrupted write drill before cleanup.

```javascript
var labName = "mongodb_enterprise_ch74_access";
var lab = db.getSiblingDB(labName);
if (labName !== "mongodb_enterprise_ch74_access" || lab.getName() !== labName) {
  throw new Error("Refusing cleanup outside Chapter 74 database");
}
var admin = db.getSiblingDB("admin");
var owner = "mongodb-enterprise-tutorial-ch74";
if (lab.ownership.findOne({ _id: owner }) === null) throw new Error("Database ownership missing");
for (var name of ["ch74_reader", "ch74_writer"]) {
  var user = admin.getUser(name);
  if (!user || !user.customData || user.customData.owner !== owner) {
    throw new Error("User ownership mismatch: " + name);
  }
}
var probe = lab.items.findOne({ _id: "probe" });
if (!probe || probe.value !== 1) throw new Error("Reconcile probe state before cleanup");
for (var name of ["ch74_reader", "ch74_writer"]) {
  if (!admin.dropUser(name)) throw new Error("User removal failed: " + name);
  if (admin.getUser(name) !== null) throw new Error("User still exists: " + name);
}
if (lab.dropDatabase().ok !== 1) throw new Error("Owned database cleanup failed");
if (db.getSiblingDB(labName).getCollectionInfos().length !== 0) throw new Error("Collections remain");
print("PASS: owned users and access fixture removed");
```

After reviewing the exact local directory, remove the disposable unrelated certificate/private key under the lab's evidence policy. Do not remove the retained trusted CA, server certificates, application secrets, recovery administrator or other chapter resources. Partial setup/cleanup must be reconciled by exact ownership rather than bypassing guards.

Review questions:

1. Why can a TLS failure appear as a server-selection timeout?
2. What does seed reachability fail to prove about replica-set discovery?
3. How do authSource and the requested application database differ?
4. Why is a denied reader write successful least-privilege behavior?
5. Why must access recovery be checked with a fresh session?
6. How do transport client certificates and x509 database identity differ?
7. Why is a timed-out write not automatically safe to repeat?
8. What proves full application recovery beyond ping?

## 15. DBRE/SRE extension — access outage, certificate rotation and Kubernetes recovery

This section adds an incident command and change-acceptance layer to the existing scoped client failure labs. It does **not** authorize production certificate rotation, broad access changes, disabled TLS validation or Kubernetes network-policy edits.

### 15.1 First-response classification and escalation

| Observed symptom | Evidence to collect from affected runtime | Escalation and stop condition |
|---|---|---|
| DNS/SRV or member discovery failure | Pod/host resolver results, seed/SRV/TXT records, advertised replica-set addresses and driver topology view | Platform/network owner; do not edit replica-set membership based on a single resolver failure |
| TCP timeout or refusal | Destination, route, security group/NetworkPolicy, service/endpoints, connection budget and UTC window | Kubernetes/network on-call; do not widen cluster-wide ingress as a diagnostic shortcut |
| TLS trust/hostname/expiry failure | Verified chain, SAN, validity, clock, client trust-store path, SNI and exact endpoint | PKI/security owner + DBRE; never use `tlsAllowInvalidCertificates` or disable hostname validation as an incident workaround |
| Authentication failure | Auth mechanism, authSource, identity scope, secret version and fresh-session result | Identity/secret owner; preserve break-glass path and do not dump credentials |
| Authorization failure | Required command/namespace, effective role grants and policy change history | Application owner + security/DBRE; do not grant `root` to restore one query |
| Pool exhaustion / server selection | Pool checkout latency, open connections, retry rate, member health and client timeout budgets | Service on-call + DBRE; stop retry storms and avoid raising timeouts without capacity evidence |
| Ambiguous write after disconnect | Request ID/idempotency key, write concern, outcome lookup and application consistency evidence | Service owner; reconcile before replay to avoid duplicate mutation |

Record incident ID, severity under the existing policy, incident commander, affected tenants/services, UTC start, last known good version, change owner and current SLO impact.

### 15.2 Kubernetes-specific diagnostic sequence

From an **approved diagnostic pod or the affected application pod** (not an unrestricted cluster-wide shell), record namespace, service account, pod/container image digest, mounted secret/config version, DNS policy, NetworkPolicy, service/endpoint readiness and node/AZ. Check name resolution and TCP/TLS reachability to the **actual advertised replica-set member hostnames**, not only the initial Service address.

A pod marked Running does not prove its MongoDB client can validate certificates, discover the primary or authenticate. Confirm that TLS certificates cover the names used by the driver, and that pod restarts/redeployments load the intended secret versions. Use least-privilege Kubernetes RBAC; do not print secret contents into incident logs.

If a network or certificate change is suspected, compare the authoritative GitOps/operator/IaC desired state and reconciliation events. Revert only the approved scoped change; avoid manual drift that a controller will immediately overwrite.

### 15.3 Certificate and credential rotation safety runbook

1. Inventory clients, members, CA trust chains, certificate SANs/expiry, auth mechanisms, secret versions and ownership; identify whether existing connections mask a fresh-session failure.
2. Confirm a tested independent recovery administrator and approved change/rollback path before touching authentication or TLS.
3. Rehearse **overlapping trust** in an isolated environment, with both old and new client populations; ensure all expected member hostnames and routes remain valid.
4. Roll out CA/certificate/secret changes using the supported MongoDB version and authoritative operator/service procedure. Record each affected client and server identity.
5. Validate new connections from every affected runtime: DNS → TCP → verified TLS → topology selection → authentication → authorized read/write probe. Check replica set health, error ratios and pool behavior.
6. Revoke retired trust/credentials only after all required consumers are verified on the new configuration and the security owner authorizes the cutover.
7. On failure, stop further rollout, restore the approved prior trust/configuration where safe, reconcile ambiguous writes and verify fresh-session recovery. An expired/revoked credential cannot necessarily be made usable by simply restarting a pod.

**Never** use plaintext fallback, a permissive certificate flag, anonymous access or broad privilege grants as a production recovery shortcut.

### 15.4 Failure-injection acceptance matrix

Perform only against the chapter-owned identities and an isolated TLS replica set.

| Drill | Expected detection | Recovery proof |
|---|---|---|
| Wrong CA / hostname | TLS verification fails, no insecure fallback | Correct CA/hostname permits verified fresh connection |
| Wrong password/authSource | Authentication failure distinguished from DNS/TLS | Scoped identity authenticates with correct configuration |
| Denied reader write | Authorization failure, no data mutation | Reader still reads; writer alone performs approved mutation |
| Unreachable advertised member | Topology/server-selection evidence identifies endpoint | Restored route and successful primary selection |
| Rotated client secret | Existing session vs fresh session distinguished | New secret works for all expected clients; old secret retired only after approval |
| Kubernetes pod secret mount drift | Version mismatch and fresh-connection failure visible | Reconciled pod mounts and authorized application probe |
| Ambiguous write | Outcome treated as unknown, not automatically retried | Idempotent reconciliation or explicit verified result |

Record **NOT RUN** for any unexecuted drill; the offline classifier cannot certify live TLS, identity or routing behavior.

### 15.5 Fail-closed incident acceptance packet

Save as `ch74-incident.json`:

```json
{
  "chapter": 74,
  "incident_id": "NOT_ASSIGNED",
  "incident_commander": "NOT_ASSIGNED",
  "service_owner": "NOT_ASSIGNED",
  "dbre_reviewer": "NOT_ASSIGNED",
  "runtime_and_topology_recorded": false,
  "dns_tcp_tls_auth_layers_classified": false,
  "fresh_session_verified": false,
  "least_privilege_verified": false,
  "application_read_write_verified": false,
  "replica_set_health_verified": false,
  "monitoring_and_slo_recovered": false,
  "secret_and_certificate_state_reconciled": false,
  "rollback_or_no_change_documented": false,
  "evidence_references": []
}
```

Save as `ch74_incident_gate.py`:

```python
import json
from pathlib import Path

p = json.loads(Path("ch74-incident.json").read_text(encoding="utf-8"))
checks = (
    "runtime_and_topology_recorded", "dns_tcp_tls_auth_layers_classified",
    "fresh_session_verified", "least_privilege_verified",
    "application_read_write_verified", "replica_set_health_verified",
    "monitoring_and_slo_recovered",
    "secret_and_certificate_state_reconciled",
    "rollback_or_no_change_documented",
)
missing = [key for key in checks if p.get(key) is not True]
for key in ("incident_id", "incident_commander", "service_owner", "dbre_reviewer"):
    if not isinstance(p.get(key), str) or not p[key].strip() or p[key].startswith("NOT_"):
        missing.append(key)
if not isinstance(p.get("evidence_references"), list) or not p["evidence_references"]:
    missing.append("evidence_references")
if missing:
    raise SystemExit("NOT ACCEPTED: " + ", ".join(missing))
print("PASS: incident closure declarations complete; verify underlying evidence independently")
```

Run `python ch74_incident_gate.py`. The untouched template must fail. A PASS checks only recorded declarations, not actual recovery or security correctness; reviewers must verify the artifacts and approval chain.

---

## 16. Official references and validation status

1. [MongoDB 8.0 — Connection String Options](https://www.mongodb.com/docs/v8.0/reference/connection-string-options/).
2. [PyMongo — Configure TLS](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/security/tls/): verify behavior against the pinned release.
3. [MongoDB 8.0 — SCRAM](https://www.mongodb.com/docs/v8.0/core/security-scram/).

Documentation reviewed on 2026-10-12. The owned identities, client-side negative tests, timeout budgets and classification contract are teaching designs. Python/JavaScript and shell syntax plus the actual offline classifier assertions were checked. These checks do not validate live certificates, DNS/routes, SCRAM/role enforcement, exact error wrapping, provider recovery or cleanup. No live MongoDB access changes were executed in the authoring environment.

**Chapter completion:** Written and statically reviewed; offline classification acceptance complete. Runtime validation remains pending until the authorized fresh-session failure/recovery drills and owned cleanup are executed with evidence.

Previous: [Chapter 73 — Query Slowness Investigation Runbook](73-query-slowness-investigation-runbook.md).  
Next: Chapter 75 — Disk Pressure Cache Pressure and Resource Incidents.
