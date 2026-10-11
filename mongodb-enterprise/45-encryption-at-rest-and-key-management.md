# 45 — Encryption at Rest and Key Management

Part 6 — Enterprise Security and Governance

**Baseline:** MongoDB Enterprise 8.0 on Linux with WiredTiger; record the exact server, mongosh, OpenSSL and operating-system versions.  
**Status:** Written; static review complete; live Enterprise encryption, KMIP and restore validation pending.  
**Prerequisites:** Chapters 41–44, authorized Enterprise binaries and a disposable Linux lab account with private storage.

## 1. Outcomes and lab boundaries

Create a fresh encrypted standalone, verify authenticated access over TLS, restart with its original key, take a clean offline copy, demonstrate that an unrelated key cannot recover that copy, and restore with the correct key. Then design KMIP access, rotation and recovery for a production deployment.

The executable lab uses local key management to make key dependency visible. It does not claim that local keyfiles satisfy a particular regulation. Production key lifecycle requirements need a supported manager and an organizational policy.

This is a new `mongodb-ch45` workspace and a new data directory. It does not alter the Chapter 35 sharded cluster, the retained Chapter 41–43 TLS service, or the Chapter 44 audit service. Do not point its commands at an existing production data path. Community installations can run the offline helper tests but cannot validate Enterprise encrypted storage.

## 2. What each encryption layer protects

| Layer | Protects | Boundary |
|---|---|---|
| Cloud-volume/filesystem encryption | Blocks or files under that storage boundary | A running host with storage access can often read mounted data |
| Enterprise encrypted storage engine | WiredTiger data files | An authorized database client still receives readable results |
| TLS | Connections between endpoints | Does not encrypt a logical export saved to disk |
| Client-side/Queryable Encryption | Selected application fields before storage | Separate driver, key-vault and query-design requirements; Chapter 46 |
| Audit-log encryption | Audit files through separately configured options | Storage-engine encryption does not automatically encrypt audit logs |

Diagnostic logs, dumps, application results and key files need their own access and encryption controls. Evaluate swap, core dumps, crash tooling, temporary files and backup tooling as separate exposure paths. A `strings` scan that cannot find a marker is not a proof of cryptographic protection.

Atlas has its own managed encryption and customer-key workflows. Do not apply these self-managed `mongod` commands to Atlas.

## 3. Keys, identities and failure domains

MongoDB uses an externally managed master key to protect its internal database keys. Data files depend on that key hierarchy. Replication copies logical data; it does not replicate the master keys or provide transport encryption. Inventory keys per member and use TLS between members.

| Credential/key | Purpose | Rotation/recovery owner |
|---|---|---|
| `security.encryptionKeyFile` | Local storage-encryption master key | Storage/key custodian; required for matching physical recovery |
| `security.keyFile` | Internal replica-set/sharded authentication | Database identity operations; not a storage-encryption key |
| TLS server certificate and private key | Server identity and transport | PKI owner |
| KMIP client certificate and private key | Authenticate a database process to the key manager | PKI and key-manager owners |
| KMIP key identifier | Reference to a managed key | Key custodian; identifier alone cannot decrypt data |
| SCRAM password | Authenticate a database user | Identity owner |

Keep key access separate from routine backup access. A backup and its usable master key stored together under the same unrestricted identity weaken the intended separation. Also avoid the opposite failure: a protected backup whose required key has been destroyed is not recoverable.

## 4. Preflight an authorized Linux lab

Run this lab as a non-root account on a disposable Linux host with an approved MongoDB Enterprise 8.0 installation. All lab processes and private files belong to that account. No system-service configuration is changed. The account needs `mongod`, `mongosh`, Python 3, OpenSSL and enough disk space for the original, offline backup and two restore copies.

```bash
test "$(uname -s)" = Linux
test "$(id -u)" -ne 0
command -v mongod
command -v mongosh
command -v python3
command -v openssl
mongod --version
mongosh --version
openssl version
```

Inspect the binary output for the exact version and Enterprise modules and record the approved distribution/entitlement. The server-side gate in Section 8 checks the running process again. If Enterprise is unavailable, stop the server path and mark it blocked.

Ports `27045` and `27046` must be free on loopback. Use your host's listener inspection tool before startup. The certificates below trust only this fresh lab CA; do not replace system trust or reuse production private keys.

