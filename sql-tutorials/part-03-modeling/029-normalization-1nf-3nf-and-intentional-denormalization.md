# Chapter 029 — Normalization (1NF–3NF) and Intentional Denormalization

> [Master TOC](../MASTER-TOC.md) · [Learning path](../README.md) · [Previous: 028](028-alter-table-rename-operations-and-safe-schema-changes.md) · [Next: 030](../MASTER-TOC.md)
>
> **Part 03 · 60 minutes · PostgreSQL 18 read-only lab**
>
> **Status:** Authored; targeted static reasoning only. Independent editorial review, comprehensive SQL syntax checks, and actual isolated PostgreSQL 18 runtime validation pending.

## Learning objectives and agenda (0–5 minutes)

By the end, identify a table's grain and functional dependencies; explain first, second and third normal forms; separate customers, orders, and order items; detect update/insert/delete anomalies; and justify selective denormalization with reconciliation controls. Prerequisites: [021 — relationships](021-entity-relationships-and-conceptual-data-modeling.md), [024 — keys](024-primary-keys-natural-keys-surrogate-keys-and-unique.md), and [025 — foreign keys](025-foreign-keys-and-referential-integrity.md).

| Minutes | Activity |
|---|---|
| 0–5 | Outcomes, data grain and safe environment |
| 5–15 | Functional dependencies, 1NF, 2NF, 3NF |
| 15–30 | Walkthrough: normalize a retail export |
| 30–50 | Hands-on read-only SQL lab and design exercises |
| 50–55 | Validation, tradeoffs and troubleshooting |
| 55–60 | Review questions and references |

## Concepts (5–15 minutes)

**Grain** means what one row represents. A functional dependency `A → B` means that a particular A value determines one B value in the modeled domain. It is a business rule, not merely a coincidence in sample rows. For example, in a current-customer table, `customer_id → customer_name`; a name does not necessarily identify a unique customer.

- **1NF:** Each row-column intersection contains a single value from its column domain; avoid repeated product columns or comma-separated lists. SQL arrays/JSON may be legitimate features, but they do not replace a normalized relational design for line-item queries.
- **2NF:** In 1NF, and each non-prime attribute depends on the whole of every candidate key, not just part of a composite candidate key. For an order-line key `(order_id, line_no)`, `product_name` determined solely by `product_id` belongs in a product table, not duplicated per line.
- **3NF:** In 2NF, and no non-prime attribute depends transitively on a candidate key through another non-prime attribute (formal 3NF: for each nontrivial FD X → A, X is a superkey or A is prime). If `order_id → customer_id` and `customer_id → customer_name`, store the customer's current name with the customer, not on each order.

**Important:** A product price at the time of sale is a historical *line-item fact*, not necessarily the current catalog price. Preserve `unit_price_at_sale` on order items; do not normalize away required historical meaning. Likewise, an explicitly modeled order shipping-address snapshot can be correct even if customer addresses change.

### Why it matters

An unnormalized export might contain:

| order_id | customer_id | customer_name | line_no | product_id | product_name | qty | unit_price_at_sale |
|---|---|---|---|---|---|---:|---:|
| 100 | 1 | Ada | 1 | P10 | Keyboard | 2 | 25.00 |
| 100 | 1 | Ada | 2 | P20 | Mouse | 1 | 10.00 |
| 101 | 2 | Ben | 1 | P10 | Keyboard | 1 | 25.00 |

The export's grain is **one order line**, not one order. Repeating customer and product labels creates update anomalies (change Ada in only one row), insertion anomalies (cannot represent a product with no orders), and deletion anomalies (deleting the last order line could remove the only copy of a product description).

## Walkthrough: normalized model (15–30 minutes)

A practical 3NF-oriented design separates four relations:

| Relation | Key | Meaning |
|---|---|---|
| customers | customer_id | One current customer |
| products | product_id | One current catalog product |
| orders | order_id | One order, with customer_id foreign key |
| order_items | (order_id, line_no) | One line; product_id foreign key, quantity and historical sale price |

**Portable SQL illustration** (run DDL only in a disposable database; syntax and constraint semantics vary by vendor):

```sql
CREATE TABLE customers (
  customer_id INTEGER PRIMARY KEY,
  customer_name VARCHAR(100) NOT NULL
);
CREATE TABLE products (
  product_id VARCHAR(10) PRIMARY KEY,
  product_name VARCHAR(100) NOT NULL
);
CREATE TABLE orders (
  order_id INTEGER PRIMARY KEY,
  customer_id INTEGER NOT NULL REFERENCES customers(customer_id)
);
CREATE TABLE order_items (
  order_id INTEGER NOT NULL REFERENCES orders(order_id),
  line_no INTEGER NOT NULL,
  product_id VARCHAR(10) NOT NULL REFERENCES products(product_id),
  quantity INTEGER NOT NULL CHECK (quantity > 0),
  unit_price_at_sale DECIMAL(10,2) NOT NULL CHECK (unit_price_at_sale >= 0),
  PRIMARY KEY (order_id, line_no)
);
```

This is an illustrative schema, **not executed by the accompanying read-only lab**. In production, decide whether order line numbers can change, which attributes are immutable, whether customer details are versioned, and which indexes support joins.

To reconstruct the export, join at the correct grain:

```sql
SELECT o.order_id, c.customer_name, i.line_no,
       p.product_name, i.quantity, i.unit_price_at_sale
FROM orders AS o
JOIN customers AS c ON c.customer_id = o.customer_id
JOIN order_items AS i ON i.order_id = o.order_id
JOIN products AS p ON p.product_id = i.product_id
ORDER BY o.order_id, i.line_no;
```

**Expected:** three rows, not two; order 100 appears twice because it has two lines. Total revenue = `2 × 25.00 + 1 × 10.00 + 1 × 25.00 = 85.00`. Order totals: 100 → 60.00; 101 → 25.00. Count orders with `COUNT(DISTINCT order_id)`, not `COUNT(*)` after joining lines.

### Intentional denormalization

Denormalization can help a read-heavy reporting workload: materialize a precomputed order total, a daily sales aggregate, or a star-schema dimension attribute. It introduces a **consistency contract**: source of truth, refresh timing, acceptable staleness, correction/backfill policy, and reconciliation checks. Do not duplicate current customer names into operational orders merely to avoid a join without measuring the workload. Analytical facts often deliberately store dimensional keys and historical measures; operational 3NF and analytical star schemas solve different access patterns.

**DBRE/SRE angle:** More normalized tables can mean additional joins and foreign-key maintenance; denormalized copies can create storage, write amplification, lag, and divergent values. Measure actual plans, row counts, locking, replication lag, and recovery implications before choosing.

## Hands-on lab (30–50 minutes)

Open [029 — read-only PostgreSQL 18 lab](../labs/029-normalization-1nf-3nf-denormalization.sql). Run only against a **separately verified disposable PostgreSQL 18 primary** named `sql_tutorials`. The database name alone does not establish isolation. No real customer or patient data, production credentials, or persistent DDL.

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials \
  -f sql-tutorials/labs/029-normalization-1nf-3nf-denormalization.sql
```

The lab uses synthetic `VALUES` CTEs, a read-only transaction, server/database guards, expected-output queries, and fail-closed assertions. Expected output: 2 orders, 3 order lines, 2 customers, 2 products, total 85.00, and no orphan references. It compares a deliberately stale cached total (55.00 for order 100) with its correct source-derived total (60.00).

**Practice A (5 min):** Identify the grain and candidate key of the flat export. Answer: one order line; `(order_id, line_no)` is a candidate key given the stated business rule.

**Practice B (5 min):** Which fields depend on only `order_id`? Answer: `customer_id` (and any genuine order-level fields). Which depend on `product_id`? Current catalog `product_name`.

**Practice C (5 min):** Predict how many joined rows represent order 100 and why `COUNT(*)` overstates order counts. Answer: two line rows, one distinct order.

**Practice D (5 min):** Design a daily sales summary with a refresh SLA and reconciliation query. Suggested answer: daily total by UTC business date, documented late-arrival policy, unique date/key, compare aggregate to source order-line totals, and alert on drift.

## Validation, troubleshooting and safety (50–55 minutes)

| Symptom | Likely reason | Safe investigation |
|---|---|---|
| Double-counted orders | One-to-many join fan-out | State the grain and use distinct order keys where appropriate |
| Missing rows | INNER JOIN filters orphan/missing dimension rows | Run LEFT JOIN anti-join quality checks |
| Customer names disagree | Duplicated mutable attribute | Confirm source of truth and repair through approved pipeline |
| Cached total differs | Stale denormalized materialization | Compare source-derived and cached totals; inspect refresh lag |
| Slow normalized query | Join selectivity, indexes, statistics or skew | Read EXPLAIN in staging; measure before changing schema |
| Historical totals change | Current price used instead of sale-time price | Preserve and reconcile historical transaction measures |

**Guardrails:** This chapter's SQL file is read-only; never use production credentials even for training. A real migration needs schema ownership, dependency inventory, approved change window, data-quality profiling, backfill plan, constraints, locks/WAL/replica headroom, backup/restore readiness, dual-read compatibility and rollback criteria. Do not drop legacy columns until independent reconciliation succeeds.

## Review questions with answers (55–60 minutes)

1. **What is the grain of order_items?** One order line identified by order ID and line number.
2. **Why is a comma-separated list of products problematic?** It complicates relational constraints, filtering and line-level updates; model one line per product occurrence.
3. **What is a partial dependency?** A non-prime attribute depending on a proper subset of a composite candidate key.
4. **What is a transitive dependency example?** `order_id → customer_id → customer_name` for current customer data.
5. **Should historical sale price be moved into products?** No. It records a transaction-specific fact that may differ from today's catalog price.
6. **When is denormalization justified?** When measured query needs outweigh extra storage/consistency costs and there is a tested refresh/reconciliation contract.
7. **What is the expected synthetic revenue?** 85.00 across three lines and two orders.

## References and next chapter

- [PostgreSQL 18 — Table Constraints](https://www.postgresql.org/docs/18/ddl-constraints.html)
- [PostgreSQL 18 — SELECT and Joins](https://www.postgresql.org/docs/18/queries-table-expressions.html)
- [PostgreSQL 18 — Numeric Types](https://www.postgresql.org/docs/18/datatype-numeric.html)
- [PostgreSQL 18 — EXPLAIN](https://www.postgresql.org/docs/18/using-explain.html)
- [Master TOC](../MASTER-TOC.md)

**Next:** Chapter 030 — Lab 03: design and build a normalized operational schema.
