# Chapter 15 Lab — Fleet Inventory and Governance

**Duration:** 60 minutes (includes lecture and lab); practical exercises approximately 25–35 minutes.  
**Status:** Authored, **not executed**; expected results are illustrative, not evidence.  
**Related lesson:** [Chapter 15 — Fleet Inventory and Governance](../../chapters/15-fleet-inventory-and-governance.md)

## 1. Prerequisites and platform assumptions

- Docker Desktop/Engine with Linux containers; `docker version` and `docker info` must succeed. Tested command *design* for Bash and PowerShell; commands have **not** been executed as part of publication.
- PostgreSQL **17** official image (`postgres:17`); Docker may pull image bytes over the network. Prefer an approved, pinned digest in controlled environments.
- At least ~1 GB free disk and enough RAM for one small container. All data is synthetic.
- Run from the **repository root** so paths beginning `postgresql/postgresql-dbre-sre-enterprise-learning-path/` resolve.
- Port **55415** is used on `127.0.0.1` only; change it if occupied.
- No AWS credentials, Kubernetes cluster, production PostgreSQL endpoint, or paid resources required.

**Safety boundary:** never replace the container name or SQL target with a production host. `docker rm` and `docker volume rm` are destructive for their named resources. Use only the lab identifiers below and inspect before removal.

## 2. Teaching plan (60 minutes)

| Time | Activity | Evidence |
|---|---|---|
| 0–10 min | Explain fleet identity and data ownership | Sketch of cluster/database/service mapping |
| 10–20 min | Launch isolated PostgreSQL and create synthetic assets | Version and database list |
| 20–35 min | Capture read-only inventory | Timestamped SQL output |
| 35–45 min | Compare illustrative configuration policy | MATCH/REVIEW findings |
| 45–53 min | Enrich with human owner attestation | Synthetic governance record |
| 53–60 min | Review limitations, troubleshoot, clean up | Acceptance checklist |

## 3. Architecture and lab identifiers

```text
Your terminal (Bash or PowerShell)
   |
   | docker cp / docker exec psql
   v
Docker container: pg-fleet-ch15
   |-- PostgreSQL 17 (single instance, NOT HA)
   |-- postgres (administrative database)
   |-- fleet_lab_app (synthetic app database)
   |-- fleet_lab_reporting (synthetic reporting database)
   '-- Docker named volume: pg-fleet-ch15-data
```

This is **one PostgreSQL cluster with two application databases**, not two independent fleet members. The lab demonstrates the inventory unit of observation and why a second, owner-attested record is needed. No replicas, backup or TLS certification are implied.

## 4. Start the isolated instance

From a terminal at the repository root:

```bash
docker version
docker info --format '{{.OSType}}'
docker ps -a --filter name=^/pg-fleet-ch15$
docker volume ls --filter name=^pg-fleet-ch15-data$
```

**Stop if either lab name already exists**: inspect it and confirm provenance; do not overwrite or delete an unrelated resource. Only if neither exists:

```bash
docker volume create pg-fleet-ch15-data
docker run -d --name pg-fleet-ch15 \
  --label training.postgresql.chapter=15 \
  -e POSTGRES_PASSWORD=training_only_change_me \
  -e POSTGRES_DB=postgres \
  -p 127.0.0.1:55415:5432 \
  -v pg-fleet-ch15-data:/var/lib/postgresql/data \
  postgres:17
```

**PowerShell:** the multi-line `docker run` above uses Bash continuations; enter it as a **single line** in PowerShell:

```powershell
docker run -d --name pg-fleet-ch15 --label training.postgresql.chapter=15 -e POSTGRES_PASSWORD=training_only_change_me -e POSTGRES_DB=postgres -p 127.0.0.1:55415:5432 -v pg-fleet-ch15-data:/var/lib/postgresql/data postgres:17
```

The password is a public training-only placeholder; do not reuse it. For a controlled environment use an approved secret injection method. The port is loopback-bound, but local machine users may still access it.

Wait until ready (repeat if necessary):

```bash
docker exec pg-fleet-ch15 pg_isready -U postgres -d postgres
docker exec pg-fleet-ch15 psql -U postgres -d postgres -Atc "SHOW server_version;"
```

**Expected:** `accepting connections` and a `17.x` version. First initialization may take several seconds. **Immediately save the full container ID returned by `docker run` in your private lab evidence** (for example, `CH15_CONTAINER_ID`). Do not use the name or image tag as proof of ownership. Do not mistake a successful container launch for a healthy database.

