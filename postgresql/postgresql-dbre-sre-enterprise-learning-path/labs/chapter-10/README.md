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

The two servers share one Docker host, so this lab **does not demonstrate independent HA, RPO/RTO, fencing or failover**. The plaintext passwords are disposable lab examples visible to Docker administrators; never reuse them in real environments. Do not use customer data.

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
if ($LASTEXITCODE -ne 0 -or $imageId -notmatch '^sha256:[0-9a-f]{64}

~~~powershell
docker network create --internal --label training.track=pg-enterprise-ch10 pg-ha10-net
docker volume create --label training.track=pg-enterprise-ch10 pg-ha10-primary-data
docker volume create --label training.track=pg-enterprise-ch10 pg-ha10-standby-data
~~~

**Immediately after creation, before starting a container, capture provenance** in the private lab record:

~~~powershell
docker context show
docker image inspect postgres:17 --format '{{.Id}} {{json .RepoDigests}}'
docker network inspect pg-ha10-net --format '{{.Id}} {{json .Labels}} {{json .Containers}}'
docker volume inspect pg-ha10-primary-data pg-ha10-standby-data --format '{{.Name}} {{json .Labels}} {{.Mountpoint}}'
~~~

Confirm that the Docker context and image ID match Section 0a, both volumes are newly created, and the network has no consumers. **If any creation or inspection command fails, stop.** Never continue with an existing resource just because its name matches. Capture the **full** primary container ID and its mounts/labels immediately after the Section 2 `docker run`, and the full standby container ID immediately after Section 5 `docker run`:

~~~powershell
docker inspect pg-ha10-primary --format '{{.Id}} {{json .Config.Labels}} {{json .Mounts}}'
# Run the following only after the standby is created in Section 5:
docker inspect pg-ha10-standby --format '{{.Id}} {{json .Config.Labels}} {{json .Mounts}}'
~~~

A Docker volume has a name rather than a portable immutable volume ID; retain its creation record, driver, mountpoint, labels, and context. Never treat a later same-name volume as the original. If any identity or creation-time evidence is missing, cleanup is blocked pending manual review.

Expected: network and volumes created. The internal network prevents normal external routing for the lab containers. It is not a production network security control.

## 2. Start primary with WAL streaming settings

~~~powershell
docker run -d --label training.track=pg-enterprise-ch10 --name pg-ha10-primary --network pg-ha10-net -e POSTGRES_PASSWORD=TrainingOnly_HA10_123 -e POSTGRES_DB=ha10_lab -v pg-ha10-primary-data:/var/lib/postgresql/data postgres:17 -c wal_level=replica -c max_wal_senders=5 -c max_replication_slots=5 -c wal_keep_size=64MB -c max_slot_wal_keep_size=256MB

docker exec pg-ha10-primary pg_isready -U postgres -d ha10_lab
docker exec pg-ha10-primary psql -U postgres -d ha10_lab -c "SELECT version(), pg_is_in_recovery();"
docker exec pg-ha10-primary psql -U postgres -d ha10_lab -c "SHOW wal_level; SHOW max_wal_senders; SHOW max_replication_slots;"
~~~

Expected: primary ready, `pg_is_in_recovery() = false`, `wal_level = replica`. If not ready, allow initialization to finish and check logs. The retention cap is applied at checkpoints; it does **not** guarantee WAL disk cannot fill, and a lagging slot can eventually become unusable.

## 3. Create a dedicated replication role and HBA entry

~~~powershell
docker exec pg-ha10-primary psql -U postgres -d ha10_lab -c "CREATE ROLE ha10_repl WITH REPLICATION LOGIN PASSWORD 'TrainingOnly_Repl_HA10_123';"
docker exec -u postgres pg-ha10-primary sh -c 'echo host replication ha10_repl all scram-sha-256 >> /var/lib/postgresql/data/pg_hba.conf && pg_ctl reload -D /var/lib/postgresql/data'
docker exec pg-ha10-primary psql -U postgres -d ha10_lab -c "SELECT rolname, rolreplication, rolsuper FROM pg_roles WHERE rolname='ha10_repl';"
docker exec pg-ha10-primary psql -U postgres -d ha10_lab -c "SELECT line_number, database, user_name, auth_method, error FROM pg_hba_file_rules WHERE 'ha10_repl'=ANY(user_name);"
~~~

Expected: role has replication permission but is not superuser; HBA rule uses SCRAM with no parse error. The HBA `all` address is only tolerable in this dedicated internal training network. Production requires scoped CIDRs, TLS, managed secrets, review and independent security controls. WAL can expose sensitive data.

## 4. Prepare empty standby volume and seed with pg_basebackup

The new named volume may initially be root-owned. Set ownership **only** on the confirmed empty lab standby volume:

~~~powershell
docker run --rm --user root -v pg-ha10-standby-data:/var/lib/postgresql/data postgres:17 sh -c 'chown postgres:postgres /var/lib/postgresql/data && chmod 700 /var/lib/postgresql/data'
~~~

Seed standby using the physical replication protocol. The temporary `PGPASSWORD` is used for the base-backup process; the `passfile` connection option will be recorded by `-R` for later standby connections.

~~~powershell
docker run --rm --network pg-ha10-net --user postgres -e PGPASSWORD=TrainingOnly_Repl_HA10_123 -v pg-ha10-standby-data:/var/lib/postgresql/data postgres:17 pg_basebackup -d 'host=pg-ha10-primary port=5432 user=ha10_repl passfile=/var/lib/postgresql/data/.pgpass application_name=ha10_standby' -D /var/lib/postgresql/data -Fp -Xs -P -R -C -S ha10_standby_slot
~~~

**Partial-failure stop gate:** Capture the actual `pg_basebackup` exit code before proceeding. If nonzero, **do not** rerun `-C`, start the standby, drop the slot, or delete the volume. Inspect only the dedicated primary's slot and the standby volume metadata, then document whether the slot exists and whether backup files were partially written. Reset is a separate owner-approved, identity-verified disposable-lab procedure; it is not an automatic recovery step.

~~~powershell
docker exec pg-ha10-primary psql -X -v ON_ERROR_STOP=1 -U postgres -d ha10_lab -c "SELECT slot_name, slot_type, active, wal_status FROM pg_replication_slots WHERE slot_name='ha10_standby_slot';"
docker volume inspect pg-ha10-standby-data --format '{{.Name}} {{.Mountpoint}} {{json .Labels}}'
~~~

Do not print `.pgpass`, `primary_conninfo`, or credential-bearing container environment values into evidence.

**Expected:** exit code 0; a physical slot named `ha10_standby_slot` exists on the primary; the standby data volume now contains `standby.signal` and generated `primary_conninfo`/`primary_slot_name` settings. Do not rerun: the slot and data directory already exist.

Create the standby's credential file with restricted permissions **inside the lab volume**:

~~~powershell
docker run --rm --user root -v pg-ha10-standby-data:/var/lib/postgresql/data postgres:17 sh -c 'echo pg-ha10-primary:5432:replication:ha10_repl:TrainingOnly_Repl_HA10_123 > /var/lib/postgresql/data/.pgpass && chown postgres:postgres /var/lib/postgresql/data/.pgpass && chmod 600 /var/lib/postgresql/data/.pgpass'
~~~

Expected: exit code 0. Never commit the `.pgpass` file or any real secret. The password is intentionally static for a disposable demonstration only.

## 5. Start standby and verify primary/standby roles

~~~powershell
docker run -d --label training.track=pg-enterprise-ch10 --name pg-ha10-standby --network pg-ha10-net -v pg-ha10-standby-data:/var/lib/postgresql/data postgres:17
docker exec pg-ha10-standby pg_isready -U postgres -d ha10_lab
docker exec pg-ha10-primary psql -U postgres -d ha10_lab -c "SELECT pg_is_in_recovery() AS is_standby;"
docker exec pg-ha10-standby psql -U postgres -d ha10_lab -c "SELECT pg_is_in_recovery() AS is_standby;"
~~~

**Expected:** primary false, standby true. If the standby is not ready, inspect `docker logs --tail 80 pg-ha10-standby`, then recheck.

~~~powershell
docker exec pg-ha10-primary psql -U postgres -d ha10_lab -c "SELECT application_name, state, sync_state, sent_lsn, write_lsn, flush_lsn, replay_lsn FROM pg_stat_replication;"
docker exec pg-ha10-standby psql -U postgres -d ha10_lab -c "SELECT status, sender_host, slot_name, latest_end_lsn FROM pg_stat_wal_receiver;"
~~~

**Expected:** primary sees one `streaming` sender with `sync_state = async`; standby sees one `streaming` receiver with slot `ha10_standby_slot`. Allow brief connection startup time before retrying read-only queries.

## 6. Insert on primary, read on standby

~~~powershell
docker exec pg-ha10-primary psql -U postgres -d ha10_lab -c "CREATE TABLE public.ha10_events (event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, note TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now());"
docker exec pg-ha10-primary psql -U postgres -d ha10_lab -c "INSERT INTO public.ha10_events (note) VALUES ('synthetic replication check');"
docker exec pg-ha10-standby psql -U postgres -d ha10_lab -c "SELECT event_id, note FROM public.ha10_events ORDER BY event_id;"
~~~

**Expected:** one replicated row with note `synthetic replication check`. Because replication is asynchronous, the standby query can initially fail with "relation does not exist" or show no row. Wait briefly and retry the **SELECT only**, checking receiver/replay health if necessary.

## 7. Prove the standby rejects writes (intentional failure)

This is an expected-error test, **not** a command to put in an all-success script:

~~~powershell
docker exec pg-ha10-standby psql -U postgres -d ha10_lab -c "INSERT INTO public.ha10_events (note) VALUES ('must not write on standby');"
~~~

**Expected:** read-only/recovery error and a nonzero exit code. Do not promote or bypass read-only safeguards.

## 8. Inspect WAL, lag and retention safely

Primary-side read-only queries:

~~~powershell
docker exec pg-ha10-primary psql -U postgres -d ha10_lab -c "SELECT application_name, state, sync_state, write_lag, flush_lag, replay_lag FROM pg_stat_replication;"
docker exec pg-ha10-primary psql -U postgres -d ha10_lab -c "SELECT slot_name, slot_type, active, restart_lsn, wal_status FROM pg_replication_slots;"
docker exec pg-ha10-primary psql -U postgres -d ha10_lab -c "SELECT pg_current_wal_lsn() AS primary_lsn;"
~~~

Standby-side read-only queries:

~~~powershell
docker exec pg-ha10-standby psql -U postgres -d ha10_lab -c "SELECT pg_last_wal_receive_lsn() AS received, pg_last_wal_replay_lsn() AS replayed, pg_last_xact_replay_timestamp() AS last_replayed_commit;"
docker exec pg-ha10-standby psql -U postgres -d ha10_lab -c "SELECT status, latest_end_lsn, last_msg_receipt_time FROM pg_stat_wal_receiver;"
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
) { throw 'Cannot establish immutable postgres:17 image ID' }
foreach ($name in @('pg-ha10-primary','pg-ha10-standby')) {
  $found = @(docker ps -a --format '{{.Names}}' | Where-Object { $_ -eq $name })
  if ($LASTEXITCODE -ne 0 -or $found.Count -ne 0) { throw "Container name unavailable: $name" }
}
foreach ($name in @('pg-ha10-primary-data','pg-ha10-standby-data')) {
  $found = @(docker volume ls --format '{{.Name}}' | Where-Object { $_ -eq $name })
  if ($LASTEXITCODE -ne 0 -or $found.Count -ne 0) { throw "Volume name unavailable: $name" }
}
$found = @(docker network ls --format '{{.Name}}' | Where-Object { $_ -eq 'pg-ha10-net' })
if ($LASTEXITCODE -ne 0 -or $found.Count -ne 0) { throw 'Network name unavailable: pg-ha10-net' }
"Context=$labContext ImageId=$imageId Preflight=PASS"
~~~

