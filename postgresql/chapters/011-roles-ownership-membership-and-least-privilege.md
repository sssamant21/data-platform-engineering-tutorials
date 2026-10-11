# Chapter 011 — Roles, Ownership, Membership and Least Privilege

**Audience:** DBRE and SRE teams only. **Baseline:** PostgreSQL 18.
**Duration:** 90–120 minutes with the lab. **Prerequisites:** Chapters 004, 005 and 010.
**Status:** Authored and reviewed statically; PostgreSQL execution pending.

[Master plan](../MASTER-PLAN.md) · [Previous chapter](010-configuration-drift-and-baseline-acceptance.md) · [Hands-on lab](../labs/011-roles-ownership-membership-least-privilege-lab.md) · [Read-only inventory](../scripts/011-role-access-inspection.sql) · [Runtime checks](../scripts/011-runtime-acceptance.sql)

## 1. Operational problem and objectives

An application can connect but cannot use a sequence. A deployment creates its next table under the migration login instead of the intended owner, so future-object grants do not apply. During an incident, someone grants a service ownership to remove a permission error, and the service can now change or destroy its schema.

DBRE/SRE operators need to explain the exact authorization path before changing it. This chapter teaches role attributes, object ownership, membership options and layered privileges. Its lab provisions isolated identities and proves both permitted and forbidden operations through actual restricted connections.

The outcome is an access contract with evidence: who logs in, who owns objects, who can assume another role, what applications can do, and how access can be removed without destroying production data.

## 2. Build a role model with separate responsibilities

Roles are cluster-wide identities. Database objects and most object grants are scoped to a database. A role can exist on the cluster without having useful access to a particular database.

| Responsibility | Login? | Intended authority |
|---|---|---|
| Object owner | Usually NOLOGIN | Own application schema and objects; perform owner-level DDL |
| Migration identity | LOGIN | Connect and explicitly assume the owner for reviewed deployments |
| Reader group | NOLOGIN | Use the application schema and read approved objects |
| Writer group | NOLOGIN | Inherit reads and perform explicitly approved writes |
| Application identity | LOGIN | Inherit runtime groups; no owner membership |
| Monitoring identity | LOGIN | Approved observability privileges, reviewed for data exposure |
| Emergency administrator | Controlled separately | Exceptional authority with incident/change evidence |

NOLOGIN prevents direct login; it does not prevent members from using the role's authority. Granting an owner role with inheritance can still give a service powerful ownership rights. Review membership paths, not just login flags. Keep runtime grant groups free of owned SQL objects: INHERIT TRUE with SET FALSE does not safely contain an inherited owner's authority.

The lab intentionally gives its runtime role SELECT, INSERT and UPDATE, but no DELETE, TRUNCATE, DDL or membership delegation. That is a sample service contract, not a universal write-role definition. Production applications may need DELETE or specific functions; grant them only when the operation is required and tested.

Superuser bypasses access restrictions. CREATEDB, CREATEROLE, REPLICATION and BYPASSRLS also deserve explicit review. These attributes are not ordinary inherited object grants. Membership that permits SET ROLE to a powerful role can nevertheless expose that role's authority.

## 3. Membership: INHERIT, SET and ADMIN answer different questions

PostgreSQL 16 and later support per-membership inheritance and role-switching options. PostgreSQL 18 examples explicitly set them; do not paste this syntax into older versions without checking their role-level behavior.

| Option | Question | Lab policy |
|---|---|---|
| INHERIT | Are this role's privileges automatically available to the member? | True for runtime access; false for migration ownership |
| SET | Can the original login assume this role through SET ROLE? | False for runtime groups; true for migration owner |
| ADMIN | Can the member grant that role's membership onward? | False for application and migration identities |

Example lab grants:

~~~sql
GRANT c011_reader TO c011_writer
  WITH INHERIT TRUE, SET FALSE, ADMIN FALSE;
GRANT c011_writer TO c011_runtime
  WITH INHERIT TRUE, SET FALSE, ADMIN FALSE;
GRANT c011_owner TO c011_deploy
  WITH INHERIT FALSE, SET TRUE, ADMIN FALSE;
~~~

The runtime role automatically gets the reader/writer privileges. It cannot assume either group as its current execution identity and has no owner membership. The migration role starts without owner privileges but may explicitly become c011_owner.

For nested membership, examine every edge. An inheritance path stops at an edge with INHERIT FALSE; a permitted role switch needs a suitable SET path from the original login. Role-level INHERIT supplies defaults for newly granted memberships; inspect the actual membership options instead of inferring them from one attribute.

