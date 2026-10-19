# 42 — TLS Certificates and x509 Authentication

**Status:** Written; static review complete; runtime lab validation pending  
**Part:** 6 — Enterprise Security and Governance  
**Goal:** Enable validated TLS on an authenticated lab, map an x.509 certificate subject to a scoped MongoDB user, test trust/authentication/authorization failures separately, and rehearse certificate renewal and recovery.  
**Audience:** Developers, Data Engineers, DBREs, SREs and Platform Engineers  
**Time:** 120–150 minutes.  
**Baseline:** MongoDB 8.0, mongosh and OpenSSL 3.x; reuse the pinned image digest and record exact tool versions.  
**Deployment:** Retained authenticated standalone `mongodb-ch41`; synthetic CA/certificates and Chapter 42 database. Independent of the Chapter 35 sharded cluster. Community-compatible.  
**Prerequisites:** Chapter 41 cleanup complete, three retained lab administrators and tested bootstrap password, original Compose volumes intact, Bash/Docker/Compose/OpenSSL, exclusive use of this disposable environment and capacity for a planned standalone restart.

## 1. Separate encryption, certificate identity and privileges

**Use case:** A reporting service must validate the MongoDB server, authenticate with a client certificate and read only an event collection. Operators also need an independent administrator path while rotating certificates. The acceptance decision must distinguish a trusted TLS connection from a valid MongoDB identity and from permission to access data.

| Layer | Question | Lab evidence |
|---|---|---|
| TLS server validation | Is this the expected server, signed by a trusted CA? | CA chain, SAN/hostname match, successful encrypted client connection |
| Client certificate validation | Is the presented client certificate valid and trusted? | Chain/purpose/validity checks and x.509 login |
| MongoDB authentication | Does its subject identify a registered user? | `$external` identity with `MONGODB-X509` |
| MongoDB authorization | What may that identity do? | Allowed event read and code-13 denied operations |

TLS alone does not assign database privileges. A trusted certificate with an unregistered subject must not authenticate as the reader. A registered subject with narrow privileges must not gain administrative access merely because the TLS connection is valid.

The client certificate subject is the x.509 username. Renewal with the same subject can authenticate as the same user; possession of any still-valid trusted certificate/private key with that subject may retain the same identity. Serial number alone is not a MongoDB username.

## 2. Scope, compatibility and trust choices

This lab enables `requireTLS` and preserves `security.authorization` through `--auth`. It explicitly sets `tlsAllowConnectionsWithoutCertificates` so SCRAM clients can connect without presenting a certificate **over TLS**. Those clients still need MongoDB credentials for protected operations. x.509 clients present a trusted client certificate and authenticate through `$external`.

| Setting/choice | Meaning in this lab |
|---|---|
| `requireTLS` | Plaintext clients rejected |
| CA file | Trust anchor for certificate verification |
| Server PEM | Server certificate plus private key |
| SANs | DNS `mongo41`, DNS `localhost`, IP `127.0.0.1` |
| Allow connections without client certificates | Keeps the TLS/SCRAM administrator path; does not disable access control |
| `$external` / `MONGODB-X509` | Certificate-based MongoDB identity |
| Custom reader role | `find` on the chapter event collection only |

This is client authentication on a standalone. Replica-set/sharded-cluster membership authentication requires a separate supported procedure, compatible member certificates and coordinated rollout. The client subjects below use a different organization/unit from the server; do not reuse member certificates as application credentials.

Use an organizational CA and managed private-key lifecycle in production. The disposable lab CA key is unencrypted and locally protected to make the exercise reproducible; it is never mounted into the MongoDB server or clients. The certificate lifetimes and key choices are lab fixtures, not an organizational cryptographic policy.

## 3. Verify the Chapter 41 baseline before changing transport

Use **Bash** in the retained `mongodb-ch41` folder. Do not recreate its volumes or first administrator.

```bash
dc41() { docker compose -p mongodb-ch41 -f compose.yaml "$@"; }
set -a
source .env
set +a
openssl version
docker version
dc41 ps -a
mkdir -p evidence-ch42
cp compose.yaml compose.pre-tls41.yaml
docker exec -it mongodb-ch41 mongosh 'mongodb://127.0.0.1:27017/admin' --quiet --username ch41_bootstrap --authenticationDatabase admin --authenticationMechanism SCRAM-SHA-256 --password
```

In the authenticated **mongosh** session:

```javascript
const baseline42 = db.adminCommand({ connectionStatus: 1 });
if (baseline42.ok !== 1 || baseline42.authInfo.authenticatedUsers.length !== 1 ||
    baseline42.authInfo.authenticatedUsers[0].user !== "ch41_bootstrap" ||
    baseline42.authInfo.authenticatedUsers[0].db !== "admin") throw new Error("Wrong administrator");
if (db.getSiblingDB("mongodb_enterprise_tutorial_ch41").getCollectionNames().length ||
    db.getSiblingDB("mongodb_enterprise_tutorial_ch41_other").getCollectionNames().length)
  throw new Error("Chapter 41 data cleanup incomplete");
const expectedAdmin42 = ["ch41_bootstrap", "ch41_identity", "ch41_data"];
const existingAdmin42 = db.getSiblingDB("admin").runCommand({ usersInfo: 1, showCredentials: false });
if (existingAdmin42.ok !== 1 || existingAdmin42.users.length !== 3 ||
    !existingAdmin42.users.every(u => expectedAdmin42.includes(u.user)))
  throw new Error("Unexpected administrator inventory");
printjson({ version: db.version(), shell: version(), identity: baseline42.authInfo,
  administrators: existingAdmin42.users.map(u => ({ user: u.user, roles: u.roles })) });
```

Record image digest, actual versions, original volume names and redacted administrator roles. Exit before the restart. This standalone restart causes an outage; it is not an online rollout or an AZ failure test.

## 4. Create a synthetic CA and server certificate

Save **`scripts/certificates42.sh`**. Run only once with a fresh `pki` directory. Secrets remain local; do not commit `pki`, private keys or combined PEM files to the tutorial repository.

```bash
#!/usr/bin/env bash
set -euo pipefail
umask 077
test ! -e pki || { echo 'Existing PKI; inspect before changing it' >&2; exit 1; }
mkdir -p pki/ca pki/public pki/server pki/clients
openssl req -x509 -newkey rsa:3072 -nodes -sha256 -days 365 \
  -keyout pki/ca/ca.key -out pki/public/ca.crt \
  -subj '/C=US/O=Ch42TrainingCA/CN=Ch42TrainingRoot' \
  -addext 'basicConstraints=critical,CA:TRUE' \
  -addext 'keyUsage=critical,keyCertSign,cRLSign'
openssl req -new -newkey rsa:3072 -nodes -sha256 \
  -keyout pki/server/server.key -out pki/server/server.csr \
  -subj '/C=US/O=Ch42Server/OU=Database/CN=mongo41'
cat > pki/server/server.ext <<'EOF'
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment,keyAgreement
extendedKeyUsage=serverAuth,clientAuth
subjectAltName=DNS:mongo41,DNS:localhost,IP:127.0.0.1
subjectKeyIdentifier=hash
authorityKeyIdentifier=keyid,issuer
EOF
openssl x509 -req -in pki/server/server.csr -CA pki/public/ca.crt \
  -CAkey pki/ca/ca.key -set_serial 1001 -days 45 -sha256 \
  -extfile pki/server/server.ext -out pki/server/server.crt
cat pki/server/server.crt pki/server/server.key > pki/server/server.pem
chmod 600 pki/ca/ca.key pki/server/server.key pki/server/server.pem
chmod 644 pki/public/ca.crt
openssl verify -CAfile pki/public/ca.crt -purpose sslserver \
  -verify_hostname mongo41 pki/server/server.crt
openssl verify -CAfile pki/public/ca.crt -purpose sslserver \
  -verify_ip 127.0.0.1 pki/server/server.crt
```

```bash
bash scripts/certificates42.sh
```

The SAN must cover the actual connection name. CN alone is not a substitute for planned DNS/IP SANs. All clients below use the same pinned image; OpenSSL runs on the host's Bash environment. Keep the CA key off the server, preserve its confidentiality and do not use these synthetic certificates for real services.

## 5. Create reader, renewed and unregistered client certificates

Save **`scripts/clients42.sh`** and run once after the CA exists:

```bash
#!/usr/bin/env bash
set -euo pipefail
umask 077
test -f pki/ca/ca.key && test -f pki/public/ca.crt
test ! -e pki/clients/reader.pem || { echo 'Client PKI exists; inspect first' >&2; exit 1; }
cat > pki/clients/client.ext <<'EOF'
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature
extendedKeyUsage=clientAuth
subjectKeyIdentifier=hash
authorityKeyIdentifier=keyid,issuer
EOF
for item in reader:2001 reader-renewed:2002 unregistered:2003; do
  label=${item%:*}
  serial=${item#*:}
  case "$label" in reader|reader-renewed) cn=events-reader ;; unregistered) cn=unregistered ;; *) exit 1 ;; esac
  openssl req -new -newkey rsa:3072 -nodes -sha256 \
    -keyout "pki/clients/$label.key" -out "pki/clients/$label.csr" \
    -subj "/C=US/O=Ch42Client/OU=Applications/CN=$cn"
  openssl x509 -req -in "pki/clients/$label.csr" -CA pki/public/ca.crt \
    -CAkey pki/ca/ca.key -set_serial "$serial" -days 45 -sha256 \
    -extfile pki/clients/client.ext -out "pki/clients/$label.crt"
  cat "pki/clients/$label.crt" "pki/clients/$label.key" > "pki/clients/$label.pem"
  chmod 600 "pki/clients/$label.key" "pki/clients/$label.pem"
  openssl verify -CAfile pki/public/ca.crt -purpose sslclient "pki/clients/$label.crt"
  openssl x509 -in "pki/clients/$label.crt" -subject -nameopt RFC2253 -noout \
    | sed 's/^subject= *//' > "pki/public/$label-subject.txt"
done
cmp pki/public/reader-subject.txt pki/public/reader-renewed-subject.txt
openssl req -x509 -newkey rsa:3072 -nodes -sha256 -days 365 \
  -keyout pki/ca/wrong-ca.key -out pki/public/wrong-ca.crt \
  -subj '/C=US/O=Ch42WrongCA/CN=UntrustedTrainingRoot' \
  -addext 'basicConstraints=critical,CA:TRUE' \
  -addext 'keyUsage=critical,keyCertSign,cRLSign'
chmod 644 pki/public/*.crt pki/public/*-subject.txt
```