**Important:** PowerShell pipelines and Docker subcommands must be checked independently in any production-grade automation; the above is a guided interactive preflight, **not** a concurrency-safe reservation or authorization mechanism. Recheck immediately before creation. If another process creates a matching resource, stop rather than reusing it.

## 1. Create isolated network and volumes

~~~powershell
docker network create --internal --label training.track=pg-enterprise-ch10 pg-ha10-net
docker volume create --label training.track=pg-enterprise-ch10 pg-ha10-primary-data
docker volume create --label training.track=pg-enterprise-ch10 pg-ha10-standby-data
~~~

Expected: network and volumes created. The internal network prevents normal external routing for the lab containers. It is not a production network security control.

## 2. Start primary with WAL streaming settings

~~~powershell
docker run -d --label training.track=pg-enterprise-ch10 --name pg-ha10-primary --network pg-ha10-net -e POSTGRES_PASSWORD=TrainingOnly_HA10_123 -e POSTGRES_DB=ha10_lab -v pg-ha10-primary-data:/var/lib/postgresql/data postgres:17 -c wal_level=replica -c max_wal_senders=5 -c max_replication_slots=5 -c wal_keep_size=64MB -c max_slot_wal_keep_size=256MB

docker exec pg-ha10-primary pg_isready -U postgres -d ha10_lab
docker exec pg-ha10-primary psql -U postgres -d ha10_lab -c "SELECT version(), pg_is_in_recovery();"
docker exec pg-ha10-primary psql -U postgres -d ha10_lab -c "SHOW wal_level; SHOW max_wal_senders; SHOW max_replication_slots;"
~~~