After SET ROLE, current_user changes and determines permission checking and new-object ownership. session_user normally identifies the original login. RESET ROLE returns to that original authority. SET ROLE does not automatically apply the target role's ALTER ROLE login defaults; establish required migration session settings explicitly.

Use pg_auth_members to identify member, granted role, grantor and the three options. Use pg_has_role with MEMBER, USAGE and SET to distinguish membership existence, immediately usable privileges and role-switch capability. Actual operations remain necessary acceptance evidence.

## 4. Ownership is stronger than runtime privileges

An owner has intrinsic authority over an object's definition and lifecycle. Withdrawing ordinary table privileges does not turn an owner into a safely restricted application role; an owner can regrant privileges.

Create durable application objects under a dedicated owner. Migration tooling should SET ROLE before DDL and verify the resulting owner after it creates an object. A table owned by a personal login becomes a retirement and handover problem.

Database ownership does not automatically assign ownership of every contained relation. Schema ownership and table ownership are also separate. For ordinary users, changing an object's owner involves current-owner authority, the ability to assume the target owner, and relevant object-type requirements such as CREATE on the containing schema.

Do not “fix” a SELECT error by transferring ownership. Diagnose the object grant or membership path. Reserve ownership changes for a reviewed lifecycle action with dependency inventory and rollback planning.

## 5. Access is layered

Authentication establishes identity. Authorization decides what that identity may do. A valid password alone grants no table access.

| Layer | Typical required privilege | Common failure |
|---|---|---|
| Database | CONNECT | Login succeeds against the server but database access is denied |
| Schema | USAGE | Table grant exists but its schema is inaccessible |
| Table | SELECT, INSERT, UPDATE or other required operation | Read works while write fails |
| Sequence | USAGE for nextval in this lab's bigserial default | INSERT permission exists but generated ID fails |
| Function/procedure | EXECUTE | Application can see objects but cannot invoke an API |
| Membership | Suitable inherited privileges or SET path | Group grant exists but is unavailable to the session |

A realistic UPDATE may require SELECT on referenced columns as well as UPDATE. INSERT ... RETURNING also needs the corresponding SELECT access. Use representative statements rather than evaluating only a privilege-name checklist.

PUBLIC includes every role. PostgreSQL grants some privileges to PUBLIC by default, including database CONNECT/TEMPORARY and routine EXECUTE. Null ACL fields represent defaults, not an absence of rights. Examine PUBLIC and inherited paths when a revoke appears ineffective.

The lab revokes PUBLIC privileges only in its newly created database and schema. Do not copy a broad PUBLIC revoke into a shared production database without inventorying affected services. PostgreSQL's public-schema defaults also differ between newly created modern databases and upgraded databases; inspect the actual ACL.

Schema CREATE and search_path need care because object lookup can trust code created by another role. Use schema-qualified application references and review writable search-path schemas. SECURITY DEFINER functions, RLS and privileged operational APIs need separate security review; table grants alone cannot certify them.

## 6. Existing objects and future objects need different controls

GRANT ON ALL TABLES IN SCHEMA affects existing tables. It does not define what happens to tomorrow's table.

ALTER DEFAULT PRIVILEGES defines grants for future objects created by a particular current role in a particular database, optionally scoped to a schema. The creator's defaults matter; inherited group defaults are not automatically substituted.

~~~sql
ALTER DEFAULT PRIVILEGES FOR ROLE c011_owner IN SCHEMA c011_data
  GRANT SELECT ON TABLES TO c011_reader;
ALTER DEFAULT PRIVILEGES FOR ROLE c011_owner IN SCHEMA c011_data
  GRANT INSERT, UPDATE ON TABLES TO c011_writer;
ALTER DEFAULT PRIVILEGES FOR ROLE c011_owner IN SCHEMA c011_data
  GRANT USAGE ON SEQUENCES TO c011_writer;
~~~

If c011_deploy creates a table before SET ROLE, its own creator defaults apply. Changing ownership afterward does not replay c011_owner's default grants. Repair existing ACLs explicitly, then correct the creation process.

Schema-specific default grants add to global defaults; a schema-specific revoke cannot undo a globally granted default. Audit pg_default_acl with the creator and schema scope. The lab establishes defaults before creating fixtures and tests a second table created through the migration login.

## 7. Diagnose a permission incident from evidence

Begin with the actual application login and database. Collect session_user/current_user, object identity, SQLSTATE, schema/table/sequence privileges and membership edges. The accompanying inventory performs read-only catalog queries, with timeouts and no password-catalog reads.

