# Chapter 10 Lab — Isolated PostgreSQL Physical Streaming Replication

**Audience:** DBRE/SRE · **Lab:** ~23 minutes of a 60-minute lesson · **Legacy runtime target:** PostgreSQL 17 · **Documentation baseline:** PostgreSQL 18 ([version policy](../../POSTGRESQL-18-BASELINE.md))  
**Runtime state:** Authored, **not executed** or independently reviewed

[Chapter 10](../../chapters/10-streaming-replication-and-high-availability.md) · [Course home](../../README.md)

## 0. Safety, prerequisites and topology

Use Windows PowerShell with Docker Desktop in Linux-container mode (or Docker Engine with equivalent commands). The following commands are **first-run-only** and create a new single-host primary and standby. They must not be used against any real or shared PostgreSQL instance.

Dedicated lab resource names:
- Network: `pg-ha10-net` (Docker internal bridge; no published database ports)
- Containers: `pg-ha10-primary` and `pg-ha10-standby`
- Volumes: `pg-ha10-primary-data` and `pg-ha10-standby-data`
- Database: `ha10_lab`, role: `ha10_repl`, slot: `ha10_standby_slot`

The two servers share one Docker host, so this lab **does not demonstrate independent HA, RPO/RTO, fencing or failover**. The plaintext passwords are disposable lab examples visible in command history and Docker metadata to administrators; never reuse them in real environments. **Credential exposure remains an open security limitation**: the hard-coded values and `docker run -e`/shell arguments are unsuitable for shared hosts. Use only an approved disposable local Docker context, do not publish terminal transcripts containing commands with secrets, and rotate/destroy these credentials with the isolated lab. Do not treat this lab as a secure-secret-management demonstration. Do not use customer data.

~~~powershell
docker version
docker info --format '{{.OSType}}'
docker pull postgres:17
docker ps -a --filter "name=pg-ha10-"
docker volume ls --filter "name=pg-ha10-"
docker network ls --filter "name=pg-ha10-"
~~~

**Expected:** Linux container mode, image available, and **no pre-existing resources** with these names. If any exist, stop and inspect them; do not overwrite or delete. Record the actual PostgreSQL minor version and Docker image digest; `postgres:17` is a moving tag. An image pull needs internet and local disk, but no cloud account.

## 0a. Fail-closed first-run preflight and provenance

Run this **before** Section 1 in a fresh PowerShell session. It checks the selected Docker context, Linux mode, the exact names (rather than prefix matches), and the local PostgreSQL 17 image ID. Stop if any check fails. Keep the output in a private, timestamped lab record; do not include credentials. These checks do **not** prove a Docker daemon is dedicated or that a pre-existing volume is safe to reuse: obtain approval for the selected disposable Docker context before continuing.

~~~powershell
$ErrorActionPreference = 'Stop'
$labContext = (docker context show)
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($labContext)) { throw 'Cannot establish Docker context' }
$osType = (docker info --format '{{.OSType}}')
if ($LASTEXITCODE -ne 0 -or $osType.Trim() -ne 'linux') { throw 'Docker Linux engine required' }
$imageId = (docker image inspect postgres:17 --format '{{.Id}}')
if ($LASTEXITCODE -ne 0 -or $imageId -notmatch '^sha256:[0-9a-f]{64}$') { throw 'Invalid postgres:17 image ID' }
foreach ($name in @('pg-ha10-primary','pg-ha10-standby')) {
  $existing = @(docker ps -a --format '{{.Names}}')
  if ($LASTEXITCODE -ne 0) { throw 'Container inventory failed' }
  if ($existing -contains $name) { throw "Existing container: $name" }
}
foreach ($name in @('pg-ha10-primary-data','pg-ha10-standby-data')) {
  $existing = @(docker volume ls --format '{{.Name}}')
  if ($LASTEXITCODE -ne 0) { throw 'Volume inventory failed' }
  if ($existing -contains $name) { throw "Existing volume: $name" }
}
$existing = @(docker network ls --format '{{.Name}}')
if ($LASTEXITCODE -ne 0) { throw 'Network inventory failed' }
if ($existing -contains 'pg-ha10-net') { throw 'Existing network: pg-ha10-net' }
"Preflight passed: $labContext $imageId"
~~~

