# Chapter 02 --- Connecting to Redis Enterprise: Clients, Endpoints, TLS & Connection Management

**Status:** Canonical\
**Track:** Redis Enterprise / Redis Software Production Engineering\
**Level:** Foundation → Production Operations\
**Audience:** SREs, DBREs, Platform Engineers, Redis Administrators,
Developers\
**Lab type:** Connectivity, TLS, client configuration, failure
injection, and troubleshooting

------------------------------------------------------------------------

## 1. Objective

A Redis database can be healthy while an application is completely
unable to use it because of DNS, routing, firewall, TLS, authentication,
connection-pool, timeout, or retry problems.

This chapter teaches the complete connection path from an application to
a Redis Enterprise database.

By the end, you should be able to:

-   Identify the correct Redis Enterprise database endpoint and port.
-   Explain why applications should use the database endpoint instead of
    a specific shard.
-   Connect with `redis-cli`.
-   Authenticate with password and ACL-style username/password
    credentials where configured.
-   Understand `redis://` and `rediss://` connection URIs.
-   Connect over TLS and validate the server certificate.
-   Understand mutual TLS (mTLS).
-   Inspect certificates with OpenSSL.
-   Configure a production Python client.
-   Understand connection pools.
-   Configure connect, socket, and health-check behavior.
-   Design bounded retries with backoff and jitter.
-   Avoid retry storms.
-   Test DNS, TCP, TLS, authentication, and Redis independently.
-   Troubleshoot Kubernetes connectivity.
-   Distinguish network, TLS, authentication, authorization, and Redis
    failures.
-   Execute a production connection-troubleshooting runbook.

------------------------------------------------------------------------

## 2. The Connection Path

A typical application connection is:

``` text
Application
    |
    v
Redis client library
    |
    v
DNS resolver
    |
    v
Network / firewall / security policy
    |
    v
Redis Enterprise database endpoint
    |
    v
Enterprise proxy
    |
    v
Correct database shard
```

If TLS is enabled:

``` text
Application
    |
Redis client
    |
DNS
    |
TCP
    |
TLS handshake
    |
Authentication
    |
Enterprise proxy
    |
Redis command
```

A failure at any layer can look like:

``` text
Redis connection failed
```

to the application.

The SRE's job is to identify the exact failing layer.

------------------------------------------------------------------------

## 3. Database Endpoint

A Redis Enterprise database endpoint contains:

``` text
hostname / FQDN
+
database port
```

Conceptual example:

``` text
redis-cache.example.internal:12000
```

The endpoint is the stable application-facing abstraction.

The application should not normally connect directly to:

``` text
individual shard process
specific primary shard
specific replica shard
random cluster node port
```

The Enterprise platform can move shards during:

-   failover
-   maintenance
-   resharding
-   rebalancing
-   node replacement

The endpoint and proxy architecture hides that physical placement from
clients.

------------------------------------------------------------------------

## 4. Find the Correct Endpoint

The Redis Enterprise Cluster Manager UI exposes database endpoint
information in the database configuration.

Before troubleshooting, record:

``` text
Database name:
Database ID:
Endpoint FQDN:
Port:
TLS enabled:
Authentication method:
Expected username:
Expected CA:
Client certificate required:
```

Do not begin troubleshooting with an assumed hostname or port copied
from an old ticket.

------------------------------------------------------------------------

## 5. Public vs Private Connectivity

Depending on architecture, a database may be reachable through different
network paths.

Examples:

``` text
private corporate network
VPC/VNet
Kubernetes network
peered network
VPN
approved public endpoint
```

Production applications should normally use the connectivity path
approved by the organization's security architecture.

A working connection from your laptop does not prove that the
application pod or VM can connect.

Always test from the affected client network when possible.

------------------------------------------------------------------------

## 6. DNS

The endpoint hostname must resolve from the client.

Linux:

``` bash
dig <REDIS_ENDPOINT>
```

or:

``` bash
nslookup <REDIS_ENDPOINT>
```

PowerShell:

``` powershell
Resolve-DnsName <REDIS_ENDPOINT>
```

Expected:

``` text
one or more valid addresses
```

If the endpoint resolves on a Redis Enterprise node but not from the
client environment, investigate client-side or enterprise DNS.

DNS is a separate dependency from Redis itself.

------------------------------------------------------------------------

## 7. Test TCP Before Redis

Linux:

``` bash
nc -vz <REDIS_ENDPOINT> <REDIS_PORT>
```

Alternative:

``` bash
telnet <REDIS_ENDPOINT> <REDIS_PORT>
```

PowerShell:

``` powershell
Test-NetConnection <REDIS_ENDPOINT> -Port <REDIS_PORT>
```

A successful TCP test means:

``` text
DNS/routing/firewall/TCP path is sufficiently functional to establish the socket
```

It does **not** prove:

``` text
TLS works
authentication works
Redis commands work
application client configuration is correct
```

------------------------------------------------------------------------

## 8. `redis-cli`

`redis-cli` is one of the most useful tools for separating application
problems from platform problems.

Basic connection:

``` bash
redis-cli -h <REDIS_ENDPOINT> -p <REDIS_PORT>
```

Password example:

``` bash
redis-cli \
  -h <REDIS_ENDPOINT> \
  -p <REDIS_PORT> \
  -a '<PASSWORD>'
```

Then:

``` redis
PING
```

Expected:

``` text
PONG
```

------------------------------------------------------------------------

## 9. Avoid Password Exposure

This works:

``` bash
redis-cli -a '<PASSWORD>'
```

but command-line arguments can be exposed through shell history or
process inspection.

For interactive troubleshooting, Redis supports:

``` bash
export REDISCLI_AUTH='<PASSWORD>'
```

then:

``` bash
redis-cli -h <REDIS_ENDPOINT> -p <REDIS_PORT>
```

PowerShell:

``` powershell
$env:REDISCLI_AUTH="<PASSWORD>"
redis-cli -h <REDIS_ENDPOINT> -p <REDIS_PORT>
```

Unset it afterward.

Linux:

``` bash
unset REDISCLI_AUTH
```

PowerShell:

``` powershell
Remove-Item Env:REDISCLI_AUTH
```

Production applications should use an approved secrets-management
mechanism rather than hard-coded credentials.

------------------------------------------------------------------------

## 10. Username and Password Authentication

Modern Redis access control can use a username and password.

Conceptual connection:

``` bash
redis-cli \
  -h <REDIS_ENDPOINT> \
  -p <REDIS_PORT> \
  --user <USERNAME> \
  -a '<PASSWORD>'
```

Inside an existing connection, authentication syntax can be:

``` redis
AUTH <USERNAME> <PASSWORD>
```

Do not assume every environment uses the `default` user.

Production systems should use explicitly managed identities and least
privilege where the platform design supports them.

------------------------------------------------------------------------

## 11. Redis Connection URIs

Many client libraries support URI-style configuration.

Without TLS:

``` text
redis://username:password@hostname:port
```

With TLS:

``` text
rediss://username:password@hostname:port
```

The extra `s` conventionally indicates TLS:

``` text
redis://   -> plaintext Redis connection
rediss://  -> Redis over TLS
```

Do not store a URI containing a real password in:

``` text
Git
Dockerfile
ConfigMap
ticket
wiki page
application log
shell history
```

Use a secret reference.

------------------------------------------------------------------------

## 12. TLS

TLS protects client-to-database traffic.

Simplified handshake:

``` text
Client
  |
  | TCP connect
  v
Redis endpoint
  |
  | server certificate
  v
Client validates:
  - issuing CA
  - hostname
  - certificate validity
  |
  v
encrypted Redis session
```

TLS can provide:

-   encryption in transit
-   server identity validation
-   optional client identity with mTLS

------------------------------------------------------------------------

## 13. Redis Enterprise Proxy Certificate

For Redis Enterprise / Redis Software, client TLS connections use the
database/proxy certificate chain.

A controlled lab may use the platform-generated certificate.

Production environments commonly replace or integrate certificates
according to organizational PKI requirements.

The client needs to trust the CA/certificate used by the database
endpoint.

------------------------------------------------------------------------

## 14. Connect with TLS

Typical `redis-cli` syntax:

``` bash
redis-cli \
  -h <REDIS_ENDPOINT> \
  -p <REDIS_PORT> \
  --tls \
  --cacert proxy_cert.pem
```

With password:

``` bash
redis-cli \
  -h <REDIS_ENDPOINT> \
  -p <REDIS_PORT> \
  --tls \
  --cacert proxy_cert.pem \
  -a '<PASSWORD>'
```

Expected:

``` redis
PING
```

returns:

``` text
PONG
```

------------------------------------------------------------------------

## 15. Do Not Normalize `--insecure`

A troubleshooting command may bypass certificate verification.

That can help isolate a certificate problem, but it should not become
the production configuration.

The correct production design is:

``` text
client trusts approved CA
+
hostname validation succeeds
+
certificate is valid
```

not:

``` text
disable TLS verification permanently
```

------------------------------------------------------------------------

## 16. Inspect TLS with OpenSSL

Test the endpoint:

``` bash
openssl s_client \
  -connect <REDIS_ENDPOINT>:<REDIS_PORT> \
  -servername <REDIS_ENDPOINT>
```

Inspect:

-   certificate subject
-   issuer
-   validity dates
-   certificate chain
-   negotiated TLS version
-   verification result

Useful certificate command:

``` bash
openssl x509 \
  -in proxy_cert.pem \
  -noout \
  -subject \
  -issuer \
  -dates
```

Expected fields include:

``` text
subject=
issuer=
notBefore=
notAfter=
```

------------------------------------------------------------------------

## 17. Hostname Validation

A certificate can be cryptographically valid but still be wrong for the
endpoint hostname.

Example:

``` text
Endpoint:
redis-prod.example.internal

Certificate:
CN=redis-old.example.internal
```

A strict client can reject this.

Do not solve hostname mismatch by globally disabling verification.

Fix the endpoint/certificate design.

------------------------------------------------------------------------

## 18. Expired Certificates

Check:

``` bash
openssl x509 -in proxy_cert.pem -noout -dates
```

A certificate past:

``` text
notAfter
```

is expired.

Certificate expiration can cause widespread connection failures even
while Redis shards remain healthy.

Certificate monitoring therefore belongs in production observability.

------------------------------------------------------------------------

## 19. Mutual TLS

Normal server-authenticated TLS:

``` text
Client validates server
```

Mutual TLS:

``` text
Client validates server
+
Server validates client certificate
```

Conceptual `redis-cli` command:

``` bash
redis-cli \
  -h <REDIS_ENDPOINT> \
  -p <REDIS_PORT> \
  --tls \
  --cacert proxy_cert.pem \
  --cert redis_user.crt \
  --key redis_user_private.key
```

The private key must be protected carefully.

Never commit:

``` text
*.key
client private keys
real certificates containing sensitive private material
```

to a tutorial repository.

------------------------------------------------------------------------

## 20. TLS Changes and Existing Connections

An important operational detail:

> TLS configuration changes apply to new connections; existing
> connections may continue until clients disconnect/reconnect.

Therefore a TLS migration needs:

``` text
1. client configuration prepared
2. certificate trust prepared
3. TLS setting changed
4. clients deliberately recycle/reconnect
5. new connections validated
```

Otherwise teams may incorrectly conclude the change is successful
because old pooled connections still work.

------------------------------------------------------------------------

# Client Architecture

## 21. Application Client Libraries

Applications should use a supported Redis client for their language.

Examples include clients for:

``` text
Python
Java
Node.js
Go
.NET
```

Client libraries handle:

-   socket creation
-   command encoding
-   response parsing
-   authentication
-   TLS
-   connection pooling
-   retries
-   timeouts
-   pipelining
-   health checks

They do not configure the Redis Enterprise platform itself.

Platform administration belongs to tools such as:

``` text
Cluster Manager
rladmin
REST API
```

------------------------------------------------------------------------

## 22. Connection Pooling

Creating a new TCP/TLS connection for every Redis command is
inefficient.

Preferred application architecture:

``` text
Application workers
      |
      v
Connection pool
  |   |   |   |
  v   v   v   v
Redis connections
      |
      v
Database endpoint
```

Benefits:

-   connection reuse
-   lower handshake overhead
-   predictable connection management
-   better throughput
-   reduced server connection churn

But an unbounded pool can become a production problem.

------------------------------------------------------------------------

## 23. Connection Budget

Suppose:

``` text
100 application pods
x
50 possible Redis connections per pod
=
5,000 potential connections
```

Now add:

``` text
multiple services
deployment overlap
autoscaling
batch workers
health checks
admin tools
```

Connection count can grow quickly.

Capacity planning should therefore include:

``` text
pods × workers × pool size × services
```

not just database memory.

------------------------------------------------------------------------

## 24. Connect Timeout

Connect timeout controls how long the client waits to establish a
connection.

Conceptually:

``` text
client
  |
  | connect()
  |
  |------ timeout ------|
```

Too short:

``` text
transient network delay becomes unnecessary failure
```

Too long:

``` text
application threads/workers may hang waiting for unreachable Redis
```

Set it according to application SLOs and network expectations.

------------------------------------------------------------------------

## 25. Command / Socket Timeout

After a connection exists, a client also needs a bounded wait for Redis
responses.

Conceptually:

``` text
SET key value
     |
     |------ socket timeout ------|
     v
response
```

A timeout should be:

-   long enough for expected healthy behavior
-   short enough to preserve the application's latency budget

Do not blindly copy a timeout from another service.

------------------------------------------------------------------------

## 26. Retry Strategy

Transient failures can justify retries.

But this is dangerous:

``` text
Redis slows
  |
applications retry immediately
  |
traffic multiplies
  |
Redis slows more
  |
more retries
```

This is a retry storm.

Preferred pattern:

``` text
bounded retries
+
exponential backoff
+
jitter
+
timeouts
+
application fallback/circuit breaking where appropriate
```

------------------------------------------------------------------------

## 27. Retry Safety

Not every operation should be blindly retried.

Consider:

``` redis
INCR billing:event:count
```

If the client times out after the server executed the command but before
the response arrived, retrying can execute it twice.

This is an ambiguous outcome.

For retry-sensitive workflows, consider:

-   idempotent operations
-   request IDs
-   deduplication
-   transactional design
-   application-level semantics

A network timeout does not prove the Redis command did not execute.

------------------------------------------------------------------------

## 28. Health Checks

A basic Redis health check is:

``` redis
PING
```

But application readiness may require more context.

Examples:

``` text
DNS resolves
TCP works
TLS works
AUTH works
PING works
required command permissions work
```

Avoid expensive health checks that themselves create load.

------------------------------------------------------------------------

# Python Production Client Example

## 29. Basic `redis-py` Example

Install:

``` bash
pip install redis
```

Example:

``` python
import os
import redis

client = redis.Redis(
    host=os.environ["REDIS_HOST"],
    port=int(os.environ["REDIS_PORT"]),
    username=os.environ.get("REDIS_USERNAME"),
    password=os.environ["REDIS_PASSWORD"],
    socket_connect_timeout=3,
    socket_timeout=2,
    health_check_interval=30,
    decode_responses=True,
)

print(client.ping())
```