Start a fresh shell session for the lab. Treat each code block as a separate step and stop on any unexpected output or failed command; do not paste the entire chapter as an unattended script.

## 5. Create private storage and non-overwriting keys

```bash
umask 077
mkdir mongodb-ch45
cd mongodb-ch45
export LAB45_ROOT="$PWD"
mkdir data logs secrets pki scripts evidence backup restore-wrong restore-good
printf '%s\n' 'chapter45-disposable-encryption-lab' > .chapter45-owned
```

The local key is outside `data` and will be excluded from the data backup. Both paths remain private to the same account for this teaching lab; production separation requires a stronger custody boundary.

Save `scripts/key45.py`. It creates a single base64-encoded 32-byte random key without printing it, refuses overwrite and verifies the properties used by this lab. It never hashes or exports key content.

```python
import base64
import os
import pathlib
import secrets
import stat
import sys

def create(path):
    with pathlib.Path(path).open("xb") as handle:
        os.chmod(path, 0o600)
        handle.write(base64.b64encode(secrets.token_bytes(32)) + b"\n")

def validate(path):
    path = pathlib.Path(path)
    if path.is_symlink():
        raise ValueError("symlink key paths are not accepted in this lab")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
        raise ValueError("key must be a regular file owned by the lab process user")
    if stat.S_IMODE(info.st_mode) != 0o600:
        raise ValueError("lab key mode must be 0600")
    raw = base64.b64decode(path.read_bytes().strip(), validate=True)
    if len(raw) != 32:
        raise ValueError("lab key must decode to exactly 32 bytes")
    return {"owner_matches_process": True, "mode": "0600", "decoded_bytes": 32}

if __name__ == "__main__":
    try:
        if len(sys.argv) != 3 or sys.argv[1] not in {"create", "validate"}:
            raise ValueError("usage: key45.py create|validate KEY_PATH")
        if sys.argv[1] == "create":
            create(sys.argv[2])
        print(validate(sys.argv[2]))
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
```

```bash
python3 scripts/key45.py create secrets/master45.key
python3 scripts/key45.py create secrets/unrelated45.key
```

The unrelated key is a negative-test fixture. Never configure it on the original database. A replica-set authentication keyfile and a TLS PEM file are not interchangeable with either file.

## 6. Create TLS and the encrypted startup configuration

Generate a short-lived private lab CA and server leaf. These commands produce new files in the fresh workspace; they are not a renewal workflow.

```bash
openssl req -x509 -newkey rsa:3072 -sha256 -nodes -days 30 \
  -keyout pki/ca.key -out pki/ca.crt \
  -subj '/CN=Chapter45LabCA' \
  -addext 'basicConstraints=critical,CA:TRUE' \
  -addext 'keyUsage=critical,keyCertSign,cRLSign'
openssl req -new -newkey rsa:3072 -nodes \
  -keyout pki/server.key -out pki/server.csr \
  -subj '/CN=localhost'
cat > pki/server.ext <<'EOF'
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=DNS:localhost,IP:127.0.0.1
EOF
openssl x509 -req -in pki/server.csr -CA pki/ca.crt -CAkey pki/ca.key \
  -CAcreateserial -out pki/server.crt -days 14 -sha256 -extfile pki/server.ext
cat pki/server.crt pki/server.key > pki/server.pem
chmod 600 pki/ca.key pki/server.key pki/server.pem
openssl verify -CAfile pki/ca.crt -purpose sslserver pki/server.crt
```

The server uses this leaf only for server TLS, with no cluster-authentication role. The CA private key is not passed to `mongod`.

Write an absolute-path configuration as JSON, which is valid YAML input for this configuration. Save `scripts/config45.py`:

```python
import json
import pathlib

root = pathlib.Path.cwd().resolve()
if (root / ".chapter45-owned").read_text().strip() != "chapter45-disposable-encryption-lab":
    raise ValueError("wrong workspace")
if any((root / "data").iterdir()):
    raise ValueError("initial encrypted data directory must be empty")
config = {
    "storage": {"dbPath": str(root / "data"), "engine": "wiredTiger",
                "wiredTiger": {"engineConfig": {"cacheSizeGB": 0.25}}},
    "systemLog": {"destination": "file", "path": str(root / "logs/server45.log"),
                  "logAppend": True},
    "net": {"bindIp": "127.0.0.1", "port": 27045,
            "tls": {"mode": "requireTLS", "certificateKeyFile": str(root / "pki/server.pem"),
                    "CAFile": str(root / "pki/ca.crt"),
                    "allowConnectionsWithoutCertificates": True}},
    "security": {"authorization": "enabled", "enableEncryption": True,
                 "encryptionCipherMode": "AES256-CBC",
                 "encryptionKeyFile": str(root / "secrets/master45.key")}
}
with (root / "mongod45.json").open("x", encoding="utf-8") as handle:
    json.dump(config, handle, indent=2)
```

```bash
python3 scripts/config45.py
```

Access control is enabled at first startup. The localhost exception allows creating the first administrator before any users/roles exist. Allowing clients without a certificate permits TLS/SCRAM; it does not permit plaintext or bypass user authentication.

The lab explicitly chooses CBC to keep the cold-copy restore exercise separate from GCM IV/counter rollover rules. This is not a universal cipher recommendation. Review cipher/platform and compliance requirements independently.

## 7. Start the fresh server and bootstrap access control

Run the process in the foreground in **Terminal A** from the same workspace:

```bash
mongod --config "$LAB45_ROOT/mongod45.json"
```

Leave it running. Startup messages go to `logs/server45.log`. Do not add `--fork` or let a system supervisor launch a second process against this directory.

In **Terminal B**, enter the same workspace and define the client wrappers:

```bash
cd /ABSOLUTE/PATH/TO/mongodb-ch45
export LAB45_ROOT="$PWD"
ese_admin45() {
  mongosh 'mongodb://localhost:27045/admin' --tls \
    --tlsCAFile "$LAB45_ROOT/pki/ca.crt" \
    --username ch45_bootstrap --authenticationDatabase admin \
    --authenticationMechanism SCRAM-SHA-256 --password "$@"
}
ese_restore45() {
  mongosh 'mongodb://localhost:27046/admin' --tls \
    --tlsCAFile "$LAB45_ROOT/pki/ca.crt" \
    --username ch45_bootstrap --authenticationDatabase admin \
    --authenticationMechanism SCRAM-SHA-256 --password "$@"
}
```

Save `scripts/bootstrap45.js`:

```javascript
const admin45 = db.getSiblingDB('admin');
print('Choose a unique disposable-lab administrator password:');
admin45.createUser({user: 'ch45_bootstrap', pwd: passwordPrompt(),
  mechanisms: ['SCRAM-SHA-256'], roles: [{role: 'root', db: 'admin'}],
  customData: {owner: 'chapter45-disposable-encryption-lab'}});
print('Administrator created; reconnect with authentication');
```

Connect locally without a user **only for initial bootstrap**:

```bash
mongosh 'mongodb://localhost:27045/admin' --tls \
  --tlsCAFile "$LAB45_ROOT/pki/ca.crt" --quiet --file scripts/bootstrap45.js
ese_admin45 --quiet --eval 'db.runCommand({ping: 1})'
```

Expect `ok: 1` from the authenticated ping. The administrator's root role is scoped operationally to this disposable standalone, not a recommended application role. Never save the password in a URI, command argument, environment variable or Git repository.

If the localhost exception does not work, investigate pre-existing users, a wrong data directory or a disabled exception. Do not restart with `--noauth`. Configuration generation refuses an initially nonempty directory for this reason.

## 8. Verify effective encryption and create deterministic data

Save `scripts/gate45.js`:

```javascript
const info45 = db.adminCommand({buildInfo: 1});
const hello45 = db.adminCommand({hello: 1});
const options45 = db.adminCommand({getCmdLineOpts: 1});
if (info45.ok !== 1 || !info45.modules?.includes('enterprise') ||
    !/^8\.0\./.test(info45.version)) throw new Error('Enterprise 8.0 gate failed');
if (hello45.setName || hello45.msg === 'isdbgrid') throw new Error('Standalone required');
const security45 = options45.parsed?.security;
if (options45.ok !== 1 || security45?.enableEncryption !== true ||
    security45.encryptionCipherMode !== 'AES256-CBC' ||
    options45.parsed.net?.tls?.mode !== 'requireTLS' ||
    security45.authorization !== 'enabled') throw new Error('Effective policy mismatch');
const status45 = db.adminCommand({serverStatus: 1});
if (status45.storageEngine?.name !== 'wiredTiger') throw new Error('WiredTiger required');
print(EJSON.stringify({version: info45.version, modules: info45.modules,
  storageEngine: status45.storageEngine.name, encryptionConfigured: true,
  cipher: security45.encryptionCipherMode, tls: 'requireTLS',
  authorization: 'enabled', observedAt: new Date()}, null, 2));
```

