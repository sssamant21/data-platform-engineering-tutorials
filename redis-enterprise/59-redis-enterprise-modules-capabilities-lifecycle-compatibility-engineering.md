# Chapter 59 --- Redis Enterprise Modules / Capabilities Lifecycle & Compatibility Engineering

**Status:** Canonical\
**Track:** Redis Enterprise / Redis Software Production Engineering\
**Part:** Part 10 --- Migration, Data Services & Advanced Capabilities\
**Level:** Advanced → Production Platform Engineering\
**Audience:** SREs, DBREs, Platform Engineers, Redis Administrators,
Developers, Application Architects, Change Managers\
**Lab type:** Capability inventory, dependency mapping, compatibility
matrices, enablement, upgrade qualification, mixed-version testing,
backup/restore validation, migration portability, deprecation
management, rollback, observability, failure injection, troubleshooting,
runbooks, and production acceptance

------------------------------------------------------------------------

# 1. Objective

Redis applications can depend on more than core key/value commands.

A production workload may rely on capabilities such as:

``` text
JSON
Search / Query
Vector Search
probabilistic structures
time-series capabilities
other product/version-specific features
```

The important operational question is not only:

``` text
Does the feature work?
```

It is:

``` text
Is the entire dependency chain compatible,
recoverable, observable, upgradeable, and supportable?
```

A useful model is:

``` text
application
   |
client SDK
   |
commands / data structures
   |
Redis capability
   |
Redis database version
   |
Redis Enterprise software
   |
backup / restore / replication / migration
   |
infrastructure
```

By the end of this chapter, you should be able to:

-   inventory application Redis capabilities;
-   distinguish core-command and advanced-capability dependencies;
-   create a compatibility matrix;
-   map client and server dependencies;
-   qualify feature enablement;
-   test upgrades and mixed-version states;
-   validate persistence and backup/restore behavior;
-   validate HA/DR behavior;
-   assess migration portability;
-   manage deprecations;
-   design rollback;
-   create capability regression suites;
-   troubleshoot compatibility incidents;
-   define production runbooks and acceptance gates.

------------------------------------------------------------------------

# 2. Core Production Principle

Treat every Redis capability used by an application as a production
dependency.

Do not document only:

``` text
Redis version = X
```

Document:

``` text
Redis Enterprise version
Redis database compatibility/version
capabilities/features used
client SDK/version
command/API assumptions
persistence requirements
backup/restore expectations
HA/DR expectations
migration dependencies
```

------------------------------------------------------------------------

# Part 1 --- Capability Inventory

## 3. Start With Usage

Inventory what applications actually use.

Examples:

``` text
GET / SET
HASH
LIST
SET / ZSET
Streams
Pub/Sub
JSON
Search
Vector Search
transactions
Lua / functions where applicable
```

------------------------------------------------------------------------

# Part 2 --- Why Inventory Matters

## 4. Hidden Dependency

An application may appear to use "Redis" but actually require:

``` text
JSON.SET
FT.SEARCH
vector index support
```

A target environment supporting only the application's simple cache
commands would be insufficient.

------------------------------------------------------------------------

# Part 3 --- Command Discovery

## 5. Sources

Build inventory from:

``` text
application code
client wrappers
APM/tracing
command statistics
runbooks
deployment manifests
integration tests
developer interviews
```

No single source is always complete.

------------------------------------------------------------------------

# Part 4 --- Data Structure Inventory

## 6. Record

``` text
STRING
HASH
LIST
SET
ZSET
STREAM
JSON
other supported structures
```

Also record whether the application can rebuild the data.

------------------------------------------------------------------------

# Part 5 --- Capability Classification

## 7. Example

  Capability   Application Use      Criticality
  ------------ -------------------- -------------
  Core KV      session lookup       critical
  Streams      event processing     critical
  JSON         profile documents    high
  Search       product lookup       high
  Vector       semantic retrieval   high

------------------------------------------------------------------------

# Part 6 --- Ownership

## 8. Assign

For each capability define:

``` text
application owner
platform owner
operational owner
upgrade approver
```

Avoid dependencies with no clear owner.

------------------------------------------------------------------------

# Part 7 --- Compatibility Matrix

## 9. Minimum

Track:

``` text
Redis Enterprise version
Redis database/version compatibility
capability
client SDK
application version
```

------------------------------------------------------------------------

# Part 8 --- Example Matrix

