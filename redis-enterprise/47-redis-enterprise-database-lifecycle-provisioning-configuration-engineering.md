# Chapter 47 --- Redis Enterprise Database Lifecycle, Provisioning & Configuration Engineering

**Status:** Canonical\
**Track:** Redis Enterprise / Redis Software Production Engineering\
**Part:** Part 7 --- Platform, Kubernetes & Cloud Operations\
**Level:** Advanced → Production Database Service Engineering\
**Audience:** SREs, DBREs, Platform Engineers, Redis Administrators, Service Owners\
**Lab type:** Service request, workload classification, provisioning, configuration baseline, validation, resize/change, migration preparation, drift review, decommission, failure injection, runbooks, and production acceptance

------------------------------------------------------------------------

# 1. Objective

A Redis Enterprise database has a lifecycle:

```text
request -> classify -> design -> provision -> validate -> operate
        -> change/resize -> migrate if needed -> retire
```

This chapter standardizes that lifecycle so databases do not become unowned, inconsistently configured, oversized, insecure, or impossible to retire safely.

# 2. Service Request

Require:
```text
owner
application/use case
environment
criticality
cache vs durable state
peak workload
dataset/growth
RPO/RTO
security classification
regional requirements
```

# Part 1 --- Workload Classification

## 3. Identify the Role

Classify cache, session/state, rate limiting, Streams/messaging, search/query, or other supported workload. Do not apply one configuration template to every use case.

# Part 2 --- Service Tier

## 4. Record

Define availability, support, recovery, maintenance, and escalation expectations.

# Part 3 --- Topology Selection

## 5. Decide

Use requirements to select replication, persistence, shards, failure domains, Active-Active where justified, and Kubernetes/cloud placement. Reference Chapters 35–37 and 45–46 for deep engineering.

# Part 4 --- Capacity Input

## 6. Use Chapter 41

Provisioning inputs include peak ops/sec, value sizes, dataset, connections, growth, hottest-shard risk, persistence overhead, and failure headroom. Do not recreate a second capacity methodology here.

# Part 5 --- Configuration Baseline

## 7. Record

```text
database name
endpoint
memory limit
shards
replication
persistence
eviction policy
TLS/auth
backup
maintenance
monitoring
owner/tags
```

# Part 6 --- Naming and Metadata

## 8. Standardize

Names and tags should make environment, service, owner, and cost allocation discoverable without placing secrets or sensitive data in names.

# Part 7 --- Eviction Policy

## 9. Match Semantics

Choose eviction behavior according to whether data is rebuildable and how the application behaves under memory pressure. Validate with workload tests.

# Part 8 --- Persistence

## 10. Match Recovery Requirement

Select persistence only after classifying acceptable data loss, restart/recovery behavior, storage impact, and workload semantics.

# Part 9 --- Backup

## 11. Configure Where Required

Define schedule, retention, destination, encryption, monitoring, owner, and restore-test requirement.

# Part 10 --- Security

## 12. Provision

Use service identities, least privilege, TLS, secret management, and network controls from Chapter 38.

# Part 11 --- Endpoint and Connectivity

## 13. Validate

Test DNS, routing, firewall/network policy, TLS trust, authentication, client library, timeout, pooling, and reconnect behavior.

# Part 12 --- Observability Onboarding

## 14. Before Production

Register dashboards, alerts, SLO/SLI where used, ownership, and runbook links.

# Part 13 --- Provisioning Through Automation

## 15. Preferred

Use approved UI/API/IaC workflows from Chapter 43. Automation should read current state, compare desired state, apply controlled changes, verify, and record evidence.

# Part 14 --- Post-Provision Smoke Test

## 16. Validate

```text
connect
authenticate
TLS
SET/GET disposable key
TTL if relevant
application connectivity
metrics
alerts
replication
persistence
backup configuration
```

# Part 15 --- Performance Qualification

## 17. Before Production

Run representative load sufficient to validate latency, throughput, connection budget, shard behavior, memory headroom, and required failure capacity.

# Part 16 --- Operational Readiness

## 18. Gate

Complete Chapter 44 governance/ORR evidence and Chapter 48 production-readiness gate before go-live.

# Part 17 --- Configuration Drift

## 19. Detect

Compare actual vs approved state for capacity, replication, persistence, eviction, security, backup, monitoring, and metadata. Investigate before auto-remediation.

# Part 18 --- Resize

## 20. Workflow

Baseline → forecast → choose change → confirm recovery/failure headroom → execute supported resize → validate application/Redis → update inventory.

# Part 19 --- Shard Change

## 21. Caution

Resharding/rebalancing may create CPU, memory, network, and recovery pressure. Test and monitor the exact supported workflow.

# Part 20 --- Persistence / Eviction Change

## 22. Treat as Behavior Change

These settings can alter latency, storage, data survival, and application failure behavior. Use formal change control.

# Part 21 --- Endpoint / Certificate / Secret Change

## 23. Client Impact

