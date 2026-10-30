# Chapter 10 --- Architecture Inspection & Foundation Acceptance Lab

**Status:** Canonical\
**Track:** Redis Enterprise / Redis Software Production Engineering\
**Part:** Part 1 --- Foundations & Architecture\
**Level:** Production Foundation Acceptance\
**Audience:** Redis Administrators, SREs, DBREs, Platform Engineers,
Developers\
**Lab type:** End-to-end architecture inspection, topology mapping,
endpoint validation, shard/replica analysis, key-distribution review,
failure tabletop, troubleshooting, and production readiness acceptance

------------------------------------------------------------------------

# 1. Objective

This chapter is the acceptance project for:

**Part 1 --- Foundations & Architecture**

It combines the concepts from Chapters 01--09 into one operational
exercise.

You will not simply answer:

``` text
Is Redis running?
```

You will build enough evidence to answer:

``` text
What cluster am I connected to?
Which databases exist?
How do applications connect?
Where are the shards?
Where are the replicas?
Where are the proxies?
Are failure domains safe?
How are keys distributed?
Is replication healthy?
What happens if a node fails?
Can I inspect the platform through UI, rladmin, and REST API?
Is the current architecture ready for production operations?
```

The output of this lab should be a reusable Redis Enterprise
architecture baseline.

------------------------------------------------------------------------

# 2. Chapters Validated

This project validates knowledge from:

``` text
01 Redis Enterprise Fundamentals & Architecture
02 Connecting to Redis Enterprise
03 Redis Data Types, Key Design & Memory-Aware Data Modeling
04 Redis Commands, Command Semantics & Safe Operations
05 Redis Enterprise Databases, Endpoints & Configuration
06 Redis Enterprise Nodes, Shards, Proxies & Placement
07 Hash Slots, Key Distribution & Sharding Internals
08 Replication Architecture & Primary/Replica Behavior
09 Redis Enterprise Administration Interfaces
```

------------------------------------------------------------------------

# 3. Acceptance Deliverables

By the end, produce:

``` text
1. Cluster inventory
2. Node inventory
3. Database inventory
4. Endpoint/connectivity record
5. Shard topology
6. Primary/replica map
7. Proxy map
8. Failure-domain map
9. Key-design review
10. Hash-tag/distribution review
11. Command-safety review
12. Configuration baseline
13. Management-interface validation
14. Capacity observations
15. Failure-impact matrix
16. Troubleshooting evidence
17. Architecture diagram
18. Production readiness scorecard
19. Open-risk register
20. Acceptance decision
```

------------------------------------------------------------------------

# 4. Lab Safety Rules

Use:

``` text
development
training
test
staging
```

for command experiments.

Production inspection must remain read-only unless a separately approved
change exists.

Do not use:

``` redis
FLUSHALL
FLUSHDB
KEYS *
```

as routine lab commands.

Do not:

``` text
stop production nodes
kill Redis processes
remove shards
change shard count
disable replication
delete production databases
bypass TLS permanently
```

for this acceptance lab.

------------------------------------------------------------------------

# Phase 1 --- Environment Identification

## 5. Record the Environment

Create:

``` text
Environment:
Cluster name:
Platform/version:
Region/data center:
Owner:
Business service:
Date:
Operator:
Change/assessment ticket:
```

The first operational rule is:

> Know exactly which Redis environment you are inspecting.

------------------------------------------------------------------------

## 6. Validate Management Endpoint

Record:

``` text
Cluster Manager endpoint:
DNS name:
Port:
TLS enabled:
Certificate issuer:
Certificate expiration:
Authentication method:
```

Do not store passwords in the document.

------------------------------------------------------------------------

# Phase 2 --- Cluster Inspection

## 7. Cluster Manager UI

Open the Cluster Manager UI.

Record:

``` text
Cluster health:
Node count:
Database count:
Current alerts:
License/status indicators:
Recent warnings:
```

Take screenshots only if organizational policy permits them and they do
not expose secrets.

------------------------------------------------------------------------

## 8. `rladmin status`

Run:

``` bash
rladmin status
```

Record:

``` text
Nodes:
Databases:
Shards:
Warnings:
```

Compare with the UI.

Expected:

``` text
UI and CLI describe the same logical cluster state.
```

------------------------------------------------------------------------

## 9. Cluster Information

Where supported:

``` bash
rladmin info cluster
```

Record relevant cluster information.

Do not build automation around output fields until verified for the
deployed release.

------------------------------------------------------------------------

# Phase 3 --- Node Inventory

## 10. Inspect Nodes

Run:

``` bash
rladmin info node
```