## 10. Template

  App          App Version   Client     Redis/DB   Capability   Status
  ------------ ------------- ---------- ---------- ------------ --------
  API          4.2           client-X   target     JSON         PASS
  Search API   7.1           client-Y   target     Search       PASS
  RAG          2.0           client-Z   target     Vector       TEST

Use real product/version data from official support documentation.

------------------------------------------------------------------------

# Part 9 --- Do Not Infer Compatibility

## 11. Rule

Do not assume:

``` text
newer server
=
all old application behavior unchanged
```

or:

``` text
new client
=
compatible with every server feature
```

Validate supported combinations.

------------------------------------------------------------------------

# Part 10 --- Official Support Matrix

## 12. Source of Truth

Use current official Redis/Redis Enterprise documentation for:

``` text
supported versions
feature availability
upgrade paths
known limitations
deprecations
```

Do not use tutorial examples as a substitute for vendor support policy.

------------------------------------------------------------------------

# Part 11 --- Client Compatibility

## 13. More Than Connectivity

A client can connect successfully but still fail on:

``` text
command support
response parsing
cluster/topology behavior
TLS/auth
Search responses
JSON paths
vector binary encoding
```

------------------------------------------------------------------------

# Part 12 --- Client Regression Suite

## 14. Test

For each application client:

``` text
connect
authenticate
read
write
pipeline
transaction where used
JSON where used
Search where used
Vector where used
failover/reconnect
```

------------------------------------------------------------------------

# Part 13 --- Framework Abstraction

## 15. Risk

Application frameworks may wrap Redis clients.

Record both:

``` text
framework version
underlying Redis client version
```

when relevant.

------------------------------------------------------------------------

# Part 14 --- Capability Enablement

## 16. Change

Enabling or adopting a new capability is a production change.

Before enablement define:

``` text
business use case
version support
capacity
security
backup/recovery
monitoring
rollback
```

------------------------------------------------------------------------

# Part 15 --- Feature Readiness

## 17. Gate

Ask:

``` text
Is it supported?
Is the client compatible?
Is capacity sufficient?
Is it backed up?
Can it fail over?
Can it be restored?
Can it be migrated?
Can it be monitored?
```

------------------------------------------------------------------------

# Part 16 --- Lab Namespace

## 18. Safety

Use:

``` text
tutorial:chapter59:*
```

Create only isolated test objects and indexes.

Do not enable/disable production capabilities for a tutorial lab.

------------------------------------------------------------------------

# Part 17 --- Core Baseline Test

## 19. Example

For an approved isolated **nonproduction** database, these are **interactive Redis commands** executed only after an authorized certificate-validated TLS/ACL Redis CLI connection has been established:

``` redis
SET tutorial:chapter59:core "ok" EX 300
GET tutorial:chapter59:core
```

**Expected:** `SET` returns `OK` and `GET` returns `ok`; connection/authentication errors are **FAIL**, not evidence of the module state. The key is a disposable, expiring lab key.

This verifies basic connectivity only.

It does not prove advanced capability compatibility.

------------------------------------------------------------------------

# Part 18 --- JSON Capability Test

## 20. Where Supported

**Prerequisite:** Verify RedisJSON is actually enabled and the deployed engine/module supports JSONPath (`$`, RedisJSON v2), and that the authorized lab identity has the needed `@json` permissions. The commands below run in the **same authenticated, CA-verified TLS Redis CLI session** as the core test, not from an unconfigured local shell:

``` redis
JSON.SET tutorial:chapter59:json '$' '{"status":"ok"}'
JSON.GET tutorial:chapter59:json '$.status'
```

**Expected:** `JSON.SET` returns `OK`; a RedisJSON v2 `JSON.GET` using JSONPath returns an array of matched values (schematically `["ok"]` when parsed from the RESP2 JSON-encoded bulk-string reply). RESP3/client display can differ. This is only a module-capability smoke test, not an index, search, or production certification. A failure can indicate capability/version, ACL, or endpoint problems; log the exact error **without** automatically enabling modules, bypassing TLS, or escalating production permissions. Use only these isolated tutorial keys and leave cleanup ownership explicit.

A failure here can expose capability/version mismatch even when
`GET`/`SET` works.

------------------------------------------------------------------------

# Part 19 --- Search Capability Test

## 21. Where Supported

Create a small isolated source object and Search index using the exact
syntax supported by the deployed version.

Validate:

``` text
index creation
document indexing
query
index inspection
safe index removal
```

------------------------------------------------------------------------

# Part 20 --- Vector Capability Test

## 22. Where Supported

Validate:

``` text
vector field/index creation
dimension/type
write
KNN query
metadata filter
```

Use synthetic vectors.

------------------------------------------------------------------------

# Part 21 --- Streams Capability Test

## 23. Where Used

Validate:

``` text
XADD
XREAD/XREADGROUP
consumer group
acknowledgement
pending recovery
```

according to the application's actual use.

------------------------------------------------------------------------

# Part 22 --- Transaction Test

## 24. Where Used

Validate:

``` text
MULTI
EXEC
WATCH
```

and application-specific atomicity assumptions.

------------------------------------------------------------------------

# Part 23 --- Lua / Server-Side Logic

## 25. Where Used

Inventory:

``` text
scripts/functions
keys touched
runtime assumptions
return types
```

Test against target versions.

------------------------------------------------------------------------

# Part 24 --- Persistence Dependency

## 26. Classify

For each capability/data family define whether data is:

``` text
disposable cache
rebuildable derived data
durable application state
```

This determines recovery requirements.

------------------------------------------------------------------------

# Part 25 --- Backup Contract

## 27. Define

For durable/recovery-required data, specify:

``` text
what is backed up
frequency
retention
encryption
restore procedure
validation
```

------------------------------------------------------------------------

# Part 26 --- Restore Validation

## 28. Not Key Count Only

After restore validate capability behavior.

Examples:

``` text
JSON paths work
Search queries return expected results
vector retrieval works
Streams state is correct
```

------------------------------------------------------------------------

# Part 27 --- Search Recovery

## 29. Validate

Recovery acceptance should include:

``` text
source documents
index definitions/state
query correctness
```

using behavior supported by the deployed version.

------------------------------------------------------------------------

# Part 28 --- Vector Recovery

## 30. Validate

Test:

``` text
vector fields
index schema
KNN query
metadata filters
quality sample
```

------------------------------------------------------------------------

# Part 29 --- Streams Recovery

## 31. Validate

Where business-critical:

``` text
stream entries
consumer groups
pending entries
acknowledgement behavior
```

must meet the recovery contract.

------------------------------------------------------------------------

# Part 30 --- HA Compatibility

## 32. Failover

A capability must work through the deployment's HA model.

Test:

``` text
core reads/writes
JSON
Search
Vector
Streams
```

that are actually production-critical.

------------------------------------------------------------------------

# Part 31 --- Client Failover

## 33. Measure

During failover record:

``` text
connection errors
retry
reconnect
P99
recovery time
duplicate effects
```

------------------------------------------------------------------------

# Part 32 --- DR Compatibility

## 34. Remote Recovery

A DR environment must support the same required capability contract.

Do not discover during disaster recovery that the target environment
lacks a required feature/version.

------------------------------------------------------------------------

# Part 33 --- Active-Active / Geo Features

## 35. Validate Separately

Not every data type or capability necessarily has identical behavior in
every geo-distributed topology/version.

Validate the exact supported matrix and application semantics.

------------------------------------------------------------------------

# Part 34 --- Upgrade Dependency Map

## 36. Before Upgrade

Record:

``` text
current platform version
target platform version
database versions
capabilities
client versions
application versions
```

------------------------------------------------------------------------

# Part 35 --- Upgrade Release Review

## 37. Read

Review official:

``` text
release notes
upgrade guidance
breaking changes
deprecations
known issues
```

for every relevant version hop.

------------------------------------------------------------------------

# Part 36 --- Upgrade Lab

## 38. Reproduce Production Capability Set

A useful upgrade lab should contain representative:

``` text
core keys
Streams
JSON
Search
Vector
scripts
```

only for features actually used.

------------------------------------------------------------------------

# Part 37 --- Pre-Upgrade Baseline

## 39. Record

``` text
functional test results
P99
memory
CPU
Search result set
vector recall sample
stream state
```

------------------------------------------------------------------------

# Part 38 --- Post-Upgrade Validation

## 40. Compare

Run the same suite after upgrade.

Classify differences:

``` text
expected
benign
performance regression
functional regression
data incompatibility
```

------------------------------------------------------------------------

# Part 39 --- Mixed-Version State

## 41. Maintenance Window

During rolling changes, the environment may temporarily contain mixed
software versions where supported.

Validate only states explicitly supported by vendor guidance.

Do not intentionally create unsupported mixed-version combinations.

------------------------------------------------------------------------

# Part 40 --- Mixed Client Versions

## 42. Rolling Application Deployment

Old and new application/client versions may run simultaneously.

Test both against the target Redis environment.

