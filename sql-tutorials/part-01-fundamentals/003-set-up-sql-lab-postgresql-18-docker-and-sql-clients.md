# Chapter 003 — Set Up the SQL Lab: PostgreSQL 18, Docker, and SQL Clients

> **Track:** [SQL Tutorials](../README.md) · [Master TOC](../MASTER-TOC.md) · Part 01  
> **Duration:** 60 minutes · **Audience:** Beginners, data engineers, DBRE/SRE  
> **Prerequisites:** [Chapter 002](002-relational-databases-and-dbms-architecture.md); Docker Desktop with Linux containers or Docker Engine with Compose v2  
> **Status:** Published instructional content; independent review and PostgreSQL 18 runtime acceptance **pending**.

## Learning objectives and time plan

| Segment | Minutes | Outcome |
|---|---:|---|
| Prerequisites and safety | 5 | Check Docker and host resources |
| Architecture and configuration | 10 | Explain image, container, volume, port, credentials |
| Start isolated PostgreSQL 18 | 15 | Bring up the lab and check server version |
| Connect with SQL clients | 10 | Use `psql` and optionally a GUI |
| Hands-on validation | 15 | Execute reproducible SQL and compare expected output |
| Troubleshooting and cleanup | 5 | Recover safely and preserve data |

This is a **local, disposable, synthetic-data-only lab**. Never reuse production passwords, hosts, backups, or datasets. The Compose service binds the database port to **127.0.0.1** rather than all interfaces. That is a host-network boundary, **not** a substitute for authentication or workstation security.

## 1. Architecture and requirements

```text
SQL editor / psql (Windows, macOS or Linux)
            |
     localhost:55432
            |
Docker port mapping 127.0.0.1:55432 -> 5432
            |
 PostgreSQL 18 container
            |
  sql_pg18_data named volume (persistent across restarts)
```

**Requirements:** Docker Engine/Desktop with Compose v2, Linux container mode, approximately 2 GB of available RAM for a small local lab, free disk space, and port 55432 available. These are teaching-lab suggestions, not PostgreSQL minimum specifications. Run:

```powershell
docker --version
docker compose version
docker info --format '{{.OSType}}'
```

Expected: valid Docker/Compose versions and `linux`. If `docker info` fails, start Docker Desktop and verify the daemon. On Windows, Docker Desktop may require WSL2 and the Virtual Machine Platform Windows feature; coordinate with IT on managed machines.

**Why these settings?**

| Setting | Purpose |
|---|---|
| `postgres:18` | PostgreSQL major version baseline; record the actual minor version at runtime |
| `127.0.0.1:55432:5432` | Host-local client access without exposing the database on the LAN |
| `POSTGRES_USER` | Dedicated lab superuser inside the container; **never** use for production applications |
| `POSTGRES_DB` | Database created only when the data directory is initialized |
| `POSTGRES_PASSWORD` | Password set at initial database initialization |
| Named volume | Keeps lab data through `docker compose down`; `down -v` deletes it |

**Security note:** The Docker official image initializes the named volume on first start. Changing `POSTGRES_USER`, `POSTGRES_DB`, or `POSTGRES_PASSWORD` later **does not** automatically update an already initialized database. Keep the password local, never commit it, and never paste it into issue reports or logs. Container-local `docker exec ... psql` commonly uses local socket authentication; that is **not** proof that host TCP password authentication works.

## 2. Get the lab files and configure a local secret

Files in this repository:

- [Compose configuration](../labs/docker/compose.yaml)
- [SQL verification script](../labs/003-lab-smoke-test.sql)
- [Lab troubleshooting checklist](../labs/docker/README.md)

If you cloned the repository, run from the repository root:

```powershell
cd sql-tutorials/labs/docker
```

Or download the three files from GitHub into their indicated relative locations. Do **not** put the secret in `compose.yaml` or Git.

**PowerShell (Windows):**

```powershell
$env:SQL_LAB_PASSWORD = Read-Host "Choose a unique local SQL lab password"
docker compose config --quiet
docker compose up -d
```

**Bash (Linux/macOS):**

```bash
read -r -s -p 'Choose a unique local SQL lab password: ' SQL_LAB_PASSWORD; echo
export SQL_LAB_PASSWORD
docker compose config --quiet
docker compose up -d
```

The environment variable is local to the current shell and child processes; it can be inspected by sufficiently privileged local processes. Use a **unique, disposable** lab password. The `docker compose config --quiet` step validates configuration without printing the interpolated secret. Avoid `docker compose config` without `--quiet` because it may display credentials.

**Check health:**

```powershell
docker compose ps
docker compose logs --tail=30 postgres
```

Expected: the `postgres` service is running and eventually healthy. The first initialization can take longer than subsequent starts. Logs must not be assumed to contain no sensitive information; review before sharing.

## 3. Connect with psql (inside the container)

From `sql-tutorials/labs/docker`:

```powershell
docker compose exec -T postgres psql -U sql_lab -d sql_tutorials -X -v ON_ERROR_STOP=1 -c "SELECT current_database(), current_user, current_setting('server_version');"
```

Expected: one row, database `sql_tutorials`, role `sql_lab`, and a server version beginning with `18`. The patch version is environment-dependent.

**Important:** `sql_lab` is the initialization superuser for this disposable lab. Later production-security chapters will use non-superuser, least-privilege roles. Never interpret a successful container-local socket login as a successful TCP/password login.

To check TCP password authentication without echoing a password in a command line, use a locally installed `psql` client:

```powershell
psql -h 127.0.0.1 -p 55432 -U sql_lab -d sql_tutorials -X -W -c "SELECT 1 AS connected;"
```

