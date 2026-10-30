# Chapter 09 --- Redis Enterprise Administration Interfaces: UI, `rladmin` & REST API

**Status:** Canonical\
**Track:** Redis Enterprise / Redis Software Production Engineering\
**Level:** Foundation → Production Administration\
**Audience:** Redis Administrators, SREs, DBREs, Platform Engineers,
Automation Engineers\
**Lab type:** Cluster inspection, database/node/shard/proxy
administration, REST API exploration, secure credential handling,
failure injection, automation design, and production runbooks

------------------------------------------------------------------------

# 1. Objective

Redis Enterprise / Redis Software provides multiple administration
interfaces.

The three most important operational interfaces are:

``` text
Cluster Manager UI
rladmin
REST API
```

Each serves a different purpose.

A production operator should know:

``` text
which interface to use
which operations are read-only
which operations can change production
how authentication is handled
how to inspect cluster topology
how to inspect databases
how to inspect nodes/shards/proxies
how to automate safely
how to validate changes
how to preserve auditability
```

This chapter focuses on administration rather than application Redis
commands.

By the end, you should be able to:

-   Explain the purpose of Cluster Manager.
-   Use `rladmin` for operational inspection.
-   Understand the Redis Enterprise REST API model.
-   Distinguish data-plane commands from management-plane operations.
-   Build a read-only inspection workflow.
-   Secure administrative credentials.
-   Inspect cluster, database, node, shard, and proxy state.
-   Parse REST API responses.
-   Handle API failures safely.
-   Design idempotent automation.
-   Prevent configuration drift.
-   Build pre-change and post-change validation.
-   Create administration runbooks.

------------------------------------------------------------------------

# Part 1 --- Management Plane vs Data Plane

## 2. Data Plane

Application clients normally interact with Redis through the database
endpoint.

Examples:

``` redis
GET key
SET key value
HGET hash field
ZADD leaderboard 100 user1
```

Conceptually:

``` text
Application
   |
   v
Database Endpoint
   |
   v
Redis Data
```

This is the data path.

------------------------------------------------------------------------

## 3. Management Plane

Administration operations manage the Redis Enterprise platform.

Examples:

``` text
inspect cluster
inspect database
inspect nodes
inspect shards
change database configuration
manage cluster resources
review alerts
perform maintenance
```

Conceptually:

``` text
Administrator / Automation
        |
        v
Management Interface
        |
        +-- Cluster
        +-- Databases
        +-- Nodes
        +-- Shards
        +-- Proxies
```

------------------------------------------------------------------------

## 4. Keep the Two Separate

Do not use application credentials for cluster administration unless the
security design explicitly requires it.

Prefer separation:

``` text
Application identity
    -> database access

Operator identity
    -> management access

Automation identity
    -> narrowly scoped management access
```

This supports least privilege and auditability.

------------------------------------------------------------------------

# Part 2 --- Cluster Manager UI

## 5. Purpose

The Cluster Manager UI provides a graphical administration interface.

Typical areas include:

``` text
cluster health
databases
nodes
alerts
configuration
security
metrics
maintenance
```

Exact navigation and labels vary by Redis Enterprise / Redis Software
release.

------------------------------------------------------------------------

## 6. When the UI Is Useful

The UI is particularly useful for:

``` text
visual inspection
learning topology
reviewing configuration
incident triage
one-time approved changes
checking alerts
reviewing database status
```

It is often the easiest interface for humans to understand current
state.

------------------------------------------------------------------------

## 7. UI Limitations for Automation

A graphical interface is not ideal for repeatable infrastructure
automation.

Avoid operational processes that require:

``` text
human clicks
manual screenshots
copy/paste values
```

for every deployment.

For repeatable workflows, use supported APIs and automation with
appropriate controls.

------------------------------------------------------------------------

# Part 3 --- `rladmin`

## 8. What Is `rladmin`?

`rladmin` is an administrative command-line tool for Redis Enterprise /
Redis Software self-managed environments.