------------------------------------------------------------------------

# Part 41 --- Schema Compatibility

## 43. JSON/Search

An application upgrade may change:

``` text
JSON field
JSONPath
Search field
field type
index name
```

Server compatibility alone does not guarantee application compatibility.

------------------------------------------------------------------------

# Part 42 --- Vector Model Compatibility

## 44. Separate Contract

Vector workloads also depend on:

``` text
embedding model
dimension
numeric type
distance metric
```

Treat these as application-data compatibility dependencies.

------------------------------------------------------------------------

# Part 43 --- Migration Portability

## 45. Inventory

Before moving environments/providers/clusters, determine whether the
target supports:

``` text
commands
data structures
capabilities
index definitions
persistence behavior
HA behavior
```

------------------------------------------------------------------------

# Part 44 --- Data Copy Is Not Enough

## 46. Example

Copying source keys without recreating or validating:

``` text
Search index
vector index
capability configuration
```

can leave the application nonfunctional.

------------------------------------------------------------------------

# Part 45 --- Migration Acceptance

## 47. Validate

``` text
key count/sample
data types
TTL
JSON
Search
Vector
Streams
scripts
client behavior
performance
```

as applicable.

------------------------------------------------------------------------

# Part 46 --- Downgrade / Rollback

## 48. High Risk

A rollback is not simply:

``` text
install old version
```

if the newer version has changed:

``` text
data format
capability state
index state
configuration
```

Use vendor-supported rollback procedures only.

------------------------------------------------------------------------

# Part 47 --- Rollback Gate

## 49. Before Change

Document:

``` text
rollback supported?
rollback deadline?
backup required?
restore required?
data written after upgrade?
client compatibility?
```

------------------------------------------------------------------------

# Part 48 --- Point of No Return

## 50. Explicit

Some changes may create a point after which rollback requires
restore/migration rather than simple software reversal.

Identify it before the change.

------------------------------------------------------------------------

# Part 49 --- Deprecation Management

## 51. Inventory

Track:

``` text
deprecated command
deprecated API
deprecated configuration
deprecated capability/version
```

------------------------------------------------------------------------

# Part 50 --- Deprecation Lifecycle

## 52. Process

``` text
detect
assign owner
identify consumers
define replacement
test
migrate
verify
remove
```

------------------------------------------------------------------------

# Part 51 --- Client Deprecations

## 53. Watch

A client SDK may deprecate:

``` text
method
connection option
response type
API abstraction
```

even when the server command remains available.

------------------------------------------------------------------------

# Part 52 --- Feature Flags

## 54. Useful Pattern

Where application architecture allows, a feature flag can help control
adoption of a new Redis capability.

Example:

``` text
search_v2_enabled
```

This can improve canary and rollback control.

------------------------------------------------------------------------

# Part 53 --- Canary

## 55. Reduce Risk

Canary:

``` text
small application traffic
small tenant group
small workload percentage
```

before broad rollout.

------------------------------------------------------------------------

# Part 54 --- Dual Read

## 56. Validation Pattern

For selected migrations:

``` text
read old path
read new path
compare
```

without making both authoritative.

Use carefully to control extra load.

------------------------------------------------------------------------

# Part 55 --- Shadow Query

## 57. Search / Vector

Send a copy of representative queries to the new index/capability
without serving its results to users.

Compare:

``` text
correctness
latency
errors
```

------------------------------------------------------------------------

# Part 56 --- Dual Write

## 58. Caution

Writing old and new formats simultaneously can support migration but
introduces:

``` text
consistency risk
retry complexity
rollback complexity
```

Use idempotency and reconciliation.

------------------------------------------------------------------------

# Part 57 --- Capability-Specific SLO

## 59. Define

Examples:

``` text
JSON P99
Search P99
Vector P99 + recall
Stream processing lag
```

Do not hide all behavior behind one Redis availability metric.

------------------------------------------------------------------------

# Part 58 --- Observability

## 60. Platform

Track:

``` text
CPU
memory
network
connections
replication
persistence
errors
```

------------------------------------------------------------------------

# Part 59 --- Capability Metrics

## 61. Examples

``` text
Search query P99
Search index memory
vector query P99
vector recall evaluation
ingestion lag
stream pending count
JSON document growth
```

------------------------------------------------------------------------

# Part 60 --- Application Errors

## 62. Classify

Separate:

``` text
unknown command
syntax error
unsupported option
type error
auth error
timeout
connection error
schema mismatch
```

Compatibility incidents become easier to diagnose.

