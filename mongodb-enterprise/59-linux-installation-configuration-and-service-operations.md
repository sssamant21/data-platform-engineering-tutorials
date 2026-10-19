# 59 — Linux Installation Configuration and Service Operations

Part 8 — Administration Deployment and Integration

**Baseline:** Approved exact MongoDB Enterprise 8.0 patch/FCV 8.0, supported Ubuntu LTS/systemd, WiredTiger, mongosh, OpenSSL, Python 3 and PyYAML.  
**Status:** Written; static review complete; live Linux/systemd service lab pending.  
**Prerequisites:** Chapters 23–24, 41–48 and 57–58; a disposable Linux VM with sudo access and capacity for one isolated standalone.

## 1. Define installation and service acceptance

Install an approved Enterprise server binary into a dedicated lab location, create an authenticated TLS loopback service, verify configuration and runtime identity, insert a controlled dataset, stop cleanly, change one setting and restart without losing data. Restore the setting and verify application authorization.

The runnable path uses an approved manually downloaded Enterprise archive binary and a custom unit named `mongodb-ch59.service`. This avoids modifying a package's existing `mongod.service`. Package-managed production installation is discussed separately. No Ops Manager agent or Kubernetes operator manages this process.

This standalone demonstrates service operations, not replica-set availability or disaster recovery. Its deliberate stop interrupts the only database process. Never transpose its stop/restart commands onto production without the appropriate topology, maintenance and application plan.

## 2. Choose one installation and configuration authority

| Method | Configuration/service authority | Operational implication |
|---|---|---|
| Official distribution packages | Approved package config and installed service unit | Track package versions, repositories, defaults and service overrides |
| Approved Enterprise archive | Explicit binary path, config and custom service | Operator supplies dependencies, service integration and upgrade tracking |
| Ops Manager automation | Accepted automation configuration and Agent | Make changes through the supported management workflow |
| Kubernetes controller | Custom resource/controller and container lifecycle | Use supported operator/pod/PV procedures, not host service commands |

Use the official installation guide for the exact server release, OS and CPU architecture. Verify entitlement, artifact source and integrity. MongoDB Server, mongosh and Database Tools have separate versioning; a server archive does not necessarily include the client tools.

For package installations, pin every required component according to the package matrix and review upgrades explicitly. Installing a versioned meta-package alone can leave component packages on unintended versions. Inspect any installation-time service-start behavior before installing on a host with existing data or ports.

Do not mix an OS distribution's unofficial MongoDB package with the official Enterprise packages. Do not remove another package or purge its data to make this lab work. Use a fresh VM or resolve the existing installation through its change process.

## 3. Assess the Linux host and retained evidence

Choose a supported Ubuntu LTS/architecture combination using the MongoDB 8.0 platform matrix. Record kernel, OS, CPU, RAM, storage filesystem/mounts, available space/inodes, time synchronization and exact binary/client versions. Capacity and kernel tuning follow Chapter 24 and the selected release's production notes; they are not inferred from this small fixture.

```bash
umask 077
mkdir mongodb-ch59
cd mongodb-ch59
export LAB59_ROOT="$PWD"
mkdir scripts evidence pki private
export RUN59="$(python3 -c 'import uuid; print(uuid.uuid4())')"
printf '%s\n' "$RUN59" > evidence/run59.txt
cat /etc/os-release > evidence/os59.txt
uname -srm > evidence/kernel59.txt
df -Pk > evidence/filesystems59.txt
df -Pi > evidence/inodes59.txt
systemctl --version > evidence/systemd59.txt
openssl version > evidence/openssl59.txt
python3 -c 'import yaml; print(yaml.__version__)' > evidence/pyyaml59.txt
```

Use an approved PyYAML installation if unavailable. Do not silently install a new unpinned dependency into a production Python environment. Confirm PID 1 is systemd; a scratch container with `systemctl` installed does not supply a running systemd manager.

