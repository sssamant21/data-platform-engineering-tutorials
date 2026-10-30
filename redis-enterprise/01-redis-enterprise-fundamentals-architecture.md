# Chapter 01 --- Redis Enterprise Fundamentals & Architecture

**Status:** Canonical\
**Track:** Redis Enterprise / Redis Software Production Engineering\
**Level:** Foundation → Production Operations\
**Audience:** SREs, DBREs, Platform Engineers, Redis Administrators,
Developers\
**Lab type:** Read-mostly architecture inspection + isolated test-key
operations

------------------------------------------------------------------------

## 1. Objective

This chapter builds the foundation required to operate Redis Enterprise
safely in production.

By the end of the chapter, you should be able to:

-   Explain what Redis Enterprise / Redis Software provides beyond a
    standalone Redis server.
-   Distinguish a cluster, node, database, shard, primary shard, replica
    shard, proxy, and database endpoint.
-   Trace a client request through the Redis Enterprise data path.
-   Explain the difference between sharding, replication, persistence,
    backup, and Active-Active.
-   Explain why adding a cluster node does not automatically make one
    database faster.
-   Connect to a test database with `redis-cli`.
-   Inspect the platform with `rladmin`.
-   Query basic cluster objects with the Redis Enterprise REST API.
-   Identify primary and replica shard placement.
-   Verify that the database is reachable and that a test key is stored
    correctly.
-   Recognize basic architectural failure conditions before making
    production changes.

This is intentionally an architecture and inspection chapter.
Destructive failover, shard migration, node removal, persistence
changes, and production tuning are covered in later chapters.

------------------------------------------------------------------------

## 2. Product Terminology

Current Redis documentation commonly refers to the self-managed
enterprise platform as **Redis Software**.

In many organizations and existing deployments, the product is still
commonly called **Redis Enterprise**.

Throughout this tutorial:

> **Redis Enterprise** refers to the self-managed Redis Software
> platform unless a section explicitly discusses Redis Cloud or Redis
> Open Source.

Do not assume that commands or architecture described for Redis Cloud
are identical to a self-managed Redis Enterprise cluster.

------------------------------------------------------------------------

## 3. Redis Open Source vs Redis Enterprise

A Redis application still sends normal Redis commands such as:

``` text
GET
SET
DEL
HGET
HSET
INCR
EXPIRE
XADD
```

Redis Enterprise adds a platform around Redis to operate databases
across multiple nodes.

Major enterprise capabilities include:

-   Cluster management
-   Database lifecycle management
-   Transparent sharding
-   Primary/replica placement
-   Automatic failover
-   Rack/zone awareness
-   Persistence
-   Backup and recovery
-   Database endpoints and proxy routing
-   Authentication and access control
-   TLS and certificate management
-   Metrics and alerting
-   REST APIs
-   Administrative CLI tools
-   Active-Active geo-distribution
-   Auto Tiering / Flex
-   Kubernetes deployment and operation

A useful mental model is:

``` text
Redis commands
      |
      v
Redis database
      |
      v
Redis Enterprise platform
      |
      +-- routing
      +-- sharding
      +-- replication
      +-- failover
      +-- placement
      +-- security
      +-- persistence
      +-- monitoring
      +-- lifecycle management
```

------------------------------------------------------------------------

## 4. Core Architecture

A simplified Redis Enterprise architecture looks like this:

``` text
                     APPLICATIONS
                         |
                         |
                 Redis database endpoint
                         |
                         v
                +------------------+
                | Enterprise Proxy |
                +------------------+
                   /      |      \
                  /       |       \
                 v        v        v
             Primary   Primary   Primary
             Shard 1   Shard 2   Shard 3
                |         |         |
                v         v         v
             Replica   Replica   Replica
             Shard 1   Shard 2   Shard 3

        +--------------------------------------+
        |       Redis Enterprise Cluster       |
        |                                      |
        | Node 1       Node 2       Node 3     |
        | shards       shards       shards     |
        | proxy        proxy        proxy      |
        | services     services     services   |
        +--------------------------------------+
```

The application should normally connect to the **database endpoint**,
not directly to an individual shard process.

------------------------------------------------------------------------

## 5. Cluster

A Redis Enterprise cluster is a group of nodes managed as one platform.

The cluster provides the resource pool used by databases.

Cluster-level responsibilities include:

-   Node membership
-   Resource management
-   Shard placement
-   Endpoint placement
-   Cluster policies
-   Rack/zone awareness
-   Administrative services
-   Monitoring
-   Failover coordination

A production cluster commonly contains multiple nodes so databases can
distribute primary and replica shards across failure domains.

### Important

A Redis Enterprise **cluster** is not the same thing as a Redis
database.

One cluster can host many databases.

``` text
Redis Enterprise Cluster
|
+-- Database A
+-- Database B
+-- Database C
+-- Database D
```

Each database can have different:

-   memory limits
-   shard counts
-   replication settings
-   persistence settings
-   authentication
-   endpoints
-   modules/capabilities
-   operational policies

------------------------------------------------------------------------

## 6. Node

A node is a machine or runtime instance participating in the Redis
Enterprise cluster.

Depending on deployment architecture, a node might be:

-   a physical server
-   a virtual machine
-   a cloud VM
-   a containerized Redis Enterprise node

A node can host multiple Redis shard processes.

Conceptually:

``` text
Node 1
|
+-- Proxy
+-- Primary shard for DB-A
+-- Replica shard for DB-B
+-- Primary shard for DB-C
+-- Enterprise platform processes
```

