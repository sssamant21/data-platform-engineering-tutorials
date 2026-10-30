# Chapter 04 --- Redis Commands, Command Semantics & Safe Operations

**Status:** Canonical\
**Track:** Redis Enterprise / Redis Software Production Engineering\
**Level:** Foundation → Production Operations\
**Audience:** Developers, SREs, DBREs, Platform Engineers, Redis
Administrators\
**Lab type:** Command semantics, atomic operations, expiration behavior,
safe deletion, command-risk analysis, failure injection,
troubleshooting, and operational acceptance

------------------------------------------------------------------------

## 1. Objective

Redis commands are simple to execute, but production safety depends on
understanding what each command actually does.

A command that is harmless against ten keys can become disruptive
against millions of keys. A write that appears correct can accidentally
remove a TTL. A multi-key command can create unexpected latency. A
deletion strategy can create CPU stalls. A blocking command can consume
client connections. An administrative command can have database-wide
impact.

This chapter teaches command behavior from an application and SRE
perspective.

By the end, you should be able to:

-   Classify common Redis commands by purpose.
-   Understand command semantics before using a command in production.
-   Interpret command time-complexity guidance.
-   Distinguish atomic commands from multi-step application workflows.
-   Use conditional `SET` operations.
-   Understand `NX`, `XX`, `EX`, `PX`, and related options.
-   Understand how writes can affect TTL state.
-   Use expiration commands deliberately.
-   Compare `DEL` and `UNLINK`.
-   Use `EXISTS`, `TYPE`, `TTL`, and `MEMORY USAGE` before destructive
    operations.
-   Understand risks associated with large multi-key operations.
-   Avoid routine production use of broad synchronous keyspace commands.
-   Use `SCAN` for incremental keyspace iteration.
-   Recognize blocking-command risks.
-   Recognize expensive collection commands.
-   Understand why command complexity depends on both the command and
    the size of the data structure.
-   Design safe application retries around command semantics.
-   Troubleshoot command failures systematically.
-   Apply a production command-safety review.

------------------------------------------------------------------------

# Part 1 --- Command Mental Model

## 2. Redis Commands Operate on Data Structures

Redis commands are not generic SQL-like operations.

Commands normally target specific Redis data types.

Examples:

``` text
GET / SET          -> String
HGET / HSET        -> Hash
LPUSH / LRANGE     -> List
SADD / SISMEMBER   -> Set
ZADD / ZRANGE      -> Sorted Set
XADD / XREAD       -> Stream
```

A command that expects one type cannot normally operate on another.

Example:

``` redis
HSET tutorial:chapter04:user name Alice
GET tutorial:chapter04:user
```

The second command returns:

``` text
WRONGTYPE
```

The command is valid.

The key type is incompatible.

------------------------------------------------------------------------

## 3. Command Categories

Operationally, it is useful to group commands into categories.

### Read commands

Examples:

``` text
GET
MGET
HGET
HMGET
LRANGE
SISMEMBER
ZRANGE
XRANGE
```

### Write commands

Examples:

``` text
SET
MSET
HSET
LPUSH
SADD
ZADD
XADD
```

### Keyspace commands

Examples:

``` text
EXISTS
TYPE
TTL
EXPIRE
DEL
UNLINK
SCAN
```

### Diagnostic commands

Examples:

``` text
INFO
MEMORY USAGE
OBJECT ENCODING
SLOWLOG
CLIENT
```

Availability can depend on permissions and platform policy.

### Administrative commands

Redis Enterprise environments can restrict commands that would conflict
with platform management or create unsafe database-wide effects.

Do not assume every command available in standalone Redis is appropriate
or permitted in Redis Enterprise.

------------------------------------------------------------------------

# Part 2 --- Command Semantics

## 4. Read the Semantics, Not Just the Command Name

Consider:

``` redis
SET cache:key new-value
```

This looks simple.

But operational questions include:

``` text
Did the key already exist?
Did it have a TTL?
Should the write happen only if absent?
Should the write happen only if present?
Should the new value expire?
Could the client retry this operation?
```

Production correctness comes from these details.

------------------------------------------------------------------------

## 5. Basic `SET`

Create:

``` redis
SET tutorial:chapter04:greeting "hello"
```

Expected:

``` text
OK
```

Read:

``` redis
GET tutorial:chapter04:greeting
```

Expected:

``` text
hello
```

------------------------------------------------------------------------

## 6. `SET` With Expiration

Create a key that expires in 300 seconds:

``` redis
SET tutorial:chapter04:session "active" EX 300
```

Verify:

``` redis
TTL tutorial:chapter04:session
```

This is preferable to:

``` redis
SET key value
EXPIRE key 300
```

when application correctness requires the value and TTL to be
established as one operation.

The two-command version creates an intermediate state where the key
exists without the intended expiration.

------------------------------------------------------------------------

## 7. Millisecond Expiration

Use:

``` redis
SET tutorial:chapter04:short-lived "value" PX 5000
```

Check:

``` redis
PTTL tutorial:chapter04:short-lived
```

`PX` specifies milliseconds.

`EX` specifies seconds.

Choose based on application semantics rather than convenience.

------------------------------------------------------------------------

# Part 3 --- Conditional Writes

## 8. `SET NX`

`NX` means:

``` text
set only if the key does not exist
```

Example:

``` redis
SET tutorial:chapter04:lock owner-a NX EX 30
```

If the key does not exist:

``` text
OK
```

A second attempt:

``` redis
SET tutorial:chapter04:lock owner-b NX EX 30
```

does not replace the existing value.

This is useful for conditional creation patterns.

Distributed locking itself requires deeper design than simply copying
one command; ownership, expiration, failure modes, and safe release must
all be considered.

------------------------------------------------------------------------

## 9. `SET XX`

`XX` means:

``` text
set only if the key already exists
```

Example:

``` redis
SET tutorial:chapter04:profile:v1 "old" EX 300
SET tutorial:chapter04:profile:v1 "new" XX EX 300
GET tutorial:chapter04:profile:v1
```

Expected:

``` text
new
```

Against a missing key:

``` redis
SET tutorial:chapter04:missing "value" XX
```

the value is not created.

------------------------------------------------------------------------

## 10. Conditional Writes Reduce Race Windows

Application pattern:

``` text
GET key
if missing:
    SET key
```

contains a race window between commands.

When Redis provides the needed condition directly:

``` redis
SET key value NX
```

the condition and write occur as one Redis command.

General principle:

> Prefer native atomic command semantics over client-side
> read-check-write sequences when Redis provides the required operation.

------------------------------------------------------------------------

# Part 4 --- Atomic Operations

## 11. Single Redis Commands

Individual Redis commands execute atomically with respect to other
commands.

Example:

``` redis
INCR tutorial:chapter04:counter
```

Multiple clients can increment the same counter without implementing a
client-side:

``` text
GET
+1
SET
```

sequence.

------------------------------------------------------------------------

## 12. Unsafe Read-Modify-Write

Consider two clients.

Both execute:

``` redis
GET counter
```

Both receive:

``` text
10
```

Both calculate:

``` text
11
```

Both execute:

``` redis
SET counter 11
```

One increment is lost.

Use:

``` redis
INCR counter
```

when the desired operation matches Redis semantics.

------------------------------------------------------------------------

## 13. Hash Atomic Updates

Increment a hash field:

``` redis
HSET tutorial:chapter04:metrics requests 0
HINCRBY tutorial:chapter04:metrics requests 1
```

This avoids application-side:

``` text
HGET
calculate
HSET
```

for simple counters.

------------------------------------------------------------------------

## 14. Transactions and Scripts

Redis also supports mechanisms such as:

``` text
MULTI / EXEC
WATCH
Lua/server-side programmability
```

These are covered in a later dedicated chapter.

Do not use a transaction simply because several commands appear next to
each other in application code.

First ask whether Redis already provides one command that expresses the
operation.

------------------------------------------------------------------------

# Part 5 --- TTL Semantics

## 15. Inspect Expiration

Seconds:

``` redis
TTL key
```

Milliseconds:

``` redis
PTTL key
```

Typical results:

``` text
positive value -> expiration remaining
-1             -> key exists without expiration
-2             -> key does not exist
```

------------------------------------------------------------------------

## 16. Apply Expiration

``` redis
EXPIRE tutorial:chapter04:cache 300
```

Milliseconds:

``` redis
PEXPIRE tutorial:chapter04:cache 300000
```

Absolute expiration commands also exist.

Use the semantic form that makes application intent clear.

------------------------------------------------------------------------

## 17. Remove Expiration

``` redis
PERSIST tutorial:chapter04:cache
```

After:

``` redis
TTL tutorial:chapter04:cache
```

expected:

``` text
-1
```

This is useful when intentional.

It is dangerous when accidental.

------------------------------------------------------------------------

## 18. Replacement and TTL

Create:

``` redis
SET tutorial:chapter04:ttl-test "v1" EX 300
```

Verify:

``` redis
TTL tutorial:chapter04:ttl-test
```

Then replace:

``` redis
SET tutorial:chapter04:ttl-test "v2"
```

Check again:

``` redis
TTL tutorial:chapter04:ttl-test
```

A normal replacement `SET` does not automatically preserve the previous
TTL.

This is a common cache bug.

Applications should intentionally define expiration behavior when
replacing cached values.

------------------------------------------------------------------------

## 19. Preserve TTL When Appropriate

Redis versions supporting the option can use:

``` redis
SET tutorial:chapter04:ttl-test "v3" KEEPTTL
```

Do not assume every client library exposes every option identically.

Validate against the deployed Redis version and client library.

------------------------------------------------------------------------

# Part 6 --- Existence and Inspection

## 20. `EXISTS`

