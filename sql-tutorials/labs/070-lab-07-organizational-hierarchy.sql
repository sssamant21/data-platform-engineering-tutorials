-- Chapter 070: synthetic hierarchy capstone; PostgreSQL 18 only.
-- Execute only on an independently verified disposable sql_tutorials instance.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';
SELECT current_database() AS database_name, current_setting('server_version') AS server_version,
       inet_server_addr() AS server_ip, inet_server_port() AS server_port;
SELECT 1 / CASE WHEN current_setting('server_version_num')::integer BETWEEN 180000 AND 189999 THEN 1 ELSE 0 END AS version_guard;
SELECT 1 / CASE WHEN current_database() = 'sql_tutorials' THEN 1 ELSE 0 END AS database_guard;

-- Root traversal: expected 1..6, depths 0,1,1,2,2,2.
WITH RECURSIVE employees(id,name,manager_id) AS (
 VALUES (1,'Ada',NULL::integer),(2,'Ben',1),(3,'Cora',1),
        (4,'Dev',2),(5,'Eli',2),(6,'Fay',3),
        (7,'Gus',99),(8,'Hana',9),(9,'Ivan',8)
), hierarchy(id,name,manager_id,depth,path) AS (
 SELECT id,name,manager_id,0,ARRAY[id] FROM employees WHERE id=1
 UNION ALL
 SELECT e.id,e.name,e.manager_id,h.depth+1,h.path||e.id
 FROM employees e JOIN hierarchy h ON e.manager_id=h.id
 WHERE h.depth<10 AND NOT e.id=ANY(h.path)
)
SELECT id,name,depth,path FROM hierarchy ORDER BY depth,id;

-- Ben's subtree: 2,4,5.
WITH RECURSIVE employees(id,manager_id) AS (
 VALUES (1,NULL::integer),(2,1),(3,1),(4,2),(5,2),(6,3),(7,99),(8,9),(9,8)
), subtree(id,depth,path) AS (
 SELECT id,0,ARRAY[id] FROM employees WHERE id=2
 UNION ALL
 SELECT e.id,s.depth+1,s.path||e.id
 FROM employees e JOIN subtree s ON e.manager_id=s.id
 WHERE s.depth<10 AND NOT e.id=ANY(s.path)
)
SELECT id,depth FROM subtree ORDER BY depth,id;

-- Single consolidated fail-closed acceptance: all checks must be true.
WITH RECURSIVE employees(id,name,manager_id) AS (
 VALUES (1,'Ada',NULL::integer),(2,'Ben',1),(3,'Cora',1),
        (4,'Dev',2),(5,'Eli',2),(6,'Fay',3),
        (7,'Gus',99),(8,'Hana',9),(9,'Ivan',8)
), reachable(id,depth,path) AS (
 SELECT id,0,ARRAY[id] FROM employees WHERE id=1
 UNION ALL
 SELECT e.id,r.depth+1,r.path||e.id
 FROM employees e JOIN reachable r ON e.manager_id=r.id
 WHERE r.depth<10 AND NOT e.id=ANY(r.path)
), subtree(id,depth,path) AS (
 SELECT id,0,ARRAY[id] FROM employees WHERE id=2
 UNION ALL
 SELECT e.id,s.depth+1,s.path||e.id
 FROM employees e JOIN subtree s ON e.manager_id=s.id
 WHERE s.depth<10 AND NOT e.id=ANY(s.path)
), orphans AS (
 SELECT e.id FROM employees e LEFT JOIN employees m ON e.manager_id=m.id
 WHERE e.manager_id IS NOT NULL AND m.id IS NULL
), unreachable AS (
 SELECT id FROM employees EXCEPT SELECT id FROM reachable
), manager_walk(start_id,id,manager_id,path,depth,cycle) AS (
 SELECT id,id,manager_id,ARRAY[id],0,false FROM employees
 UNION ALL
 SELECT w.start_id,m.id,m.manager_id,w.path||m.id,w.depth+1,
        m.id=ANY(w.path)
 FROM manager_walk w JOIN employees m ON m.id=w.manager_id
 WHERE NOT w.cycle AND w.depth<10
), cycle_starts AS (
 SELECT DISTINCT start_id FROM manager_walk WHERE cycle
), checks AS (
 SELECT
 (SELECT COUNT(*)=9 FROM employees) AS input_ok,
 (SELECT COUNT(*)=6 FROM reachable) AS reachable_count_ok,
 (SELECT COALESCE(array_agg(id ORDER BY id),ARRAY[]::integer[])=ARRAY[1,2,3,4,5,6] FROM reachable) AS reachable_ids_ok,
 (SELECT COALESCE(array_agg(id ORDER BY id),ARRAY[]::integer[])=ARRAY[2,4,5] FROM subtree) AS subtree_ok,
 (SELECT COALESCE(array_agg(id ORDER BY id),ARRAY[]::integer[])=ARRAY[7] FROM orphans) AS orphan_ok,
 (SELECT COALESCE(array_agg(id ORDER BY id),ARRAY[]::integer[])=ARRAY[7,8,9] FROM unreachable) AS unreachable_ok,
 (SELECT COALESCE(array_agg(start_id ORDER BY start_id),ARRAY[]::integer[])=ARRAY[8,9] FROM cycle_starts) AS cycles_ok,
 (SELECT COUNT(*) FILTER (WHERE depth=0)=1 AND COUNT(*) FILTER (WHERE depth=1)=2 AND COUNT(*) FILTER (WHERE depth=2)=3 FROM reachable) AS depths_ok
)
SELECT * FROM checks;
-- An assertion fails with division by zero if any condition is false.
WITH RECURSIVE employees(id,manager_id) AS (
 VALUES (1,NULL::integer),(2,1),(3,1),(4,2),(5,2),(6,3),(7,99),(8,9),(9,8)
), reachable(id,path) AS (
 SELECT id,ARRAY[id] FROM employees WHERE id=1
 UNION ALL SELECT e.id,r.path||e.id FROM employees e JOIN reachable r ON e.manager_id=r.id
 WHERE cardinality(r.path)<11 AND NOT e.id=ANY(r.path)
)
SELECT 1 / CASE WHEN (SELECT COUNT(*) FROM employees)=9
 AND (SELECT COUNT(*) FROM reachable)=6
 AND (SELECT COALESCE(array_agg(id ORDER BY id),ARRAY[]::integer[]) FROM reachable)=ARRAY[1,2,3,4,5,6]
 THEN 1 ELSE 0 END AS basic_acceptance_guard;
ROLLBACK;
