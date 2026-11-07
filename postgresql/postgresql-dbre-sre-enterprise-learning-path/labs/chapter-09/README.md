# Chapter 09 Lab — Evidence-Based PostgreSQL Architecture Decision

**Course:** [Chapter 09 — Selecting the Right Enterprise PostgreSQL Architecture](../../chapters/09-selecting-the-right-enterprise-postgresql-architecture.md)  
**Duration:** 20 minutes guided SQL + 10 minutes ADR discussion (within a 60-minute chapter)  
**Environment:** Docker Desktop/Engine, disposable PostgreSQL 17 container from Chapter 01  
**Cost:** No AWS/Kubernetes resources required or created  
**Status:** Instructions authored; **not executed or independently verified**.

## 0. Safety, prerequisites and expected scope

- Use only the existing **disposable local** `pg-fleet-lab` container from [Chapter 01](../chapter-01/README.md). Do not use production credentials.
- This lab connects to the built-in `postgres` database and creates **session-local temporary objects only**. It does not change persistent application data or configuration.
- The candidate ratings, gates and workload assumptions are **fictional training data**. Do not reuse them as real approval or cost evidence.
- SQL examples target PostgreSQL 17. Other supported versions may behave similarly, but verify before adapting.
- If the Docker container does not exist, follow Chapter 01 setup. Do not start an unrelated existing container or overwrite a named volume.

**PowerShell preflight:**

```powershell
$ErrorActionPreference = 'Stop'
docker version
if ($LASTEXITCODE -ne 0) { throw 'Docker client/server unavailable' }
$context = docker context show
if ($LASTEXITCODE -ne 0) { throw 'Cannot determine Docker context' }
docker context inspect $context
if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect Docker endpoint' }
# Confirm manually that this endpoint is the approved local disposable engine.
# Compare the context and full ID with the Chapter 01 creation record.
$containerId = docker inspect --type container --format '{{.Id}}' pg-fleet-lab
if ($LASTEXITCODE -ne 0 -or -not $containerId) { throw 'Chapter 01 lab container missing' }
$owner = docker inspect --type container --format '{{index .Config.Labels "dbre.training"}}' pg-fleet-lab
if ($LASTEXITCODE -ne 0 -or $owner -ne 'postgresql-enterprise-ch01') { throw 'Unexpected lab ownership label' }
$image = docker inspect --type container --format '{{.Config.Image}}' pg-fleet-lab
if ($LASTEXITCODE -ne 0 -or $image -ne 'postgres:17') { throw 'Unexpected image; inspect before proceeding' }
$mount = docker inspect --type container --format '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}}{{end}}{{end}}' pg-fleet-lab
if ($LASTEXITCODE -ne 0 -or $mount -ne 'pg_fleet_data') { throw 'Unexpected data mount' }
Write-Host "Verify against Chapter 01 record: context=$context id=$containerId"
docker exec pg-fleet-lab pg_isready -U postgres
if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL not ready' }
$serverVersion = docker exec $containerId psql -X -v ON_ERROR_STOP=1 -U postgres -d postgres -Atc 'SHOW server_version_num;'
if ($LASTEXITCODE -ne 0 -or -not ($serverVersion -match '^17[0-9]{4}
```

Expected: Docker server available on the **manually verified local disposable context**, exact full container ID matching the Chapter 01 creation record, expected ownership label/image/data mount, successful readiness check, and PostgreSQL 17 server version number in the `170000`–`179999` range. **Stop** on any mismatch; a matching name or image tag alone does not prove ownership. The SQL exercises must not run until this preflight passes.

## 1. Connect and collect read-only baseline facts (3 minutes)

```powershell
docker exec -it $containerId psql -X -v ON_ERROR_STOP=1 -U postgres -d postgres
```

Inside the interactive `psql` session:

```sql
SELECT current_database(), current_user, pg_is_in_recovery();
SHOW server_version;
SHOW max_connections;
SHOW shared_buffers;
SHOW wal_level;
SELECT pg_size_pretty(pg_database_size(current_database())) AS database_size;
```

**Expected:** `current_database()` is `postgres`, `pg_is_in_recovery()` is `false` for the Chapter 01 standalone primary. Other settings/sizes vary. These values are **observations**, not production capacity or recovery certification.

