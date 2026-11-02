# Chapter 10 Lab — Isolated PostgreSQL Physical Streaming Replication

**Audience:** DBRE/SRE · **Lab:** ~23 minutes of a 60-minute lesson · **Version:** PostgreSQL 17  
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

## 1. Create isolated network and volumes

~~~powershell
docker network create --internal pg-ha10-net
docker volume create pg-ha10-primary-data
docker volume create pg-ha10-standby-data
~~~

Expected: network and volumes created. The internal network prevents normal external routing for the lab containers. It is not a production network security control.

## 2. Start primary with WAL streaming settings

~~~powershell
docker run -d --name pg-ha10-primary --network pg-ha10-net -e POSTGRES_PASSWORD=TrainingOnly_HA10_123 -e POSTGRES_DB=ha10_lab -v pg-ha10-primary-data:/var/lib/postgresql/data postgres:17 -c wal_level=replica -c max_wal_senders=5 -c max_replication_slots=5 -c wal_keep_size=64MB -c max_slot_wal_keep_size=256MB

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
docker run -d --name pg-ha10-standby --network pg-ha10-net -v pg-ha10-standby-data:/var/lib/postgresql/data postgres:17
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

Only an authorized lab owner, **after verifying the exact names and no data retention need**, may manually remove these dedicated resources. These commands irreversibly delete the two lab volumes and all lab data. **Never run on a shared/production host without change approval.**

~~~powershell
docker stop pg-ha10-standby pg-ha10-primary
docker rm pg-ha10-standby pg-ha10-primary
docker volume rm pg-ha10-standby-data pg-ha10-primary-data
docker network rm pg-ha10-net
~~~

No cleanup is required to pass the lab.

## Official PostgreSQL 17 references

- [Streaming replication and standby setup](https://www.postgresql.org/docs/17/warm-standby.html)
- [pg_basebackup](https://www.postgresql.org/docs/17/app-pgbasebackup.html)
- [Replication configuration](https://www.postgresql.org/docs/17/runtime-config-replication.html)
- [Statistics and replication views](https://www.postgresql.org/docs/17/monitoring-stats.html)
- [Replication slot view](https://www.postgresql.org/docs/17/view-pg-replication-slots.html)