Expected:

``` text
True
```

Do not hard-code credentials.

------------------------------------------------------------------------

## 30. Python TLS Example

``` python
import os
import redis

client = redis.Redis(
    host=os.environ["REDIS_HOST"],
    port=int(os.environ["REDIS_PORT"]),
    username=os.environ.get("REDIS_USERNAME"),
    password=os.environ["REDIS_PASSWORD"],
    ssl=True,
    ssl_ca_certs=os.environ["REDIS_CA_CERT"],
    socket_connect_timeout=3,
    socket_timeout=2,
    health_check_interval=30,
    decode_responses=True,
)

print(client.ping())
```

The exact TLS parameters depend on client version and security
architecture.

Validate against the client version used by your application.

------------------------------------------------------------------------

## 31. Explicit Connection Pool Example

``` python
import os
import redis

pool = redis.ConnectionPool(
    host=os.environ["REDIS_HOST"],
    port=int(os.environ["REDIS_PORT"]),
    username=os.environ.get("REDIS_USERNAME"),
    password=os.environ["REDIS_PASSWORD"],
    max_connections=50,
    socket_connect_timeout=3,
    socket_timeout=2,
    health_check_interval=30,
    decode_responses=True,
)

client = redis.Redis(connection_pool=pool)

print(client.ping())
```

`50` is an example, not a universal recommendation.

Calculate pool limits from application concurrency and total fleet size.

------------------------------------------------------------------------

## 32. Retry Example

Modern `redis-py` supports retry behavior and backoff strategies.

Conceptual example:

``` python
from redis import Redis
from redis.retry import Retry
from redis.backoff import ExponentialWithJitterBackoff
from redis.exceptions import ConnectionError, TimeoutError

retry = Retry(
    ExponentialWithJitterBackoff(),
    3,
)

client = Redis(
    host="redis.example.internal",
    port=12000,
    socket_connect_timeout=3,
    socket_timeout=2,
    retry=retry,
    retry_on_error=[
        ConnectionError,
        TimeoutError,
    ],
)
```

Confirm syntax against the exact `redis-py` version deployed.

Production principle:

``` text
retry only known transient failures
+
bound retry count
+
backoff
+
jitter
```

------------------------------------------------------------------------

# Kubernetes Connectivity

## 33. Application Pod to Redis

A Kubernetes workload may follow:

``` text
Pod
 |
CoreDNS
 |
Kubernetes network
 |
egress policy
 |
VPC/VNet routing
 |
Redis endpoint
```

A Redis database can be perfectly healthy while a Kubernetes
`NetworkPolicy` blocks the pod.

------------------------------------------------------------------------

## 34. DNS from a Pod

Run from an approved troubleshooting pod/container:

``` bash
nslookup <REDIS_ENDPOINT>
```

or:

``` bash
getent hosts <REDIS_ENDPOINT>
```

If DNS fails inside the pod but works from your workstation, investigate
Kubernetes DNS/network configuration rather than Redis.

------------------------------------------------------------------------

## 35. TCP from a Pod

``` bash
nc -vz <REDIS_ENDPOINT> <REDIS_PORT>
```

If unavailable, use an approved diagnostic image that contains
networking utilities.

Do not permanently add unnecessary troubleshooting binaries to hardened
application images merely for convenience.

------------------------------------------------------------------------

## 36. Redis Test from a Pod

Run this only from an **approved troubleshooting container in the same network and security context as the affected workload**, with `redis-cli` installed and permission to test the database endpoint. For a remote Redis Software/Enterprise endpoint, **require certificate-validated TLS and the approved database identity**. Obtain `REDISCLI_AUTH` through an approved ephemeral secret-injection mechanism rather than passing a password in command arguments.

``` bash
: "${REDIS_HOST:?Approved Redis endpoint is required}"
: "${REDIS_PORT:?Approved database port is required}"
: "${REDIS_CA:?Trusted CA bundle is required}"
: "${REDISCLI_AUTH:?Approved Redis database secret is required}"
test -r "$REDIS_CA" || { echo "Missing trusted CA bundle" >&2; exit 2; }

if [[ -n "${REDIS_USER:-}" ]]; then
  redis-cli --tls --cacert "$REDIS_CA" --user "$REDIS_USER" \
    -h "$REDIS_HOST" -p "$REDIS_PORT" PING
else
  redis-cli --tls --cacert "$REDIS_CA" \
    -h "$REDIS_HOST" -p "$REDIS_PORT" PING
fi
```

**Expected:** `PONG` for a reachable endpoint with valid server certificate, authentication and `PING` permission. A TLS/certificate error, ACL denial, timeout, or DNS failure must be retained as evidence; **do not** disable TLS verification or weaken ACLs merely to get `PONG`. If mutual TLS is required, supply the approved `--cert` and `--key` options in addition to the CA and fail closed if those files are unavailable. Avoid including passwords or secret-bearing environment dumps in a ticket. Unset any temporary interactive secret after the test.

