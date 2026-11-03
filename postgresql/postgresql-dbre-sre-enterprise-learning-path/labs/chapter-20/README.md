# Chapter 20 — Enterprise DBRE/SRE Capstone Lab

**Status:** Authored only; commands have not been executed in this publication run. **Duration:** 60 minutes including the [lesson](../../chapters/20-enterprise-postgresql-dbre-sre-capstone.md).

## Prerequisites / safety
Docker Engine/Desktop, Docker CLI, PostgreSQL 17 image, terminal (POSIX shell/Git Bash/WSL). Use only a disposable local environment. No host port is published. Never substitute a real database or reuse an existing named container. No AWS/Kubernetes resources or costs are involved. Do not paste real patient information.

## 1. Launch isolated database (10 minutes)
```sh
docker info
docker container inspect pg-dbre-capstone20 >/dev/null 2>&1 && { echo "Container name already exists: stop and investigate"; exit 1; }
docker run -d --name pg-dbre-capstone20 -e POSTGRES_PASSWORD=local_training_only -e POSTGRES_DB=capstone --health-cmd='pg_isready -U postgres -d capstone' --health-interval=5s --health-retries=12 postgres:17
docker exec pg-dbre-capstone20 pg_isready -U postgres -d capstone
```
Expected: container ID, then `accepting connections` after initialization (retry the last command if needed). Password is synthetic and not suitable for a real deployment.

## 2. Build integrity and workload (15 minutes)
```sh
docker exec -i pg-dbre-capstone20 psql -v ON_ERROR_STOP=1 -U postgres -d capstone <<'SQL'
CREATE SCHEMA capstone_lab;
CREATE TABLE capstone_lab.patient (
  patient_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  external_ref text UNIQUE NOT NULL
);
CREATE TABLE capstone_lab.appointment (
  appointment_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  patient_id bigint NOT NULL REFERENCES capstone_lab.patient(patient_id),
  scheduled_at timestamptz NOT NULL,
  status text NOT NULL CHECK (status IN ('scheduled','cancelled'))
);
INSERT INTO capstone_lab.patient(external_ref)
SELECT 'synthetic-' || n FROM generate_series(1,1000) AS n;
INSERT INTO capstone_lab.appointment(patient_id,scheduled_at,status)
SELECT (n % 1000)+1, now() + (n || ' hours')::interval, 'scheduled'
FROM generate_series(1,5000) AS n;
CREATE INDEX appointment_patient_time_idx ON capstone_lab.appointment(patient_id,scheduled_at);
BEGIN;
UPDATE capstone_lab.appointment SET status='cancelled' WHERE appointment_id=1;
ROLLBACK;
SELECT count(*) AS patients FROM capstone_lab.patient;
SELECT count(*) AS appointments FROM capstone_lab.appointment;
SELECT status FROM capstone_lab.appointment WHERE appointment_id=1;
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM capstone_lab.appointment WHERE patient_id=42 ORDER BY scheduled_at LIMIT 10;
SQL
```
Expected: 1,000 patients, 5,000 appointments, `scheduled` for appointment 1 after rollback. EXPLAIN plan and timing vary; index use is not guaranteed on small datasets.

## 3. Capture operational evidence (10 minutes)
```sh
docker exec -i pg-dbre-capstone20 psql -v ON_ERROR_STOP=1 -U postgres -d capstone <<'SQL'
SELECT version();
SHOW max_connections;
SHOW wal_level;
SELECT pg_size_pretty(pg_database_size(current_database())) AS db_size;
SELECT datname,numbackends,xact_commit,xact_rollback FROM pg_stat_database WHERE datname=current_database();
SELECT schemaname,relname,n_live_tup,n_dead_tup FROM pg_stat_user_tables WHERE schemaname='capstone_lab';
SELECT count(*) AS fk_count FROM pg_constraint WHERE contype='f' AND connamespace='capstone_lab'::regnamespace;
SQL
```
Expected: PostgreSQL 17 version, configuration values, nonzero DB size, statistics (some counters lag), and one foreign key. Record actual output with timestamp and host/container image digest; do not fabricate results.

## 4. Design review tabletop (15 minutes)
Write a one-page ADR answering: why PostgreSQL; single-writer and standby topology; RACI; backup location and retention; isolation of restore tests; proposed RPO/RTO and how to measure them; fencing; TLS and secret rotation; capacity assumptions; p95 latency and availability SLO; maintenance and rollback. Mark all untested objectives **NOT VERIFIED**. Optional provider comparison: read AWS RDS/CloudNativePG documentation only; deployment requires a separately approved, potentially billable sandbox.

## 5. Acceptance and peer review (5 minutes)
- [ ] Disposable container name and version recorded
- [ ] Synthetic rows and rollback observed
- [ ] Constraints and query plan captured
- [ ] DB size and monitoring statistics captured
- [ ] ADR, RACI, risk register, security controls and proposed SLO documented
- [ ] Backup/PITR/failover/RPO/RTO marked **not tested**
- [ ] Reviewer, review date, and findings recorded (pending until performed)

## 6. Cleanup / rollback (5 minutes)
```sh
docker ps --filter name=pg-dbre-capstone20
# Only after verifying this is your own disposable training container:
docker rm -f pg-dbre-capstone20
```
No named volume or host port was created. The container's ephemeral database is removed. Do not use broad prune commands.

## Troubleshooting
- Docker daemon unavailable: start Docker Desktop/Engine; rerun `docker info`.
- Container still starting: `docker logs pg-dbre-capstone20`; retry `pg_isready`.
- Name conflict: inspect existing container; **do not overwrite it**.
- SQL error: use `-v ON_ERROR_STOP=1`; do not blindly rerun non-idempotent DDL. Remove only your confirmed disposable container and restart.
- Plan differs: planner choices depend on row counts/statistics; capture the observation rather than forcing a claim.

## References
[PostgreSQL 17 SQL](https://www.postgresql.org/docs/17/sql.html) · [EXPLAIN](https://www.postgresql.org/docs/17/using-explain.html) · [Statistics](https://www.postgresql.org/docs/17/monitoring-stats.html) · [Backup](https://www.postgresql.org/docs/17/backup.html) · [Docker official postgres image](https://hub.docker.com/_/postgres)
