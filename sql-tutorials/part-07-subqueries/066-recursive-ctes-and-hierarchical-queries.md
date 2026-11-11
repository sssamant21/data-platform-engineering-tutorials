# 066 — Recursive CTEs and Hierarchical Queries

**Part 07 — Subqueries, CTEs & Set Operations** · **60 minutes** · **Audience:** SQL beginners, data engineers, DBREs and SREs.

**Prerequisite:** [065 — Common Table Expressions (WITH)](065-common-table-expressions-with.md). **Next:** 067 — UNION versus UNION ALL.

> **Safety:** Use only synthetic organizational records. Execute the [PostgreSQL 18 read-only lab](../labs/066-recursive-ctes-hierarchical-queries.sql) against an independently verified disposable PostgreSQL 18 database. A database-name guard does not establish that an endpoint is isolated. Never use production credentials.

## 1. Learning objectives and schedule (5 minutes)

After this lesson, you can identify an anchor and recursive member, traverse parent-child relationships, explain `UNION ALL` and termination, calculate hierarchy depth, identify disconnected records and cycles, and recognize PostgreSQL-specific cycle protection.

| Activity | Minutes |
|---|---:|
| Objectives, fixture and safety | 5 |
| Concepts and portability | 10 |
| Guided queries and expected output | 15 |
| Hands-on exercises | 20 |
| Troubleshooting and validation | 5 |
| Review questions | 5 |

**Scenario:** A fictional data-platform team has six employees and one disconnected record. A reporting hierarchy supports escalation routing and organizational reporting, not authorization decisions.

| employee_id | employee_name | manager_id |
|---:|---|---:|
| 1 | Ava (director) | NULL |
| 2 | Ben (DBRE lead) | 1 |
| 3 | Cora (data lead) | 1 |
| 4 | Dev (DBRE) | 2 |
| 5 | Eli (SRE) | 2 |
| 6 | Fay (analyst) | 3 |
| 7 | Gus (orphan) | 99 |

The disconnected record deliberately has a missing parent. In a real normalized schema, a foreign key would usually prevent this state.

## 2. Concepts, semantics, and portability (10 minutes)

A recursive common table expression has an **anchor term** (initial rows) and a **recursive term** (rows derived from the previous iteration). `WITH RECURSIVE` is supported by PostgreSQL and many major engines, but dialect-specific limits, `SEARCH`/`CYCLE` support, and type inference differ. The query below uses standard-style recursion and a PostgreSQL `VALUES` fixture.

Conceptually, PostgreSQL evaluates the anchor, then repeatedly evaluates the recursive term against a working set until no new rows appear. `UNION ALL` preserves all rows; it does **not** stop cycles. `UNION` removes duplicate *entire rows*, which may still fail to stop cycles if a changing depth or path is included. A finite depth cap and explicit visited-node detection are important for untrusted hierarchy data.

**Traversal order is not guaranteed by recursive evaluation.** Always use an explicit final `ORDER BY`. A depth column is not a complete path ordering; a visited-node path is helpful for diagnostics. PostgreSQL 18 additionally supports the SQL `SEARCH` and `CYCLE` clauses; these are not uniformly portable.

## 3. Guided examples (15 minutes)

### A. Traverse from the root

```sql
WITH RECURSIVE employees(employee_id, employee_name, manager_id) AS (
  VALUES (1,'Ava',NULL::integer),(2,'Ben',1),(3,'Cora',1),
         (4,'Dev',2),(5,'Eli',2),(6,'Fay',3),(7,'Gus',99)
), tree(employee_id, employee_name, manager_id, depth) AS (
  SELECT employee_id, employee_name, manager_id, 0
  FROM employees WHERE manager_id IS NULL
  UNION ALL
  SELECT e.employee_id, e.employee_name, e.manager_id, t.depth + 1
  FROM employees e JOIN tree t ON e.manager_id = t.employee_id
  WHERE t.depth < 10
)
SELECT employee_id, employee_name, depth
FROM tree ORDER BY depth, employee_id;
```

**Expected:** (1,Ava,0), (2,Ben,1), (3,Cora,1), (4,Dev,2), (5,Eli,2), (6,Fay,2). Gus is excluded because there is no path from root 1 to employee 7. The cap is a last-resort bound, not a substitute for cycle detection.

### B. Calculate descendants of a manager

Change the anchor to `WHERE employee_id = 2`, retaining the same recursive member. Expected IDs and depths relative to Ben: (2,0), (4,1), (5,1). For a manager's **direct** reports only, a simple `WHERE manager_id = 2` is clearer and cheaper.

### C. Detect missing parents before traversal

```sql
WITH employees(employee_id, employee_name, manager_id) AS (
  VALUES (1,'Ava',NULL::integer),(2,'Ben',1),(3,'Cora',1),
         (4,'Dev',2),(5,'Eli',2),(6,'Fay',3),(7,'Gus',99)
)
SELECT e.employee_id, e.manager_id
FROM employees e
LEFT JOIN employees m ON m.employee_id = e.manager_id
WHERE e.manager_id IS NOT NULL AND m.employee_id IS NULL;
```

**Expected:** employee 7 references missing manager 99. This is a data-quality problem, not proof of a cycle.