## 5. Create synthetic roles and databases (lab-only writes)

Copy the tracked setup script into the **named container**, then execute with stop-on-error:

```bash
docker cp postgresql/postgresql-dbre-sre-enterprise-learning-path/labs/chapter-15/setup.sql pg-fleet-ch15:/tmp/ch15-setup.sql
docker exec pg-fleet-ch15 psql -X -v ON_ERROR_STOP=1 -U postgres -d postgres -f /tmp/ch15-setup.sql
```

The script creates two `NOLOGIN` owner roles and two databases **only when absent**, then creates two synthetic tables and seed rows. `\gexec` is a `psql` meta-command; do not run this script via a generic SQL driver. It must never be pointed at a shared or production PostgreSQL server.

**Expected:** `CREATE ROLE`, `CREATE DATABASE`, `CREATE SCHEMA`, `CREATE TABLE`, `INSERT 0 2` on first run; reruns may show NOTICE for already-existing objects and `INSERT 0 0`. No real patient, customer, or company data is used.

## 6. Read-only inventory collection

```bash
docker cp postgresql/postgresql-dbre-sre-enterprise-learning-path/labs/chapter-15/inventory.sql pg-fleet-ch15:/tmp/ch15-inventory.sql
docker exec pg-fleet-ch15 psql -X -v ON_ERROR_STOP=1 -U postgres -d postgres -f /tmp/ch15-inventory.sql
```

**Expected observations (not actual run evidence):**

- Server version begins `17.`; `pg_is_in_recovery()` is `f` for this standalone primary.
- `fleet_lab_app` and `fleet_lab_reporting` appear with `fleet_lab_app_owner` and `fleet_lab_reporting_owner` as **database role owners**.
- The two owner roles have `rolcanlogin=f` and `rolsuper=f`.
- `pg_settings` shows values, units, source and `pending_restart`. These are session-visible settings, not proof of a fleet-wide policy.
- `pg_stat_database` counters and database sizes are environment- and timing-dependent; do not assert exact numbers.
- The timestamp is an observation timestamp. `pg_control_system()` reports a local PostgreSQL system identifier; do not publish it as a secret-free globally unique enterprise asset key without a governance mapping.

**Important:** The SQL intentionally avoids passwords, `pg_authid`, query text, network endpoints, and personally identifying data. In a real collector, require a dedicated least-privilege role and validate visibility before deployment. This lab uses the container administrator only to simplify isolated setup.

## 7. Compare with an illustrative policy (no config changes)

```bash
docker cp postgresql/postgresql-dbre-sre-enterprise-learning-path/labs/chapter-15/drift.sql pg-fleet-ch15:/tmp/ch15-drift.sql
docker exec pg-fleet-ch15 psql -X -v ON_ERROR_STOP=1 -U postgres -d postgres -f /tmp/ch15-drift.sql
```

The lab's synthetic baseline expects `max_connections=200` to intentionally demonstrate a mismatch against the stock image default (often 100); other sample values are `wal_level=replica` and `password_encryption=scram-sha-256`. If the image or environment differs, **interpret actual values**; do not hardcode pass/fail based on the example.

Example (illustrative):

```text
name                 observed       expected         finding
max_connections      100            200              REVIEW
password_encryption  scram-sha-256  scram-sha-256    MATCH
wal_level            replica        replica          MATCH
```

`REVIEW` means **policy comparison**, not a recommendation to increase connections. No `ALTER SYSTEM`, `SET`, or restart occurs.

## 8. Owner attestation exercise (manual, no secrets)

Copy and fill this **synthetic** record in your training notes:

```yaml
fleet_asset_id: TRAINING-CH15-LOCAL-01
platform: local-docker
environment: disposable-training
database: fleet_lab_app
postgres_role_owner: fleet_lab_app_owner
business_owner: example-application-team  # NOT discovered from SQL
dbre_owner: example-dbre-team              # NOT discovered from SQL
classification: synthetic-public
rpo_target: not-established
rto_target: not-established
backup_restore_verified: false
observed_at: <UTC timestamp of your query>
baseline_version: training-v1
drift: REVIEW
exception_ticket: TRAINING-EXCEPTION-001
exception_owner: example-dbre-team
exception_expires_at: <training date>
evidence: <local sanitized SQL output location>
```

Explain in two sentences why a database authorization role is not a business owner, and why an RPO/RTO target cannot be inferred from the existence of a database. The `TRAINING-` identifiers are not production ticket numbers.

## 9. Optional platform discovery (not required; no provisioning)