Inventory consumers, overlap credentials/trust where supported, validate reconnect, monitor failures, then retire old material.

# Part 22 --- Tenant / Workload Migration

## 24. Prepare

Document source, target, compatibility, data-copy method, dual-write/replay if used, validation, cutover, rollback, and cleanup. Detailed migration engineering is reserved for Chapter 52.

# Part 23 --- Decommission

## 25. Safety Gate

Never delete solely because a ticket says unused. Verify application traffic, dependencies, owner approval, retention, recovery requirements, DNS/secrets/automation, and observation window.

# Part 24 --- Decommission Procedure

## 26. Steps

1. confirm owner;
2. inventory clients/dependencies;
3. verify traffic;
4. stop clients;
5. observe;
6. retain required backup/evidence;
7. remove database through approved procedure;
8. remove monitoring/automation/secrets/DNS;
9. verify no orphaned resources;
10. update inventory/cost records.

# Part 25 --- Hands-On Lab

## 27. Lifecycle Exercise — Reproducible Nonproduction Acceptance

**Scope:** An approved DBRE/platform owner must provision a *disposable staging database* using release-supported Redis Software/Enterprise UI, Operator or approved IaC. Commands below check the *database endpoint* after provisioning; they do not create, resize or delete any Redis Enterprise database.

### 27.1 Prerequisites and version record

Record product version, deployment mode (VM or Kubernetes Operator), endpoint/port, TLS trust settings, scoped test identity, change ID, baseline, rollback plan and service owner. This lab is for **isolated staging/test only**, with synthetic data. Never target production or shared databases. Keep credentials outside source control; never place passwords in command-line arguments or bypass TLS verification.

The lab requires Redis CLI with --tls and --cacert, and permission to run PING, SET, GET, TTL, EXISTS and UNLINK on its lab keys. If mutual TLS is required, use approved --cert and --key values. The Bash sample can be run from an approved WSL/Bash environment on Windows.

### 27.2 TLS/auth and disposable-key smoke

Replace example endpoint and CA path with approved staging values. Input the password interactively; do not log it.

~~~bash
set -euo pipefail
export REDIS_HOST="lab-redis.example.test"   # approved staging endpoint
export REDIS_PORT="10000"                    # approved staging port
export REDIS_CA="/secure/path/proxy_cert.pem"
test -r "$REDIS_CA"
read -r -s -p "Staging Redis password: " REDISCLI_AUTH
echo
export REDISCLI_AUTH
rcli() {
  redis-cli --raw --tls --cacert "$REDIS_CA" -h "$REDIS_HOST" -p "$REDIS_PORT" "$@"
}
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$"
LAB_KEY="tutorial:chapter47:$RUN_ID:smoke"
test "$(rcli PING)" = "PONG"
test "$(rcli SET "$LAB_KEY" lifecycle-smoke EX 300 NX)" = "OK"
test "$(rcli GET "$LAB_KEY")" = "lifecycle-smoke"
TTL_VALUE="$(rcli TTL "$LAB_KEY")"
test "$TTL_VALUE" -gt 0 && test "$TTL_VALUE" -le 300
printf 'PASS: PING, SET NX EX, GET, TTL (TTL=%s)\n' "$TTL_VALUE"
~~~

**Expected:** PING replies PONG; first SET NX EX 300 replies OK; GET returns lifecycle-smoke; TTL is an integer between 1 and 300. The PASS line is printed only if all assertions succeed. Record FAIL and stop on any unexpected result; never retry against another database.

### 27.3 Scoped cleanup

Run the following **in the same shell session** while LAB_KEY refers to the key created above. Never run FLUSHDB, FLUSHALL or wildcard deletion.

~~~bash
test -n "$LAB_KEY"
rcli UNLINK "$LAB_KEY"
test "$(rcli EXISTS "$LAB_KEY")" = "0"
echo "PASS: exact disposable key removed"
unset REDISCLI_AUTH
~~~

**Expected:** UNLINK returns integer 1 if the key is still present (0 if expired); EXISTS returns 0. If cleanup fails, record the exact key and involve the lab owner; do not broaden deletion. Memory reclamation after UNLINK may be asynchronous.

### 27.4 Lifecycle workflow and expected evidence

| Stage | Approved operator action | Expected observation | Gate |
|---|---|---|---|
| Provision | Create disposable DB with version-supported tooling | Endpoint, owner, memory, replication, persistence, eviction, TLS and backup align with request | Actual = approved baseline |
| Connectivity | Execute smoke above | PONG, OK, GET value, bounded TTL | All assertions PASS |
| Observability | Review metrics/alerts and runbooks | Fresh database metrics and correctly routed test alert | Missing samples = FAIL |
| Drift | Read actual configuration via approved UI/API and compare with desired | Differences in memory, shards, replication, persistence, eviction, backup, TLS | Unexplained differences = FAIL |
| Resize | **Only after separate approval** and demonstrated N-1 capacity | Before/after resource, client, latency and recovery evidence | Without authorization = NOT EXECUTED |
| Retirement | Verify owner, traffic/dependency inventory, retention and written approval | Disposable database retired through approved procedure; inventory/secrets reconciled | Without authorization = NOT EXECUTED |

