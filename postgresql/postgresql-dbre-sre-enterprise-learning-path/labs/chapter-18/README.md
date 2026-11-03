# Chapter 18 Lab — Capacity Baseline and Growth Forecast

**Status:** Authored, not executed or independently reviewed. **Safety:** local disposable PostgreSQL 17 only; no production/cloud access, no published ports, no paid resources.

## Prerequisites, platform and architecture
Docker Desktop running Linux containers, Docker CLI, PowerShell or bash, 2 GB free RAM and approximately 1 GB spare disk. Official `postgres:17` image; exact patch release depends on pull date. Architecture: host Docker CLI → isolated `pg-dbre-ch18` container → local PostgreSQL socket → synthetic `ch18_capacity` table. No external endpoint or persistent named volume.

## 60-minute outline
0–10 environment/identity; 10–20 create baseline; 20–30 size/statistics; 30–45 write growth and explain; 45–53 forecast/cost; 53–60 cleanup and evidence.

## 1. Verify identity and start
Run each line in PowerShell or bash. The first inspect should fail with `No such container`; if it succeeds, **STOP** and investigate, never replace the existing container.
```sh
docker info
docker container inspect pg-dbre-ch18
```
Only if the container does not exist:
```sh
docker run --name pg-dbre-ch18 -e POSTGRES_PASSWORD=ch18-disposable-only -d postgres:17
docker exec pg-dbre-ch18 pg_isready -U postgres
docker exec pg-dbre-ch18 psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c "SELECT current_database(), current_user, current_setting('server_version_num') AS version_num;"
docker inspect --format '{{.Image}}' pg-dbre-ch18
```
Expected: after startup, `accepting connections`, database/user `postgres`, version number starting `17`. If readiness fails immediately, retry after startup. Password is disposable; never reuse.

## 2. Create a synthetic workload
```sh
docker exec pg-dbre-ch18 psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c "CREATE TABLE ch18_capacity (id integer PRIMARY KEY, category integer NOT NULL, payload text NOT NULL); INSERT INTO ch18_capacity SELECT g, g % 20, repeat(md5(g::text), 8) FROM generate_series(1,10000) AS g; ANALYZE ch18_capacity;"
```
Expected: `CREATE TABLE`, `INSERT 0 10000`, `ANALYZE`. If the table already exists, stop and confirm container identity rather than dropping unknown data.

## 3. Record baseline sizes and counters
```sh
docker exec pg-dbre-ch18 psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c "SELECT pg_database_size(current_database()) AS database_bytes, pg_total_relation_size('ch18_capacity') AS total_table_bytes, pg_table_size('ch18_capacity') AS table_bytes, pg_indexes_size('ch18_capacity') AS index_bytes;"
docker exec pg-dbre-ch18 psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c "SELECT relname, n_live_tup, n_dead_tup, n_tup_ins, n_tup_upd FROM pg_stat_user_tables WHERE relname='ch18_capacity';"
docker exec pg-dbre-ch18 psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c "SELECT wal_bytes, wal_records FROM pg_stat_wal;"
```
Expected: nonzero byte counts; approximately 10,000 estimated live tuples after ANALYZE; cumulative WAL counters (not per-second rates). Save output with observation timestamps; do not interpret counters without two timestamps.

## 4. Generate additional writes and compare
```sh
docker exec pg-dbre-ch18 psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c "INSERT INTO ch18_capacity SELECT g, g % 20, repeat(md5(g::text), 8) FROM generate_series(10001,20000) AS g; UPDATE ch18_capacity SET category=category+1 WHERE id BETWEEN 1 AND 2000; ANALYZE ch18_capacity;"
docker exec pg-dbre-ch18 psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c "SELECT count(*) AS row_count, pg_total_relation_size('ch18_capacity') AS total_bytes, pg_indexes_size('ch18_capacity') AS index_bytes FROM ch18_capacity;"
docker exec pg-dbre-ch18 psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c "SELECT wal_bytes, wal_records FROM pg_stat_wal;"
docker exec pg-dbre-ch18 psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c "EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM ch18_capacity WHERE id BETWEEN 100 AND 110;"
```
Expected: `INSERT 0 10000`, `UPDATE 2000`, `ANALYZE`, row count **20000**; a plan and execution/buffer statistics. Exact bytes, WAL delta and query timings vary. Compare WAL counter difference with timestamps; this is a synthetic workload, not a production rate. `EXPLAIN ANALYZE` executes its statement; use SELECT only here.

## 5. Forecast and FinOps worksheet
Record measured lab values and separately compute this **illustrative enterprise scenario**:
- Current database footprint: 200 GiB; low/base/high growth: 4/8/12 GiB per week; horizon: 26 weeks.
- Forecast footprints: 304 / 408 / 512 GiB.
- For 30% *free* headroom: required allocations `forecast / 0.70` = approximately 435 / 583 / 732 GiB (round up).
- Separately estimate WAL, archive, backups, replicas and restore staging space; never add them blindly to a database-only metric without checking where each resides.
- Write a one-page decision: workload/SLO, forecast inputs, measured peak utilization, cost components, candidate optimization, risk, owner, evidence and rollback.

## 6. Cleanup / rollback
Only after verifying `docker inspect pg-dbre-ch18` identifies your lab container:
```sh
docker exec pg-dbre-ch18 psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c "DROP TABLE ch18_capacity;"
docker stop pg-dbre-ch18
docker rm pg-dbre-ch18
```
Expected: table removed, only `pg-dbre-ch18` stopped and removed. Do not run `docker system prune`, `docker volume prune`, `docker rm -f` against unknown resources or any production cleanup. If interrupted, inspect the named container before deciding whether to resume or clean up.

## Troubleshooting
- Docker daemon error: start local Docker Desktop; check `docker context show`.
- Container name exists: STOP; do not delete it to make the exercise pass.
- `pg_isready` fails: inspect `docker logs pg-dbre-ch18`; wait for initialization.
- SQL `relation already exists`: confirm identity and whether lab was already run; never silently overwrite.
- Statistics seem stale: PostgreSQL counters are cumulative/asynchronous; `ANALYZE` updates planner estimates but does not reset all counters.
- Query plan differs: record actual plan; timings depend on cache and machine.
- Disk space low: stop and inspect host/Docker storage; do not indiscriminately prune.

## Acceptance and evidence checklist
- [ ] Docker context, image ID and PostgreSQL version recorded.
- [ ] Synthetic row counts and before/after table/index/database sizes recorded.
- [ ] WAL counter values captured with timestamps and correctly interpreted.
- [ ] EXPLAIN output captured for bounded SELECT.
- [ ] Low/base/high forecast, free-space headroom and cost assumptions documented.
- [ ] Cleanup verified; no external resource touched.
- [ ] Runtime marked **not executed** until evidence exists; independent review remains separate.

## Official references
- [PostgreSQL 17 size functions](https://www.postgresql.org/docs/17/functions-admin.html#FUNCTIONS-ADMIN-DBSIZE)
- [PostgreSQL 17 monitoring](https://www.postgresql.org/docs/17/monitoring-stats.html)
- [PostgreSQL 17 EXPLAIN](https://www.postgresql.org/docs/17/sql-explain.html)
- [PostgreSQL 17 ANALYZE](https://www.postgresql.org/docs/17/sql-analyze.html)
- [Docker official PostgreSQL image](https://hub.docker.com/_/postgres)