Only with existing permission and **after checking account/cluster context**:

```bash
# AWS CLI v2; read-only, may produce API audit records.
aws sts get-caller-identity
aws rds describe-db-instances --region YOUR_REGION --query 'DBInstances[?Engine==`postgres`].[DBInstanceIdentifier,EngineVersion,DBInstanceStatus]' --output table

# Only if an authorized Kubernetes context and CloudNativePG CRD already exist.
kubectl config current-context
kubectl get clusters.postgresql.cnpg.io -A
```

No AWS or Kubernetes access is assumed. Do not create cloud resources, deploy an operator, enumerate Kubernetes Secrets, or infer missing objects mean no databases exist.

## 10. Troubleshooting

| Symptom | Safe response |
|---|---|
| Docker daemon unavailable | Start Docker Desktop/Engine; check `docker info`; do not change managed host settings without IT approval |
| Port 55415 busy | Use another localhost port; do not stop unrelated processes |
| Container exists | Inspect `docker inspect pg-fleet-ch15`; do not overwrite a resource of unknown origin |
| `pg_isready` fails | Wait for initialization, inspect `docker logs pg-fleet-ch15` (redact before sharing) |
| `psql: error` during setup | Confirm `-d postgres`, file copied, and `psql` client inside container; use `ON_ERROR_STOP` |
| `\gexec` syntax error | Use `psql -f`, not a SQL-only executor |
| Different config values | Capture `source` and actual image version; treat policy as synthetic |
| No rows for app databases | Re-run setup after confirming correct isolated container |
| Permission denied for system identifier | Admin-only function; omit in least-privilege inventory or use approved collector privileges |
| `docker volume rm` reports in use | Container still references it; do not force-delete unrelated resources |

## 11. Safe cleanup / rollback

Before cleanup, confirm the Docker context, **full container ID from the original `docker run`**, ownership label, and all mounts. Do not copy a container ID from a fresh inspect as a substitute for the original creation record. Run the following read-only commands in Bash or PowerShell:

```text
docker context show
docker inspect --format '{{.Id}}' pg-fleet-ch15
docker inspect --format '{{index .Config.Labels "training.postgresql.chapter"}}' pg-fleet-ch15
docker inspect --format '{{json .Mounts}}' pg-fleet-ch15
docker volume inspect pg-fleet-ch15-data
```

**Stop unless all checks pass:** the Docker context is the one used to create the disposable lab; the full inspected ID exactly matches the saved `CH15_CONTAINER_ID`; the label is `15`; the only mount is the named volume `pg-fleet-ch15-data` at `/var/lib/postgresql/data`; and the volume is not shared with any other container. Check other container references before deleting the volume:

```text
docker ps -a --filter volume=pg-fleet-ch15-data --format '{{.ID}} {{.Names}}'```

The output must contain **only the originally created lab container**. If the original ID was not recorded, or the context, mount, or volume provenance is uncertain, **retain the resources and record cleanup as blocked**; never remove by name alone. After all checks pass, the following **manual destructive commands** remove synthetic data irreversibly:

```text
docker rm -f pg-fleet-ch15
docker volume rm pg-fleet-ch15-data
```

Capture the command results and verify absence with `docker ps -a --filter name=^/pg-fleet-ch15# Chapter 15 Lab — Fleet Inventory and Governance

**Duration:** 60 minutes (includes lecture and lab); practical exercises approximately 25–35 minutes.  
**Status:** Authored, **not executed**; expected results are illustrative, not evidence.  
**Related lesson:** [Chapter 15 — Fleet Inventory and Governance](../../chapters/15-fleet-inventory-and-governance.md)

## 1. Prerequisites and platform assumptions

- Docker Desktop/Engine with Linux containers; `docker version` and `docker info` must succeed. Tested command *design* for Bash and PowerShell; commands have **not** been executed as part of publication.
- PostgreSQL **17** official image (`postgres:17`); Docker may pull image bytes over the network. Prefer an approved, pinned digest in controlled environments.
- At least ~1 GB free disk and enough RAM for one small container. All data is synthetic.
- Run from the **repository root** so paths beginning `postgresql/postgresql-dbre-sre-enterprise-learning-path/` resolve.
- Port **55415** is used on `127.0.0.1` only; change it if occupied.
- No AWS credentials, Kubernetes cluster, production PostgreSQL endpoint, or paid resources required.

**Safety boundary:** never replace the container name or SQL target with a production host. `docker rm` and `docker volume rm` are destructive for their named resources. Use only the lab identifiers below and inspect before removal.

## 2. Teaching plan (60 minutes)

| Time | Activity | Evidence |
|---|---|---|
| 0–10 min | Explain fleet identity and data ownership | Sketch of cluster/database/service mapping |
| 10–20 min | Launch isolated PostgreSQL and create synthetic assets | Version and database list |
| 20–35 min | Capture read-only inventory | Timestamped SQL output |
| 35–45 min | Compare illustrative configuration policy | MATCH/REVIEW findings |
| 45–53 min | Enrich with human owner attestation | Synthetic governance record |
| 53–60 min | Review limitations, troubleshoot, clean up | Acceptance checklist |

## 3. Architecture and lab identifiers

```text
Your terminal (Bash or PowerShell)
   |
   | docker cp / docker exec psql
   v