Another node could contain:

``` text
Node 2
|
+-- Proxy
+-- Replica shard for DB-A
+-- Primary shard for DB-B
+-- Replica shard for DB-C
+-- Enterprise platform processes
```

Redis Enterprise manages placement rather than requiring the application
to understand which node owns a key.

------------------------------------------------------------------------

## 7. Database

A Redis Enterprise database is the application-facing logical Redis
service.

A database normally has:

-   a name
-   an ID
-   an endpoint
-   a port
-   a memory limit
-   one or more shards
-   optional replicas
-   security configuration
-   optional persistence
-   optional additional capabilities

Applications should think in terms of the database endpoint rather than
individual cluster nodes.

Example conceptual endpoint:

``` text
cache-prod.example.internal:12000
```

The endpoint hides the underlying shard placement from the application.

------------------------------------------------------------------------

## 8. Shards

A shard is an individual Redis instance responsible for part of a
database's data.

A database can contain:

``` text
1 shard
```

or:

``` text
many shards
```

Sharding allows the workload and dataset to be distributed.

Example:

``` text
Database: customer-cache

Primary shard 1
Primary shard 2
Primary shard 3
Primary shard 4
```

When replication is enabled:

``` text
Primary 1  ---> Replica 1
Primary 2  ---> Replica 2
Primary 3  ---> Replica 3
Primary 4  ---> Replica 4
```

The platform attempts to place corresponding primary and replica shards
on different nodes.

------------------------------------------------------------------------

## 9. Why Sharding Matters

A Redis shard is a major unit of compute and memory processing.

If one database has only one primary shard, simply adding more nodes to
the cluster does not automatically split that database's workload across
those nodes.

This distinction is critical:

``` text
More cluster nodes
        !=
Automatically more database throughput
```

Database throughput depends on factors including:

-   shard count
-   key distribution
-   command complexity
-   CPU consumption
-   network throughput
-   proxy capacity
-   data structures
-   pipelining
-   client behavior
-   hot keys
-   memory pressure

Later performance chapters will test these factors directly.

------------------------------------------------------------------------

## 10. Primary Shards

Primary shards process application writes for their portion of the
keyspace.

Simplified flow:

``` text
Client
  |
  v
Endpoint / Proxy
  |
  v
Correct Primary Shard
```

The primary executes the operation and returns the result through the
request path.

------------------------------------------------------------------------

## 11. Replica Shards

When database replication is enabled, primary shards have corresponding
replica shards.

Conceptually:

``` text
Primary shard
     |
     | replication
     v
Replica shard
```

The replica is continuously synchronized with the primary.

If a primary fails, Redis Enterprise can promote the replica to primary.

This supports **high availability**.

Replication is not the same as backup.

If the application intentionally deletes a key and the deletion
replicates successfully, the replica also receives that deletion.

------------------------------------------------------------------------

## 12. Proxy

Redis Enterprise includes proxy processes that route database traffic.

The application sends Redis operations to the database endpoint.

The proxy determines where the request should go.

Simplified request path:

``` text
Application
    |
    v
Database Endpoint
    |
    v
Enterprise Proxy
    |
    +------> Shard 1
    |
    +------> Shard 2
    |
    +------> Shard 3
```

The proxy allows applications to use standard Redis clients without
needing to understand physical shard placement.

This abstraction is one of the most important architectural differences
between directly managing individual Redis processes and operating Redis
Enterprise.

------------------------------------------------------------------------

## 13. Database Endpoint

The database endpoint is the application-facing network location for the
database.

Typically it consists of:

``` text
hostname + port
```

Applications should normally use this endpoint.

Avoid designing applications around a particular Redis Enterprise node
unless the deployment architecture explicitly requires it.

The underlying shard or endpoint placement can change during:

-   failover
-   maintenance
-   migration
-   rebalancing
-   node replacement

The endpoint abstraction allows the platform to handle those changes.

------------------------------------------------------------------------

## 14. Request Flow --- Read

Consider:

``` redis
GET customer:1001
```

Conceptually:

``` text
1. Client sends GET customer:1001
2. Request reaches database endpoint
3. Enterprise proxy receives request
4. Key is mapped to the appropriate shard
5. Request is forwarded to that shard
6. Redis executes GET
7. Result returns through the proxy
8. Client receives the value
```

Diagram:

``` text
Client
  |
  | GET customer:1001
  v
Endpoint
  |
  v
Proxy
  |
  | route key
  v
Primary shard
  |
  | value
  v
Proxy
  |
  v
Client
```

------------------------------------------------------------------------

## 15. Request Flow --- Write with Replication

Consider:

``` redis
SET customer:1001 active
```

Simplified flow:

``` text
Client
  |
  v
Endpoint / Proxy
  |
  v
Primary Shard
  |
  +---- update data
  |
  +---- replicate ----> Replica Shard
```

Redis replication behavior and acknowledgment guarantees require more
nuance than this simplified diagram. Later chapters cover replication
consistency, `WAIT`, persistence, and durability.

For this chapter, remember:

> The application writes through the endpoint; the primary owns the
> write; replication maintains another copy for HA.

------------------------------------------------------------------------

## 16. Sharding vs Replication

These solve different problems.

### Sharding

Purpose:

``` text
Scale workload and dataset across multiple Redis instances.
```

Example:

``` text
DB
|
+-- Primary shard 1
+-- Primary shard 2
+-- Primary shard 3
```

### Replication

Purpose:

``` text
Maintain another copy for availability.
```

Example:

``` text
Primary 1 -> Replica 1
Primary 2 -> Replica 2
Primary 3 -> Replica 3
```

### Combined

``` text
                 DATABASE
                    |
       +------------+------------+
       |            |            |
   Primary 1    Primary 2    Primary 3
       |            |            |
   Replica 1    Replica 2    Replica 3
```

A production database often uses both.

------------------------------------------------------------------------

## 17. High Availability vs Durability

These terms must not be treated as synonyms.

### High Availability

Goal:

> Keep the database serving traffic when components fail.

Typical mechanisms:

-   replication
-   automatic failover
-   replica HA
-   rack/zone awareness
-   resilient endpoint placement

### Durability

Goal:

> Reduce the risk of losing acknowledged data.

Typical mechanisms can include:

-   AOF persistence
-   RDB snapshots
-   replication
-   backups
-   application-level recovery strategy

Replication helps availability but should not be considered a
replacement for backup or a complete durability strategy.

------------------------------------------------------------------------

## 18. Persistence

Redis is fundamentally an in-memory data platform.

Redis Enterprise can persist database data to disk using supported
persistence modes.

Conceptually:

``` text
Redis memory
    |
    +---- AOF
    |
    +---- RDB snapshots
```

Persistence involves tradeoffs among:

-   durability
-   disk I/O
-   CPU
-   latency
-   recovery time
-   storage capacity

Persistence configuration deserves its own production lab and is covered
later.

Do not change persistence settings in production merely to experiment
with this chapter.

------------------------------------------------------------------------

## 19. Rack / Zone Awareness

Replication only protects against infrastructure failure when copies are
separated appropriately.

Bad placement conceptually:

``` text
Rack A
|
+-- Primary
+-- Replica
```

A rack failure can remove both.

Preferred architecture:

``` text
Rack / Zone A        Rack / Zone B
     |                    |
  Primary              Replica
```

Redis Enterprise rack/zone awareness helps enforce failure-domain
separation.

This becomes especially important in cloud environments where nodes are
distributed across availability zones.

------------------------------------------------------------------------

## 20. Replica High Availability

Consider this failure:

``` text
Node 1
Primary A

Node 2
Replica A
```

If Node 1 fails:

``` text
Replica A -> promoted to Primary A
```

The database is serving again, but now there may temporarily be only one
surviving copy.

Replica HA can create/migrate a new replica onto an eligible node so
redundancy is restored.

Conceptually:

``` text
Before failure:

Node 1              Node 2
Primary A           Replica A

After Node 1 failure:

Node 2              Node 3
Primary A           New Replica A
```

Capacity matters. The cluster needs an eligible node with enough
resources to host the new replica.

------------------------------------------------------------------------

## 21. Management Plane vs Data Plane

For operational thinking, separate application traffic from
administrative traffic.

### Data plane

Application operations:

``` text
GET
SET
HGET
HSET
INCR
XADD
JSON.GET
FT.SEARCH
```

Usually accessed through:

``` text
redis-cli
application Redis clients
```

### Management plane

Platform operations:

-   inspect cluster
-   inspect nodes
-   inspect databases
-   inspect shards
-   configure databases
-   migrate shards
-   perform administrative failover
-   manage policies

Common interfaces include:

``` text
Cluster Manager UI
rladmin
REST API
```

Do not confuse:

``` bash
redis-cli
```

with:

``` bash
rladmin
```

They operate at different layers.

------------------------------------------------------------------------

## 22. Administrative Interfaces

### Cluster Manager UI

Web interface used for:

-   cluster status
-   database management
-   configuration
-   monitoring
-   alerts
-   security
-   operational workflows

### `redis-cli`

Used to communicate with a Redis database.

Example:

``` bash
redis-cli -h <endpoint> -p <port> PING
```

### `rladmin`

Administrative utility for Redis Enterprise.

Common inspection commands include:

``` bash
rladmin status
rladmin info cluster
rladmin info db
rladmin info node
rladmin info proxy
```

The exact available syntax can depend on product version.

Always check:

``` bash
rladmin help
```

before performing an unfamiliar administrative operation.

### REST API

Redis Enterprise provides a REST API for automation and platform
integration.

Typical resource families include:

``` text
/v1/cluster
/v1/nodes
/v1/bdbs
/v1/shards
/v1/proxies
```

Use least-privileged credentials and never embed production passwords in
source code.

------------------------------------------------------------------------

# Hands-On Lab --- Inspect Redis Enterprise Architecture

## 23. Lab Goal

You will:

1.  Verify the database endpoint.
2.  Test database connectivity.
3.  Create isolated tutorial keys.
4.  Inspect cluster status.
5.  Inspect nodes.
6.  Inspect databases.
7.  Inspect shards.
8.  Inspect proxies/endpoints.
9.  Use the REST API for read-only inspection.
10. Map the logical database to its physical architecture.
11. Perform basic troubleshooting.
12. Clean up test keys.

------------------------------------------------------------------------

## 24. Lab Safety

Run this lab against:

``` text
development
test
staging
training
```

Prefer a non-production database.

If production access is unavoidable:

-   run inspection commands only
-   do not create tutorial keys without approval
-   do not fail over shards
-   do not migrate shards
-   do not remove nodes
-   do not tune cluster settings
-   do not change persistence
-   do not change replication
-   do not flush the database

Never run:

``` redis
FLUSHALL
FLUSHDB
```

as part of this tutorial.

------------------------------------------------------------------------

