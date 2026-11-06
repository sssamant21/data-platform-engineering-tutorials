# Chapter 11 Lab — Physical Backup Verification and Named-Point PITR

**Platform:** Windows PowerShell with Docker Desktop (Linux containers) or equivalent Docker Engine  
**Reference:** PostgreSQL 17 (official `postgres:17` image) · **Guided lab:** ~23 minutes plus image-pull/recovery time  
**Status:** Authored, NOT executed or independently reviewed

[Chapter 11](../../chapters/11-backup-restore-pitr-and-disaster-recovery.md) · [Course home](../../README.md)

## 0. Safety and prerequisite checks

This lab uses a **single local Docker host** and synthetic data. It is not enterprise DR, high availability, a production backup procedure, or evidence of achieved RPO/RTO. Never use customer data or production credentials.

Dedicated, first-run-only resources: containers `pg-ch11-primary` and `pg-ch11-restore`; volumes `pg-ch11-primary-data`, `pg-ch11-archive`, `pg-ch11-base` and `pg-ch11-restore-data`; database `pitr_lab`; restore point `ch11_safe_point`.

~~~powershell
docker version
docker info --format '{{.OSType}}'
docker ps -a --filter "name=pg-ch11-"
docker volume ls --filter "name=pg-ch11-"
docker pull postgres:17
docker image inspect postgres:17 --format '{{index .RepoDigests 0}}'
~~~

**Expected:** Docker Linux mode, PostgreSQL 17 image, and **no** existing matching containers/volumes. If any exist, stop and inspect; do not overwrite or delete them. Image pull needs internet and local disk but no cloud account.

## 1. Create four isolated volumes and set permissions

~~~powershell
$labLabel = 'org.postgresql.dbre.training=chapter-11'
$dockerContext = (docker context show).Trim()
if ($LASTEXITCODE -ne 0 -or -not $dockerContext) { throw 'Cannot establish Docker context; stop.' }
docker volume create --label $labLabel pg-ch11-primary-data
docker volume create --label $labLabel pg-ch11-archive
docker volume create --label $labLabel pg-ch11-base
docker volume create --label $labLabel pg-ch11-restore-data
if ($LASTEXITCODE -ne 0) { throw 'Volume creation failed; stop and inspect.' }
$volumeIds = @{}
foreach ($v in @('pg-ch11-primary-data','pg-ch11-archive','pg-ch11-base','pg-ch11-restore-data')) {
    $volumeIds[$v] = (docker volume inspect $v --format '{{.Name}}').Trim()
    if ($LASTEXITCODE -ne 0 -or $volumeIds[$v] -ne $v) { throw "Volume identity mismatch: $v" }
}
# Retain the context and names in the sanitized run record. Do not reuse prior-run identities.

docker run --rm --user root -v pg-ch11-archive:/wal-archive -v pg-ch11-base:/backup -v pg-ch11-restore-data:/restore-data postgres:17 sh -c 'chown postgres:postgres /wal-archive /backup /restore-data && chmod 700 /wal-archive /backup /restore-data'
~~~

Expected: four new volumes; helper exits 0. Ownership changes are safe only for these confirmed disposable volumes.

## 2. Start the source with a local WAL archive

~~~powershell
docker run -d --label org.postgresql.dbre.training=chapter-11 --name pg-ch11-primary -e POSTGRES_PASSWORD=TrainingOnly_PITR11_123 -e POSTGRES_DB=pitr_lab -v pg-ch11-primary-data:/var/lib/postgresql/data -v pg-ch11-archive:/wal-archive -v pg-ch11-base:/backup postgres:17 -c wal_level=replica -c archive_mode=on -c "archive_command=test ! -f /wal-archive/%f && cp %p /wal-archive/%f" -c archive_timeout=60s

