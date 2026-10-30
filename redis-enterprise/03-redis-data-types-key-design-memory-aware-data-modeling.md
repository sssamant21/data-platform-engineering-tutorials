# Chapter 03 --- Redis Data Types, Key Design & Memory-Aware Data Modeling

**Status:** Canonical\
**Track:** Redis Enterprise / Redis Software Production Engineering\
**Level:** Foundation → Production Engineering\
**Audience:** Developers, SREs, DBREs, Platform Engineers, Redis
Administrators\
**Lab type:** Data modeling, memory inspection, TTL design, failure
injection, and production design review

------------------------------------------------------------------------

## 1. Objective

Redis performance depends heavily on data modeling.

Two applications can store the same logical information in Redis but
produce very different:

-   memory consumption
-   command latency
-   network traffic
-   CPU usage
-   key counts
-   expiration behavior
-   operational risk

This chapter teaches how to choose Redis data types and key structures
deliberately rather than treating Redis as a generic key/value bucket.

By the end, you should be able to:

-   Explain the major Redis data types.
-   Choose between strings and hashes for object storage.
-   Use lists, sets, sorted sets, and streams appropriately.
-   Understand that serialized JSON stored with `SET` is still a Redis
    string.
-   Distinguish serialized JSON from the Redis JSON data
    type/capability.
-   Design predictable key namespaces.
-   Include tenant, authorization, version, and query dimensions when
    required.
-   Avoid sensitive information in key names.
-   Apply TTLs intentionally.
-   Understand how data-model choices affect memory.
-   Inspect memory usage for individual keys.
-   Detect type mismatches.
-   Recognize big-key and hot-key risks.
-   Avoid unbounded collections.
-   Inspect keyspace safely with `SCAN`.
-   Build and compare several Redis models in a hands-on lab.
-   Perform a production data-model review before an application
    launches.

------------------------------------------------------------------------

# Part 1 --- Redis Data Modeling Fundamentals

## 2. Redis Is More Than `GET` and `SET`

The simplest Redis mental model is:

``` text
key -> value
```

Example:

``` redis
SET customer:1001 "Alice"
```

But Redis values can have different native data structures.

Common types include:

``` text
String
Hash
List
Set
Sorted Set
Stream
```

Additional Redis capabilities can provide structures such as JSON and
search/query functionality depending on product configuration.

Choosing the correct structure affects:

``` text
memory
CPU
network
atomicity
application complexity
operational behavior
```

------------------------------------------------------------------------

## 3. Inspect a Key's Type

Use:

``` redis
TYPE <key>
```

Example:

``` redis
SET tutorial:chapter03:name "Alice"
TYPE tutorial:chapter03:name
```

Expected:

``` text
string
```

Type awareness matters because commands operate on specific data types.

For example:

``` redis
GET
```

expects a string.

Running `GET` against a hash produces:

``` text
WRONGTYPE
```

This is not Redis corruption.

It is an application/data-model mismatch.

------------------------------------------------------------------------

# Part 2 --- Strings

## 4. Redis Strings

Strings are the most general Redis value type.

Examples:

``` redis
SET tutorial:chapter03:user:1001:name "Alice"
GET tutorial:chapter03:user:1001:name
```

Strings can store:

``` text
text
integers
floating-point representations
serialized JSON
binary data
serialized application objects
```

Common commands:

``` text
SET
GET
MSET
MGET
INCR
INCRBY
DECR
APPEND
STRLEN
GETRANGE
```

------------------------------------------------------------------------

## 5. Whole-Object String Pattern

An application may serialize an entire object:

``` redis
SET tutorial:chapter03:product:1001  '{"name":"Keyboard","price":49.99,"stock":25}'
```

Read:

``` redis
GET tutorial:chapter03:product:1001
```

Advantages:

``` text
simple
one GET
one SET
natural cache-aside representation
easy whole-object replacement
```

Disadvantages:

``` text
changing one field may require replacing the entire object
larger network payload for partial access
application owns serialization/deserialization
```

This pattern is often appropriate for cached API/database objects.

------------------------------------------------------------------------

## 6. Serialized JSON Is Still a String

This:

``` redis
SET product:1001 '{"name":"Keyboard"}'
```

creates:

``` text
TYPE product:1001
-> string
```

It does **not** automatically create a Redis JSON document.

This distinction matters operationally.

A serialized JSON string is manipulated with string commands.

A native Redis JSON document uses JSON-specific commands/capabilities
where enabled.

Do not mix these models accidentally.

------------------------------------------------------------------------

## 7. Atomic Counters

Strings can represent numeric counters.

Example:

``` redis
SET tutorial:chapter03:requests 0
INCR tutorial:chapter03:requests
INCR tutorial:chapter03:requests
GET tutorial:chapter03:requests
```

Expected:

``` text
2
```

`INCR` is atomic for the key.

Useful examples:

``` text
request counters
rate-limit counters
sequence-like values
usage counters
```

Counters can become hot keys under extreme concurrency, which later
performance chapters address.

------------------------------------------------------------------------

# Part 3 --- Hashes

## 8. Redis Hashes

A hash stores field/value pairs under one Redis key.

Example:

``` redis
HSET tutorial:chapter03:user:1001  name "Alice"  status "active"  region "us-east"
```

Read one field:

``` redis
HGET tutorial:chapter03:user:1001 status
```

Read all fields:

``` redis
HGETALL tutorial:chapter03:user:1001
```

------------------------------------------------------------------------

## 9. Hash Use Cases

Hashes are useful when:

