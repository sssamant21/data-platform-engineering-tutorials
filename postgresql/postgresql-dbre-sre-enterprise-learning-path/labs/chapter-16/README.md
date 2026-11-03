# Chapter 16 Lab — Least-Privilege Roles and Security Evidence

**Platform:** Docker Desktop/Engine with Linux containers; official `postgres:17` image; Docker CLI. **Time:** 30–35 minutes within the 60-minute lesson. **Cost:** local only. **Runtime status:** instructions authored, not executed. No AWS, Kubernetes or production access required.

## Prerequisites and safety
Use an isolated workstation with Docker running. The lab uses a disposable container named `pg-dbre-ch16`, no published TCP ports, and synthetic rows only. Commands are Bash-compatible (Git Bash or WSL on Windows). Confirm the container name is unused before proceeding. Never reuse a production Docker context. The lab's bootstrap password is a **local disposable placeholder** used only for a container without published ports; replace it for any networked deployment.

## 1. Start isolated PostgreSQL
```bash
docker context show
docker ps -a --filter name='^/pg-dbre-ch16$'
# Continue only if no container with this name exists.
docker run -d --name pg-dbre-ch16 -e POSTGRES_PASSWORD=local_lab_only_change_me postgres:17
docker exec pg-dbre-ch16 pg_isready -U postgres
docker exec -i pg-dbre-ch16 psql -U postgres -v ON_ERROR_STOP=1 -d postgres <<'SQL'
CREATE ROLE ch16_owner NOLOGIN;
CREATE ROLE ch16_reader NOLOGIN;
CREATE ROLE ch16_writer NOLOGIN;
CREATE ROLE ch16_login LOGIN;
GRANT ch16_reader TO ch16_login;
CREATE SCHEMA ch16_demo AUTHORIZATION ch16_owner;
REVOKE ALL ON SCHEMA ch16_demo FROM PUBLIC;
GRANT USAGE ON SCHEMA ch16_demo TO ch16_reader, ch16_writer;
SET ROLE ch16_owner;
CREATE TABLE ch16_demo.tickets (id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY, title text NOT NULL);
INSERT INTO ch16_demo.tickets(title) VALUES ('synthetic ticket');
RESET ROLE;
GRANT SELECT ON ch16_demo.tickets TO ch16_reader;
GRANT SELECT, INSERT, UPDATE ON ch16_demo.tickets TO ch16_writer;
GRANT USAGE ON SEQUENCE ch16_demo.tickets_id_seq TO ch16_writer;
ALTER DEFAULT PRIVILEGES FOR ROLE ch16_owner IN SCHEMA ch16_demo GRANT SELECT ON TABLES TO ch16_reader;
SQL
```
Expected: `pg_isready` reports accepting connections, setup exits 0. If a setup statement fails, stop and use cleanup rather than rerunning blindly; role/schema creation is intentionally non-idempotent within the disposable container.

## 2. Positive and negative authorization checks
```bash
docker exec -i pg-dbre-ch16 psql -U postgres -v ON_ERROR_STOP=1 -d postgres <<'SQL'
SET ROLE ch16_login;
SELECT current_user, count(*) FROM ch16_demo.tickets GROUP BY current_user;
RESET ROLE;
SELECT rolname, rolcanlogin, rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls FROM pg_roles WHERE rolname LIKE 'ch16_%' ORDER BY 1;
SQL
# Expected denial: psql must exit nonzero; capture status without masking it.
docker exec -i pg-dbre-ch16 psql -U postgres -v ON_ERROR_STOP=1 -d postgres <<'SQL'
SET ROLE ch16_login;
INSERT INTO ch16_demo.tickets(title) VALUES ('must be denied');
SQL
echo "Previous INSERT should have failed with permission denied for table tickets"
```
Expected: reader sees one row; INSERT fails with permission denied. A negative test is **successful only when the intended statement is rejected**; do not treat a zero exit status as passing.

## 3. Grant scoped writer and verify
```bash
docker exec -i pg-dbre-ch16 psql -U postgres -v ON_ERROR_STOP=1 -d postgres <<'SQL'
GRANT ch16_writer TO ch16_login;
SET ROLE ch16_login;
INSERT INTO ch16_demo.tickets(title) VALUES ('synthetic writer check');
SELECT count(*) FROM ch16_demo.tickets;
RESET ROLE;
SELECT grantee, privilege_type FROM information_schema.role_table_grants
WHERE table_schema='ch16_demo' AND table_name='tickets'
ORDER BY grantee, privilege_type;
SQL
```
Expected: row count 2; runtime role has no superuser/CREATEDB/CREATEROLE/REPLICATION/BYPASSRLS flags. Note: this lab uses `SET ROLE` via the local administrative socket for repeatable privilege checks; it does **not** validate login passwords or network authentication.

## 4. Evidence and governance discussion
Record Docker image digest/version, SQL command outcomes, exact denial message, role flags, table grants, operator initials and date. Do not capture real secrets. Discuss: `pg_hba.conf` order, SCRAM, TLS verification, password rotation, audit logging policy, access-review cadence and break-glass access. These are **design exercises**, not implemented controls in this lab.

## Troubleshooting
- Container not ready: `docker logs pg-dbre-ch16`; retry `pg_isready`.
- Role/schema already exists: stop; inspect and clean up the **lab-only** container before retrying.
- `permission denied for schema`: check `GRANT USAGE ON SCHEMA`.
- INSERT unexpectedly succeeds before writer grant: inspect memberships, owner and session role; do not count the test as passed.
- `SET ROLE` fails: confirm initial connection uses local lab admin and `ch16_login` was created.

## Rollback and cleanup
Only after verifying the exact container name and that it contains no data you need:
```bash
docker ps -a --filter name='^/pg-dbre-ch16$'
docker rm -f pg-dbre-ch16
```
No host bind mounts or named volumes are created by these commands; the container's anonymous volume may remain after `docker rm -f`. Inspect `docker inspect pg-dbre-ch16` **before removal** if you need to identify its mounts; remove any leftover anonymous volume only after verifying its exact ID and that it belongs exclusively to this disposable lab. Do not use global Docker prune commands.

## Acceptance checklist
- [ ] Docker context and isolation checked.
- [ ] Initial SELECT returns one synthetic row.
- [ ] Reader INSERT rejected (nonzero exit).
- [ ] Writer INSERT succeeds and count becomes two.
- [ ] Role flags show no elevated runtime privileges.
- [ ] Privilege and membership evidence recorded.
- [ ] Cleanup verified; runtime evidence and independent review tracked separately.

## Official references
[PostgreSQL 17 roles](https://www.postgresql.org/docs/17/user-manag.html) · [GRANT](https://www.postgresql.org/docs/17/sql-grant.html) · [Privileges](https://www.postgresql.org/docs/17/ddl-priv.html) · [Client authentication](https://www.postgresql.org/docs/17/client-authentication.html) · [TLS](https://www.postgresql.org/docs/17/ssl-tcp.html)