### 27.5 Offline-only drift simulation (does not contact Redis)

~~~python
desired = {"memory_mb": 256, "replication": True, "eviction": "noeviction"}
observed = {"memory_mb": 256, "replication": True, "eviction": "allkeys-lru"}
differences = {
    field: {"expected": desired[field], "observed": observed.get(field)}
    for field in desired if desired[field] != observed.get(field)
}
assert differences == {
    "eviction": {"expected": "noeviction", "observed": "allkeys-lru"}
}
print("DRIFT DETECTED: eviction")
~~~

**Expected:** DRIFT DETECTED: eviction. Values are synthetic and must not be represented as real Redis evidence; do not auto-remediate operational drift.

### 27.6 Evidence and acceptance record

~~~text
Run ID / staging Redis release / deployment mode:
DB endpoint and CA reference (no secrets):
Owner / approved change:
Desired vs actual settings evidence:
PING / SET / GET / TTL observed:
Cleanup: exact key / EXISTS=0:
Metrics, alert and runbook evidence:
Resize: PASS / FAIL / NOT EXECUTED, approval reference:
Retirement: PASS / FAIL / NOT EXECUTED, approval reference:
Reviewer / timestamp / remaining risks:
~~~

A step not performed is **NOT EXECUTED**, never PASS; repeating the lab requires a new run ID. Production certification is out of scope.

Official references: [Redis CLI TLS](https://redis.io/docs/latest/operate/rs/references/cli-utilities/redis-cli/), [SET](https://redis.io/docs/latest/commands/set/), [UNLINK](https://redis.io/docs/latest/commands/unlink/).


# Part 26 --- Failure Injection

## 28. Ten Scenarios

1. missing owner;
2. wrong eviction policy;
3. insufficient memory;
4. missing replication;
5. backup not configured for required RPO;
6. TLS/client trust failure;
7. monitoring not onboarded;
8. configuration drift;
9. resize during insufficient failure headroom;
10. decommission request while a client still connects.

# Part 27 --- Troubleshooting

## 29. Matrix

| Symptom | Investigate |
|---|---|
| cannot connect | DNS/network/TLS/auth/endpoint |
| latency after provision | workload, shard, client, infrastructure |
| memory pressure | sizing, TTL, eviction, value size |
| drift | manual change, automation, emergency change |
| resize regression | capacity movement, recovery, client behavior |
| cannot retire | unknown dependency, retention, owner |

# Part 28 --- Production Runbooks

## 30. Provision
Validate request → design → capacity → security/recovery → create → smoke/load test → ORR.

## 31. Resize
Baseline → capacity decision → change plan → execute → validate → update inventory.

## 32. Configuration Drift
Detect → classify → identify source → approve desired state → remediate → verify.

## 33. Credential/Endpoint Change
Inventory consumers → stage new config → validate → monitor → retire old.

## 34. Decommission
Owner/dependency/retention gate → stop traffic → observe → retain evidence → remove → cleanup.

## 35. Failed Provision
Stop go-live → preserve evidence → correct configuration/dependency → repeat validation.

# Part 29 --- Templates

## 36. Database Request

```text
Service:
Owner:
Environment:
Use case:
Criticality:
Peak workload:
Dataset/growth:
Connections:
RPO/RTO:
Security classification:
Region:
Requested date:
```

## 37. Configuration Baseline

```text
Database:
Endpoint:
Memory:
Shards:
Replication:
Persistence:
Eviction:
Backup:
TLS/auth:
Monitoring:
Owner:
Tags:
```

# Part 30 --- Production Acceptance

## 38. Checklist

- [ ] Owner/use case defined.
- [ ] Workload classified.
- [ ] Service tier defined.
- [ ] Topology approved.
- [ ] Capacity model referenced.
- [ ] Failure headroom validated.
- [ ] Configuration baseline recorded.
- [ ] Security validated.
- [ ] Backup/recovery configured as required.
- [ ] Connectivity/client behavior tested.
- [ ] Observability onboarded.
- [ ] Smoke test passed.
- [ ] Representative load test passed.
- [ ] ORR completed.
- [ ] Drift detection defined.
- [ ] Resize procedure tested.
- [ ] Migration dependencies understood.
- [ ] Decommission procedure tested.
- [ ] Ten lifecycle failure scenarios reviewed.

# 39. Key Takeaways

Database lifecycle engineering connects request, configuration, validation, operation, change, migration, and retirement. Capacity belongs to Chapter 41; this chapter ensures those engineering decisions are consistently applied to each database throughout its life.

# 40. References

Validate provisioning, database configuration, resize, persistence, backup, security, and deletion workflows against the exact deployed Redis Enterprise version and official Redis documentation.