```bash
bash scripts/clients42.sh
openssl x509 -in pki/clients/reader.crt -noout -subject -issuer -serial -dates -fingerprint -sha256
openssl x509 -in pki/clients/reader-renewed.crt -noout -subject -issuer -serial -dates -fingerprint -sha256
```

Use the **RFC2253 subject output**, not a guessed CN or manually reversed DN. The two reader certificates have the same subject, different keys and serials. The unregistered certificate is valid under the trusted CA but has a different subject. Client certificates have `clientAuth`. The server certificate includes both `serverAuth` and `clientAuth`, following MongoDB's documented rule when no separate TLS cluster file is configured; this standalone lab does not exercise member authentication.

## 6. Offline validation and safe certificate inventory

Save public certificate inventory; never print the PEM private-key content:

```bash
openssl x509 -in pki/server/server.crt -noout -subject -issuer -serial -dates -fingerprint -sha256 > evidence-ch42/server-certificate.txt
openssl x509 -in pki/clients/reader.crt -noout -subject -issuer -serial -dates -fingerprint -sha256 > evidence-ch42/reader-certificate.txt
openssl x509 -in pki/clients/reader-renewed.crt -noout -subject -issuer -serial -dates -fingerprint -sha256 > evidence-ch42/renewed-certificate.txt
openssl verify -CAfile pki/public/ca.crt -purpose sslclient pki/clients/reader.crt
if openssl verify -CAfile pki/public/wrong-ca.crt pki/server/server.crt > evidence-ch42/offline-wrong-ca.txt 2>&1; then exit 1; fi
if openssl verify -CAfile pki/public/ca.crt -verify_hostname wrongname42 pki/server/server.crt > evidence-ch42/offline-wrong-host.txt 2>&1; then exit 1; fi
FUTURE42=$(date -u -d '+60 days' +%s)
if openssl verify -CAfile pki/public/ca.crt -purpose sslclient -attime "$FUTURE42" pki/clients/reader.crt > evidence-ch42/offline-expired.txt 2>&1; then exit 1; fi
```

Inspect outputs: the failures must be untrusted issuer, hostname mismatch and certificate expiry at the simulated verification time. An absent file or OpenSSL option error is a failed test. The `-attime` test is an **offline expiry check**, not evidence that the running MongoDB server rejected an actually expired certificate. No host/server clock is changed.

Certificate inventory should include issuer, subject, SANs, EKU, serial, fingerprint, validity, owner and renewal date. It should never include private keys. Alert and renew before expiry with enough time for rollout and recovery; a certificate being valid today does not establish adequate renewal lead time.

## 7. Enable TLS using the same server volumes

Allow the container's `mongodb` user to read the server PEM without making it world-readable. The helper mounts only server material, not client/CA private keys:

```bash
docker run --rm --user 0 --entrypoint sh -v "$PWD/pki/server:/server" "$MONGO_IMAGE" -c 'chown -R "$(id -u mongodb):$(id -g mongodb)" /server; chmod 700 /server; chmod 600 /server/server.key /server/server.pem; chmod 644 /server/server.crt'
```

On hosts with different bind-mount/permission semantics, verify actual readability and permissions instead of loosening them globally. Root/host administrators remain trusted.

Replace **`compose.yaml`** with this configuration, keeping the same project/service/volume names:

```yaml
services:
  mongo41:
    image: ${MONGO_IMAGE:?Set a pinned image digest}
    container_name: mongodb-ch41
    command: ["mongod", "--auth", "--bind_ip_all", "--port", "27017", "--wiredTigerCacheSizeGB", "0.25", "--tlsMode", "requireTLS", "--tlsCertificateKeyFile", "/tls/server/server.pem", "--tlsCAFile", "/tls/ca.crt", "--tlsAllowConnectionsWithoutCertificates"]
    mem_limit: 1g
    networks:
      security41:
        aliases: [wrongname42]
    volumes:
      - data41:/data/db
      - config41:/data/configdb
      - ./scripts:/scripts:ro
      - ./pki/server:/tls/server:ro
      - ./pki/public/ca.crt:/tls/ca.crt:ro
networks:
  security41:
    internal: true
volumes:
  data41:
  config41:
```

