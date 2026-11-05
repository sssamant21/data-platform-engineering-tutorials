# Chapter 19 Lab — Requirements to PostgreSQL Design

**Status:** instructional only; not executed, not independently reviewed. **Duration:** 25 minutes hands-on within the 60-minute chapter. **Platform:** Docker Desktop/Engine with Linux containers, official `postgres:17` image, PostgreSQL 17, shell or PowerShell, ~1 GiB RAM. No AWS/Kubernetes access, paid services, or real patient data.

## Prerequisites and isolation

Docker daemon must be running; commands below use `docker` and `docker exec` and work in PowerShell or a POSIX shell. Use a unique container name `pg-dbre-ch19`; abort if it already exists rather than touching someone else's container. The lab intentionally does **not** publish a host port. Password is a local disposable lab secret, not a production example.

~~~sh
docker version
docker container inspect pg-dbre-ch19
~~~

The second command **should fail with "No such container"** before proceeding. If it succeeds, stop and investigate ownership; do not overwrite or delete it.

## 1. Launch disposable PostgreSQL

~~~sh
docker run --name pg-dbre-ch19 --label training.postgresql.chapter=19 -e POSTGRES_PASSWORD=ch19-local-only -e POSTGRES_DB=design_lab -d postgres:17
docker exec pg-dbre-ch19 pg_isready -U postgres -d design_lab
docker exec pg-dbre-ch19 psql -U postgres -d design_lab -c "SELECT current_setting('server_version') AS version, current_database() AS db;"
~~~

Wait a few seconds and retry `pg_isready` if initialization is in progress. Expected: `accepting connections`, PostgreSQL version beginning with 17 and `design_lab`. Docker image pull requires network access and may consume local disk space.

## 2. Define schema and synthetic data

Execute this entire block in a shell that supports piping a heredoc (Linux/macOS/WSL/Git Bash). **PowerShell alternative:** save the SQL between `BEGIN;` and `COMMIT;` to a UTF-8 file `ch19.sql` and run `docker cp ch19.sql pg-dbre-ch19:/tmp/ch19.sql` followed by `docker exec pg-dbre-ch19 psql -X -v ON_ERROR_STOP=1 -U postgres -d design_lab -f /tmp/ch19.sql`.