## 1. Create isolated network and volumes

Run once after the approved preflight. Stop after any failed creation; do not reuse an existing resource.

~~~powershell
docker network create --internal --label training.track=pg-enterprise-ch10 pg-ha10-net
if ($LASTEXITCODE -ne 0) { throw 'Network creation failed' }
docker volume create --label training.track=pg-enterprise-ch10 pg-ha10-primary-data
if ($LASTEXITCODE -ne 0) { throw 'Primary volume creation failed' }
docker volume create --label training.track=pg-enterprise-ch10 pg-ha10-standby-data
if ($LASTEXITCODE -ne 0) { throw 'Standby volume creation failed' }
~~~

**Immediately after creation, before starting a container, capture provenance** in the private lab record:

~~~powershell
docker context show
docker image inspect postgres:17 --format '{{.Id}} {{json .RepoDigests}}'
docker network inspect pg-ha10-net --format '{{.Id}} {{json .Labels}} {{json .Containers}}'
docker volume inspect pg-ha10-primary-data pg-ha10-standby-data --format '{{.Name}} {{json .Labels}} {{.Mountpoint}}'
~~~

Confirm Docker context and image ID match Section 0a, both volumes are new, and the network has no consumers. **If any creation or inspection command fails, stop.** Never continue with an existing resource just because its name matches. Capture full container IDs and mounts/labels immediately after the corresponding Section 2 and Section 5 creation commands:

~~~powershell
docker inspect pg-ha10-primary --format '{{.Id}} {{json .Config.Labels}} {{json .Mounts}}'
# Run only after standby creation:
docker inspect pg-ha10-standby --format '{{.Id}} {{json .Config.Labels}} {{json .Mounts}}'
~~~

A Docker volume has a name rather than a portable immutable ID. Retain its creation record, driver, mountpoint, labels, and context. If creation-time evidence is missing, cleanup is blocked pending manual review. The internal network limits external routing but is not a production security boundary.

## 2. Start primary with WAL streaming settings

~~~powershell
docker run -d --label training.track=pg-enterprise-ch10 --name pg-ha10-primary --network pg-ha10-net -e POSTGRES_PASSWORD=TrainingOnly_HA10_123 -e POSTGRES_DB=ha10_lab -v pg-ha10-primary-data:/var/lib/postgresql/data postgres:17 -c wal_level=replica -c max_wal_senders=5 -c max_replication_slots=5 -c wal_keep_size=64MB -c max_slot_wal_keep_size=256MB
if ($LASTEXITCODE -ne 0) { throw 'Primary container creation failed; stop and inspect resource provenance' }

docker exec pg-ha10-primary pg_isready -U postgres -d ha10_lab
if ($LASTEXITCODE -ne 0) { throw 'Chapter 10 observation command failed; stop and inspect the named lab container' }
docker exec pg-ha10-primary psql -U postgres -d ha10_lab -c "SELECT version(), pg_is_in_recovery();"
if ($LASTEXITCODE -ne 0) { throw 'Chapter 10 observation command failed; stop and inspect the named lab container' }
docker exec pg-ha10-primary psql -U postgres -d ha10_lab -c "SHOW wal_level; SHOW max_wal_senders; SHOW max_replication_slots;"
if ($LASTEXITCODE -ne 0) { throw 'Chapter 10 observation command failed; stop and inspect the named lab container' }
~~~

Expected: primary ready, `pg_is_in_recovery() = false`, `wal_level = replica`. If not ready, allow initialization to finish and check logs. The retention cap is applied at checkpoints; it does **not** guarantee WAL disk cannot fill, and a lagging slot can eventually become unusable.