------------------------------------------------------------------------

# Part 61 --- Unknown Command

## 63. Signal

An `unknown command` error after migration/upgrade may indicate:

``` text
missing capability
wrong endpoint
version mismatch
feature unavailable
```

Do not retry indefinitely.

------------------------------------------------------------------------

# Part 62 --- Response Shape Change

## 64. Client Risk

Even when a command succeeds, application parsing can fail if the client
or command response assumptions changed.

Regression tests must validate parsed application behavior.

------------------------------------------------------------------------

# Part 63 --- Performance Compatibility

## 65. Functional PASS Is Not Enough

A new version may be functionally correct but have different:

``` text
latency
memory
CPU
index size
```

Qualification must include performance.

------------------------------------------------------------------------

# Part 64 --- Capacity Compatibility

## 66. New Capability

Before enabling Search/Vector/other memory-intensive capabilities,
include their overhead in capacity planning.

------------------------------------------------------------------------

# Part 65 --- Security Compatibility

## 67. Validate

Changes can affect:

``` text
authentication
ACLs
TLS
certificates
client options
permissions
```

Run security-path tests.

------------------------------------------------------------------------

# Part 66 --- ACL Command Permissions

## 68. Capability Commands

If applications use advanced commands, their ACL policy must allow
exactly the required operations.

Do not grant broad command access merely to make a new feature work.

------------------------------------------------------------------------

# Part 67 --- Backup Compatibility

## 69. Upgrade

Before major changes, confirm backups are:

``` text
current
restorable
compatible with the planned recovery path
```

A backup that has never been restore-tested is weak evidence.

------------------------------------------------------------------------

# Part 68 --- Restore Drill

## 70. Procedure

In an isolated environment:

``` text
restore
connect
validate core data
validate capabilities
validate clients
validate performance sample
```

------------------------------------------------------------------------

# Part 69 --- Test Matrix

## 71. Dimensions

A full matrix may include:

``` text
old client + old server
old client + new server
new client + old server
new client + new server
```

Only test combinations that are relevant and supported.

------------------------------------------------------------------------

# Part 70 --- Change Sequencing

## 72. Example

A safer sequence may be:

``` text
1. deploy clients compatible with both old/new server
2. upgrade Redis
3. validate
4. enable new capability
5. migrate application usage
6. remove old compatibility code
```

The exact sequence depends on support constraints.

------------------------------------------------------------------------

# Part 71 --- Dependency Graph

## 73. Visualize

``` text
App v5
 |
 +-- redis-client 6.x
 |
 +-- JSON
 |    +-- schema v3
 |
 +-- Search
      +-- idx:product:v2
```

This makes change impact clearer.

------------------------------------------------------------------------

# Part 72 --- Configuration as Code

## 74. Prefer

Where supported, keep capability-related definitions in controlled
configuration/code:

``` text
index schemas
ACL definitions
client settings
alerts
dashboards
```

Avoid undocumented manual state.

------------------------------------------------------------------------

# Part 73 --- Drift Detection

## 75. Compare

Detect differences between:

``` text
expected index schema
actual index schema
expected ACL
actual ACL
expected version
actual version
```

------------------------------------------------------------------------

# Part 74 --- Environment Parity

## 76. Staging

Staging should reproduce the capability set needed for production
qualification.

A staging environment without Search cannot meaningfully qualify a
Search-dependent release.

------------------------------------------------------------------------

# Part 75 --- Lower-Environment Limits

## 77. Document

If staging is smaller than production, document which conclusions can
and cannot be drawn.

Functional compatibility may be validated even when full-scale capacity
cannot.

------------------------------------------------------------------------

# Part 76 --- Failure Scenario 1

## 78. Missing Capability

Point a synthetic test at an environment without the required
capability.

Validate:

``` text
clear error
no retry storm
deployment gate fails
```

------------------------------------------------------------------------

# Part 77 --- Failure Scenario 2

## 79. Old Client

Run an intentionally older supported test client against the target lab.

Validate required command behavior.

------------------------------------------------------------------------

# Part 78 --- Failure Scenario 3

## 80. Unsupported Combination

Do not intentionally deploy unsupported production combinations.

Instead, use documentation/test fixtures to verify deployment gates
reject an unsupported version matrix.

------------------------------------------------------------------------

# Part 79 --- Failure Scenario 4

## 81. JSON Schema Change

Change a synthetic JSON field/path.

Validate application/Search compatibility tests detect it.

------------------------------------------------------------------------

# Part 80 --- Failure Scenario 5

