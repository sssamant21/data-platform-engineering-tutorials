# Chapter 17 Lab — Version Inventory and Reversible Schema Change

**Safety:** disposable local Docker PostgreSQL 17 only. No cloud account, cluster or production database required. **Status:** instructions authored; not executed.

## Prerequisites and assumptions
Docker Desktop running Linux containers, Docker CLI, PowerShell or bash, 2 GB free memory. Commands use `docker` and `psql` inside the official `postgres:17` container. Docker may pull an image from the internet. Container name `pg-dbre-ch17` is reserved for this lab. Do not overwrite a container with that name; stop if it already exists.

## 60-minute outline
0–10 prerequisites and lifecycle; 10–20 version inventory; 20–30 schema change design; 30–45 execute and verify; 45–55 rollback/cleanup; 55–60 acceptance and change record.

## Architecture
Docker container → isolated PostgreSQL 17 instance → synthetic `lifecycle_lab` table. No host port is published. Commands are run with `docker exec`, not against a remote endpoint. Data is disposable.

## Setup and identity checks
Run in PowerShell or bash:

```sh
docker info
docker container inspect pg-dbre-ch17
```

The inspect command **should fail with No such container**. If it succeeds, STOP: investigate the existing container and do not replace it.

```sh
docker run --name pg-dbre-ch17 -e POSTGRES_PASSWORD=local-only-example -d postgres:17
docker exec pg-dbre-ch17 pg_isready -U postgres
docker exec pg-dbre-ch17 psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c "SELECT current_database(), current_user, current_setting('server_version_num') AS version_num;"
```

Expected: `accepting connections`, database `postgres`, user `postgres`, version number beginning with `17`. If startup is still in progress, retry readiness after a short wait. The example password is disposable and must never be reused.

## Version and extension inventory
```sh
docker exec pg-dbre-ch17 psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c "SHOW server_version;"
docker exec pg-dbre-ch17 psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c "SELECT extname, extversion FROM pg_extension ORDER BY 1;"
docker exec pg-dbre-ch17 psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c "SELECT datname FROM pg_database WHERE datallowconn ORDER BY 1;"
```

Expected: PostgreSQL 17.x; `plpgsql` typically installed; connectable databases listed. Exact patch version varies with image pull date.

## Reversible migration (lab-only)
```sh
docker exec pg-dbre-ch17 psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c "CREATE TABLE lifecycle_lab (id integer PRIMARY KEY, note text NOT NULL); INSERT INTO lifecycle_lab VALUES (1, 'before');"
docker exec pg-dbre-ch17 psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c "BEGIN; SET LOCAL lock_timeout = '3s'; ALTER TABLE lifecycle_lab ADD COLUMN status text DEFAULT 'new'; COMMIT;"
docker exec pg-dbre-ch17 psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c "SELECT id, note, status FROM lifecycle_lab;"
```

Expected: one row `1 | before | new`. Record the output as evidence. The added column is backward-compatible with this synthetic query, but that does not prove application compatibility.

## Rollback and cleanup
```sh
docker exec pg-dbre-ch17 psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c "BEGIN; SET LOCAL lock_timeout = '3s'; ALTER TABLE lifecycle_lab DROP COLUMN status; COMMIT;"
docker exec pg-dbre-ch17 psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c "SELECT id, note FROM lifecycle_lab;"
docker exec pg-dbre-ch17 psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c "DROP TABLE lifecycle_lab;"
docker stop pg-dbre-ch17
docker rm -v pg-dbre-ch17
```

Expected: original two columns restored; table removed; only the specifically named lab container and its anonymous volume(s) removed. Verify container identity and mounts before cleanup; `-v` does not delete named volumes. Never use `docker system prune`, `docker volume prune` or broad deletion commands. This lab does not execute a PostgreSQL major upgrade or restore exercise.

## Troubleshooting
- `Cannot connect to Docker daemon`: start Docker Desktop; confirm Linux engine.
- Container name conflict: stop and inspect; do not delete an unknown container.
- `pg_isready` fails: inspect `docker logs pg-dbre-ch17`; retry after startup.
- `relation already exists`: confirm you are on the intended disposable container; do not drop external objects.
- Lock timeout: rollback is automatic for the failed statement; inspect active sessions before retrying.
- SQL errors: `ON_ERROR_STOP=1` ensures command failure is visible; do not treat failed steps as passed.

## Acceptance and evidence
- [ ] Record Docker image identifier and PostgreSQL version.
- [ ] Confirm database/user identity.
- [ ] Save extension inventory and baseline table output.
- [ ] Verify added column and expected row.
- [ ] Verify rollback to original columns and explicit cleanup.
- [ ] Write a one-page change plan: prechecks, backup/restore proof required, upgrade strategy, application tests, abort criteria, recovery owner and independent approval.
- [ ] Record runtime status as **not executed** until actual evidence exists.

## Official references
[Versioning](https://www.postgresql.org/support/versioning/) · [Upgrading](https://www.postgresql.org/docs/17/upgrading.html) · [ALTER TABLE](https://www.postgresql.org/docs/17/sql-altertable.html) · [Docker official PostgreSQL image](https://hub.docker.com/_/postgres)