## 3. Create a dedicated replication role and HBA entry

~~~powershell
docker exec pg-ha10-primary psql -X -v ON_ERROR_STOP=1 -U postgres -d ha10_lab -c "CREATE ROLE ha10_repl WITH REPLICATION LOGIN PASSWORD 'TrainingOnly_Repl_HA10_123';"
if ($LASTEXITCODE -ne 0) { throw 'Replication role creation failed; stop' }
docker exec -u postgres pg-ha10-primary sh -c 'echo host replication ha10_repl all scram-sha-256 >> /var/lib/postgresql/data/pg_hba.conf && pg_ctl reload -D /var/lib/postgresql/data'
if ($LASTEXITCODE -ne 0) { throw 'HBA append/reload failed; stop and inspect without retrying append' }
docker exec pg-ha10-primary psql -X -v ON_ERROR_STOP=1 -U postgres -d ha10_lab -c "SELECT rolname, rolreplication, rolsuper FROM pg_roles WHERE rolname='ha10_repl';"
if ($LASTEXITCODE -ne 0) { throw 'Replication role observation failed; stop' }
docker exec pg-ha10-primary psql -X -v ON_ERROR_STOP=1 -U postgres -d ha10_lab -c "SELECT line_number, database, user_name, auth_method, error FROM pg_hba_file_rules WHERE 'ha10_repl'=ANY(user_name);"
if ($LASTEXITCODE -ne 0) { throw 'HBA rule observation failed; stop' }
~~~

**Configuration acceptance assertions (read-only):** The preceding formatted queries do not establish the expected values. Run these before the base backup, stopping on any mismatch.

~~~powershell
$roleRows = @(docker exec pg-ha10-primary psql -X -v ON_ERROR_STOP=1 -tA -U postgres -d ha10_lab -c "SELECT rolreplication::text || '|' || rolsuper::text || '|' || rolcanlogin::text FROM pg_roles WHERE rolname = 'ha10_repl';")
$roleExit = $LASTEXITCODE
if ($roleExit -ne 0 -or $roleRows.Count -ne 1 -or $roleRows[0].Trim() -cne 'true|false|true') {
  throw 'Replication role privileges do not match expected values; stop'
}
$hbaRows = @(docker exec pg-ha10-primary psql -X -v ON_ERROR_STOP=1 -tA -U postgres -d ha10_lab -c "SELECT count(*) FROM pg_hba_file_rules WHERE type = 'host' AND database = ARRAY['replication']::text[] AND user_name = ARRAY['ha10_repl']::text[] AND address = 'all' AND auth_method = 'scram-sha-256' AND error IS NULL;")
$hbaExit = $LASTEXITCODE
if ($hbaExit -ne 0 -or $hbaRows.Count -ne 1 -or $hbaRows[0].Trim() -cne '1') {
  throw 'Expected replication HBA rule not found exactly once; stop'
}
'PASS: replication role and HBA configuration asserted'
~~~

These checks are unexecuted static examples. The HBA address `all` is restricted to this disposable lab, not a production access policy.

Expected: role has replication permission but is not superuser; HBA rule uses SCRAM with no parse error. The HBA `all` address is only tolerable in this dedicated internal training network. Production requires scoped CIDRs, TLS, managed secrets, review and independent security controls. WAL can expose sensitive data.

## 4. Prepare empty standby volume and seed with pg_basebackup

The new named volume may initially be root-owned. Set ownership **only** on the confirmed empty lab standby volume:

~~~powershell
docker run --rm --user root -v pg-ha10-standby-data:/var/lib/postgresql/data postgres:17 sh -c 'chown postgres:postgres /var/lib/postgresql/data && chmod 700 /var/lib/postgresql/data'
if ($LASTEXITCODE -ne 0) { throw 'Standby volume permission initialization failed; stop' }
~~~