``` redis
EXISTS tutorial:chapter04:greeting
```

Result:

``` text
1
```

Missing:

``` redis
EXISTS tutorial:chapter04:does-not-exist
```

Result:

``` text
0
```

For multiple keys, the result represents how many supplied keys exist.

------------------------------------------------------------------------

## 21. `TYPE`

Before troubleshooting or performing a type-specific operation:

``` redis
TYPE <key>
```

This is one of the safest and most useful diagnostic commands.

------------------------------------------------------------------------

## 22. `MEMORY USAGE`

Before deleting or investigating a suspicious key:

``` redis
MEMORY USAGE <key>
```

Combine with:

``` text
TYPE
TTL
type-specific cardinality
```

to understand the object.

------------------------------------------------------------------------

# Part 7 --- Delete Semantics

## 23. `DEL`

Delete:

``` redis
DEL tutorial:chapter04:temporary
```

`DEL` removes keys synchronously.

For small keys this is normally straightforward.

For very large complex values, synchronous reclamation can create more
work in the command path.

------------------------------------------------------------------------

## 24. `UNLINK`

`UNLINK` removes the key from the keyspace and allows memory reclamation
to occur asynchronously.

Example:

``` redis
UNLINK tutorial:chapter04:large-test-key
```

For large objects, `UNLINK` can reduce the latency impact associated
with synchronous deletion.

This does not mean:

``` text
always replace DEL with UNLINK
```

Understand:

``` text
key size
data type
memory pressure
operational objective
Redis version/platform behavior
```

------------------------------------------------------------------------

## 25. Safe Production Deletion Workflow

Before deleting an unfamiliar production key:

``` text
1. Identify owner.
2. Verify database/environment.
3. TYPE key.
4. TTL key.
5. MEMORY USAGE key.
6. Check type-specific size/cardinality.
7. Determine whether application can recreate it.
8. Determine whether it is source-of-truth data.
9. Select DEL or UNLINK deliberately.
10. Observe application and database after deletion.
```

Never make:

``` redis
DEL <unknown-production-key>
```

your first troubleshooting step.

------------------------------------------------------------------------

# Part 8 --- Multi-Key Commands

## 26. `MGET`

Example:

``` redis
MGET key1 key2 key3
```

This can reduce network round trips.

But a request for an extremely large number of keys can create:

``` text
large request
large response
CPU work
network pressure
latency
```

Batch intentionally.

------------------------------------------------------------------------

## 27. `MSET`

Example:

``` redis
MSET \
  tutorial:chapter04:a 1 \
  tutorial:chapter04:b 2 \
  tutorial:chapter04:c 3
```

Useful for multiple string writes.

But note:

``` text
MSET does not express per-key TTLs in the same command
```

If TTL is required, design the workflow carefully.

------------------------------------------------------------------------

## 28. Multi-Key Operations and Clustered Data

In distributed/sharded Redis environments, multi-key command behavior
can depend on key placement, command capabilities, and product
implementation.

Do not design a critical application workflow around an assumed
cross-shard behavior without validating it against:

``` text
your Redis Enterprise version
your database configuration
your client
the exact command
```

Later chapters cover hash slots and sharding in depth.

------------------------------------------------------------------------

# Part 9 --- Command Complexity

## 29. Big-O Is Operationally Important

Redis command documentation provides time-complexity information.

Examples conceptually include:

``` text
O(1)
O(N)
O(log N)
O(N + M)
```

The important lesson is not memorizing every complexity.

The lesson is:

> Command cost can grow with key size, collection cardinality, number of
> requested elements, or number of supplied keys.

------------------------------------------------------------------------

## 30. `GET` vs Large Response

Even when command lookup behavior is efficient, returning a very large
value still creates:

``` text
memory copying
network transfer
client deserialization
application latency
```

Therefore:

``` text
fast algorithmic lookup
```

does not mean:

``` text
unlimited payload is safe
```

------------------------------------------------------------------------

## 31. Range Commands

Consider:

``` redis
LRANGE mylist 0 -1
```

Against:

``` text
20 elements
```

this may be trivial.

Against:

``` text
5,000,000 elements
```

it can be a very different operation.

The same applies conceptually to commands that retrieve entire:

``` text
hashes
sets
sorted sets
streams
```

------------------------------------------------------------------------

# Part 10 --- Expensive Collection Patterns

## 32. Avoid Full-Collection Retrieval by Default

Potentially dangerous at large cardinality:

``` redis
HGETALL huge-hash
SMEMBERS huge-set
LRANGE huge-list 0 -1
ZRANGE huge-zset 0 -1
XRANGE huge-stream - +
```

These commands are not inherently bad.

Their risk depends on object size and requested range.

Use bounded queries or incremental iteration when appropriate.

------------------------------------------------------------------------

## 33. Incremental Iteration

Keyspace:

``` redis
SCAN
```

Hash:

``` redis
HSCAN
```