Docker container: pg-fleet-ch15
   |-- PostgreSQL 17 (single instance, NOT HA)
   |-- postgres (administrative database)
   |-- fleet_lab_app (synthetic app database)
   |-- fleet_lab_reporting (synthetic reporting database)
   '-- Docker named volume: pg-fleet-ch15-data
```

This is **one PostgreSQL cluster with two application databases**, not two independent fleet members. The lab demonstrates the inventory unit of observation and why a second, owner-attested record is needed. No replicas, backup or TLS certification are implied.

## 4. Start the isolated instance

From a terminal at the repository root:

```bash
docker version
docker info --format '{{.OSType}}'
docker ps -a --filter name=^/pg-fleet-ch15$
docker volume ls --filter name=^pg-fleet-ch15-data$
```

**Stop if either lab name already exists**: inspect it and confirm provenance; do not overwrite or delete an unrelated resource. Only if neither exists:

```bash
docker volume create pg-fleet-ch15-data
docker run -d --name pg-fleet-ch15 \
  --label training.postgresql.chapter=15 \
  -e POSTGRES_PASSWORD=training_only_change_me \
  -e POSTGRES_DB=postgres \
  -p 127.0.0.1:55415:5432 \
  -v pg-fleet-ch15-data:/var/lib/postgresql/data \
  postgres:17
