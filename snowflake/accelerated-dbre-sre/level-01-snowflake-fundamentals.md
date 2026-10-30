# Level 1 — Snowflake Fundamentals

**Track:** Snowflake Accelerated DBRE/SRE | **Duration:** 60 minutes | **Status:** DRAFT — static review pending; live Snowflake validation NOT RUN  
**Audience:** All stakeholders, new DBRE/SRE engineers, analysts, developers, and data engineers  
**Prerequisites:** Authorized Snowflake training account; basic SQL recommended for Levels 2–7.

## Learning objectives
Explain what Snowflake does, its architecture, and basic database objects; complete a small SQL exercise.

## 60-minute lesson plan
| Topic | Time |
|---|---:|
| What Snowflake is and OLAP vs OLTP | 10 min |
| Storage, compute and cloud services | 10 min |
| Accounts, databases, schemas, objects and SQL | 15 min |
| Guided beginner lab | 20 min |
| Knowledge check and recap | 5 min |
| **Total** | **60 min** |

## Core concepts
### What Snowflake is
Snowflake is a managed cloud data platform for analytics, transformations, reporting and data sharing. It runs on supported cloud providers. Unlike a self-managed PostgreSQL or MongoDB server, its underlying infrastructure is managed by Snowflake. Its core strength is analytical (OLAP) workloads, not replacing every transactional (OLTP) system.

### Architecture in one diagram
~~~text
Users / BI / applications / pipelines
              |
        Cloud services
    Auth + metadata + optimizer
              |
    Virtual warehouses (compute)
    ETL_WH    ANALYTICS_WH
              |
    Centralized managed storage
     Databases and tables
~~~
**Storage** keeps the data; **virtual warehouses** execute SQL workloads; **cloud services** handle coordination, authentication, metadata and query optimization. Compute and storage scale independently.

### Database building blocks
An **account** contains warehouses, users, roles and databases. A **database** contains **schemas**; schemas contain **tables**, **views**, stages and other objects. A **table** has **rows** (records) and **columns** (attributes). Common types include NUMBER, VARCHAR, DATE, TIMESTAMP and VARIANT. A **view** stores a query definition instead of storing another full table copy.

Example name: \`DBRE_SRE_LAB.TRAINING.ORDERS\` represents database.schema.table.

### Common workflows
A source exports data or streams changes to Snowflake; ingestion loads it into tables; transformations prepare analytical datasets; dashboards and applications query them. Important features include COPY INTO, Snowpipe, streams, tasks, Time Travel and RBAC. Learn what each is for before administering it.

### SQL concepts
- SELECT chooses columns, WHERE filters rows, GROUP BY aggregates, and ORDER BY sorts results.
- COUNT counts rows; SUM adds numeric values. A join combines related tables.
- Warehouses are compute and incur usage charges while running; set a small approved training warehouse before running SQL.

## Hands-on lab and expected results
### Prerequisites
Use Snowsight and a designated **training** warehouse. For the CREATE TABLE exercise, use an existing scratch database/schema where your training role has CREATE TABLE privileges. Do not create tables in production schemas.

### Step 1 — Confirm session context (read-only)
~~~sql
SELECT CURRENT_USER(), CURRENT_ROLE(),
       CURRENT_WAREHOUSE(), CURRENT_DATABASE(), CURRENT_SCHEMA();
~~~
Expected: your active context; some values can be NULL until selected.

### Step 2 — A SELECT that needs no persistent table
~~~sql
SELECT column1 AS region, column2 AS amount
FROM VALUES ('EAST',120),('WEST',80),('EAST',50);
~~~
Expected: three rows, two columns.

### Step 3 — Create data only in your approved scratch schema
~~~sql
CREATE TEMP TABLE DBRE_SRE_L1_ORDERS (
  ORDER_ID NUMBER, REGION VARCHAR, AMOUNT NUMBER(10,2)
);
INSERT INTO DBRE_SRE_L1_ORDERS VALUES
  (1,'EAST',120),(2,'WEST',80),(3,'EAST',50);
SELECT REGION, COUNT(*) AS NUM_ORDERS, SUM(AMOUNT) AS SALES
FROM DBRE_SRE_L1_ORDERS
GROUP BY REGION ORDER BY REGION;
~~~
Expected: EAST has 2 orders, sales 170; WEST has 1 order, sales 80. The temporary table is session-scoped. The CREATE command intentionally fails if the name is already in use: do not replace an existing object. Use a fresh session or a new uniquely named scratch table for a re-run. The temporary table disappears when the session ends.

### Step 4 — Explain the result
Identify the database, schema, table, three columns, three rows, and the warehouse used. **Pass:** correct counts and an explanation of why the warehouse—not the table—provides compute.

## DBRE/SRE troubleshooting quick reference
| Symptom | Initial check | Interpretation |
|---|---|---|
| No warehouse selected | CURRENT_WAREHOUSE() | Select an approved training warehouse |
| Object does not exist | CURRENT_DATABASE()/SCHEMA() | Check name and session context |
| SQL access denied | CURRENT_ROLE() | Request least-privilege access from owner |
| Query unexpectedly slow | Query History | Compare query time versus baseline |

Do not attempt to fix lab permissions by switching to ACCOUNTADMIN. Use the approved training role.

## Knowledge check (with answers)
1. **What are Snowflake's three main layers?** Storage, compute, cloud services.
2. **What is a schema?** A logical container inside a database.
3. **What runs SQL?** A virtual warehouse.
4. **Does a view normally store separate rows?** No, it stores a query definition.
5. **What does GROUP BY do?** Aggregates records by grouping keys.

## Operational safety and validation
- Use a **designated lab account/warehouse** and synthetic data. Protect query-history text and any personal or customer information.
- SQL that creates/changes warehouse, roles, objects, retention or data requires appropriate role, approval and isolated test scope.
- Expected outcomes describe intended behavior, **not proof of execution**. No SQL was run against live Snowflake when authoring this lesson.
- If a command is not applicable to the account edition or current role, document the limitation rather than escalating privileges.
- **Acceptance:** instructor checks concepts, learner documents observed output, and a separate runtime review confirms SQL syntax/permissions and clean-up.

## Continue into the full 90-chapter curriculum
[01 Fundamentals](../01-snowflake-fundamentals.md), [03 Database Objects](../03-databases-schemas-tables-objects.md), [10 SQL Fundamentals](../10-sql-fundamentals-joins-ctes-window-functions.md)

## Official documentation
- https://docs.snowflake.com/en/user-guide/intro-key-concepts
- https://docs.snowflake.com/en/user-guide/warehouses-overview

[Back to accelerated track index](README.md) | [Validation tracker](STATUS.md)
