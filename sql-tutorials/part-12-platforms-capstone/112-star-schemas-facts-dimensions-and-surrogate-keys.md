# 112 — Star Schemas, Facts, Dimensions, and Surrogate Keys

**Part 12 — Data Engineering, SQL Dialects & Final Projects | Duration: 60 minutes | Audience: data engineers, analysts, DBRE/SRE beginners**

**Status:** Authored for PostgreSQL 18 lab; independently reviewed: no; comprehensive static QA: pending; actual PostgreSQL 18 runtime validation: pending.

## 1. Outcomes, prerequisites and schedule (0–5 minutes)

By the end, you can identify a fact table's grain, distinguish facts from dimensions, explain business versus surrogate keys, model slowly changing dimensions (SCD Type 2), join without double-counting, and reconcile warehouse totals to synthetic source transactions.

**Schedule:** 0–5 outcomes; 5–15 concepts; 15–30 walkthrough; 30–50 hands-on; 50–55 troubleshooting; 55–60 review.

Prerequisites: [021 — Entity relationships](../part-03-modeling/021-entity-relationships-and-conceptual-data-modeling.md), [024 — Keys](../part-03-modeling/024-primary-keys-natural-keys-surrogate-keys-and-unique.md), [052 — Aggregation grain](../part-06-aggregation/052-group-by-and-aggregation-grain.md), [111 — OLTP versus OLAP](111-oltp-versus-olap-query-design.md).

## 2. Key concepts (5–15 minutes)

A **star schema** places a central *fact* table (events and numeric measures) beside descriptive *dimension* tables. In this example, `fact_sales` has **one row per completed order line**, not one row per order. `dim_product` describes a product; `dim_customer` describes a customer; `dim_date` can describe a calendar day. A **conformed dimension** is reused consistently by multiple facts.

- **Business/natural key:** `product_code` (e.g., SKU-A), stable in the source's business domain, though it can be renamed or reused.
- **Surrogate key:** `product_sk` (e.g., 101), warehouse-generated identifier for a particular dimension version. Never assume its value has business meaning.
- **Fact foreign key:** `fact_sales.product_sk` resolves to exactly one dimension version. A missing match is an integrity exception; do not silently drop facts with an inner join.
- **Additive measure:** `net_amount` can be summed across product, customer, and date in this example. Ratios and distinct counts are not generally additive.
- **SCD Type 1:** overwrite an attribute, losing its prior value. **SCD Type 2:** insert a new dimension version with an effective time range, retaining historical context.

**Important:** surrogate keys alone do not prevent fan-out. A valid fact-to-dimension join requires a unique dimension key, and time-range joins must match at most one version. A transaction line's `order_id` is a *degenerate dimension* attribute on the fact; the compound source identity is `(order_id, line_no)`.

### Conceptual model

```text
dim_product(product_sk PK, product_code, category, valid_from, valid_to)
                         1
                         |
                         *
fact_sales(order_id, line_no, product_sk FK, customer_sk FK, net_amount)
                         *
                         |
                         1
dim_customer(customer_sk PK, customer_code, segment)
```

In a production design, enforce unique source line identity, dimension-key uniqueness, foreign keys where feasible, non-overlapping SCD2 intervals, and explicit handling for late-arriving facts. Some warehouses do not enforce foreign keys; automated quality tests remain essential.

## 3. Worked examples (15–30 minutes)

**Synthetic business case:** SKU-A moved from category `Basic` to `Premium` on 2026-02-01. The historical sale from January must remain Basic. A new sale in February must be Premium.

| product_sk | product_code | category | valid_from | valid_to (exclusive) |
|---:|---|---|---|---|
| 101 | SKU-A | Basic | 2026-01-01 | 2026-02-01 |
| 102 | SKU-A | Premium | 2026-02-01 | NULL (current) |
| 201 | SKU-B | Basic | 2026-01-01 | NULL (current) |

**Fact grain and synthetic amounts:**

| order_id | line_no | sale_date | product_sk | net_amount |
|---:|---:|---|---:|---:|
| 5001 | 1 | 2026-01-15 | 101 | 30.00 |
| 5001 | 2 | 2026-01-15 | 201 | 20.00 |
| 5002 | 1 | 2026-02-10 | 102 | 40.00 |
| 5003 | 1 | 2026-02-12 | 201 | 10.00 |

A fact-to-version join uses the surrogate key, **not only** `product_code`:

```sql
WITH dim_product(product_sk, category) AS (
  VALUES (101, 'Basic'), (102, 'Premium'), (201, 'Basic')
), fact_sales(product_sk, net_amount) AS (
  VALUES (101, 30.00::numeric), (201, 20.00::numeric),
         (102, 40.00::numeric), (201, 10.00::numeric)
)
SELECT d.category, COUNT(*) AS line_count, SUM(f.net_amount) AS revenue
FROM fact_sales AS f
JOIN dim_product AS d ON d.product_sk = f.product_sk
GROUP BY d.category
ORDER BY d.category;
```

**Calculated expected results:** Basic = 3 lines / 60.00; Premium = 1 line / 40.00; grand total = 4 lines / 100.00. The SQL uses broadly portable `WITH`, `VALUES`, `JOIN`, and `GROUP BY` constructs; `::numeric` is PostgreSQL-specific shorthand (use `CAST(... AS DECIMAL(...))` for greater portability).