Inspect mounted storage and service limits before provisioning. Shell `ulimit` describes the shell; systemd limits and `/proc/PID/limits` describe the actual service. Free RAM on a shared host is not a guaranteed workload allocation.

## 4. Guard the fresh service boundary

This lab reserves `/opt/mongodb-ch59`, `/etc/mongodb-ch59`, `/var/lib/mongodb-ch59`, `/var/log/mongodb-ch59`, user/group `mongodb-ch59`, unit `mongodb-ch59.service` and TCP port 27559. They must all be unused. Stop if any ownership is ambiguous.

```bash
for path59 in /opt/mongodb-ch59 /etc/mongodb-ch59 /var/lib/mongodb-ch59 \
  /var/log/mongodb-ch59 /etc/systemd/system/mongodb-ch59.service; do
  sudo test ! -e "$path59" || exit 1
  sudo test ! -L "$path59" || exit 1
done
if getent passwd mongodb-ch59 >/dev/null; then exit 1; fi
if getent group mongodb-ch59 >/dev/null; then exit 1; fi
systemctl list-unit-files mongodb-ch59.service
sudo ss -ltnp 'sport = :27559'
```

Inspect the last two outputs: no loaded/installed unit anywhere and no listener on 27559 are required. These observations are not an atomic lock against another provisioning process. Reserve the host/resources for the exercise and recheck immediately before installation/start.

Existing services on other ports are not targets for this chapter. In particular, do not stop `mongod.service`, an Ops Manager agent, or an existing tutorial deployment.

## 5. Install the approved binary and owned directories

Download/extract the exact approved Enterprise archive in a private staging area using the selected-release official guide. Install its OS dependencies through the approved host process. Verify the archive/hash before extraction and binary execution; do not run `ldd` or `--version` on untrusted executable material.

Set `CH59_MONGOD` to the absolute `mongod` path from that verified archive and `CH59_BINARY_SHA256` to the approved binary hash derived from it. This avoids a hard-coded outdated patch URL and never overwrites `/usr/bin/mongod`.

```bash
test -f "${CH59_MONGOD:?set the verified absolute Enterprise mongod path}"
test -n "${CH59_BINARY_SHA256:?set its approved binary SHA-256}"
case "$CH59_MONGOD" in /*) ;; *) exit 1 ;; esac
printf '%s  %s\n' "$CH59_BINARY_SHA256" "$CH59_MONGOD" | sha256sum -c -
"$CH59_MONGOD" --version > evidence/mongod-version59.txt
mongosh --version > evidence/mongosh-version59.txt
sudo groupadd --system mongodb-ch59
sudo useradd --system --gid mongodb-ch59 --no-create-home \
  --home-dir /var/lib/mongodb-ch59 --shell /usr/sbin/nologin mongodb-ch59
sudo install -d -o root -g root -m 0755 /opt/mongodb-ch59 /opt/mongodb-ch59/bin
sudo install -o root -g root -m 0755 "$CH59_MONGOD" /opt/mongodb-ch59/bin/mongod
sudo install -d -o root -g mongodb-ch59 -m 0750 /etc/mongodb-ch59 /etc/mongodb-ch59/pki
sudo install -d -o mongodb-ch59 -g mongodb-ch59 -m 0700 \
  /var/lib/mongodb-ch59 /var/log/mongodb-ch59
printf '%s\n' "$RUN59" | sudo tee /etc/mongodb-ch59/run59.txt >/dev/null
sudo chown root:mongodb-ch59 /etc/mongodb-ch59/run59.txt
sudo chmod 0640 /etc/mongodb-ch59/run59.txt
sudo sha256sum /opt/mongodb-ch59/bin/mongod > evidence/installed-binary59.sha256
```

Review the version output for the expected Enterprise edition, exact patch and build. Missing shared libraries are an installation prerequisite failure, not a reason to change the global library path until an arbitrary binary starts. Keep server dependencies aligned with the archive's selected OS build.

