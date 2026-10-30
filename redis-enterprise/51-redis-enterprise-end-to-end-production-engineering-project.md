# Chapter 51 --- Redis Enterprise End-to-End Production Engineering Project

**Status:** Canonical
**Track:** Redis Enterprise / Redis Software Production Engineering
**Part:** Part 9 --- End-to-End Production Engineering Projects
**Level:** Advanced to Production Capstone
**Audience:** SREs, DBREs, Platform Engineers, Redis Administrators, Developers, Application Owners

------------------------------------------------------------------------

# 1. Objective

This capstone proves that an engineer can design, validate, operate, troubleshoot, recover, and improve a production Redis Enterprise service.

The fictional workload is a Profile API using synthetic lab data. PostgreSQL is the authoritative profile source; Redis provides cache, session metadata, rate limiting, and event processing.

# 2. Project Flow

requirements -> architecture -> provision -> application patterns -> security -> capacity -> HA/recovery -> observability -> failure tests -> go-live -> incident/RCA -> Day-2 acceptance

# 3. Requirements

Record normal/peak requests, read/write ratio, dataset/growth, value sizes, connection scale, criticality, availability/latency objectives, RPO/RTO, data classification, and regional requirements.

# 4. Architecture

Document API clients, Profile API, Redis Enterprise, PostgreSQL source of truth, DNS, network, secret store, monitoring, backup destination, owners, and failure behavior.

# 5. Key Design

Use only synthetic lab namespaces:

tutorial:chapter51:profile:<id>
tutorial:chapter51:session:<id>
tutorial:chapter51:ratelimit:<client>
tutorial:chapter51:stream:profile-events

# 6. Cache Engineering

Implement cache-aside with TTL jitter, invalidation/change propagation, source concurrency limits, bounded retries, and stampede protection.

# 7. Client Reliability

Record client/version, TLS, service identity, connect/command timeouts, pool size, connection budget, retry/backoff/jitter, reconnect behavior, and pipelining where justified.

# 8. Rate Limiting

Use an atomic algorithm appropriate to requirements and test correctness under concurrency.

# 9. Redis Streams

Validate consumer groups, acknowledgment, pending entries, reclaim, retry, poison-message/DLQ handling, idempotency, retention, and outage catch-up capacity.

# 10. Persistence and HA

Classify which state is rebuildable and which requires durability. Validate replication, failure-domain placement, promotion capacity, client reconnect, and persistence behavior.

# 11. Backup and Restore

Where backup is required, define frequency, retention, destination, encryption, ownership, and complete an isolated restore with measured RPO/RTO evidence.

# 12. Security

Validate service identity, least privilege, TLS trust/hostname, secret storage/rotation, network controls, and negative access tests.

# 13. Observability

Monitor application request/P99/errors/cache hits/misses; client pool wait/timeouts/retries; Redis ops/latency/CPU/memory/connections/network/evictions/replication/persistence; Streams backlog; infrastructure/network/storage.

# 14. Capacity

Use the Chapter 41 model. Measure normal and peak load, memory, CPU saturation knee, network, connections, hottest shard, growth, N-1, and recovery capacity.

# 15. Representative Lab — Isolated Component Smoke With Evidence

**Scope:** This section makes the Redis *component* portion of the project reproducible. It is **not** an end-to-end application certification: PostgreSQL integration, application retry behavior, concurrency-correct rate limiting, alert routing, backup/restore, failover and N-1 performance remain separately approved staging exercises. Mark those items **NOT EXECUTED**, not PASS, until demonstrated.

## 15.1 Prepare an approved staging Redis database

Use an isolated, owner-approved Redis Software/Enterprise test database, with TLS configured and a test identity permitted to run PING, SET, GET, TTL, XGROUP CREATE, XADD, XREADGROUP, XPENDING, XACK, EXISTS and UNLINK. Redis CLI must support --tls and --cacert. Do not run against production/shared databases, or store authentication secrets in code, command-line arguments or evidence logs.

Record release/build, deployment mode, approved endpoint/port, trust CA reference, lab owner and change ticket. If mutual TLS is mandatory, configure certificate and private key using an approved method. On Windows, a sanctioned WSL/Bash client can run this sample.

~~~bash
set -euo pipefail
export REDIS_HOST="lab-redis.example.test"    # approved test endpoint
export REDIS_PORT="10000"                     # approved test port
export REDIS_CA="/secure/path/proxy_cert.pem"
test -r "$REDIS_CA"
read -r -s -p "Staging Redis password: " REDISCLI_AUTH
echo
export REDISCLI_AUTH
rcli() {
  redis-cli --raw --tls --cacert "$REDIS_CA" -h "$REDIS_HOST" -p "$REDIS_PORT" "$@"
}
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$"
PREFIX="tutorial:chapter51:$RUN_ID"
PROFILE="$PREFIX:profile:1001"
SESSION="$PREFIX:session:demo"
LIMIT_TOKEN="$PREFIX:ratelimit:one-shot"
STREAM="$PREFIX:stream:profile-events"
GROUP="group-$RUN_ID"
CONSUMER="consumer-$RUN_ID"
test "$(rcli PING)" = "PONG"
printf 'PASS: TLS-enabled Redis endpoint reached; lab=%s\n' "$RUN_ID"
~~~