**Why the wrong join fails:** joining a fact's product business code to all historical dimension rows matches SKU-A twice. It produces 6 joined rows instead of 4 and 170.00 instead of 100.00. Never repair this with `SUM(DISTINCT net_amount)`: equal-valued legitimate lines would be lost.

**SCD2 lookup when loading a new fact** (illustrative; do not run on production):

```sql
SELECT product_sk
FROM dim_product
WHERE product_code = :product_code
  AND valid_from <= :sale_date
  AND (valid_to > :sale_date OR valid_to IS NULL);
```

`:product_code` and `:sale_date` are **application placeholders**, not executable bare PostgreSQL SQL; use bound parameters in the application. Use a half-open `[valid_from, valid_to)` interval to avoid boundary overlap. Validate exactly one match and define a late-arrival policy before loading.

## 4. Hands-on lab (30–50 minutes)

Companion: [112 — synthetic read-only PostgreSQL 18 lab](../labs/112-star-schema-facts-dimensions-surrogate-keys.sql).

After verifying you are connected to a **disposable, isolated PostgreSQL 18 database** named `sql_tutorials`:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/112-star-schema-facts-dimensions-surrogate-keys.sql
```

The script checks the database and major version, starts a read-only transaction, uses transaction-local timeouts, runs synthetic `VALUES` datasets, asserts exact expected results, and rolls back. It creates no persistent tables, roles, or objects. Do not run if the database identity is uncertain.

**Tasks (20 minutes):** (1) name the fact grain; (2) identify each SKU-A dimension version; (3) compute category revenue; (4) inspect the erroneous business-key join; (5) verify January and February SKU-A classification; (6) explain why an unmatched dimension lookup must block or quarantine the row rather than silently drop it.

**Expected (calculated, not observed):** 4 fact lines; 3 dimension versions; 100.00 revenue; Basic 60.00, Premium 40.00; SKU-A history 30.00 Basic and 40.00 Premium; incorrect business-key join 6 rows / 170.00; zero assertion mismatches.

**Practice extension:** in a scratch copy of the CTE, add a third version of SKU-A effective 2026-03-01 and a March line. Explain which dimension version each line should use. Keep it synthetic and read-only.

## 5. Troubleshooting, validation, and operational safety (50–55 minutes)

| Symptom | Check | DBRE/SRE or data-engineering action |
|---|---|---|
| Revenue inflated | Dimension uniqueness; joined row count vs fact count | Stop promotion, reconcile at line grain |
| Historical category changed | SCD2 version selection and effective dates | Repair mapping in isolated staging, replay with approval |
| Facts disappear | INNER JOIN to missing dimension | Anti-join to list unmatched facts; quarantine per contract |
| Multiple SCD2 matches | Overlapping validity windows | Fail load; enforce interval exclusion or equivalent QA |
| Warehouse report differs from source | Time-zone, currency, refunds, watermark, grain | Reconcile a consistent snapshot and document freshness |
| Query slow | Join key types, statistics, scan volume, partition pruning | Use approved EXPLAIN and measured tests, not speculative indexes |

**Guardrails:** use fictional data only; never access production credentials; do not alter real warehouse dimensions, backfill facts, or modify keys without approval, restore plan, and tested rollback. A read-only simulated lab does **not** demonstrate physical constraints, ETL correctness, CDC delivery, or measured query performance. For real systems, retain row-count checks, duplicate-key tests, SCD2 non-overlap tests, and signed reconciliation evidence.

## 6. Review questions with answers (55–60 minutes)

1. **What is the grain?** One completed order line, identified by `(order_id, line_no)`.
2. **Why use a surrogate key for SCD2?** It points a fact to the correct historical version of a business entity.
3. **Does `product_code` uniquely identify a dimension row?** No; a Type 2 dimension has multiple versions per business key.
4. **Why is `valid_to` exclusive?** Adjacent versions can meet at the same boundary without overlapping.
5. **What should happen when a fact cannot resolve exactly one dimension version?** Reject or quarantine according to a documented load contract; do not silently drop or duplicate.
6. **What is the category revenue?** Basic 60.00 and Premium 40.00, total 100.00.

**Next milestone:** 113 — ELT, incremental loads, and change data capture patterns (not linked until published).

## References

- [PostgreSQL 18 — SELECT](https://www.postgresql.org/docs/18/sql-select.html)
- [PostgreSQL 18 — Table Constraints](https://www.postgresql.org/docs/18/ddl-constraints.html)
- [PostgreSQL 18 — Range Types](https://www.postgresql.org/docs/18/rangetypes.html)
- [Kimball Group — Fact Table Structure](https://www.kimballgroup.com/2008/11/fact-tables/)
- [Kimball Group — Slowly Changing Dimensions](https://www.kimballgroup.com/2008/09/slowly-changing-dimensions-part-2/)

**Evidence statement:** Authored and targeted statically reasoned; independent editorial review, comprehensive parser/link QA, and actual isolated PostgreSQL 18 execution with retained logs remain pending.