Expected: primary ready, `pg_is_in_recovery() = false`, `wal_level = replica`. If not ready, allow initialization to finish and check logs. The retention cap is applied at checkpoints; it does **not** guarantee WAL disk cannot fill, and a lagging slot can eventually become unusable.

## 3. Create a dedicated replication role and HBA entry

~~~powershell
docker exec pg-ha10-primary psql -U postgres -d ha10_lab -c "CREATE ROLE ha10_repl WITH REPLICATION LOGIN PASSWORD 'TrainingOnly_Repl_HA10_123';"
docker exec -u postgres pg-ha10-primary sh -c 'echo host replication ha10_repl all scram-sha-256 >> /var/lib/postgresql/data/pg_hba.conf && pg_ctl reload -D /var/lib/postgresql/data'
docker exec pg-ha10-primary psql -U postgres -d ha10_lab -c "SELECT rolname, rolreplication, rolsuper FROM pg_roles WHERE rolname='ha10_repl';"
docker exec pg-ha10-primary psql -U postgres -d ha10_lab -c "SELECT line_number, database, user_name, auth_method, error FROM pg_hba_file_rules WHERE 'ha10_repl'=ANY(user_name);"
~~~

Expected: role has replication permission but is not superuser; HBA rule uses SCRAM with no parse error. The HBA `all` address is only tolerable in this dedicated internal training network. Production requires scoped CIDRs, TLS, managed secrets, review and independent security controls. WAL can expose sensitive data.