### D. Explicit cycle detection (PostgreSQL arrays)

For a graph that might contain loops, carry an array of visited employee IDs, and only recurse when the next ID is not already visited:

```sql
WITH RECURSIVE edges(child_id, parent_id) AS (
  VALUES (1,3),(2,1),(3,2)
), walk(node_id, visited, cycle_found, depth) AS (
  SELECT 1, ARRAY[1], false, 0
  UNION ALL
  SELECT e.parent_id, w.visited || e.parent_id,
         e.parent_id = ANY(w.visited), w.depth + 1
  FROM walk w JOIN edges e ON e.child_id = w.node_id
  WHERE NOT w.cycle_found AND w.depth < 10
)
SELECT node_id, depth, cycle_found FROM walk ORDER BY depth;
```

**Expected:** (1,0,false), (3,1,false), (2,2,false), (1,3,true). The cycle-closing row is emitted once, then recursion stops. PostgreSQL arrays and `ANY(array)` are vendor-specific here. PostgreSQL's `CYCLE` clause offers an alternative; verify semantics and supported syntax for each engine.

## 4. Hands-on lab (20 minutes)

1. Confirm the endpoint is a disposable PostgreSQL **18** instance, database `sql_tutorials`, and a least-privilege account. Review the complete [lab SQL](../labs/066-recursive-ctes-hierarchical-queries.sql).
2. From the repository root, on that verified endpoint only, run:

   ```bash
   psql -X -h 127.0.0.1 -p 5432 -U lab_user -d sql_tutorials \
     -v ON_ERROR_STOP=1 -f sql-tutorials/labs/066-recursive-ctes-hierarchical-queries.sql
   ```

3. Confirm six reachable employees, depth distribution **1/2/3**, manager 2 subtree **2/4/5**, orphan **7**, and a detected three-edge cycle. All assertion flags must be `t`; the fail-closed guard must return `1`.
4. On a local copy of the fixture only, change Gus's manager from 99 to 3. Predict seven reachable employees, depth distribution **1/2/4**, and zero missing-parent records. Restore the original fixture before running the supplied acceptance assertions.
5. Try anchoring at employee 3. Predict subtree IDs **3 and 6**. Explain why a recursive traversal is unnecessary for a single level.
6. Compare `UNION ALL` with `UNION` on a deliberately cyclic graph **only with a strict depth cap**. Explain why changing depth prevents whole-row duplicate elimination from ensuring termination.

**Runtime evidence requirements:** immutable commit SHA, isolated container identity, PostgreSQL version, redacted endpoint information, full `psql` output, assertions, process exit code and rollback confirmation. No such execution is claimed by this publication.

## 5. Troubleshooting and operational guardrails (5 minutes)

| Symptom | Likely cause | Safe response |
|---|---|---|
| Recursion does not terminate | Cycle or uncontrolled graph expansion | Add visited-node detection and finite depth bound |
| Missing employee from tree | Orphan or disconnected component | Run missing-parent and reachability checks |
| Duplicate employees | Multiple paths or incorrect edge grain | Validate key uniqueness and intended graph semantics |
| Unexpected order | Recursive output order assumed | Add explicit final `ORDER BY` |
| Slow query or timeout | Wide/deep graph, poor join access | Inspect `EXPLAIN` on isolated representative data; consider indexing parent IDs |
| Guard fails | Wrong database/version | Stop and verify endpoint; never bypass checks |

For production diagnostics, prefer read-only queries with bounded recursion, short timeouts, and a reviewed access path. Never assume a hierarchy is an access-control boundary. On large graphs, estimate the number of edges and maximum depth before running traversal.

## 6. Review questions with answers (5 minutes)

1. **What is the anchor term?** The initial row set, such as the root employee.
2. **What is the recursive term?** The query that derives another level from the previous working set.
3. **Does `UNION ALL` prevent cycles?** No.
4. **Why may `UNION` still fail to stop a cycle?** Rows with different depth/path values are not duplicates.
5. **What depth does Ava have?** Zero.
6. **How many employees are reachable from Ava?** Six.
7. **Who is disconnected?** Gus (ID 7), whose manager 99 is absent.
8. **Why specify `ORDER BY`?** Recursive evaluation order is not a stable result-order guarantee.
9. **What are two safety measures?** Visited-node cycle checks and a finite depth cap, plus a statement timeout.
10. **What is PostgreSQL-specific in the cycle example?** Array path construction and `ANY(array)`.

## References and validation status

- [PostgreSQL 18 — WITH Queries, recursive evaluation and cycle detection](https://www.postgresql.org/docs/18/queries-with.html)
- [PostgreSQL 18 — SELECT](https://www.postgresql.org/docs/18/sql-select.html)
- [PostgreSQL 18 — Arrays](https://www.postgresql.org/docs/18/arrays.html)
- [Master TOC](../MASTER-TOC.md) · [Status tracker](../STATUS-TRACKER.md)

**State:** Authored and published when confirmed on GitHub; expected results manually reasoned and targeted static inspection performed. Independent editorial review, comprehensive syntax/link QA, and **actual isolated PostgreSQL 18 runtime validation** remain pending.