The extra `wrongname42` DNS alias deliberately resolves to the same server but is absent from its SANs. It makes the hostname-negative test distinct from a DNS failure.

```bash
dc41 config
dc41 up -d --force-recreate mongo41
dc41 ps -a
dc41 logs --tail 100 mongo41
docker exec -it mongodb-ch41 mongosh 'mongodb://127.0.0.1:27017/admin' --tls --tlsCAFile /tls/ca.crt --quiet --username ch41_bootstrap --authenticationDatabase admin --authenticationMechanism SCRAM-SHA-256 --password
```

In the authenticated **mongosh** session:

```javascript
const options42 = db.adminCommand({ getCmdLineOpts: 1 });
if (options42.ok !== 1 || options42.parsed.security.authorization !== "enabled" ||
    options42.parsed.net.tls.mode !== "requireTLS" ||
    options42.parsed.net.tls.allowConnectionsWithoutCertificates !== true)
  throw new Error("Unexpected TLS/access-control configuration");
const admin42 = db.adminCommand({ connectionStatus: 1 });
if (admin42.ok !== 1 || admin42.authInfo.authenticatedUsers.length !== 1 ||
    admin42.authInfo.authenticatedUsers[0].user !== "ch41_bootstrap") throw new Error("Wrong admin identity");
printjson({ tlsMode: options42.parsed.net.tls.mode, authorization: options42.parsed.security.authorization,
  allowNoClientCertificate: options42.parsed.net.tls.allowConnectionsWithoutCertificates,
  identity: admin42.authInfo });
```

Exit and save the known-good TLS configuration only after this check succeeds:

```bash
cp compose.yaml compose.tls42.known-good.yaml
```

Keep the known-good certificate files/fingerprints protected. TLS connection success plus server configuration establishes this path; a generic TCP/ping success without these checks is insufficient.

If startup fails, preserve logs and keep the original volumes. Diagnose PEM readability, cert/key match, file paths, configuration and validity. Do not bypass CA/hostname verification or remove access control to get a passing screenshot.

## 8. Shared TLS client and authorization helpers

Define independent client containers on the retained project network. They mount public trust, protected client material and scripts; no CA signing key or server private key is supplied:

```bash
client42() {
  docker run --rm --network mongodb-ch41_security41 -v "$PWD/pki/public:/trust:ro" -v "$PWD/pki/clients:/client:ro" -v "$PWD/scripts:/scripts:ro" "$MONGO_IMAGE" mongosh "$@"
}
```

Save **`scripts/lib42.js`**:

```javascript
const name42 = "mongodb_enterprise_tutorial_ch42";
const app42 = db.getSiblingDB(name42);
const external42 = db.getSiblingDB("$external");
const subject42 = require("fs").readFileSync("/trust/reader-subject.txt", "utf8").trim();
const wc42 = { w: 1, j: true, wtimeout: 10000 };
function check42(ok, message) { if (!ok) throw new Error(message); }
function equal42(a, b) { return EJSON.stringify(a) === EJSON.stringify(b); }
function identity42(user, authDB) {
  const status = db.adminCommand({ connectionStatus: 1 });
  check42(status.ok === 1 && status.authInfo.authenticatedUsers.length === 1 &&
    status.authInfo.authenticatedUsers[0].user === user &&
    status.authInfo.authenticatedUsers[0].db === authDB, "Unexpected identity");
  printjson({ identity: status.authInfo.authenticatedUsers[0] });
}
function denied42(label, command) {
  let response;
  try { response = app42.runCommand(command); }
  catch (e) {
    check42(e.code === 13, label + " failed for another reason: " + String(e));
    printjson({ label, denied: true, code: e.code });
    return;
  }
  check42(response.ok !== 1 && response.code === 13, label + " allowed or wrong error");
  printjson({ label, denied: true, code: response.code });
}
function fixture42() {
  return Array.from({ length: 5 }, (_, i) => ({ _id: "tls-event-" + i, seq: i,
    payload: "synthetic-" + i }));
}
function verifyData42() {
  const docs = app42.events.find({}).sort({ seq: 1 }).maxTimeMS(5000).toArray();
  const expected = fixture42();
  check42(docs.length === 5, "Wrong fixture count");
  for (let i = 0; i < 5; i++) {
    for (const field of ["_id", "seq", "payload"]) check42(docs[i][field] === expected[i][field],
      "Wrong fixture field " + field);
  }
  check42(new Set(docs.map(d => d._id)).size === 5, "Duplicate IDs");
  return { count: docs.length, sum: docs.reduce((n, d) => n + d.seq, 0) };
}
```

`lib42.js` is used by independent clients that have `/trust`. The server-side `docker exec` session in Section 7 does not load it. Password-prompted administrators below run independent clients with `-it`; passwords are not embedded in command arguments.

## 9. Register the RFC2253 subject with a narrow role

Save **`scripts/setup42.js`** and execute as the retained bootstrap user over TLS:

```javascript
load("/scripts/lib42.js");
identity42("ch41_bootstrap", "admin");
check42(subject42 === "CN=events-reader,OU=Applications,O=Ch42Client,C=US", "Unexpected certificate subject");
check42(app42.getCollectionNames().length === 0, "Chapter namespace exists; reconcile first");
const existing = external42.runCommand({ usersInfo: { user: subject42, db: "$external" }, showCredentials: false });
check42(existing.ok === 1 && existing.users.length === 0, "Subject already registered");
const priorRoles = app42.runCommand({ rolesInfo: 1, showBuiltinRoles: false });
check42(priorRoles.ok === 1 && priorRoles.roles.length === 0, "Custom role already exists");
for (const collection of ["events", "audit", "control"]) check42(app42.createCollection(collection).ok === 1,
  "Collection creation failed");
check42(app42.events.insertMany(fixture42(), { writeConcern: wc42 }).acknowledged, "Fixture insert failed");
check42(app42.audit.insertOne({ _id: "audit-sentinel", owner: "chapter42" },
  { writeConcern: wc42 }).acknowledged, "Audit insert failed");
check42(app42.runCommand({ createRole: "Ch42CertificateReader", privileges: [
  { resource: { db: name42, collection: "events" }, actions: ["find"] }
], roles: [] }).ok === 1, "Reader role creation failed");
check42(external42.runCommand({ createUser: subject42,
  roles: [{ role: "Ch42CertificateReader", db: name42 }],
  customData: { owner: "chapter42" } }).ok === 1, "Certificate user creation failed");
const user = external42.runCommand({ usersInfo: { user: subject42, db: "$external" }, showCredentials: false });
check42(user.ok === 1 && user.users.length === 1, "Certificate user not found");
const uuids = app42.getCollectionInfos().map(c => ({ name: c.name, uuid: c.info.uuid }));
check42(app42.control.insertOne({ _id: "ownership", owner: "chapter42", subject: subject42,
  externalUserId: user.users[0].userId, uuids, at: new Date() }, { writeConcern: wc42 }).acknowledged,
  "Ownership checkpoint failed");
printjson({ configuredSubject: subject42, userId: user.users[0].userId, data: verifyData42() });
```

```bash
docker run --rm -it --network mongodb-ch41_security41 -v "$PWD/pki/public:/trust:ro" -v "$PWD/scripts:/scripts:ro" "$MONGO_IMAGE" mongosh 'mongodb://mongo41:27017/admin' --tls --tlsCAFile /trust/ca.crt --quiet --file /scripts/setup42.js --username ch41_bootstrap --authenticationDatabase admin --authenticationMechanism SCRAM-SHA-256 --password
```

The external user has no password. Its subject is the identifier, and its custom role limits event reads. Creating external users requires appropriate identity authority on `$external`; Chapter 41's identity administrator was scoped to another database and is not silently expanded here.

If setup fails, inspect the exact namespace, role and external user before retrying. Ownership includes collection UUIDs and the user's `userId`, so cleanup can reject replacement objects. Unrelated `$external` users are never assumed to belong to this chapter.

## 10. Prove x.509 authentication and least privilege

Save **`scripts/reader42.js`**:

```javascript
load("/scripts/lib42.js");
identity42(subject42, "$external");
printjson({ allowedRead: verifyData42() });
denied42("certificate reader insert", { insert: "events", documents: [{ _id: "unexpected" }] });
denied42("certificate reader delete", { delete: "events", deletes: [{ q: { _id: "tls-event-0" }, limit: 1 }] });
denied42("certificate reader audit read", { find: "audit", filter: {}, maxTimeMS: 5000 });
denied42("certificate reader role grant", { grantRolesToUser: "unexpected", roles: [{ role: "readWrite", db: name42 }] });
denied42("certificate reader collection drop", { drop: "events" });
printjson({ certificateReaderPassed: true, finalData: verifyData42() });
```

```bash
client42 'mongodb://mongo41:27017/mongodb_enterprise_tutorial_ch42?serverSelectionTimeoutMS=5000&connectTimeoutMS=3000&socketTimeoutMS=15000' --tls --tlsCAFile /trust/ca.crt --tlsCertificateKeyFile /client/reader.pem --authenticationDatabase '$external' --authenticationMechanism MONGODB-X509 --quiet --file /scripts/reader42.js > evidence-ch42/x509-reader.json
```

The shell derives the username from the certificate; `$external` is quoted to prevent Bash variable expansion. Successful login must identify the exact subject, and all prohibited operations must return code 13. A valid certificate is not permission to read `audit` or mutate `events`.

The negative grant uses a nonexistent target but still requires authorization. If the server returns a user-not-found or another category instead of code 13, the strict helper fails: investigate the authorization/result behavior rather than accepting the wrong error as a pass.

## 11. Distinguish transport, authentication and authorization failures

Run each independent negative connection and inspect the saved error. A nonzero process exit alone is insufficient: missing Docker images, bad paths and DNS errors are not the intended failures.

