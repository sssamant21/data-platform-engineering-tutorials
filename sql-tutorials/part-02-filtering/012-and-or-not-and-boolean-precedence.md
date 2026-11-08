# Chapter 012 — AND, OR, NOT, and Boolean Precedence

> [Master TOC](../MASTER-TOC.md) · [Learning path](../README.md) · [Previous: Chapter 011](011-where-and-comparison-operators.md) · [Next: Chapter 013 (planned)](../MASTER-TOC.md)
>
> **Part 02 — Filtering, Sorting & Conditional Logic** · **60 minutes** · **Audience:** beginners, data engineers, DBRE/SRE
>
> **Status:** Authored/published; targeted static inspection only. Independent editorial review, comprehensive syntax review, and isolated PostgreSQL 18 runtime validation pending.

## Learning objectives and 60-minute agenda (0–5 minutes)

By the end, learners can combine conditions with `AND`, `OR`, and `NOT`; predict precedence; use parentheses to communicate intent; explain how `NULL` creates UNKNOWN; and review filters safely for operational extracts.

| Time | Activity |
|---|---|
| 0–5 min | Prerequisites, outcomes, environment safety |
| 5–15 min | Truth tables and operator precedence |
| 15–30 min | Six worked examples and expected rows |
| 30–50 min | Read-only PostgreSQL 18 lab and practice |
| 50–55 min | Troubleshooting, portability, and guardrails |
| 55–60 min | Review questions with answers |

**Prerequisites:** [Chapter 011](011-where-and-comparison-operators.md), [Chapter 009](../part-01-fundamentals/009-data-types-null-and-explicit-type-conversion.md), and [Chapter 003 lab setup](../part-01-fundamentals/003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md). Use a verified disposable PostgreSQL 18 instance and the database `sql_tutorials`. A database-name/version check alone cannot establish that an endpoint is safe.

## 1. Concepts and portable syntax (5–15 minutes)

A `WHERE` clause retains rows whose complete predicate is **TRUE**. `AND` requires both conditions to be TRUE; `OR` requires at least one TRUE; `NOT` negates a Boolean expression. SQL also has **UNKNOWN** when a comparison involves `NULL`. `WHERE` discards both FALSE and UNKNOWN.

| A | B | A AND B | A OR B |
|---|---|---|---|
| TRUE | TRUE | TRUE | TRUE |
| TRUE | FALSE | FALSE | TRUE |
| FALSE | FALSE | FALSE | FALSE |
| TRUE | UNKNOWN | UNKNOWN | TRUE |
| FALSE | UNKNOWN | FALSE | UNKNOWN |
| UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |

`NOT TRUE` is FALSE, `NOT FALSE` is TRUE, and `NOT UNKNOWN` is UNKNOWN. **Do not interpret UNKNOWN as FALSE.**

For the Boolean operators covered here, SQL evaluates **NOT before AND before OR**. Comparisons such as `amount >= 100` form Boolean expressions before those operators combine them. Parentheses override grouping and are strongly recommended whenever both `AND` and `OR` appear.

```sql
-- Portable SQL: explicit grouping communicates the business rule.
SELECT order_id
FROM orders
WHERE (status = 'paid' OR status = 'pending')
  AND amount >= 100
ORDER BY order_id;
```

`orders` is illustrative in this snippet. The executable lab builds the same data with an in-query CTE and `VALUES`, without creating tables.

## 2. Synthetic example dataset (15–30 minutes)

| order_id | customer | amount | status | priority |
|---:|---|---:|---|---|
| 301 | Ava | 50.00 | paid | TRUE |
| 302 | Ben | 100.00 | pending | FALSE |
| 303 | Ava | 150.00 | paid | FALSE |
| 304 | Chen | 100.00 | NULL | TRUE |
| 305 | Ben | 0.00 | cancelled | FALSE |
| 306 | Chen | 200.00 | paid | TRUE |
| 307 | Dee | 125.00 | pending | TRUE |

All data is fictional. In these examples, `priority` is a Boolean, not a text value.

### Example A — AND

`status = 'paid' AND amount >= 100` selects **303, 306**. Order 301 is paid but below the threshold.

### Example B — OR

`status = 'pending' OR priority = TRUE` selects **301, 302, 304, 306, 307**. Order 304 qualifies because priority is TRUE even though status is NULL.

### Example C — Precedence changes the result

```sql
-- NOT before AND before OR:
WHERE status = 'paid' OR status = 'pending' AND amount >= 100
-- Equivalent to:
WHERE status = 'paid' OR (status = 'pending' AND amount >= 100)
```

Expected **301, 302, 303, 306, 307**. By contrast:

```sql
WHERE (status = 'paid' OR status = 'pending') AND amount >= 100
```

Expected **302, 303, 306, 307**. The parenthesized version excludes order 301. This is a real data-quality risk for incremental extracts and operational reports.

### Example D — NOT with NULL

`NOT (status = 'paid')` selects **302, 305, 307**, not order 304: `NOT UNKNOWN` remains UNKNOWN. If the business rule explicitly includes missing statuses, write `status <> 'paid' OR status IS NULL`; expected **302, 304, 305, 307**.

### Example E — Complex business rule

`(status = 'paid' AND amount >= 100) OR (status = 'pending' AND priority = TRUE)` selects **303, 306, 307**. This could represent a synthetic exception queue. Always confirm the intended scope with the application/data owner.