Build:

  ---------------------------------------------------------------------------
  Node      Address   Status    Failure   CPU Capacity       Memory Notes
                                Domain                     Capacity 
  --------- --------- --------- --------- ------------ ------------ ---------
                                                                    

                                                                    

                                                                    
  ---------------------------------------------------------------------------

------------------------------------------------------------------------

## 11. Node Questions

Answer:

``` text
Are all nodes healthy?
Are nodes distributed across expected failure domains?
Are node capacities consistent?
Are there known maintenance conditions?
Is any node under unusual pressure?
```

------------------------------------------------------------------------

# Phase 4 --- Database Inventory

## 12. Inspect Databases

Run:

``` bash
rladmin info db
```

Build:

  ---------------------------------------------------------------------------------
  Database   ID        Status          Memory      Primary Replication   Endpoint
                                                    Shards               
  ---------- --------- --------- ------------ ------------ ------------- ----------
                                                                         

                                                                         
  ---------------------------------------------------------------------------------

------------------------------------------------------------------------

## 13. Ownership Inventory

Extend:

  Database   Environment   Application   Owner   Criticality
  ---------- ------------- ------------- ------- -------------
                                                 
                                                 

Every production database should have an owner.

Unknown ownership is an operational risk.

------------------------------------------------------------------------

# Phase 5 --- Endpoint Validation

## 14. Select Target Database

Choose one non-production target database for the hands-on portion.

Record:

``` text
Database:
Endpoint:
Port:
TLS:
Authentication:
Expected client:
```

------------------------------------------------------------------------

## 15. DNS Test

``` bash
nslookup <database-endpoint>
```

or:

``` bash
dig <database-endpoint>
```

Record:

``` text
DNS resolves: Yes/No
Resolved address:
```

------------------------------------------------------------------------

## 16. TCP Test

Where permitted:

``` bash
nc -vz <database-endpoint> <port>
```

or equivalent platform tooling.

Record:

``` text
TCP reachable: Yes/No
Latency/observation:
```

------------------------------------------------------------------------

## 17. TLS Test

Where TLS is enabled:

``` bash
openssl s_client \
  -connect <database-endpoint>:<port> \
  -servername <database-endpoint>
```

Review:

``` text
certificate chain
subject
issuer
expiration
hostname
```

------------------------------------------------------------------------

## 18. Redis Client Test

Conceptual TLS example:

``` bash
redis-cli \
  -h <database-endpoint> \
  -p <port> \
  --tls \
  --cacert /path/to/ca.pem \
  --user '<username>' \
  --pass '<password>' \
  PING
```

Expected:

``` text
PONG
```

Use the authentication model configured for the target database.

Avoid exposing passwords in shell history.

------------------------------------------------------------------------

# Phase 6 --- Basic Data-Plane Validation

## 19. Create Lab Namespace

Use:

``` text
tutorial:chapter10:
```

All lab keys must have TTLs unless the exercise explicitly validates TTL
behavior.

------------------------------------------------------------------------

## 20. String Test

``` redis
SET tutorial:chapter10:string "foundation-acceptance" EX 900
GET tutorial:chapter10:string
TTL tutorial:chapter10:string
```

**Expected per-command responses:** `SET` returns `OK`; `GET` returns `foundation-acceptance`; `TTL` is a positive integer up to 900 (not a fixed 900 because time passes).

Expected:

``` text
foundation-acceptance
positive TTL
```

------------------------------------------------------------------------

## 21. Hash Test

``` redis
HSET tutorial:chapter10:user:1001 name "Alice" status "active"
EXPIRE tutorial:chapter10:user:1001 900
HGETALL tutorial:chapter10:user:1001
TTL tutorial:chapter10:user:1001
```

**Expected, when the isolated lab key does not already exist:** `HSET` returns integer `2` newly added fields; `EXPIRE` returns `1`; `HGETALL` returns the `name=Alice` and `status=active` pairs (hash field ordering is not a contract); and `TTL` returns a positive integer no greater than 900. If re-running without cleanup, `HSET` may return `0` because the fields already exist. Do not mistake a changed field ordering for incorrect data.

------------------------------------------------------------------------

## 22. Counter Test

``` redis
SET tutorial:chapter10:counter 0 EX 900
INCR tutorial:chapter10:counter
INCRBY tutorial:chapter10:counter 9
GET tutorial:chapter10:counter
```

Expected final value:

``` text
10
```

------------------------------------------------------------------------

## 23. Sorted Set Test

``` redis
ZADD tutorial:chapter10:leaderboard 100 user1
ZADD tutorial:chapter10:leaderboard 200 user2
ZADD tutorial:chapter10:leaderboard 150 user3
EXPIRE tutorial:chapter10:leaderboard 900
ZREVRANGE tutorial:chapter10:leaderboard 0 -1 WITHSCORES
```