```bash
ese_admin45 --quiet --file scripts/gate45.js
```

Inspect the startup log for successful encryption-key-manager initialization and absence of encryption errors. Record the corresponding timestamp/process/version. The effective settings and startup evidence together are stronger than merely finding an option in a file. They are still not an independent cryptographic certification.

Save `scripts/seed45.js`:

```javascript
const lab45 = db.getSiblingDB('mongodb_enterprise_tutorial_ch45');
if (lab45.getCollectionInfos().length) throw new Error('Fixture already exists');
lab45.createCollection('records');
const rows45 = Array.from({length: 100}, (_, i) => ({
  _id: i, owner: 'chapter45', amount: i * 7, marker: 'synthetic-encrypted-storage-lab'
}));
const result45 = lab45.records.insertMany(rows45, {writeConcern: {w: 1, j: true}});
if (!result45.acknowledged || Object.keys(result45.insertedIds).length !== 100) {
  throw new Error('Fixture insert was not acknowledged');
}
print('100 synthetic records inserted with journal acknowledgement');
```

Save `scripts/verify45.js`, reused after restart and restore:

```javascript
const lab45 = db.getSiblingDB('mongodb_enterprise_tutorial_ch45');
const rows45 = lab45.records.find({}, {_id: 1, owner: 1, amount: 1, marker: 1})
  .sort({_id: 1}).toArray();
if (rows45.length !== 100) throw new Error('Count mismatch');
let sum45 = 0;
for (let i = 0; i < rows45.length; i++) {
  const row45 = rows45[i];
  if (row45._id !== i || row45.owner !== 'chapter45' || row45.amount !== i * 7 ||
      row45.marker !== 'synthetic-encrypted-storage-lab') {
    throw new Error('Record mismatch at position ' + i);
  }
  sum45 += row45.amount;
}
if (sum45 !== 34650) throw new Error('Aggregate mismatch');
const validation45 = lab45.runCommand({validate: 'records', full: true});
if (validation45.ok !== 1 || validation45.valid !== true) throw new Error('Collection validation failed');
print(EJSON.stringify({count: rows45.length, amountSum: sum45,
  contentAssertions: 'passed', collectionValid: true, observedAt: new Date()}, null, 2));
```

```bash
ese_admin45 --quiet --file scripts/seed45.js
ese_admin45 --quiet --file scripts/verify45.js
```

Keep application content assertions separate from encryption configuration assertions. Journal acknowledgement on this standalone does not demonstrate replicated durability or a production RPO.

## 9. Prove restart dependency on the original key

In Terminal A, press Ctrl+C once and wait for `mongod` to exit cleanly. Inspect the log for completed shutdown. Do not use `kill -9`. Confirm no process still owns this data directory before proceeding.

Validate the original key again without displaying it:

```bash
python3 scripts/key45.py validate secrets/master45.key
```

Start the original server again in Terminal A with the same configuration. In Terminal B, run `gate45.js` and `verify45.js` again and authenticate using the same administrator password. Record both results.

A readable restart with the original key proves this instance can reopen the encrypted data. Replacing that file with a new random key is not rotation. Copying encrypted files without their usable master key is not recovery.

## 10. Make a clean offline data backup

Stop the original process cleanly again and leave it stopped throughout Sections 10–12. No writer, reader or background process may reopen `data` while it is being copied. This lab copies the complete standalone directory after shutdown; a running filesystem copy is not an equivalent backup procedure.

Use a fresh backup target and inspect its scope:

```bash
test -f .chapter45-owned
test ! -e backup/data45
cp -a data backup/data45
test ! -e backup/data45/master45.key
du -sh data backup/data45
```

Save `scripts/manifest45.py` to record integrity of this teaching backup. It refuses symlinks and excludes nothing silently. The manifest contains relative paths, lengths and file digests, never key material.

