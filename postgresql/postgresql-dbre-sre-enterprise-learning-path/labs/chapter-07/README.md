# Chapter 07 Lab — RDS Operational Readiness Without Creating AWS Resources

**Lesson:** [PostgreSQL on AWS RDS](../../chapters/07-postgresql-on-aws-rds.md)  
**Guided duration:** 23 minutes in the 60-minute chapter · **Local runtime:** PostgreSQL 17 on Docker Desktop (Windows PowerShell)  
**AWS account:** Not required for core lab · **State:** Written, not executed or independently reviewed

> This is a **self-managed PostgreSQL comparison lab**, not an RDS emulator. It teaches the SQL and evidence-gathering responsibilities that remain with DBRE/SRE on RDS. It does **not** simulate AWS-managed backups, Multi-AZ failover, RDS-specific roles, CloudWatch, or RDS point-in-time recovery.

## 0. Prerequisites and safety (3 minutes)

Use only the disposable `pg-fleet-lab` PostgreSQL container from [Chapter 01](../chapter-01/README.md). Do not run these commands against production or a shared database. The lab uses synthetic data, no real credentials, no cloud resources and no AWS billing.

In **PowerShell**:

```powershell
docker version
docker ps --filter "name=pg-fleet-lab"
docker exec pg-fleet-lab pg_isready -U postgres
docker exec pg-fleet-lab psql -U postgres -d postgres -c "SELECT version();"
```

**Expected:** Docker server available; container running; `accepting connections`; PostgreSQL 17. If missing, follow Chapter 01 setup and return. Do not create a similarly named resource on an unverified server.

Check for existing objects:

```powershell
docker exec pg-fleet-lab psql -U postgres -d postgres -tAc "SELECT datname FROM pg_database WHERE datname IN ('training_ch07','training_ch07_restore') ORDER BY datname;"
docker exec pg-fleet-lab psql -U postgres -d postgres -tAc "SELECT rolname FROM pg_roles WHERE rolname='ch07_reader';"
```

**Expected on first run:** blank results. If any name already exists, inspect it and stop rather than overwriting, dropping or silently reusing unknown data. The role is **cluster-wide**, not scoped to one database.

## 1. Create an isolated database (2 minutes)

Only after verifying the name is unused:

```powershell
docker exec pg-fleet-lab createdb -U postgres training_ch07
docker exec -it pg-fleet-lab psql -U postgres -d training_ch07
```

The following SQL blocks are run inside this interactive `psql` session until you see `\q`.

```sql
SELECT current_database() AS database, current_user AS connected_as;
SELECT version();
SELECT pg_is_in_recovery() AS is_replica;
```

**Expected:** `training_ch07`, `postgres`, and `false`. A local primary does not demonstrate RDS Multi-AZ.

## 2. Create synthetic application data (3 minutes)

```sql
CREATE SCHEMA rds_compare;

CREATE TABLE rds_compare.order_events (
    event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    external_order_id TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK (event_type IN ('created','paid','shipped')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO rds_compare.order_events (external_order_id, event_type)
VALUES
  ('DEMO-1001','created'),
  ('DEMO-1001','paid'),
  ('DEMO-1002','created');

SELECT count(*) AS event_count FROM rds_compare.order_events;
```

**Expected:** `3`. Data is synthetic and disposable.

## 3. Inspect configuration, capacity and sessions (4 minutes)

These read-only SQL queries also work on RDS when the account has appropriate database privileges:

```sql
SELECT name, setting, unit, context, pending_restart
FROM pg_settings
WHERE name IN (
  'max_connections',
  'shared_buffers',
  'work_mem',
  'log_min_duration_statement'
)
ORDER BY name;

SELECT current_database() AS db_name,
       pg_size_pretty(pg_database_size(current_database())) AS db_size;

SELECT datname, numbackends, xact_commit, xact_rollback, deadlocks
FROM pg_stat_database
WHERE datname = current_database();

SELECT pid, usename, state, wait_event_type
FROM pg_stat_activity
WHERE datname = current_database()
ORDER BY pid;
```

**Expected:** settings and a small database size; `pending_restart` values normally `false` in a fresh lab. Actual memory settings, counters, PIDs and session state vary.

Record:
- Which settings are `postmaster` (restart context) versus user/session configurable?
- What would you monitor before changing `max_connections`?
- What is missing from local SQL evidence that AWS RDS CloudWatch and event logs would add?