## 25. Lab Variables

Replace example endpoint and certificate paths with your approved **nonproduction** Redis Software/Enterprise values. Use the trusted certificate for the **database proxy** and a trusted CA for the **management API**; the certificate files may be different.

``` text
REDIS_HOST / REDIS_PORT / REDIS_CA
CLUSTER_HOST / API_USER / API_CA
DATABASE_NAME
```

Example environment variables for a trusted Bash lab terminal:

``` bash
export REDIS_HOST="redis-test.example.internal"
export REDIS_PORT="12000"
export REDIS_CA="/secure/path/proxy_cert.pem"
export CLUSTER_HOST="redis-cluster.example.internal"
export API_USER="<api-user>"
export API_CA="/secure/path/management_ca.pem"
test -r "$REDIS_CA" && test -r "$API_CA"
read -r -s -p "Staging Redis database password: " REDISCLI_AUTH
echo
export REDISCLI_AUTH
```

The `redis-cli` commands below use **REDISCLI_AUTH**, not a password command-line argument. For Redis ACL users, provide the approved `--user` argument as appropriate. The management REST examples use `curl --user "$API_USER"` so curl prompts for the API password rather than including it in process arguments.

For Windows PowerShell, configure non-secret connection parameters as follows and supply `REDISCLI_AUTH` privately through an approved secrets workflow:

``` powershell
$env:REDIS_HOST="redis-test.example.internal"
$env:REDIS_PORT="12000"
$env:REDIS_CA="C:\secure\proxy_cert.pem"
$env:CLUSTER_HOST="redis-cluster.example.internal"
$env:API_USER="<api-user>"
$env:API_CA="C:\secure\management_ca.pem"
```

**Do not** put actual passwords into shell history, committed scripts, screenshots, command arguments, or ticket records. When finished, run `unset REDISCLI_AUTH` in the Bash session. The examples require accessible certificate trust and permitted identities; stop if TLS validation fails rather than bypassing it.

------------------------------------------------------------------------

## 26. Step 1 --- Verify Network Connectivity

Linux:

``` bash
nc -vz "$REDIS_HOST" "$REDIS_PORT"
```

PowerShell:

``` powershell
Test-NetConnection $env:REDIS_HOST -Port $env:REDIS_PORT
```

Expected result:

``` text
TCP connection succeeds
```

If it fails, investigate:

-   DNS
-   firewall
-   security group
-   network policy
-   load balancer
-   endpoint configuration
-   wrong port
-   routing

Do not immediately assume Redis itself is down.

------------------------------------------------------------------------

## 27. Step 2 --- Connect with `redis-cli`

Password authentication example:

``` bash
redis-cli \
  -h "$REDIS_HOST" \
  -p "$REDIS_PORT" \
  --tls --cacert "$REDIS_CA" \
  PING
```

Expected:

``` text
PONG
```

The credential comes from the privately populated REDISCLI_AUTH environment variable.

These staging examples **require** hostname-validated TLS with a trusted CA; adjust for mTLS with a client certificate and key where required by your deployment.

A typical TLS form is:

``` bash
redis-cli \
  -h "$REDIS_HOST" \
  -p "$REDIS_PORT" \
  --tls --cacert "$REDIS_CA" \
  PING
```

Certificate parameters may also be required depending on your
deployment.

TLS is covered in the security section of this curriculum.

------------------------------------------------------------------------

## 28. Step 3 --- Inspect Basic Redis Information

Run:

``` bash
redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" --tls --cacert "$REDIS_CA" INFO server
```

Then:

``` bash
redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" --tls --cacert "$REDIS_CA" INFO memory
```

Then:

``` bash
redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" --tls --cacert "$REDIS_CA" INFO stats
```

Do not attempt to memorize every metric yet.

Identify:

-   Redis version
-   uptime
-   used memory
-   connected clients
-   operations
-   hits/misses if applicable
-   evictions if applicable

Later chapters analyze these metrics in depth.

------------------------------------------------------------------------

## 29. Step 4 --- Create an Isolated Test Key

Use a namespace that cannot collide with application keys:

``` bash
redis-cli \
  -h "$REDIS_HOST" \
  -p "$REDIS_PORT" \
  --tls --cacert "$REDIS_CA" \
  SET tutorial:chapter01:hello "redis-enterprise" EX 300
```

Expected:

``` text
OK
```

Read it:

``` bash
redis-cli \
  -h "$REDIS_HOST" \
  -p "$REDIS_PORT" \
  --tls --cacert "$REDIS_CA" \
  GET tutorial:chapter01:hello
```

Expected:

``` text
redis-enterprise
```

Check TTL:

``` bash
redis-cli \
  -h "$REDIS_HOST" \
  -p "$REDIS_PORT" \
  --tls --cacert "$REDIS_CA" \
  TTL tutorial:chapter01:hello
```

Expected:

``` text
A positive number <= 300
```

------------------------------------------------------------------------

## 30. Step 5 --- Test Multiple Data Types

String:

``` redis
SET tutorial:chapter01:user:1001:name "Alice" EX 300
```

Hash:

``` redis
HSET tutorial:chapter01:user:1001 profile_status active region us-east
EXPIRE tutorial:chapter01:user:1001 300
```

Counter:

``` redis
INCR tutorial:chapter01:requests
EXPIRE tutorial:chapter01:requests 300
```

List:

``` redis
LPUSH tutorial:chapter01:events event1 event2 event3
EXPIRE tutorial:chapter01:events 300
```