## 6. Provision a fresh lab TLS identity

Generate a disposable CA and a server certificate for `localhost` and `127.0.0.1`. These private materials are for this isolated lab, not a production certificate authority. Certificate issuance and rotation in production use the Chapter 42/47 process.

```bash
openssl req -x509 -newkey rsa:3072 -nodes -days 7 \
  -keyout pki/ca59.key -out pki/ca59.pem -subj '/CN=Chapter59-Lab-CA' \
  -addext 'basicConstraints=critical,CA:TRUE' \
  -addext 'keyUsage=critical,keyCertSign,cRLSign'
openssl req -new -newkey rsa:3072 -nodes -keyout pki/server59.key \
  -out pki/server59.csr -subj '/CN=localhost'
cat > pki/server59.ext <<'EOF'
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth,clientAuth
subjectAltName=DNS:localhost,IP:127.0.0.1
EOF
openssl x509 -req -in pki/server59.csr -CA pki/ca59.pem -CAkey pki/ca59.key \
  -CAcreateserial -days 7 -out pki/server59.crt -extfile pki/server59.ext
cat pki/server59.key pki/server59.crt > pki/server59.pem
openssl verify -CAfile pki/ca59.pem -verify_hostname localhost pki/server59.crt
openssl verify -CAfile pki/ca59.pem -verify_ip 127.0.0.1 pki/server59.crt
sudo install -o root -g mongodb-ch59 -m 0640 pki/server59.pem \
  /etc/mongodb-ch59/pki/server59.pem
sudo install -o root -g mongodb-ch59 -m 0640 pki/ca59.pem \
  /etc/mongodb-ch59/pki/ca59.pem
```

The client trusts only this run's CA. Authentication uses SCRAM; no client certificate is required by this configuration. The service needs read access to the combined server PEM, not the CA signing key. Retain signing/private keys only in the protected workspace under the lab retention policy.

## 7. Write an explicit minimal configuration

Save `private/mongod59.yaml`:

```yaml
storage:
  dbPath: /var/lib/mongodb-ch59
systemLog:
  destination: file
  path: /var/log/mongodb-ch59/mongod.log
  logAppend: true
net:
  bindIp: 127.0.0.1
  port: 27559
  tls:
    mode: requireTLS
    certificateKeyFile: /etc/mongodb-ch59/pki/server59.pem
    CAFile: /etc/mongodb-ch59/pki/ca59.pem
    allowConnectionsWithoutCertificates: true
security:
  authorization: enabled
processManagement:
  fork: false
operationProfiling:
  mode: "off"
  slowOpThresholdMs: 100
```

`allowConnectionsWithoutCertificates` permits password-authenticated TLS clients without a client certificate; it does not disable server TLS or MongoDB authorization. The loopback bind is intentional. This is a standalone, so there is no replica-set internal keyfile or member configuration.

Use foreground execution under this custom `Type=simple` service. Do not mix `fork: true` with this unit. For a vendor package unit, follow its supported forking/override behavior and inspect the installed unit before changing defaults.

## 8. Reject configuration drift before starting

Save `scripts/config59.py`. The helper checks this exact lab schema and prevents duplicate-key overrides. It permits thresholds 100/150 only and rejects every other structural change. It is not a general MongoDB configuration validator.

