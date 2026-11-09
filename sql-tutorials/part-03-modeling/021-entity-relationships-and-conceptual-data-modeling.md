# Chapter 021 — Entity Relationships and Conceptual Data Modeling

> [Master TOC](../MASTER-TOC.md) · [Learning path](../README.md) · [Previous: 020](../part-02-filtering/020-lab-02-filter-and-rank-operational-records.md) · [Next: 022](../MASTER-TOC.md)
>
> **Part 03 · 60 minutes · SQL concepts portable; companion lab targets PostgreSQL 18**
>
> **Validation:** Authored; targeted static review only. Independent editorial review, comprehensive SQL syntax verification and isolated PostgreSQL 18 execution pending.

## Learning outcomes and prerequisites (0–5 minutes)

After this chapter, you should be able to identify entities and attributes from requirements, name a table's **grain**, distinguish business identifiers from database keys, classify one-to-one, one-to-many and many-to-many relationships, describe optional participation, and translate a conceptual model into a candidate relational design without prematurely choosing database-specific DDL. Prerequisites: [tables and rows (004)](../part-01-fundamentals/004-databases-schemas-tables-rows-columns.md), [keys and relationships (005)](../part-01-fundamentals/005-records-relationships-keys-and-relational-terminology.md), and [Lab 02 (020)](../part-02-filtering/020-lab-02-filter-and-rank-operational-records.md).

| Time | Activity |
|---|---|
| 0–5 min | Goals, requirements, safety |
| 5–15 min | Entities, attributes, grain, keys |
| 15–30 min | Relationships and worked model |
| 30–50 min | Guided read-only SQL lab and design exercise |
| 50–55 min | Validation, pitfalls and operational controls |
| 55–60 min | Review questions and answers |

## Concepts (5–15 minutes)

**Conceptual modeling** describes what the business needs to represent, not SQL syntax. An **entity** is a distinguishable thing (Customer, Order, Product). An **attribute** describes it (Customer email, Order placed_at). A **relationship** expresses a business rule (a Customer places Orders). A **business key** is meaningful to the domain (external order number); a **surrogate key** is an internally assigned identifier. A **primary key** uniquely identifies a relational row; a **foreign key** is a constraint used in a later logical/physical implementation to enforce a reference. Conceptual diagrams need not commit to integer IDs or a particular database.

**Grain** answers: “What does one row mean?” For example, one row per order is different from one row per product line in an order. A model without a declared grain can produce incorrect counts and join fan-out. Cardinality describes how many instances can participate: 1:1, 1:N or M:N. Optionality describes whether participation can be zero (0..1 or 0..N) rather than mandatory (1 or 1..N). Specify rules from requirements rather than assuming them from sample rows.

**Fictional retail requirement:** Customers can register without ordering. Each order belongs to exactly one customer. An order may have zero or more line items while it is a draft. Each line item references exactly one product; a product can appear on many orders. A customer's email can change and must not be treated as a permanent identity key. Product prices can change; an order line must retain its agreed unit price.

## Worked conceptual model (15–30 minutes)

| Entity | Grain | Illustrative attributes | Candidate identifier |
|---|---|---|---|
| Customer | One customer account | customer_code, display_name, email | customer_code |
| Order | One checkout/order | order_number, placed_at, status | order_number |
| OrderLine | One product occurrence on an order | line_number, quantity, agreed_unit_price | (order_number, line_number) |
| Product | One catalog product | sku, description, current_price | sku |

```text
Customer (1) -------- (0..N) Order
Order    (1) -------- (0..N) OrderLine
Product  (1) -------- (0..N) OrderLine
```

The conceptual many-to-many relationship between **Order** and **Product** is resolved through **OrderLine**, which carries quantity and the agreed price. The OrderLine business key is scoped to its parent order. Avoid storing comma-separated product IDs in an Order record. A nullable customer identifier on an order would contradict the stated “exactly one customer” rule. Conversely, requiring every customer to have an order would contradict the optionality requirement.

**Concrete synthetic example:** Customer C01 places order O100. That order has line 1 for SKU-A, quantity 2 at 12.50 each, and line 2 for SKU-B, quantity 1 at 7.00. The order-line extended total is 32.00, while there is only **one** order. Joining orders to lines and then counting orders without `DISTINCT` produces two joined rows, not two orders.

### Logical mapping, not yet DDL