Verify:

``` redis
GET tutorial:chapter01:user:1001:name
HGETALL tutorial:chapter01:user:1001
GET tutorial:chapter01:requests
LRANGE tutorial:chapter01:events 0 -1
```

The purpose here is not data-model mastery. It is to confirm that normal
Redis commands work through the Enterprise endpoint.

------------------------------------------------------------------------

## 31. Step 6 --- Inspect Cluster Status with `rladmin`

Log in to a Redis Enterprise node with appropriate administrative
access.

Run:

``` bash
rladmin status
```

Study the output.

Depending on version and configuration, you should be able to identify
information about:

-   nodes
-   databases
-   shards
-   endpoints
-   status

Do not modify anything.

Capture the following for the lab worksheet:

``` text
Cluster node count:
Database name:
Database ID:
Database endpoint:
Primary shard count:
Replica shard count:
```

------------------------------------------------------------------------

## 32. Step 7 --- Inspect Cluster Configuration

Run:

``` bash
rladmin info cluster
```

Review the cluster configuration.

Look for information related to:

-   cluster state
-   policies
-   replica HA
-   placement behavior
-   other platform settings

The exact fields vary by version.

Do not change cluster configuration in Chapter 01.

------------------------------------------------------------------------

## 33. Step 8 --- Inspect Databases

Run:

``` bash
rladmin info db
```

If your version requires or supports a database identifier, inspect the
target database specifically.

Use:

``` bash
rladmin help
```

or:

``` bash
rladmin help info
```

to confirm syntax for the installed version.

Identify:

``` text
Database ID
Database name
Memory limit
Shard count
Replication status
Endpoint
```

------------------------------------------------------------------------

## 34. Step 9 --- Inspect Nodes

Run:

``` bash
rladmin info node
```

Map the cluster:

``` text
Node ID | Host/IP | Status | Rack/Zone | Notes
--------|---------|--------|-----------|------
        |         |        |           |
        |         |        |           |
        |         |        |           |
```

Questions:

1.  How many nodes are present?
2.  Are all nodes healthy?
3.  Are rack/zone IDs configured?
4.  Is capacity reasonably distributed?
5.  Are any nodes reporting an unexpected state?

Do not conclude that a node is overloaded based on one metric.
Performance analysis comes later.

------------------------------------------------------------------------

## 35. Step 10 --- Inspect Shards

Use `rladmin status` and supported `rladmin info` commands to identify
shard placement.

Build a table:

``` text
Database | Shard | Role    | Node | Status
---------|-------|---------|------|-------
         |       | primary |      |
         |       | replica |      |
```

Validate:

> A primary shard and its corresponding replica should not be on the
> same node.

If rack/zone awareness is enabled, also verify appropriate
failure-domain separation.

------------------------------------------------------------------------

## 36. Step 11 --- Inspect Proxy Information

Run:

``` bash
rladmin info proxy
```

Review the proxy configuration/status.

Do not tune proxy policy yet.

Understand the relationship:

``` text
database endpoint
      |
      v
active proxy path
      |
      v
database shards
```

A database can be healthy at the shard level while client traffic still
experiences a networking or endpoint/proxy problem.

This distinction becomes important during incidents.

------------------------------------------------------------------------

## 37. Step 12 --- REST API Health Check

Redis Enterprise REST APIs commonly use the management HTTPS endpoint.

Example:

``` bash
curl --fail --silent --show-error --cacert "$API_CA" \
  --user "$API_USER" \
  "https://$CLUSTER_HOST:9443/v1/cluster"
```

Use a trusted management certificate bundle (`--cacert`) and a hostname matching the certificate. The interactive curl password prompt avoids exposing an API password in command arguments. For noninteractive automation, use a supported, approved secret-delivery mechanism that does not leak credentials into process arguments. **Never** bypass certificate verification to make a failing lab pass.

Expected:

``` text
JSON cluster information
```

Do not paste real credentials into terminal screenshots, tickets, or
documentation.

------------------------------------------------------------------------

## 38. Step 13 --- List Nodes with REST API

``` bash
curl --fail --silent --show-error --cacert "$API_CA" \
  --user "$API_USER" \
  "https://$CLUSTER_HOST:9443/v1/nodes"
```

If `jq` is available:

``` bash
curl --fail --silent --show-error --cacert "$API_CA" \
  --user "$API_USER" \
  "https://$CLUSTER_HOST:9443/v1/nodes" | jq
```

Compare the result with:

``` bash
rladmin status
```

The two interfaces expose the same platform from different operational
perspectives.

------------------------------------------------------------------------

## 39. Step 14 --- List Databases with REST API

``` bash
curl --fail --silent --show-error --cacert "$API_CA" \
  --user "$API_USER" \
  "https://$CLUSTER_HOST:9443/v1/bdbs"
```

With `jq`:

``` bash
curl --fail --silent --show-error --cacert "$API_CA" \
  --user "$API_USER" \
  "https://$CLUSTER_HOST:9443/v1/bdbs" | jq
```

Find your test database.

Record:

``` text
Database ID:
Name:
Port:
Memory limit:
Replication:
Shard count:
```

Field names can vary with product version.

------------------------------------------------------------------------

## 40. Step 15 --- Inspect Shards with REST API

``` bash
curl --fail --silent --show-error --cacert "$API_CA" \
  --user "$API_USER" \
  "https://$CLUSTER_HOST:9443/v1/shards"
```

With `jq`:

``` bash
curl --fail --silent --show-error --cacert "$API_CA" \
  --user "$API_USER" \
  "https://$CLUSTER_HOST:9443/v1/shards" | jq
```

Use the result to answer:

-   Which shards belong to the test database?
-   Which are primary?
-   Which are replicas?
-   Which nodes host them?

Do not assume shard IDs correspond to database IDs.

------------------------------------------------------------------------

## 41. Step 16 --- Inspect Proxies with REST API

``` bash
curl --fail --silent --show-error --cacert "$API_CA" \
  --user "$API_USER" \
  "https://$CLUSTER_HOST:9443/v1/proxies"
```

This reinforces that the proxy is an actual Enterprise platform
component, not merely an architecture diagram.

------------------------------------------------------------------------

## 42. Step 17 --- Build the Physical Map

Using your observations, create a map similar to:

``` text
Database: tutorial-cache
Endpoint: redis-test.example.internal:12000

                   Endpoint
                      |
                      v
                  Proxy path
                      |
          +-----------+-----------+
          |                       |
          v                       v
      Primary 1               Primary 2
        Node 1                  Node 2
          |                       |
          v                       v
      Replica 1               Replica 2
        Node 3                  Node 3
```

Your real layout may differ.

The objective is to understand how a logical database maps onto physical
cluster resources.

------------------------------------------------------------------------

## 43. Step 18 --- Verify Key Behavior

Run:

``` redis
SET tutorial:chapter01:counter 0 EX 300
INCR tutorial:chapter01:counter
INCR tutorial:chapter01:counter
INCR tutorial:chapter01:counter
GET tutorial:chapter01:counter
```

Expected final value:

``` text
3
```

Now verify expiration:

``` redis
TTL tutorial:chapter01:counter
```

This confirms:

``` text
client -> endpoint -> proxy -> shard -> response
```

without requiring the client to know the physical shard.

------------------------------------------------------------------------

## 44. Lab Failure Exercise 1 --- Wrong Port

Intentionally use a known incorrect, unused port in the test
environment.

Example:

``` bash
redis-cli -h "$REDIS_HOST" -p 19999 PING
```

Expected behavior:

``` text
connection failure
```

Troubleshooting lesson:

A connection failure does not automatically mean:

``` text
Redis database failure
```

Check the complete path:

``` text
DNS
 |
network
 |
firewall/security policy
 |
endpoint
 |
port
 |
TLS
 |
authentication
 |
proxy
 |
database
```

------------------------------------------------------------------------

## 45. Lab Failure Exercise 2 --- Authentication Failure

Use an intentionally incorrect password against the test database.

Expected result:

``` text
authentication error
```

Then restore the correct credential and confirm:

``` redis
PING
```

returns:

``` text
PONG
```

Operational lesson:

Differentiate:

``` text
network failure
authentication failure
authorization failure
database failure
```

They require different remediation.

------------------------------------------------------------------------

## 46. Lab Failure Exercise 3 --- Expiration

Create:

``` redis
SET tutorial:chapter01:expire-test value EX 10
```

Immediately:

``` redis
GET tutorial:chapter01:expire-test
TTL tutorial:chapter01:expire-test
```

Wait longer than ten seconds.

Then:

``` redis
GET tutorial:chapter01:expire-test
```

Expected:

``` text
(nil)
```

This is normal expiration, not data corruption.

------------------------------------------------------------------------

## 47. Optional Lab --- Observe Distribution

Only if approved in your test environment, create a small set of test
keys:

``` bash
for i in $(seq 1 100); do
  redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" --tls --cacert "$REDIS_CA" \
    SET "tutorial:chapter01:key:$i" "$i" EX 300 >/dev/null
done
```

Then inspect shard metrics/placement using the platform tooling.

Do not attempt to infer exact key placement from unsupported
assumptions.

The goal is simply to observe that the logical database can span
multiple shards while the application continues to use one endpoint.

------------------------------------------------------------------------

## 48. Cleanup

Delete only the tutorial keys you created.

Examples:

``` redis
DEL tutorial:chapter01:hello
DEL tutorial:chapter01:user:1001:name
DEL tutorial:chapter01:user:1001
DEL tutorial:chapter01:requests
DEL tutorial:chapter01:events
DEL tutorial:chapter01:counter
DEL tutorial:chapter01:expire-test
```

If you created the optional numbered keys, remove only that exact
tutorial namespace using a safe, reviewed method.

Never use:

``` redis
FLUSHDB
FLUSHALL
```

for cleanup.

------------------------------------------------------------------------

# Troubleshooting

## 49. `redis-cli` Cannot Connect

Check:

``` text
1. DNS resolution
2. Endpoint hostname
3. Endpoint port
4. Firewall/security group
5. Kubernetes/network policy if applicable
6. TLS requirement
7. Proxy/endpoint availability
8. Database status
```

Useful tests:

``` bash
nslookup <hostname>
nc -vz <hostname> <port>
```

PowerShell:

``` powershell
Resolve-DnsName <hostname>
Test-NetConnection <hostname> -Port <port>
```

------------------------------------------------------------------------

## 50. TCP Works but `PING` Fails

Investigate:

``` text
authentication
TLS configuration
ACL permissions
database state
client configuration
```

Do not treat successful TCP connectivity as proof that Redis
authentication is correct.

------------------------------------------------------------------------

## 51. Database Is Up but Application Is Slow

Do not immediately restart Redis.

Start by separating the layers:

``` text
Application
    |
Client pool
    |
Network
    |
Endpoint / Proxy
    |
Shard
    |
CPU / Memory
```