```

**PowerShell:** the multi-line `docker run` above uses Bash continuations; enter it as a **single line** in PowerShell:

```powershell
docker run -d --name pg-fleet-ch15 --label training.postgresql.chapter=15 -e POSTGRES_PASSWORD=training_only_change_me -e POSTGRES_DB=postgres -p 127.0.0.1:55415:5432 -v pg-fleet-ch15-data:/var/lib/postgresql/data postgres:17
```

The password is a public training-only placeholder; do not reuse it. For a controlled environment use an approved secret injection method. The port is loopback-bound, but local machine users may still access it.

Wait until ready (repeat if necessary):

```bash
docker exec pg-fleet-ch15 pg_isready -U postgres -d postgres
docker exec pg-fleet-ch15 psql -U postgres -d postgres -Atc "SHOW server_version;"
```

**Expected:** `accepting connections` and a `17.x` version. First initialization may take several seconds. **Immediately save the full container ID returned by `docker run` in your private lab evidence** (for example, `CH15_CONTAINER_ID`). Do not use the name or image tag as proof of ownership. Do not mistake a successful container launch for a healthy database.

## 5. Create synthetic roles and databases (lab-only writes)

Copy the tracked setup script into the **named container**, then execute with stop-on-error:

```bash
docker cp postgresql/postgresql-dbre-sre-enterprise-learning-path/labs/chapter-15/setup.sql pg-fleet-ch15:/tmp/ch15-setup.sql
docker exec pg-fleet-ch15 psql -X -v ON_ERROR_STOP=1 -U postgres -d postgres -f /tmp/ch15-setup.sql
```

The script creates two `NOLOGIN` owner roles and two databases **only when absent**, then creates two synthetic tables and seed rows. `\gexec` is a `psql` meta-command; do not run this script via a generic SQL driver. It must never be pointed at a shared or production PostgreSQL server.

**Expected:** `CREATE ROLE`, `CREATE DATABASE`, `CREATE SCHEMA`, `CREATE TABLE`, `INSERT 0 2` on first run; reruns may show NOTICE for already-existing objects and `INSERT 0 0`. No real patient, customer, or company data is used.

## 6. Read-only inventory collection

```bash
docker cp postgresql/postgresql-dbre-sre-enterprise-learning-path/labs/chapter-15/inventory.sql pg-fleet-ch15:/tmp/ch15-inventory.sql
docker exec pg-fleet-ch15 psql -X -v ON_ERROR_STOP=1 -U postgres -d postgres -f /tmp/ch15-inventory.sql
```

**Expected observations (not actual run evidence):**

- Server version begins `17.`; `pg_is_in_recovery()` is `f` for this standalone primary.
- `fleet_lab_app` and `fleet_lab_reporting` appear with `fleet_lab_app_owner` and `fleet_lab_reporting_owner` as **database role owners**.
- The two owner roles have `rolcanlogin=f` and `rolsuper=f`.
- `pg_settings` shows values, units, source and `pending_restart`. These are session-visible settings, not proof of a fleet-wide policy.
- `pg_stat_database` counters and database sizes are environment- and timing-dependent; do not assert exact numbers.
- The timestamp is an observation timestamp. `pg_control_system()` reports a local PostgreSQL system identifier; do not publish it as a secret-free globally unique enterprise asset key without a governance mapping.

**Important:** The SQL intentionally avoids passwords, `pg_authid`, query text, network endpoints, and personally identifying data. In a real collector, require a dedicated least-privilege role and validate visibility before deployment. This lab uses the container administrator only to simplify isolated setup.

## 7. Compare with an illustrative policy (no config changes)

```bash
docker cp postgresql/postgresql-dbre-sre-enterprise-learning-path/labs/chapter-15/drift.sql pg-fleet-ch15:/tmp/ch15-drift.sql
docker exec pg-fleet-ch15 psql -X -v ON_ERROR_STOP=1 -U postgres -d postgres -f /tmp/ch15-drift.sql
```

The lab's synthetic baseline expects `max_connections=200` to intentionally demonstrate a mismatch against the stock image default (often 100); other sample values are `wal_level=replica` and `password_encryption=scram-sha-256`. If the image or environment differs, **interpret actual values**; do not hardcode pass/fail based on the example.

Example (illustrative):

```text
name                 observed       expected         finding
max_connections      100            200              REVIEW
password_encryption  scram-sha-256  scram-sha-256    MATCH
wal_level            replica        replica          MATCH
```

`REVIEW` means **policy comparison**, not a recommendation to increase connections. No `ALTER SYSTEM`, `SET`, or restart occurs.

## 8. Owner attestation exercise (manual, no secrets)

Copy and fill this **synthetic** record in your training notes:

```yaml
fleet_asset_id: TRAINING-CH15-LOCAL-01
platform: local-docker
environment: disposable-training
database: fleet_lab_app
postgres_role_owner: fleet_lab_app_owner
business_owner: example-application-team  # NOT discovered from SQL
dbre_owner: example-dbre-team              # NOT discovered from SQL
classification: synthetic-public
rpo_target: not-established
rto_target: not-established
backup_restore_verified: false
observed_at: <UTC timestamp of your query>
baseline_version: training-v1
drift: REVIEW
exception_ticket: TRAINING-EXCEPTION-001
exception_owner: example-dbre-team
exception_expires_at: <training date>
evidence: <local sanitized SQL output location>
```

Explain in two sentences why a database authorization role is not a business owner, and why an RPO/RTO target cannot be inferred from the existence of a database. The `TRAINING-` identifiers are not production ticket numbers.

## 9. Optional platform discovery (not required; no provisioning)

Only with existing permission and **after checking account/cluster context**:

```bash
# AWS CLI v2; read-only, may produce API audit records.
aws sts get-caller-identity
aws rds describe-db-instances --region YOUR_REGION --query 'DBInstances[?Engine==`postgres`].[DBInstanceIdentifier,EngineVersion,DBInstanceStatus]' --output table

# Only if an authorized Kubernetes context and CloudNativePG CRD already exist.
kubectl config current-context
kubectl get clusters.postgresql.cnpg.io -A
```

No AWS or Kubernetes access is assumed. Do not create cloud resources, deploy an operator, enumerate Kubernetes Secrets, or infer missing objects mean no databases exist.

## 10. Troubleshooting

| Symptom | Safe response |
|---|---|
| Docker daemon unavailable | Start Docker Desktop/Engine; check `docker info`; do not change managed host settings without IT approval |
| Port 55415 busy | Use another localhost port; do not stop unrelated processes |
| Container exists | Inspect `docker inspect pg-fleet-ch15`; do not overwrite a resource of unknown origin |
| `pg_isready` fails | Wait for initialization, inspect `docker logs pg-fleet-ch15` (redact before sharing) |
| `psql: error` during setup | Confirm `-d postgres`, file copied, and `psql` client inside container; use `ON_ERROR_STOP` |
| `\gexec` syntax error | Use `psql -f`, not a SQL-only executor |
| Different config values | Capture `source` and actual image version; treat policy as synthetic |
| No rows for app databases | Re-run setup after confirming correct isolated container |
| Permission denied for system identifier | Admin-only function; omit in least-privilege inventory or use approved collector privileges |
| `docker volume rm` reports in use | Container still references it; do not force-delete unrelated resources |

## 11. Safe cleanup / rollback

 and `docker volume ls --filter name=^pg-fleet-ch15-data# Chapter 15 Lab — Fleet Inventory and Governance