```python
import hashlib
import json
import pathlib
import sys
import yaml

class UniqueLoader(yaml.SafeLoader):
    pass

def mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValueError('duplicate YAML key')
        result[key] = loader.construct_object(value_node, deep=deep)
    return result

UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)

def evaluate(blob, threshold):
    if type(threshold) is not int or threshold not in (100, 150):
        raise ValueError('only lab thresholds 100/150 supported')
    actual = yaml.load(blob, Loader=UniqueLoader)
    expected = {
        'storage': {'dbPath': '/var/lib/mongodb-ch59'},
        'systemLog': {'destination': 'file', 'path': '/var/log/mongodb-ch59/mongod.log',
                      'logAppend': True},
        'net': {'bindIp': '127.0.0.1', 'port': 27559, 'tls': {
            'mode': 'requireTLS', 'certificateKeyFile': '/etc/mongodb-ch59/pki/server59.pem',
            'CAFile': '/etc/mongodb-ch59/pki/ca59.pem',
            'allowConnectionsWithoutCertificates': True}},
        'security': {'authorization': 'enabled'},
        'processManagement': {'fork': False},
        'operationProfiling': {'mode': 'off', 'slowOpThresholdMs': threshold}}
    # JSON comparison distinguishes boolean values from integer substitutes.
    if json.dumps(actual, sort_keys=True) != json.dumps(expected, sort_keys=True):
        raise ValueError('configuration differs from the exact owned lab contract')
    return {'claim': 'exact_lab_configuration', 'thresholdMs': threshold,
            'sha256': hashlib.sha256(blob).hexdigest()}

if __name__ == '__main__':
    try:
        if len(sys.argv) != 3:
            raise ValueError('usage: config59.py CONFIG_YAML EXPECTED_THRESHOLD')
        print(json.dumps(evaluate(pathlib.Path(sys.argv[1]).read_bytes(), int(sys.argv[2])), indent=2))
    except (ValueError, TypeError, OSError, yaml.YAMLError) as error:
        print('REJECTED: ' + str(error), file=sys.stderr)
        sys.exit(1)
```

Review and install the checked file, then use MongoDB's own output-config parse path as the service user:

```bash
python3 scripts/config59.py private/mongod59.yaml 100 > evidence/config-baseline59.json
sudo install -o root -g mongodb-ch59 -m 0640 private/mongod59.yaml \
  /etc/mongodb-ch59/mongod.yaml
sudo -u mongodb-ch59 /opt/mongodb-ch59/bin/mongod \
  --config /etc/mongodb-ch59/mongod.yaml --outputConfig > private/output-config59.yaml
```

Require successful exit at every step. `--outputConfig` parses/resolves configuration and exits; it does not prove TLS file usability, storage access, port availability or service readiness. Do not enable external configuration expansion directives in this exercise. Resolved config can contain secrets in other deployments; keep it private.

## 9. Install the dedicated systemd unit

Save `private/mongodb-ch59.service`:

```ini
[Unit]
Description=Owned Chapter 59 MongoDB standalone lab
After=network.target

[Service]
Type=simple
User=mongodb-ch59
Group=mongodb-ch59
ExecStart=/opt/mongodb-ch59/bin/mongod --config /etc/mongodb-ch59/mongod.yaml
Restart=no
KillSignal=SIGTERM
KillMode=control-group
TimeoutStopSec=300
SendSIGKILL=no
LimitNOFILE=64000
LimitNPROC=64000
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
ProtectHome=true
ProtectSystem=strict
ReadWritePaths=/var/lib/mongodb-ch59 /var/log/mongodb-ch59

[Install]
WantedBy=multi-user.target
```

The unit disables automatic restarts and final SIGKILL for this controlled exercise. A stop timeout must be investigated: do not proceed while a process remains alive. Production restart policy, hardening and stop deadlines require their own availability/shutdown review and measured workload behavior.

```bash
sudo systemd-analyze verify "$LAB59_ROOT/private/mongodb-ch59.service"
sudo test ! -e /etc/systemd/system/mongodb-ch59.service || exit 1
sudo install -o root -g root -m 0644 private/mongodb-ch59.service \
  /etc/systemd/system/mongodb-ch59.service
sudo systemctl daemon-reload
systemctl cat mongodb-ch59.service > evidence/unit59.txt
sudo systemctl start mongodb-ch59.service
systemctl show mongodb-ch59.service -p ActiveState -p SubState -p MainPID \
  -p FragmentPath -p User -p Group -p LimitNOFILE -p LimitNPROC > evidence/service-start59.txt
```