Capture evidence:

``` text
latency
connection count
timeouts
retries
shard CPU
proxy CPU
memory
evictions
network
hot keys
big keys
command mix
```

Later chapters provide the complete performance investigation workflow.

------------------------------------------------------------------------

## 52. One Node Is Down

Ask:

``` text
Did the cluster retain quorum?
Were primary shards on that node?
Were replicas available?
Did automatic failover occur?
Is replica redundancy being restored?
Is rack/zone placement still valid?
Is there enough capacity on surviving nodes?
```

Do not remove or replace the failed node until you understand the
current cluster state.

------------------------------------------------------------------------

## 53. Primary and Replica Placement Looks Wrong

Do not manually move shards based solely on a screenshot.

First verify:

``` bash
rladmin status
rladmin info cluster
rladmin info node
```

Then check:

-   database replication configuration
-   rack/zone configuration
-   available memory
-   node status
-   placement policy
-   ongoing migration/recovery
-   replica HA state

Escalate before changing placement in production.

------------------------------------------------------------------------

## 54. REST API Returns 401

Likely causes:

``` text
wrong username
wrong password
missing credentials
```

Verify authentication and role permissions.

Do not weaken security controls to make a lab command work.

------------------------------------------------------------------------

## 55. REST API TLS Error

Do not automatically add:

``` bash
-k
```

to production scripts.

Instead validate:

-   certificate chain
-   hostname
-   CA trust
-   expiration
-   correct management endpoint

Use certificate-verified HTTPS with an approved trust bundle; do not normalize TLS bypass flags even for ad hoc troubleshooting.

------------------------------------------------------------------------

# Production Engineering Concepts

## 56. Capacity Is Shared

A Redis Enterprise cluster can host multiple databases.

Example:

``` text
Cluster
|
+-- session-cache
+-- patient-cache
+-- api-rate-limit
+-- application-config
```

Even when databases are logically separate, they ultimately consume
cluster resources such as:

-   CPU
-   RAM
-   network
-   storage
-   node capacity

This is why cluster capacity planning matters.

------------------------------------------------------------------------

## 57. Database Isolation Is Not Infinite

Separate databases provide useful administrative and workload
boundaries, but they do not create physically independent hardware
unless deployed that way.

A noisy workload can still contribute to shared resource pressure.

Production monitoring therefore needs both:

``` text
database-level metrics
```

and:

``` text
node/cluster-level metrics
```

------------------------------------------------------------------------

## 58. Avoid One Giant Shared Keyspace

Where application architecture permits, avoid placing unrelated services
into one giant database simply because Redis supports many keys.

Separate databases can improve:

-   ownership
-   memory governance
-   access control
-   blast-radius management
-   monitoring
-   capacity planning
-   troubleshooting

The correct design depends on workload and operational requirements.

------------------------------------------------------------------------

## 59. Key Names Matter

Prefer predictable namespaces.

Example:

``` text
service:entity:id:attribute
```

Examples:

``` text
patient360:session:12345
claims:cache:member:98765
auth:ratelimit:user:1001
```

Avoid ambiguous keys such as:

``` text
123
data
cache1
temp
```

Key-design details are covered in Chapter 03.

------------------------------------------------------------------------

## 60. TTL Is an Architecture Decision

TTL should not be chosen arbitrarily.

Ask:

``` text
How stale may the data become?
How expensive is a cache miss?
How quickly can the source system recover?
What happens if millions of keys expire together?
How is invalidation performed?
```

TTL strategy affects:

-   correctness
-   memory
-   hit ratio
-   source database load
-   cache stampedes
-   recovery behavior

------------------------------------------------------------------------

## 61. Replication Is Not Backup

This is a critical production rule.

Replication protects availability from certain failures.

It does not inherently protect against:

``` text
bad application writes
accidental DEL
logical corruption
incorrect bulk update
credential misuse
```

because those operations can replicate.

A recovery strategy may require:

-   persistence
-   backups
-   source-of-truth reconstruction
-   Active-Active design
-   application-level replay

depending on the use case.

------------------------------------------------------------------------

## 62. Cache vs System of Record

For a pure cache:

``` text
Source database = authoritative
Redis = rebuildable
```

For other Redis use cases:

``` text
sessions
streams
counters
leaderboards
rate limits
operational state
```

the recovery requirements may be very different.

Never apply one durability policy to every Redis database without
understanding its data semantics.

------------------------------------------------------------------------

# Incident Thinking

## 63. Basic Failure Domains

A Redis Enterprise incident can occur at several layers:

``` text
Application
Client library
DNS
Network
Load balancer
Endpoint
Proxy
Shard
Database
Node
Cluster
Rack / Zone
Storage
Authentication
TLS
External dependency
```

A good SRE does not jump directly to:

``` text
"Redis is slow."
```

Instead ask:

``` text
Which layer is failing?
What evidence proves it?
What changed?
What is the blast radius?
```

------------------------------------------------------------------------

## 64. Architecture-Based Triage

When an application reports Redis errors:

### Step 1 --- Establish scope

``` text
one client?
one service?
one database?
multiple databases?
one node?
whole cluster?
```

### Step 2 --- Test endpoint

``` redis
PING
```

### Step 3 --- Inspect database

``` bash
rladmin status
```

### Step 4 --- Inspect nodes/shards

Check:

``` text
primary status
replica status
node health
migrations
failovers
```

### Step 5 --- Check resources

