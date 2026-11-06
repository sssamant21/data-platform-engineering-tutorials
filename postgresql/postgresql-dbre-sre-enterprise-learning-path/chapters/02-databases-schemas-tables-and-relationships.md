# Chapter 02 — Databases, Schemas, Tables, Columns, Rows and Relationships

**Level:** Beginner DBRE/SRE · **Duration:** 60 minutes · **Reference runtime:** PostgreSQL 17 · **State:** Authored; lab execution pending

[Learning path](../README.md) · [Master TOC](../MASTER-TOC.md) · [Chapter 02 lab](../labs/chapter-02/README.md) · [Progress](../STATUS-TRACKER.md)

## 1. Why this matters to a database engineer

Application teams often ask the Postgres team to create "a database." Before provisioning anything, an engineer must determine the logical data model, ownership boundary, relationships and constraints. A structurally valid relational design prevents data anomalies and makes ongoing operations less risky.

**Outcome:** design a small order-management schema, implement it safely in a disposable lab, explain referential integrity, and identify operational implications of design choices.

## 2. 60-minute lesson plan

| Minutes | Activity | Evidence |
|---|---|---|
| 0–10 | Database hierarchy and data types | Explain object ownership |
| 10–20 | Keys, constraints, cardinality and normalization | Sketch a data model |
| 20–30 | DBRE/SRE design and production considerations | Design review answers |
| 30–52 | Execute [Chapter 02 lab](../labs/chapter-02/README.md) | Tables, rows, joins, constraint behavior |
| 52–60 | Acceptance checks and troubleshooting | Evidence checklist |

## 3. PostgreSQL object hierarchy

```text
PostgreSQL server / cluster
├── database: postgres
└── database: training_ch02
    └── schema: retail_lab
        ├── customers
        ├── products
        ├── orders
        └── order_items
```

- **Server/cluster:** a PostgreSQL instance with a data directory and its databases. A database server does not automatically mean an HA cluster.
- **Database:** isolation boundary for logical objects and connections. A PostgreSQL connection targets one database; you cannot directly join tables across databases with ordinary SQL.
- **Schema:** namespace inside a database. For example, `retail_lab.customers` names the `customers` table in schema `retail_lab`.
- **Table:** relational collection with columns, constraints and rows.
- **Column:** named typed attribute, such as `amount NUMERIC(12,2)`.
- **Row:** one record.
- **Primary key (PK):** uniquely identifies each row; implies uniqueness and no nulls.
- **Foreign key (FK):** ensures values reference an existing parent key, subject to the declared FK behavior.
- **Index:** data structure supporting selected lookup/order operations; adds disk and write maintenance overhead.
- **Sequence/identity:** PostgreSQL can generate surrogate keys with `GENERATED ... AS IDENTITY`. Identity values are not guaranteed gap-free and gaps are normal.

### Data type selection

| Type | Suitable use | Operational consideration |
|---|---|---|
| `BIGINT` | Long-lived surrogate identifiers | Fixed-width integer; consider lifetime volume |
| `TEXT` | Email, names, labels | Apply length or format constraints only when justified |
| `NUMERIC(12,2)` | Exact financial amounts | Avoid floating-point rounding for currency |
| `TIMESTAMPTZ` | Event timestamps | Stores instants; render in a chosen timezone |
| `BOOLEAN` | True/false flag | Consider whether "unknown" is allowed |
| `JSONB` | Flexible semi-structured fields | Do not automatically replace well-defined relational columns |

**Application design tip:** use `TIMESTAMPTZ` with explicit UTC handling at integration boundaries, and document client-local presentation requirements. Database time zone is a session setting, not a substitute for timestamp semantics.

## 4. Relationships and normalization

The sample model has:

- One customer **to many** orders.
- One order **to many** order items.
- One product **to many** order items.

```text
customers (customer_id PK)
        1
        |
        | many
orders (order_id PK, customer_id FK)
        1
        |
        | many
order_items (order_id FK, line_no, product_id FK, quantity, unit_price)
        |
        | many to one
products (product_id PK, sku UNIQUE, unit_price)
```

The `order_items` table also stores **unit_price at time of purchase**. This is deliberate: a change to the catalog price must not silently rewrite past orders. Capture the business meaning of snapshot fields.

### Why not one huge table?

Combining customer email, order status, product name and quantity into every line item repeats data, complicates updates and creates anomalies. A normalized design separates entities and establishes relationships through keys.

Normalization helps, but it is not an absolute performance rule. Denormalization requires a documented workload reason, data ownership, and a strategy for keeping duplicated fields consistent.

## 5. Declarative constraints versus application checks

