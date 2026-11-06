# Chapter 01 — PostgreSQL Fundamentals and Architecture

**Audience:** Beginner DBRE/SRE and Database Engineers  
**Duration:** ~60 minutes  
**Platform:** Any host with Docker Desktop or Docker Engine for the first lab  
**Runtime target:** PostgreSQL 17 container for a reproducible teaching example; production environments may use different supported versions  
**State:** Authored; runtime lab **not** executed / certified

[Learning path](../README.md) · [Chapter 01 lab](../labs/chapter-01/README.md) · [Progress](../STATUS-TRACKER.md)

## 1. Learning outcomes (5 minutes)

After this chapter, participants should be able to:
1. distinguish PostgreSQL instance, database, schema, table, row, column, primary/foreign keys and indexes;
2. explain how an application connects to PostgreSQL;
3. describe transactions, MVCC, WAL, checkpoints and autovacuum at a high level;
4. run safe database-health queries;
5. provision a disposable lab and verify a logical backup restores successfully.

## 2. Why this matters for enterprise DBRE/SRE (5 minutes)

An enterprise Postgres team designs, configures and maintains databases that support applications. Operational ownership varies by deployment platform.

| Dimension | Bare metal / VM | AWS RDS | Kubernetes |
|---|---|---|---|
| Operating system & storage | DB/platform team | AWS-managed | Kubernetes node/storage platform team |
| PostgreSQL configuration | DB team | DB team via supported parameter groups | DB/operator controllers with platform team |
| Backup implementation | DB team | RDS features with customer-managed policy and validation | Operator and backup components with DB/platform team |
| High availability | DB/platform team designs and tests | RDS deployment mode is decisive | Operator + persistent storage + fencing design |
| Application schema & SQL | Application/DB joint ownership | Application/DB joint ownership | Application/DB joint ownership |

The responsibility boundary changes, but application performance, database design, restore validation, and lifecycle governance still require engineering decisions.

## 3. Core concepts (10 minutes)

- **PostgreSQL instance/cluster:** a running PostgreSQL server environment with a data directory and one or more databases. In PostgreSQL terminology a database cluster is a set of databases managed by a server; this is not automatically a distributed HA cluster.
- **Database:** logical container for schemas and objects; e.g. `appdb`.
- **Schema:** namespace for tables/views/functions; e.g. `public`.
- **Table:** row/column relation storing application data; e.g. `orders`.
- **Row:** one record; e.g. order #101.
- **Column:** named attribute with a data type; e.g. `amount NUMERIC(12,2)`.
- **Primary key:** unique, not-null identifier of a row.
- **Foreign key:** enforces a reference to another table's key.
- **Index:** access structure for certain queries; speeds some reads, adds storage and write overhead.
- **Transaction:** atomic unit of work, committed or rolled back as a unit.
- **ACID:** atomicity, consistency, isolation, durability.

Illustrative data hierarchy:

```text
PostgreSQL instance
└── database: appdb
    └── schema: public
        ├── table: customers
        │   ├── customer_id (primary key)
        │   └── email
        └── table: orders
            ├── order_id (primary key)
            ├── customer_id (foreign key)
            └── amount
```

## 4. Internal architecture (10 minutes)

```text
Application / psql
      |
TCP connection / authentication
      |
PostgreSQL postmaster + backend processes
      |
+-----------------------+-------------------+
| Shared memory         | Background work   |
| shared_buffers        | checkpointer      |
| WAL buffers           | background writer |
| locks and statistics  | WAL writer        |
+-----------------------+-------------------+
      |
Persistent storage: table/index files + WAL
```

- **Shared buffers** cache PostgreSQL data pages.
- **WAL** is write-ahead logging: changes are logged before relevant data pages are persisted, enabling crash recovery and supporting replication.
- **MVCC** provides row versions and transaction snapshots that support concurrency without making readers block ordinary writers in many common cases.
- **Checkpoints** coordinate dirty-page flushing and help limit crash-recovery work.
- **Autovacuum** recovers reusable storage from obsolete row versions and maintains statistics; it also helps prevent transaction ID wraparound.

**Do not assume:** more shared buffers always improves performance, an index always accelerates a query, or a replica is automatically available for writes.

## 5. Hands-on lab (25 minutes)

Use the [fully reproducible Chapter 01 lab](../labs/chapter-01/README.md).

### Lab activities

1. Start PostgreSQL 17 bound to the local loopback interface.
2. Check `pg_isready` and connect with `psql`.
3. Create a two-table customer/order model and insert sample data.
4. Compare `EXPLAIN (ANALYZE, BUFFERS)` before and after an index.
5. Demonstrate `BEGIN`, `ROLLBACK`, and `COMMIT`.
6. Query PostgreSQL version, session health, configuration and storage statistics.
7. Take a logical backup with `pg_dump` and restore it to an isolated database.

For efficiency, the instructor may run restore demonstration after class; the actual runtime verification requirement remains unchanged.

## 6. Application consulting scenario (5 minutes)

A service team requests a data store for 50,000 customer orders and expects recurring updates to order statuses.

Discuss:
- Why is PostgreSQL a sensible starting point for strongly consistent relational order data?
- Which columns need indexes for the application queries?
- What connection concurrency and write rate are expected?
- What are the SLO, RPO, RTO, retention and regulatory requirements?
- Which deployment environment (bare metal, AWS RDS, Kubernetes) has an existing platform team and operational standard?

**Design output:** one-paragraph recommendation with assumptions and open questions. Avoid selecting a platform based solely on familiarity.

## 7. Acceptance

Mark this chapter `Lab verified` only after retaining:
- PostgreSQL version, container image version/tag and lab environment details;
- proof of a healthy connection and successful sample dataset creation;
- two query plans and a brief explanation of differences;
- transaction rollback evidence;
- database health-query output;
- independent logical restore and row-count evidence;
- sanitized logs and reviewer acknowledgement.

A successful `pg_dump` is **not** proof of disaster-recovery readiness or point-in-time recovery.

## 8. Troubleshooting

| Symptom | Check | Safe next step |
|---|---|---|
| Docker daemon unavailable | `docker info` | Start Docker Desktop / verify container mode |
| Port 55432 occupied | `docker ps`, host port listing | Use an unused local port |
| Connection refused | `docker logs pg-fleet-lab`; `pg_isready` | Validate container startup and mapping |
| SQL fails with permission error | `SELECT current_user;` | Connect as designated lab administrator |
| Sequential scan after index creation | Compare row estimates and table size | Do not force index usage without evidence |
| Restore produces errors | Review `pg_restore` output and target DB state | Repeat restore into a fresh disposable database |

## 9. Official references and further reading

- [PostgreSQL tutorial](https://www.postgresql.org/docs/18/tutorial.html)
- [PostgreSQL MVCC](https://www.postgresql.org/docs/18/mvcc.html)
- [PostgreSQL WAL](https://www.postgresql.org/docs/18/wal.html)
- [PostgreSQL statistics](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [pg_dump](https://www.postgresql.org/docs/18/app-pgdump.html)
- [pg_restore](https://www.postgresql.org/docs/18/app-pgrestore.html)
- Deeper existing chapters: [PostgreSQL architecture](../../chapters/002-architecture-processes-memory-storage-and-wal.md), [operations lab](../../chapters/004-build-a-reproducible-postgresql-operations-lab.md).