``` text
CPU
memory
network
connections
latency
evictions
```

### Step 6 --- Correlate timeline

Compare:

``` text
application errors
platform alerts
deployments
batch jobs
traffic spikes
maintenance
node events
```

This becomes the foundation of the later incident runbooks.

------------------------------------------------------------------------

# Operational Runbook

## 65. Runbook --- Application Cannot Reach Redis

``` text
1. Record affected application and database.
2. Record incident start time.
3. Resolve endpoint DNS.
4. Test endpoint TCP port.
5. Verify TLS requirements.
6. Verify authentication.
7. Run PING from an approved host.
8. Check rladmin status.
9. Check database status.
10. Check endpoint/proxy state.
11. Check shard state.
12. Check node state.
13. Review recent failover/migration events.
14. Determine blast radius.
15. Avoid configuration changes until evidence identifies the failing layer.
```

------------------------------------------------------------------------

## 66. Runbook --- Suspected Node Failure

``` text
1. Confirm the node state.
2. Identify databases/shards hosted by the node.
3. Determine whether affected shards were primary or replica.
4. Confirm automatic failover status.
5. Verify application availability.
6. Verify surviving primary/replica topology.
7. Check replica HA/recovery activity.
8. Check surviving-node capacity.
9. Verify rack/zone redundancy.
10. Preserve logs and timestamps.
11. Do not remove the node until recovery impact is understood.
12. Follow the dedicated HA/failure runbook in later chapters.
```

------------------------------------------------------------------------

# Validation

## 67. Architecture Questions

You should be able to answer all of these without guessing:

1.  What is a Redis Enterprise cluster?
2.  What is a node?
3.  What is a database?
4.  What is a shard?
5.  What is the difference between primary and replica shards?
6.  What does the Enterprise proxy do?
7.  What is the database endpoint?
8.  Why does the application not need to know shard placement?
9.  What problem does sharding solve?
10. What problem does replication solve?
11. Why is replication not backup?
12. What does rack/zone awareness protect against?
13. What is replica HA?
14. What is the difference between `redis-cli` and `rladmin`?
15. Why does adding a node not automatically scale a one-shard database?

------------------------------------------------------------------------

## 68. Hands-On Acceptance Checklist

Complete the following:

-   [ ] Resolve the Redis database hostname.
-   [ ] Verify the endpoint port.
-   [ ] Connect using `redis-cli`.
-   [ ] Receive `PONG`.
-   [ ] Create a namespaced test key.
-   [ ] Read the test key.
-   [ ] Verify its TTL.
-   [ ] Inspect `INFO server`.
-   [ ] Inspect `INFO memory`.
-   [ ] Inspect `INFO stats`.
-   [ ] Run `rladmin status`.
-   [ ] Inspect cluster configuration.
-   [ ] Identify the target database.
-   [ ] Identify its endpoint.
-   [ ] Identify its shard count.
-   [ ] Identify primary shards.
-   [ ] Identify replica shards.
-   [ ] Identify node placement.
-   [ ] Inspect proxy information.
-   [ ] Query the REST API.
-   [ ] List nodes using the API.
-   [ ] List databases using the API.
-   [ ] List shards using the API.
-   [ ] Draw the database's physical architecture.
-   [ ] Test an authentication failure.
-   [ ] Test key expiration.
-   [ ] Remove tutorial keys.
-   [ ] Confirm no production configuration was modified.

------------------------------------------------------------------------

## 69. Production Readiness Checklist

Before considering the architecture understood, verify that the team
knows:

``` text
Cluster size
Node sizing
Failure domains
Database inventory
Database ownership
Memory limits
Shard counts
Replication settings
Persistence settings
Backup requirements
Endpoints
TLS requirements
Authentication model
Monitoring location
Alert ownership
Recovery expectations
RPO
RTO
```

Unknown answers should become operational follow-up items.

------------------------------------------------------------------------

## 70. Key Takeaways

1.  Redis Enterprise is a platform for operating Redis databases across
    a cluster.
2.  Applications connect to a database endpoint rather than individual
    shards.
3.  Enterprise proxies route commands to the appropriate shards.
4.  Sharding scales a database across multiple Redis instances.
5.  Replication creates additional copies for high availability.
6.  Primary and corresponding replica shards should be separated across
    failure domains.
7.  Replica HA helps restore redundancy after failure.
8.  Persistence and backup address different durability/recovery
    concerns from replication.
9.  `redis-cli` operates against Redis data; `rladmin` operates against
    the Enterprise platform.
10. The REST API enables management automation.
11. Adding nodes increases cluster capacity, but database scaling still
    depends on shard/workload design.
12. Production troubleshooting should follow the request path rather
    than immediately blaming Redis.

------------------------------------------------------------------------

## 71. Completion

**Chapter 01 is complete when you can explain and inspect:**

``` text
Client
  |
  v
Database Endpoint
  |
  v
Enterprise Proxy
  |
  v
Primary Shard
  |
  v
Replica Shard
```

and map those components to the actual Redis Enterprise cluster used in
your lab.

------------------------------------------------------------------------

## Next Chapter

**Chapter 02 --- Connecting to Redis Enterprise: Clients, Endpoints, TLS
& Connection Management**

Chapter 02 will go deeper into:

-   database endpoints
-   `redis-cli`
-   authentication
-   TLS
-   connection strings
-   client libraries
-   connection pooling
-   timeouts
-   retries
-   health checks
-   Kubernetes connectivity
-   DNS
-   connection troubleshooting
-   production client configuration