It provides access to cluster administration and inspection.

A common starting command is:

``` bash
rladmin status
```

------------------------------------------------------------------------

## 9. `rladmin status`

Run:

``` bash
rladmin status
```

Use it to establish an initial operational picture.

Look for:

``` text
nodes
databases
shards
cluster state
warnings
```

Exact formatting varies by release.

------------------------------------------------------------------------

## 10. Information Commands

Depending on release, useful inspection patterns include:

``` bash
rladmin info cluster
rladmin info db
rladmin info node
rladmin info shard
rladmin info proxy
```

Before scripting them, verify exact syntax and output for your installed
release.

------------------------------------------------------------------------

# Part 4 --- Safe CLI Workflow

## 11. Start Read-Only

During an incident, begin with inspection. On an **authorized Redis Software/Enterprise cluster node with `rladmin` installed**, confirm the intended cluster and the installed utility version before issuing these read-only commands. `rladmin` is a cluster administration utility, not the ordinary Redis database endpoint client.

Example (use only the subcommands supported by your installed release):

``` bash
rladmin status
rladmin info db
rladmin info node
rladmin info shard
rladmin info proxy
```

**Expected:** `status` describes the cluster state; each supported `info` command prints product-specific database, node, shard or proxy information. Exact fields vary by release and privileges—capture the actual output, do not assert a fixed healthy status, and mark unsupported/unauthorized subcommands as `NOT EXECUTED` or `FAIL` with evidence. These commands are for **inspection only** and must not be used as proof that the application data path is healthy.

Do not begin by changing configuration.

------------------------------------------------------------------------

## 12. Capture Before Change

Before any approved administrative modification capture:

``` text
timestamp
cluster state
database state
node state
shard state
replication state
endpoint health
latency
error rate
current configuration
```

This is your rollback and comparison baseline.

------------------------------------------------------------------------

# Part 5 --- REST API

## 13. Why the REST API Matters

The REST API enables:

``` text
automation
inventory
configuration inspection
monitoring integration
drift detection
controlled administrative workflows
```

It is the primary conceptual bridge between manual administration and
platform engineering.

------------------------------------------------------------------------

## 14. API Endpoint

In self-managed Redis Enterprise deployments, management APIs are
exposed through the cluster management endpoint.

Conceptual form:

``` text
https://<cluster-manager>:9443
```

The exact endpoint, port, authentication, and API behavior must be
validated against your deployed release.

------------------------------------------------------------------------

# Part 6 --- REST Resources

## 15. Common Resource Categories

Conceptual resources include:

``` text
/v1/cluster
/v1/nodes
/v1/bdbs
/v1/shards
/v1/proxies
```

`bdbs` refers to database resources in Redis Enterprise API terminology.

Do not assume every field or endpoint remains identical across releases.

------------------------------------------------------------------------

## 16. Cluster Resource

Conceptual:

``` bash
curl \
  --cacert /path/to/ca.pem \
  -u '<admin-user>:<admin-password>' \
  https://<cluster-manager>:9443/v1/cluster
```

Use secure credential handling rather than embedding passwords in
scripts.

------------------------------------------------------------------------

## 17. Database Resources

Conceptual:

``` bash
curl \
  --cacert /path/to/ca.pem \
  -u '<admin-user>:<admin-password>' \
  https://<cluster-manager>:9443/v1/bdbs
```

This can provide a database inventory.

------------------------------------------------------------------------

## 18. Node Resources

Conceptual:

``` bash
curl \
  --cacert /path/to/ca.pem \
  -u '<admin-user>:<admin-password>' \
  https://<cluster-manager>:9443/v1/nodes
```

------------------------------------------------------------------------

## 19. Shard Resources

Conceptual:

``` bash
curl \
  --cacert /path/to/ca.pem \
  -u '<admin-user>:<admin-password>' \
  https://<cluster-manager>:9443/v1/shards
```

------------------------------------------------------------------------

## 20. Proxy Resources

Conceptual:

``` bash
curl \
  --cacert /path/to/ca.pem \
  -u '<admin-user>:<admin-password>' \
  https://<cluster-manager>:9443/v1/proxies
```

------------------------------------------------------------------------

# Part 7 --- Secure Authentication

## 21. Avoid Credentials in Command History

This:

``` bash
curl -u admin:SuperSecretPassword ...
```

can expose credentials through:

``` text
shell history
process inspection
logs
screenshots
documentation
```

Use an approved secret-management workflow.

------------------------------------------------------------------------

## 22. Environment Variables

For a training environment:

``` bash
export RE_USER='<admin-user>'
export RE_PASSWORD='<admin-password>'
```

Then:

``` bash
curl \
  --cacert /path/to/ca.pem \
  -u "$RE_USER:$RE_PASSWORD" \
  https://<cluster-manager>:9443/v1/cluster
```

After:

``` bash
unset RE_PASSWORD
```

Environment variables are not automatically a perfect secret store.

Production automation should use the organization's approved secrets
platform.

------------------------------------------------------------------------

## 23. Secret Managers

Preferred production patterns can include:

``` text
Kubernetes Secret / external secret integration
cloud secret manager
vault product
CI/CD protected secret
workload identity where supported
```

Principle:

> Administrative secrets should not live in source code.

------------------------------------------------------------------------

# Part 8 --- TLS Verification

## 24. Verify Certificates

Use:

``` bash
curl --cacert /path/to/ca.pem ...
```

or the platform's trusted CA configuration.

Do not normalize:

``` bash
curl -k
```

as a permanent production solution.

Skipping certificate verification hides:

``` text
wrong endpoint
untrusted certificate
MITM risk
certificate-chain problems
```

------------------------------------------------------------------------

# Part 9 --- HTTP Methods

## 25. GET

Typically used to retrieve state.

Conceptually:

``` text
GET /v1/bdbs
```

This is the safest starting point for API learning.

------------------------------------------------------------------------

## 26. POST

Often used to create resources or initiate actions.

Conceptually:

``` text
POST
```

can change production.

Do not experiment with it against production.

------------------------------------------------------------------------

## 27. PUT

Often represents replacement/update semantics depending on the API.

Validate exact behavior before use.

------------------------------------------------------------------------

## 28. PATCH

Where supported, may modify selected resource properties.

Do not assume PATCH is always available or safe.

------------------------------------------------------------------------

## 29. DELETE

Can remove a resource.

Treat it as destructive.

Never test DELETE against a production resource for tutorial purposes.

------------------------------------------------------------------------

# Part 10 --- HTTP Status Codes

## 30. Success

Common:

``` text
200 OK
201 Created
202 Accepted
204 No Content
```

Exact meaning depends on the operation.

------------------------------------------------------------------------

## 31. Client Errors

Examples:

``` text
400 Bad Request
401 Unauthorized
403 Forbidden
404 Not Found
409 Conflict
```

Do not automatically retry all 4xx responses.

Many indicate a request/configuration problem.

------------------------------------------------------------------------

## 32. Server Errors

Examples:

``` text
500
502
503
```

These require investigation.

Blind high-frequency retries can amplify an outage.

------------------------------------------------------------------------

# Part 11 --- Inspecting JSON

## 33. `jq`

Example:

``` bash
curl ... https://<cluster-manager>:9443/v1/bdbs | jq
```

Filter:

``` bash
curl ... https://<cluster-manager>:9443/v1/bdbs |
jq '.[] | {uid, name}'
```

Field names are illustrative.

Verify actual response schema.

------------------------------------------------------------------------

## 34. Save a Baseline

Example:

``` bash
curl ... https://<cluster-manager>:9443/v1/bdbs \
  > bdbs-before.json
```

After an approved change:

``` bash
curl ... https://<cluster-manager>:9443/v1/bdbs \
  > bdbs-after.json
```

Compare:

``` bash
diff bdbs-before.json bdbs-after.json
```

For real automation, normalize volatile fields before diffing.