**Do not issue `ALTER SYSTEM`, edit configuration files, or restart the container in this lab.** On RDS, supported settings are managed through parameter groups and approved change processes.

## 4. Least-privilege database role (4 minutes)

This role is **not** `rds_superuser`. It demonstrates ordinary PostgreSQL privileges only.

```sql
CREATE ROLE ch07_reader NOLOGIN NOSUPERUSER;
GRANT CONNECT ON DATABASE training_ch07 TO ch07_reader;
GRANT USAGE ON SCHEMA rds_compare TO ch07_reader;
GRANT SELECT ON TABLE rds_compare.order_events TO ch07_reader;

SET ROLE ch07_reader;
SELECT current_user AS effective_role;
SELECT count(*) AS readable_rows FROM rds_compare.order_events;
```

**Expected:** effective role `ch07_reader` and readable rows `3`.

Now intentionally attempt a forbidden write:

```sql
INSERT INTO rds_compare.order_events (external_order_id, event_type)
VALUES ('DEMO-BLOCKED','created');
```

**Expected error:** `permission denied for table order_events`. This is a planned negative test. Since `psql` is in autocommit mode, the error does not leave an explicit transaction open.

Restore the original role and verify no data was added:

```sql
RESET ROLE;
SELECT current_user AS effective_role;
SELECT count(*) AS event_count FROM rds_compare.order_events;
```

**Expected:** `postgres`, `3`.

**Production warning:** do not grant RDS `rds_superuser` to application accounts. The local container's true PostgreSQL superuser cannot model the RDS administrative boundary.

## 5. Logical backup and independent local restore (5 minutes)

Leave `psql`:

```text
\q
```

In **PowerShell**:

```powershell
docker exec pg-fleet-lab pg_dump -U postgres -Fc -f /tmp/training_ch07.dump training_ch07
docker exec pg-fleet-lab ls -lh /tmp/training_ch07.dump
docker exec pg-fleet-lab createdb -U postgres training_ch07_restore
docker exec pg-fleet-lab pg_restore -U postgres -d training_ch07_restore /tmp/training_ch07.dump
docker exec pg-fleet-lab psql -U postgres -d training_ch07_restore -c "SELECT count(*) AS restored_events FROM rds_compare.order_events;"
```

**Expected:** `pg_dump` and `pg_restore` return without errors; restored row count `3`. The archive is stored **inside the disposable container**; copy it out and protect it appropriately only if your training workflow requires it.

**Important limitations:** this is a PostgreSQL **logical backup** restored to another database on the **same host/container**. It does **not** prove independent-node recovery, AWS automated backups, RDS snapshots, PITR, RPO/RTO, encryption policy or cross-region DR. Those require separate approved tests and evidence.

## 6. Optional AWS CLI inventory — existing resources only (outside core lab)

**Skip unless** you already have an approved AWS account, a read-only role, an installed AWS CLI, a known region and an existing RDS identifier. These commands make **no AWS mutations** and create no RDS resources. Do not invent identifiers, run provisioning commands, or modify credentials. Existing organizational logging and service costs may still apply.

In **PowerShell** (substitute only authorized existing values):

```powershell
# OPTIONAL: do not run unless you have authorized read-only AWS access.
$Region = "us-east-1"       # Replace with the actual authorized Region.
$DbId = "EXISTING-DB-ID"     # Replace with an existing authorized DB instance ID.

aws --version
aws sts get-caller-identity
aws rds describe-db-instances --region $Region --db-instance-identifier $DbId --query 'DBInstances[0].{Engine:Engine,EngineVersion:EngineVersion,Class:DBInstanceClass,MultiAZ:MultiAZ,BackupRetentionDays:BackupRetentionPeriod,LatestRestorableTime:LatestRestorableTime,StorageEncrypted:StorageEncrypted,PubliclyAccessible:PubliclyAccessible,DeletionProtection:DeletionProtection,ParameterGroups:DBParameterGroups[*].DBParameterGroupName}' --output json
```

**Expected:** a JSON inventory for the authorized instance, if it exists and the role permits access. `LatestRestorableTime` can be null when no usable point is reported. Redact account identifiers, endpoints, instance IDs, tags, and sensitive metadata before sharing.

For an **existing Multi-AZ DB cluster** (not a DB instance), use a separately authorized known cluster identifier:

```powershell
# OPTIONAL: only if a real authorized Multi-AZ DB cluster already exists.
$ClusterId = "EXISTING-CLUSTER-ID"
aws rds describe-db-clusters --region $Region --db-cluster-identifier $ClusterId --query 'DBClusters[0].{Engine:Engine,EngineVersion:EngineVersion,Members:DBClusterMembers[*].{Instance:DBInstanceIdentifier,Writer:IsClusterWriter},BackupRetentionDays:BackupRetentionPeriod,LatestRestorableTime:LatestRestorableTime,StorageEncrypted:StorageEncrypted}' --output json
```

These commands are **read-only inventory**. They do not test failover or backup restore. AWS CLI authentication failures or absent resources are an **optional step skipped**, not a reason to invent output.

## 7. Architecture review deliverable (2 minutes)

Use this table in a short review memo:

| Question | Proposed answer | Evidence still needed |
|---|---|---|
| Workload and consistency | Transactional PostgreSQL; write traffic to writer | Peak TPS, SQL plans |
| Availability topology | Compare Multi-AZ DB instance vs Multi-AZ DB cluster | SLO, read ratio, regional support |
| Read scaling | Independent read replica only if justified | Lag tolerance, query rate |
| Recovery | Explicit retention, isolated restore drills | Approved RPO/RTO and measured evidence |
| Access | Private network, TLS, least privilege | SG, IAM, DB grants and KMS review |
| Monitoring | CloudWatch Database Insights + DB metrics | Alert thresholds and on-call owner |
| Cost | Class, storage, IOPS, AZ mode, backup, logs | Current regional estimate |

State what remains unknown rather than selecting a production topology without requirements.

## 8. Troubleshooting and safe recovery

| Symptom | Explanation | Safe action |
|---|---|---|
| `pg-fleet-lab` missing | Docker lab not started | Revisit Chapter 01 setup |
| Database or role already exists | Prior exercise or name collision | Inspect and use a newly approved lab name; do not drop automatically |
| Permission denied on SELECT | Grant or role context incorrect | Check `current_user` and explicit grants |
| Permission denied on INSERT | **Expected** least-privilege result | Run `RESET ROLE` and verify row count |
| `pg_restore` error | Target not empty, missing role, archive issue | Inspect output and choose a fresh disposable restore DB |
| AWS `AccessDenied` | Missing IAM permission | Skip optional inventory; request approved read-only role |
| AWS resource not found | Wrong region, ID or account | Verify with owner; do not create replacement |
| AWS CLI unavailable | Not installed or not configured | Skip optional inventory |

## 9. Evidence and acceptance checklist

- [ ] Verified PostgreSQL 17 and correct disposable container/database.
- [ ] Created synthetic table and observed exactly three events.
- [ ] Recorded configuration context, DB size and session metrics.
- [ ] Observed read-only role can SELECT but cannot INSERT.
- [ ] Restored a logical backup into `training_ch07_restore` and verified three events.
- [ ] Distinguished local backup from RDS automated backup and PITR.
- [ ] Completed an architecture recommendation with recovery and ownership assumptions.
- [ ] Optional AWS CLI inventory: mark **skipped** unless real authorized output was captured.
- [ ] Saved sanitized evidence and noted actual execution date, reviewer and environment.

**Authored is not runtime verified.** Expected values above are instructional, not observed results.

## 10. Cleanup policy

Keep `training_ch07`, `training_ch07_restore` and `ch07_reader` for review if useful. No destructive cleanup is performed or required. If removing them later, first verify the exact disposable database/role identities and obtain appropriate approval; never automate a broad `DROP DATABASE` or `DROP ROLE` on shared servers.

## 11. Official references

- [AWS RDS PostgreSQL](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_PostgreSQL.html)
- [AWS RDS roles and `rds_superuser`](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Appendix.PostgreSQL.CommonDBATasks.Roles.rds_superuser.html)
- [AWS RDS PITR](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_PIT.html)
- [AWS RDS automated backup retention](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithAutomatedBackups.BackupRetention.html)
- [PostgreSQL 17 pg_dump](https://www.postgresql.org/docs/17/app-pgdump.html)
- [PostgreSQL 17 pg_restore](https://www.postgresql.org/docs/17/app-pgrestore.html)
- [PostgreSQL 17 pg_settings](https://www.postgresql.org/docs/17/view-pg-settings.html)