Do not enable boot start in this disposable lab. `daemon-reload` refreshes systemd unit definitions; it does not reload MongoDB configuration. `systemctl start` returning success for `Type=simple` is also not a readiness probe: check the listener, logs and authenticated database response.

## 10. Bootstrap authentication and validate runtime

Connect locally with verified TLS before the first user exists. The localhost exception permits initial administrative bootstrap on this new authenticated service. Keep `authorization: enabled`; if a user already exists unexpectedly, investigate ownership rather than disable authentication.

```bash
mongosh 'mongodb://127.0.0.1:27559/admin?directConnection=true' \
  --tls --tlsCAFile "$LAB59_ROOT/pki/ca59.pem"
```

In that interactive shell, verify the port/service identity is the owned fresh standalone and create the first administrator with a prompted password:

```javascript
const bootstrapOpts59 = db.getSiblingDB('admin').runCommand({getCmdLineOpts: 1});
if (bootstrapOpts59.ok !== 1 || bootstrapOpts59.parsed.storage.dbPath !== '/var/lib/mongodb-ch59')
  throw new Error('wrong service');
db.getSiblingDB('admin').createUser({user: 'ch59_admin', pwd: passwordPrompt(),
  roles: [{role: 'root', db: 'admin'}]});
```

If your server's localhost-exception privileges do not allow the diagnostic command before bootstrap, verify the owned listener/PID/unit/config locally first and create only the initial user through the documented exception. Do not broaden bootstrap privileges. Close that session and reconnect with authentication:

```bash
mongosh 'mongodb://127.0.0.1:27559/admin?directConnection=true' \
  --tls --tlsCAFile "$LAB59_ROOT/pki/ca59.pem" --username ch59_admin \
  --authenticationDatabase admin --authenticationMechanism SCRAM-SHA-256 --password
```

Inspect `buildInfo`, FCV, `hello` and `getCmdLineOpts`. Require Enterprise 8.0, FCV 8.0, no replica-set name, correct paths/port/bind/TLS/auth and the expected profiler setting. Check service PID/executable/UID and its effective limits directly:

```bash
PID59="$(systemctl show mongodb-ch59.service -p MainPID --value)"
case "$PID59" in ''|0|*[!0-9]*) exit 1 ;; esac
sudo readlink -f "/proc/$PID59/exe"
sudo ps -p "$PID59" -o pid,user,group,args
sudo cat "/proc/$PID59/limits" > evidence/process-limits59.txt
sudo ss -ltnp 'sport = :27559' > evidence/listener59.txt
```

The executable must be `/opt/mongodb-ch59/bin/mongod`, user/group the lab identity and listener only `127.0.0.1:27559`. If the process exits between observations, reject the stale PID evidence and investigate. Do not accept a shell limit or an unrelated listener as proof of this service's effective state.

## 11. Create and verify the persistent dataset

Save `scripts/fixture59.js`; edit the run-ID file path to the protected workspace path on the client. Execute through the authenticated TLS administrator connection with `ACTION59=initialize`, then use verification mode for subsequent runs.

