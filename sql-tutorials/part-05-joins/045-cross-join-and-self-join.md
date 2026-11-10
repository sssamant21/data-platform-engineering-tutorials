# 045 — CROSS JOIN and SELF JOIN

**Part 05 — Joins & Relational Query Patterns** · **Duration: 60 minutes** · **Audience:** SQL beginners, data engineers, DBRE/SRE.

**Prerequisites:** [Join fundamentals](041-join-fundamentals-and-relationship-cardinality.md), [INNER JOIN](042-inner-join-matched-records.md), and [outer joins](044-right-and-full-outer-join-applicability-and-portability.md). **Next:** Chapter 046 — Multi-table joins and join condition design (planned; link added after publication).

## 1. Learning objectives (5 minutes)

By the end, you can (1) explain why CROSS JOIN generates every combination, (2) calculate and cap its cardinality, (3) join a table to itself using distinct aliases, (4) find employees without managers and managers with reports, (5) validate row counts and detect accidental Cartesian products, and (6) explain operational safeguards.

## 2. Core ideas (10 minutes)

A **CROSS JOIN** combines every left row with every right row: if the inputs have *m* and *n* rows, the output has *m × n* rows. No matching predicate is applied. This is useful for constructing a complete test matrix (e.g., each region × each reporting month) but dangerous when either input is large. A missing predicate in an old-style comma join can accidentally create the same Cartesian product.

A **SELF JOIN** uses the *same table twice* under separate aliases. It is not a distinct SQL keyword: ordinary INNER/LEFT JOIN syntax is used. For employee-manager relationships, `employees e LEFT JOIN employees m ON e.manager_id = m.employee_id` retains top-level employees with no manager.

**Portable SQL:** `CROSS JOIN`, `INNER JOIN`, `LEFT JOIN`, `COUNT`, and `ORDER BY` are widely supported. **PostgreSQL-specific lab features:** `CREATE TEMP TABLE ... ON COMMIT DROP`, `DO`, `RAISE EXCEPTION`, `SET LOCAL`, and `pg_is_in_recovery()`. Do not copy the lab guard into other dialects unchanged.

## 3. Synthetic scenario and expected data (5 minutes)

A fictional retailer has three regions (East, West, Central) and two shipping modes (Standard, Express). The reporting team needs **six** region/mode combinations, including combinations with no actual orders. Separately, a four-person operations team has one director, two direct reports, and one employee reporting to one of those reports.

| employee_id | name | manager_id |
|---:|---|---:|
| 1 | Avery | NULL |
| 2 | Blake | 1 |
| 3 | Casey | 1 |
| 4 | Drew | 2 |

Expected hierarchy: Avery → Blake → Drew, and Avery → Casey.

## 4. Walkthrough A — deliberate CROSS JOIN (10 minutes)

The following is a portable, stand-alone query using derived tables:

```sql
SELECT r.region, s.shipping_mode
FROM (SELECT 'East' AS region UNION ALL
      SELECT 'West' UNION ALL SELECT 'Central') AS r
CROSS JOIN
     (SELECT 'Standard' AS shipping_mode UNION ALL
      SELECT 'Express') AS s
ORDER BY r.region, s.shipping_mode;
```

Expected **6 rows**, sorted by region then mode. The result is a *possible-combinations* grid, not proof that orders exist in all six combinations. For large input tables, estimate cardinality first: 10,000 × 50,000 = 500 million rows. Apply intentional input filters and limits before considering the cross product. A `LIMIT` on the final result does not necessarily make upstream work inexpensive.

## 5. Walkthrough B — SELF JOIN (5 minutes)

```sql
-- Run after the lab creates lab045_employees.
SELECT e.employee_id, e.employee_name,
       m.employee_name AS manager_name
FROM lab045_employees AS e
LEFT JOIN lab045_employees AS m
  ON e.manager_id = m.employee_id
ORDER BY e.employee_id;
```

Expected rows: Avery/NULL, Blake/Avery, Casey/Avery, Drew/Blake. An `INNER JOIN` would omit Avery because `NULL` does not equal any manager ID. Use `IS NULL` to find top-level employees, not `= NULL`.

## 6. Data engineering and DBRE/SRE applications (5 minutes)