$primaryId = (docker inspect pg-ch11-primary --format '{{.Id}}').Trim()
if ($LASTEXITCODE -ne 0 -or $primaryId.Length -ne 64) { throw 'Primary container identity missing; stop.' }
docker exec pg-ch11-primary pg_isready -U postgres -d pitr_lab
docker exec pg-ch11-primary psql -U postgres -d pitr_lab -c "SELECT version(), pg_is_in_recovery();"
docker exec pg-ch11-primary psql -U postgres -d pitr_lab -c "SHOW archive_mode; SHOW wal_level; SHOW archive_command;"
docker logs --tail 30 pg-ch11-primary
~~~

Expected: PostgreSQL 17 accepts connections; recovery is false; archive_mode is on and wal_level is replica. Wait for initialization if necessary; inspect logs before proceeding. No ports are published. The plaintext demo password is for this disposable local exercise only.

The local `archive_command` is **not production-ready**. Real archives require protected off-host durable storage, integrity controls, robust retry/idempotency and monitoring.

## 3. Create synthetic baseline data

~~~powershell
docker exec pg-ch11-primary psql -U postgres -d pitr_lab -v ON_ERROR_STOP=1 -c "CREATE TABLE public.pitr_events (event_id INTEGER PRIMARY KEY, note TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp());"
docker exec pg-ch11-primary psql -U postgres -d pitr_lab -v ON_ERROR_STOP=1 -c "INSERT INTO public.pitr_events (event_id, note) VALUES (1, 'baseline');"
docker exec pg-ch11-primary psql -U postgres -d pitr_lab -c "SELECT event_id, note FROM public.pitr_events ORDER BY event_id;"
~~~

Expected: one row, `(1, baseline)`. Confirm successful command exit codes before continuing.

## 4. Take a physical base backup and verify its manifest

The official disposable image permits local socket access to PostgreSQL. Production should instead use scoped replication identities, secret management and approved network/TLS controls.

~~~powershell
docker exec -u postgres pg-ch11-primary pg_basebackup -h /var/run/postgresql -U postgres -D /backup/base -Fp -Xs -P -c fast
docker exec -u postgres pg-ch11-primary pg_verifybackup /backup/base
docker exec pg-ch11-primary sh -c 'test -f /backup/base/backup_manifest && echo manifest-present'
~~~

Expected: backup and verification both exit 0, followed by `manifest-present`. The `-Xs` option includes streamed WAL needed for the backup. A passing `pg_verifybackup` checks the manifest/files/required WAL but does not prove application recovery.

**Stop on failure.** Never rerun a base backup into an existing nonempty directory. Investigate, then use a new empty disposable backup volume if needed.

## 5. Commit data AFTER the base backup

~~~powershell
docker exec pg-ch11-primary psql -U postgres -d pitr_lab -v ON_ERROR_STOP=1 -c "INSERT INTO public.pitr_events (event_id, note) VALUES (2, 'safe_before_point');"
docker exec pg-ch11-primary psql -U postgres -d pitr_lab -c "SELECT event_id, note FROM public.pitr_events ORDER BY event_id;"
~~~

Expected: rows 1 and 2. Row 2 can only be recovered from WAL because it was committed after the physical base backup.

## 6. Record a named recovery point and simulate an error

Create the named restore point **exactly once**. Record the WAL segment that contains it:

~~~powershell
$targetWal = (docker exec pg-ch11-primary psql -U postgres -d pitr_lab -At -v ON_ERROR_STOP=1 -c "SELECT pg_walfile_name(pg_create_restore_point('ch11_safe_point'));").Trim()
$targetWal
~~~

Expected: a nonempty WAL segment name (normally 24 hexadecimal characters). If the command fails or returns blank, stop.

Make the intentionally incorrect changes AFTER the restore point:

~~~powershell
docker exec pg-ch11-primary psql -U postgres -d pitr_lab -v ON_ERROR_STOP=1 -c "UPDATE public.pitr_events SET note = 'incorrect_change' WHERE event_id = 1;"
docker exec pg-ch11-primary psql -U postgres -d pitr_lab -v ON_ERROR_STOP=1 -c "INSERT INTO public.pitr_events (event_id, note) VALUES (3, 'after_target');"
docker exec pg-ch11-primary psql -U postgres -d pitr_lab -c "SELECT event_id, note FROM public.pitr_events ORDER BY event_id;"
~~~