## 2. Define the hypothetical workload and hard gates (3 minutes)

**Fictional scenario A:** an online order application with an approved AWS footprint, moderate writes, high-availability requirement, and a team familiar with RDS but not yet operationally ready to run a PostgreSQL operator.

**Important:** All gates below represent *hypothetical prior approval for teaching*. Real security, extension, residency, and operational gates require documented evidence and may remain `NULL` until verified.

Create a temporary weight table (100 points total) and a candidate table:

```sql
CREATE TEMP TABLE architecture_weights (
    reliability_weight INTEGER NOT NULL CHECK (reliability_weight >= 0),
    operations_weight INTEGER NOT NULL CHECK (operations_weight >= 0),
    performance_weight INTEGER NOT NULL CHECK (performance_weight >= 0),
    cost_weight INTEGER NOT NULL CHECK (cost_weight >= 0),
    portability_weight INTEGER NOT NULL CHECK (portability_weight >= 0),
    CHECK (
        reliability_weight + operations_weight + performance_weight
        + cost_weight + portability_weight = 100
    )
);

INSERT INTO architecture_weights VALUES (30, 25, 15, 20, 10);

CREATE TEMP TABLE architecture_candidates (
    platform TEXT PRIMARY KEY,
    residency_ok BOOLEAN,
    extension_ok BOOLEAN,
    team_ready BOOLEAN,
    security_ok BOOLEAN,
    reliability_score INTEGER CHECK (reliability_score BETWEEN 1 AND 5),
    operations_score INTEGER CHECK (operations_score BETWEEN 1 AND 5),
    performance_score INTEGER CHECK (performance_score BETWEEN 1 AND 5),
    cost_score INTEGER CHECK (cost_score BETWEEN 1 AND 5),
    portability_score INTEGER CHECK (portability_score BETWEEN 1 AND 5)
);

INSERT INTO architecture_candidates VALUES
    ('Bare metal / VM',          TRUE, TRUE, TRUE,  TRUE, 4, 2, 3, 3, 5),
    ('RDS Multi-AZ instance',    TRUE, TRUE, TRUE,  TRUE, 4, 5, 3, 4, 2),
    ('RDS Multi-AZ cluster',     TRUE, TRUE, TRUE,  TRUE, 5, 4, 4, 2, 2),
    ('Kubernetes CNPG',         TRUE, TRUE, FALSE, TRUE, 4, 3, 4, 3, 4);
```

**Expected:** two successful `CREATE TABLE` commands and inserts of 1 and 4 rows. No production resource or database object is created.

## 3. Build the assessment view and enforce hard gates (4 minutes)

```sql
CREATE TEMP VIEW architecture_assessment AS
SELECT
    c.platform,
    CASE
        WHEN c.residency_ok IS TRUE
         AND c.extension_ok IS TRUE
         AND c.team_ready IS TRUE
         AND c.security_ok IS TRUE
        THEN 'ELIGIBLE'
        ELSE 'BLOCKED_OR_UNVERIFIED'
    END AS gate_status,
    ROUND(
        (
            c.reliability_score * w.reliability_weight
          + c.operations_score * w.operations_weight
          + c.performance_score * w.performance_weight
          + c.cost_score * w.cost_weight
          + c.portability_score * w.portability_weight
        )::NUMERIC / 100,
        2
    ) AS preference_score
FROM architecture_candidates AS c
CROSS JOIN architecture_weights AS w;

SELECT platform, gate_status, preference_score
FROM architecture_assessment
ORDER BY
    CASE WHEN gate_status = 'ELIGIBLE' THEN 0 ELSE 1 END,
    preference_score DESC,
    platform;
```

**Expected baseline results (illustrative only):**

| Platform | Gate status | Preference score |
|---|---|---:|
| RDS Multi-AZ instance | ELIGIBLE | 3.90 |
| RDS Multi-AZ cluster | ELIGIBLE | 3.70 |
| Bare metal / VM | ELIGIBLE | 3.25 |
| Kubernetes CNPG | BLOCKED_OR_UNVERIFIED | 3.55 |