Seed standby using the physical replication protocol. The temporary `PGPASSWORD` is used for the base-backup process; the `passfile` connection option will be recorded by `-R` for later standby connections.

~~~powershell
docker run --rm --network pg-ha10-net --user postgres -e PGPASSWORD=TrainingOnly_Repl_HA10_123 -v pg-ha10-standby-data:/var/lib/postgresql/data postgres:17 pg_basebackup -d 'host=pg-ha10-primary port=5432 user=ha10_repl passfile=/var/lib/postgresql/data/.pgpass application_name=ha10_standby' -D /var/lib/postgresql/data -Fp -Xs -P -R -C -S ha10_standby_slot
$baseBackupExit = $LASTEXITCODE
if ($baseBackupExit -ne 0) { throw "pg_basebackup failed (exit $baseBackupExit); STOP: inspect slot and volume read-only; do not retry, start standby or clean up automatically" }
~~~

**Partial-failure stop gate:** Capture the actual `pg_basebackup` exit code before proceeding. If nonzero, **do not** rerun `-C`, start the standby, drop the slot, or delete the volume. Inspect only the dedicated primary's slot and the standby volume metadata, then document whether the slot exists and whether backup files were partially written. Reset is a separate owner-approved, identity-verified disposable-lab procedure; it is not an automatic recovery step.

~~~powershell
docker exec pg-ha10-primary psql -X -v ON_ERROR_STOP=1 -U postgres -d ha10_lab -c "SELECT slot_name, slot_type, active, wal_status FROM pg_replication_slots WHERE slot_name='ha10_standby_slot';"
if ($LASTEXITCODE -ne 0) { throw 'Replication slot observation failed; stop' }
docker volume inspect pg-ha10-standby-data --format '{{.Name}} {{.Mountpoint}} {{json .Labels}}'
if ($LASTEXITCODE -ne 0) { throw 'Standby volume metadata observation failed; stop' }
~~~

Do not print `.pgpass`, `primary_conninfo`, or credential-bearing container environment values into evidence.

Before creating the standby passfile, assert that the slot created by `pg_basebackup -C` is a physical, inactive slot. Do not delete or recreate a slot when this check fails.

~~~powershell
$slotRows = @(docker exec pg-ha10-primary psql -X -v ON_ERROR_STOP=1 -tA -U postgres -d ha10_lab -c "SELECT slot_type || '|' || active::text FROM pg_replication_slots WHERE slot_name = 'ha10_standby_slot';")
$slotExit = $LASTEXITCODE
if ($slotExit -ne 0 -or $slotRows.Count -ne 1 -or $slotRows[0].Trim() -cne 'physical|false') {
  throw 'Expected inactive physical slot not observed; stop and inspect read-only'
}
'PASS: inactive physical replication slot asserted'
~~~

After standby startup, the slot should become active; do not rerun this pre-start assertion then.

**Expected:** exit code 0; a physical slot named `ha10_standby_slot` exists on the primary; the standby data volume now contains `standby.signal` and generated `primary_conninfo`/`primary_slot_name` settings. Do not rerun: the slot and data directory already exist.

Create the standby's credential file with restricted permissions **inside the lab volume**:

~~~powershell
docker run --rm --user root -v pg-ha10-standby-data:/var/lib/postgresql/data postgres:17 sh -c 'echo pg-ha10-primary:5432:replication:ha10_repl:TrainingOnly_Repl_HA10_123 > /var/lib/postgresql/data/.pgpass && chown postgres:postgres /var/lib/postgresql/data/.pgpass && chmod 600 /var/lib/postgresql/data/.pgpass'
if ($LASTEXITCODE -ne 0) { throw 'Standby passfile creation/permissions failed; stop' }
# Record only metadata; never display passfile contents.
docker run --rm --user postgres -v pg-ha10-standby-data:/var/lib/postgresql/data postgres:17 sh -c 'test "$(stat -c %a /var/lib/postgresql/data/.pgpass)" = 600 && test "$(stat -c %u /var/lib/postgresql/data/.pgpass)" = "$(id -u)"'
if ($LASTEXITCODE -ne 0) { throw 'Standby passfile ownership/mode assertion failed; stop' }
~~~