``` text
one logical object has multiple fields
fields are accessed independently
fields are updated independently
```

Example:

``` text
user:1001
|
+-- name
+-- email
+-- status
+-- region
```

Commands:

``` text
HSET
HGET
HMGET
HGETALL
HDEL
HEXISTS
HINCRBY
HLEN
HSCAN
```

------------------------------------------------------------------------

## 10. Partial Updates

Suppose:

``` redis
HSET tutorial:chapter03:product:1002  name "Mouse"  price "19.99"  stock "25"
```

Update only stock:

``` redis
HSET tutorial:chapter03:product:1002 stock "24"
```

Redis does not need the application to replace the entire object.

This can reduce:

``` text
serialization
network payload
application work
```

when partial updates are common.

------------------------------------------------------------------------

## 11. String vs Hash

Suppose we store:

``` text
Product:
ID: 1001
Name: Keyboard
Price: 49.99
Stock: 25
```

### String model

``` redis
SET product:1001  '{"name":"Keyboard","price":49.99,"stock":25}'
```

### Hash model

``` redis
HSET product:1001  name "Keyboard"  price "49.99"  stock "25"
```

Neither is universally better.

Choose based on access patterns.

### Prefer a string when

``` text
application usually reads whole object
application usually replaces whole object
serialized source representation is already available
cache is primarily whole-response caching
```

### Prefer a hash when

``` text
fields are independently accessed
fields are independently updated
atomic field increments are useful
partial retrieval is common
```

------------------------------------------------------------------------

# Part 4 --- Lists

## 12. Redis Lists

Lists are ordered sequences.

Example:

``` redis
LPUSH tutorial:chapter03:recent-events event3 event2 event1
```

Read:

``` redis
LRANGE tutorial:chapter03:recent-events 0 -1
```

Common commands:

``` text
LPUSH
RPUSH
LPOP
RPOP
LRANGE
LLEN
LTRIM
```

Potential use cases:

``` text
bounded recent-event lists
simple queues
recent-history buffers
```

For durable messaging and consumer-group semantics, Redis Streams are
generally a more appropriate model.

------------------------------------------------------------------------

## 13. Bound Lists

Avoid indefinitely growing lists.

Example bounded pattern:

``` redis
LPUSH application:recent-events <event>
LTRIM application:recent-events 0 999
```

This retains approximately the latest 1,000 elements.

Unbounded collections can cause:

``` text
memory growth
large-key problems
slow operations
difficult migrations
recovery overhead
```

------------------------------------------------------------------------

# Part 5 --- Sets

## 14. Redis Sets

Sets store unique unordered members.

Example:

``` redis
SADD tutorial:chapter03:user:1001:roles admin viewer
```

Check membership:

``` redis
SISMEMBER tutorial:chapter03:user:1001:roles admin
```

Expected:

``` text
1
```

Read members:

``` redis
SMEMBERS tutorial:chapter03:user:1001:roles
```

Common commands:

``` text
SADD
SREM
SISMEMBER
SCARD
SMEMBERS
SSCAN
SINTER
SUNION
SDIFF
```

------------------------------------------------------------------------

## 15. Set Use Cases

Sets are useful for:

``` text
unique membership
tags
permissions
feature membership
deduplicated IDs
relationship sets
```

Example:

``` text
feature:beta:users
|
+-- user1001
+-- user1007
+-- user1044
```

Before using one huge set, estimate maximum cardinality.

------------------------------------------------------------------------

# Part 6 --- Sorted Sets

## 16. Redis Sorted Sets

Sorted sets associate members with numeric scores.

Example:

``` redis
ZADD tutorial:chapter03:leaderboard  1500 alice  2200 bob  1800 carol
```

Read ordered ranking:

``` redis
ZRANGE tutorial:chapter03:leaderboard 0 -1 WITHSCORES
```

Descending ranking:

``` redis
ZREVRANGE tutorial:chapter03:leaderboard 0 -1 WITHSCORES
```

Common commands:

``` text
ZADD
ZRANGE
ZREVRANGE
ZRANK
ZREVRANK
ZSCORE
ZINCRBY
ZCARD
ZREM
ZSCAN
```

------------------------------------------------------------------------

## 17. Sorted Set Use Cases

Typical patterns:

``` text
leaderboards
priority ranking
time-ordered indexes
scored recommendations
scheduling indexes
```

Example time-based index:

``` redis
ZADD job:schedule 1791400000 job:1001
```

The score can represent a timestamp.

Be deliberate about collection growth.

------------------------------------------------------------------------

# Part 7 --- Streams

## 18. Redis Streams

Streams are append-oriented structures designed for event/message
workloads.

Example:

``` redis
XADD tutorial:chapter03:events '*'  type login  user 1001
```

Read:

``` redis
XRANGE tutorial:chapter03:events - +
```

Common concepts:

``` text
stream entry
entry ID
consumer group
consumer
pending entries
acknowledgment
```

Streams are covered deeply later.

For Chapter 03, understand that a Stream is not merely a List with a
different command name.

------------------------------------------------------------------------

## 19. Stream Growth

An unbounded stream can consume increasing memory.

Bound growth deliberately.

Example approximate trimming:

``` redis
XADD tutorial:chapter03:bounded-stream  MAXLEN ~ 1000  '*' type test value 1
```

Retention requirements should be based on:

``` text
consumer lag
recovery needs
event rate
memory budget
```

not an arbitrary number copied from another system.

------------------------------------------------------------------------

# Part 8 --- Redis JSON

## 20. Native JSON vs Serialized JSON

Serialized JSON string:

``` redis
SET customer:1001 '{"name":"Alice","status":"active"}'
```

Type:

``` redis
TYPE customer:1001
```

returns:

``` text
string
```

Where Redis JSON capability is enabled, a native JSON document can use
JSON commands such as:

``` text
JSON.SET
JSON.GET
```

Example conceptually:

``` redis
JSON.SET customer:1001 $ '{"name":"Alice","status":"active"}'
```

Do not assume JSON commands are enabled on every database.

Validate product/database capabilities first.

Redis JSON and Search are covered in a dedicated advanced chapter.

------------------------------------------------------------------------

# Part 9 --- Key Design

## 21. Key Naming Convention

A useful convention is:

``` text
<service>:<entity>:<id>:<attribute/version>
```

Examples:

``` text
catalog:product:1001:v1
patient360:session:abc123
claims:member:1001:summary:v2
auth:ratelimit:user:1001
```

Colons are a convention.

They do not create directories.

------------------------------------------------------------------------

## 22. Key Names Should Explain Ownership

Compare:

``` text
1001
```

with:

``` text
catalog:product:1001:v1
```

The second communicates:

``` text
owner/service = catalog
entity = product
ID = 1001
version = v1
```

Operationally meaningful names improve troubleshooting.

------------------------------------------------------------------------

## 23. Include All Cache Dimensions

Suppose an API response varies by:

``` text
patient
region
language
permission scope
```

This may be unsafe:

``` text
patient:1001:summary
```

because different callers could receive different representations.

A conceptual key might require:

``` text
patient:1001:summary:region:us-east:lang:en:scope:clinician:v2
```

The exact design depends on application requirements.

Principle:

> Every input that changes the cached output may need representation in
> the cache identity.

Failure to do this can become a correctness or security issue.

------------------------------------------------------------------------

## 24. Multi-Tenant Key Design

For multi-tenant applications:

``` text
service:tenant:<tenant-id>:entity:<id>
```

Example:

``` text
billing:tenant:acme:invoice:1001
```

This can reduce accidental key collisions.

However:

> A key prefix is not an access-control boundary.

Redis authorization must still be designed correctly.

------------------------------------------------------------------------

## 25. Do Not Put Secrets in Keys

Avoid:

``` text
session:<password>
token:<access-token>
api-key:<secret>
```

Key names can appear in:

``` text
diagnostic output
monitoring
memory analysis
debug logs
support artifacts
```

Use non-sensitive identifiers.

------------------------------------------------------------------------

## 26. Sensitive Personal Data in Key Names

Avoid unnecessarily embedding:

``` text
patient names
email addresses
SSNs
medical identifiers
other sensitive data
```

Prefer opaque internal IDs where possible.

Example:

``` text
patient:9f72c1:summary
```

instead of:

``` text
patient:john-smith-ssn-123456789:summary
```

------------------------------------------------------------------------

## 27. Key Versioning

Versioning can make cache schema changes safer.

Example:

``` text
catalog:product:1001:v1
catalog:product:1001:v2
```

Application deployment can begin reading:

``` text
v2
```

while old `v1` keys expire naturally.

This can reduce complex bulk invalidation.

------------------------------------------------------------------------

# Part 10 --- TTL Design

## 28. TTL Is Part of the Data Model

Set expiration:

``` redis
EXPIRE key 300
```

or atomically with string creation:

``` redis
SET key value EX 300
```

Check:

``` redis
TTL key
```

Possible results include:

``` text
positive integer -> seconds remaining
-1               -> key exists without expiration
-2               -> key does not exist
```

------------------------------------------------------------------------

## 29. Avoid Accidental Persistent Cache Keys

A cache key that was intended to expire but has:

``` redis
TTL key
```

return:

``` text
-1
```

can contribute to long-term memory growth.

Production cache validation should check:

``` text
expected TTL present
unexpected persistent keys
expiration distribution
```

------------------------------------------------------------------------

## 30. TTL by Data Semantics

Example conceptual policy:

``` text
static reference data      -> long TTL
product pricing            -> moderate TTL
user session               -> session-driven TTL
rapidly changing status    -> short TTL
negative cache             -> short TTL
```

Do not set all keys to:

``` text
300 seconds
```

simply because one tutorial used that value.

------------------------------------------------------------------------

## 31. TTL Jitter

If millions of keys are created simultaneously with exactly:

``` text
TTL = 3600
```

many can expire around the same time.

This can cause:

``` text
cache misses
source database spike
cache stampede
```

Applications can add controlled TTL jitter.

Conceptually:

``` text
base TTL = 3600
jitter   = ±300
```

The exact policy must preserve freshness requirements.

------------------------------------------------------------------------

# Part 11 --- Memory-Aware Modeling

## 32. Redis Memory Is Not Just Payload Size

A logical value:

``` text
100 bytes
```

does not necessarily consume exactly:

``` text
100 bytes
```

Redis memory includes overhead related to:

``` text
key object
value object
data structure
allocator
metadata
encoding
fragmentation
replication
platform/database architecture
```

Capacity planning must measure real workloads.

------------------------------------------------------------------------

## 33. Inspect Key Memory

Use:

``` redis
MEMORY USAGE <key>
```

Example:

``` redis
MEMORY USAGE tutorial:chapter03:product:string
```

Result:

``` text
<number of bytes>
```

This allows empirical comparison between models.

Do not extrapolate an entire production capacity plan from one tiny
sample.

------------------------------------------------------------------------

## 34. Inspect Object Encoding

Where permitted:

``` redis
OBJECT ENCODING <key>
```

Redis can use different internal encodings depending on:

``` text
type
size
member count
value sizes
Redis version
```

Internal encoding is an implementation detail and can change.

Do not build application correctness around a specific encoding.

------------------------------------------------------------------------

## 35. Compare String and Hash Memory

Create string:

``` redis
SET tutorial:chapter03:product:string  '{"name":"Keyboard","price":"49.99","stock":"25","category":"accessories"}'
```

Create hash:

``` redis
HSET tutorial:chapter03:product:hash  name "Keyboard"  price "49.99"  stock "25"  category "accessories"
```

Measure:

``` redis
MEMORY USAGE tutorial:chapter03:product:string
MEMORY USAGE tutorial:chapter03:product:hash
```

The result can differ based on Redis version and internal encoding.

The lesson is:

> Measure realistic representative objects rather than relying on
> folklore such as "hashes always use less memory."

------------------------------------------------------------------------

# Part 12 --- Big Keys

## 36. What Is a Big Key?

A big key is a key whose value or collection is operationally large.

Examples:

``` text
huge string
hash with millions of fields
list with millions of elements
set with millions of members
sorted set with millions of members
very large stream
```

There is no universal byte/member threshold for every workload.

Impact depends on:

``` text
command
CPU
network
memory
latency SLO
replication
migration
backup
failure recovery
```

------------------------------------------------------------------------

## 37. Why Big Keys Are Dangerous

Potential impact:

``` text
long command execution
large network responses
CPU spikes
memory spikes
slow deletion
replication overhead
shard migration overhead
backup/recovery overhead
latency outliers
```

Example:

``` redis
HGETALL gigantic-hash
```

can return an enormous response.

Avoid designing APIs that require retrieving an unbounded structure in
one command.

------------------------------------------------------------------------

## 38. Safer Collection Inspection

For large collections prefer incremental iteration where appropriate:

``` text
HSCAN
SSCAN
ZSCAN
SCAN
```

rather than requesting everything at once.

Example:

``` redis
HSCAN myhash 0 COUNT 100
```

`COUNT` is a hint, not an exact guarantee.

------------------------------------------------------------------------

# Part 13 --- Hot Keys

## 39. What Is a Hot Key?

A hot key receives a disproportionate share of operations.

Example:

``` text
homepage:global-config
```

may receive:

``` text
100,000 GETs/sec
```

while most keys receive almost none.

Even a tiny key can be operationally hot.

Therefore:

``` text
big key != hot key
```

A key can be:

``` text
big but cold
small but hot
big and hot
neither
```

------------------------------------------------------------------------

## 40. Why Hot Keys Matter

A key maps to a shard.

Extreme traffic concentration can therefore concentrate CPU/work on one
shard.

Symptoms may include:

``` text
one shard CPU high
other shards low
database average looks acceptable
latency increases
```

This is why average database CPU alone can hide skew.

Hot-key investigation is covered deeply in the performance section.

------------------------------------------------------------------------

# Part 14 --- Cardinality

## 41. Key Cardinality

Cardinality means how many keys or members exist.

Questions to ask before launch:

``` text
How many customers?
How many keys per customer?
How many tenants?
How many collection members?
How fast does the count grow?
What expires?
What never expires?
```

Example:

``` text
2 million users
× 20 cache keys/user
=
40 million potential keys
```

Key naming is therefore also capacity planning.

------------------------------------------------------------------------

## 42. Collection Cardinality

Suppose:

``` text
user:all-sessions
```

is one Set containing every session ID.

At large scale this becomes one enormous key.

An alternative design may partition by:

``` text
tenant
time window
region
bucket
```

depending on access requirements.

Do not partition blindly; design from the queries/operations the
application needs.

------------------------------------------------------------------------

# Part 15 --- Safe Keyspace Inspection

## 43. Avoid `KEYS *` in Production

This command:

``` redis
KEYS *
```

scans the keyspace synchronously and can be disruptive on large
databases.

Do not use it as a routine production inventory command.

Prefer:

``` redis
SCAN 0
```

Example:

``` redis
SCAN 0 MATCH 'catalog:*' COUNT 100
```

Continue using the returned cursor until:

``` text
cursor = 0
```

------------------------------------------------------------------------

## 44. `SCAN` Is Incremental

Example response:

``` text
1) "42"
2) 1) "catalog:product:1001"
   2) "catalog:product:1002"
```

Continue:

``` redis
SCAN 42 MATCH 'catalog:*' COUNT 100
```

until cursor returns:

``` text
0
```

Important:

-   `COUNT` is a hint.
-   Results can change while the keyspace changes.
-   Applications should not assume one scan page is complete.

------------------------------------------------------------------------

# Part 16 --- Type Mismatch

## 45. `WRONGTYPE`

Create:

``` redis
HSET tutorial:chapter03:type-test name Alice
```

Then:

``` redis
GET tutorial:chapter03:type-test
```

Expected:

``` text
WRONGTYPE Operation against a key holding the wrong kind of value
```

Troubleshoot:

``` redis
TYPE tutorial:chapter03:type-test
```

Expected:

``` text
hash
```

Then use:

``` redis
HGETALL tutorial:chapter03:type-test
```

------------------------------------------------------------------------

## 46. Why Type Mismatches Happen

Common causes:

``` text
two services reuse same key namespace
application deployment changes model
old cache keys survive deployment
manual testing writes wrong type
missing key version
environment collision
```

Prevention:

``` text
clear ownership
namespaces
schema/key versioning
TTL
deployment compatibility
tests
```