------------------------------------------------------------------------

# Part 12 --- Inventory Automation

## 35. Why Inventory Matters

A production platform should be able to answer:

``` text
What databases exist?
Who owns them?
How much memory is allocated?
How many shards?
Is replication enabled?
What is the endpoint?
Which nodes host them?
```

The REST API can support this inventory.

------------------------------------------------------------------------

## 36. Example Inventory Model

Create a normalized record:

``` json
{
  "database": "customer-cache",
  "environment": "production",
  "owner": "customer-platform",
  "memory_gb": 100,
  "primary_shards": 4,
  "replication": true
}
```

Do not copy unknown API fields directly into long-lived automation
without schema validation.

------------------------------------------------------------------------

# Part 13 --- Read vs Change Operations

## 37. Read-Only First

Production automation should distinguish:

``` text
inventory
validation
drift detection
```

from:

``` text
create
update
delete
maintenance
```

A read-only service account is preferable for workflows that only need
inspection, where supported.

------------------------------------------------------------------------

## 38. Change Guardrails

A change workflow should include:

``` text
current state
desired state
diff
approval
execution
verification
rollback
audit record
```

Do not write:

``` text
API script that always sends configuration
```

without checking current state.

------------------------------------------------------------------------

# Part 14 --- Idempotent Automation

## 39. Desired Behavior

Suppose desired memory is:

``` text
40 GB
```

Current memory:

``` text
40 GB
```

Good automation:

``` text
no change required
```

Poor automation:

``` text
send update anyway every run
```

Idempotency reduces unnecessary changes.

------------------------------------------------------------------------

## 40. Pseudocode

``` python
current = get_database()

if current["memory"] != desired_memory:
    validate_capacity()
    require_approval()
    update_database()
    verify_database()
else:
    print("Already in desired state")
```

The exact API fields and change endpoints must come from the deployed
version's documentation.

------------------------------------------------------------------------

# Part 15 --- Configuration Drift

## 41. Drift

Drift occurs when:

``` text
actual configuration != approved desired configuration
```

Example:

``` text
Desired:
replication = enabled
shards = 4

Actual:
replication = enabled
shards = 2
```

------------------------------------------------------------------------

## 42. Drift Detection Workflow

``` text
1. Fetch current configuration.
2. Normalize response.
3. Compare with desired state.
4. Report differences.
5. Classify severity.
6. Do not auto-correct high-risk drift without policy.
7. Create approved remediation.
8. Verify after correction.
```

------------------------------------------------------------------------

# Part 16 --- Auditability

## 43. Every Change Should Be Traceable

Capture:

``` text
who
what
when
why
ticket/change
before state
after state
result
```

For automation:

``` text
pipeline/job ID
commit
service identity
API response
validation result
```

------------------------------------------------------------------------

## 44. Do Not Log Secrets

Logs should never include:

``` text
password
private key
token
secret header
full sensitive connection string
```

Redact them before logging.

------------------------------------------------------------------------

# Hands-On Lab

## 45. Lab Safety

Use:

``` text
training
development
staging
```

The main lab uses read-only inspection.

Do not issue resource-changing API requests unless you have a dedicated
lab and explicit approval.

------------------------------------------------------------------------

## 46. Lab 1 --- UI Inspection

Open Cluster Manager.

Record:

``` text
Cluster health:
Node count:
Database count:
Alerts:
Target database:
Target endpoint:
```

No changes.

------------------------------------------------------------------------

## 47. Lab 2 --- `rladmin status`

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

Compare with UI.

------------------------------------------------------------------------

## 48. Lab 3 --- Cluster Info

Where supported:

``` bash
rladmin info cluster
```

Record:

``` text
cluster identity
cluster status
relevant configuration
```

------------------------------------------------------------------------

## 49. Lab 4 --- Database Info

``` bash
rladmin info db
```

Record:

``` text
Database:
ID:
Status:
Memory:
Shards:
Replication:
Endpoint:
```

------------------------------------------------------------------------