Set:

``` redis
SSCAN
```

Sorted set:

``` redis
ZSCAN
```

These support incremental iteration.

Example:

``` redis
HSCAN application:large-hash 0 COUNT 100
```

Remember:

``` text
COUNT is a hint
```

not a strict page-size guarantee.

------------------------------------------------------------------------

# Part 11 --- `KEYS` and Production Safety

## 34. `KEYS`

Example:

``` redis
KEYS 'tutorial:*'
```

It may be convenient in a tiny test database.

It should not become a routine production inventory pattern on large
keyspaces.

Prefer:

``` redis
SCAN 0 MATCH 'tutorial:*' COUNT 100
```

and iterate cursors.

------------------------------------------------------------------------

## 35. Why `SCAN` Is Operationally Different

`SCAN` incrementally traverses the keyspace.

It does not require returning the entire matching keyspace in one
operation.

Applications using `SCAN` must handle:

``` text
cursor iteration
changing keyspace
possible repeated elements
COUNT as a hint
```

Use it as an iteration primitive, not as a transactional snapshot.

------------------------------------------------------------------------

# Part 12 --- Blocking Commands

## 36. Blocking Operations

Redis supports commands that can wait for data.

Examples in relevant data structures include blocking list/stream
patterns.

Blocking can be useful.

But application design must consider:

``` text
connection consumption
client pool size
timeouts
shutdown behavior
failover behavior
retry behavior
```

A connection waiting in a blocking operation is not freely available to
unrelated application work.

------------------------------------------------------------------------

## 37. Separate Workloads When Appropriate

A service may use:

``` text
regular cache commands
+
long-lived blocking consumers
```

Using one tiny connection pool for both can cause pool starvation.

Design connection pools based on workload semantics.

------------------------------------------------------------------------

# Part 13 --- Retries and Idempotency

## 38. A Timeout Does Not Always Mean the Command Failed

Suppose an application sends:

``` redis
INCR payment:attempts
```

Then the network fails before the client receives the response.

The client may not know whether Redis executed the command.

Blind retry could increment twice.

This is an ambiguous outcome.

------------------------------------------------------------------------

## 39. Retry Safety Depends on the Operation

Often naturally idempotent:

``` redis
SET key exact-value
```

Potentially non-idempotent:

``` redis
INCR key
LPUSH key value
XADD key '*' ...
```

This does not mean never retry them.

It means retry behavior must account for operation semantics and
application correctness.

------------------------------------------------------------------------

## 40. Incident Question

When an application reports:

``` text
Redis timeout
```

do not immediately assume:

``` text
Redis rejected the write
```

Ask:

``` text
Did the server receive it?
Did it execute?
Did only the response fail?
Did the client retry?
Could the retry duplicate the operation?
```

This distinction is critical for counters, queues, events, and business
operations.

------------------------------------------------------------------------

# Part 14 --- Administrative Safety

## 41. Destructive Commands

Commands with broad destructive impact must not be casually used.

Examples conceptually include database-wide clearing operations.

For tutorials and normal troubleshooting:

``` text
do not use FLUSHDB
do not use FLUSHALL
```

Delete only isolated lab keys.

------------------------------------------------------------------------

## 42. Production Command Approval

High-impact operations should have:

``` text
change context
target database
exact command
expected impact
rollback/recovery plan
monitoring
owner
maintenance window when required
```

A technically valid command can still be operationally unsafe.

------------------------------------------------------------------------

# Hands-On Lab

## 43. Lab Safety

Use:

``` text
development
test
staging
training database
```

All keys use:

``` text
tutorial:chapter04:
```

Do not run destructive database-wide commands.

------------------------------------------------------------------------

## 44. Lab 1 --- Basic Commands

``` redis
SET tutorial:chapter04:basic "hello"
GET tutorial:chapter04:basic
EXISTS tutorial:chapter04:basic
TYPE tutorial:chapter04:basic
```

Expected:

``` text
OK
hello
1
string
```

------------------------------------------------------------------------

## 45. Lab 2 --- Atomic TTL Creation

``` redis
SET tutorial:chapter04:cache "payload" EX 300
TTL tutorial:chapter04:cache
```

Expected TTL:

``` text
> 0
```

------------------------------------------------------------------------

## 46. Lab 3 --- Conditional Create

``` redis
DEL tutorial:chapter04:nx-test
SET tutorial:chapter04:nx-test "first" NX EX 300
SET tutorial:chapter04:nx-test "second" NX EX 300
GET tutorial:chapter04:nx-test
```

**Expected per-command results:** The initial scoped `DEL` returns 0 or 1 depending on whether the disposable key existed. The first conditional `SET ... NX` returns `OK`; the second returns **nil/null** because the key is already present, and it does not replace the original value. Do not confuse a conditional `SET` null reply with a network failure.

Expected final value:

``` text
first
```

------------------------------------------------------------------------

## 47. Lab 4 --- Conditional Update