## 4. Prepare empty standby volume and seed with pg_basebackup

The new named volume may initially be root-owned. Set ownership **only** on the confirmed empty lab standby volume:

~~~powershell
docker run --rm --user root -v pg-ha10-standby-data:/var/lib/postgresql/data postgres:17 sh -c 'chown postgres:postgres /var/lib/postgresql/data && chmod 700 /var/lib/postgresql/data'
~~~

Seed standby using the physical replication protocol. The temporary `PGPASSWORD` is used for the base-backup process; the `passfile` connection option will be recorded by `-R` for later standby connections.

~~~powershell
docker run --rm --network pg-ha10-net --user postgres -e PGPASSWORD=TrainingOnly_Repl_HA10_123 -v pg-ha10-standby-data:/var/lib/postgresql/data postgres:17 pg_basebackup -d 'host=pg-ha10-primary port=5432 user=ha10_repl passfile=/var/lib/postgresql/data/.pgpass application_name=ha10_standby' -D /var/lib/postgresql/data -Fp -Xs -P -R -C -S ha10_standby_slot
~~~

**Expected:** exit code 0; a physical slot named `ha10_standby_slot` exists on the primary; the standby data volume now contains `standby.signal` and generated `primary_conninfo`/`primary_slot_name` settings. Do not rerun: the slot and data directory already exist.

Create the standby's credential file with restricted permissions **inside the lab volume**:

~~~powershell
docker run --rm --user root -v pg-ha10-standby-data:/var/lib/postgresql/data postgres:17 sh -c 'echo pg-ha10-primary:5432:replication:ha10_repl:TrainingOnly_Repl_HA10_123 > /var/lib/postgresql/data/.pgpass && chown postgres:postgres /var/lib/postgresql/data/.pgpass && chmod 600 /var/lib/postgresql/data/.pgpass'
~~~

Expected: exit code 0. Never commit the `.pgpass` file or any real secret. The password is intentionally static for a disposable demonstration only.

## 5. Start standby and verify primary/standby roles

~~~powershell
docker run -d --label training.track=pg-enterprise-ch10 --name pg-ha10-standby --network pg-ha10-net -v pg-ha10-standby-data:/var/lib/postgresql/data postgres:17
docker exec pg-ha10-standby pg_isready -U postgres -d ha10_lab
docker exec pg-ha10-primary psql -U postgres -d ha10_lab -c "SELECT pg_is_in_recovery() AS is_standby;"
docker exec pg-ha10-standby psql -U postgres -d ha10_lab -c "SELECT pg_is_in_recovery() AS is_standby;"
~~~

**Expected:** primary false, standby true. If the standby is not ready, inspect `docker logs --tail 80 pg-ha10-standby`, then recheck.

~~~powershell
docker exec pg-ha10-primary psql -U postgres -d ha10_lab -c "SELECT application_name, state, sync_state, sent_lsn, write_lsn, flush_lsn, replay_lsn FROM pg_stat_replication;"
docker exec pg-ha10-standby psql -U postgres -d ha10_lab -c "SELECT status, sender_host, slot_name, latest_end_lsn FROM pg_stat_wal_receiver;"
~~~

**Expected:** primary sees one `streaming` sender with `sync_state = async`; standby sees one `streaming` receiver with slot `ha10_standby_slot`. Allow brief connection startup time before retrying read-only queries.

## 6. Insert on primary, read on standby

~~~powershell
docker exec pg-ha10-primary psql -U postgres -d ha10_lab -c "CREATE TABLE public.ha10_events (event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, note TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now());"
docker exec pg-ha10-primary psql -U postgres -d ha10_lab -c "INSERT INTO public.ha10_events (note) VALUES ('synthetic replication check');"
docker exec pg-ha10-standby psql -U postgres -d ha10_lab -c "SELECT event_id, note FROM public.ha10_events ORDER BY event_id;"
~~~

**Expected:** one replicated row with note `synthetic replication check`. Because replication is asynchronous, the standby query can initially fail with "relation does not exist" or show no row. Wait briefly and retry the **SELECT only**, checking receiver/replay health if necessary.

## 7. Prove the standby rejects writes (intentional failure)

This is an expected-error test, **not** a command to put in an all-success script:

~~~powershell
docker exec pg-ha10-standby psql -U postgres -d ha10_lab -c "INSERT INTO public.ha10_events (note) VALUES ('must not write on standby');"
~~~

**Expected:** read-only/recovery error and a nonzero exit code. Do not promote or bypass read-only safeguards.

## 8. Inspect WAL, lag and retention safely

Primary-side read-only queries:

~~~powershell
docker exec pg-ha10-primary psql -U postgres -d ha10_lab -c "SELECT application_name, state, sync_state, write_lag, flush_lag, replay_lag FROM pg_stat_replication;"
docker exec pg-ha10-primary psql -U postgres -d ha10_lab -c "SELECT slot_name, slot_type, active, restart_lsn, wal_status FROM pg_replication_slots;"
docker exec pg-ha10-primary psql -U postgres -d ha10_lab -c "SELECT pg_current_wal_lsn() AS primary_lsn;"
~~~

Standby-side read-only queries:

~~~powershell
docker exec pg-ha10-standby psql -U postgres -d ha10_lab -c "SELECT pg_last_wal_receive_lsn() AS received, pg_last_wal_replay_lsn() AS replayed, pg_last_xact_replay_timestamp() AS last_replayed_commit;"
docker exec pg-ha10-standby psql -U postgres -d ha10_lab -c "SELECT status, latest_end_lsn, last_msg_receipt_time FROM pg_stat_wal_receiver;"
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