## 50. Lab 5 --- Node Info

``` bash
rladmin info node
```

Record:

``` text
Node:
Address:
Status:
Failure domain:
```

------------------------------------------------------------------------

## 51. Lab 6 --- Shard Info

``` bash
rladmin info shard
```

Map:

``` text
Shard -> Database -> Role -> Node
```

------------------------------------------------------------------------

## 52. Lab 7 --- Proxy Info

``` bash
rladmin info proxy
```

Map:

``` text
Proxy -> Node -> Status
```

------------------------------------------------------------------------

# Part 17 --- REST API Lab

## 53. Lab Variables

Training shell:

``` bash
export RE_MGMT='https://<cluster-manager>:9443'
export RE_USER='<admin-user>'
export RE_PASSWORD='<admin-password>'
export RE_CA='/path/to/ca.pem'
```

Do not commit this shell content with real credentials.

------------------------------------------------------------------------

## 54. Lab 8 --- Cluster API

``` bash
curl \
  --cacert "$RE_CA" \
  -u "$RE_USER:$RE_PASSWORD" \
  "$RE_MGMT/v1/cluster" |
jq
```

Save:

``` bash
curl \
  --cacert "$RE_CA" \
  -u "$RE_USER:$RE_PASSWORD" \
  "$RE_MGMT/v1/cluster" \
  > cluster.json
```

------------------------------------------------------------------------

## 55. Lab 9 --- Database API

``` bash
curl \
  --cacert "$RE_CA" \
  -u "$RE_USER:$RE_PASSWORD" \
  "$RE_MGMT/v1/bdbs" |
jq
```

Record:

``` text
database count
target database ID
target database name
```

------------------------------------------------------------------------

## 56. Lab 10 --- Node API

``` bash
curl \
  --cacert "$RE_CA" \
  -u "$RE_USER:$RE_PASSWORD" \
  "$RE_MGMT/v1/nodes" |
jq
```

Compare to:

``` bash
rladmin info node
```

------------------------------------------------------------------------

## 57. Lab 11 --- Shard API

``` bash
curl \
  --cacert "$RE_CA" \
  -u "$RE_USER:$RE_PASSWORD" \
  "$RE_MGMT/v1/shards" |
jq
```

Compare to:

``` bash
rladmin info shard
```

------------------------------------------------------------------------

## 58. Lab 12 --- Proxy API

``` bash
curl \
  --cacert "$RE_CA" \
  -u "$RE_USER:$RE_PASSWORD" \
  "$RE_MGMT/v1/proxies" |
jq
```

Compare to:

``` bash
rladmin info proxy
```

------------------------------------------------------------------------

# Part 18 --- API Response Capture

## 59. Capture HTTP Status

Use:

``` bash
curl \
  --silent \
  --show-error \
  --output response.json \
  --write-out '%{http_code}\n' \
  --cacert "$RE_CA" \
  -u "$RE_USER:$RE_PASSWORD" \
  "$RE_MGMT/v1/bdbs"
```

This separates:

``` text
response body
HTTP status
```

Automation should evaluate both.

------------------------------------------------------------------------

## 60. Do Not Assume JSON Means Success

An API may return an error body in JSON.

Always inspect:

``` text
HTTP status
response body
```

before declaring success.

------------------------------------------------------------------------

# Failure Injection

## 61. Failure 1 --- Wrong Password

In a safe environment, use an invalid credential.

Expected category:

``` text
authentication failure
```

Observe:

``` text
HTTP status
response body
```

Do not repeatedly retry invalid credentials.

------------------------------------------------------------------------

## 62. Failure 2 --- Wrong API Path

Request a nonexistent resource:

``` bash
curl \
  --cacert "$RE_CA" \
  -u "$RE_USER:$RE_PASSWORD" \
  "$RE_MGMT/v1/does-not-exist"
```

Expected:

``` text
not-found/client-error behavior
```

Automation should not treat this as a transient infrastructure outage by
default.