``` redis
SET tutorial:chapter04:xx-test "v1" EX 300
SET tutorial:chapter04:xx-test "v2" XX EX 300
GET tutorial:chapter04:xx-test
```

Expected:

``` text
v2
```

Then:

``` redis
SET tutorial:chapter04:missing-xx "value" XX
EXISTS tutorial:chapter04:missing-xx
```

**Expected per-command results:** A conditional `SET ... XX` against a missing key returns **nil/null** (not `OK`) because no update occurred. `EXISTS` must return integer 0.

Expected:

``` text
0
```

------------------------------------------------------------------------

## 48. Lab 5 --- Atomic Counter

``` redis
SET tutorial:chapter04:counter 0 EX 300
INCR tutorial:chapter04:counter
INCR tutorial:chapter04:counter
INCRBY tutorial:chapter04:counter 8
GET tutorial:chapter04:counter
```

Expected:

``` text
10
```

------------------------------------------------------------------------

## 49. Lab 6 --- TTL Replacement Behavior

``` redis
SET tutorial:chapter04:ttl-replace "v1" EX 300
TTL tutorial:chapter04:ttl-replace
```

Now:

``` redis
SET tutorial:chapter04:ttl-replace "v2"
TTL tutorial:chapter04:ttl-replace
```

Observe the TTL result.

This lab demonstrates why application cache updates must define TTL
behavior explicitly.

Restore expiration:

``` redis
EXPIRE tutorial:chapter04:ttl-replace 300
```

------------------------------------------------------------------------

## 50. Lab 7 --- `PERSIST`

``` redis
SET tutorial:chapter04:persist-test "value" EX 300
TTL tutorial:chapter04:persist-test
PERSIST tutorial:chapter04:persist-test
TTL tutorial:chapter04:persist-test
```

Expected final TTL:

``` text
-1
```

Restore:

``` redis
EXPIRE tutorial:chapter04:persist-test 300
```

------------------------------------------------------------------------

## 51. Lab 8 --- Multi-Key Read

``` redis
MSET \
  tutorial:chapter04:m1 one \
  tutorial:chapter04:m2 two \
  tutorial:chapter04:m3 three
```

Read:

``` redis
MGET \
  tutorial:chapter04:m1 \
  tutorial:chapter04:m2 \
  tutorial:chapter04:m3
```

Expected:

``` text
one
two
three
```

Apply lab TTLs:

``` redis
EXPIRE tutorial:chapter04:m1 300
EXPIRE tutorial:chapter04:m2 300
EXPIRE tutorial:chapter04:m3 300
```

Notice that `MSET` itself did not establish these per-key TTLs.

------------------------------------------------------------------------

## 52. Lab 9 --- Type Failure

``` redis
HSET tutorial:chapter04:user name Alice status active
GET tutorial:chapter04:user
```

Expected:

``` text
WRONGTYPE
```

Diagnose:

``` redis
TYPE tutorial:chapter04:user
HGETALL tutorial:chapter04:user
```

Apply:

``` redis
EXPIRE tutorial:chapter04:user 300
```

------------------------------------------------------------------------

## 53. Lab 10 --- Safe Key Inspection

``` redis
TYPE tutorial:chapter04:user
TTL tutorial:chapter04:user
MEMORY USAGE tutorial:chapter04:user
HLEN tutorial:chapter04:user
```

Record:

``` text
Type:
TTL:
Memory:
Fields:
```

------------------------------------------------------------------------

## 54. Lab 11 --- `DEL`

Create:

``` redis
SET tutorial:chapter04:delete-me "small-value"
```

Delete:

``` redis
DEL tutorial:chapter04:delete-me
```

Verify:

``` redis
EXISTS tutorial:chapter04:delete-me
```

Expected:

``` text
0
```

------------------------------------------------------------------------

## 55. Lab 12 --- `UNLINK`

Create:

``` redis
SET tutorial:chapter04:unlink-me "small-training-value"
```

Run:

``` redis
UNLINK tutorial:chapter04:unlink-me
```

Verify:

``` redis
EXISTS tutorial:chapter04:unlink-me
```

Expected:

``` text
0
```

This tiny key does not demonstrate performance improvement.

The lab demonstrates command semantics safely.

------------------------------------------------------------------------

## 56. Lab 13 --- Bounded Collection Retrieval

Create:

``` redis
RPUSH tutorial:chapter04:list a b c d e f g h i j
EXPIRE tutorial:chapter04:list 300
```

Instead of:

``` redis
LRANGE tutorial:chapter04:list 0 -1
```

pretend the collection is huge and retrieve a bounded range:

``` redis
LRANGE tutorial:chapter04:list 0 4
```

Then:

``` redis
LLEN tutorial:chapter04:list
```

Operational lesson:

> The requested result size matters.

------------------------------------------------------------------------

## 57. Lab 14 --- Incremental Keyspace Scan