A later physical schema could use `customers(customer_id PK, customer_code UNIQUE, ...)`, `orders(order_id PK, customer_id FK, order_number UNIQUE, ...)`, `products(product_id PK, sku UNIQUE, ...)`, and `order_lines(order_id FK, line_number, product_id FK, quantity, agreed_unit_price, PRIMARY KEY(order_id,line_number))`. The exact SQL and enforcement choices belong to Chapters [022](../MASTER-TOC.md)–[026](../MASTER-TOC.md). The conceptual business rules come first.

**Portable SQL vs PostgreSQL:** `SELECT`, `JOIN`, `GROUP BY`, `COUNT`, and `SUM` are broadly portable; literal `VALUES` in a `FROM` clause and `WITH` are widely supported but details differ. The companion lab uses PostgreSQL-specific `DO`, `current_setting`, and `::` casts for environment checks. It does **not** create tables or enforce foreign keys; the relationship tests illustrate data-quality checks, not a replacement for constraints.

## Hands-on lab (30–50 minutes)

Use only an independently verified **disposable** PostgreSQL 18 instance with a database named `sql_tutorials`. The name/version check is an additional safeguard, not proof of isolation. Never use production credentials. The companion [SQL lab](../labs/021-entity-relationships-conceptual-modeling.sql) uses inline synthetic data in a read-only transaction and leaves no objects behind.

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/021-entity-relationships-conceptual-modeling.sql
```

1. **Identify grain:** Explain why counting line rows does not count orders. Expected: two lines, one order in the example above.
2. **Inspect participation:** Identify customers with no orders. Expected: C03.
3. **Check relationship integrity:** Detect an orphan order (customer code absent from the customer set). Expected: none.
4. **Compute line totals:** Multiply quantity by agreed unit price; aggregate by order. Expected O100 = 32.00, O101 = 15.00.
5. **Practice modeling:** Sketch a support-ticket system with Ticket, Service, and TicketEvent. Define each grain, optionality, and whether one Ticket can have many events. Discuss what an immutable event ID provides to an incident audit trail.

The lab performs assertions and fails if the expected synthetic result differs. It does not certify the design against real workloads.

## Troubleshooting and safety (50–55 minutes)

| Symptom | Likely cause | Safe next step |
|---|---|---|
| Orders are overcounted after a join | OrderLine has a different grain | Count distinct order identifiers or aggregate lines first |
| Missing customers in reports | INNER JOIN removes customers with no orders | Consider LEFT JOIN and explicit NULL handling |
| Orphan references | Ingestion skipped referential checks | Quarantine suspect records; add constraints in isolated testing |
| Price history changes unexpectedly | Report uses current catalog price | Store agreed unit price on each order line |
| Duplicate line numbers | Unclear key scope | Define uniqueness within each order |
| Lab refuses to run | Wrong PostgreSQL version or database | Verify isolated instance; do not bypass guards |

**DBRE/SRE controls:** Treat cardinality assumptions as testable data contracts. Assess index and foreign-key overhead in later chapters. Do not deploy schema changes based solely on a diagram; use change review, backups, staging migration rehearsals and rollback plans. For healthcare-like datasets, use only synthetic records; a patient identity model requires explicit privacy, lifecycle and historical-update rules.

## Review questions with answers (55–60 minutes)

1. **What is grain?** The meaning of a single row, e.g. one OrderLine rather than one Order.
2. **Can a customer have zero orders?** Yes; the requirement specifies optional customer participation (0..N orders).
3. **Why is OrderLine a separate entity?** It resolves the M:N order/product relationship and stores relationship attributes such as quantity and agreed price.
4. **Is email a reliable customer primary key?** Usually not; it may change or be reused. Use a stable identifier with a separate uniqueness policy.
5. **Why can a join inflate order counts?** One order matches multiple lines, yielding multiple result rows.
6. **Does a read-only query prove referential integrity?** No; it checks a snapshot. Actual integrity enforcement requires appropriate constraints and operational controls.

## References and next chapter

- [PostgreSQL 18 — Table constraints](https://www.postgresql.org/docs/18/ddl-constraints.html)
- [PostgreSQL 18 — Table expressions and joins](https://www.postgresql.org/docs/18/queries-table-expressions.html)
- [PostgreSQL 18 — WITH queries](https://www.postgresql.org/docs/18/queries-with.html)

Next: **022 — CREATE DATABASE, CREATE SCHEMA, and CREATE TABLE** ([Master TOC](../MASTER-TOC.md)). That chapter will distinguish disposable lab DDL from production migration procedures.