------------------------------------------------------------------------

## 63. Failure 3 --- TLS Trust Failure

Use an invalid CA path or untrusted CA in a safe environment.

Expected:

``` text
TLS/certificate verification failure
```

Correct the trust configuration.

Do not permanently bypass verification.

------------------------------------------------------------------------

## 64. Failure 4 --- Permission Failure

Using a restricted test identity, request a resource it is not permitted
to access.

Expected category:

``` text
authorization failure
```

Distinguish:

``` text
401 authentication
```

from:

``` text
403 authorization
```

where the API uses those semantics.

------------------------------------------------------------------------

## 65. Failure 5 --- Malformed Change Request Tabletop

Do not send it.

Review this conceptual request:

``` json
{
  "memory_size": "banana"
}
```

Questions:

``` text
Should automation validate type before request?
Should API rejection be retried?
Should failure open a change incident?
```

Answer:

Validate input first, and do not blindly retry invalid configuration.

------------------------------------------------------------------------

## 66. Failure 6 --- Retry Storm

Scenario:

``` text
API returns 503
100 automation workers retry every 100 ms
```

Potential result:

``` text
management-plane overload
log flood
recovery slowdown
```

Use:

``` text
bounded retry
exponential backoff
jitter
maximum attempts
```

for appropriate transient failures.

------------------------------------------------------------------------

# Part 19 --- Automation Guardrails

## 67. Required Controls

Production administrative automation should consider:

``` text
authentication
authorization
TLS
input validation
current-state check
desired-state diff
approval
rate limiting
retry policy
timeout
idempotency
logging
secret redaction
post-change validation
rollback
```

------------------------------------------------------------------------

## 68. Dry Run

Where your automation design supports it:

``` text
current: 2 shards
desired: 4 shards
action: would modify database
```

before execution.

A dry-run mode reduces accidental changes.

------------------------------------------------------------------------

## 69. Explicit Environment

Never infer production from an ambiguous default.

Require:

``` text
environment=production
cluster=<expected-cluster>
database=<expected-database>
```

and validate identity before change.

------------------------------------------------------------------------

## 70. Destructive Confirmation

High-impact automation should require stronger controls than read-only
inventory.

Examples:

``` text
database deletion
node removal
major topology changes
```

Use organizational change controls and product-supported procedures.

------------------------------------------------------------------------

# Part 20 --- Troubleshooting

## 71. `rladmin` Command Fails

Check:

``` text
running on supported/admin host?
permissions?
exact syntax for version?
cluster health?
command available in this release?
```

Do not copy syntax blindly from a different product version.

------------------------------------------------------------------------

## 72. REST API Connection Fails

Troubleshoot in order:

``` text
DNS
TCP
TLS
authentication
authorization
API path
API service
```

Do not jump directly to API payload debugging when TCP cannot connect.

------------------------------------------------------------------------

## 73. API Returns 401

Check:

``` text
username
password
credential rotation
authentication method
secret source
```

------------------------------------------------------------------------

## 74. API Returns 403

Check:

``` text
identity authenticated?
required role?
least-privilege policy?
resource authorization?
```

Do not solve every 403 by granting broad administrator access.

------------------------------------------------------------------------

## 75. API Returns 404

Check:

``` text
endpoint path
API version
resource ID
product release
cluster endpoint
```

------------------------------------------------------------------------

## 76. API Returns 409

Potentially indicates a state/conflict issue depending on the endpoint.

Investigate:

``` text
current resource state
concurrent operation
desired state
API documentation
```

Do not blindly retry.

------------------------------------------------------------------------

## 77. API Returns 5xx

Check:

``` text
cluster health
management service health
current maintenance
resource pressure
request validity
recent changes
```

Use bounded retries only when the operation is safe to retry.

------------------------------------------------------------------------

# Part 21 --- Administration Runbooks

## 78. Runbook --- Read-Only Cluster Inspection