``` redis
SCAN 0 MATCH 'tutorial:chapter04:*' COUNT 10
```

If returned cursor is not zero:

``` redis
SCAN <cursor> MATCH 'tutorial:chapter04:*' COUNT 10
```

Continue until:

``` text
cursor = 0
```

------------------------------------------------------------------------

## 58. Lab 15 --- Hash Scan

Create:

``` redis
HSET tutorial:chapter04:inventory \
  product:1001 10 \
  product:1002 20 \
  product:1003 30 \
  product:1004 40 \
  product:1005 50
```

Then:

``` redis
HSCAN tutorial:chapter04:inventory 0 COUNT 2
```

Continue using returned cursors.

Apply:

``` redis
EXPIRE tutorial:chapter04:inventory 300
```

------------------------------------------------------------------------

# Failure Injection

## 59. Failure 1 --- `WRONGTYPE`

Already created:

``` redis
GET tutorial:chapter04:user
```

Expected:

``` text
WRONGTYPE
```

Diagnosis:

``` redis
TYPE tutorial:chapter04:user
```

Lesson:

``` text
command validity != data-type compatibility
```

------------------------------------------------------------------------

## 60. Failure 2 --- Lost TTL

Create:

``` redis
SET tutorial:chapter04:lost-ttl "v1" EX 300
```

Verify:

``` redis
TTL tutorial:chapter04:lost-ttl
```

Replace:

``` redis
SET tutorial:chapter04:lost-ttl "v2"
```

Verify:

``` redis
TTL tutorial:chapter04:lost-ttl
```

Correct:

``` redis
EXPIRE tutorial:chapter04:lost-ttl 300
```

Lesson:

> Cache-update code must test expiration behavior.

------------------------------------------------------------------------

## 61. Failure 3 --- Conditional Write Rejected

``` redis
SET tutorial:chapter04:condition "existing" EX 300
SET tutorial:chapter04:condition "replacement" NX EX 300
GET tutorial:chapter04:condition
```

Expected:

``` text
existing
```

This is not a Redis failure.

The condition was not satisfied.

Application code must distinguish:

``` text
command error
```

from:

``` text
conditional no-op
```

------------------------------------------------------------------------

## 62. Failure 4 --- Oversized Result Design

Do not create a million-element list.

Review this proposed command:

``` redis
LRANGE production:events 0 -1
```

Assume:

``` text
LLEN = 5,000,000
```

Ask:

``` text
How large is the response?
Does the caller need every item?
Can pagination/bounded retrieval be used?
Should this data structure be redesigned?
```

Safe failure injection can be analytical rather than destructive.

------------------------------------------------------------------------

## 63. Failure 5 --- Retry Ambiguity

Conceptual exercise:

Client sends:

``` redis
INCR tutorial:chapter04:billing-attempts
```

Connection drops before response.

Questions:

``` text
Did Redis execute INCR?
Can client know?
What happens if application retries?
Can the business operation tolerate duplicate increment?
```

This exercise teaches why retry policies cannot be designed only from
network-error types.

------------------------------------------------------------------------

# Troubleshooting

## 64. Command Returns `WRONGTYPE`

Check:

``` redis
TYPE <key>
```

Then:

``` text
compare expected schema
check key namespace
check recent deployment
check old cache versions
check TTL
identify writer
```

Do not blindly delete the key.

------------------------------------------------------------------------

## 65. `SET NX` Does Nothing

Check:

``` redis
EXISTS <key>
GET <key>
TTL <key>
```

Potential explanation:

``` text
key already exists
```

For lock-like patterns, also investigate:

``` text
owner
expiration
safe release semantics
client failure
```

------------------------------------------------------------------------

## 66. Key No Longer Expires

Check:

``` redis
TTL <key>
```

If:

``` text
-1
```

investigate:

``` text
replacement SET
PERSIST
application deployment
manual operation
incorrect write path
```

------------------------------------------------------------------------

## 67. Command Latency Suddenly High

Investigate:

``` text
command type
key size
collection cardinality
requested range
response size
CPU
network
slowlog
hot key
client behavior
concurrent workload
```

Do not conclude:

``` text
Redis is slow
```

without identifying the command and object involved.

------------------------------------------------------------------------

## 68. Delete Causes Latency

Investigate:

``` text
DEL or UNLINK?
key type?
key memory?
collection cardinality?
frequency of deletion?
CPU pressure?
memory pressure?
```

Large-object lifecycle should be part of application design.

------------------------------------------------------------------------

## 69. Application Pool Exhausted

Check whether the application uses:

``` text
blocking consumers
long commands
large responses
slow network
too-small pool
connection leaks
```

Separate long-lived blocking workloads from normal request/response
traffic where appropriate.

------------------------------------------------------------------------

# Production Command-Safety Framework

## 70. Before Running a Production Command

Ask:

``` text
What database?
What environment?
What key or pattern?
Read or write?
What data type?
How large is the key?
How many keys?
What is command complexity?
How large can the response be?
Can it block?
Can it delete data?
Can it change TTL?
Can it affect every key?
Can it be safely retried?
What happens if connection fails mid-operation?
```

------------------------------------------------------------------------

## 71. Risk Classes

A practical operational classification:

### Low-risk diagnostic

Examples:

``` text
TYPE specific-key
TTL specific-key
EXISTS specific-key
```

### Bounded diagnostic

Examples:

``` text
MEMORY USAGE specific-key
HLEN specific-key
SCAN with controlled pattern/count
```

### Application write

Examples:

``` text
SET
HSET
INCR
EXPIRE
```

Requires ownership and semantic understanding.

### Potentially expensive

Examples:

``` text
full large collection retrieval
large multi-key operation
large synchronous deletion
```

### High-impact administrative/destructive

Database-wide or cluster-impacting operations require explicit
operational controls.

------------------------------------------------------------------------

# Runbooks

## 72. Runbook --- Unexpected Redis Command Latency

``` text
1. Capture timestamp and affected service.
2. Identify exact Redis command.
3. Identify database and endpoint.
4. Identify key or key pattern if safe.
5. Determine key type.
6. Determine key size/cardinality.
7. Determine response size.
8. Check database/shard CPU.
9. Check memory pressure.
10. Check connection/client metrics.
11. Check slow-command evidence.
12. Check hot-key/skew indicators.
13. Check recent deployment/workload changes.
14. Reproduce only in a safe environment when possible.
15. Remediate command/data model rather than only scaling infrastructure.
16. Validate latency after remediation.
```

------------------------------------------------------------------------

## 73. Runbook --- Accidental Persistent Cache Key

``` text
1. Confirm key should be cache data.
2. Run TTL.
3. Confirm result is -1.
4. Identify writer/application owner.
5. Determine expected TTL.
6. Check whether SET replacement removed TTL.
7. Check recent deployment.
8. Apply expiration only after confirming intended lifecycle.
9. Fix application write semantics.
10. Search safely for similar affected namespace keys.
11. Monitor memory trend.
```

------------------------------------------------------------------------

## 74. Runbook --- Production Key Deletion

``` text
1. Confirm exact environment.
2. Confirm exact database.
3. Confirm exact key.
4. Identify application/data owner.
5. TYPE key.
6. TTL key.
7. MEMORY USAGE key.
8. Check type-specific size/cardinality.
9. Confirm whether key is cache or source-of-truth data.
10. Confirm application recreation behavior.
11. Determine DEL vs UNLINK.
12. Obtain required change/incident approval.
13. Execute exact-key operation.
14. Verify key state.
15. Observe application.
16. Observe Redis latency/CPU/memory.
17. Record operation in incident/change notes.
```

------------------------------------------------------------------------

## 75. Runbook --- Retry-Related Duplicate Operation

``` text
1. Capture client timeout/error.
2. Identify exact command.
3. Determine whether command is idempotent.
4. Determine whether Redis may have executed it.
5. Review client retry policy.
6. Check application/business identifier.
7. Check for duplicate counter/event/list/stream effects.
8. Stop uncontrolled retries if causing amplification.
9. Correct application idempotency strategy.
10. Validate under injected network failure in non-production.
```

------------------------------------------------------------------------

# Lab Cleanup

## 76. Delete Only Tutorial Keys

Known lab keys include:

``` redis
UNLINK tutorial:chapter04:basic
UNLINK tutorial:chapter04:cache
UNLINK tutorial:chapter04:nx-test
UNLINK tutorial:chapter04:xx-test
UNLINK tutorial:chapter04:counter
UNLINK tutorial:chapter04:ttl-replace
UNLINK tutorial:chapter04:persist-test
UNLINK tutorial:chapter04:m1
UNLINK tutorial:chapter04:m2
UNLINK tutorial:chapter04:m3
UNLINK tutorial:chapter04:user
UNLINK tutorial:chapter04:list
UNLINK tutorial:chapter04:inventory
UNLINK tutorial:chapter04:lost-ttl
UNLINK tutorial:chapter04:condition
UNLINK tutorial:chapter04:billing-attempts
```

Verify:

``` redis
SCAN 0 MATCH 'tutorial:chapter04:*' COUNT 100
```

Never use:

``` redis
FLUSHDB
FLUSHALL
```

for tutorial cleanup.

------------------------------------------------------------------------

# Validation

## 77. Knowledge Questions

You should be able to answer:

1.  Why is command semantics more important than memorizing syntax?
2.  What does `SET NX` do?
3.  What does `SET XX` do?
4.  Why can `SET key value EX 300` be safer than separate `SET` and
    `EXPIRE` operations?
5.  Why is `INCR` preferable to a client-side GET/increment/SET
    sequence?