```bash
if client42 'mongodb://mongo41:27017/?serverSelectionTimeoutMS=5000&connectTimeoutMS=3000' --quiet --eval 'db.adminCommand({ping:1})' > evidence-ch42/plaintext-rejected.txt 2>&1; then exit 1; fi
if client42 'mongodb://mongo41:27017/?serverSelectionTimeoutMS=5000&connectTimeoutMS=3000' --tls --tlsCAFile /trust/wrong-ca.crt --quiet --eval 'db.adminCommand({ping:1})' > evidence-ch42/wrong-ca-rejected.txt 2>&1; then exit 1; fi
if client42 'mongodb://wrongname42:27017/?serverSelectionTimeoutMS=5000&connectTimeoutMS=3000' --tls --tlsCAFile /trust/ca.crt --quiet --eval 'db.adminCommand({ping:1})' > evidence-ch42/wrong-host-rejected.txt 2>&1; then exit 1; fi
if client42 'mongodb://mongo41:27017/?serverSelectionTimeoutMS=5000&connectTimeoutMS=3000' --tls --tlsCAFile /trust/ca.crt --tlsCertificateKeyFile /client/unregistered.pem --authenticationDatabase '$external' --authenticationMechanism MONGODB-X509 --quiet --eval 'db.adminCommand({connectionStatus:1})' > evidence-ch42/unregistered-subject-rejected.txt 2>&1; then exit 1; fi
```

| Test | Intended failure evidence |
|---|---|
| Plaintext request | Server refuses non-TLS connection; correlate server log if client sees disconnect |
| Wrong CA | Client rejects server certificate chain |
| Wrong hostname | Client rejects server name/SAN match while alias resolves to same server |
| Trusted but unregistered subject | TLS succeeds; MongoDB authentication fails, normally code 18 |
| Registered reader attempting mutation | Authentication succeeds; MongoDB authorization fails with code 13 |

Do not expect one universal TLS error string across driver/OpenSSL versions. Record actual category and relevant server/client evidence. Never use invalid-certificate or invalid-hostname bypass flags to make a negative test or broken setup pass.

Also prove that TLS without a client certificate or MongoDB credentials does not grant data access:

```bash
client42 'mongodb://mongo41:27017/' --tls --tlsCAFile /trust/ca.crt --quiet --eval 'load("/scripts/lib42.js"); const s=db.adminCommand({connectionStatus:1}); check42(s.authInfo.authenticatedUsers.length===0,"Unexpected identity"); denied42("anonymous TLS protected read",{find:"events",filter:{},maxTimeMS:5000});' > evidence-ch42/anonymous-tls-denied.json
```

The deliberate mixed SCRAM/x.509 policy allows this anonymous encrypted connection but denies its protected read. Requiring a client certificate at TLS handshake for every client is a different policy that needs its own rollout and recovery plan.

## 12. Rehearse same-subject certificate renewal

The renewed certificate has a different private key/serial but the same RFC2253 subject. No database user or role change is required for that identity:

```bash
client42 'mongodb://mongo41:27017/mongodb_enterprise_tutorial_ch42?serverSelectionTimeoutMS=5000&socketTimeoutMS=15000' --tls --tlsCAFile /trust/ca.crt --tlsCertificateKeyFile /client/reader-renewed.pem --authenticationDatabase '$external' --authenticationMechanism MONGODB-X509 --quiet --file /scripts/reader42.js > evidence-ch42/renewed-reader.json
client42 'mongodb://mongo41:27017/mongodb_enterprise_tutorial_ch42?serverSelectionTimeoutMS=5000&socketTimeoutMS=15000' --tls --tlsCAFile /trust/ca.crt --tlsCertificateKeyFile /client/reader.pem --authenticationDatabase '$external' --authenticationMechanism MONGODB-X509 --quiet --file /scripts/reader42.js > evidence-ch42/original-reader-still-valid.json
```

Both certificates pass while trusted and valid. This demonstrates renewal overlap and the important limit: replacing a PEM file in one service does not revoke every old same-subject certificate. Changing the subject creates a different MongoDB identity and requires registration/roles for that subject.

Plan renewal with key issuance, secure distribution, consumer/pool restart or reload, fresh-session checks and monitoring. Retire old material according to PKI policy; compromise response may need certificate revocation/trust changes and identity retirement, not just issuance of a new serial. This lab does not configure/test CRLs, OCSP, compromised-key revocation, server-certificate live reload or production consumer cutover.

For server renewal, verify the new key/certificate match, chain, SANs, purposes, validity and file permissions before replacing material. Preserve a valid known-good pair and test the exact MongoDB reload/restart procedure for the installed version. A CA rotation additionally needs an overlap/trust-distribution plan for every server and client.

## 13. Recovery and certificate operational checks