Expected source rows:

~~~text
1 | incorrect_change
2 | safe_before_point
3 | after_target
~~~

## 7. Archive the WAL and verify the target segment exists

~~~powershell
docker exec pg-ch11-primary psql -U postgres -d pitr_lab -c "SELECT pg_switch_wal();"
docker exec pg-ch11-primary psql -U postgres -d pitr_lab -c "SELECT archived_count, last_archived_wal, last_archived_time, failed_count, last_failed_wal FROM pg_stat_archiver;"
~~~

A WAL segment is archived after completion; `pg_switch_wal()` forces a switch on this lab source. Poll for the specific target segment:

~~~powershell
$archived = $false
for ($i = 0; $i -lt 30; $i++) {
    docker exec pg-ch11-primary test -f "/wal-archive/$targetWal"
    if ($LASTEXITCODE -eq 0) {
        $archived = $true
        break
    }
    Start-Sleep -Seconds 2
}
if (-not $archived) {
    throw "Required target WAL segment is not archived. Stop and investigate."
}
Write-Output "Target WAL segment archived: $targetWal"
~~~

Expected: target WAL segment exists. This is an archive-presence check, not a full continuity or durability audit. If it fails, inspect archive logs, permissions and disk; **never** manually remove or invent WAL files.

## 8. Stop the source BEFORE creating a new writable copy

~~~powershell
docker stop pg-ch11-primary
# Require an exact stopped source before any writable restore is started.
$sourceState = (docker inspect --format '{{.State.Running}}' pg-ch11-primary).Trim()
if ($LASTEXITCODE -ne 0 -or $sourceState -ne "false") { throw "Source is not confirmed stopped; abort restore." }
docker ps -a --filter "name=pg-ch11-"
~~~

Expected: source stopped. **Do not restart it while the restored copy is writable.** This avoids two active writers in the teaching topology; production requires independently verified fencing and routing controls.

## 9. Restore the base backup to a separate, empty volume

~~~powershell
docker run --rm --user root -v pg-ch11-base:/backup:ro -v pg-ch11-restore-data:/restore-data postgres:17 sh -c 'cp -a /backup/base/. /restore-data/ && touch /restore-data/recovery.signal && chown -R postgres:postgres /restore-data && chmod 700 /restore-data'
~~~

Expected: exit 0. The restore volume contains `PG_VERSION` and `recovery.signal`. Do not rerun this copy over a nonempty restore volume or modify the source data volume.

## 10. Start PITR to the named recovery point

Mount the WAL archive read-only. Recovery is configured to stop at `ch11_safe_point` and promote the restored instance; the original source stays stopped.

~~~powershell
$restoreStart = Get-Date
docker run -d --label org.postgresql.dbre.training=chapter-11 --name pg-ch11-restore -v pg-ch11-restore-data:/var/lib/postgresql/data -v pg-ch11-archive:/wal-archive:ro postgres:17 -c archive_mode=off -c "restore_command=cp /wal-archive/%f %p" -c recovery_target_name=ch11_safe_point -c recovery_target_action=promote

$restoreId = (docker inspect pg-ch11-restore --format '{{.Id}}').Trim()
if ($LASTEXITCODE -ne 0 -or $restoreId.Length -ne 64) { throw 'Restore container identity missing; stop.' }
docker logs --tail 80 pg-ch11-restore
docker exec pg-ch11-restore pg_isready -U postgres -d pitr_lab
~~~

If not ready, wait briefly and retry `pg_isready` while inspecting logs. Do not recreate or overwrite the container. After recovery completes, run:

~~~powershell
docker exec pg-ch11-restore psql -U postgres -d pitr_lab -v ON_ERROR_STOP=1 -c "SELECT pg_is_in_recovery() AS still_recovering;"
docker exec pg-ch11-restore psql -U postgres -d pitr_lab -v ON_ERROR_STOP=1 -c "SELECT event_id, note FROM public.pitr_events ORDER BY event_id;"
docker exec pg-ch11-restore psql -U postgres -d pitr_lab -v ON_ERROR_STOP=1 -c "SELECT count(*) AS recovered_rows FROM public.pitr_events;"

$restoreEnd = Get-Date
$elapsed = ($restoreEnd - $restoreStart).TotalSeconds
"Restored-container-start-to-verified-query seconds: {0:N1}" -f $elapsed
~~~

**Expected:** `still_recovering = false`, exactly two rows `(1, baseline)` and `(2, safe_before_point)`, count 2. The post-target incorrect update and row 3 must be absent. If they appear, **fail the lab** and inspect the recovery logs/target; do not claim success.

The measured interval covers only restored-container startup and the queries after `$restoreStart` (the base-backup copy in step 9 is excluded); it is **not** the complete restore duration or an end-to-end RTO. The intentional omission of post-target writes is not measured disaster RPO.

## 11. Recovery evidence and enterprise acceptance boundary

Retain sanitized evidence for:
- image digest, PostgreSQL version, source/restore identity and timestamps;
- backup command and `pg_verifybackup` exit status;
- restore point name, target WAL segment, archive health and source-stop evidence;
- recovery logs, restored row values, counts and elapsed seconds;
- any failed commands, root cause and corrective action.

A real DR test additionally needs a declared failure event, last business-acknowledged write, independent backup site, application validation, routing/fencing, and measured data loss and restoration times against **business-approved RPO/RTO**. A same-host Docker PITR exercise cannot certify these.

## 12. Troubleshooting

| Symptom | Inspect | Safe response |
|---|---|---|
| Docker initialization fails | Container logs, disk and volume permissions | Stop; verify disposable resource identity |
| `pg_basebackup` fails | Socket auth, disk, backup directory | Do not continue to recovery |
| `pg_verifybackup` fails | Manifest, missing files, WAL | Reject this backup |
| Target WAL missing | `pg_stat_archiver`, permissions, logs | Wait/investigate; do not delete WAL |
| Recovery says WAL missing | Archive chain, timeline and source identity | Stop; do not fabricate segments |
| Restore point not reached | Target spelling and archived WAL coverage | Treat as failed recovery |
| Unexpected rows | Target semantics or wrong restore instance | Fail acceptance and investigate |
| Two writable copies | Source restarted | Stop client writes and assess fencing/routing |

## 13. Optional manual cleanup — destructive to lab volumes

First retain sanitized evidence. Cleanup is **optional** and must run in the same PowerShell session that captured `$dockerContext`, `$primaryId`, `$restoreId`, and `$volumeIds`. If that session or any identifier is lost, **stop and perform a separate manual provenance review**; never reconstruct ownership from names alone. Do not run against real database storage.