```python
import hashlib
import json
import pathlib
import sys

def manifest(root):
    root = pathlib.Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("backup root must be a real directory")
    entries = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("symlink in backup tree")
        if path.is_file():
            digest = hashlib.sha256()
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            entries.append({"path": path.relative_to(root).as_posix(),
                            "bytes": path.stat().st_size, "sha256": digest.hexdigest()})
        elif not path.is_dir():
            raise ValueError("unsupported backup entry")
    if not entries:
        raise ValueError("empty backup")
    return entries

if __name__ == "__main__":
    try:
        if len(sys.argv) != 2:
            raise ValueError("usage: manifest45.py STOPPED_DATA_COPY")
        print(json.dumps(manifest(sys.argv[1]), indent=2))
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
```

```bash
python3 scripts/manifest45.py backup/data45 > evidence/backup-manifest.json
```

Record the clean-stop time, exact binary, cipher, configuration revision, data path, backup time and the **protected recovery reference** for `master45.key`. Do not include the key in the manifest or archive. Store a separately protected recovery copy through your secret-management workflow and test the custodian's retrieval process; another unrestricted file beside the backup is not separated custody.

This manifest detects changed retained files when compared to a trusted original. It does not certify a consistent live snapshot, authenticate its creator, or prove that a key custodian can release the required key.

## 11. Fail recovery with an unrelated key on a disposable copy

Copy the backup into a separate target. Never perform the wrong-key experiment against the original or the only backup:

```bash
test ! -e restore-wrong/data45
cp -a backup/data45 restore-wrong/data45
```

Save `scripts/wrong_key45.py`. It runs a bounded foreground startup against the disposable copy, overriding only the data path, key, port and log path. Any exit must still be interpreted from the log: a busy port, unreadable certificate or permissions error is not proof of encryption-key rejection.

```python
import pathlib
import subprocess
import sys

root = pathlib.Path.cwd().resolve()
if (root / ".chapter45-owned").read_text().strip() != "chapter45-disposable-encryption-lab":
    raise ValueError("wrong workspace")
target = root / "restore-wrong/data45"
if not target.is_dir() or target.is_symlink():
    raise ValueError("disposable restore copy required")
command = ["mongod", "--config", str(root / "mongod45.json"),
           "--dbpath", str(target), "--port", "27046",
           "--encryptionKeyFile", str(root / "secrets/unrelated45.key"),
           "--logpath", str(root / "logs/wrong-key45.log")]
try:
    result = subprocess.run(command, timeout=30, capture_output=True, text=True)
except subprocess.TimeoutExpired:
    print("INCONCLUSIVE: startup did not reject the key within 30 seconds; child killed; inspect copy/log", file=sys.stderr)
    sys.exit(2)
if result.returncode == 0:
    print("UNEXPECTED: startup returned success; no negative-test acceptance", file=sys.stderr)
    sys.exit(2)
print({"exit_code": result.returncode,
       "status": "nonzero startup; require encryption/key error inspection",
       "log": "logs/wrong-key45.log"})
```

```bash
python3 scripts/wrong_key45.py
```

Inspect `logs/wrong-key45.log` privately. Require an error identifying failure to open/decrypt the encrypted storage or key hierarchy, plus a stopped process and no listening server. Record the actual error and exit code without assuming a universal error number or message. A timeout is inconclusive; the helper kills its child but the copy may have undergone recovery, so do not reuse it as the positive restore target.

The helper returning zero means it recorded a nonzero server exit, not that the cause was verified. Keep the manual cause check in the acceptance record.

## 12. Recover a fresh copy with the correct key

Use another fresh target from the untouched offline backup:

```bash
test ! -e restore-good/data45
cp -a backup/data45 restore-good/data45
python3 scripts/manifest45.py restore-good/data45 > evidence/restore-before-start.json
cmp evidence/backup-manifest.json evidence/restore-before-start.json
```

A successful comparison verifies copied bytes before startup. Starting `mongod` can change internal files, so do not demand the same filesystem manifest after recovery.

In Terminal A, start the restore copy using the original key on the other loopback port:

```bash
mongod --config "$LAB45_ROOT/mongod45.json" \
  --dbpath "$LAB45_ROOT/restore-good/data45" --port 27046 \
  --encryptionKeyFile "$LAB45_ROOT/secrets/master45.key" \
  --logpath "$LAB45_ROOT/logs/restore-good45.log"
```

In Terminal B:

```bash
ese_restore45 --quiet --file scripts/gate45.js
ese_restore45 --quiet --file scripts/verify45.js
```

The restored administrator user is in the copied data. Authenticate with its original password; do not rerun bootstrap. Require successful key-manager initialization, Enterprise/TLS/auth gates, all 100 records and sum `34650`, and valid collection metadata. Record elapsed time from the start of the drill to verified readable data, including key retrieval and authorization, as the measured lab recovery time.

The fixture remained idle before its cold copy, so this drill does not measure a production RPO or recovery under concurrent writes. A production drill must restore a known consistency point and reconcile a workload-specific recovery marker.

**GCM restore boundary:** if a real deployment uses AES256-GCM, do not reuse this CBC startup recipe unchanged. A cold filesystem restore requires the documented `--eseDatabaseKeyRollover` procedure to avoid IV reuse. That one-shot operation exits before normal startup and is distinct from master-key rotation. Review hot-backup handling and the exact server/tool workflow as well.

## 13. Configure and accept KMIP separately

KMIP replaces the local master-key source with a supported external manager. A generic cloud KMS API is not automatically a KMIP endpoint. Record vendor/product/firmware, protocol compatibility, MongoDB patch, client identity and approved key permissions before integration.

The following is a configuration fragment for a **separate fresh KMIP lab deployment**, not a conversion command for the locally encrypted directory. Merge it with that deployment's TLS/auth/storage settings and remove `encryptionKeyFile`:

```yaml
security:
  authorization: enabled
  enableEncryption: true
  encryptionCipherMode: AES256-CBC
  kmip:
    serverName: kmip-lab.example.internal
    port: 5696
    serverCAFile: /run/secrets/kmip/ca.crt
    clientCertificateFile: /run/secrets/kmip/client.pem
    keyIdentifier: APPROVED_EXISTING_LAB_KEY_ID
```

Replace the endpoint, paths and identifier with provisioned lab values. Use a valid client certificate accepted by the manager, with a readable private key limited to the database process identity. Keep database-server TLS and KMIP client TLS configurations distinct. Check server-name validation and certificate expiry. Do not disable hostname validation to get a connection.

For a managed existing key, confirm it is active and accessible to the intended client. If the approved procedure allows MongoDB to create a new key, omit `keyIdentifier` **on that fresh instance** and record the resulting identifier. Do not casually change identifiers on an already encrypted data directory.

| Acceptance exercise | Required evidence |
|---|---|
| Fresh encrypted startup | Key-manager initialization plus matching manager-side access audit |
| Restart | Retrieval of the same required key and correct application data |
| Unauthorized client | Separate disposable deployment denied; identity not silently broadened |
| Wrong endpoint/CA/name | Transport failure identified before key access |
| Manager outage | Controlled lab restart behavior and recovery after manager restoration |
| Key unavailable/inactive | Controlled disposable-copy failure; key custodian restores access |
| Manager failover | Supported HA endpoint behavior, latency and readable database restart |
| Client-certificate renewal | New valid identity works and old identity's removal is verified |

The manager's required operations depend on protocol mode. Current documentation lists Create, Get, Activate, GetAttributes, Encrypt and Decrypt for the default integration; legacy protocol changes requirements. Give the managed identity the approved scope for its workflow and verify actual behavior. Do not enable legacy mode solely to sidestep denied permissions.

Server uptime during a manager outage does not prove a cold restart will work. Acceptance needs retrieval after a stopped instance restarts. Avoid an invented universal key-cache duration or availability guarantee.

Review `security.kmip.activateKeys` and `keyStatePollingSeconds` in the effective policy. With key activation enabled, a transition to an inactive key can cause the database process to shut down. Also, a configured list of KMIP servers is selected at startup; do not infer continuous failover from successful startup against the first reachable endpoint.

## 14. Migrate existing data and rotate keys safely

Do not enable encryption in place on an existing unencrypted directory. Choose a reviewed migration with fresh storage and a verified rollback. For an existing replica set, rehearse replacement/initial-sync procedures from Chapter 30 on Enterprise members, preserve quorum and replace one secondary at a time. Verify synchronization, data and encryption readiness before touching the next member. Transfer primary only after eligible encrypted secondaries are healthy, then handle the former primary.