| Symptom | First evidence | Recovery direction |
|---|---|---|
| Server fails to start after TLS change | Mongod logs, rendered Compose, mounted paths and file readability | Repair valid cert/key/config; retain original volumes |
| SCRAM administrator cannot connect | TLS trust/name validation versus authentication result | Restore tested TLS/SCRAM path; do not broaden reader roles |
| x.509 fails but TLS works | RFC2253 subject, `$external` user, mechanism and client PEM | Repair identity mapping or client credential selection |
| CA/hostname mismatch | Chain, issuer, SANs and actual URI host | Use approved CA and matching names; no validation bypass |
| Certificate approaching expiry | Validity inventory, owner and renewal lead time | Issue/test/roll out replacement before expiry |
| Old same-subject certificate still works | Serial/fingerprint, user identity and trust policy | Expected overlap until appropriate expiry/revocation/identity action |
| Denied operation unexpectedly succeeds | Effective role/resource/actions | Stop test, inspect excessive privileges and possible mutations |

The independent SCRAM bootstrap identity remains the recovery administrator **over TLS**. Do not retire it before testing a supported replacement administrator and recovery procedure. The client-reader identity has no identity-management privilege.

If a known-good TLS configuration is needed, inspect the current state first, stop the owned server, restore the validated configuration and still-valid certificate/key pair, then start the same project/volumes and run fresh admin/reader tests. Merely copying `compose.pre-tls41.yaml` would remove TLS; it is a before-change record, not the normal recovery target.

Do not delete the database volume, regenerate the CA over existing paths or create a new administrator as an outage reflex. Preserve error logs and fingerprints. On a real cluster, repair and restart/reload ordering must follow its supported topology procedure; this standalone restart plan cannot be copied across every member simultaneously.

## 14. Review effective access and close the security gates

In a fresh **TLS/SCRAM bootstrap** independent client, inspect only the chapter subject and role. Use the administrator command pattern from Section 9 without `--file`, then run:

```javascript
load("/scripts/lib42.js");
identity42("ch41_bootstrap", "admin");
const user42 = external42.runCommand({ usersInfo: { user: subject42, db: "$external" },
  showPrivileges: true, showCredentials: false });
check42(user42.ok === 1 && user42.users.length === 1, "Certificate user missing");
const u42 = user42.users[0];
check42(u42.roles.length === 1 && u42.roles[0].role === "Ch42CertificateReader" &&
  u42.roles[0].db === name42, "Unexpected direct role");
check42(u42.inheritedPrivileges.length === 1 &&
  equal42(u42.inheritedPrivileges[0].resource, { db: name42, collection: "events" }) &&
  equal42(u42.inheritedPrivileges[0].actions, ["find"]), "Unexpected effective privileges");
printjson({ subject: u42.user, userId: u42.userId, roles: u42.roles,
  inheritedPrivileges: u42.inheritedPrivileges, data: verifyData42() });
```

Preserve redacted identities, role actions/resources, certificate public metadata and actual negative-test categories. A passing reader test does not prove certificate revocation, production audit coverage, network isolation from host administrators or internal membership authentication. Mark those separate gates explicitly.

## 15. Guarded cleanup while retaining TLS

Save **`scripts/cleanup42.js`**. Execute through the TLS/SCRAM administrator pattern from Section 9, changing `--file` to `/scripts/cleanup42.js`.

```javascript
load("/scripts/lib42.js");
identity42("ch41_bootstrap", "admin");
const owned = app42.control.findOne({ _id: "ownership" });
check42(owned && owned.owner === "chapter42" && owned.subject === subject42 && owned.uuids.length === 3,
  "Ownership checkpoint missing");
const collections = app42.getCollectionInfos();
check42(collections.length === 3 && collections.every(c => ["events", "audit", "control"].includes(c.name)),
  "Unexpected collection footprint");
for (const c of collections) {
  const saved = owned.uuids.find(x => x.name === c.name);
  check42(saved && equal42(saved.uuid, c.info.uuid), "Collection replaced; stop cleanup");
}
check42(app42.control.countDocuments({}) === 1, "Unexpected control records");
verifyData42();
const audit = app42.audit.find({}).toArray();
check42(audit.length === 1 && audit[0]._id === "audit-sentinel" && audit[0].owner === "chapter42",
  "Audit fixture changed");
const users = external42.runCommand({ usersInfo: { user: subject42, db: "$external" }, showCredentials: false });
check42(users.ok === 1 && users.users.length === 1, "Owned external user absent");
const user = users.users[0];
check42(equal42(user.userId, owned.externalUserId) && user.customData && user.customData.owner === "chapter42" &&
  user.roles.length === 1 && user.roles[0].role === "Ch42CertificateReader" && user.roles[0].db === name42,
  "External user replaced or privileges changed");
const roles = app42.runCommand({ rolesInfo: 1, showBuiltinRoles: false, showPrivileges: true });
check42(roles.ok === 1 && roles.roles.length === 1 && roles.roles[0].role === "Ch42CertificateReader",
  "Unexpected custom role inventory");
const role = roles.roles[0];
check42(role.roles.length === 0 && role.privileges.length === 1 &&
  equal42(role.privileges[0].resource, { db: name42, collection: "events" }) &&
  equal42(role.privileges[0].actions, ["find"]), "Reader role changed");
check42(external42.runCommand({ dropUser: subject42 }).ok === 1, "External user removal failed");
check42(app42.runCommand({ dropRole: "Ch42CertificateReader" }).ok === 1, "Role removal failed");
check42(app42.dropDatabase().ok === 1, "Scoped data drop failed");
const afterUser = external42.runCommand({ usersInfo: { user: subject42, db: "$external" }, showCredentials: false });
const afterRoles = app42.runCommand({ rolesInfo: 1, showBuiltinRoles: false });
check42(afterUser.ok === 1 && afterUser.users.length === 0 && afterRoles.ok === 1 &&
  afterRoles.roles.length === 0 && app42.getCollectionNames().length === 0, "Cleanup incomplete");
printjson({ cleanupComplete: true, tlsRetained: true, administratorRetained: "ch41_bootstrap" });
```