**Interpretation:** Kubernetes CNPG is blocked because the *fictional team* is not ready; its 3.55 cannot override the hard gate. The eligible RDS Multi-AZ instance has the highest preference score **for these fabricated assumptions**. That does **not** establish it as a recommended production deployment.

Verify the weights:

```sql
SELECT reliability_weight + operations_weight + performance_weight
       + cost_weight + portability_weight AS total_weight
FROM architecture_weights;
```

Expected: `100`.

## 4. Model a different residency policy (4 minutes)

**Fictional scenario B:** cloud deployment is not permitted under the proposed residency policy; the organization has an experienced Kubernetes PostgreSQL operator team. This is a different hypothetical workload policy, not a real security conclusion.

Only update the **temporary** candidate table:

```sql
UPDATE architecture_candidates
SET residency_ok = FALSE
WHERE platform IN ('RDS Multi-AZ instance', 'RDS Multi-AZ cluster');

UPDATE architecture_candidates
SET team_ready = TRUE
WHERE platform = 'Kubernetes CNPG';

SELECT platform, gate_status, preference_score
FROM architecture_assessment
ORDER BY
    CASE WHEN gate_status = 'ELIGIBLE' THEN 0 ELSE 1 END,
    preference_score DESC,
    platform;
```

**Expected eligible candidates:**

| Platform | Gate status | Preference score |
|---|---|---:|
| Kubernetes CNPG | ELIGIBLE | 3.55 |
| Bare metal / VM | ELIGIBLE | 3.25 |

The two RDS candidates appear **after** the eligible options, both with `BLOCKED_OR_UNVERIFIED`. Their numerical scores remain 3.90 and 3.70, illustrating that a high score does not override a hard gate.

**Discussion:** Would you automatically approve Kubernetes CNPG? **No.** Actual storage, fencing, recovery, upgrade, team support, data residency, security and TCO evidence are still required.

## 5. Test an unknown gate and explain uncertainty (3 minutes)

```sql
UPDATE architecture_candidates
SET extension_ok = NULL
WHERE platform = 'Kubernetes CNPG';

SELECT platform, gate_status, preference_score
FROM architecture_assessment
WHERE platform = 'Kubernetes CNPG';
```

Expected: `Kubernetes CNPG | BLOCKED_OR_UNVERIFIED | 3.55`.

**Why:** `NULL` means not established; it is **not** equivalent to passing a mandatory requirement. Before production selection, validate extension support against the exact PostgreSQL/operator image and version.

To restore this lab's hypothetical gate, run:

```sql
UPDATE architecture_candidates
SET extension_ok = TRUE
WHERE platform = 'Kubernetes CNPG';
```

## 6. Produce a one-page architecture decision record (7 minutes)

Create a Markdown note locally (do **not** upload secrets, customer data, or confidential network information). Include:

```text
ADR: Example order service PostgreSQL platform selection
Date: [actual date]    Author: [learner]
Workload: Fictional 200 GB OLTP service with moderate writes
Mandatory gates: residency, security, extension support, support team
Assumptions: teaching inputs only; no measured benchmarks or TCO
Candidate shortlist: bare metal, RDS Multi-AZ instance/cluster, CNPG
Scenario A: RDS Multi-AZ instance ranks highest among fictional eligible options
Scenario B: CNPG ranks highest among fictional eligible options
Decision status: PROVISIONAL / NOT APPROVED
Required tests: application p95/p99, load, restore/PITR, RPO/RTO,
                failover and single-writer safety, capacity, security
Risks: unsupported extensions, backup gaps, cost unknowns, operator readiness
Owners/approvers: DBRE, application, platform, security, change management
Next review: after evidence collection
```

In your ADR, explain why **a weighted score is not an approval** and why a standby, PVC, or backup policy does not itself prove recoverability.

## 7. Optional read-only provider inspection (no cloud creation)

**Skip unless already authorized, configured, and explicitly within your access scope.** These commands inspect existing metadata only; they do not provision infrastructure, but may expose environment details. Do not commit their raw output.

For an authorized AWS account (PowerShell; adjust the approved region):

```powershell
aws sts get-caller-identity
aws rds describe-db-instances --region us-east-1 --query "DBInstances[].{Engine:Engine,MultiAZ:MultiAZ,Class:DBInstanceClass}" --output table
```