**Expected, on an absent disposable key:** Each `ZADD` returns `1` for one new member, and `EXPIRE` returns `1`. The final `ZREVRANGE ... WITHSCORES` returns descending score order:

```text
user2 200
user3 150
user1 100
```

This presentation is **schematic**: `redis-cli` normally displays members and scores as alternating reply elements, not necessarily paired on one line. On an existing key, the `ZADD` added-member counts can be 0; an approval-gated lab must verify the expected key state before interpreting results.

------------------------------------------------------------------------

# Phase 7 --- Key Design Review

## 24. Review Naming

Evaluate:

``` text
service ownership
entity
identifier
purpose
versioning
tenant dimension
TTL policy
hash tags
```

Example:

``` text
checkout:cart:{customer:1001}
```

Questions:

``` text
Who owns it?
Why does it need a hash tag?
What is the maximum size?
What is the TTL?
What happens on schema change?
```

------------------------------------------------------------------------

## 25. Memory Inspection

For lab keys:

``` redis
MEMORY USAGE tutorial:chapter10:string
MEMORY USAGE tutorial:chapter10:user:1001
MEMORY USAGE tutorial:chapter10:leaderboard
```

Record:

  Key   Type     Memory   TTL
  ----- ------ -------- -----
                        

This establishes the connection between logical modeling and memory use.

------------------------------------------------------------------------

# Phase 8 --- Command Safety Review

## 26. Safe Discovery

Use:

``` redis
SCAN 0 MATCH 'tutorial:chapter10:*' COUNT 100
```

Do not use:

``` redis
KEYS *
```

on production databases.

------------------------------------------------------------------------

## 27. Safe Deletion Review

For known lab keys:

``` redis
UNLINK tutorial:chapter10:string
```

Recreate it if needed for later exercises.

Understand:

``` text
DEL
```

versus:

``` text
UNLINK
```

before large-key deletion.

------------------------------------------------------------------------

## 28. Conditional Write Test

``` redis
SET tutorial:chapter10:lock token-1 NX EX 60
SET tutorial:chapter10:lock token-2 NX EX 60
GET tutorial:chapter10:lock
```

Expected:

``` text
first SET succeeds
second NX SET does not overwrite existing key
```

This validates command semantics, not a complete distributed-lock
implementation.

------------------------------------------------------------------------

# Phase 9 --- Shard Topology

## 29. Inspect Shards

Run:

``` bash
rladmin info shard
```

Build:

  Shard   Database   Role      Node   Status
  ------- ---------- --------- ------ --------
                     Primary          
                     Replica          

------------------------------------------------------------------------

## 30. Target Database Map

For the target database:

``` text
P1 -> Node ?
R1 -> Node ?

P2 -> Node ?
R2 -> Node ?
```

Create a full mapping.

------------------------------------------------------------------------

# Phase 10 --- Proxy Topology

## 31. Inspect Proxies

Run:

``` bash
rladmin info proxy
```

Build:

  Proxy   Node   Status   Notes
  ------- ------ -------- -------
                          
                          

------------------------------------------------------------------------

## 32. Request Path

Document:

``` text
Client
  |
  v
Database Endpoint
  |
  v
Proxy / routing layer
  |
  v
Primary shard
```

Add actual node/shard names from your environment where appropriate.

------------------------------------------------------------------------

# Phase 11 --- Replication Validation

## 33. Pair Primary and Replica

Build:

  Pair    Primary Node   Replica Node   Same Node?
  ------- -------------- -------------- ------------
  P1/R1                                 
  P2/R2                                 

Expected for node-level HA:

``` text
Same Node? No
```

------------------------------------------------------------------------

## 34. Failure-Domain Validation

Build:

  Pair   Primary Domain   Replica Domain   Same Domain?   Risk
  ------ ---------------- ---------------- -------------- ------
                                                          
                                                          

Document exceptions.

Do not silently accept unsafe placement.

------------------------------------------------------------------------

## 35. Replication Health

Record:

``` text
Replication enabled:
Expected replicas:
Healthy replicas:
Synchronization in progress:
Replication warning:
Recent failover:
```

Exact metrics depend on release.

------------------------------------------------------------------------

# Phase 12 --- Hash Slot and Distribution Review

## 36. Create Tagged Keys

``` redis
SET tutorial:chapter10:profile:{1001} profile EX 900
SET tutorial:chapter10:cart:{1001} cart EX 900
SET tutorial:chapter10:session:{1001} session EX 900

SET tutorial:chapter10:profile:{1002} profile EX 900
```

The three `{1001}` keys intentionally share the same tag.