``` text
1. Confirm target cluster.
2. Record timestamp.
3. Open Cluster Manager.
4. Run rladmin status.
5. Inspect databases.
6. Inspect nodes.
7. Inspect shards.
8. Inspect proxies.
9. Retrieve read-only API resources.
10. Compare interfaces.
11. Record warnings.
12. Escalate inconsistencies.
13. Make no configuration change during inspection.
```

------------------------------------------------------------------------

## 79. Runbook --- Pre-Change Validation

``` text
1. Confirm ticket/change.
2. Confirm target cluster.
3. Confirm target database/resource.
4. Retrieve current state.
5. Compare desired state.
6. Validate capacity.
7. Validate HA state.
8. Validate no active incident.
9. Validate rollback.
10. Validate monitoring.
11. Confirm approval.
12. Capture before-state artifacts.
```

------------------------------------------------------------------------

## 80. Runbook --- API Change Failure

``` text
1. Stop repeated automated retries.
2. Record HTTP status.
3. Record sanitized response.
4. Confirm whether operation was applied.
5. Retrieve current resource state.
6. Determine authentication/authorization/request/server failure.
7. Determine whether retry is safe.
8. Correct root cause.
9. Re-run only with controlled approval.
10. Validate final state.
11. Record audit trail.
```

------------------------------------------------------------------------

## 81. Runbook --- Configuration Drift

``` text
1. Fetch actual configuration.
2. Load approved desired configuration.
3. Normalize both.
4. Generate diff.
5. Identify severity.
6. Identify last approved change.
7. Identify owner.
8. Determine whether actual or desired state is correct.
9. Create remediation change.
10. Apply controlled correction.
11. Validate.
12. Update source of truth.
```

------------------------------------------------------------------------

# Part 22 --- Administration Acceptance

## 82. Interface Matrix

  Task                         UI        `rladmin`            REST API
  ---------------------------- --------- -------------------- ----------
  Human visual inspection      Strong    Good                 Possible
  CLI incident inspection      Limited   Strong               Strong
  Automation                   Weak      Limited/scriptable   Strong
  Configuration inventory      Good      Good                 Strong
  Repeatable drift detection   Weak      Possible             Strong
  One-time operator workflow   Strong    Strong               Possible

Exact capabilities depend on release.

------------------------------------------------------------------------

## 83. Operational Principle

Use:

``` text
UI -> understand and inspect
rladmin -> operate and inspect from CLI
REST API -> automate and integrate
```

but always prefer the interface supported for the specific operation in
your deployed release.

------------------------------------------------------------------------

# Production Acceptance Checklist

## 84. Administration Readiness

-   [ ] Cluster Manager access controlled.
-   [ ] `rladmin` access controlled.
-   [ ] REST API access controlled.
-   [ ] Application and admin identities separated.
-   [ ] Automation identity uses least privilege.
-   [ ] TLS verification enabled.
-   [ ] Administrative secrets stored securely.
-   [ ] Secrets excluded from Git.
-   [ ] Secrets excluded from logs.
-   [ ] Read-only inventory workflow documented.
-   [ ] API status codes handled.
-   [ ] API response bodies validated.
-   [ ] Timeouts configured.
-   [ ] Retry policy bounded.
-   [ ] Backoff/jitter configured where appropriate.
-   [ ] Idempotency considered.
-   [ ] Current-state checks implemented.
-   [ ] Desired-state diff implemented.
-   [ ] Change approval integrated.
-   [ ] Before-state captured.
-   [ ] Post-change validation implemented.
-   [ ] Rollback documented.
-   [ ] Audit trail retained.
-   [ ] Drift detection available.
-   [ ] Administration runbooks available.

------------------------------------------------------------------------

# Knowledge Validation

## 85. Questions

You should be able to answer:

1.  What is the difference between Redis data plane and management
    plane?