For a standalone, an outage-bound logical migration to a fresh encrypted target may be appropriate: consistent export, fresh encrypted startup, restore, counts/content/index/user checks, application cutover and recovery tests. Logical exports are readable unless separately protected; this is not a physical encrypted-file backup. Detailed dump/restore mechanics are covered in Chapter 50.

| Change | Supported approach | Required proof |
|---|---|---|
| New master key for local-file deployment | Fresh instance/storage and reviewed data migration; no in-place local-key rotation | Target data verified, old backups' key references retained |
| KMIP master-key rotation | Documented one-shot rotation on one stopped member | New key identifier, successful exit, normal restart and readable data |
| Fresh internal database keys | Fresh encrypted member and initial sync | Full synchronization and topology health |
| GCM database-key rollover after cold restore | Documented `eseDatabaseKeyRollover` workflow | Successful rollover exit and normal verified restart |
| TLS or KMIP certificate renewal | PKI credential lifecycle | Valid trust/name, authorized identity and restart/retrieval test |

For KMIP master-key rotation, prepare a one-shot copy of the effective config with `security.kmip.rotateMasterKey: true`; either use the approved new key identifier or the documented request-new-key workflow. Disable supervisor automatic restart for the one-shot operation. Stop one secondary, run the rotation, require successful completion and exit, then remove the rotation flag and start normally with the resulting key configuration. Verify data and secondary health before continuing. After secondaries pass, step down the primary and rotate the former primary. Never rotate multiple members together.

Master-key rotation re-protects the keystore; it does not rewrite the entire dataset with fresh database keys. Preserve prior master keys needed by older backups until their retention and restore obligations are satisfied. Rotation is not permission to destroy the historical key.

For a standalone, plan an outage and a verified pre-change backup. An unsuccessful rotation needs incident-specific recovery using recorded state; do not assume switching the key identifier back always reverses a completed keystore change.

## 15. Operating runbook and offline helper tests

| Symptom | First checks | Recovery boundary |
|---|---|---|
| Encryption option rejected | Binary modules, exact version, storage engine | Use an authorized compatible Enterprise binary |
| Existing data refuses new encryption | Wrong/freshness of `dbPath` | Preserve source; migrate into fresh storage |
| Local key unreadable | File mode, owner, mount, SELinux/AppArmor | Restore correct controlled access; no world-readable key |
| Encrypted copy will not open | Matching key source/identifier, cipher, whole-directory copy | Keep only backup immutable; diagnose on disposable copies |
| KMIP transport failure | Name, CA, expiry, routing/firewall | Repair authenticated endpoint connectivity |
| KMIP key access denied | Client identity, key state, manager ACL | Custodian restores intended access; no broad wildcard grant |
| Rotation repeatedly starts/exits | One-shot flag left enabled, supervisor policy | Remove flag after verified completion and normal-start config |
| Restore works but app fails | Restored users/roles, URI, indexes, data markers | Validate application contract separately |

Monitor startup/restart failures, manager latency/availability, certificate expiry, key state changes and unauthorized key access. Maintain a nonsecret inventory mapping process, environment, key identifier/reference, creation/rotation dates, backup dependencies and custodian. Export neither PEM private keys nor local master keys into ordinary telemetry.

Measure throughput, CPU and p50/p95/p99 latency using comparable datasets, concurrency and hardware on isolated baseline/encrypted instances. Include backup/restore elapsed time and manager failure scenarios. The 100-document fixture establishes correctness, not an encryption-overhead benchmark.

Save `scripts/test_helpers45.py` and run it independently of Enterprise. It uses temporary synthetic files, never the runtime key or backup:

```python
import os
import pathlib
import tempfile
import unittest
from key45 import create, validate
from manifest45 import manifest

class HelperTests(unittest.TestCase):
    def test_key_creation_and_overwrite_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            key = pathlib.Path(tmp) / "synthetic.key"
            create(key)
            self.assertEqual(validate(key)["decoded_bytes"], 32)
            with self.assertRaises(FileExistsError):
                create(key)
            os.chmod(key, 0o644)
            with self.assertRaises(ValueError):
                validate(key)

    def test_invalid_and_symlink_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            key = pathlib.Path(tmp) / "bad.key"
            key.write_bytes(b"not-base64!\n")
            os.chmod(key, 0o600)
            with self.assertRaises(ValueError):
                validate(key)
            link = pathlib.Path(tmp) / "link.key"
            link.symlink_to(key)
            with self.assertRaises(ValueError):
                validate(link)

    def test_manifest_changes_and_symlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            with self.assertRaises(ValueError):
                manifest(root)
            (root / "file").write_bytes(b"original")
            first = manifest(root)
            self.assertEqual(first, manifest(root))
            (root / "file").write_bytes(b"changed")
            self.assertNotEqual(first, manifest(root))
            (root / "link").symlink_to(root / "file")
            with self.assertRaises(ValueError):
                manifest(root)

if __name__ == "__main__":
    unittest.main()
```

```bash
python3 scripts/test_helpers45.py
```

Passing these tests validates file guards and manifest behavior only. It does not exercise MongoDB encryption, KMIP or real recovery.

## 16. Cleanup and acceptance record

Stop the restored process cleanly in Terminal A. Keep it stopped. To return to the original lab instance, start `mongod45.json` without restore overrides, authenticate and rerun both verification scripts. Stop it cleanly again before disposal.

Retain the evidence and required protected recovery key through the planned retention period. Do not destroy a key while retained data/backups depend on it. To dispose of the entire **owned disposable workspace**, first verify its path, ownership marker and stopped processes; then use the organization's normal disposal procedure. File deletion is not a guaranteed secure erase on SSD, snapshots or copy-on-write storage. Secret-manager revocation and storage sanitization must match the actual storage system and retention obligations.

No automatic recursive deletion is provided: this workspace contains the tested database, key and backup whose dependency is the point of the exercise. Do not commit `secrets`, `pki` private material, data files or physical backups to Git. Only sanitized notes and tutorial scripts belong in the tutorial repository.

| Acceptance item | Required observation | Authored chapter status |
|---|---|---|
| Edition/identity | Authorized Enterprise 8.0 and disposable Linux process | Runtime pending |
| Policy | WiredTiger, encryption enabled, CBC, TLS and access control | Runtime pending |
| Content | Exactly 100 validated fixture records; sum `34650` | Runtime pending |
| Restart | Original key reopens data and authenticated access works | Runtime pending |
| Backup | Clean shutdown, full offline copy, trusted manifest, separate key custody | Runtime pending |
| Negative recovery | Unrelated-key startup fails for an encryption-related reason | Runtime pending |
| Positive recovery | Fresh copy opens with correct key; administrator and content verified | Runtime pending |
| KMIP | Authorized key retrieval, negative cases, outage/failover/renewal drills | Separate integration pending |
| Rotation | One-member workflow, resulting key and historical backup dependencies | Separate drill pending |
| Helpers | Key overwrite/mode/input guards and manifest mutation/symlink checks | Offline tests only |

Review questions:

1. Why does an encrypted storage engine not protect a logical dump or authenticated query result?
2. How do the storage master key, replica-set authentication key and KMIP client key differ?
3. Why is replacing a local encryption keyfile not a rotation procedure?
4. What must be preserved to restore a backup taken before master-key rotation?
5. Why does a running server during a KMIP outage not prove restart readiness?
6. Which extra step matters for a cold filesystem restore using GCM?

## 17. References and next chapter

Consult the exact deployed release and key-manager documentation:

- [Encryption at rest and coverage boundaries](https://www.mongodb.com/docs/v8.0/core/security-encryption-at-rest/)
- [Configure encryption and migrate existing data](https://www.mongodb.com/docs/v8.0/tutorial/configure-encryption/)
- [Master-key rotation and member replacement](https://www.mongodb.com/docs/v8.0/tutorial/rotate-encryption-key/)
- [mongod encryption and database-key rollover options](https://www.mongodb.com/docs/v8.0/reference/program/mongod/)
- [Self-managed configuration options](https://www.mongodb.com/docs/v8.0/reference/configuration-options/)
- [Localhost exception](https://www.mongodb.com/docs/v8.0/core/localhost-exception/)

Next: **Chapter 46 — Client Side and Queryable Encryption** (planned).
