# Chapter 06 Lab — PostgreSQL Host Operations and Persistence

**Duration:** 25–30 minutes of a 60-minute lesson. **Platform:** Windows PowerShell + Docker Desktop in Linux-container mode; PostgreSQL 17 official image. **Status:** Authored, not executed or independently reviewed.

[Chapter 06](../../chapters/06-postgresql-on-bare-metal.md) · [Course home](../../README.md)

> This is a disposable local **simulation** of host-level PostgreSQL operations. It does not validate physical storage, Linux systemd, host kernel tuning, HA, backups, PITR or disaster recovery. Never run these lifecycle commands against production.

## 0. Preflight: protect existing resources (3 minutes)

The exercise uses a dedicated container `pg-baremetal-ch06`, volume `pg_baremetal_ch06_data`, database `training_ch06` and loopback port `55436`. It does not touch previous chapters.

In **PowerShell**, verify Docker and that the resource names/port are unused:

~~~powershell
docker version
docker info --format '{{.OSType}}'
docker ps -a --filter "name=pg-baremetal-ch06"
docker volume ls --filter "name=pg_baremetal_ch06_data"
Get-NetTCPConnection -LocalPort 55436 -State Listen -ErrorAction SilentlyContinue
~~~

Expected: Docker daemon available; `OSType` = `linux`; no matching container/volume or port listener. The last command is Windows-specific; on a Linux host use read-only `ss -lnt`.

**Stop if any resource already exists.** Investigate ownership and select a new approved lab identity; do not delete or overwrite unknown resources.

## 1. Start PostgreSQL with persistent local storage (4 minutes)

The password below is deliberately a disposable **training-only** value; Docker environment metadata can expose it to administrators. Never use this pattern for production secrets.

~~~powershell
docker run -d `
  --name pg-baremetal-ch06 `
  --publish 127.0.0.1:55436:5432 `
  --mount type=volume,source=pg_baremetal_ch06_data,target=/var/lib/postgresql/data `
  --env POSTGRES_PASSWORD=LocalCh06_TrainingOnly_123 `
  --env POSTGRES_DB=training_ch06 `
  postgres:17
~~~

**PowerShell note:** The trailing character on each continued command line is the PowerShell backtick; ensure there are no spaces after it. The container listens only on the host's loopback interface.

~~~powershell
docker ps --filter "name=pg-baremetal-ch06"
docker exec pg-baremetal-ch06 pg_isready -U postgres -d training_ch06
docker logs --tail 25 pg-baremetal-ch06
~~~

Expected: running container and `accepting connections`. Initialization may take a few seconds. If readiness fails, wait briefly and recheck the logs rather than assuming the database is available.

## 2. Verify identity and role (3 minutes)

~~~powershell
docker exec pg-baremetal-ch06 psql -U postgres -d training_ch06 -c "SELECT current_database(), current_user, version();"
docker exec pg-baremetal-ch06 psql -U postgres -d training_ch06 -c "SELECT pg_postmaster_start_time(), pg_is_in_recovery();"
~~~

Expected: `training_ch06`, `postgres`, PostgreSQL 17 and `pg_is_in_recovery() = false`. Record actual values; never invent a startup timestamp.

## 3. Discover configuration, authentication and restart requirements (4 minutes)

~~~powershell
docker exec pg-baremetal-ch06 psql -U postgres -d training_ch06 -c "SHOW data_directory;"
docker exec pg-baremetal-ch06 psql -U postgres -d training_ch06 -c "SHOW config_file;"
docker exec pg-baremetal-ch06 psql -U postgres -d training_ch06 -c "SHOW hba_file;"
docker exec pg-baremetal-ch06 psql -U postgres -d training_ch06 -c "SHOW ident_file;"
docker exec pg-baremetal-ch06 psql -U postgres -d training_ch06 -c "SELECT name, setting, unit, source, context, pending_restart FROM pg_settings WHERE name IN ('shared_buffers','max_connections','work_mem','wal_level','fsync','logging_collector') ORDER BY name;"
~~~

Expected: data directory `/var/lib/postgresql/data` and file paths determined by the image; `pg_settings` shows values and whether restart is pending. A fresh lab normally has `pending_restart = false`. Native Linux package paths can differ: always discover them.

Read-only HBA syntax inspection:

~~~powershell
docker exec pg-baremetal-ch06 psql -U postgres -d training_ch06 -c "SELECT rule_number, type, address, auth_method, error FROM pg_hba_file_rules ORDER BY rule_number LIMIT 20;"
~~~

Expected: valid rules have a null `error`. Redact addresses before sharing logs. Do not edit `pg_hba.conf` or change authentication in this lab.

## 4. Observe OS/storage and runtime usage (3 minutes)

~~~powershell
docker exec pg-baremetal-ch06 sh -c 'cat /proc/1/comm; ls -ld /var/lib/postgresql/data; df -h /var/lib/postgresql/data'
docker stats --no-stream pg-baremetal-ch06
docker inspect --format '{{.Mounts}}' pg-baremetal-ch06
~~~

Expected: process name, directory permissions, filesystem usage, one-time CPU/memory sample and mount referencing `pg_baremetal_ch06_data`.

**Limits of evidence:** Docker Desktop may report a virtual disk rather than physical host storage; these commands do not prove IOPS, latency, power-loss durability or NUMA behavior. Avoid committing unrestricted `docker inspect` output because it can expose the training password.

## 5. Create a synthetic marker and inspect health (4 minutes)

Execute **once** in the newly created disposable database:

~~~powershell
docker exec pg-baremetal-ch06 psql -U postgres -d training_ch06 -v ON_ERROR_STOP=1 -c "CREATE TABLE public.chapter06_marker (id integer PRIMARY KEY, note text NOT NULL);"
docker exec pg-baremetal-ch06 psql -U postgres -d training_ch06 -v ON_ERROR_STOP=1 -c "INSERT INTO public.chapter06_marker(id,note) VALUES (1,'persisted');"
docker exec pg-baremetal-ch06 psql -U postgres -d training_ch06 -c "SELECT id, note FROM public.chapter06_marker;"
docker exec pg-baremetal-ch06 psql -U postgres -d training_ch06 -c "SELECT datname, numbackends, xact_commit, xact_rollback, deadlocks FROM pg_stat_database WHERE datname='training_ch06';"
docker exec pg-baremetal-ch06 psql -U postgres -d training_ch06 -c "SELECT pg_size_pretty(pg_database_size(current_database())) AS database_size;"
~~~

Expected: exactly one marker `1 | persisted`, a statistics row, and a small database size. Stats are cumulative and timing-dependent. The table creation is intentionally not idempotent: if it already exists, inspect the target identity and prior data rather than dropping it.

## 6. Optional controlled local stop/start (4 minutes)

**Only after verifying the exact disposable container identity.** This is an intentionally disruptive operation on a local training instance, not an HA test.

~~~powershell
docker stop --time 60 pg-baremetal-ch06
docker ps -a --filter "name=pg-baremetal-ch06"
docker start pg-baremetal-ch06
docker exec pg-baremetal-ch06 pg_isready -U postgres -d training_ch06
~~~

If the readiness check occurs during startup, wait and retry. Once ready:

~~~powershell
docker exec pg-baremetal-ch06 psql -U postgres -d training_ch06 -c "SELECT id, note FROM public.chapter06_marker;"
docker exec pg-baremetal-ch06 psql -U postgres -d training_ch06 -c "SELECT pg_postmaster_start_time();"
~~~

Expected: marker remains present and the startup time is newer. This proves persistence across this controlled restart, **not** backup/restore, WAL archive correctness, independent-node failover or measured RPO/RTO. Skip this step if you cannot confirm the lab identity.

## 7. Optional native Linux staging comparison (read-only)

On an **approved non-production Linux staging host only**, inspect the OS and discover the actual PostgreSQL service unit:

~~~bash
hostnamectl
systemctl list-units --type=service --all 'postgresql*'
lsblk -f
df -h
ss -lnt
~~~

If permitted, review `systemctl status <verified-unit>` and `journalctl -u <verified-unit>` for the unit discovered above. Unit names, package layouts and access policies vary. Do **not** restart services, edit kernel settings, open firewalls or guess a service name.

A Docker container cannot validate native systemd integration, physical storage guarantees, Linux limits, real network segmentation, enterprise TLS/identity, or HA/DR.

## 8. Troubleshooting

| Symptom | Check | Safe next step |
|---|---|---|
| Docker daemon unavailable | `docker version` / `docker info` | Start local Docker Engine; confirm Linux mode |
| Container/volume exists | `docker ps -a`, `docker volume ls` | Inspect ownership; never delete blindly |
| Port in use | `Get-NetTCPConnection` | Use a different loopback port consistently |
| Connection refused | `pg_isready` and scoped logs | Wait for startup; inspect initialization errors |
| Auth failure | Database identity, reused volume | Verify credentials/initialization; don't set global trust |
| Marker missing | DB name, volume mount, SQL result | Confirm correct target; avoid overwriting data |
| Config path differs | `SHOW data_directory`, `SHOW config_file` | Trust discovered values, not hard-coded assumptions |
| Unexpected resource use | `docker stats` and host workload | Record evidence; do not blindly tune settings |

## 9. Acceptance and evidence

- [ ] Docker daemon and isolated resource identity confirmed.
- [ ] PostgreSQL version, database identity and primary/standby state recorded.
- [ ] PGDATA, config, HBA and ident paths discovered.
- [ ] `pg_settings` values, source, context and pending restart captured.
- [ ] HBA parser checked without sharing sensitive network data.
- [ ] OS/process/storage and Docker metrics observed with limitations noted.
- [ ] Synthetic marker and database health queries succeeded.
- [ ] Optional restart persistence confirmed, or explicitly skipped.
- [ ] Explain which checks require a real staging Linux host and a separate HA/DR test.
- [ ] Sanitize evidence and obtain independent reviewer approval before changing validation status.

**Publication status:** expected outputs are written examples; no execution evidence has been collected.

## 10. Cleanup and rollback policy

Retain the disposable container and volume for review. This lab intentionally includes **no destructive cleanup command**. Deleting a named volume destroys lab data and requires a separate manual identity check and approval. For a failed local startup, inspect logs and isolate the issue rather than deleting the volume.

## 11. Official references

- [PostgreSQL 17: Starting the Database Server](https://www.postgresql.org/docs/17/server-start.html)
- [PostgreSQL 17: Configuration File Locations](https://www.postgresql.org/docs/17/runtime-config-file-locations.html)
- [PostgreSQL 17: pg_hba.conf](https://www.postgresql.org/docs/17/auth-pg-hba-conf.html)
- [PostgreSQL 17: pg_settings](https://www.postgresql.org/docs/17/view-pg-settings.html)
- [PostgreSQL 17: Database File Layout](https://www.postgresql.org/docs/17/storage-file-layout.html)
- [PostgreSQL 17: Monitoring Statistics](https://www.postgresql.org/docs/17/monitoring-stats.html)