**Expected:** PING returns PONG and the PASS line is printed. Any auth/TLS/client failure stops the lab; never disable certificate validation as a workaround.

## 15.2 Cache record and session TTL

~~~bash
test "$(rcli SET "$PROFILE" '{"id":1001,"name":"Synthetic"}' EX 600 NX)" = "OK"
test "$(rcli GET "$PROFILE")" = '{"id":1001,"name":"Synthetic"}'
test "$(rcli SET "$SESSION" active EX 300 NX)" = "OK"
test "$(rcli GET "$SESSION")" = "active"
PROFILE_TTL="$(rcli TTL "$PROFILE")"
SESSION_TTL="$(rcli TTL "$SESSION")"
test "$PROFILE_TTL" -gt 0 && test "$PROFILE_TTL" -le 600
test "$SESSION_TTL" -gt 0 && test "$SESSION_TTL" -le 300
printf 'PASS: profile/session values and bounded TTLs (%s,%s)\n' "$PROFILE_TTL" "$SESSION_TTL"
~~~

**Expected:** Each first SET NX EX returns OK, GET values match the synthetic values, and TTLs are positive and bounded. The PASS line confirms only these primitive operations, not cache-aside correctness, source invalidation or the user's real application integration. A repeated run with the same keys can return null for SET NX; always use a fresh RUN_ID.

## 15.3 One-shot request token (not a rate limiter)

~~~bash
test "$(rcli SET "$LIMIT_TOKEN" "admitted" EX 60 NX)" = "OK"
test "$(rcli GET "$LIMIT_TOKEN")" = "admitted"
test "$(rcli TTL "$LIMIT_TOKEN")" -gt 0
echo "PASS: single-use admission token has a TTL"
~~~

**Expected:** First SET NX EX returns OK, GET returns admitted, and TTL is positive. This demonstrates conditional creation of a *single token* only. **It is not** a complete per-client rate-limit algorithm. A production limiter still needs a concurrency-correct algorithm, fairness/limits, atomic TTL handling, fallback, and load tests, none of which this check certifies.

## 15.4 Streams consumer-group delivery and acknowledgment

The group, consumer and stream names are unique to the run. Do **not** omit the scoped prefix or use the names of existing shared streams.

~~~bash
test "$(rcli XGROUP CREATE "$STREAM" "$GROUP" 0 MKSTREAM)" = "OK"
EVENT_ID="$(rcli XADD "$STREAM" '*' event profile-created profile_id 1001)"
test -n "$EVENT_ID"
READ_RESULT="$(rcli XREADGROUP GROUP "$GROUP" "$CONSUMER" COUNT 1 STREAMS "$STREAM" '>')"
[[ "$READ_RESULT" == *"$EVENT_ID"* ]]
echo "PASS: consumer received expected stream entry"
rcli XPENDING "$STREAM" "$GROUP"  # record count 1 before acknowledgment
test "$(rcli XACK "$STREAM" "$GROUP" "$EVENT_ID")" = "1"
rcli XPENDING "$STREAM" "$GROUP"  # record count 0 after acknowledgment
echo "PASS: stream entry acknowledged"
~~~

**Expected:** XGROUP CREATE returns OK; XADD produces a generated stream ID (not a fixed constant); the first XREADGROUP for the new consumer includes that ID; pending count is **1 before XACK**, XACK returns **1**, and pending count is **0 afterward**. XPENDING's reply format varies with client output mode, so record and review it rather than relying on a fixed line layout. This does not test retry, poison-message/DLQ processing, lag under outage, or actual application consumers.

## 15.5 Exact-key cleanup, no database flush

**Run in the same shell session**, using the exact keys and stream created by this run. Inspect values before deletion when troubleshooting. Never use wildcard deletion, FLUSHDB or FLUSHALL.

~~~bash
test -n "$PREFIX"
rcli UNLINK "$PROFILE"
rcli UNLINK "$SESSION"
rcli UNLINK "$LIMIT_TOKEN"
rcli UNLINK "$STREAM"
test "$(rcli EXISTS "$PROFILE" "$SESSION" "$LIMIT_TOKEN" "$STREAM")" = "0"
echo "PASS: only this run's four known lab keys removed"
unset REDISCLI_AUTH
~~~

**Expected:** Each UNLINK returns 1 when its key still exists, or 0 if already expired; EXISTS on the four explicit keys returns 0. UNLINK removes stream data and its attached test consumer-group metadata with that isolated stream. If cleanup fails, record the exact keys and notify the lab owner rather than broadening the deletion scope.

## 15.6 Evidence sheet and acceptance boundary