### Example F — De Morgan's laws and UNKNOWN

`NOT (priority = TRUE OR amount >= 100)` is logically equivalent to `NOT (priority = TRUE) AND NOT (amount >= 100)` under SQL three-valued logic. Both select **305** for this dataset. If the operands can be NULL, the equivalence still holds, but UNKNOWN rows are not returned.

## 3. Hands-on PostgreSQL 18 lab (30–50 minutes)

Open [012-and-or-not-boolean-precedence.sql](../labs/012-and-or-not-boolean-precedence.sql). First independently verify the connection points to the disposable lab instance; never rely only on the script's guard.

From the repository root:

```powershell
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/012-and-or-not-boolean-precedence.sql
```

The SQL file uses `BEGIN READ ONLY`, synthetic `VALUES`, an environment assertion, six result-set queries, a fail-closed acceptance assertion, and `ROLLBACK`. Expected outputs, in order:

| Check | Expected order IDs |
|---|---|
| A: paid AND amount >= 100 | 303, 306 |
| B: pending OR priority | 301, 302, 304, 306, 307 |
| C1: implicit precedence | 301, 302, 303, 306, 307 |
| C2: grouped rule | 302, 303, 306, 307 |
| D: NOT paid | 302, 305, 307 |
| E: exception queue | 303, 306, 307 |

The final `acceptance_assertion` must equal **1** and the `psql` process must exit with status **0**. The expected results here are **manually derived**, not proof of execution.

**Practice 1 (5 minutes):** Predict `priority = TRUE AND amount >= 100`. Answer: **304, 306, 307**.

**Practice 2 (5 minutes):** Predict `status = 'cancelled' OR amount = 0`. Answer: **305**. Do not assume OR produces duplicate rows.

**Practice 3 (5 minutes):** Rewrite `NOT (status = 'pending' OR status = 'cancelled')` to include missing statuses intentionally. Answer: `(status <> 'pending' AND status <> 'cancelled') OR status IS NULL`; expected **301, 303, 304, 306**.

**Practice 4 (5 minutes):** Compare the C1/C2 results and explain the single differing row: **301**; it is paid but its amount is only 50.

## 4. Troubleshooting and operational guardrails (50–55 minutes)

| Symptom | Cause | Safe response |
|---|---|---|
| Unexpected extra rows | `OR` grouping wider than intended | Add parentheses and compare exact ID sets |
| NULL-status row missing | UNKNOWN filtered by WHERE | Explicitly decide whether `IS NULL` belongs in rule |
| `NOT` behaves unexpectedly | NOT applied to only one expression | Parenthesize the full intended condition |
| Results change ordering | No stable sort | Add `ORDER BY order_id` |
| Assertion fails | Incorrect data, predicate, or environment | Stop; inspect query and expected IDs |
| Server guard fails | Wrong PostgreSQL major version or DB name | Stop; inspect disposable endpoint, do not bypass guard |

**DBRE/SRE:** A Boolean predicate is not a substitute for change management or a scoped write preview. This lab performs no persistent writes. On large real tables, compound `OR` conditions can affect optimizer choices and index usage; do not extrapolate performance from seven synthetic rows. **Data engineering:** document parentheses and NULL policy in extract specifications and reconcile selected IDs and counts after rule changes.

**Portability:** `AND`, `OR`, `NOT`, `IS NULL`, `CASE`, `VALUES`, and `WHERE` are broadly standard SQL constructs. Boolean column representation and typed literals vary by vendor; the lab's `::numeric`, `current_database()`, `current_setting()`, `BEGIN READ ONLY`, and version assertion are PostgreSQL-specific. Test translations rather than assuming equivalence.

**Runtime acceptance evidence:** record UTC time, exact commit and script hash, Docker image digest/server version, independently confirmed isolated endpoint, executed command, complete stdout/stderr, exit status, and remediation. Do not mark runtime validated without that evidence.

## 5. Review questions with answers (55–60 minutes)

1. Which operator has higher precedence, AND or OR? **AND.**
2. Which Boolean operator binds most tightly of these three? **NOT.**
3. When does WHERE retain a row? **Only when the whole predicate is TRUE.**
4. What is `TRUE OR UNKNOWN`? **TRUE.**
5. What is `FALSE AND UNKNOWN`? **FALSE.**
6. What is `NOT UNKNOWN`? **UNKNOWN.**
7. Does `NOT (status = 'paid')` include NULL status? **No.**
8. Why parenthesize mixed AND/OR predicates? **To make business intent explicit and prevent precedence mistakes.**
9. What is the operational risk of a misplaced OR? **It can expand the selected data scope unexpectedly.**
10. Does passing a database-name guard certify a lab is isolated? **No; the endpoint must be independently verified.**

## References and navigation

- [PostgreSQL 18 logical operators](https://www.postgresql.org/docs/18/functions-logical.html)
- [PostgreSQL 18 operator precedence](https://www.postgresql.org/docs/18/sql-syntax-lexical.html#SQL-PRECEDENCE)
- [PostgreSQL 18 comparison and NULL semantics](https://www.postgresql.org/docs/18/functions-comparison.html)
- [PostgreSQL 18 SELECT](https://www.postgresql.org/docs/18/sql-select.html)
- [Chapter 011 — WHERE and Comparison Operators](011-where-and-comparison-operators.md)
- [Chapter 013 — NULL Handling and SQL Three-Valued Logic (next)](../MASTER-TOC.md)