~~~powershell
if ((docker context show).Trim() -ne $dockerContext -or $LASTEXITCODE -ne 0) { throw 'Docker context changed; abort cleanup.' }
$expected = @{ 'pg-ch11-primary' = $primaryId; 'pg-ch11-restore' = $restoreId }
foreach ($name in $expected.Keys) {
    if (-not $expected[$name] -or $expected[$name].Length -ne 64) { throw "Missing original ID: $name" }
    $actual = (docker inspect $name --format '{{.Id}}').Trim()
    if ($LASTEXITCODE -ne 0 -or $actual -ne $expected[$name]) { throw "Container ID mismatch: $name" }
    $label = (docker inspect $name --format '{{index .Config.Labels "org.postgresql.dbre.training"}}').Trim()
    if ($LASTEXITCODE -ne 0 -or $label -ne 'chapter-11') { throw "Ownership label mismatch: $name" }
    docker inspect $name --format '{{json .Mounts}}'
    if ($LASTEXITCODE -ne 0) { throw "Cannot inspect mounts: $name" }
}
foreach ($name in $volumeIds.Keys) {
    if ($volumeIds[$name] -ne $name) { throw "Missing original volume identity: $name" }
    $label = (docker volume inspect $name --format '{{index .Labels "org.postgresql.dbre.training"}}').Trim()
    if ($LASTEXITCODE -ne 0 -or $label -ne 'chapter-11') { throw "Volume ownership mismatch: $name" }
    $users = @(docker ps -a --filter "volume=$name" --format '{{.ID}}')
    if ($LASTEXITCODE -ne 0) { throw "Cannot inspect volume consumers: $name" }
    foreach ($id in $users) {
        if ($id -and -not (@($primaryId, $restoreId) | Where-Object { $_.StartsWith($id) })) {
            throw "Unexpected container uses volume $name; abort cleanup."
        }
    }
}
# Review the mount JSON above: only the four chapter-11 volumes at the documented paths are permitted.
# If any unexpected bind mount, volume, or container appears, STOP; do not run the commands below.
docker stop pg-ch11-restore
if ($LASTEXITCODE -ne 0) { throw 'Stop failed; abort cleanup.' }
docker rm pg-ch11-restore
if ($LASTEXITCODE -ne 0) { throw 'Restore removal failed; abort cleanup.' }
docker stop pg-ch11-primary
# The source is normally already stopped. A nonzero stop status is acceptable only after inspecting State.Running=false.
$running = (docker inspect pg-ch11-primary --format '{{.State.Running}}').Trim()
if ($LASTEXITCODE -ne 0 -or $running -ne 'false') { throw 'Source not confirmed stopped; abort cleanup.' }
docker rm pg-ch11-primary
if ($LASTEXITCODE -ne 0) { throw 'Source removal failed; abort volume cleanup.' }
foreach ($name in @('pg-ch11-restore-data','pg-ch11-base','pg-ch11-archive','pg-ch11-primary-data')) {
    docker volume rm $name
    if ($LASTEXITCODE -ne 0) { throw "Volume removal failed: $name" }
}
foreach ($name in $expected.Keys) {
    docker inspect $name *> $null
    if ($LASTEXITCODE -eq 0) { throw "Container still exists: $name" }
}
foreach ($name in $volumeIds.Keys) {
    docker volume inspect $name *> $null
    if ($LASTEXITCODE -eq 0) { throw "Volume still exists: $name" }
}
~~~

The helper containers used for permissions and file copy are ephemeral (`--rm`), but verify that none remain and that no unexpected volume consumers exist. Never use broad cleanup commands such as `docker volume prune`. Record sanitized inspection and post-cleanup results; this is an **unexecuted procedure** until independently tested.

## 14. Acceptance checklist

- [ ] No conflicting resources at preflight.
- [ ] PostgreSQL version and image digest recorded.
- [ ] Base backup and `pg_verifybackup` passed in a real execution.
- [ ] Row 2 committed after backup and before restore point.
- [ ] Target WAL segment archived.
- [ ] Source stopped before restored copy became writable.
- [ ] Named PITR completed and recovered rows 1 and 2 only.
- [ ] Restored-container startup-to-query elapsed seconds recorded and correctly labeled; base-copy time excluded.
- [ ] Actual evidence retained and independently reviewed.
- [ ] No enterprise RPO/RTO or production certification claimed.

**Publication status:** instructions are authored; checkboxes remain unverified until actual execution.

## 15. Official documentation

- [PostgreSQL 18 — Continuous Archiving and PITR](https://www.postgresql.org/docs/18/continuous-archiving.html)
- [PostgreSQL 18 — pg_basebackup](https://www.postgresql.org/docs/18/app-pgbasebackup.html)
- [PostgreSQL 18 — pg_verifybackup](https://www.postgresql.org/docs/18/app-pgverifybackup.html)
- [PostgreSQL 18 — Recovery Target Settings](https://www.postgresql.org/docs/18/runtime-config-wal.html#RUNTIME-CONFIG-WAL-RECOVERY-TARGET)