## 82. Search Index Missing

Remove only an isolated lab Search index.

Validate health checks detect functional failure.

------------------------------------------------------------------------

# Part 81 --- Failure Scenario 6

## 83. Vector Dimension Change

Change the synthetic embedding dimension.

Validate deployment/migration gates fail before production use.

------------------------------------------------------------------------

# Part 82 --- Failure Scenario 7

## 84. Restore Without Functional Validation

Simulate a restore acceptance process that checks only key count.

Show why capability queries must also be executed.

------------------------------------------------------------------------

# Part 83 --- Failure Scenario 8

## 85. ACL Missing Command

Remove an advanced command permission from a lab-only principal.

Validate least-privilege troubleshooting.

------------------------------------------------------------------------

# Part 84 --- Failure Scenario 9

## 86. Performance Regression

Introduce a controlled heavier index/query configuration.

Validate regression thresholds detect increased P99/memory.

------------------------------------------------------------------------

# Part 85 --- Failure Scenario 10

## 87. Rollback Incompatibility

Use a tabletop exercise to identify a change whose rollback would
require restore/rebuild.

Validate the point-of-no-return gate.

------------------------------------------------------------------------

# Part 86 --- Troubleshooting Matrix

## 88. Common Problems

  -----------------------------------------------------------------------
  Symptom                             Investigate
  ----------------------------------- -----------------------------------
  unknown command                     capability, endpoint, server
                                      version

  client parse failure                client version, response
                                      assumptions

  JSON works but Search fails         Search capability/index/schema

  Search data missing                 prefix, index state, migration

  vector query fails                  dimension/type/index/model

  restore keys exist but app fails    capability/index/client validation

  upgrade increases P99               version regression, config,
                                      capacity

  ACL denies advanced command         command categories/permissions

  DR app fails                        target capability/version parity

  rollback blocked                    data/config format, support policy
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# Part 87 --- Runbook 1: Capability Inventory

## 89. Procedure

``` text
1. list applications.
2. inspect client dependencies.
3. inventory commands/data structures.
4. identify advanced capabilities.
5. classify criticality.
6. assign owners.
7. record versions.
8. store compatibility matrix.
```

------------------------------------------------------------------------

# Part 88 --- Runbook 2: New Capability Enablement

## 90. Procedure

``` text
1. document use case.
2. validate official support.
3. validate client.
4. estimate capacity.
5. define security.
6. define backup/recovery.
7. run lab/canary.
8. approve production enablement.
```

------------------------------------------------------------------------

# Part 89 --- Runbook 3: Upgrade Compatibility

## 91. Procedure

``` text
1. inventory dependency graph.
2. review release/support docs.
3. create representative lab.
4. capture baseline.
5. upgrade.
6. run functional/performance suite.
7. test failover/recovery.
8. approve or rollback.
```

------------------------------------------------------------------------

# Part 90 --- Runbook 4: Client Upgrade

## 92. Procedure

``` text
1. record old/new client.
2. review client release notes.
3. run command regression.
4. run TLS/auth tests.
5. run capability tests.
6. run failover test.
7. canary.
8. roll out with rollback window.
```

------------------------------------------------------------------------

# Part 91 --- Runbook 5: Backup/Restore Compatibility

## 93. Procedure

``` text
1. restore isolated backup.
2. validate key/data samples.
3. validate TTL.
4. validate JSON/Search/Vector/Streams used.
5. run client suite.
6. run query-quality sample.
7. record RTO/RPO evidence.
8. approve recovery path.
```

------------------------------------------------------------------------

# Part 92 --- Runbook 6: Migration Compatibility

## 94. Procedure

``` text
1. inventory source capabilities.
2. validate target support.
3. migrate sample.
4. recreate/validate indexes/config.
5. run client tests.
6. run performance tests.
7. run cutover rehearsal.
8. approve migration.
```

------------------------------------------------------------------------

# Part 93 --- Runbook 7: Deprecation

## 95. Procedure

``` text
1. identify deprecated dependency.
2. locate consumers.
3. assign owner/deadline.
4. implement replacement.
5. dual/shadow test if appropriate.
6. migrate.
7. verify no usage.
8. remove old dependency.
```

------------------------------------------------------------------------

# Part 94 --- Runbook 8: Compatibility Incident

## 96. Procedure

``` text
1. identify failing application/capability.
2. record versions.
3. capture exact error.
4. compare support matrix.
5. test minimal command.
6. apply supported remediation.
7. validate full capability path.
8. document RCA/prevention.
```