------------------------------------------------------------------------

## 37. Explain the Design

Document:

``` text
Hash tag: 1001
Reason for co-location:
Multi-key requirement:
Expected keys per tag:
Expected traffic per tag:
Largest possible tenant:
```

If no co-location requirement exists, braces may not be justified.

------------------------------------------------------------------------

## 38. Identify Bad Pattern

Review:

``` text
cache:{global}:user:1
cache:{global}:user:2
cache:{global}:user:3
```

Explain:

``` text
All keys share one hash tag.
This intentionally concentrates them into one logical slot.
Adding shards alone does not correct that design.
```

------------------------------------------------------------------------

# Phase 13 --- Shard Distribution Baseline

## 39. Collect Per-Shard Metrics

Where available:

  Shard   Node     Keys   Memory   Ops/sec   CPU   Network   Latency
  ------- ------ ------ -------- --------- ----- --------- ---------
                                                           
                                                           

------------------------------------------------------------------------

## 40. Analyze Skew

Identify:

``` text
highest CPU shard
highest memory shard
highest ops shard
highest network shard
largest latency outlier
```

Then classify:

``` text
balanced
data skew
workload skew
hot key suspected
hot partition suspected
unknown
```

------------------------------------------------------------------------

# Phase 14 --- Node Capacity Baseline

## 41. Node Resource Table

  ---------------------------------------------------------------------------------
  Node            CPU            CPU     Memory     Memory     Shards Network
             Capacity   Current/Peak   Capacity       Used            Observation
  -------- ---------- -------------- ---------- ---------- ---------- -------------
                                                                      

                                                                      
  ---------------------------------------------------------------------------------

------------------------------------------------------------------------

## 42. Capacity Questions

Answer:

``` text
Is one node significantly hotter?
Is one node carrying more memory?
Are shard counts uneven?
Is workload uneven despite equal shard count?
Is there enough headroom for one-node failure?
```

Do not infer HA capacity from cluster averages alone.

------------------------------------------------------------------------

# Phase 15 --- REST API Validation

## 43. Secure Lab Variables

``` bash
export RE_MGMT='https://<cluster-manager>:9443'
export RE_USER='<admin-user>'
export RE_PASSWORD='<admin-password>'
export RE_CA='/path/to/ca.pem'
```

Use only in an approved lab shell.

Production automation should use approved secret management.

------------------------------------------------------------------------

## 44. Cluster API

``` bash
curl \
  --cacert "$RE_CA" \
  -u "$RE_USER:$RE_PASSWORD" \
  "$RE_MGMT/v1/cluster" |
jq
```

------------------------------------------------------------------------

## 45. Database API

``` bash
curl \
  --cacert "$RE_CA" \
  -u "$RE_USER:$RE_PASSWORD" \
  "$RE_MGMT/v1/bdbs" |
jq
```

------------------------------------------------------------------------

## 46. Node API

``` bash
curl \
  --cacert "$RE_CA" \
  -u "$RE_USER:$RE_PASSWORD" \
  "$RE_MGMT/v1/nodes" |
jq
```

------------------------------------------------------------------------

## 47. Shard API

``` bash
curl \
  --cacert "$RE_CA" \
  -u "$RE_USER:$RE_PASSWORD" \
  "$RE_MGMT/v1/shards" |
jq
```

------------------------------------------------------------------------

## 48. Proxy API

``` bash
curl \
  --cacert "$RE_CA" \
  -u "$RE_USER:$RE_PASSWORD" \
  "$RE_MGMT/v1/proxies" |
jq
```

Compare REST observations with UI and `rladmin`.

------------------------------------------------------------------------

# Phase 16 --- Configuration Baseline

## 49. Database Baseline

For each important database record:

``` text
Name:
ID:
Owner:
Endpoint:
TLS:
Authentication:
Memory limit:
Eviction policy:
Primary shards:
Replication:
Persistence:
Backup:
Criticality:
RPO:
RTO:
```

Some topics such as persistence and backup will be developed deeply
later; capture current state now.

------------------------------------------------------------------------

## 50. Baseline as Code-Friendly Data

Example:

``` yaml
database: customer-cache
environment: production
owner: customer-platform
replication: true
primary_shards: 4
tls: true
```

Do not store passwords or private keys in the baseline.

------------------------------------------------------------------------

# Phase 17 --- Failure Tabletop 1: Node Loss

## 51. Select One Node

Choose:

``` text
Node X
```

List:

``` text
primaries on Node X
replicas on Node X
proxies on Node X
databases affected
failure domain
```

------------------------------------------------------------------------

## 52. Predict Impact

Answer:

``` text
Which primary shards require HA transition?
Where are their replicas?
Which databases temporarily lose redundancy?
Are replicas in separate failure domains?
Can remaining nodes absorb workload?
What client symptoms may occur?
```

------------------------------------------------------------------------

# Phase 18 --- Failure Tabletop 2: Replica Loss

## 53. Scenario

``` text
Primary healthy
Replica unavailable
```

Classify:

``` text
Application availability: potentially healthy
HA state: degraded
```

Required operational response:

``` text
restore redundancy
```

Do not close based only on successful application traffic.

------------------------------------------------------------------------

# Phase 19 --- Failure Tabletop 3: Hot Shard

## 54. Scenario

``` text
P1 CPU 92%
P2 CPU 30%
P3 CPU 28%
P4 CPU 31%
```

Investigation:

``` text
hot key
hash tags
tenant skew
big key
command mix
ops/sec
network
```

Do not automatically:

``` text
add nodes
```

------------------------------------------------------------------------

# Phase 20 --- Failure Tabletop 4: Endpoint Failure

## 55. Scenario

Application reports:

``` text
Redis connection timeout
```

Troubleshoot in layers:

``` text
1. DNS
2. TCP
3. TLS
4. authentication
5. authorization
6. endpoint/proxy
7. database
8. shards
9. client pool
```

Capture evidence at each layer.

------------------------------------------------------------------------

# Phase 21 --- Failure Tabletop 5: API Failure

## 56. Scenario

Automation receives:

``` text
503
```

Correct response:

``` text
capture status
capture sanitized body
check cluster management health
stop aggressive retries
use bounded backoff if retry is safe
confirm whether any change was applied
```

Incorrect response:

``` text
retry forever every 100 ms
```

------------------------------------------------------------------------

# Phase 22 --- Failure Tabletop 6: Bad Key Design

## 57. Scenario

Application uses:

``` text
orders:{global}:<order-id>
```

for millions of orders.

Analysis:

``` text
low-cardinality hash tag
intentional slot concentration
possible hot partition
poor horizontal distribution
```

Remediation starts with key-design review.

------------------------------------------------------------------------

# Phase 23 --- Failure Tabletop 7: Missing TTL

## 58. Scenario

A cache database continuously grows.

Inspection finds:

``` redis
TTL some-cache-key
```

returns:

``` text
-1
```

for a large population of cache keys.

Investigate:

``` text
application write path
TTL policy
invalidation
key ownership
memory growth
eviction behavior
```

Do not solve a lifecycle bug only by adding memory.

------------------------------------------------------------------------

# Phase 24 --- Failure Tabletop 8: Unsafe Command

## 59. Scenario

An engineer proposes:

``` redis
KEYS *
```

against a large production database.

Review:

``` text
operational cost
blocking/work impact
safer SCAN workflow
namespace targeting
```

Preferred pattern:

``` redis
SCAN 0 MATCH 'service:entity:*' COUNT 100
```

with incremental iteration.

------------------------------------------------------------------------

# Phase 25 --- Troubleshooting Drill

## 60. Symptom

Assume:

``` text
Application p99 Redis latency increased from 3 ms to 120 ms.
```

Build an evidence-driven investigation.

------------------------------------------------------------------------

## 61. Step 1 --- Scope

Determine:

``` text
one application?
one database?
one endpoint?
all commands?
one shard?
one node?
```

------------------------------------------------------------------------

## 62. Step 2 --- Connectivity

Check:

``` text
DNS
TCP
TLS
connection errors
pool exhaustion
```

------------------------------------------------------------------------

## 63. Step 3 --- Database

Check:

``` text
database status
memory
evictions
ops/sec
latency
```

------------------------------------------------------------------------

## 64. Step 4 --- Shards

Check:

``` text
CPU per shard
memory per shard
ops per shard
network per shard
hot shard
replication state
```

------------------------------------------------------------------------

## 65. Step 5 --- Commands

Check:

``` text
command mix
expensive operations
large responses
blocking behavior
slow operations
```

------------------------------------------------------------------------

## 66. Step 6 --- Keys

Check:

``` text
hot keys
big keys
hash-tag concentration
tenant skew
missing TTL
```

------------------------------------------------------------------------

## 67. Step 7 --- Nodes

Check:

``` text
CPU
memory
network
shard density
recovery activity
```

------------------------------------------------------------------------

## 68. Step 8 --- Correlate

Build a timeline:

``` text
latency increase
traffic change
deployment
failover
maintenance
replication event
capacity event
```

Correlation is stronger than isolated snapshots.

------------------------------------------------------------------------

# Phase 26 --- Architecture Diagram

## 69. Required Diagram

Produce a diagram similar to:

``` text
                         Applications
                              |
                              v
                       Database Endpoint
                              |
                       +------+------+
                       |   Proxies   |
                       +------+------+
                              |
            +-----------------+-----------------+
            |                 |                 |
           P1                P2                P3
            |                 |                 |
           R1                R2                R3

P1 Node1 AZ-A          P2 Node2 AZ-A       P3 Node3 AZ-B
R1 Node3 AZ-B          R2 Node4 AZ-B       R3 Node1 AZ-A
```

Add:

``` text
management endpoint
Cluster Manager
rladmin access location
REST API
monitoring
```

------------------------------------------------------------------------

# Phase 27 --- Architecture Risk Register

## 70. Risk Template

  ID   Risk   Evidence   Impact   Severity   Owner   Action
  ---- ------ ---------- -------- ---------- ------- --------
  R1                                                 
  R2                                                 

Examples:

``` text
replica same failure domain
unknown database owner
no TLS
no spare capacity
hot shard
global hash tag
missing TTL policy
no failover runbook
```

------------------------------------------------------------------------

# Phase 28 --- Readiness Scorecard

## 71. Scoring

Use:

``` text
2 = Meets requirement
1 = Partially meets requirement
0 = Does not meet requirement
N/A = Not applicable
```

------------------------------------------------------------------------

## 72. Architecture Scorecard

  Area                          Score Evidence
  --------------------------- ------- ----------
  Cluster inventory                   
  Node inventory                      
  Database ownership                  
  Endpoint documentation              
  TLS                                 
  Authentication                      
  Key naming                          
  TTL policy                          
  Command safety                      
  Shard topology                      
  Replica topology                    
  Failure-domain separation           
  Proxy health                        
  Key distribution                    
  Hash-tag design                     
  Per-shard observability             
  Node capacity                       
  Failover capacity                   
  Management access                   
  API inspection                      
  Runbooks                            

------------------------------------------------------------------------

## 73. Score Interpretation

Example internal interpretation:

``` text
90–100% = Foundation ready
75–89%  = Ready with tracked improvements
50–74%  = Significant gaps
<50%    = Foundation not ready
```

These are tutorial assessment bands, not vendor-defined Redis Enterprise
thresholds.

Your organization may use different acceptance criteria.

------------------------------------------------------------------------

# Phase 29 --- Production Acceptance Decision

## 74. Decision Template

``` text
Cluster:
Assessment date:
Assessor:

Decision:
[ ] ACCEPT
[ ] ACCEPT WITH CONDITIONS
[ ] REJECT / REMEDIATION REQUIRED

Critical findings:

High findings:

Medium findings:

Required actions:

Owners:

Due dates:

Retest date:
```

------------------------------------------------------------------------

# Phase 30 --- Runbooks

## 75. Runbook --- Architecture Inspection

``` text
1. Confirm cluster identity.
2. Record timestamp.
3. Inspect Cluster Manager.
4. Run rladmin status.
5. Inventory nodes.
6. Inventory databases.
7. Inventory shards.
8. Inventory proxies.
9. Map primary/replica pairs.
10. Map failure domains.
11. Validate endpoints.
12. Review key design.
13. Review hash tags.
14. Review per-shard metrics.
15. Review node capacity.
16. Retrieve REST API state.
17. Record risks.
18. Update architecture diagram.
```

------------------------------------------------------------------------

## 76. Runbook --- New Database Foundation Review

``` text
1. Identify owner.
2. Identify business criticality.
3. Define endpoint/TLS.
4. Define authentication.
5. Define memory limit.
6. Define eviction behavior.
7. Define shard requirement.
8. Define replication requirement.
9. Define failure-domain requirement.
10. Define persistence requirement.
11. Define backup requirement.
12. Review key naming.
13. Review TTL policy.
14. Review hash tags.
15. Review multi-key commands.
16. Review client pooling/timeouts/retries.
17. Define monitoring.
18. Define runbooks.
19. Complete acceptance scorecard.
```

------------------------------------------------------------------------

## 77. Runbook --- Foundation Incident Triage

``` text
1. Confirm affected database.
2. Confirm endpoint.
3. Check DNS/TCP/TLS.
4. Check database health.
5. Check proxies.
6. Check shards.
7. Check replication.
8. Check node health.
9. Check shard CPU/memory/ops.
10. Check command behavior.
11. Check hot/big keys.
12. Check key distribution/hash tags.
13. Check recent changes.
14. Build timeline.
15. Mitigate based on evidence.
16. Validate service and HA recovery.
```

------------------------------------------------------------------------

# Part 31 --- Final Acceptance Checklist

## 78. Cluster