Compare:

``` text
application fails
approved TLS redis-cli PING succeeds from the same workload context
```

This shifts investigation toward application client configuration **but does not rule out ACL authorization for other commands, client-library behavior, connection pooling, or a pod-specific identity/network difference**. The test is read-only and **NOT EXECUTED** by the V02 static review.

See [Redis Software TLS client documentation](https://redis.io/docs/latest/operate/rs/security/encryption/tls/enable-tls/).

------------------------------------------------------------------------

# Hands-On Lab

## 37. Lab Goal

You will validate the entire connection stack:

``` text
DNS
TCP
TLS
Authentication
Redis protocol
Client library
Connection pool
Timeout behavior
Retry behavior
```

Use a non-production database.

------------------------------------------------------------------------

## 38. Lab Variables

Linux/macOS:

``` bash
export REDIS_HOST="redis-test.example.internal"
export REDIS_PORT="12000"
export REDIS_USERNAME="<username>"
export REDIS_PASSWORD="<secret>"
export REDIS_CA_CERT="/path/to/proxy_cert.pem"
```

PowerShell:

``` powershell
$env:REDIS_HOST="redis-test.example.internal"
$env:REDIS_PORT="12000"
$env:REDIS_USERNAME="<username>"
$env:REDIS_PASSWORD="<secret>"
$env:REDIS_CA_CERT="C:\path\to\proxy_cert.pem"
```

Use the username only if the database authentication model requires one.

------------------------------------------------------------------------

## 39. Lab 1 --- Resolve Endpoint

Linux:

``` bash
dig "$REDIS_HOST"
```

PowerShell:

``` powershell
Resolve-DnsName $env:REDIS_HOST
```

Record:

``` text
Resolved address:
DNS server:
Resolution successful: yes/no
```

------------------------------------------------------------------------

## 40. Lab 2 --- Test TCP

Linux:

``` bash
nc -vz "$REDIS_HOST" "$REDIS_PORT"
```

PowerShell:

``` powershell
Test-NetConnection $env:REDIS_HOST -Port $env:REDIS_PORT
```

Record:

``` text
TCP success:
Latency if available:
```

------------------------------------------------------------------------

## 41. Lab 3 --- Test Redis Protocol

Set:

``` bash
export REDISCLI_AUTH="$REDIS_PASSWORD"
```

Then:

``` bash
redis-cli \
  -h "$REDIS_HOST" \
  -p "$REDIS_PORT" \
  PING
```

Expected:

``` text
PONG
```

If username is required:

``` bash
redis-cli \
  -h "$REDIS_HOST" \
  -p "$REDIS_PORT" \
  --user "$REDIS_USERNAME" \
  PING
```

------------------------------------------------------------------------

## 42. Lab 4 --- Inspect Client Connection

Run:

``` redis
CLIENT ID
```

Then:

``` redis
CLIENT INFO
```

Observe the current connection.

Do not use disruptive client-management commands against unrelated
production connections.

------------------------------------------------------------------------

## 43. Lab 5 --- Verify Read/Write

``` redis
SET tutorial:chapter02:connection-test "connected" EX 300
GET tutorial:chapter02:connection-test
TTL tutorial:chapter02:connection-test
```

Expected:

``` text
OK
connected
positive TTL
```

------------------------------------------------------------------------

## 44. Lab 6 --- Validate TLS Certificate

If TLS is enabled:

``` bash
openssl s_client \
  -connect "$REDIS_HOST:$REDIS_PORT" \
  -servername "$REDIS_HOST"
```

Record:

``` text
Subject:
Issuer:
Not before:
Not after:
TLS version:
Verify return code:
```

Then:

``` bash
openssl x509 \
  -in "$REDIS_CA_CERT" \
  -noout \
  -subject \
  -issuer \
  -dates
```

------------------------------------------------------------------------

## 45. Lab 7 --- Connect with TLS

``` bash
redis-cli \
  -h "$REDIS_HOST" \
  -p "$REDIS_PORT" \
  --tls \
  --cacert "$REDIS_CA_CERT" \
  PING
```

Expected:

``` text
PONG
```

Add `--user` if required.

------------------------------------------------------------------------

## 46. Lab 8 --- Python Client

Create:

``` python
import os
import redis

r = redis.Redis(
    host=os.environ["REDIS_HOST"],
    port=int(os.environ["REDIS_PORT"]),
    username=os.environ.get("REDIS_USERNAME"),
    password=os.environ["REDIS_PASSWORD"],
    socket_connect_timeout=3,
    socket_timeout=2,
    health_check_interval=30,
    decode_responses=True,
)

print("PING:", r.ping())

r.set(
    "tutorial:chapter02:python",
    "working",
    ex=300,
)

print(
    "GET:",
    r.get("tutorial:chapter02:python"),
)
```

Expected:

``` text
PING: True
GET: working
```

------------------------------------------------------------------------

## 47. Failure Injection 1 --- Bad DNS

Use an intentionally invalid test hostname:

``` bash
redis-cli \
  -h redis-does-not-exist.invalid \
  -p "$REDIS_PORT" \
  PING
```

Expected:

``` text
name resolution failure
```

Diagnosis:

``` text
DNS layer
```

not:

``` text
Redis shard failure
```

------------------------------------------------------------------------

## 48. Failure Injection 2 --- Wrong Port

``` bash
redis-cli \
  -h "$REDIS_HOST" \
  -p 19999 \
  PING
```

Expected:

``` text
connection refused or timeout
```

Diagnosis can involve:

``` text
wrong port
firewall
endpoint
routing
```

------------------------------------------------------------------------

## 49. Failure Injection 3 --- Wrong Password

Temporarily:

``` bash
export REDISCLI_AUTH="definitely-wrong"
```

Then:

``` bash
redis-cli \
  -h "$REDIS_HOST" \
  -p "$REDIS_PORT" \
  PING
```

Expected:

``` text
authentication error
```

Restore:

``` bash
export REDISCLI_AUTH="$REDIS_PASSWORD"
```

------------------------------------------------------------------------

## 50. Failure Injection 4 --- Wrong Username

If ACL users are enabled:

``` bash
redis-cli \
  -h "$REDIS_HOST" \
  -p "$REDIS_PORT" \
  --user invalid-user \
  -a "$REDIS_PASSWORD" \
  PING
```

Expected:

``` text
authentication failure
```

This demonstrates why:

``` text
credential exists
```

does not necessarily mean:

``` text
identity is correct
```

------------------------------------------------------------------------

## 51. Failure Injection 5 --- Certificate Trust Failure

In a test environment, point the client at an unrelated CA file.

Expected:

``` text
certificate verification failure
```

Then restore the correct CA.

Do not solve the exercise by permanently disabling certificate
validation.

------------------------------------------------------------------------

## 52. Failure Injection 6 --- Timeout

Use a deliberately unreachable test address or blocked endpoint approved
for lab use and configure a short connect timeout.

Observe how quickly the application returns control.

The purpose is to understand:

``` text
bounded failure
```

versus:

``` text
worker hangs for a long period
```

------------------------------------------------------------------------

## 53. Failure Injection 7 --- Pool Exhaustion

In a development environment only, configure a very small client
connection pool and create more concurrent Redis operations than the
pool permits.

Observe:

-   waiting
-   connection errors
-   application latency

Lesson:

> Redis can be healthy while the application fails because its own
> connection pool is exhausted.

Restore normal configuration afterward.

------------------------------------------------------------------------

# Troubleshooting Decision Tree

## 54. Layer 1 --- DNS

Run:

``` bash
dig <endpoint>
```

If failure:

``` text
Investigate DNS.
Stop blaming Redis.
```

If success:

``` text
continue to TCP
```

------------------------------------------------------------------------

## 55. Layer 2 --- TCP

Run:

``` bash
nc -vz <endpoint> <port>
```

If failure:

``` text
routing
firewall
security group
NetworkPolicy
wrong port
endpoint availability
```

If success:

``` text
continue to TLS
```

------------------------------------------------------------------------

## 56. Layer 3 --- TLS

Run:

``` bash
openssl s_client \
  -connect <endpoint>:<port> \
  -servername <endpoint>
```

Investigate:

``` text
expired certificate
untrusted issuer
hostname mismatch
protocol mismatch
cipher mismatch
missing client certificate
```

If success:

``` text
continue to authentication
```

------------------------------------------------------------------------

## 57. Layer 4 --- Authentication

Run:

``` bash
redis-cli ... PING
```

Investigate:

``` text
wrong username
wrong password
disabled user
wrong authentication method
certificate identity mismatch
```

------------------------------------------------------------------------

## 58. Layer 5 --- Authorization

A client may authenticate successfully but still lack permission for a
command.

Example:

``` text
AUTH succeeds
GET succeeds
CONFIG fails
```

This may be correct least-privilege behavior.

Do not grant broad privileges simply to eliminate an expected
authorization error.

------------------------------------------------------------------------

## 59. Layer 6 --- Application Client

If:

``` text
redis-cli works from same host/pod
application fails
```

investigate:

``` text
client URI
TLS settings
CA path
username
password source
connection pool
timeouts
retry configuration
library version
DNS caching
application thread exhaustion
```

------------------------------------------------------------------------

# Common Production Failures

## 60. Connection Refused

Usually indicates:

``` text
host reachable
but no listener / rejected port
```

Check:

-   endpoint
-   port
-   proxy/database state
-   network translation
-   service configuration

------------------------------------------------------------------------

## 61. Connection Timeout

Potential causes:

``` text
routing
firewall drop
security policy
network congestion
unreachable endpoint
client timeout too aggressive
```

A timeout is not automatically a Redis CPU problem.

------------------------------------------------------------------------

## 62. Authentication Error

Check:

``` text
username
password
user status
secret version
secret rotation
ACL
authentication method
```

Correlate with recent credential rotations.

------------------------------------------------------------------------

## 63. TLS Handshake Error

Check:

``` text
CA
certificate expiration
hostname
client certificate
private key
TLS version
cipher compatibility
```

Inspect with OpenSSL before changing Redis.

------------------------------------------------------------------------

## 64. Intermittent Connection Failures

Investigate:

``` text
connection pool exhaustion
network instability
DNS
proxy/endpoint behavior
client retry storm
autoscaling
NAT/SNAT exhaustion
TLS reconnect churn
application deployment
node/failover events
```

Capture timestamps.

Intermittent failures are difficult to diagnose without correlation.

------------------------------------------------------------------------

## 65. Too Many Connections

Calculate:

``` text
application instances
× workers
× pool maximum
```

Then add deployment overlap.

Example:

``` text
200 pods
× 40 connections
=
8,000 connections
```

During rolling deployment:

``` text
old pods + new pods
```

may temporarily increase that substantially.

Connection budgets must account for deployment behavior.

------------------------------------------------------------------------

## 66. Retry Storm

Symptoms:

``` text
Redis latency increases
application timeout increases
retry count spikes
connection count rises
Redis traffic rises
```

Mitigation principles:

``` text
bounded retry
backoff
jitter
circuit breaking
load shedding
source fallback control
```

Never configure infinite immediate retries.

------------------------------------------------------------------------

# Operational Runbook

## 67. Runbook --- Redis Connection Failure

Capture first:

``` text
Timestamp:
Application:
Environment:
Database:
Endpoint:
Port:
TLS:
Error:
Affected percentage:
Recent deployment:
Recent credential rotation:
```

Then execute:

``` text
1. Resolve endpoint DNS.
2. Test TCP port.
3. Inspect TLS handshake.
4. Validate certificate dates.
5. Test redis-cli from affected client network.
6. Validate username/password or certificate.
7. Run PING.
8. Run a permitted read operation.
9. Compare application client settings.
10. Inspect pool usage.
11. Inspect client timeouts.
12. Inspect retries.
13. Check Redis Enterprise database health.
14. Check proxy/endpoint health.
15. Check node/shard events.
16. Correlate application and platform timelines.
17. Apply the smallest evidence-based remediation.
18. Validate recovery.
```

------------------------------------------------------------------------

## 68. Runbook --- TLS Failure

``` text
1. Record endpoint and port.
2. Run openssl s_client.
3. Capture certificate subject.
4. Capture issuer.
5. Check notBefore/notAfter.
6. Check hostname/SAN match.
7. Check trusted CA.
8. Check required client certificate.
9. Check private-key pairing.
10. Check TLS protocol compatibility.
11. Check recent certificate rotation.
12. Test redis-cli with explicit CA.
13. Recycle a controlled test connection.
14. Validate new connections.
15. Do not rely on old pooled connections.
```

------------------------------------------------------------------------

## 69. Runbook --- Application Fails but `redis-cli` Works

``` text
1. Run redis-cli from the same application host/pod.
2. Confirm endpoint and port match application config.
3. Confirm TLS mode.
4. Confirm CA/certificate path.
5. Confirm username.
6. Confirm secret version.
7. Inspect connection URI.
8. Inspect connection pool.
9. Inspect connect timeout.
10. Inspect command timeout.
11. Inspect retry configuration.
12. Inspect client-library version.
13. Inspect application logs.
14. Test a minimal client program.
15. Compare minimal client with application configuration.
```

------------------------------------------------------------------------

# Production Design Guidance

## 70. Separate Secrets from Configuration

Configuration:

``` text
host
port
TLS enabled
pool size
timeouts
```

Secrets:

``` text
password
private key
client certificate secret material
```

Use the organization's approved secret store.

For Kubernetes, avoid placing passwords directly into ordinary
ConfigMaps.

------------------------------------------------------------------------

## 71. Set Explicit Timeouts

Production clients should generally avoid unbounded waits.

Define:

``` text
connect timeout
command/socket timeout
pool wait behavior
```

according to the application's latency budget.

Document the rationale.

------------------------------------------------------------------------

## 72. Bound Connection Pools

Do not use:

``` text
unlimited connections
```

as a substitute for capacity planning.

Track:

``` text
connections per process
processes per pod
pods per service
services per database
deployment overlap
```

------------------------------------------------------------------------

## 73. Bound Retries

Recommended properties:

``` text
finite count
exponential backoff
jitter
transient errors only
observability
```

The retry budget must fit inside the application's total request latency
budget.

------------------------------------------------------------------------

## 74. Monitor Client-Side Metrics

Redis server metrics alone are insufficient.

Applications should expose where possible:

``` text
connection attempts
connection failures
pool utilization
pool wait
timeouts
retries
command latency
errors by type
```

This allows teams to distinguish:

``` text
server problem
```

from:

``` text
client problem
```

------------------------------------------------------------------------

## 75. Certificate Monitoring

Track certificate expiration before it becomes an incident.

Monitor:

``` text
server/proxy certificate
client certificates
trusted CA lifecycle
API certificate
```

Alert sufficiently ahead of expiration to allow controlled rotation.

------------------------------------------------------------------------

# Acceptance Lab

## 76. Connectivity Matrix

Complete:

  Test                         Result
  ---------------------------- --------
  DNS resolves                 
  TCP port reachable           
  TLS handshake succeeds       
  Server certificate trusted   
  Hostname validates           
  Authentication succeeds      
  `PING` returns `PONG`        
  Test `SET` succeeds          
  Test `GET` succeeds          
  Python client succeeds       
  Pool configured              
  Connect timeout configured   
  Socket timeout configured    
  Retry policy bounded         

------------------------------------------------------------------------

## 77. Failure Matrix

Record observed behavior:

  Failure                Expected Layer
  ---------------------- --------------------
  Invalid hostname       DNS
  Wrong port             TCP/network
  Wrong CA               TLS
  Expired cert           TLS
  Wrong username         Authentication
  Wrong password         Authentication
  Command denied         Authorization
  Tiny pool exhausted    Application client
  Unreachable endpoint   Network/timeout

The learner should be able to identify the layer from the error without
guessing.

------------------------------------------------------------------------

## 78. Cleanup

Delete only tutorial keys:

``` redis
DEL tutorial:chapter02:connection-test
DEL tutorial:chapter02:python
```

Remove temporary environment variables.

Linux:

``` bash
unset REDISCLI_AUTH
unset REDIS_PASSWORD
```

PowerShell:

``` powershell
Remove-Item Env:REDISCLI_AUTH -ErrorAction SilentlyContinue
Remove-Item Env:REDIS_PASSWORD -ErrorAction SilentlyContinue
```

Do not delete shared certificates or application secrets.

------------------------------------------------------------------------

## 79. Validation Questions

You should be able to answer:

1.  What is the Redis Enterprise database endpoint?
2.  Why should applications avoid connecting directly to a shard?
3.  What does successful DNS resolution prove?
4.  What does successful TCP connectivity prove?
5.  What does `PING` prove?
6.  What is the difference between `redis://` and `rediss://`?
7.  What does a CA certificate validate?
8.  What additional authentication does mTLS provide?
9.  Why is `--insecure` dangerous as a permanent configuration?
10. Why can old pooled connections hide a TLS configuration problem?
11. Why should production applications use connection pools?
12. How do you calculate a connection budget?
13. What is the difference between connect timeout and socket timeout?
14. Why can retries make an incident worse?
15. Why can retrying a timed-out non-idempotent operation be dangerous?
16. How do you distinguish an application client problem from a Redis
    platform problem?
17. Why should client-side connection metrics be monitored?
18. Why must certificate expiration be monitored?

------------------------------------------------------------------------

## 80. Completion Checklist

-   [ ] Database endpoint identified.
-   [ ] DNS verified.
-   [ ] TCP connectivity verified.
-   [ ] `redis-cli` installed/tested.
-   [ ] Authentication tested.
-   [ ] TLS tested where applicable.
-   [ ] Certificate inspected.
-   [ ] `PING` successful.
-   [ ] Test read/write successful.
-   [ ] Python client tested.
-   [ ] Connection pool understood.
-   [ ] Pool capacity calculated.
-   [ ] Connect timeout configured.
-   [ ] Socket timeout configured.
-   [ ] Retry behavior understood.
-   [ ] Retry storm risk understood.
-   [ ] Kubernetes path tested where applicable.
-   [ ] DNS failure reproduced.
-   [ ] Wrong-port failure reproduced.
-   [ ] Authentication failure reproduced.
-   [ ] TLS trust failure reproduced where applicable.
-   [ ] Connection troubleshooting runbook understood.
-   [ ] Tutorial keys cleaned up.

------------------------------------------------------------------------

## 81. Key Takeaways

1.  Redis connectivity is a multi-layer path, not a single Redis check.
2.  Always start with the database endpoint and correct port.
3.  Test DNS, TCP, TLS, authentication, and Redis separately.
4.  `redis-cli` is essential for separating application failures from
    platform failures.
5.  Production TLS should validate certificates rather than disable
    verification.
6.  mTLS authenticates the client as well as the server.
7.  Connection pooling improves efficiency but must be bounded.
8.  Timeouts should match application latency objectives.
9.  Retries require limits, backoff, and jitter.
10. A timeout does not prove a command was never executed.
11. Kubernetes DNS and network policy can break Redis connectivity while
    Redis remains healthy.
12. Client-side telemetry is as important as Redis server telemetry
    during connection incidents.

------------------------------------------------------------------------

## 82. References

-   Redis Software --- Connect to a database
-   Redis Software --- `redis-cli`
-   Redis Software --- TLS and certificate configuration
-   Redis Software --- Certificate-based authentication
-   Redis Software --- Connectivity troubleshooting
-   Redis client production usage guidance

Validate commands against the Redis Software and client-library version
deployed in your environment before production use.

------------------------------------------------------------------------

## Next Chapter

**Chapter 03 --- Redis Data Types, Key Design & Memory-Aware Data
Modeling**

Chapter 03 will cover:

-   strings
-   hashes
-   lists
-   sets
-   sorted sets
-   streams overview
-   key naming
-   TTL design
-   memory implications
-   large keys
-   hot keys
-   object inspection
-   keyspace analysis
-   hands-on modeling lab
-   production design review