The `MultiAZ` flag does not by itself fully describe Multi-AZ **DB cluster** topology; inspect deployment type using the applicable RDS documentation and approved inventory. If the AWS CLI or permissions are unavailable, record **not executed** and continue.

For an authorized Kubernetes context (PowerShell):

```powershell
kubectl config current-context
kubectl get storageclass
kubectl get clusters.postgresql.cnpg.io -A
```

The last command may fail if the CloudNativePG CRD is absent or RBAC denies listing; neither result implies PostgreSQL is unhealthy. Confirm context and authorization before any query. Do **not** run `kubectl apply`, delete, restart, failover, or create cloud resources for this chapter.

## 8. End the local lab and clean up safely

In `psql`:

```sql
SELECT current_database(), current_user;
```

Then exit:

```text
\q
```

The session-scoped temporary tables and view are removed automatically when the session ends. **Do not drop the `postgres` database, delete the container, or remove its Docker volume.** No persistent rollback is required for this exercise.

## 9. Acceptance and evidence checklist

- [ ] Preflight confirmed an isolated PostgreSQL 17 lab.
- [ ] Baseline read-only checks were recorded.
- [ ] Temporary candidate/weight tables were created successfully.
- [ ] Weights total exactly 100.
- [ ] Scenario A: 3 eligible candidates and CNPG blocked; scores matched expectations.
- [ ] Scenario B: CNPG and bare metal eligible; RDS options blocked by residency gate.
- [ ] Unknown extension gate caused a blocked/unverified status.
- [ ] ADR states the decision is provisional, with named evidence gaps.
- [ ] Local session exited; no persistent application or cloud resources changed.
- [ ] Actual runtime output, if captured, is sanitized and independently reviewed before any status promotion.

**Publication note:** These are expected observations. This repository change does not demonstrate that the lab ran, that a cloud account was accessed, or that any deployment is production-ready.

## 10. Troubleshooting

| Symptom | Likely cause | Safe response |
|---|---|---|
| `pg-fleet-lab` not found | Chapter 01 not started | Follow Chapter 01; verify disposable identity |
| SQL says relation already exists | Reused same interactive session | Exit `psql` and reconnect; temp objects vanish |
| Wrong score | Typo in weights or candidate rows | Inspect `SELECT * FROM architecture_weights;` and `architecture_candidates;` |
| Unexpected gate status | `NULL` or `FALSE` hard gate | Query individual gate columns; never override without evidence |
| RDS CLI denied | Missing permissions or wrong account | Stop provider inspection; no privilege escalation |
| Kubernetes CRD not found | Operator not installed or wrong context | Skip optional inspection; confirm with platform owner |
| Score appears to imply guaranteed RPO/RTO | Misinterpretation of illustrative rating | Replace claim with measured recovery test and signed acceptance |

## 11. Official documentation (checked 2026-11-02)