After cleanup, a **fresh x.509 reader login** with either original or renewed certificate must fail authentication because the subject user is gone. TLS chain validation can still succeed; deleting a MongoDB identity is not cryptographic revocation of its certificate. A fresh TLS/SCRAM administrator must remain usable.

Keep `requireTLS`, administrator credentials, protected server certificate/CA trust and original volumes for subsequent security chapters. Do not restore plaintext transport as cleanup. Client/CA private keys are local secrets; retain or retire them through the lab's reviewed lifecycle. Their deletion is not required to verify the database cleanup and must not remove the active server PEM.

If setup/cleanup was interrupted, inspect recorded `userId`, UUIDs, role and remaining objects before any follow-up removal. Do not replay completed drops or touch unrelated `$external` users. If ownership was never recorded, manually establish the exact partial footprint first.

## 16. Acceptance checklist and review questions

- [ ] Verified the retained authenticated server, administrators, pinned image and original volumes.
- [ ] Generated/validated CA, server SAN/purpose, client purpose and RFC2253 subjects; keys protected locally.
- [ ] Enabled `requireTLS` and preserved access control; TLS/SCRAM administrator path verified.
- [ ] Registered only the owned reader subject with a collection-scoped `find` role.
- [ ] Fresh x.509 reader login identifies the exact `$external` subject and reads all five events.
- [ ] Registered reader's prohibited operations return code 13.
- [ ] Plaintext, wrong-CA and wrong-host tests fail for the intended transport categories.
- [ ] Trusted unregistered subject fails authentication; anonymous TLS protected read returns code 13.
- [ ] Offline future-time check detects expiry; live expired-certificate enforcement remains separately untested.
- [ ] Renewed same-subject certificate passes; original valid certificate still passes as expected.
- [ ] Effective access, public certificate inventory and known-good TLS recovery path recorded.
- [ ] Owned external user/role/data removed; fresh reader login fails and TLS administrator remains usable.

**Evidence:** Tool/image versions, redacted baseline/administrator identities, public certificate subjects/SANs/purposes/serials/fingerprints/validity, offline verification outcomes, rendered TLS configuration, server startup logs, reader identity/data and code-13 denials, actual transport/authentication failure categories, renewal overlap, effective privileges and cleanup. Do not attach private keys or password material. Docker/static certificate checks alone do not satisfy live MongoDB acceptance.

**Review questions:**

1. How do TLS server validation, x.509 authentication and MongoDB authorization differ?
2. Why must the connection hostname match a SAN?
3. Why use the RFC2253 subject instead of guessing the certificate username?
4. Why does a valid unregistered client certificate fail MongoDB authentication?
5. Why quote `$external` in Bash?
6. What does allowing connections without client certificates leave enforced?
7. Why can a renewed same-subject certificate and its predecessor both authenticate?
8. How does deleting the subject user differ from revoking a certificate?
9. What does an offline `-attime` test leave unproved about the running server?
10. Why retain a valid TLS administrator/recovery path during rollout and renewal?

## 17. References and next chapter

- [MongoDB 8.0: TLS configuration](https://www.mongodb.com/docs/v8.0/tutorial/configure-ssl/)
- [MongoDB 8.0: x.509 client authentication](https://www.mongodb.com/docs/v8.0/tutorial/configure-x509-client-authentication/)
- [MongoDB 8.0: configuration options](https://www.mongodb.com/docs/v8.0/reference/configuration-options/)
- [MongoDB 8.0: membership authentication with x.509](https://www.mongodb.com/docs/v8.0/tutorial/configure-x509-member-authentication/)
- [OpenSSL: x509 command](https://docs.openssl.org/3.0/man1/openssl-x509/)
- [OpenSSL: verify command](https://docs.openssl.org/3.0/man1/openssl-verify/)
- [Chapter 41 — Users Roles and Least Privilege](41-users-roles-and-least-privilege.md)

Next: **[Chapter 43 — Enterprise External Authentication Compatibility](43-enterprise-external-authentication-compatibility.md)**.

Previous: [Chapter 41 — Users Roles and Least Privilege](41-users-roles-and-least-privilege.md).