------------------------------------------------------------------------

# Part 95 --- Capability Inventory Template

## 97. Record

``` text
Application:
Owner:
Criticality:
Redis endpoint/database:
Redis Enterprise version:
Database/version:
Client/framework:
Data structures:
Capabilities:
Indexes:
Scripts/functions:
Persistence requirement:
Backup requirement:
DR requirement:
```

------------------------------------------------------------------------

# Part 96 --- Compatibility Matrix Template

## 98. Record

``` text
Application version:
Client version:
Redis Enterprise version:
Database version:
Capability:
Feature/schema version:
Supported by vendor:
Functional test:
Performance test:
Failover test:
Restore test:
Status:
```

------------------------------------------------------------------------

# Part 97 --- Change Template

## 99. Record

``` text
Change:
Current versions:
Target versions:
Capabilities affected:
Applications affected:
Support evidence:
Capacity impact:
Security impact:
Backup status:
Test evidence:
Canary:
Rollback:
Point of no return:
Approval:
```

------------------------------------------------------------------------

# Part 98 --- Production Acceptance

## 100. Inventory

-   [ ] applications inventoried;
-   [ ] clients/frameworks inventoried;
-   [ ] commands/data structures inventoried;
-   [ ] advanced capabilities inventoried;
-   [ ] owners assigned;
-   [ ] criticality defined.

## 101. Compatibility

-   [ ] official support matrix reviewed;
-   [ ] application/client/server matrix documented;
-   [ ] unsupported combinations blocked;
-   [ ] schema/model dependencies documented;
-   [ ] mixed-version states reviewed;
-   [ ] deprecations tracked.

## 102. Functional

-   [ ] core commands tested;
-   [ ] Streams tested where used;
-   [ ] JSON tested where used;
-   [ ] Search tested where used;
-   [ ] Vector tested where used;
-   [ ] scripts/functions tested where used;
-   [ ] ACL/TLS/auth tested.

## 103. Resilience

-   [ ] persistence contract defined;
-   [ ] backup tested;
-   [ ] restore tested;
-   [ ] capability behavior tested after restore;
-   [ ] failover tested;
-   [ ] DR parity validated;
-   [ ] migration portability validated.

## 104. Change Management

-   [ ] pre-upgrade baseline recorded;
-   [ ] post-upgrade regression completed;
-   [ ] client regression completed;
-   [ ] performance comparison completed;
-   [ ] rollback documented;
-   [ ] point of no return documented;
-   [ ] canary defined;
-   [ ] eight runbooks reviewed;
-   [ ] ten failure scenarios completed.

------------------------------------------------------------------------

# 105. Knowledge Validation

1.  Why should Redis capabilities be treated as production dependencies?
2.  Why is "Redis version" alone insufficient documentation?
3.  What sources can reveal capability usage?
4.  Why assign capability ownership?
5.  What belongs in a compatibility matrix?
6.  Why should compatibility not be inferred from version numbers?
7.  Why can a client connect yet still be incompatible?
8.  Why record framework and underlying client versions?
9.  What should be checked before enabling a new capability?
10. Why does `GET`/`SET` success not validate JSON/Search?
11. Why classify data as cache, derived, or durable?
12. Why must restore validation test capability behavior?
13. Why must DR have capability parity?
14. Why review release notes before upgrades?
15. Why capture a pre-upgrade baseline?
16. Why can mixed client versions matter?
17. Why is JSON/Search schema part of compatibility?
18. Why is embedding model/dimension part of vector compatibility?
19. Why is copying Redis keys alone insufficient for some migrations?
20. Why can rollback be more complex than reinstalling old software?
21. What is a point of no return?
22. How should deprecations be managed?
23. How can feature flags reduce rollout risk?
24. What is shadow querying?
25. Why is dual write risky?
26. Why should SLOs be capability-specific?
27. What does an unknown-command error suggest?
28. Why include performance in compatibility testing?
29. Why test ACL permissions for advanced commands?
30. What must pass before a capability/version change is
    production-ready?

------------------------------------------------------------------------

# 106. Hands-On Acceptance Checklist

