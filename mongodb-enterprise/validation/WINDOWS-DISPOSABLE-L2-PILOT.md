# Windows disposable MongoDB L2 pilot — Chapters 01–04

**Approval:** The user authorized creating a **new disposable local Docker container** for this pilot on 2026-10-20. Existing `mongodb-ch05` and its named volumes are strictly out of scope. These instructions require a human operator on the Windows host; no container was created by the authoring environment.

## Preconditions (PowerShell)

Use Docker Desktop with Linux containers. Choose a fresh, disposable standalone `mongod` with **no host or named volume mounts**. This is a **MongoDB Community 8.0 smoke pilot**; it does **not** validate MongoDB Enterprise-only capabilities. Keep the host port dedicated to the new lab, never forward a remote/production endpoint into it, and never reuse an existing container.

```powershell
docker info --format '{{.OSType}}'
docker ps -a --filter 'name=^/mongodb-dbre-l2-0104$'
docker ps --format '{{.Names}} {{.Ports}}'
Get-NetTCPConnection -LocalPort 27039 -ErrorAction SilentlyContinue
```

**STOP** if Docker is not running, the reserved container name already exists, port 27039 is in use, or the endpoint identity is unclear. Do not remove or overwrite any preexisting container.

## Create and independently identify the disposable lab

```powershell
docker pull mongo:8.0
docker run -d --name mongodb-dbre-l2-0104 --network bridge -p 127.0.0.1:27039:27017 --memory 2g mongo:8.0 --bind_ip_all
docker inspect mongodb-dbre-l2-0104 --format '{{.Id}} {{.Image}} {{json .Mounts}} {{json .NetworkSettings.Ports}}'
docker exec mongodb-dbre-l2-0104 mongosh --quiet --eval 'JSON.stringify(db.adminCommand({hello:1}))'
docker exec mongodb-dbre-l2-0104 mongosh --quiet --eval 'JSON.stringify(db.adminCommand({buildInfo:1}).version)'
```

Verify `Mounts` is empty, the image is the expected MongoDB image, the port is bound to **127.0.0.1 only**, and the `hello` response identifies a writable standalone, not a replica set or mongos. Stop if any condition differs. Record the image digest, container ID, server version, host UTC timestamp and Git commit in a local evidence folder **outside Git**. This temporary lab has no authentication and must never be exposed to other hosts.

## Run the approved pilot

From a local clone of `sssamant21/data-platform-engineering-tutorials`, check out `audit/mongodb-dbre-sre-readiness` and verify `git rev-parse HEAD` before proceeding.

```powershell
py -3 -m venv .venv-mongodb-l2
.\.venv-mongodb-l2\Scripts\python.exe -m pip install 'pymongo>=4,<5'
$env:MONGODB_LAB_URI = 'mongodb://127.0.0.1:27039'
$env:MONGODB_LAB_APPROVED = 'YES'
$env:MONGODB_LAB_MUTATION_APPROVED = 'YES'
$runId = 'pilot_20261020_l2'
New-Item -ItemType Directory -Force -Path "$HOME\mongodb-l2-evidence" | Out-Null
.\.venv-mongodb-l2\Scripts\python.exe mongodb-enterprise/validation/lab_preflight.py --chapter 1 --run-id $runId --allowed-host 127.0.0.1 --output "$HOME\mongodb-l2-evidence\preflight-ch01.json"
if ($LASTEXITCODE -ne 0) { throw 'Preflight failed; stop' }
.\.venv-mongodb-l2\Scripts\python.exe mongodb-enterprise/validation/ch01_04_smoke.py --allowed-host 127.0.0.1 --run-id $runId --output "$HOME\mongodb-l2-evidence\smoke-ch01-04.json"
if ($LASTEXITCODE -ne 0) { throw 'Smoke test failed; preserve container and evidence for review' }
```

The harness refuses preexisting chapter namespaces and drops only a precisely named, run-owned collection when ownership checks pass. It may leave a failed fixture for inspection. A successful smoke test is **partial L2 evidence**, not chapter certification.

## Post-run verification and teardown

Inspect the evidence JSON and confirm `smoke_passed`. Independently verify no run collections remain in the four chapter databases:

```powershell
docker exec mongodb-dbre-l2-0104 mongosh --quiet --eval 'for (let n=1;n<=4;n++){const d=db.getSiblingDB("mongodb_enterprise_tutorial_ch"+String(n).padStart(2,"0"));print(d.getName()+": "+JSON.stringify(d.getCollectionNames()))}'
```

Only after the evidence has been saved and reviewed, tear down **this exact disposable container**:

```powershell
docker rm -f mongodb-dbre-l2-0104
Remove-Item Env:MONGODB_LAB_URI,Env:MONGODB_LAB_APPROVED,Env:MONGODB_LAB_MUTATION_APPROVED -ErrorAction SilentlyContinue
```

Never run `docker volume prune`, broad container deletion, or commands against `mongodb-ch05`. If a test fails or ownership is uncertain, **do not** automatically tear down the container; retain it for diagnosis.

## Acceptance

Record exact Git SHA, image digest, MongoDB version/edition, Docker container ID, test command and exit code, preflight and smoke JSON, namespace cleanup check, exceptions and reviewer sign-off. Do not mark any chapter runtime-certified until the complete chapter lab, negative/recovery cases, and independent review are completed.