------------------------------------------------------------------------

# Hands-On Lab --- Model a Product Cache

## 47. Lab Goal

You will:

1.  Build string and hash models.
2.  Create a list.
3.  Create a set.
4.  Create a sorted set.
5.  Create a stream.
6.  Apply TTLs.
7.  Inspect types.
8.  Inspect cardinality.
9.  Compare memory.
10. inspect internal encoding.
11. reproduce `WRONGTYPE`.
12. use `SCAN`.
13. test versioned keys.
14. clean up safely.

Use a development/test database.

------------------------------------------------------------------------

## 48. Lab Namespace

All lab keys use:

``` text
tutorial:chapter03:
```

Do not change this to an application production prefix.

------------------------------------------------------------------------

## 49. Lab 1 --- String Object

Create:

``` redis
SET tutorial:chapter03:product:1001:v1 '{"name":"Keyboard","price":49.99,"stock":25,"category":"accessories"}' EX 600
```

Verify:

``` redis
GET tutorial:chapter03:product:1001:v1
TYPE tutorial:chapter03:product:1001:v1
TTL tutorial:chapter03:product:1001:v1
STRLEN tutorial:chapter03:product:1001:v1
MEMORY USAGE tutorial:chapter03:product:1001:v1
```

Record:

``` text
Type:
TTL:
String length:
Memory usage:
```

------------------------------------------------------------------------

## 50. Lab 2 --- Hash Object

Create:

``` redis
HSET tutorial:chapter03:product:1002:v1 name "Mouse" price "19.99" stock "25" category "accessories"
```

**Expected:** HSET reports 4 newly added hash fields when run on an absent lab key. The example uses a **single Redis command**; do not paste Bash-style trailing backslashes into an interactive Redis command prompt. If a prior lab run left this key in place, the added-field count can differ; use a fresh isolated test database or review/remove the exact disposable key first.

Apply TTL:

``` redis
EXPIRE tutorial:chapter03:product:1002:v1 600
```

Verify:

``` redis
TYPE tutorial:chapter03:product:1002:v1
HGETALL tutorial:chapter03:product:1002:v1
HLEN tutorial:chapter03:product:1002:v1
TTL tutorial:chapter03:product:1002:v1
MEMORY USAGE tutorial:chapter03:product:1002:v1
```

Update one field:

``` redis
HSET tutorial:chapter03:product:1002:v1 stock "24"
```

Verify:

``` redis
HGET tutorial:chapter03:product:1002:v1 stock
TTL tutorial:chapter03:product:1002:v1
```

Observe that updating a hash field does not inherently remove the
existing key TTL.

------------------------------------------------------------------------

## 51. Lab 3 --- Counter

``` redis
SET tutorial:chapter03:product:1002:views 0 EX 600
INCR tutorial:chapter03:product:1002:views
INCR tutorial:chapter03:product:1002:views
INCRBY tutorial:chapter03:product:1002:views 5
GET tutorial:chapter03:product:1002:views
```

Expected:

``` text
7
```

------------------------------------------------------------------------

## 52. Lab 4 --- Bounded Recent-Views List

``` redis
LPUSH tutorial:chapter03:recent-products 1001 1002 1003 1004
LTRIM tutorial:chapter03:recent-products 0 2
EXPIRE tutorial:chapter03:recent-products 600
LRANGE tutorial:chapter03:recent-products 0 -1
LLEN tutorial:chapter03:recent-products
```

Expected length:

``` text
3
```

The exercise demonstrates explicit bounding.

------------------------------------------------------------------------

## 53. Lab 5 --- Product Tags Set

``` redis
SADD tutorial:chapter03:product:1001:tags  electronics  accessories  keyboard
```

Then:

``` redis
SISMEMBER tutorial:chapter03:product:1001:tags keyboard
SCARD tutorial:chapter03:product:1001:tags
SMEMBERS tutorial:chapter03:product:1001:tags
EXPIRE tutorial:chapter03:product:1001:tags 600
```

Expected cardinality:

``` text
3
```

------------------------------------------------------------------------

## 54. Lab 6 --- Leaderboard Sorted Set

``` redis
ZADD tutorial:chapter03:product:views  150 1001  275 1002  90 1003
```

Read descending:

``` redis
ZREVRANGE tutorial:chapter03:product:views 0 -1 WITHSCORES
```

Increment:

``` redis
ZINCRBY tutorial:chapter03:product:views 25 1001
```

Check:

``` redis
ZSCORE tutorial:chapter03:product:views 1001
ZCARD tutorial:chapter03:product:views
EXPIRE tutorial:chapter03:product:views 600
```

------------------------------------------------------------------------

## 55. Lab 7 --- Stream

Create:

``` redis
XADD tutorial:chapter03:events MAXLEN ~ 1000 '*'  type product_view  product_id 1001
```

Add another:

``` redis
XADD tutorial:chapter03:events MAXLEN ~ 1000 '*'  type product_view  product_id 1002
```

Inspect:

``` redis
XLEN tutorial:chapter03:events
XRANGE tutorial:chapter03:events - +
```

Set TTL for the lab:

``` redis
EXPIRE tutorial:chapter03:events 600
```

Production stream retention should be designed explicitly rather than
relying solely on a key-level TTL.

------------------------------------------------------------------------

## 56. Lab 8 --- Compare Types

Run:

``` redis
TYPE tutorial:chapter03:product:1001:v1
TYPE tutorial:chapter03:product:1002:v1
TYPE tutorial:chapter03:recent-products
TYPE tutorial:chapter03:product:1001:tags
TYPE tutorial:chapter03:product:views
TYPE tutorial:chapter03:events
```