```javascript
const fs59 = require('fs');
const run59 = fs59.readFileSync('/approved/ch59/run59.txt', 'utf8').trim();
const action59 = process.env.ACTION59;
const a59 = db.getSiblingDB('admin');
const d59 = db.getSiblingDB('mongodb_enterprise_tutorial_ch59');
function check59(ok, message) { if (!ok) throw new Error(message); }
const options59 = a59.runCommand({getCmdLineOpts: 1});
check59(options59.ok === 1 && options59.parsed.storage.dbPath === '/var/lib/mongodb-ch59'
  && options59.parsed.net.port === 27559 && run59, 'wrong owned service');
const build59 = a59.runCommand({buildInfo: 1});
const fcv59 = a59.runCommand({getParameter: 1, featureCompatibilityVersion: 1});
check59(build59.version.startsWith('8.0.') && build59.modules.includes('enterprise') &&
  fcv59.featureCompatibilityVersion.version === '8.0', 'wrong baseline');
if (action59 === 'initialize') {
  check59(d59.getCollectionInfos().length === 0, 'database not empty');
  check59(d59.createCollection('orders').ok === 1, 'collection creation failed');
  d59.orders.createIndex({code: 1}, {unique: true, name: 'code_unique59'});
  d59.orders.insertMany(Array.from({length: 50}, (_, n) =>
    ({_id: n + 1, code: `order-${n + 1}`, amountCents: (n + 1) * 10})),
    {writeConcern: {w: 1, j: true, wtimeout: 30000}});
  d59.markers.insertOne({_id: 'owner', runId: run59, chapter: 59},
    {writeConcern: {w: 1, j: true, wtimeout: 30000}});
} else check59(action59 === 'verify', 'initialize or verify required');
const owner59 = d59.markers.findOne({_id: 'owner'});
check59(owner59 && owner59.runId === run59 && owner59.chapter === 59, 'owner mismatch');
const rows59 = d59.orders.find().sort({_id: 1}).toArray();
check59(rows59.length === 50, 'wrong count');
rows59.forEach((row, n) => check59(row._id === n + 1 && row.code === `order-${n + 1}` &&
  row.amountCents === (n + 1) * 10 && Object.keys(row).length === 3, 'document mismatch'));
check59(rows59.reduce((sum, row) => sum + row.amountCents, 0) === 12750, 'wrong sum');
check59(d59.orders.getIndexes().some(index => index.name === 'code_unique59' &&
  index.unique === true && index.key.code === 1), 'unique index missing');
printjson({runId: run59, count: 50, amountCents: 12750,
  profiling: d59.getProfilingStatus(), ordersUUID: d59.getCollectionInfos({name: 'orders'})[0].info.uuid});
```

Record the collection UUID externally before shutdown and compare it afterward. This service restart reuses the same dbPath and should preserve identity; unlike a logical restore, it does not intentionally recreate the collection. Retain exact documents and index checks, not just the count.

The standalone uses `w:1,j:true`; it has no replica redundancy or majority-of-three durability claim. This experiment demonstrates journaled persistence across a planned clean restart, not survival of a disk/host loss or abrupt power failure.

## 12. Perform a controlled configuration restart

Prepare a candidate copied from the baseline with only `slowOpThresholdMs` changed from 100 to 150. Keep the baseline as a protected rollback candidate. Check the full candidate with `config59.py`, not a loose text substitution across an unknown file.

```bash
python3 - <<'PY'
import pathlib
import yaml
source = pathlib.Path('private/mongod59.yaml')
config = yaml.safe_load(source.read_text())
config['operationProfiling']['slowOpThresholdMs'] = 150
with open('private/candidate59.yaml', 'x') as out:
    yaml.safe_dump(config, out, sort_keys=False)
PY
python3 scripts/config59.py private/candidate59.yaml 150 > evidence/config-candidate59.json
date -u +'%Y-%m-%dT%H:%M:%SZ' > evidence/stop-start59.txt
sudo systemctl stop mongodb-ch59.service
systemctl show mongodb-ch59.service -p ActiveState -p SubState -p MainPID
sudo ss -ltnp 'sport = :27559'
```

Require successful stop, `MainPID=0`, inactive service, no listener and no remaining process in the unit's cgroup. Inspect the MongoDB log for completion of shutdown/checkpoint activity. With `SendSIGKILL=no`, a timeout can leave a process alive; do not edit/restart over it. Do not remove lock or WiredTiger files to fix shutdown.

After confirmed stop, install the checked candidate, parse as the service user, then start:

```bash
sudo install -o root -g mongodb-ch59 -m 0640 private/candidate59.yaml \
  /etc/mongodb-ch59/mongod.yaml
sudo -u mongodb-ch59 /opt/mongodb-ch59/bin/mongod \
  --config /etc/mongodb-ch59/mongod.yaml --outputConfig > private/output-candidate59.yaml
sudo systemctl start mongodb-ch59.service
```

Repeat authenticated fixture verification, effective process/unit checks and startup-option inspection. Require profiler level zero and `slowms:150`, all 50 exact orders/12,750 cents, unchanged UUID and index. Record a new service invocation/PID and readiness time. A PID can theoretically be reused; use invocation/start timestamps as well as PID when comparing runs.

No `daemon-reload` is needed for this YAML-only change. MongoDB does not automatically apply every on-disk setting to the running process; this lab performs a controlled restart and then checks runtime.

## 13. Restore the baseline and test application access

Stop with the same complete shutdown checks. Revalidate `private/mongod59.yaml` at threshold 100, install it with the original permissions, parse as the service user and start again. Repeat fixture/UUID verification and require `slowms:100` with profiling disabled.

Create a fresh scoped application user through the authenticated administrator connection:

```javascript
const adminUser59 = db.getSiblingDB('admin');
if (adminUser59.getUser('ch59_app')) throw new Error('application username already exists');
adminUser59.createUser({user: 'ch59_app', pwd: passwordPrompt(),
  roles: [{role: 'readWrite', db: 'mongodb_enterprise_tutorial_ch59'}]});
```

Reconnect with `ch59_app` and the same verified TLS options/authentication DB. Verify the owner/run ID and 50 orders. Insert a separate run-owned marker using `w:1,j:true`; do not modify the acceptance fixture. Confirm an administrative `getParameter` operation is denied with unauthorized code 13. Do not interpret a network/TLS error as an authorization success.

Preserve the final application result and authenticated runtime observations. The administrative root account is used for provisioning/diagnostics, not presented as the application identity.

## 14. Operate logs, permissions and service settings

File logging and systemd journaling serve different paths here. MongoDB writes its configured file; the journal captures service lifecycle and early startup failures. Capture bounded relevant excerpts privately and redact credentials/internal connection information before sharing.

| Operation | Correct boundary |
|---|---|
| Change MongoDB YAML | Validate supported options; restart or use the documented runtime setter where appropriate |
| Change custom unit | Validate unit; `daemon-reload`; planned service restart if effective settings require it |
| Change vendor unit settings | Supported drop-in/config mechanism; preserve package ownership |
| Rotate logs | Supported MongoDB rotation or coordinated external procedure with correct reopen behavior |
| Change dbPath/mount | Planned data migration, ownership and capacity checks; empty new path is not the old dataset |
| Rotate certificate | Issue/validate trust material; supported reload/restart procedure and client checks |

Do not assume `systemctl reload` exists for a unit with no `ExecReload`, or that a generic SIGHUP reloads the entire MongoDB configuration. Avoid `copytruncate` or log deletion as an unreviewed solution to disk pressure; inspect rotation policy and open-file behavior. Chapter 24 covers capacity; service restart is not a substitute for finding sustained growth.

The unit's hardening settings are part of the observed runtime. `ProtectSystem=strict` permits writes only to the declared locations; apparmor/SELinux can impose additional policy. Fix the specific owned policy/permission failure rather than disabling host security globally.

## 15. Troubleshoot startup and shutdown failures

| Symptom | Inspect | Safe response |
|---|---|---|
| Unit starts then fails | Journal, configured log, parse output and shared-library prerequisites | Correct the exact cause before a new attempt |
| Permission denied | Service UID, path traversal, mount state and MAC policy | Fix only intended owned access |
| Address already in use | Exact port/listener PID and unit ownership | Resolve collision; never kill an unidentified process |
| TLS certificate/key error | PEM match, chain, expiry, file permissions and names | Correct issued material; retain verification |
| Database appears empty after restart | Effective dbPath, mount availability and fixture marker | Stop writes; restore correct authoritative path |
| Unknown option | Exact server release and supported schema | Correct configuration; do not downgrade blindly |
| Stop times out | Database logs, workload/checkpoint progress, unit/cgroup state | Investigate pending shutdown; do not start a second process |
| Service active but login fails | TLS/auth DB/username/mechanism and server readiness | Separate access failure from process state |