- **Coverage matrix:** Cross join a small dimension of sites with a small dimension of expected dates, then LEFT JOIN observed activity to identify missing feeds.
- **Organization chart:** Self join employees to managers to audit broken relationships or missing supervisors.
- **Risk control:** An accidental cross join can multiply memory, network, sort, and temporary-disk usage. Inspect estimated cardinality and query plans before deploying.
- **Correctness:** Count distinct source keys and compare against expected output grain. A self join on a nonunique manager key may fan out unexpectedly.

## 7. Hands-on PostgreSQL 18 lab (15 minutes)

Open [`../labs/045-cross-join-self-join.sql`](../labs/045-cross-join-self-join.sql). Execute **only** in an isolated, disposable PostgreSQL 18+ database named `sql_tutorials`:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/045-cross-join-self-join.sql
```

The script refuses the wrong database, older PostgreSQL versions, and standby servers; creates only transaction-scoped temporary tables; sets timeouts; checks counts and relationships; then explicitly rolls back. It does **not** require permanent schema changes. Expected notice: `PASS: combinations=6, employees=4, manager_matches=3, top_level=1, direct_reports_to_avery=2`, followed by `ROLLBACK`. These are *predicted*, not yet runtime-confirmed results.

**Practice:** (a) Add a third shipping mode inside a disposable copy and predict 9 combinations. (b) Change the employee query to INNER JOIN and explain the 3-row result. (c) List employees reporting directly to Avery and verify Blake and Casey. (d) Explain why a four-row table self-joined without a predicate would produce 16 rows.

## 8. Validation and expected outcomes (3 minutes)

Verify that the Cartesian count equals 3 × 2, the LEFT self join returns all four employees, and exactly three rows have matched managers. The SQL lab raises an exception if any assertion fails. Successful completion ends in `ROLLBACK`; no persistent objects are created. This chapter has **not** been independently editorially reviewed or executed on PostgreSQL 18 as part of publication.

## 9. Troubleshooting and safety (2 minutes)

| Symptom | Likely cause | Safe response |
|---|---|---|
| Unexpectedly huge result | Missing or incomplete join predicate | Cancel in sandbox; inspect `ON` conditions and input counts |
| Director missing | INNER JOIN excludes NULL manager | Use LEFT JOIN |
| Duplicate employee rows | Nonunique join key | Check primary/unique key and source grain |
| `relation does not exist` | Temporary lab table not created in this session | Run the complete script in one session |
| Guard exception | Wrong DB/version/standby | Use isolated PostgreSQL 18+ `sql_tutorials` |

Never use production credentials, real patient data, or a production database for this lab. Avoid `EXPLAIN ANALYZE` on uncontrolled Cartesian joins; it executes the query.

## 10. Review questions and answers (3 minutes)

1. **What does a 3 × 2 CROSS JOIN return?** Six rows.
2. **Why use CROSS JOIN for a reporting matrix?** It creates all required combinations, even those with no activity.
3. **Is SELF JOIN a special SQL keyword?** No; it joins the same table under different aliases.
4. **Why does LEFT JOIN preserve Avery?** Its unmatched manager columns are NULL rather than dropping the employee row.
5. **What is the main operational risk?** Multiplicative row growth and resource exhaustion.
6. **How do you prevent a silent fan-out?** Specify the intended grain, enforce uniqueness where appropriate, and assert output cardinality.

## 11. References (1 minute)

- [PostgreSQL 18: Table Expressions and Joined Tables](https://www.postgresql.org/docs/18/queries-table-expressions.html)
- [PostgreSQL 18: SELECT](https://www.postgresql.org/docs/18/sql-select.html)
- [PostgreSQL 18: EXPLAIN](https://www.postgresql.org/docs/18/sql-explain.html)

## 12. Completion checklist (1 minute)

- [ ] Explain CROSS JOIN cardinality and self-join aliases.
- [ ] Predict the six combinations and four hierarchy rows.
- [ ] Run the lab only on a disposable PostgreSQL 18+ instance.
- [ ] Record actual runtime evidence separately if performed.
- [ ] Proceed to Chapter 046 (after publication).

**Publication state:** Authored; targeted static reasoning only. **Independent editorial review:** Pending. **Comprehensive static QA:** Pending. **PostgreSQL 18 runtime validation:** Pending.
