# Chapter 002 — Relational Databases and DBMS Architecture

> **Track:** [SQL Tutorials](../README.md) → [Master TOC](../MASTER-TOC.md) → Part 01: Fundamentals  
> **Duration:** 60 minutes · **Audience:** Beginner SQL, data engineering, application engineering, DBRE/SRE  
> **Primary reference:** PostgreSQL 18 · **Prerequisite:** [Chapter 001](001-introduction-to-sql.md)  
> **Publication status:** Authored; independent editorial review and PostgreSQL 18 execution pending.

## Learning outcomes and lesson plan (5 minutes)

By the end, learners can explain the relational model, distinguish logical relationships from physical storage, describe a SQL request's path through a DBMS, identify core PostgreSQL server components, and inspect read-only catalog information.

| Segment | Minutes |
|---|---:|
| Outcomes and terminology | 5 |
| Relational model and constraints | 10 |
| DBMS architecture and SQL request lifecycle | 15 |
| Worked examples | 10 |
| Hands-on lab | 15 |
| Troubleshooting, review and next steps | 5 |

## 1. Relational model: logical view (10 minutes)

A **relational database** represents information as relations (commonly exposed as tables). Each row represents an instance; columns represent attributes. SQL uses **set- and bag-oriented operations** to query these relations. Unlike a spreadsheet, a database can enforce constraints and transactions across many connected tables.

Consider synthetic retail data:

**customers**

| customer_id | customer_name |
|---:|---|
| 1 | Ava |
| 2 | Noah |
| 3 | Mia |

**orders**

| order_id | customer_id | amount_usd |
|---:|---:|---:|
| 101 | 1 | 40.00 |
| 102 | 1 | 25.00 |
| 103 | 2 | 15.00 |

- **Primary key:** a column or combination of columns uniquely identifying a row (e.g. `customers.customer_id`).
- **Foreign key:** a constraint that requires referenced values to exist (e.g. `orders.customer_id` → `customers.customer_id`). This is a *conceptual* relationship in this read-only chapter; no permanent constraints are created by the lab.
- **Cardinality:** one customer can have many orders; an order belongs to one customer in this example.
- **Normalization:** storing the customer's name once avoids repeated copies in every order.
- **Join:** reconstructs related information when needed.
- **NULL:** represents a missing or unknown value, not an empty string or zero.
- **No guaranteed row order:** use `ORDER BY` when output order matters.

**Important distinction:** a primary key does not automatically imply that a table is physically stored in key order. Logical relationships and physical access paths are separate.

## 2. DBMS architecture and SQL request lifecycle (15 minutes)

A **DBMS** is the software that receives SQL, checks access, plans execution, coordinates transactions, manages storage, and returns results. A PostgreSQL deployment may be self-managed or hosted by a cloud provider; the core concepts remain useful across SQL platforms.

### Conceptual request path

```text
SQL client / application / BI tool
              |
              v
Network connection + authentication
              |
              v
PostgreSQL server process (session/backend)
              |
              v
Parse SQL -> analyze names/types -> rewrite -> plan/optimize
              |
              v
Executor -> buffer/cache & storage access -> rows returned
              |
              v
Client displays result
```

**What each stage does:**

1. **Connection:** the client connects to the PostgreSQL server and authenticates. The server authorizes access according to roles and privileges.
2. **Parsing and analysis:** PostgreSQL checks SQL syntax and resolves names and types. The query rewriter applies applicable rules, including view expansion.
3. **Planning:** the optimizer selects an execution strategy, considering statistics and available access paths.
4. **Execution:** the executor obtains rows using scans, joins, sorts, or aggregates; buffer and storage components support reads.
5. **Result delivery:** selected columns/rows are sent to the client. The client may then format the result.

This is a simplified lifecycle. Prepared statements, caching, parallel execution, and different SQL statement types introduce additional details.

### PostgreSQL 18 components: what beginners should recognize

| Component | Main responsibility | Practical DBRE/SRE relevance |
|---|---|---|
| Postmaster/main server | Accepts connections and coordinates server processes | Availability, connection limits |
| Client backend processes | Handle client sessions and execute statements | Sessions, long-running queries, locks |
| Shared buffers | Cache database pages in shared memory | Cache effectiveness and memory sizing |
| WAL (write-ahead log) | Logs changes for crash recovery and replication | Recovery, replication, disk capacity |
| Checkpointer | Writes checkpoint-related dirty buffers and records checkpoints | Write I/O and recovery considerations |
| Background writer | Helps write dirty shared buffers | Buffer management and write workload |
| Autovacuum workers | Reclaim reusable space and maintain visibility/statistics | Table bloat, transaction ID safety, planner estimates |
| WAL sender/receiver | Transfer WAL for physical streaming replication | Replication health and lag |
| Storage files and indexes | Persist table/index data and support access paths | Disk capacity, query performance |