Expected: exit code 0. Never commit the `.pgpass` file or any real secret. The password is intentionally static for a disposable demonstration only.

## 5. Start standby and verify primary/standby roles

~~~powershell
docker run -d --label training.track=pg-enterprise-ch10 --name pg-ha10-standby --network pg-ha10-net -v pg-ha10-standby-data:/var/lib/postgresql/data postgres:17
if ($LASTEXITCODE -ne 0) { throw 'Standby container creation failed; stop and inspect provenance' }
docker exec pg-ha10-standby pg_isready -U postgres -d ha10_lab
if ($LASTEXITCODE -ne 0) { throw 'Chapter 10 observation command failed; stop and inspect the named lab container' }
docker exec pg-ha10-primary psql -U postgres -d ha10_lab -c "SELECT pg_is_in_recovery() AS is_standby;"
if ($LASTEXITCODE -ne 0) { throw 'Chapter 10 observation command failed; stop and inspect the named lab container' }
docker exec pg-ha10-standby psql -U postgres -d ha10_lab -c "SELECT pg_is_in_recovery() AS is_standby;"
if ($LASTEXITCODE -ne 0) { throw 'Chapter 10 observation command failed; stop and inspect the named lab container' }
~~~

**Expected:** primary false, standby true. If the standby is not ready, inspect `docker logs --tail 80 pg-ha10-standby`, then recheck.

~~~powershell
docker exec pg-ha10-primary psql -U postgres -d ha10_lab -c "SELECT application_name, state, sync_state, sent_lsn, write_lsn, flush_lsn, replay_lsn FROM pg_stat_replication;"
if ($LASTEXITCODE -ne 0) { throw 'Chapter 10 observation command failed; stop and inspect the named lab container' }
docker exec pg-ha10-standby psql -U postgres -d ha10_lab -c "SELECT status, sender_host, slot_name, latest_end_lsn FROM pg_stat_wal_receiver;"
if ($LASTEXITCODE -ne 0) { throw 'Chapter 10 observation command failed; stop and inspect the named lab container' }
~~~

**Expected:** primary sees one `streaming` sender with `sync_state = async`; standby sees one `streaming` receiver with slot `ha10_standby_slot`. Allow brief connection startup time before retrying read-only queries.

### 5a. Assert roles and streaming state (bounded, read-only)

The preceding formatted queries are observations, not acceptance assertions. Run this in the same PowerShell session after both servers are ready. The exact-value checks reject empty output and unexpected roles; the 15-attempt window permits normal asynchronous startup without hiding a persistent failure. Do not promote or reinitialize either server to force a PASS.

~~~powershell
function Assert-Ha10Scalar([string]$container, [string]$sql, [string]$expected) {
  $lines = @(docker exec $container psql -X -v ON_ERROR_STOP=1 -tA -U postgres -d ha10_lab -c $sql)
  $exitCode = $LASTEXITCODE
  if ($exitCode -ne 0 -or $lines.Count -ne 1 -or $lines[0].Trim() -cne $expected) {
    throw "Chapter 10 assertion failed for $container (exit=$exitCode); expected $expected; inspect locally"
  }
}
Assert-Ha10Scalar 'pg-ha10-primary' 'SELECT pg_is_in_recovery();' 'f'
Assert-Ha10Scalar 'pg-ha10-standby' 'SELECT pg_is_in_recovery();' 't'
$streaming = $false
for ($attempt = 1; $attempt -le 15; $attempt++) {
  $sender = @(docker exec pg-ha10-primary psql -X -v ON_ERROR_STOP=1 -tA -U postgres -d ha10_lab -c "SELECT state || '|' || sync_state FROM pg_stat_replication WHERE application_name = 'ha10_standby';")
  $senderExit = $LASTEXITCODE
  $receiver = @(docker exec pg-ha10-standby psql -X -v ON_ERROR_STOP=1 -tA -U postgres -d ha10_lab -c "SELECT status || '|' || slot_name FROM pg_stat_wal_receiver;")
  $receiverExit = $LASTEXITCODE
  if ($senderExit -ne 0 -or $receiverExit -ne 0) { throw 'Replication state query failed; stop' }
  if ($sender.Count -eq 1 -and $sender[0].Trim() -ceq 'streaming|async' -and
      $receiver.Count -eq 1 -and $receiver[0].Trim() -ceq 'streaming|ha10_standby_slot') {
    $streaming = $true
    break
  }
  Start-Sleep -Seconds 2
}
if (-not $streaming) { throw 'Replication did not reach expected streaming state within 30 seconds' }
'PASS: primary/standby roles and asynchronous streaming state asserted'
~~~