**Duration:** 60 minutes (includes lecture and lab); practical exercises approximately 25–35 minutes.  
**Status:** Authored, **not executed**; expected results are illustrative, not evidence.  
**Related lesson:** [Chapter 15 — Fleet Inventory and Governance](../../chapters/15-fleet-inventory-and-governance.md)

## 1. Prerequisites and platform assumptions

- Docker Desktop/Engine with Linux containers; `docker version` and `docker info` must succeed. Tested command *design* for Bash and PowerShell; commands have **not** been executed as part of publication.
- PostgreSQL **17** official image (`postgres:17`); Docker may pull image bytes over the network. Prefer an approved, pinned digest in controlled environments.
- At least ~1 GB free disk and enough RAM for one small container. All data is synthetic.
- Run from the **repository root** so paths beginning `postgresql/postgresql-dbre-sre-enterprise-learning-path/` resolve.
- Port **55415** is used on `127.0.0.1` only; change it if occupied.
- No AWS credentials, Kubernetes cluster, production PostgreSQL endpoint, or paid resources required.

**Safety boundary:** never replace the container name or SQL target with a production host. `docker rm` and `docker volume rm` are destructive for their named resources. Use only the lab identifiers below and inspect before removal.

## 2. Teaching plan (60 minutes)

| Time | Activity | Evidence |
|---|---|---|
| 0–10 min | Explain fleet identity and data ownership | Sketch of cluster/database/service mapping |
| 10–20 min | Launch isolated PostgreSQL and create synthetic assets | Version and database list |
| 20–35 min | Capture read-only inventory | Timestamped SQL output |
| 35–45 min | Compare illustrative configuration policy | MATCH/REVIEW findings |
| 45–53 min | Enrich with human owner attestation | Synthetic governance record |
| 53–60 min | Review limitations, troubleshoot, clean up | Acceptance checklist |

## 3. Architecture and lab identifiers

```text
Your terminal (Bash or PowerShell)
   |
   | docker cp / docker exec psql
   v
Docker container: pg-fleet-ch15
   |-- PostgreSQL 17 (single instance, NOT HA)
   |-- postgres (administrative database)
   |-- fleet_lab_app (synthetic app database)
   |-- fleet_lab_reporting (synthetic reporting database)
   '-- Docker named volume: pg-fleet-ch15-data
```

This is **one PostgreSQL cluster with two application databases**, not two independent fleet members. The lab demonstrates the inventory unit of observation and why a second, owner-attested record is needed. No replicas, backup or TLS certification are implied.

## 4. Start the isolated instance

From a terminal at the repository root:

```bash
docker version
docker info --format '{{.OSType}}'
docker ps -a --filter name=^/pg-fleet-ch15$
docker volume ls --filter name=^pg-fleet-ch15-data$
```

**Stop if either lab name already exists**: inspect it and confirm provenance; do not overwrite or delete an unrelated resource. Only if neither exists:

```bash
docker volume create pg-fleet-ch15-data
docker run -d --name pg-fleet-ch15 \
  --label training.postgresql.chapter=15 \
  -e POSTGRES_PASSWORD=training_only_change_me \
  -e POSTGRES_DB=postgres \
  -p 127.0.0.1:55415:5432 \
  -v pg-fleet-ch15-data:/var/lib/postgresql/data \
  postgres:17
```

**PowerShell:** the multi-line `docker run` above uses Bash continuations; enter it as a **single line** in PowerShell:

```powershell
docker run -d --name pg-fleet-ch15 --label training.postgresql.chapter=15 -e POSTGRES_PASSWORD=training_only_change_me -e POSTGRES_DB=postgres -p 127.0.0.1:55415:5432 -v pg-fleet-ch15-data:/var/lib/postgresql/data postgres:17
```

The password is a public training-only placeholder; do not reuse it. For a controlled environment use an approved secret injection method. The port is loopback-bound, but local machine users may still access it.

