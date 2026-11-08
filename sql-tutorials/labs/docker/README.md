# PostgreSQL 18 lab (Chapter 003)

This directory contains [Compose](compose.yaml) for a disposable, localhost-only PostgreSQL 18 instance.

From this directory, set a **unique** `SQL_LAB_PASSWORD` shell variable (do not commit or print it), then run `docker compose config --quiet` and `docker compose up -d`.

On PowerShell, test with:

```powershell
Get-Content ../003-lab-smoke-test.sql -Raw | docker compose exec -T postgres psql -U sql_lab -d sql_tutorials -X -v ON_ERROR_STOP=1 -f -
if ($LASTEXITCODE -ne 0) { throw "SQL smoke test failed" }
```

On Bash:

```bash
docker compose exec -T postgres psql -U sql_lab -d sql_tutorials -X -v ON_ERROR_STOP=1 -f - < ../003-lab-smoke-test.sql
```

Expected: `environment_assertion = 1`, `paid_count = 3`, `paid_revenue = 220.00`, `result = PASS`, and zero exit code.

`docker compose down` retains the named volume. **Never** use `docker compose down -v` without confirming the lab volume can be destroyed.

See [Chapter 003](../../part-01-fundamentals/003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md) for prerequisites, troubleshooting, client setup, and validation boundaries. **Runtime testing remains pending until an isolated PostgreSQL 18 run produces evidence.**