~~~sh
docker exec -i pg-dbre-ch19 psql -X -v ON_ERROR_STOP=1 -U postgres -d design_lab <<'SQL'
BEGIN;
CREATE SCHEMA ch19;
CREATE TABLE ch19.patients (
  patient_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  external_id text NOT NULL UNIQUE,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE ch19.appointments (
  appointment_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  patient_id bigint NOT NULL REFERENCES ch19.patients(patient_id),
  scheduled_at timestamptz NOT NULL,
  status text NOT NULL CHECK (status IN ('scheduled','completed','cancelled'))
);
INSERT INTO ch19.patients (external_id)
SELECT 'synthetic-' || g FROM generate_series(1,1000) AS g;
INSERT INTO ch19.appointments (patient_id,scheduled_at,status)
SELECT (g % 1000)+1, now() + (g || ' hours')::interval, 'scheduled'
FROM generate_series(1,5000) AS g;
COMMIT;
SELECT (SELECT count(*) FROM ch19.patients) AS patients,
       (SELECT count(*) FROM ch19.appointments) AS appointments;
SQL
~~~

Expected counts: **1000 patients, 5000 appointments**. Re-running the setup intentionally fails on existing schema; it is not an idempotent migration. If partially applied, the enclosing transaction rolls back; do not drop shared objects.

## 3. Check invariants and query plans

~~~sh
docker exec pg-dbre-ch19 psql -X -v ON_ERROR_STOP=1 -U postgres -d design_lab -c "SELECT count(*) AS orphans FROM ch19.appointments a LEFT JOIN ch19.patients p USING(patient_id) WHERE p.patient_id IS NULL;"
docker exec pg-dbre-ch19 psql -X -v ON_ERROR_STOP=1 -U postgres -d design_lab -c "EXPLAIN (ANALYZE, BUFFERS) SELECT appointment_id,scheduled_at FROM ch19.appointments WHERE patient_id=42 ORDER BY scheduled_at LIMIT 10;"
docker exec pg-dbre-ch19 psql -X -v ON_ERROR_STOP=1 -U postgres -d design_lab -c "CREATE INDEX appointments_patient_time_idx ON ch19.appointments(patient_id,scheduled_at); ANALYZE ch19.appointments;"
docker exec pg-dbre-ch19 psql -X -v ON_ERROR_STOP=1 -U postgres -d design_lab -c "EXPLAIN (ANALYZE, BUFFERS) SELECT appointment_id,scheduled_at FROM ch19.appointments WHERE patient_id=42 ORDER BY scheduled_at LIMIT 10;"
~~~

Expected: `orphans=0`; query plan is valid before and after the index. Index Scan or Bitmap Index Scan may appear afterward, but planner choice is **not guaranteed** for this small synthetic dataset. Record costs, actual rows, execution time and buffers rather than asserting a speedup.

Negative constraint test (expected **error**, no persistent row):

~~~sh
docker exec pg-dbre-ch19 psql -X -U postgres -d design_lab -c "INSERT INTO ch19.appointments(patient_id,scheduled_at,status) VALUES (999999,now(),'scheduled');"
~~~

Expected: foreign-key violation SQLSTATE 23503; this command exits nonzero by design.

## 4. Requirement and design worksheet

Complete a short ADR: top three application queries; write frequency and burst assumptions; primary and foreign keys; indexes justified by access patterns; update and deletion policy; security classification; RPO/RTO owner and acceptance test; p95 budget; pool size assumptions; alternative designs; migration/rollback; monitoring; unresolved questions. Mark every hypothetical SLO as **unapproved** until owner confirmation.

## 5. Troubleshooting and guardrails

- `Cannot connect to Docker daemon`: start Docker Desktop/Engine; do not change production host settings.
- `container name already in use`: stop; investigate; never delete an unknown container.
- `database system is starting up`: wait and retry readiness.
- `relation already exists`: setup was already run; use a fresh, uniquely named disposable lab instance rather than modifying shared data.
- `permission denied`: verify commands run only against the isolated lab as `postgres`.
- Sequential scan after index: expected possibility; do not disable planner features to force a preferred output.
- Do not use real PII/PHI, cloud credentials, public port mappings, production backups, or external endpoints.

## 6. Cleanup / rollback

Verify target identity before deleting anything:

~~~sh
docker inspect --format '{{.Name}} {{.Config.Image}} {{index .Config.Labels "training.postgresql.chapter"}} {{.Id}}' pg-dbre-ch19
~~~

Expected: `/pg-dbre-ch19 postgres:17 19 <container-ID>`. Before cleanup, compare the full container ID with the ID returned by your own `docker run`, verify the chapter label is `19`, and confirm there are no unexpected mounts or resources attached (`docker inspect pg-dbre-ch19`; redact secrets from any retained output). **Name, image tag and label alone do not prove ownership.** If the ID is unavailable or differs, stop and retain the container for investigation. **Only after verifying this is the exact disposable container created for this run**, remove it and its anonymous data volume:

~~~sh
docker rm -f -v pg-dbre-ch19
~~~

The container removal is destructive to its lab data. If you need evidence, capture output first. If retaining the container, omit cleanup and document its owner.

## Acceptance and evidence

- [ ] Docker/PostgreSQL versions captured
- [ ] 1000/5000 row counts recorded
- [ ] Orphan count = 0
- [ ] Foreign-key violation observed without persisted invalid data
- [ ] Before/after plans captured without claiming guaranteed acceleration
- [ ] ADR and unresolved stakeholder questions written
- [ ] Cleanup performed or retained-resource owner documented
- [ ] Runtime status recorded accurately (not executed until actually run)
- [ ] Independent review still pending

## Official references

- [PostgreSQL 17 — CREATE TABLE](https://www.postgresql.org/docs/17/sql-createtable.html)
- [PostgreSQL 17 — Constraints](https://www.postgresql.org/docs/17/ddl-constraints.html)
- [PostgreSQL 17 — EXPLAIN](https://www.postgresql.org/docs/17/sql-explain.html)
- [PostgreSQL 17 — CREATE INDEX](https://www.postgresql.org/docs/17/sql-createindex.html)
- [Docker — docker container run](https://docs.docker.com/reference/cli/docker/container/run/)