Expected:

``` text
string
hash
list
set
zset
stream
```

------------------------------------------------------------------------

## 57. Lab 9 --- Compare Memory

Run:

``` redis
MEMORY USAGE tutorial:chapter03:product:1001:v1
MEMORY USAGE tutorial:chapter03:product:1002:v1
MEMORY USAGE tutorial:chapter03:recent-products
MEMORY USAGE tutorial:chapter03:product:1001:tags
MEMORY USAGE tutorial:chapter03:product:views
MEMORY USAGE tutorial:chapter03:events
```

Record:

  Key                 Type       Logical size/cardinality   Memory
  ------------------- -------- -------------------------- --------
  product:1001:v1     string                              
  product:1002:v1     hash                                
  recent-products     list                                
  product:1001:tags   set                                 
  product:views       zset                                
  events              stream                              

Do not compare memory numbers without also considering what information
each structure stores.

------------------------------------------------------------------------

## 58. Lab 10 --- Inspect Encoding

Where allowed:

``` redis
OBJECT ENCODING tutorial:chapter03:product:1001:v1
OBJECT ENCODING tutorial:chapter03:product:1002:v1
OBJECT ENCODING tutorial:chapter03:recent-products
OBJECT ENCODING tutorial:chapter03:product:1001:tags
OBJECT ENCODING tutorial:chapter03:product:views
```

Record the results.

Do not write application logic based on these encodings.

------------------------------------------------------------------------

## 59. Lab 11 --- Type Mismatch

Run:

``` redis
GET tutorial:chapter03:product:1002:v1
```

Expected:

``` text
WRONGTYPE
```

Diagnose:

``` redis
TYPE tutorial:chapter03:product:1002:v1
```

Then use:

``` redis
HGETALL tutorial:chapter03:product:1002:v1
```

------------------------------------------------------------------------

## 60. Lab 12 --- Versioned Cache

Create:

``` redis
SET tutorial:chapter03:product:2001:v1 '{"name":"Monitor","schema":1}' EX 600
SET tutorial:chapter03:product:2001:v2 '{"name":"Monitor","schema":2,"currency":"USD"}' EX 600
```

Read both:

``` redis
GET tutorial:chapter03:product:2001:v1
GET tutorial:chapter03:product:2001:v2
```

This demonstrates parallel schema versions.

A deployment can move to `v2` without mutating the `v1` representation.

------------------------------------------------------------------------

## 61. Lab 13 --- Safe Namespace Scan

Run:

``` redis
SCAN 0 MATCH 'tutorial:chapter03:*' COUNT 100
```

If the cursor is non-zero, continue with that cursor.

Example:

``` redis
SCAN <cursor> MATCH 'tutorial:chapter03:*' COUNT 100
```

Continue until cursor:

``` text
0
```

Do not replace this with:

``` redis
KEYS *
```

in a large production database.

------------------------------------------------------------------------

## 62. Lab 14 --- TTL Audit

For the lab namespace, inspect TTLs of the keys you created.

Examples:

``` redis
TTL tutorial:chapter03:product:1001:v1
TTL tutorial:chapter03:product:1002:v1
TTL tutorial:chapter03:recent-products
TTL tutorial:chapter03:product:1001:tags
TTL tutorial:chapter03:product:views
TTL tutorial:chapter03:events
```

Any intended cache key returning:

``` text
-1
```

should be reviewed.

------------------------------------------------------------------------

# Failure Injection

## 63. Failure 1 --- Wrong Type

Already reproduced:

``` redis
GET tutorial:chapter03:product:1002:v1
```

Expected:

``` text
WRONGTYPE
```

Recovery:

``` text
inspect TYPE
use correct command
review application schema/key ownership
```

------------------------------------------------------------------------

## 64. Failure 2 --- Missing TTL

Create intentionally:

``` redis
SET tutorial:chapter03:no-ttl "test"
```

Check:

``` redis
TTL tutorial:chapter03:no-ttl
```

Expected:

``` text
-1
```

Fix:

``` redis
EXPIRE tutorial:chapter03:no-ttl 300
```

Verify:

``` redis
TTL tutorial:chapter03:no-ttl
```

Operational lesson:

> Successful cache writes do not guarantee expiration was configured.

------------------------------------------------------------------------

## 65. Failure 3 --- Namespace Collision

In the isolated lab, create:

``` redis
SET tutorial:chapter03:collision "string"
```

Then attempt:

``` redis
HSET tutorial:chapter03:collision field value
```

Expected:

``` text
WRONGTYPE
```

This simulates two code paths disagreeing about the schema of one key.

Fix the key model, not Redis.

------------------------------------------------------------------------

## 66. Failure 4 --- Unbounded Collection Design Review

Do **not** create millions of elements.

Instead inspect this proposed design:

``` text
all-users:sessions
```

Questions:

``` text
Could it grow forever?
What is expected maximum cardinality?
Can old members be removed?
Does one operation retrieve the entire set?
Can it be partitioned safely?
```

Failure injection does not need to damage a database to teach an
operational failure mode.

------------------------------------------------------------------------

# Troubleshooting

## 67. Application Reports `WRONGTYPE`

Run:

``` redis
TYPE <key>
```

Then identify:

``` text
expected application type
actual Redis type
key owner
deployment/version
TTL
creation path
```

Do not delete the key immediately in production without understanding
impact.

------------------------------------------------------------------------

## 68. Memory Growth

Investigate:

``` text
key count growth
persistent keys
TTL distribution
large values
large collections
streams
unexpected namespaces
application deployment
traffic growth
```

Useful commands may include:

``` redis
DBSIZE
INFO memory
SCAN 0 MATCH 'tutorial:chapter03:*' COUNT 100
MEMORY USAGE <key>
TYPE <key>
TTL <key>
```

Avoid running expensive broad diagnostics blindly during an incident.

**Expected:** `SCAN` returns a cursor and possibly zero or more lab keys; continue using the returned cursor until it is `0`, even if an intermediate batch is empty. `COUNT` is a hint, duplicates are possible, and scanning is not a transactional snapshot. `DBSIZE` and `INFO` are database-wide metrics, so review permissions and operational cost before using them. Replace `<key>` with an exact owned key before type/size checks. One SCAN call is not a complete inventory.

------------------------------------------------------------------------

## 69. One Key Uses Large Memory

Identify:

``` redis
TYPE <key>
MEMORY USAGE <key>
```

Then use type-specific cardinality:

``` text
String     -> STRLEN
Hash       -> HLEN
List       -> LLEN
Set        -> SCARD
Sorted Set -> ZCARD
Stream     -> XLEN
```

This gives both memory and logical size context.

------------------------------------------------------------------------

## 70. One Shard Is Hot

Potential causes include:

``` text
hot key
skewed key distribution
large expensive commands
application traffic pattern
collection design
```

Do not conclude:

``` text
need more nodes
```

before checking workload distribution.

A single hot key can remain concentrated even in a large cluster.

------------------------------------------------------------------------

## 71. Cache Keeps Growing

Check for:

``` text
missing TTL
TTL accidentally removed
new key version without expiration
old versions not expiring
unbounded collection
stream growth
higher traffic/cardinality
negative cache without TTL
```

Capacity problems often originate in data-model behavior rather than
infrastructure alone.

------------------------------------------------------------------------

# Production Data-Model Review

## 72. Review Template

Before approving a new Redis use case, document:

``` text
Service:
Owner:
Database:
Use case:
Source of truth:
Expected key count:
Peak key count:
Expected value size:
Maximum value size:
Data type:
Collection cardinality:
TTL:
TTL jitter:
Write rate:
Read rate:
Hot-key risk:
Big-key risk:
Persistence required:
Replication required:
Recovery method:
Sensitive data:
Key namespace:
Schema version:
```

------------------------------------------------------------------------

## 73. Estimate Dataset

Example:

``` text
5,000,000 keys
×
average measured 700 bytes/key
=
3.5 GB measured key footprint
```

But do not stop there.

Capacity also needs to account for:

``` text
replicas
memory headroom
fragmentation
growth
platform overhead
temporary operational overhead
```

Detailed Redis Enterprise capacity planning is covered later.

------------------------------------------------------------------------

## 74. Design for Deletion

Every persistent or long-lived structure needs a lifecycle.

Ask:

``` text
Who deletes it?
When?
By TTL?
By explicit DEL?
By trimming?
By application lifecycle?
```

"No one knows" is a production risk.

------------------------------------------------------------------------

## 75. Design for Schema Change

Before launch ask:

``` text
What happens when fields change?
Can old clients read new values?
Can new clients read old values?
Will we version keys?
Will old keys expire?
```

Redis has no automatic application schema migration for arbitrary cached
payloads.

The application owns that compatibility.

------------------------------------------------------------------------

# Operational Runbook

## 76. Runbook --- Suspected Big Key

``` text
1. Record database and incident timestamp.
2. Identify candidate key safely.
3. Run TYPE on the key.
4. Run MEMORY USAGE on the key.
5. Run type-specific cardinality/size command.
6. Identify commands executed against the key.
7. Check latency impact.
8. Check shard CPU.
9. Check network response sizes.
10. Check replication/migration impact.
11. Determine application ownership.
12. Avoid blindly deleting production data.
13. Design split/bound/expire/remodel remediation.
14. Validate remediation in non-production.
```

------------------------------------------------------------------------

## 77. Runbook --- Unexpected Memory Growth

``` text
1. Confirm database memory trend.
2. Confirm key-count trend.
3. Identify new namespaces/deployments.
4. Sample TTL behavior safely.
5. Look for persistent cache keys.
6. Identify large structures.
7. Check stream/list/set/zset growth.
8. Check average value-size changes.
9. Check traffic/cardinality changes.
10. Check eviction behavior.
11. Identify owning service.
12. Correct lifecycle/model before simply increasing memory.
13. Validate memory trend after remediation.
```

------------------------------------------------------------------------

## 78. Runbook --- Type Mismatch Incident

``` text
1. Capture exact WRONGTYPE error.
2. Capture key name safely.
3. Run TYPE.
4. Identify expected type.
5. Identify application owner.
6. Check recent deployment.
7. Check key version.
8. Check TTL.
9. Determine whether old/new code paths overlap.
10. Do not overwrite production key blindly.
11. Correct namespace/schema compatibility.
12. Validate with representative requests.
```

------------------------------------------------------------------------

# Cleanup

## 79. Lab Cleanup

Use `SCAN` to confirm the exact tutorial namespace.

Then delete only known lab keys.

Examples:

``` redis
DEL tutorial:chapter03:product:1001:v1
DEL tutorial:chapter03:product:1002:v1
DEL tutorial:chapter03:product:1002:views
DEL tutorial:chapter03:recent-products
DEL tutorial:chapter03:product:1001:tags
DEL tutorial:chapter03:product:views
DEL tutorial:chapter03:events
DEL tutorial:chapter03:product:2001:v1
DEL tutorial:chapter03:product:2001:v2
DEL tutorial:chapter03:no-ttl
DEL tutorial:chapter03:collision
```