**Safety nuance:** `SELECT` is read-only in intent, but it still consumes CPU, memory, I/O, and locks; catalog queries are not automatically harmless on a heavily loaded server. Use a disposable lab.

### Relational DBMS versus a single file

A CSV file stores rows but does not itself provide concurrent transactions, foreign-key enforcement, an SQL optimizer, a recovery log, or role-based access. PostgreSQL adds these services. A database is not merely a directory of tables.

### Logical vs. physical architecture

- **Logical:** databases, schemas, tables, columns, keys, views, and SQL.
- **Physical:** server processes, shared buffers, WAL, table/index files, disk, CPU, and network.
- **Operational:** monitoring, backup/restore, high availability, access control, and change management.

An index is a physical access structure; a foreign key is a logical integrity constraint. Both influence system behavior, but they solve different problems.

## 3. Worked examples (10 minutes)

All SQL below is **read-only**, uses in-query fictional rows, and creates no permanent objects. These are PostgreSQL 18 reference examples; most concepts are portable, but the `VALUES` table syntax and catalog functions vary by vendor.

### Example A — Explore the session

```sql
SELECT current_database() AS database_name,
       current_user AS role_name,
       current_setting('server_version') AS server_version;
```

**Expected:** one row; values depend on your lab. For the intended baseline, `server_version` begins with `18`. This statement does not verify the safety of the connected environment by itself; confirm the lab's host and credentials independently.

### Example B — Relate two logical tables

```sql
WITH customers(customer_id, customer_name) AS (
    VALUES (1, 'Ava'), (2, 'Noah'), (3, 'Mia')
),
orders(order_id, customer_id, amount_usd) AS (
    VALUES (101, 1, 40.00::numeric(10,2)),
           (102, 1, 25.00::numeric(10,2)),
           (103, 2, 15.00::numeric(10,2))
)
SELECT c.customer_name, o.order_id, o.amount_usd
FROM customers AS c
JOIN orders AS o ON c.customer_id = o.customer_id
ORDER BY o.order_id;
```

**Expected:**

| customer_name | order_id | amount_usd |
|---|---:|---:|
| Ava | 101 | 40.00 |
| Ava | 102 | 25.00 |
| Noah | 103 | 15.00 |

Mia is absent because this is an inner join and Mia has no order. The `WITH` datasets are temporary query expressions, not real tables with enforced keys.

### Example C — Preserve customers without orders

Use the same `WITH` definitions from Example B and change only the final query to:

```sql
SELECT c.customer_name, COUNT(o.order_id) AS order_count
FROM customers AS c
LEFT JOIN orders AS o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.customer_name
ORDER BY c.customer_id;
```

**Expected:** Ava = 2, Noah = 1, Mia = 0. `COUNT(o.order_id)` excludes NULL values from unmatched orders; `COUNT(*)` would count the preserved outer-join row and give Mia an incorrect count of 1.

### Example D — Observe database metadata (PostgreSQL-specific)

```sql
SELECT current_schema() AS default_schema,
       pg_backend_pid() AS backend_pid,
       current_setting('transaction_isolation') AS isolation_level;
```

**Expected:** one row with a schema name (often `public`, but it may be NULL), a positive process ID, and a transaction isolation setting (typically `read committed`). These are observational values, not fixed test fixtures.

## 4. Hands-on Lab 002 — Trace a relational query (15 minutes)

**Environment:** An isolated PostgreSQL 18 database accessed through `psql` or an approved SQL editor. If you have not completed the environment setup, save this exercise for Chapter 003. Use [the executable SQL file](../labs/002-relational-architecture.sql). It includes all common-table-expression definitions so each statement can run independently.

**Exercise sequence:**

1. Verify the approved lab connection using the environment's connection details and run Example A. Record the database name and server version, but do not publish connection secrets.
2. Run Example B. Confirm the three expected rows and explain why Mia is absent.
3. Run the complete left-join aggregation in the lab file. Confirm the counts **2, 1, 0**.
4. Run Example D. Record the isolation level and explain that it is a session setting, not a guarantee that a query is inexpensive.
5. Predict what happens if an order references customer `99` in the in-query `VALUES` dataset. An inner join will not return that order. Explain why this **does not** prove a foreign key exists or is enforced.
6. Run the optional query below on the lab connection only to inspect the current session:

```sql
SELECT pid, datname, usename, state
FROM pg_stat_activity
WHERE pid = pg_backend_pid();
```

**Expected:** your own session appears as one row when permitted. `state` is typically `active` while this statement runs. Do not query all sessions or terminate backends as part of this lab.

### Acceptance checks

- [ ] I can distinguish primary keys from foreign keys and joins.
- [ ] Example B returns exactly 3 rows.
- [ ] Left-join counts are Ava 2, Noah 1, Mia 0.
- [ ] I can identify the client, backend, planner, executor, buffers, and WAL in a request diagram.
- [ ] I can explain why a read-only query can still cause load.
- [ ] I can distinguish a logical constraint from a physical index.

### Troubleshooting

| Symptom | Likely reason | Safe response |
|---|---|---|
| Connection refused | Server/port not reachable | Complete Chapter 003 setup and check the isolated lab service |
| SQL syntax error | Incomplete CTE or missing parentheses | Run each full statement from the lab SQL file |
| Mia missing from left-join result | Used inner join instead | Verify `LEFT JOIN` and join direction |
| Mia has count 1 | Used `COUNT(*)` | Use `COUNT(o.order_id)` |
| Unexpected version | Connected to another PostgreSQL instance | Stop and verify approved lab endpoint before continuing |
| `pg_stat_activity` visibility limited | Monitoring privileges vary | Restrict to your own backend and request no elevated access |

**Cleanup:** None. The lab runs no `CREATE`, `INSERT`, `UPDATE`, `DELETE`, or `DROP` statements.

## 5. DBRE/SRE operational connection (5 minutes)

Suppose an application report slows down. The DBRE/SRE first separates possible causes:

| Layer | Example observation | Initial safe check |
|---|---|---|
| Client/network | Slow connection setup | Application timing and network telemetry |
| Sessions | Connection saturation | Approved connection metrics |
| Planner | Poor row estimates | Explain plan in a test environment |
| Executor/storage | High I/O or expensive join | Query metrics and plan evidence |
| Transaction/WAL | Long transactions or WAL growth | Approved transaction/WAL dashboards |

Do not assume every SQL performance issue requires a larger server. Verify the workload, SQL, query plan, data size, and concurrency first.

## Review questions and answer key

1. **What is the difference between a database and a DBMS?** A database is the organized data; a DBMS is the software managing it.
2. **Why separate customers and orders?** To reduce repeated customer attributes and represent one-to-many relationships.
3. **What does the planner do?** It chooses an execution strategy for a query.
4. **What does WAL help with?** Crash recovery and replication, among other change logging needs.
5. **Why did Mia disappear in the inner join?** No matching order exists.
6. **Why use `COUNT(o.order_id)` after a left join?** To count actual matching orders, excluding the NULL-extended row.

## Portability notes and references

The relational concepts apply broadly. PostgreSQL-specific functions include `pg_backend_pid()`, `current_setting()`, and the `pg_stat_activity` view. Cast syntax `::numeric` is PostgreSQL-specific; portable code often uses `CAST(value AS DECIMAL(10,2))`. Query optimizers, transaction defaults, and architecture differ across PostgreSQL, MySQL, SQL Server, Snowflake, and BigQuery.

- [PostgreSQL 18 — SQL language](https://www.postgresql.org/docs/18/sql.html)
- [PostgreSQL 18 — Tutorial: SQL language](https://www.postgresql.org/docs/18/tutorial-sql.html)
- [PostgreSQL 18 — How connections are established](https://www.postgresql.org/docs/18/connect-estab.html)
- [PostgreSQL 18 — Query planning](https://www.postgresql.org/docs/18/planner-optimizer.html)
- [PostgreSQL 18 — Server processes](https://www.postgresql.org/docs/18/process-title.html)
- [PostgreSQL 18 — Monitoring statistics](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [PostgreSQL 18 — WAL introduction](https://www.postgresql.org/docs/18/wal-intro.html)

**Next:** Chapter 003 — Set up the SQL Lab: PostgreSQL 18, Docker, and SQL Clients (publication pending).

**Validation status:** Examples and expected outcomes were reasoned through and checked for read-only behavior. No isolated PostgreSQL 18 execution evidence has been collected; runtime validation remains **pending**.