| Symptom | Evidence | Targeted mitigation |
|---|---|---|
| Permission denied for schema | Schema USAGE and effective memberships | Grant required schema access to the intended runtime group |
| Permission denied for relation | Ownership, ACL, PUBLIC and group paths | Repair the specific object/group grant |
| Permission denied for sequence | Sequence used by the insert default | Grant the required sequence operation |
| Must be owner | Object owner and execution identity | Use the approved migration/owner path |
| New table inaccessible | Creator identity and default ACL scope | Fix current ACLs and future-object creation |
| SET ROLE denied | SET options through membership paths | Correct only an approved role-assumption path |
| Revoked privilege still available | Direct, PUBLIC, nested or column grants; current role | Remove the actual contributing path after impact review |
| Reader sees more rows than intended | RLS policies, role attributes and ownership | Investigate policy/owner behavior; object ACL alone is insufficient |

SQLSTATE 42501 denotes insufficient privilege. An authentication error, missing relation or read-only-transaction error is not evidence of correct least privilege. The lab's negative tests accept only 42501 and fail if the forbidden operation unexpectedly succeeds.

## 8. Provisioning, revocation and retirement in production

Document the access matrix, object-creation role, membership options and account owner. Review current grants and PUBLIC defaults, then apply narrowly scoped changes through the authorized administrative identity. Capture the previous ACLs/options so a compensating change can restore the exact prior state.

Use real restricted logins for acceptance. Testing through an administrator with SET ROLE can explain authorization but does not verify the application's authentication path. Reconnect pool sessions when login defaults or connection eligibility change.

Revoking one group membership does not remove every possible privilege path. Disabling LOGIN prevents new sessions but does not terminate existing sessions. Revoking CONNECT similarly does not disconnect already connected clients. Membership/privilege changes should be tested in fresh sessions and, where relevant, existing sessions; they do not cancel an already running statement.

For retirement, inventory owned objects and grants in every database. REASSIGN OWNED and DROP OWNED have different effects: reassignment transfers ownership, while DROP OWNED can destroy owned objects and revoke grants. They must be planned per database; reassignment also has documented effects on shared objects such as databases/tablespaces. Default ACLs and grants still need attention. Never use DROP OWNED ... CASCADE as an unexplained cleanup shortcut.

The isolated lab drops its dedicated database before dropping its dedicated roles. Production retirement should preserve required data and has a different approval and dependency-review boundary.

**Stop conditions:** unexpected owner membership for a runtime identity, proposed SUPERUSER/BYPASSRLS/CREATEROLE to fix ordinary object access, unknown dependencies, privilege leakage through PUBLIC, or inability to test the actual service identity. Preserve evidence and resolve the missing contract before broadening authority.

## 9. Monitoring and acceptance

Track unexpected membership options, changes to powerful attributes, runtime ownership, object grants to PUBLIC, and missing future-object grants. Alert on application authorization failures separately from authentication failures. Retain grantor/change references and review emergency exceptions on a defined schedule.

The lab passes when real runtime connections can read/insert/update, cannot delete/truncate/create/alter/assume ownership/delegate membership, and can access a future table created by the authorized owner. It also demonstrates lost access after membership revocation, restoration through the original explicit grant, and complete cleanup.

A pass does not establish RLS correctness, function safety, every database's access model or security of client credentials. Those require their own tests.

## 10. Official references

The latest stable documentation currently identifies PostgreSQL 18; examples use version-pinned links.

- [Role attributes](https://www.postgresql.org/docs/18/role-attributes.html)
- [Role membership](https://www.postgresql.org/docs/18/role-membership.html)
- [CREATE ROLE](https://www.postgresql.org/docs/18/sql-createrole.html)
- [GRANT](https://www.postgresql.org/docs/18/sql-grant.html)
- [Object privileges](https://www.postgresql.org/docs/18/ddl-priv.html)
- [SET ROLE](https://www.postgresql.org/docs/18/sql-set-role.html)
- [Default privileges](https://www.postgresql.org/docs/18/sql-alterdefaultprivileges.html)
- [pg_auth_members](https://www.postgresql.org/docs/18/catalog-pg-auth-members.html)
- [Privilege inquiry functions](https://www.postgresql.org/docs/18/functions-info.html)
- [Role retirement](https://www.postgresql.org/docs/18/role-removal.html)
- [REASSIGN OWNED](https://www.postgresql.org/docs/18/sql-reassign-owned.html)
- [DROP OWNED](https://www.postgresql.org/docs/18/sql-drop-owned.html)

**Next:** Chapter 012 — pg_hba.conf, Authentication and Connection Diagnosis.