| Mechanism | Protects against | Example |
|---|---|---|
| `NOT NULL` | Missing required values | Every order has a customer ID |
| `PRIMARY KEY` | Duplicate entity IDs | One order ID per order |
| `UNIQUE` | Duplicate business keys | Customer email, product SKU |
| `FOREIGN KEY` | Orphan references | Order must reference an existing customer |
| `CHECK` | Invalid domain values | Quantity > 0 and price >= 0 |
| `DEFAULT` | Unspecified initial value | Status is `created` |
| Transaction | Partial multi-statement change | Order plus its items commit together |

**Important:** a `CHECK` alone cannot generally verify values in another table; use keys, foreign keys or a designed transaction for cross-row and cross-table business rules.

## 6. Design review questions for application teams

Before approving the physical schema, ask:

1. What operations read or update this data, and with what expected rate and concurrency?
2. What makes an entity unique (customer email might change; perhaps tenant + external ID is the business key)?
3. Should a customer be deleted if it has historical orders? In this lab, the default FK behavior prevents deleting a referenced customer.
4. Are canceled orders retained? What are retention and data-protection requirements?
5. How do price and status changes affect historical correctness?
6. What are query shapes for customer-order lookup and reporting?
7. Who owns DDL changes and reviews index/constraint migrations?
8. What are the required RPO/RTO, availability, growth, and backup expectations?
9. Is the workload naturally transactional, or should analytical copies and aggregates live elsewhere?

### Multi-tenant design note

A tenant-aware service must prevent cross-tenant reference leaks. Tenant identifiers in tables alone are insufficient: consider composite constraints, careful query patterns, privileges, and row-level security after threat modeling. Do not use this training schema as a production security design.

## 7. Database-engineering operational implications

- **DDL changes:** some table and constraint operations lock objects. Assess lock duration, table size, and migration behavior before production changes.
- **Indexes:** unique and primary-key constraints create indexes, but foreign-key referencing columns are **not automatically indexed**. Select FK indexes based on query workload and parent-delete/update patterns.
- **Data growth:** line-item tables may grow faster than parent entities; measure rows/day, average row size and index footprint.
- **Backups:** a successful backup alone is not recovery evidence; restore and verify in isolation.
- **Privacy:** sample data is synthetic. In real systems, mask sensitive records and enforce least-privilege access.
- **Identity:** identity sequences can produce gaps and should not be treated as an audit sequence or proof of transaction count.
- **Platform choice:** bare metal, RDS and Kubernetes each require the same logical data correctness, but different operational ownership and deployment controls.

## 8. Hands-on exercise

Follow [Chapter 02 lab](../labs/chapter-02/README.md) to:
1. verify the disposable PostgreSQL instance;
2. create `training_ch02` and `retail_lab` without touching `appdb` from Chapter 01;
3. create four relational tables with PK, FK, UNIQUE, CHECK and DEFAULT;
4. load a deterministic order and calculate its total;
5. demonstrate that invalid quantity and an orphan customer ID are rejected;
6. read catalogue metadata and assess relationship indexes;
7. capture table sizes and explain the production growth implications.

The lab uses a **separate database** and does not delete existing databases.

## 9. Acceptance checklist

- [ ] Explain database, schema, table, row and column using an example.
- [ ] Draw the four-table relationship diagram and identify PK/FK columns.
- [ ] Create the database objects in a disposable environment.
- [ ] Read the expected one-order aggregate total.
- [ ] Observe and explain two safe constraint rejection tests.
- [ ] Identify which indexes are created automatically versus manually.
- [ ] Record size and object metadata queries.
- [ ] Save sanitized evidence of actual runtime execution, if performed.

**Status policy:** This chapter is *authored*; no live PostgreSQL runtime validation or independent review has been completed in this publication step.

## 10. Troubleshooting

| Symptom | Why it happens | Safe action |
|---|---|---|
| `database "training_ch02" already exists` | Lab was run earlier | Reuse after verifying its purpose; do not drop automatically |
| `relation already exists` | DDL is being repeated | Inspect `\dt retail_lab.*` before applying anything |
| Foreign-key violation | Parent row absent | Inspect reference values; do not disable FK enforcement |
| Unique violation | Duplicate email or SKU | Review business key, don't remove constraint blindly |
| Unexpected order count | Existing demo data | Check database/schema and rerun in a newly named disposable database |
| Query ignores index | Small table or planner estimates | Compare `EXPLAIN`; don't force plan solely for demo |

## 11. References and deeper reading

- [PostgreSQL 18: Creating a Database](https://www.postgresql.org/docs/18/manage-ag-createdb.html)
- [PostgreSQL 18: Schemas](https://www.postgresql.org/docs/18/ddl-schemas.html)
- [PostgreSQL 18: Constraints](https://www.postgresql.org/docs/18/ddl-constraints.html)
- [PostgreSQL 18: Identity Columns](https://www.postgresql.org/docs/18/ddl-identity-columns.html)
- [PostgreSQL 18: Data Types](https://www.postgresql.org/docs/18/datatype.html)
- [Existing extended PostgreSQL index track](../../chapters/031-b-tree-and-other-index-types-operational-tradeoffs.md)