At the password prompt, enter your local lab password. Expected: `connected = 1`. If `psql` is not installed on the host, the in-container `psql` is sufficient for this chapter.

**GUI clients:** In pgAdmin, DBeaver, or another PostgreSQL-compatible SQL editor, create a **new** connection with host `127.0.0.1`, port `55432`, database `sql_tutorials`, user `sql_lab`, and the password you chose. Do not enable cloud sync for this disposable lab credential. Test the connection, then run `SELECT 1;`.

## 4. Hands-on lab: reproducible verification

From `sql-tutorials/labs/docker` execute the committed script using the container's psql client:

```powershell
docker compose exec -T postgres psql -U sql_lab -d sql_tutorials -X -v ON_ERROR_STOP=1 -f /dev/stdin < ../003-lab-smoke-test.sql
```

The above input redirection is **Bash syntax**, not PowerShell. On **PowerShell**, use:

```powershell
Get-Content ../003-lab-smoke-test.sql -Raw | docker compose exec -T postgres psql -U sql_lab -d sql_tutorials -X -v ON_ERROR_STOP=1 -f -
if ($LASTEXITCODE -ne 0) { throw "PostgreSQL smoke test failed: $LASTEXITCODE" }
```

On **Bash**, use:

```bash
docker compose exec -T postgres psql -U sql_lab -d sql_tutorials -X -v ON_ERROR_STOP=1 -f - < ../003-lab-smoke-test.sql
```

The script checks server major version, current database and role, and synthetic sales aggregation. It is **read-only**; it does not create or alter tables. Expected assertions:

| Check | Expected |
|---|---|
| Major version | 18 |
| Current database | `sql_tutorials` |
| Current user | `sql_lab` |
| Synthetic paid order count | 3 |
| Synthetic paid revenue | 220.00 |
| Final validation result | `PASS` |

**Acceptance criteria:** Docker container is healthy, the SQL file completes with exit code 0, every assertion returns the expected value, and no persistent business tables are created.

### Manual investigation queries

```sql
SELECT current_database() AS db,
       current_user AS role,
       current_setting('server_version') AS version;
SELECT datname FROM pg_database WHERE datname = 'sql_tutorials';
SELECT pg_backend_pid() AS my_session_pid;
```

These PostgreSQL-specific catalog/session checks are safe read-only operations. The exact process ID and patch version vary.

## 5. Troubleshooting and operational guardrails

| Symptom | Diagnostic | Resolution |
|---|---|---|
| Docker daemon unavailable | `docker info` | Start Docker Desktop; confirm Linux containers / WSL2 |
| Port 55432 already allocated | `docker compose ps` and host port tools | Stop conflicting **lab** service or choose another host-only port in Compose |
| Compose reports missing password | Inspect shell variable presence, **not its value** | Set `SQL_LAB_PASSWORD` in the same terminal and retry |
| Container unhealthy | `docker compose logs --tail=50 postgres` | Wait for initialization; inspect disk/memory availability |
| Host password rejected | Confirm `127.0.0.1:55432` and initialization history | Reuse the original password; do not assume editing the variable rotates it |
| Database or user differs | Existing named volume was initialized earlier | Use the actual initialized credentials or carefully recreate **only a disposable lab volume** |
| `psql` not found on host | `psql --version` | Use the in-container `docker compose exec` method |
| SQL exits nonzero | `ON_ERROR_STOP=1` and shell exit code | Inspect the first SQL error; do not mark runtime PASS |

**Cleanup (non-destructive):**

```powershell
docker compose down
```

This stops/removes the lab container and network but **retains** the named volume. To restart, set the same local password variable (Compose still requires it) and run `docker compose up -d`.

**Destructive reset (not part of normal lab):** `docker compose down -v` permanently deletes the lab's named volume and its database contents. Use only after verifying the Compose project and that no data needs to be retained. Never run it on production or shared environments.

## 6. Portability, DBRE/SRE review and knowledge check

The lab uses PostgreSQL-specific `current_setting`, `pg_database`, `pg_backend_pid`, and `psql` options. `SELECT`, `COUNT`, and `SUM` are broadly portable, but Docker image, metadata queries, casts, and client flags differ by platform.

**Review questions:**

1. Why bind port 55432 to `127.0.0.1`?
2. Does `docker compose down` delete the named volume?
3. Why can changing `POSTGRES_PASSWORD` fail to rotate an existing database password?
4. What does `ON_ERROR_STOP=1` change?
5. How would you confirm you are connected to PostgreSQL 18 rather than an older major version?

**Answers:** (1) Limits host port exposure to loopback. (2) No, unless the destructive `-v` option is supplied. (3) Initialization environment variables only initialize an empty data directory. (4) Causes `psql` to stop on a SQL error and report failure. (5) Query `current_setting('server_version')` or `server_version_num` on the connected server.

## 7. Next lesson and references

**Next:** Chapter 004 — Databases, Schemas, Tables, Rows, and Columns (to be published). Reuse this exact lab environment.

- [PostgreSQL 18 official documentation](https://www.postgresql.org/docs/18/)
- [PostgreSQL 18: psql](https://www.postgresql.org/docs/18/app-psql.html)
- [PostgreSQL 18: Server configuration](https://www.postgresql.org/docs/18/runtime-config.html)
- [Docker Official PostgreSQL image](https://hub.docker.com/_/postgres)
- [Docker Compose services reference](https://docs.docker.com/reference/compose-file/services/)

**Validation record:** Source reviewed for safe read-only SQL, deterministic expectations, host-loopback port binding, and cross-platform shell distinctions. **No actual PostgreSQL 18 execution evidence has been collected for this chapter**; runtime acceptance remains pending.