**Expected:** exactly one sender for the lab application and exactly one receiver, with the expected state and slot. Record only sanitized scalar results and PASS/FAIL; this is not a failover, fencing, or RPO/RTO test. **Static review only:** PowerShell behavior and PostgreSQL output have not yet been executed in an isolated runtime.


## 6. Insert on primary, read on standby — bounded acceptance

Run this in the same PowerShell session as the approved preflight. Stop on every unexpected exit code. The marker is unique to this disposable lab, and the polling loop is bounded to 30 seconds. A timeout is a **failed acceptance check**, not a reason to promote the standby or recreate resources.

~~~powershell
docker exec pg-ha10-primary psql -X -v ON_ERROR_STOP=1 -U postgres -d ha10_lab -c "CREATE TABLE public.ha10_events (event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, note TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now());"
if ($LASTEXITCODE -ne 0) { throw 'Primary table creation failed; stop' }
docker exec pg-ha10-primary psql -X -v ON_ERROR_STOP=1 -U postgres -d ha10_lab -c "INSERT INTO public.ha10_events (note) VALUES ('synthetic replication check');"
if ($LASTEXITCODE -ne 0) { throw 'Primary insert failed; stop' }

$replayed = $false
for ($attempt = 1; $attempt -le 15; $attempt++) {
  # -tA emits only the boolean; a missing table returns a nonzero exit code.
  $result = @(docker exec pg-ha10-standby psql -X -v ON_ERROR_STOP=1 -tA -U postgres -d ha10_lab -c "SELECT count(*) = 1 FROM public.ha10_events WHERE note = 'synthetic replication check';")
  $code = $LASTEXITCODE
  if ($code -eq 0 -and $result.Count -eq 1 -and $result[0].Trim() -eq 't') { $replayed = $true; break }
  if ($code -ne 0) { Write-Warning "Standby query not ready on attempt $attempt; inspect replication health if persistent" }
  Start-Sleep -Seconds 2
}
if (-not $replayed) { throw 'Standby did not replay exact marker within bounded window; acceptance failed' }
'PASS: exact synthetic marker observed on standby'
~~~

**Expected:** a single row with the exact note appears on the standby within the bounded window. Because streaming is asynchronous, a missing table or row can be transient; repeated failures require read-only investigation of the sender, receiver and replay state. This acceptance test does not establish a production RPO/RTO.

## 7. Prove the standby rejects writes — assert expected SQLSTATE

This is an intentional error test. The SQLSTATE for a read-only SQL transaction is `25006`. Capture only sanitized error output; do not include connection strings, passwords, or environment dumps. A nonzero exit code **alone** is insufficient because authentication, connection or syntax errors could also cause failure.