2.  What is Cluster Manager used for?
3.  What is `rladmin` used for?
4.  What is the REST API used for?
5.  Why should application and admin identities be separated?
6.  Why should incident investigation begin read-only?
7.  What should be captured before a configuration change?
8.  What does `/v1/bdbs` conceptually represent?
9.  Why must API fields be validated against the deployed release?
10. Why should credentials not appear in shell history?
11. Why should TLS verification remain enabled?
12. What is the difference between HTTP 401 and 403 conceptually?
13. Why should 4xx responses generally not be blindly retried?
14. Why can aggressive retries worsen 5xx failures?
15. What is idempotent automation?
16. Why should current state be compared with desired state?
17. What is configuration drift?
18. Why should high-risk drift not always be auto-corrected?
19. What information belongs in an audit record?
20. Why should secrets be redacted from logs?
21. Why is dry-run mode valuable?
22. Why should automation explicitly validate environment and cluster
    identity?
23. What should happen after an API change failure?
24. When is the UI preferable?
25. When is the REST API preferable?

------------------------------------------------------------------------

# Hands-On Acceptance Checklist

## 86. Lab Completion

-   [ ] Inspected Cluster Manager.
-   [ ] Ran `rladmin status`.
-   [ ] Inspected cluster info.
-   [ ] Inspected database info.
-   [ ] Inspected node info.
-   [ ] Inspected shard info.
-   [ ] Inspected proxy info.
-   [ ] Configured safe lab API variables.
-   [ ] Retrieved cluster API.
-   [ ] Retrieved database API.
-   [ ] Retrieved node API.
-   [ ] Retrieved shard API.
-   [ ] Retrieved proxy API.
-   [ ] Parsed JSON with `jq`.
-   [ ] Captured HTTP status separately.
-   [ ] Tested wrong-password behavior.
-   [ ] Tested wrong-path behavior.
-   [ ] Reviewed TLS failure behavior.
-   [ ] Reviewed authorization failure.
-   [ ] Reviewed malformed-request handling.
-   [ ] Reviewed retry-storm behavior.
-   [ ] Reviewed automation guardrails.
-   [ ] Reviewed all administration runbooks.

------------------------------------------------------------------------

# 87. Key Takeaways

1.  Redis Enterprise administration uses a management plane separate
    from application data access.
2.  Cluster Manager is valuable for human visual inspection and
    controlled operations.
3.  `rladmin` is a core CLI administration and inspection tool in
    supported self-managed deployments.
4.  The REST API enables repeatable inventory, automation, and drift
    detection.
5.  Production investigation should begin with read-only inspection.
6.  Administrative identities should follow least privilege.
7.  Administrative credentials must not be embedded in source code or
    logs.
8.  TLS verification is part of management-plane security.
9.  Automation must evaluate HTTP status and response content.
10. Not every API failure is safe to retry.
11. Bounded retries, backoff, and jitter protect the management plane.
12. Idempotent automation compares current and desired state before
    changing anything.
13. Configuration drift should be detected and reviewed systematically.
14. Every production change should have a traceable before/after audit
    record.
15. UI, CLI, and API should complement each other rather than compete.

------------------------------------------------------------------------

# 88. References

Validate commands, REST endpoints, request schemas, response fields,
authentication, authorization, and change procedures against
documentation for the exact Redis Enterprise / Redis Software release
deployed.

Key documentation areas:

-   Redis Enterprise Cluster Manager
-   `rladmin`
-   Redis Enterprise REST API
-   cluster resources
-   database resources
-   node resources
-   shard resources
-   proxy resources
-   authentication and authorization
-   TLS
-   administration security
-   API automation

------------------------------------------------------------------------

# Next Chapter

**Chapter 10 --- Architecture Inspection & Foundation Acceptance Lab**

Chapter 10 will close Part 1 with a comprehensive production-style
project covering:

-   cluster inventory
-   database inventory
-   endpoint validation
-   node topology
-   shard topology
-   proxy topology
-   replication mapping
-   failure domains
-   hash-slot/key-distribution review
-   configuration baseline
-   API inspection
-   capacity observations
-   failure table-top exercises
-   troubleshooting
-   production readiness scorecard
-   Part 1 acceptance checklist
