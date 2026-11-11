# 070 — Lab 07: Query a Multi-Level Organizational Hierarchy

**Part 07 — Subqueries, CTEs & Set Operations** · **60 minutes** · **Audience:** beginner SQL learners, data engineers, DBRE/SRE.

**Prerequisites:** [066 — Recursive CTEs](066-recursive-ctes-and-hierarchical-queries.md), [068 — INTERSECT and EXCEPT](068-intersect-and-except.md), and [069 — Refactor Complex SQL](069-refactor-complex-sql-for-readability-and-correctness.md). **Next:** [Part 08 — Window Functions](../MASTER-TOC.md#part-08--window-functions--advanced-analytics).

**Safety:** Fictional employees only. The [PostgreSQL 18 lab](../labs/070-lab-07-organizational-hierarchy.sql) is read-only, uses inline `VALUES`, and rolls back. Run only against an independently verified disposable `sql_tutorials` database; the name/version guard alone does **not** prove isolation. No production credentials or systems.

## 1. Objectives and 60-minute agenda (5 minutes)

By the end you can: (1) model an adjacency list with employee and manager IDs; (2) traverse a hierarchy with a recursive CTE; (3) calculate depth and path; (4) locate an employee's descendants; (5) detect unreachable/orphan nodes and cycles; (6) reconcile result sets with `EXCEPT`; (7) apply bounded-recursion safeguards.

| Activity | Minutes |
|---|---:|
| Safety, objectives, input contract | 5 |
| Model and expected results | 10 |
| Guided recursive query | 15 |
| Hands-on exercises and SQL lab | 20 |
| Troubleshooting, review and answers | 10 |

## 2. Scenario and data contract (10 minutes)

An imaginary data-platform team wants a reporting hierarchy. Each row represents **one employee**, and `manager_id` references another employee or is NULL for a root. The lab intentionally includes an orphan and a two-person cycle for data-quality checks.

| ID | Name | Manager ID | Interpretation |
|---:|---|---:|---|
| 1 | Ada | NULL | root |
| 2 | Ben | 1 | Ada's report |
| 3 | Cora | 1 | Ada's report |
| 4 | Dev | 2 | Ben's report |
| 5 | Eli | 2 | Ben's report |
| 6 | Fay | 3 | Cora's report |
| 7 | Gus | 99 | missing manager (orphan) |
| 8 | Hana | 9 | cycle participant |
| 9 | Ivan | 8 | cycle participant |

**Expected:** Starting at Ada (ID 1), the reachable employee IDs are 1–6, at depths 0,1,1,2,2,2 respectively. Ben's subtree includes IDs 2,4,5. Gus is an orphan. Hana and Ivan form a disconnected cycle. Nine input employees minus six root-reachable employees equals three unreachable employees; **not all unreachable employees are orphans**.

An adjacency list is a portable relational model. The business grain of the output is one row per employee *per traversal path*; a valid tree gives one path per employee, while malformed multi-parent graph data can require additional deduplication.

## 3. Guided query (15 minutes)

A recursive CTE consists of an **anchor** (root employee) and a **recursive member** (direct reports of the current level). `UNION ALL` preserves recursive rows; a path guard prevents revisiting the same employee. A maximum depth adds defense-in-depth.

```sql
WITH RECURSIVE employees(id, name, manager_id) AS (
  VALUES (1,'Ada',NULL::integer),(2,'Ben',1),(3,'Cora',1),
         (4,'Dev',2),(5,'Eli',2),(6,'Fay',3),
         (7,'Gus',99),(8,'Hana',9),(9,'Ivan',8)
),
hierarchy(id, name, manager_id, depth, path) AS (
  SELECT id, name, manager_id, 0, ARRAY[id]
  FROM employees WHERE id = 1
  UNION ALL
  SELECT e.id, e.name, e.manager_id, h.depth + 1,
         h.path || e.id
  FROM employees e JOIN hierarchy h ON e.manager_id = h.id
  WHERE h.depth < 10 AND NOT e.id = ANY(h.path)
)
SELECT id, name, depth, path
FROM hierarchy ORDER BY depth, id;
```

**Expected:** Six rows: Ada depth 0, Ben/Cora depth 1, Dev/Eli/Fay depth 2. PostgreSQL-specific syntax here is `ARRAY[id]`, `||` array concatenation, `ANY(array)`, and `NULL::integer`. `WITH RECURSIVE` is standard SQL; portable implementations may need string-based paths or vendor-specific cycle syntax. A cycle guard is essential even when a depth limit exists.

**Descendants:** Change the anchor to `WHERE id = 2` to return Ben, Dev and Eli (including Ben himself). To exclude the anchor, add `WHERE depth > 0` to the final SELECT.

**Reconciliation:** Compute the reachable IDs, then use `EXCEPT` to find employees absent from the root traversal. This identifies 7,8,9, but does not itself tell whether each is an orphan or a cycle. An orphan is an employee with non-NULL `manager_id` and no matching manager. For a cycle, follow each node's manager pointers while tracking visited IDs; the supplied lab demonstrates this separately.

## 4. Hands-on lab (20 minutes)

Open [070-lab-07-organizational-hierarchy.sql](../labs/070-lab-07-organizational-hierarchy.sql) and run it with `psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f 070-lab-07-organizational-hierarchy.sql` from the `labs/` directory, after independently confirming a disposable PostgreSQL 18 instance. `-X` ignores user psql startup configuration; it is not a security boundary.

1. Inspect the nine synthetic employees and predict the reachable rows before executing.
2. Run the root traversal and confirm depths, paths, and six rows.
3. Run Ben's subtree and confirm IDs 2,4,5.
4. Run the orphan and unreachable checks. Explain why 7 differs from 8 and 9.
5. Run the bounded manager-chain cycle detection and verify that 8 and 9 are reported as cycle participants.
6. Run the final fail-closed acceptance query: all checks must return `true`.

**Stretch exercise:** Change the root to Cora (ID 3); predict IDs 3 and 6, depths 0 and 1. Do not edit the acceptance checks unless you also update their contract.

## 5. Troubleshooting and operational guardrails (5 minutes)

| Symptom | Likely cause | Safe response |
|---|---|---|
| Recursion does not terminate | Cycle or missing visited-ID guard | Cancel the query, add a path guard and finite depth |
| Duplicate descendants | Repeated paths or non-tree edges | Verify unique employee IDs and parent cardinality |
| Missing Gus | Orphan is not reachable from Ada | Run explicit orphan check |
| Hana/Ivan absent | Disconnected cycle | Run separate cycle detection |
| Version/database guard fails | Wrong endpoint/version/name | Stop; do not bypass the guard |
| Unexpected plan or slow query | Missing manager index on real tables, high fan-out | In a staging environment inspect `EXPLAIN`; do not use `EXPLAIN ANALYZE` against unapproved workloads |

The read-only exercise cannot certify a real organization's hierarchy. In operational pipelines, enforce primary/foreign keys where feasible, verify ingest completeness, flag missing parents, and audit cycles before publishing managerial reporting. Indexing `manager_id` can help large real datasets, but no index creation is part of this lab.

## 6. Review questions with answers (5 minutes)

**Q1. What is the anchor member?** The initial set of root employees.

**Q2. Why `UNION ALL`?** It preserves recursive rows without global duplicate elimination; explicit cycle detection controls repeated paths.

**Q3. What is Ben's subtree?** IDs 2,4,5, including Ben; excluding Ben gives 4,5.

**Q4. Why is the orphan check separate from `EXCEPT`?** `EXCEPT` finds all unreachable IDs (7,8,9), while the missing-parent join identifies only ID 7.

**Q5. Why have both a path guard and a depth cap?** The path guard stops revisiting IDs, while a depth cap bounds resource use on unexpected data.

**Q6. Does a successful SQL assertion prove production readiness?** No. It verifies only this synthetic dataset in the executed environment; independent review and production change controls remain separate.

## 7. Acceptance, portability, and references

The SQL lab's assertions cover nine inputs, six reachable, exact subtree IDs, one orphan, three unreachable, and cycle participants 8/9. Expected values are **reasoned from the synthetic dataset**, not runtime-verified unless an isolated PostgreSQL 18 run is separately recorded.

**Portable:** relational joins, `EXISTS`, `NOT EXISTS`, `EXCEPT`, `UNION ALL`, and the recursive CTE concept (dialect support varies). **PostgreSQL-specific:** array paths, `ANY(array)`, `::` casts, `SET LOCAL`, `BEGIN READ ONLY`, `psql` commands. SQL Server, Oracle, MySQL, and Snowflake have different recursion and cycle facilities; do not copy the lab unchanged.

**References:** [PostgreSQL 18 WITH queries](https://www.postgresql.org/docs/18/queries-with.html), [PostgreSQL 18 array functions](https://www.postgresql.org/docs/18/functions-array.html), [PostgreSQL 18 transaction commands](https://www.postgresql.org/docs/18/sql-begin.html), [PostgreSQL 18 EXCEPT](https://www.postgresql.org/docs/18/queries-union.html).

**Part 07 completed by authorship:** Chapters 061–070. Independent editorial review, comprehensive static QA and PostgreSQL 18 runtime acceptance remain separate pending milestones.