~~~powershell
$writeOutput = @(docker exec pg-ha10-standby psql -X -v ON_ERROR_STOP=1 -v VERBOSITY=verbose -U postgres -d ha10_lab -c "INSERT INTO public.ha10_events (note) VALUES ('must not write on standby');" 2>&1 | ForEach-Object { $_.ToString() })
$writeExit = $LASTEXITCODE
if ($writeExit -eq 0) { throw 'FAIL: standby unexpectedly accepted a write' }
if (($writeOutput -join "`n") -notmatch '(?m)ERROR:\s+25006:') {
  throw 'FAIL: write failed for a reason other than verified SQLSTATE 25006; inspect locally and redact before recording'
}
'PASS: standby write rejected with SQLSTATE 25006'
~~~

The SQLSTATE matcher uses a single regex backslash in PowerShell's single-quoted string (`\s` denotes whitespace); a doubled backslash would incorrectly match a literal backslash.

**Expected:** nonzero `psql` exit status and verbose PostgreSQL error containing `ERROR:  25006:`. Verify the exact error locally before recording only the SQLSTATE and PASS/FAIL. Never promote or disable standby read-only protection to make this test pass.

## 8. Inspect WAL, lag and retention safely

Primary-side read-only queries:

~~~powershell
docker exec pg-ha10-primary psql -U postgres -d ha10_lab -c "SELECT application_name, state, sync_state, write_lag, flush_lag, replay_lag FROM pg_stat_replication;"
if ($LASTEXITCODE -ne 0) { throw 'Chapter 10 observation command failed; stop and inspect the named lab container' }
docker exec pg-ha10-primary psql -U postgres -d ha10_lab -c "SELECT slot_name, slot_type, active, restart_lsn, wal_status FROM pg_replication_slots;"
if ($LASTEXITCODE -ne 0) { throw 'Chapter 10 observation command failed; stop and inspect the named lab container' }
docker exec pg-ha10-primary psql -U postgres -d ha10_lab -c "SELECT pg_current_wal_lsn() AS primary_lsn;"
if ($LASTEXITCODE -ne 0) { throw 'Chapter 10 observation command failed; stop and inspect the named lab container' }
~~~

Standby-side read-only queries:

~~~powershell
docker exec pg-ha10-standby psql -U postgres -d ha10_lab -c "SELECT pg_last_wal_receive_lsn() AS received, pg_last_wal_replay_lsn() AS replayed, pg_last_xact_replay_timestamp() AS last_replayed_commit;"
if ($LASTEXITCODE -ne 0) { throw 'Chapter 10 observation command failed; stop and inspect the named lab container' }
docker exec pg-ha10-standby psql -U postgres -d ha10_lab -c "SELECT status, latest_end_lsn, last_msg_receipt_time FROM pg_stat_wal_receiver;"
if ($LASTEXITCODE -ne 0) { throw 'Chapter 10 observation command failed; stop and inspect the named lab container' }
~~~

Optional primary `psql` query to estimate the **WAL position gap**, not actual disk consumption:

~~~sql
SELECT slot_name, wal_status,
       pg_size_pretty(
         GREATEST(0, pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn))::bigint
       ) AS approximate_wal_position_gap
FROM pg_replication_slots
WHERE slot_name = 'ha10_standby_slot' AND restart_lsn IS NOT NULL;
~~~

**Expected:** sender and receiver connected, active slot, WAL positions updated after the insert. Time-based lag fields may be `NULL` when the standby is caught up and idle; a large `now() - pg_last_xact_replay_timestamp()` can also reflect a healthy idle system. Do not use either alone as RPO proof.

## 9. Troubleshooting and recovery

| Symptom | Investigate | Safe next step |
|---|---|---|
| Primary won't start | Image, Docker daemon, volume ownership | Read `docker logs --tail 80 pg-ha10-primary` |
| Base backup authentication fails | Role, `pg_hba.conf`, SCRAM, DNS | Inspect `pg_hba_file_rules` and logs without sharing secrets |
| Base backup reports slot exists | Previous partial/complete run | Inspect `pg_replication_slots`; do not drop a potentially active slot |
| Standby cannot authenticate | `.pgpass` owner/mode, `primary_conninfo`, password | Inspect standby logs and file metadata; redact credentials |
| Standby not streaming | Network, sender capacity, slot, WAL availability | Read sender/receiver and slot views |
| Standby query misses table | WAL not yet replayed | Wait and retry SELECT, inspect replay position |
| Standby write fails | Expected read-only protection | Record the rejection; do not promote |
| WAL volume grows | Inactive slot, archiver backlog, write load | Monitor slot `wal_status` and disk; escalate before exhaustion |