6.  What does `TTL = -1` mean?
7.  What does `TTL = -2` mean?
8.  How can a replacement `SET` affect an existing TTL?
9.  What is `PERSIST` used for?
10. What is the operational difference between `DEL` and `UNLINK`?
11. Why should key size be inspected before deleting an unfamiliar
    production key?
12. Why can `MGET` become expensive even though it reduces round trips?
13. Why does result size matter even for efficient Redis commands?
14. Why can `HGETALL` be dangerous on a huge hash?
15. Why is `SCAN` preferable to routine `KEYS *` use on large production
    keyspaces?
16. Is `COUNT` an exact page size for `SCAN`?
17. Why can blocking commands exhaust a connection pool?
18. Why can a Redis timeout create an ambiguous write outcome?
19. Which operations are naturally more retry-safe: exact-value `SET` or
    `INCR`?
20. Why should administrative commands have change controls?
21. What information should be captured before production deletion?
22. Why can application command design matter more than adding Redis
    capacity?

------------------------------------------------------------------------

## 78. Hands-On Acceptance Checklist

-   [ ] Executed basic `SET` and `GET`.
-   [ ] Used `EXISTS`.
-   [ ] Used `TYPE`.
-   [ ] Created a key atomically with TTL.
-   [ ] Used `SET NX`.
-   [ ] Used `SET XX`.
-   [ ] Used atomic `INCR`.
-   [ ] Demonstrated TTL loss on replacement.
-   [ ] Restored expiration intentionally.
-   [ ] Used `PERSIST`.
-   [ ] Used `MSET`.
-   [ ] Used `MGET`.
-   [ ] Reproduced `WRONGTYPE`.
-   [ ] Diagnosed type with `TYPE`.
-   [ ] Used `MEMORY USAGE`.
-   [ ] Used `DEL`.
-   [ ] Used `UNLINK`.
-   [ ] Retrieved a bounded List range.
-   [ ] Iterated with `SCAN`.
-   [ ] Iterated a Hash with `HSCAN`.
-   [ ] Analyzed retry ambiguity.
-   [ ] Cleaned up only tutorial keys.

------------------------------------------------------------------------

## 79. Production Acceptance Checklist

Before approving application Redis commands:

-   [ ] Command inventory documented.
-   [ ] Data types documented.
-   [ ] Command complexity reviewed.
-   [ ] Maximum object size considered.
-   [ ] Maximum collection cardinality considered.
-   [ ] Maximum response size considered.
-   [ ] TTL semantics tested.
-   [ ] Replacement-write TTL behavior tested.
-   [ ] Conditional writes used where appropriate.
-   [ ] Atomic native operations used where appropriate.
-   [ ] Retry behavior documented.
-   [ ] Non-idempotent retry risks reviewed.
-   [ ] Multi-key behavior tested against target Redis Enterprise
    deployment.
-   [ ] Large deletion strategy reviewed.
-   [ ] Blocking command connection usage reviewed.
-   [ ] Broad keyspace operations avoided.
-   [ ] Administrative/destructive commands controlled.
-   [ ] Production runbooks documented.
-   [ ] Client metrics and Redis observability available.

------------------------------------------------------------------------

# 80. Key Takeaways

1.  A Redis command can be syntactically valid and still be
    operationally unsafe.
2.  Native atomic commands reduce client-side race conditions.
3.  Conditional `SET` options are important application primitives.
4.  TTL semantics must be tested as part of write behavior.
5.  Replacing a key can change its expiration behavior.
6.  `DEL` and `UNLINK` have different memory-reclamation behavior.
7.  Command cost depends on both command complexity and data size.
8.  Large responses can create latency even when lookup itself is
    efficient.
9.  Avoid retrieving entire unbounded collections by default.
10. Use incremental scanning for large keyspaces and collections where
    appropriate.
11. Blocking operations consume connection resources.
12. Timeouts can create ambiguous outcomes for writes.
13. Retry safety depends on command semantics.
14. Production deletion should begin with inspection, ownership, and
    impact analysis.
15. Application command design is a core part of Redis performance
    engineering.

------------------------------------------------------------------------

## 81. References

Validate production behavior against documentation for the Redis version
and Redis Enterprise / Redis Software release you operate.

Key documentation areas:

-   Redis command reference
-   `SET`
-   expiration commands
-   `INCR`
-   `DEL`
-   `UNLINK`
-   `SCAN`
-   data-type command references
-   command time complexity
-   Redis Enterprise supported/restricted command behavior
-   client retry and connection guidance

------------------------------------------------------------------------

# Next Chapter

**Chapter 05 --- Redis Enterprise Databases, Endpoints & Configuration**

Chapter 05 will cover:

-   Redis Enterprise database architecture
-   database lifecycle
-   endpoints
-   memory limits
-   replication configuration
-   persistence configuration
-   eviction policy
-   shard count
-   proxy behavior
-   database configuration inspection
-   safe configuration changes
-   hands-on database inspection lab
-   failure injection
-   troubleshooting
-   production database configuration runbook
-   acceptance checklist