-   [ ] Built application capability inventory.
-   [ ] Built client/server compatibility matrix.
-   [ ] Assigned capability owners.
-   [ ] Ran core baseline.
-   [ ] Ran JSON test where supported.
-   [ ] Ran Search test where supported.
-   [ ] Ran Vector test where supported.
-   [ ] Ran Streams test where used.
-   [ ] Ran transaction/script tests where used.
-   [ ] Classified persistence requirements.
-   [ ] Validated backup/restore path.
-   [ ] Validated capability behavior after restore.
-   [ ] Tested failover.
-   [ ] Validated DR parity.
-   [ ] Reviewed upgrade release/support docs.
-   [ ] Captured pre-upgrade baseline.
-   [ ] Ran post-upgrade regression.
-   [ ] Tested relevant mixed client versions.
-   [ ] Validated schema compatibility.
-   [ ] Validated vector model compatibility.
-   [ ] Validated migration portability.
-   [ ] Documented rollback.
-   [ ] Identified point of no return.
-   [ ] Built deprecation inventory.
-   [ ] Tested canary/shadow strategy.
-   [ ] Tested missing capability detection.
-   [ ] Tested ACL failure.
-   [ ] Tested performance-regression gate.
-   [ ] Completed ten failure scenarios.
-   [ ] Completed eight runbooks.
-   [ ] Completed production acceptance.

------------------------------------------------------------------------

# 107. Cleanup

List Chapter 59 lab keys:

``` bash
redis-cli --scan --pattern 'tutorial:chapter59:*'
```

Review matches and remove only confirmed disposable keys with `UNLINK`.

Remove isolated lab indexes using the exact safe index-drop syntax
supported by the deployed version.

Remove:

``` text
temporary test principals
temporary ACL changes
temporary feature flags
temporary dashboards
temporary test indexes
synthetic compatibility data
```

Restore all lab-only permission changes.

Never use `FLUSHDB` or `FLUSHALL` against a shared or production
database.

------------------------------------------------------------------------

# 108. Key Takeaways

1.  Redis capabilities are application dependencies, not optional
    platform trivia.
2.  Inventory commands, structures, advanced capabilities, clients, and
    schemas.
3.  Compatibility must be validated across application, client, server,
    and feature layers.
4.  Successful connection does not prove functional compatibility.
5.  Official support documentation is the source of truth for supported
    combinations.
6.  New capability adoption requires capacity, security, recovery, and
    rollback planning.
7.  Core `GET`/`SET` tests do not validate JSON, Search, Vector, or
    Streams.
8.  Persistence requirements depend on whether data is cache, derived,
    or durable.
9.  Restore acceptance must validate application capability behavior.
10. HA and DR tests must include capabilities the application actually
    depends on.
11. Upgrade labs should reproduce the production capability set.
12. Capture pre-change functional and performance baselines.
13. Rolling deployments can create mixed client/application states.
14. JSON paths, Search schemas, and vector contracts are compatibility
    dependencies.
15. Migration must move or recreate more than keys when
    indexes/configuration are involved.
16. Rollback may require restore or rebuild after a point of no return.
17. Deprecations need owners, deadlines, replacements, and verification.
18. Feature flags, canaries, and shadow queries can reduce migration
    risk.
19. Dual writes add consistency and rollback complexity.
20. Capability-specific SLOs reveal problems hidden by generic Redis
    health.
21. Unknown-command and parsing errors should be classified rather than
    blindly retried.
22. Functional compatibility does not prove performance compatibility.
23. Advanced commands require least-privilege ACL validation.
24. Configuration as code and drift detection improve repeatability.
25. Production readiness requires compatibility, functionality,
    performance, security, recovery, migration, and rollback evidence
    together.

------------------------------------------------------------------------

# 109. References

Validate capability names, availability, upgrade paths, compatibility,
backup/restore behavior, and deprecation status against the exact
deployed Redis/Redis Enterprise version and current official Redis
documentation.

Recommended documentation areas:

-   Redis Enterprise release notes
-   Redis Enterprise upgrade documentation
-   Redis compatibility and support matrices
-   Redis commands
-   Redis JSON
-   Redis Query Engine / Search
-   Redis Vector Search
-   Redis Streams
-   Redis scripting/functions
-   Redis ACL
-   Redis Enterprise backup/restore
-   Redis Enterprise Active-Active
-   Redis Enterprise migration guidance
-   Redis client documentation and release notes

------------------------------------------------------------------------

# Next Chapter

**Chapter 60 --- Redis Enterprise Auto Tiering / Flex Architecture &
Operations**

Chapter 60 will cover RAM/flash tiering architecture, hot/cold data
behavior, working-set engineering, flash storage requirements, latency
implications, capacity sizing, persistence interactions, shard
placement, scaling, observability, failure behavior, benchmarking,
troubleshooting, operational runbooks, and production acceptance.