Never run `--repair` routinely after a failed startup. Preserve data and logs, diagnose the failure and follow a recovery plan if actual corruption is suspected. Removing lockfiles does not safely resolve a live process owning the same dbPath.

For replicated deployments, planned maintenance requires topology checks, one member at a time, application behavior and healthy redundancy before proceeding. For Ops Manager-managed services, change through automation and review the plan instead of applying this custom-unit procedure.

## 16. Acceptance, helper tests and cleanup

Before publication/use, test the config helper with valid 100/150 YAML, wrong bind/port/path/TLS/auth, fork enabled, extra keys, boolean/integer substitutions, duplicate keys and malformed YAML. Check Bash/JS/Python/YAML syntax, certificate name verification and unit parsing separately. Offline checks do not exercise MongoDB or a running systemd manager.

Live acceptance requires the installed artifact/version evidence, intended TLS/authentication, correct service identity/effective limits, exact initial fixture, graceful stopped state, verified candidate restart, unchanged dataset/UUID, restored baseline and scoped application authorization. Retain failed attempts and resolution evidence; do not hide them behind the final active state.

Capture final unit properties, listener/process evidence and relevant logs. Decide data/key retention before cleanup. First inspect all resource ownership and the on-disk run marker against this workspace:

```bash
test "$RUN59" = "$(sudo cat /etc/mongodb-ch59/run59.txt)" || exit 1
systemctl cat mongodb-ch59.service
sudo stat /opt/mongodb-ch59/bin/mongod /etc/mongodb-ch59/mongod.yaml \
  /var/lib/mongodb-ch59 /var/log/mongodb-ch59
sudo systemctl stop mongodb-ch59.service
systemctl show mongodb-ch59.service -p ActiveState -p SubState -p MainPID
sudo ss -ltnp 'sport = :27559'
```

After successful shutdown with no remaining unit process/listener, leave the lab service stopped and unenabled. Retain its data, configuration, binary and evidence until the retention decision. Any later unit/account/path deletion must target only these inspected owned resources. No purge or recursive wildcard deletion is supplied.

This tutorial's runtime status remains pending until the full service exercise is executed on the authorized supported Linux VM. Local helper, certificate and unit-syntax tests do not establish live database durability or readiness.

## 17. References and next chapter

- [MongoDB 8.0 Enterprise installation on Ubuntu](https://www.mongodb.com/docs/v8.0/tutorial/install-mongodb-enterprise-on-ubuntu/)
- [MongoDB 8.0 Enterprise archive installation](https://www.mongodb.com/docs/v8.0/tutorial/install-mongodb-enterprise-on-ubuntu-tarball/)
- [MongoDB 8.0 configuration options](https://www.mongodb.com/docs/v8.0/reference/configuration-options/)
- [mongod options, including outputConfig](https://www.mongodb.com/docs/v8.0/reference/program/mongod/)
- [Manage MongoDB processes](https://www.mongodb.com/docs/v8.0/tutorial/manage-mongodb-processes/)
- [systemd service source documentation](https://github.com/systemd/systemd/blob/main/man/systemd.service.xml)
- [Chapter 58 — Ops Manager Automation Monitoring and Agents](58-ops-manager-automation-monitoring-and-agents.md)

Next: **[Chapter 60 — Kubernetes Operator Compatibility and Deployment](60-kubernetes-operator-compatibility-and-deployment.md)**.

Previous: [Chapter 58 — Ops Manager Automation Monitoring and Agents](58-ops-manager-automation-monitoring-and-agents.md).