~~~text
Run ID / approved staging environment / Redis version:
Owner and ticket; endpoint/port and CA reference (no secret contents):
PING/TLS: PASS / FAIL / NOT EXECUTED
Profile/session GET+TTL: PASS / FAIL / NOT EXECUTED
One-shot admission token: PASS / FAIL / NOT EXECUTED
Stream ID; received event ID:
XPENDING count before / after XACK; XACK result:
Cleanup: four scoped keys and EXISTS=0:
Application/PostgreSQL integration: NOT EXECUTED
Concurrency-correct rate limiter: NOT EXECUTED
HA, restore, DR, alerts, N-1 and load tests: NOT EXECUTED
Reviewer / timestamp / blockers / change evidence links:
~~~

**Do not mark the final production scorecard PASS based on this lab alone.** Commands are examples requiring the actual deployment's supported release, permissions and client behavior to be verified in a separate approved stage.

Official references: [Redis CLI TLS](https://redis.io/docs/latest/operate/rs/references/cli-utilities/redis-cli/), [SET](https://redis.io/docs/latest/commands/set/), [XGROUP CREATE](https://redis.io/docs/latest/commands/xgroup-create/), [XREADGROUP](https://redis.io/docs/latest/commands/xreadgroup/), [UNLINK](https://redis.io/docs/latest/commands/unlink/).


# 16. Test Matrix

Complete baseline, warm-cache, cold-cache, TTL-storm, hot-key, large-value, connection-scale, retry, failover-under-load, backup, restore, security-negative, monitoring, and alert-routing tests.

# 17. Fifteen Failure Scenarios

1. cache-miss storm
2. hot key
3. memory pressure
4. connection storm
5. Redis failover
6. network failure
7. authentication failure
8. Stream consumer failure
9. backup failure
10. monitoring failure
11. source slowdown
12. retry amplification
13. certificate trust failure
14. infrastructure node failure
15. N-1 capacity loss

For every scenario record detection, impact, mitigation, recovery, evidence, and corrective action.

# 18. Go-Live Gate

Require PASS for architecture, application/client, capacity, HA, restore, security, observability, runbooks, rollback, ownership, and open-risk review.

# 19. Traffic Ramp

Use a controlled ramp such as 10%, 25%, 50%, 75%, 100%. At each stage validate P99, errors, Redis CPU/memory/connections, source traffic, and failure headroom.

# 20. Incident Simulation

Create synthetic hot-key concentration leading to shard CPU saturation, P99 increase, timeouts, and retry amplification. Assign incident roles, preserve evidence, build hypotheses, apply reversible mitigation, validate recovery, write RCA, and create prevention/detection/mitigation actions.

# 21. Recurrence Test

Repeat the original incident workload after corrective actions and compare before/after evidence.

# 22. Day-2 Operations

Complete daily health review, weekly operational review, monthly capacity forecast, and periodic restore/failover/access/certificate/runbook exercises according to service criticality.

# 23. Project Runbooks

Maintain runbooks for high latency, cache-miss storm, Streams backlog, failover, backup/restore, security access failure, capacity risk, and major incident.

# 24. Evidence Package

Deliver architecture, dependency inventory, workload/key/TTL/client design, capacity model, load/N-1/failover/restore/security results, dashboards/alerts, failure tests, go-live gate, incident timeline/RCA/actions, Day-2 checklist, and final scorecard.

# 25. Final Scorecard

| Area | Result | Evidence | Open Risk |
|---|---|---|---|
| Architecture | PASS/FAIL | | |
| Application | PASS/FAIL | | |
| Capacity | PASS/FAIL | | |
| HA | PASS/FAIL | | |
| Recovery | PASS/FAIL | | |
| Security | PASS/FAIL | | |
| Observability | PASS/FAIL | | |
| Operations | PASS/FAIL | | |

Any critical FAIL blocks acceptance.

# 26. Final Acceptance Checklist

- [ ] Requirements and owners documented.
- [ ] Architecture/dependencies documented.
- [ ] Key/TTL/invalidation strategy validated.
- [ ] Stampede/source protection validated.
- [ ] Client connection/retry budget validated.
- [ ] Rate limiter and Streams tested.
- [ ] Persistence/HA decisions documented.
- [ ] Failover under load passed.
- [ ] Backup/restore passed where required.
- [ ] Security negative tests passed.
- [ ] Observability/alert routing passed.
- [ ] Peak/N-1/recovery capacity passed.
- [ ] Fifteen failure scenarios completed.
- [ ] Go-live/rollback/hypercare completed.
- [ ] Incident/RCA/recurrence test completed.
- [ ] Day-2 reviews completed.
- [ ] Eight runbooks reviewed.
- [ ] Final scorecard PASS.

# 27. Cleanup

List only Chapter 51 lab keys using SCAN with the tutorial:chapter51:* pattern. Review matches and remove only confirmed disposable keys with UNLINK. Remove temporary lab identities, alerts, dashboards, load generators, failure rules, and restore targets. Never use FLUSHDB or FLUSHALL on a shared or production database.

# 28. Key Takeaways

The capstone is accepted only when design, application behavior, capacity, failure handling, recovery, security, observability, incident response, and Day-2 operations are all supported by evidence.

# 29. References

Validate all product-specific commands, capabilities, support boundaries, and architecture choices against the exact deployed Redis Enterprise version and official Redis documentation.