- [PostgreSQL 18: Temporary Tables](https://www.postgresql.org/docs/18/sql-createtable.html)
- [PostgreSQL 18: CREATE VIEW](https://www.postgresql.org/docs/18/sql-createview.html)
- [PostgreSQL 18: Monitoring Statistics](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [Amazon RDS Multi-AZ DB instance](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZSingleStandby.html)
- [Amazon RDS Multi-AZ DB cluster](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/multi-az-db-clusters-concepts.html)
- [CloudNativePG 1.28](https://cloudnative-pg.io/docs/1.28/)
- [CloudNativePG backup](https://cloudnative-pg.io/docs/1.28/backup/)
- [Kubernetes persistent volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
)) { throw "Expected PostgreSQL 17, got: $serverVersion; STOP" }
$recoveryState = docker exec $containerId psql -X -v ON_ERROR_STOP=1 -U postgres -d postgres -Atc 'SELECT pg_is_in_recovery();'
if ($LASTEXITCODE -ne 0 -or $recoveryState -ne 'f') { throw 'Expected a standalone writable primary; STOP' }
```

Expected: Docker server available on the **manually verified local disposable context**, exact full container ID matching the Chapter 01 creation record, expected ownership label/image/data mount, successful readiness check, and PostgreSQL 17 server version number in the `170000`–`179999` range. **Stop** on any mismatch; a matching name or image tag alone does not prove ownership. The SQL exercises must not run until this preflight passes.

## 1. Connect and collect read-only baseline facts (3 minutes)

```powershell
docker exec -it pg-fleet-lab psql -U postgres -d postgres
```

Inside the interactive `psql` session:

```sql
SELECT current_database(), current_user, pg_is_in_recovery();
SHOW server_version;
SHOW max_connections;
SHOW shared_buffers;
SHOW wal_level;
SELECT pg_size_pretty(pg_database_size(current_database())) AS database_size;
```

**Expected:** `current_database()` is `postgres`, `pg_is_in_recovery()` is `false` for the Chapter 01 standalone primary. Other settings/sizes vary. These values are **observations**, not production capacity or recovery certification.

## 2. Define the hypothetical workload and hard gates (3 minutes)

**Fictional scenario A:** an online order application with an approved AWS footprint, moderate writes, high-availability requirement, and a team familiar with RDS but not yet operationally ready to run a PostgreSQL operator.

**Important:** All gates below represent *hypothetical prior approval for teaching*. Real security, extension, residency, and operational gates require documented evidence and may remain `NULL` until verified.

Create a temporary weight table (100 points total) and a candidate table:

```sql
CREATE TEMP TABLE architecture_weights (
    reliability_weight INTEGER NOT NULL CHECK (reliability_weight >= 0),
    operations_weight INTEGER NOT NULL CHECK (operations_weight >= 0),
    performance_weight INTEGER NOT NULL CHECK (performance_weight >= 0),
    cost_weight INTEGER NOT NULL CHECK (cost_weight >= 0),
    portability_weight INTEGER NOT NULL CHECK (portability_weight >= 0),
    CHECK (
        reliability_weight + operations_weight + performance_weight
        + cost_weight + portability_weight = 100
    )
);

INSERT INTO architecture_weights VALUES (30, 25, 15, 20, 10);

CREATE TEMP TABLE architecture_candidates (
    platform TEXT PRIMARY KEY,
    residency_ok BOOLEAN,
    extension_ok BOOLEAN,
    team_ready BOOLEAN,
    security_ok BOOLEAN,
    reliability_score INTEGER CHECK (reliability_score BETWEEN 1 AND 5),
    operations_score INTEGER CHECK (operations_score BETWEEN 1 AND 5),
    performance_score INTEGER CHECK (performance_score BETWEEN 1 AND 5),
    cost_score INTEGER CHECK (cost_score BETWEEN 1 AND 5),
    portability_score INTEGER CHECK (portability_score BETWEEN 1 AND 5)
);

INSERT INTO architecture_candidates VALUES
    ('Bare metal / VM',          TRUE, TRUE, TRUE,  TRUE, 4, 2, 3, 3, 5),
    ('RDS Multi-AZ instance',    TRUE, TRUE, TRUE,  TRUE, 4, 5, 3, 4, 2),
    ('RDS Multi-AZ cluster',     TRUE, TRUE, TRUE,  TRUE, 5, 4, 4, 2, 2),
    ('Kubernetes CNPG',         TRUE, TRUE, FALSE, TRUE, 4, 3, 4, 3, 4);
```

**Expected:** two successful `CREATE TABLE` commands and inserts of 1 and 4 rows. No production resource or database object is created.

## 3. Build the assessment view and enforce hard gates (4 minutes)

```sql
CREATE TEMP VIEW architecture_assessment AS
SELECT
    c.platform,
    CASE
        WHEN c.residency_ok IS TRUE
         AND c.extension_ok IS TRUE
         AND c.team_ready IS TRUE
         AND c.security_ok IS TRUE
        THEN 'ELIGIBLE'
        ELSE 'BLOCKED_OR_UNVERIFIED'
    END AS gate_status,
    ROUND(
        (
            c.reliability_score * w.reliability_weight
          + c.operations_score * w.operations_weight
          + c.performance_score * w.performance_weight
          + c.cost_score * w.cost_weight
          + c.portability_score * w.portability_weight
        )::NUMERIC / 100,
        2
    ) AS preference_score
FROM architecture_candidates AS c
CROSS JOIN architecture_weights AS w;

SELECT platform, gate_status, preference_score
FROM architecture_assessment
ORDER BY
    CASE WHEN gate_status = 'ELIGIBLE' THEN 0 ELSE 1 END,
    preference_score DESC,
    platform;
```

**Expected baseline results (illustrative only):**

| Platform | Gate status | Preference score |
|---|---|---:|
| RDS Multi-AZ instance | ELIGIBLE | 3.90 |
| RDS Multi-AZ cluster | ELIGIBLE | 3.70 |
| Bare metal / VM | ELIGIBLE | 3.25 |
| Kubernetes CNPG | BLOCKED_OR_UNVERIFIED | 3.55 |

**Interpretation:** Kubernetes CNPG is blocked because the *fictional team* is not ready; its 3.55 cannot override the hard gate. The eligible RDS Multi-AZ instance has the highest preference score **for these fabricated assumptions**. That does **not** establish it as a recommended production deployment.

Verify the weights:

```sql
SELECT reliability_weight + operations_weight + performance_weight
       + cost_weight + portability_weight AS total_weight
FROM architecture_weights;
```

Expected: `100`.

## 4. Model a different residency policy (4 minutes)

**Fictional scenario B:** cloud deployment is not permitted under the proposed residency policy; the organization has an experienced Kubernetes PostgreSQL operator team. This is a different hypothetical workload policy, not a real security conclusion.

Only update the **temporary** candidate table:

```sql
UPDATE architecture_candidates
SET residency_ok = FALSE
WHERE platform IN ('RDS Multi-AZ instance', 'RDS Multi-AZ cluster');

UPDATE architecture_candidates
SET team_ready = TRUE
WHERE platform = 'Kubernetes CNPG';

SELECT platform, gate_status, preference_score
FROM architecture_assessment
ORDER BY
    CASE WHEN gate_status = 'ELIGIBLE' THEN 0 ELSE 1 END,
    preference_score DESC,
    platform;
```

**Expected eligible candidates:**

| Platform | Gate status | Preference score |
|---|---|---:|
| Kubernetes CNPG | ELIGIBLE | 3.55 |
| Bare metal / VM | ELIGIBLE | 3.25 |

The two RDS candidates appear **after** the eligible options, both with `BLOCKED_OR_UNVERIFIED`. Their numerical scores remain 3.90 and 3.70, illustrating that a high score does not override a hard gate.

**Discussion:** Would you automatically approve Kubernetes CNPG? **No.** Actual storage, fencing, recovery, upgrade, team support, data residency, security and TCO evidence are still required.

## 5. Test an unknown gate and explain uncertainty (3 minutes)

```sql
UPDATE architecture_candidates
SET extension_ok = NULL
WHERE platform = 'Kubernetes CNPG';

SELECT platform, gate_status, preference_score
FROM architecture_assessment
WHERE platform = 'Kubernetes CNPG';
```

Expected: `Kubernetes CNPG | BLOCKED_OR_UNVERIFIED | 3.55`.

**Why:** `NULL` means not established; it is **not** equivalent to passing a mandatory requirement. Before production selection, validate extension support against the exact PostgreSQL/operator image and version.

To restore this lab's hypothetical gate, run:

```sql
UPDATE architecture_candidates
SET extension_ok = TRUE
WHERE platform = 'Kubernetes CNPG';
```

## 6. Produce a one-page architecture decision record (7 minutes)

Create a Markdown note locally (do **not** upload secrets, customer data, or confidential network information). Include:

```text
ADR: Example order service PostgreSQL platform selection
Date: [actual date]    Author: [learner]
Workload: Fictional 200 GB OLTP service with moderate writes
Mandatory gates: residency, security, extension support, support team
Assumptions: teaching inputs only; no measured benchmarks or TCO
Candidate shortlist: bare metal, RDS Multi-AZ instance/cluster, CNPG
Scenario A: RDS Multi-AZ instance ranks highest among fictional eligible options
Scenario B: CNPG ranks highest among fictional eligible options
Decision status: PROVISIONAL / NOT APPROVED
Required tests: application p95/p99, load, restore/PITR, RPO/RTO,
                failover and single-writer safety, capacity, security
Risks: unsupported extensions, backup gaps, cost unknowns, operator readiness
Owners/approvers: DBRE, application, platform, security, change management
Next review: after evidence collection
```

In your ADR, explain why **a weighted score is not an approval** and why a standby, PVC, or backup policy does not itself prove recoverability.

## 7. Optional read-only provider inspection (no cloud creation)

**Skip unless already authorized, configured, and explicitly within your access scope.** These commands inspect existing metadata only; they do not provision infrastructure, but may expose environment details. Do not commit their raw output.

For an authorized AWS account (PowerShell; adjust the approved region):

```powershell
aws sts get-caller-identity
aws rds describe-db-instances --region us-east-1 --query "DBInstances[].{Engine:Engine,MultiAZ:MultiAZ,Class:DBInstanceClass}" --output table
```

The `MultiAZ` flag does not by itself fully describe Multi-AZ **DB cluster** topology; inspect deployment type using the applicable RDS documentation and approved inventory. If the AWS CLI or permissions are unavailable, record **not executed** and continue.

For an authorized Kubernetes context (PowerShell):

```powershell
kubectl config current-context
kubectl get storageclass
kubectl get clusters.postgresql.cnpg.io -A
```

The last command may fail if the CloudNativePG CRD is absent or RBAC denies listing; neither result implies PostgreSQL is unhealthy. Confirm context and authorization before any query. Do **not** run `kubectl apply`, delete, restart, failover, or create cloud resources for this chapter.

## 8. End the local lab and clean up safely

In `psql`:

```sql
SELECT current_database(), current_user;
```

Then exit:

```text
\q
```

The session-scoped temporary tables and view are removed automatically when the session ends. **Do not drop the `postgres` database, delete the container, or remove its Docker volume.** No persistent rollback is required for this exercise.

## 9. Acceptance and evidence checklist

- [ ] Preflight confirmed an isolated PostgreSQL 17 lab.
- [ ] Baseline read-only checks were recorded.
- [ ] Temporary candidate/weight tables were created successfully.
- [ ] Weights total exactly 100.
- [ ] Scenario A: 3 eligible candidates and CNPG blocked; scores matched expectations.
- [ ] Scenario B: CNPG and bare metal eligible; RDS options blocked by residency gate.
- [ ] Unknown extension gate caused a blocked/unverified status.
- [ ] ADR states the decision is provisional, with named evidence gaps.
- [ ] Local session exited; no persistent application or cloud resources changed.
- [ ] Actual runtime output, if captured, is sanitized and independently reviewed before any status promotion.

**Publication note:** These are expected observations. This repository change does not demonstrate that the lab ran, that a cloud account was accessed, or that any deployment is production-ready.

## 10. Troubleshooting

| Symptom | Likely cause | Safe response |
|---|---|---|
| `pg-fleet-lab` not found | Chapter 01 not started | Follow Chapter 01; verify disposable identity |
| SQL says relation already exists | Reused same interactive session | Exit `psql` and reconnect; temp objects vanish |
| Wrong score | Typo in weights or candidate rows | Inspect `SELECT * FROM architecture_weights;` and `architecture_candidates;` |
| Unexpected gate status | `NULL` or `FALSE` hard gate | Query individual gate columns; never override without evidence |
| RDS CLI denied | Missing permissions or wrong account | Stop provider inspection; no privilege escalation |
| Kubernetes CRD not found | Operator not installed or wrong context | Skip optional inspection; confirm with platform owner |
| Score appears to imply guaranteed RPO/RTO | Misinterpretation of illustrative rating | Replace claim with measured recovery test and signed acceptance |

## 11. Official documentation (checked 2026-11-02)

- [PostgreSQL 18: Temporary Tables](https://www.postgresql.org/docs/18/sql-createtable.html)
- [PostgreSQL 18: CREATE VIEW](https://www.postgresql.org/docs/18/sql-createview.html)
- [PostgreSQL 18: Monitoring Statistics](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [Amazon RDS Multi-AZ DB instance](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZSingleStandby.html)
- [Amazon RDS Multi-AZ DB cluster](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/multi-az-db-clusters-concepts.html)
- [CloudNativePG 1.28](https://cloudnative-pg.io/docs/1.28/)
- [CloudNativePG backup](https://cloudnative-pg.io/docs/1.28/backup/)
- [Kubernetes persistent volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
