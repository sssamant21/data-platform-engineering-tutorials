-- 066 — Recursive CTEs and hierarchical queries; synthetic read-only PostgreSQL 18 lab
-- Independently confirm disposable endpoint. Name/version guards do NOT prove isolation.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';
SELECT current_database() AS database_name, current_setting('server_version') AS server_version,
       inet_server_addr() AS server_ip, inet_server_port() AS server_port;
SELECT 1 / CASE WHEN current_setting('server_version_num')::integer BETWEEN 180000 AND 189999 THEN 1 ELSE 0 END AS version_guard;
SELECT 1 / CASE WHEN current_database() = 'sql_tutorials' THEN 1 ELSE 0 END AS database_guard;

-- Expected six reachable employees at depths 0/1/2.
WITH RECURSIVE employees(id,name,manager_id) AS (
 VALUES (1,'Ava',NULL::integer),(2,'Ben',1),(3,'Cora',1),
        (4,'Dev',2),(5,'Eli',2),(6,'Fay',3),(7,'Gus',99)
), tree(id,name,depth,visited) AS (
 SELECT id,name,0,ARRAY[id] FROM employees WHERE manager_id IS NULL
 UNION ALL
 SELECT e.id,e.name,t.depth+1,t.visited || e.id
 FROM tree t JOIN employees e ON e.manager_id=t.id
 WHERE t.depth < 10 AND NOT e.id=ANY(t.visited)
)
SELECT id,name,depth FROM tree ORDER BY depth,id;

-- Expected Ben subtree: (2,0),(4,1),(5,1).
WITH RECURSIVE employees(id,manager_id) AS (
 VALUES (1,NULL::integer),(2,1),(3,1),(4,2),(5,2),(6,3),(7,99)
), subtree(id,depth,visited) AS (
 SELECT id,0,ARRAY[id] FROM employees WHERE id=2
 UNION ALL
 SELECT e.id,s.depth+1,s.visited || e.id
 FROM subtree s JOIN employees e ON e.manager_id=s.id
 WHERE s.depth<10 AND NOT e.id=ANY(s.visited)
)
SELECT id,depth FROM subtree ORDER BY depth,id;

-- Expected orphan (7,99).
WITH employees(id,manager_id) AS (
 VALUES (1,NULL::integer),(2,1),(3,1),(4,2),(5,2),(6,3),(7,99)
)
SELECT e.id,e.manager_id FROM employees e
LEFT JOIN employees m ON m.id=e.manager_id
WHERE e.manager_id IS NOT NULL AND m.id IS NULL;

-- Expected cycle-closing row at depth 3, node 1.
WITH RECURSIVE edges(child_id,parent_id) AS (
 VALUES (1,3),(2,1),(3,2)
), walk(node_id,visited,cycle_found,depth) AS (
 SELECT 1,ARRAY[1],false,0
 UNION ALL
 SELECT e.parent_id,w.visited || e.parent_id,
        e.parent_id=ANY(w.visited),w.depth+1
 FROM walk w JOIN edges e ON e.child_id=w.node_id
 WHERE NOT w.cycle_found AND w.depth<10
)
SELECT node_id,depth,cycle_found FROM walk ORDER BY depth;

-- Independent acceptance checks: each must be true.
WITH RECURSIVE employees(id,manager_id) AS (
 VALUES (1,NULL::integer),(2,1),(3,1),(4,2),(5,2),(6,3),(7,99)
), tree(id,depth,visited) AS (
 SELECT id,0,ARRAY[id] FROM employees WHERE manager_id IS NULL
 UNION ALL
 SELECT e.id,t.depth+1,t.visited || e.id
 FROM tree t JOIN employees e ON e.manager_id=t.id
 WHERE t.depth<10 AND NOT e.id=ANY(t.visited)
), subtree(id,depth,visited) AS (
 SELECT id,0,ARRAY[id] FROM employees WHERE id=2
 UNION ALL
 SELECT e.id,s.depth+1,s.visited || e.id
 FROM subtree s JOIN employees e ON e.manager_id=s.id
 WHERE s.depth<10 AND NOT e.id=ANY(s.visited)
), edges(child_id,parent_id) AS (
 VALUES (1,3),(2,1),(3,2)
), walk(node_id,visited,cycle_found,depth) AS (
 SELECT 1,ARRAY[1],false,0
 UNION ALL
 SELECT e.parent_id,w.visited || e.parent_id,e.parent_id=ANY(w.visited),w.depth+1
 FROM walk w JOIN edges e ON e.child_id=w.node_id
 WHERE NOT w.cycle_found AND w.depth<10
), checks AS (
 SELECT
 (SELECT COUNT(*)=6 AND MAX(depth)=2 FROM tree) AS reachability_ok,
 (SELECT array_agg(id ORDER BY depth,id)=ARRAY[1,2,3,4,5,6] FROM tree) AS order_ok,
 (SELECT COUNT(*)=1 FROM tree WHERE depth=0) AND
 (SELECT COUNT(*)=2 FROM tree WHERE depth=1) AND
 (SELECT COUNT(*)=3 FROM tree WHERE depth=2) AS depths_ok,
 (SELECT array_agg(id ORDER BY id)=ARRAY[2,4,5] FROM subtree) AS subtree_ok,
 (SELECT COUNT(*)=1 FROM employees e LEFT JOIN employees m ON m.id=e.manager_id
  WHERE e.manager_id IS NOT NULL AND m.id IS NULL) AS orphan_count_ok,
 (SELECT id=7 FROM employees e WHERE e.manager_id=99) AS orphan_id_ok,
 (SELECT COUNT(*)=4 AND COUNT(*) FILTER (WHERE cycle_found)=1 FROM walk) AS cycle_count_ok,
 (SELECT node_id=1 AND depth=3 FROM walk WHERE cycle_found) AS cycle_closure_ok
)
SELECT * FROM checks;

-- Fail closed on false or NULL; a nonzero psql exit code is required on failure.
WITH RECURSIVE employees(id,manager_id) AS (
 VALUES (1,NULL::integer),(2,1),(3,1),(4,2),(5,2),(6,3),(7,99)
), tree(id,depth,visited) AS (
 SELECT id,0,ARRAY[id] FROM employees WHERE manager_id IS NULL
 UNION ALL
 SELECT e.id,t.depth+1,t.visited || e.id FROM tree t
 JOIN employees e ON e.manager_id=t.id
 WHERE t.depth<10 AND NOT e.id=ANY(t.visited)
), edges(child_id,parent_id) AS (
 VALUES (1,3),(2,1),(3,2)
), walk(node_id,visited,cycle_found,depth) AS (
 SELECT 1,ARRAY[1],false,0
 UNION ALL
 SELECT e.parent_id,w.visited || e.parent_id,e.parent_id=ANY(w.visited),w.depth+1
 FROM walk w JOIN edges e ON e.child_id=w.node_id
 WHERE NOT w.cycle_found AND w.depth<10
)
SELECT 1 / CASE WHEN
 (SELECT COUNT(*)=6 AND MAX(depth)=2 FROM tree)
 AND (SELECT COUNT(*)=1 FROM employees e LEFT JOIN employees m ON m.id=e.manager_id
      WHERE e.manager_id IS NOT NULL AND m.id IS NULL)
 AND (SELECT COUNT(*)=4 AND COUNT(*) FILTER (WHERE cycle_found)=1 FROM walk)
 THEN 1 ELSE 0 END AS acceptance_guard;
ROLLBACK;
-- Expected outputs are statically reasoned; PostgreSQL 18 execution evidence pending.