-   [ ] Correct cluster identified.
-   [ ] Cluster health inspected.
-   [ ] Cluster Manager accessible.
-   [ ] `rladmin` inspection successful.
-   [ ] REST API inspection successful.
-   [ ] Current alerts reviewed.

------------------------------------------------------------------------

## 79. Nodes

-   [ ] All nodes inventoried.
-   [ ] Node status recorded.
-   [ ] Failure domains recorded.
-   [ ] CPU capacity reviewed.
-   [ ] Memory capacity reviewed.
-   [ ] Network considerations reviewed.
-   [ ] Single-node failure headroom considered.

------------------------------------------------------------------------

## 80. Databases

-   [ ] All databases inventoried.
-   [ ] Owners recorded.
-   [ ] Criticality recorded.
-   [ ] Endpoints recorded.
-   [ ] Memory configuration recorded.
-   [ ] Shard counts recorded.
-   [ ] Replication recorded.

------------------------------------------------------------------------

## 81. Connectivity

-   [ ] DNS validated.
-   [ ] TCP validated.
-   [ ] TLS validated.
-   [ ] Authentication validated.
-   [ ] Redis `PING` validated.
-   [ ] Credentials handled securely.

------------------------------------------------------------------------

## 82. Data Model

-   [ ] Key naming reviewed.
-   [ ] Key ownership clear.
-   [ ] TTL policy reviewed.
-   [ ] Memory use inspected.
-   [ ] Large/unbounded collection risk reviewed.
-   [ ] Schema/version strategy considered.

------------------------------------------------------------------------

## 83. Commands

-   [ ] Safe discovery uses `SCAN`.
-   [ ] `KEYS *` avoided operationally.
-   [ ] Large-key deletion strategy understood.
-   [ ] Conditional-write semantics understood.
-   [ ] Expiration semantics understood.
-   [ ] Multi-key behavior reviewed.

------------------------------------------------------------------------

## 84. Sharding

-   [ ] Primary shards mapped.
-   [ ] Hash-tag usage reviewed.
-   [ ] Low-cardinality tag risk reviewed.
-   [ ] Per-shard CPU reviewed.
-   [ ] Per-shard memory reviewed.
-   [ ] Per-shard operations reviewed.
-   [ ] Hot-shard risk reviewed.

------------------------------------------------------------------------

## 85. Replication

-   [ ] Replication enabled where required.
-   [ ] Primary/replica pairs mapped.
-   [ ] Node separation validated.
-   [ ] Failure-domain separation validated.
-   [ ] Degraded-HA process understood.
-   [ ] Failover implications understood.
-   [ ] RPO/RTO assumptions documented.

------------------------------------------------------------------------

## 86. Proxies

-   [ ] Proxies inventoried.
-   [ ] Proxy health reviewed.
-   [ ] Request path understood.
-   [ ] Endpoint/proxy relationship documented.

------------------------------------------------------------------------

## 87. Administration

-   [ ] UI access follows least privilege.
-   [ ] CLI access follows least privilege.
-   [ ] API access follows least privilege.
-   [ ] TLS verification enabled.
-   [ ] Secrets excluded from code.
-   [ ] Read-only inspection workflow documented.
-   [ ] Change guardrails understood.
-   [ ] Audit requirements understood.

------------------------------------------------------------------------

## 88. Operations

-   [ ] Architecture diagram created.
-   [ ] Risk register created.
-   [ ] Node-loss tabletop completed.
-   [ ] Replica-loss tabletop completed.
-   [ ] Hot-shard tabletop completed.
-   [ ] Endpoint-failure tabletop completed.
-   [ ] API-failure tabletop completed.
-   [ ] Key-design tabletop completed.
-   [ ] Missing-TTL tabletop completed.
-   [ ] Unsafe-command tabletop completed.
-   [ ] Troubleshooting drill completed.
-   [ ] Readiness scorecard completed.
-   [ ] Acceptance decision recorded.

------------------------------------------------------------------------

# Phase 32 --- Cleanup

## 89. Find Only Lab Keys

``` redis
SCAN 0 MATCH 'tutorial:chapter10:*' COUNT 100
```

Iterate until the cursor returns:

``` text
0
```

------------------------------------------------------------------------

## 90. Delete Exact Lab Keys

Use:

``` redis
UNLINK <exact-lab-key>
```

for the keys created by this chapter.

Do not use:

``` redis
FLUSHDB
FLUSHALL
```

------------------------------------------------------------------------

# 91. Part 1 Knowledge Validation

You should now be able to explain:

1.  What Redis Enterprise / Redis Software provides beyond a single
    Redis process.
2.  The difference between cluster, node, database, shard, replica,
    proxy, and endpoint.