Never use:

``` redis
FLUSHDB
FLUSHALL
```

for tutorial cleanup.

------------------------------------------------------------------------

# Acceptance

## 80. Validation Questions

You should be able to answer:

1.  When is a Redis string appropriate?
2.  When is a hash preferable?
3.  Is serialized JSON stored with `SET` a native Redis JSON object?
4.  Why are lists dangerous if allowed to grow indefinitely?
5.  What problem does a Set solve?
6.  What problem does a Sorted Set solve?
7.  How is a Stream different from a simple List?
8.  Why should collection cardinality be bounded?
9.  Why should sensitive information be avoided in key names?
10. Why can multi-tenant applications require tenant identifiers in
    keys?
11. Why are key prefixes not security boundaries?
12. What does `TTL = -1` mean?
13. Why can identical TTLs cause a cache-expiration wave?
14. What does `MEMORY USAGE` tell you?
15. Why should you not assume hashes always consume less memory than
    strings?
16. What is a big key?
17. What is a hot key?
18. Can a small key be hot?
19. Why can one hot key create shard-level CPU imbalance?
20. Why should `SCAN` generally be preferred over `KEYS *` for
    production keyspace iteration?
21. What causes `WRONGTYPE`?
22. Why is key versioning useful?
23. Why must data lifecycle be part of data-model design?

------------------------------------------------------------------------

## 81. Hands-On Acceptance Checklist

-   [ ] Created a string object.
-   [ ] Created a hash object.
-   [ ] Updated an individual hash field.
-   [ ] Created an atomic counter.
-   [ ] Created and bounded a list.
-   [ ] Created a Set.
-   [ ] Created a Sorted Set.
-   [ ] Created a Stream.
-   [ ] Verified all key types.
-   [ ] Applied TTLs.
-   [ ] Audited TTL values.
-   [ ] Used `MEMORY USAGE`.
-   [ ] Compared string/hash memory.
-   [ ] Inspected object encoding where permitted.
-   [ ] Reproduced `WRONGTYPE`.
-   [ ] Diagnosed the mismatch with `TYPE`.
-   [ ] Created versioned cache keys.
-   [ ] Used `SCAN` for namespace inspection.
-   [ ] Created and corrected a missing-TTL example.
-   [ ] Reviewed an unbounded-collection anti-pattern.
-   [ ] Cleaned up only tutorial keys.

------------------------------------------------------------------------

## 82. Production Acceptance Checklist

Before approving a Redis data model:

-   [ ] Service ownership documented.
-   [ ] Key namespace documented.
-   [ ] Data type justified.
-   [ ] Expected key cardinality documented.
-   [ ] Maximum collection cardinality documented.
-   [ ] Expected value size measured.
-   [ ] Maximum value size considered.
-   [ ] TTL policy documented.
-   [ ] TTL jitter considered.
-   [ ] Persistent-key lifecycle documented.
-   [ ] Big-key risk reviewed.
-   [ ] Hot-key risk reviewed.
-   [ ] Tenant/security dimensions reviewed.
-   [ ] Sensitive data excluded from key names where possible.
-   [ ] Schema/versioning strategy documented.
-   [ ] Source of truth documented.
-   [ ] Recovery behavior documented.
-   [ ] Memory impact measured with representative data.
-   [ ] Production capacity headroom considered.

------------------------------------------------------------------------

## 83. Key Takeaways

1.  Redis data modeling directly affects memory, latency, CPU, and
    operability.
2.  Strings are ideal for many whole-object cache patterns.
3.  Hashes support field-level access and updates.
4.  Lists, Sets, Sorted Sets, and Streams solve different problems and
    should not be treated interchangeably.
5.  Serialized JSON stored with `SET` remains a Redis string.
6.  Key names should communicate ownership and identity without exposing
    secrets.
7.  Every dimension that changes a cached result may need to participate
    in cache identity.
8.  TTL is part of the data model, not an afterthought.
9.  Unbounded collections eventually become operational problems.
10. Measure memory with representative data instead of relying on
    assumptions.
11. Big keys and hot keys are different failure modes.
12. One hot key can overload one shard even when database-wide averages
    look healthy.
13. `SCAN` is the normal safer approach for incremental keyspace
    iteration.
14. `WRONGTYPE` usually indicates application/schema disagreement, not
    Redis corruption.
15. Every Redis structure needs an ownership, lifecycle, capacity, and
    recovery plan.

------------------------------------------------------------------------

## 84. References

Validate production behavior against the Redis documentation version
appropriate for your deployed Redis Enterprise / Redis Software release.

Key documentation areas:

-   Redis data types
-   Redis keyspace operations
-   Redis command reference
-   `SCAN`
-   `MEMORY USAGE`
-   expiration and TTL behavior
-   Redis Streams
-   Redis JSON
-   Redis Enterprise memory and performance guidance

------------------------------------------------------------------------

## Next Chapter

**Chapter 04 --- Redis Commands, Command Semantics & Safe Operations**

Chapter 04 will cover:

-   command categories
-   command complexity
-   atomic operations
-   conditional `SET`
-   multi-key operations
-   expiration semantics
-   safe deletion
-   `UNLINK` vs `DEL`
-   blocking commands
-   dangerous/expensive command awareness
-   administrative command restrictions
-   command troubleshooting
-   full command-safety lab