Never "repair" the topology by skipping WAL consistency checks, deleting active slots, or promoting a standby.

## 10. Acceptance and evidence

- [ ] Record Docker environment, actual PostgreSQL minor version and image digest.
- [ ] Confirm dedicated network and volumes were new.
- [ ] Confirm primary `pg_is_in_recovery() = false` and standby `true`.
- [ ] Confirm sender and receiver are streaming, with async mode.
- [ ] Confirm slot is active and `wal_status` inspected.
- [ ] Observe synthetic primary insert on standby.
- [ ] Observe standby write rejection.
- [ ] Record read-only lag/LSN diagnostics and sanitized logs.
- [ ] State that no independent fencing, promotion, RPO/RTO measurement or failover test occurred.
- [ ] Obtain independent reviewer sign-off **only after** actual execution.

**Expected outputs are not execution evidence.** This document is authored, not runtime-verified or production-certified.

## 11. Optional cleanup — destructive, never automatic

Only an authorized lab owner may remove these resources, and only after recording the **full container IDs, volume names/IDs, network ID, Docker context, labels and mount/consumer inventory at creation time**. The resource names alone are insufficient proof of ownership. These commands permanently destroy lab data; never use them on production or shared resources. **If creation-time identity evidence is missing, stop: do not perform cleanup.** Do not remove resources still used by another container.

First inspect without changing anything:

~~~powershell
docker context show
docker inspect pg-ha10-primary pg-ha10-standby --format '{{.Id}} {{json .Config.Labels}} {{json .Mounts}} {{json .NetworkSettings.Networks}}'
docker volume inspect pg-ha10-primary-data pg-ha10-standby-data
docker network inspect pg-ha10-net
docker ps -a --filter volume=pg-ha10-primary-data
docker ps -a --filter volume=pg-ha10-standby-data
docker ps -a --filter network=pg-ha10-net
~~~

Compare the current Docker context and **full** container IDs against the saved creation records; verify each resource has `training.track=pg-enterprise-ch10`, that the mounts match the expected lab volumes, and that no unexpected containers use either volume or the network. The lab owner must explicitly approve deletion and confirm there is no retention requirement. **Stop if any check fails, an unexpected consumer appears, or ownership is ambiguous.** Labels can be spoofed and do not replace ID/provenance checks.

Only after all checks pass, manually execute the following **one command at a time**, inspecting exit codes. Do not add `--force`, `-v`, or automated name-based deletion:

~~~powershell
docker stop pg-ha10-standby pg-ha10-primary
docker rm pg-ha10-standby pg-ha10-primary
docker volume rm pg-ha10-standby-data pg-ha10-primary-data
docker network rm pg-ha10-net
~~~

Record post-cleanup absence using `docker ps -a`, `docker volume ls` and `docker network ls` with exact-name comparisons, plus sanitized output and timestamps. A failed removal is **not** proof of cleanup; investigate without deleting other resources.

No cleanup is required to pass the lab.

## Official PostgreSQL 18 references (documentation only; lab still targets PostgreSQL 17)

- [Streaming replication and standby setup](https://www.postgresql.org/docs/18/warm-standby.html)
- [pg_basebackup](https://www.postgresql.org/docs/18/app-pgbasebackup.html)
- [Replication configuration](https://www.postgresql.org/docs/18/runtime-config-replication.html)
- [Statistics and replication views](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [Replication slot view](https://www.postgresql.org/docs/18/view-pg-replication-slots.html)