Wait until ready (repeat if necessary):

```bash
docker exec pg-fleet-ch15 pg_isready -U postgres -d postgres
docker exec pg-fleet-ch15 psql -U postgres -d postgres -Atc "SHOW server_version;"
```

**Expected:** `accepting connections` and a `17.x` version. First initialization may take several seconds. **Immediately save the full container ID returned by `docker run` in your private lab evidence** (for example, `CH15_CONTAINER_ID`). Do not use the name or image tag as proof of ownership. Do not mistake a successful container launch for a healthy database.

## 5. Create synthetic roles and databases (lab-only writes)

Copy the tracked setup script into the **named container**, then execute with stop-on-error:

```bash
docker cp postgresql/postgresql-dbre-sre-enterprise-learning-path/labs/chapter-15/setup.sql pg-fleet-ch15:/tmp/ch15-setup.sql
docker exec pg-fleet-ch15 psql -X -v ON_ERROR_STOP=1 -U postgres -d postgres -f /tmp/ch15-setup.sql
```

The script creates two `NOLOGIN` owner roles and two databases **only when absent**, then creates two synthetic tables and seed rows. `\gexec` is a `psql` meta-command; do not run this script via a generic SQL driver. It must never be pointed at a shared or production PostgreSQL server.

**Expected:** `CREATE ROLE`, `CREATE DATABASE`, `CREATE SCHEMA`, `CREATE TABLE`, `INSERT 0 2` on first run; reruns may show NOTICE for already-existing objects and `INSERT 0 0`. No real patient, customer, or company data is used.

## 6. Read-only inventory collection

```bash
docker cp postgresql/postgresql-dbre-sre-enterprise-learning-path/labs/chapter-15/inventory.sql pg-fleet-ch15:/tmp/ch15-inventory.sql
docker exec pg-fleet-ch15 psql -X -v ON_ERROR_STOP=1 -U postgres -d postgres -f /tmp/ch15-inventory.sql
```

**Expected observations (not actual run evidence):**

- Server version begins `17.`; `pg_is_in_recovery()` is `f` for this standalone primary.
- `fleet_lab_app` and `fleet_lab_reporting` appear with `fleet_lab_app_owner` and `fleet_lab_reporting_owner` as **database role owners**.
- The two owner roles have `rolcanlogin=f` and `rolsuper=f`.
- `pg_settings` shows values, units, source and `pending_restart`. These are session-visible settings, not proof of a fleet-wide policy.
- `pg_stat_database` counters and database sizes are environment- and timing-dependent; do not assert exact numbers.
- The timestamp is an observation timestamp. `pg_control_system()` reports a local PostgreSQL system identifier; do not publish it as a secret-free globally unique enterprise asset key without a governance mapping.

**Important:** The SQL intentionally avoids passwords, `pg_authid`, query text, network endpoints, and personally identifying data. In a real collector, require a dedicated least-privilege role and validate visibility before deployment. This lab uses the container administrator only to simplify isolated setup.

## 7. Compare with an illustrative policy (no config changes)

```bash
docker cp postgresql/postgresql-dbre-sre-enterprise-learning-path/labs/chapter-15/drift.sql pg-fleet-ch15:/tmp/ch15-drift.sql
docker exec pg-fleet-ch15 psql -X -v ON_ERROR_STOP=1 -U postgres -d postgres -f /tmp/ch15-drift.sql
```

The lab's synthetic baseline expects `max_connections=200` to intentionally demonstrate a mismatch against the stock image default (often 100); other sample values are `wal_level=replica` and `password_encryption=scram-sha-256`. If the image or environment differs, **interpret actual values**; do not hardcode pass/fail based on the example.

Example (illustrative):

```text
name                 observed       expected         finding
max_connections      100            200              REVIEW
password_encryption  scram-sha-256  scram-sha-256    MATCH
wal_level            replica        replica          MATCH
```

`REVIEW` means **policy comparison**, not a recommendation to increase connections. No `ALTER SYSTEM`, `SET`, or restart occurs.

## 8. Owner attestation exercise (manual, no secrets)

Copy and fill this **synthetic** record in your training notes:

```yaml
fleet_asset_id: TRAINING-CH15-LOCAL-01
platform: local-docker
environment: disposable-training
database: fleet_lab_app
postgres_role_owner: fleet_lab_app_owner
business_owner: example-application-team  # NOT discovered from SQL
dbre_owner: example-dbre-team              # NOT discovered from SQL
classification: synthetic-public
rpo_target: not-established
rto_target: not-established
backup_restore_verified: false
observed_at: <UTC timestamp of your query>
baseline_version: training-v1
drift: REVIEW
exception_ticket: TRAINING-EXCEPTION-001
exception_owner: example-dbre-team
exception_expires_at: <training date>
evidence: <local sanitized SQL output location>
```

Explain in two sentences why a database authorization role is not a business owner, and why an RPO/RTO target cannot be inferred from the existence of a database. The `TRAINING-` identifiers are not production ticket numbers.

## 9. Optional platform discovery (not required; no provisioning)

Only with existing permission and **after checking account/cluster context**:

```bash
# AWS CLI v2; read-only, may produce API audit records.
aws sts get-caller-identity
aws rds describe-db-instances --region YOUR_REGION --query 'DBInstances[?Engine==`postgres`].[DBInstanceIdentifier,EngineVersion,DBInstanceStatus]' --output table

# Only if an authorized Kubernetes context and CloudNativePG CRD already exist.
kubectl config current-context
kubectl get clusters.postgresql.cnpg.io -A
```

No AWS or Kubernetes access is assumed. Do not create cloud resources, deploy an operator, enumerate Kubernetes Secrets, or infer missing objects mean no databases exist.

## 10. Troubleshooting

| Symptom | Safe response |
|---|---|
| Docker daemon unavailable | Start Docker Desktop/Engine; check `docker info`; do not change managed host settings without IT approval |
| Port 55415 busy | Use another localhost port; do not stop unrelated processes |
| Container exists | Inspect `docker inspect pg-fleet-ch15`; do not overwrite a resource of unknown origin |
| `pg_isready` fails | Wait for initialization, inspect `docker logs pg-fleet-ch15` (redact before sharing) |
| `psql: error` during setup | Confirm `-d postgres`, file copied, and `psql` client inside container; use `ON_ERROR_STOP` |
| `\gexec` syntax error | Use `psql -f`, not a SQL-only executor |
| Different config values | Capture `source` and actual image version; treat policy as synthetic |
| No rows for app databases | Re-run setup after confirming correct isolated container |
| Permission denied for system identifier | Admin-only function; omit in least-privilege inventory or use approved collector privileges |
| `docker volume rm` reports in use | Container still references it; do not force-delete unrelated resources |

## 11. Safe cleanup / rollback

. A failed deletion is not cleanup proof.

If provenance differs or either name is unfamiliar, **stop and investigate**. There is no production rollback in this exercise because no production changes are authorized.

## 12. Acceptance checklist and evidence discipline

- [ ] Recorded Docker/PG versions and verified loopback-only port binding.
- [ ] Created two synthetic databases in one disposable cluster.
- [ ] Captured version, recovery state, database owner role, sizes, settings and roles.
- [ ] Explained why the cluster is one fleet asset, not two.
- [ ] Demonstrated at least one synthetic policy `REVIEW` without altering server config.
- [ ] Filled an owner-attestation and exception record, marking unknown RPO/RTO explicitly.
- [ ] Avoided secrets, real customer data and production endpoints in output.
- [ ] Performed safe, identity-checked cleanup or documented why it was skipped.
- [ ] Saved sanitized actual evidence **only if commands were executed**; otherwise marked as not executed.
- [ ] Independent reviewer and production certification are recorded separately and remain pending unless supported by explicit evidence.

**Static authoring is not runtime verification.** No result shown here is a claimed observed run.

## Official references (checked 2026-11-02)

- [PostgreSQL 17 — System catalogs](https://www.postgresql.org/docs/17/catalogs.html)
- [PostgreSQL 17 — `pg_database`](https://www.postgresql.org/docs/17/catalog-pg-database.html)
- [PostgreSQL 17 — `pg_roles`](https://www.postgresql.org/docs/17/view-pg-roles.html)
- [PostgreSQL 17 — `pg_settings`](https://www.postgresql.org/docs/17/view-pg-settings.html)
- [PostgreSQL 17 — Statistics](https://www.postgresql.org/docs/17/monitoring-stats.html)
- [PostgreSQL 17 — `pg_control_system`](https://www.postgresql.org/docs/17/functions-info.html)
- [Docker Official PostgreSQL image](https://hub.docker.com/_/postgres)
- [AWS CLI v2 — RDS describe-db-instances](https://docs.aws.amazon.com/cli/latest/reference/rds/describe-db-instances.html)
- [CloudNativePG](https://cloudnative-pg.io/docs/)