3.  How an application connects to a database.
4.  Why DNS, TCP, TLS, authentication, and application behavior are
    separate troubleshooting layers.
5.  How Redis data types influence application design and memory.
6.  Why TTL is part of cache lifecycle engineering.
7.  Why command semantics and complexity matter operationally.
8.  Why `SCAN` is preferred over broad blocking discovery patterns.
9.  How databases are configured and identified.
10. How shards are placed across nodes.
11. Why primary/replica separation matters.
12. Why failure domains matter beyond individual nodes.
13. What the proxy/routing layer does.
14. How hash slots and hash tags influence key placement.
15. Why low-cardinality hash tags can create concentration.
16. The difference between a hot key and hot partition.
17. Why more shards do not fix a single hot key.
18. The difference between sharding and replication.
19. Why replication is not backup.
20. Why application recovery does not necessarily mean HA is fully
    restored.
21. The difference between availability and durability.
22. Why client retry behavior matters during failover.
23. The roles of Cluster Manager, `rladmin`, and REST API.
24. Why administrative automation should be idempotent.
25. Why production acceptance requires evidence rather than assumptions.

------------------------------------------------------------------------

# 92. Part 1 Completion Criteria

Part 1 can be considered complete when the learner can independently:

``` text
discover a Redis Enterprise cluster
inventory its nodes and databases
validate application connectivity
map shards and replicas
map proxies
review failure domains
review key design
review hash-tag strategy
identify shard skew
inspect replication
use UI, rladmin, and REST API
perform a node-loss tabletop
perform evidence-driven troubleshooting
produce a readiness scorecard
```

------------------------------------------------------------------------

# 93. Key Takeaways

1.  Production Redis operations begin with architecture visibility.
2.  A healthy `PING` is only one small part of readiness.
3.  Database topology must be mapped to physical nodes and failure
    domains.
4.  Application connectivity must be validated layer by layer.
5.  Key design, TTL policy, and command semantics are operational
    concerns.
6.  Shard-level metrics matter more than cluster averages when
    diagnosing skew.
7.  Hash tags can intentionally help co-location or accidentally destroy
    distribution.
8.  Replication provides HA but is not a backup.
9.  Service recovery after failover is not complete until redundancy is
    restored.
10. Capacity must account for failures, not only normal operation.
11. UI, `rladmin`, and REST API provide complementary views of the
    platform.
12. Production changes require current-state evidence, validation, and
    auditability.
13. Failure table-tops expose architecture weaknesses before incidents
    do.
14. A maintained architecture diagram and risk register are core SRE
    artifacts.
15. Part 1 establishes the foundation required for deeper caching,
    performance, HA, security, observability, and recovery engineering.

------------------------------------------------------------------------

# 94. References

Validate commands, UI behavior, REST API resources, authentication,
shard behavior, hash-slot semantics, replication behavior, and
administrative procedures against documentation for the exact Redis
Enterprise / Redis Software release deployed.

Key documentation areas:

-   Redis Enterprise architecture
-   Redis Software databases
-   database endpoints
-   Redis data types
-   command reference
-   Redis Cluster specification and hash tags
-   Redis Enterprise sharding
-   replication and high availability
-   rack/zone awareness
-   Cluster Manager
-   `rladmin`
-   Redis Enterprise REST API
-   security and TLS
-   monitoring and alerts

------------------------------------------------------------------------

# Part 1 Status

**Part 1 --- Foundations & Architecture: COMPLETE**

Canonical chapters:

``` text
01 Redis Enterprise Fundamentals & Architecture
02 Connecting to Redis Enterprise — Clients, Endpoints, TLS & Connection Management
03 Redis Data Types, Key Design & Memory-Aware Data Modeling
04 Redis Commands, Command Semantics & Safe Operations
05 Redis Enterprise Databases, Endpoints & Configuration
06 Redis Enterprise Nodes, Shards, Proxies & Placement
07 Hash Slots, Key Distribution & Sharding Internals
08 Replication Architecture & Primary/Replica Behavior
09 Redis Enterprise Administration Interfaces — UI, rladmin & REST API
10 Architecture Inspection & Foundation Acceptance Lab
```

------------------------------------------------------------------------

# Next Chapter

**Chapter 11 --- TTL, Expiration & Cache Freshness Engineering**

Chapter 11 begins:

**Part 2 --- Caching & Application Engineering**

It will cover:

-   TTL architecture
-   expiration semantics
-   active vs passive expiration concepts
-   cache freshness
-   TTL selection
-   TTL jitter
-   stale-data risk
-   synchronized expiration
-   cache avalanche prevention
-   TTL auditing
-   missing-TTL detection
-   expiration labs
-   failure injection
-   production cache-freshness runbooks
