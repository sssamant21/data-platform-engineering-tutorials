# Chapter 081 — PostgreSQL Extensions, Compatibility and Operational Lifecycle

**Track:** PostgreSQL DBRE/SRE | **Baseline:** PostgreSQL 18 | **Status:** Authored; runtime validation pending

## 1. Mission

Operate PostgreSQL extensions safely across installation, configuration, upgrade, migration, backup/restore and retirement. Extensions can add SQL functions, operators, index types, background workers, shared libraries and elevated security exposure. Treat them as **versioned software dependencies**, not merely SQL objects.

## 2. Architecture and inventory

```text
PostgreSQL server version / ABI
           |
 extension control file + SQL scripts + optional shared library
           |
   CREATE EXTENSION / ALTER EXTENSION UPDATE
           |
 SQL objects, dependencies, privileges, application usage
           |
 HA replicas + backups + pg_upgrade + rollback plan
```

Inspect installed extensions and available versions:

```sql
SELECT e.extname,e.extversion,n.nspname AS schema,e.extrelocatable
FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace
ORDER BY e.extname;

SELECT name,default_version,installed_version,comment
FROM pg_available_extensions ORDER BY name;

SELECT name,version,installed,superuser,trusted,relocatable,requires
FROM pg_available_extension_versions ORDER BY name,version;
```

An extension can be **available on the server** without being installed in a particular database. `pg_extension` is database-local; inventory every database, not only `postgres`. Files and binaries are installed at the server level.

## 3. Extension categories and operational risk

| Category | Examples | Operational consideration |
|---|---|---|
| Built-in/contrib | `pg_stat_statements`, `pg_trgm`, `citext` | Server packages and extension SQL versions |
| SQL-only | Application-provided SQL extensions | Ownership, dependency and upgrade scripts |
| Native/shared library | Extensions with C modules | PostgreSQL major-version ABI and OS packages |
| Preloaded/background | `pg_stat_statements`, some third-party agents | `shared_preload_libraries` and restart |
| Custom index/access methods | Third-party index extensions | Reindex and compatibility/restore risks |
| Managed-service allowlisted | Provider-approved subset | Feature availability differs by service/version |

Do not assume that all extensions are trusted, relocatable or safe for non-superusers. Review extension control metadata, install scripts, SECURITY DEFINER functions and vendor security advisories.

## 4. Dependencies and privileges

Extension members are tracked in `pg_depend`. Objects belonging to an extension are typically managed through extension lifecycle commands, not independent drops. Inspect dependencies before `DROP EXTENSION`; never use `CASCADE` casually because it can remove application objects. A trusted extension may be installable by a role with `CREATE` on the database, subject to extension and schema requirements; nontrusted extensions may require superuser/provider administration.

```sql
SELECT e.extname,c.classid::regclass AS catalog,c.objid,c.deptype
FROM pg_depend c JOIN pg_extension e ON e.oid=c.refobjid
WHERE c.refclassid='pg_extension'::regclass
ORDER BY e.extname,c.classid::regclass::text,c.objid;
```

Audit function EXECUTE privileges and `search_path`; use a trusted target schema and restrict CREATE permissions for untrusted users. An extension's install/upgrade scripts may execute with elevated privileges.

## 5. Installation and configuration workflow

1. Verify supported PostgreSQL major/minor version, OS/architecture, extension version and vendor support matrix.
2. Install matching server-side extension package/binary **on every node that might run it**; plan managed-service alternatives.
3. Confirm `pg_available_extension_versions` lists the intended version.
4. For preloaded extensions, change `shared_preload_libraries` under change control and restart the required instances; check `pending_restart`.
5. Create the extension in the intended database/schema using an approved owner.
6. Verify `pg_extension`, application behavior, permissions, monitoring and replica compatibility.

Example **disposable lab only**:

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;
SELECT extname,extversion FROM pg_extension WHERE extname='pg_trgm';
```

The `public` schema is illustrative for a disposable lab, not a recommendation to expose untrusted schema CREATE in production.

## 6. Upgrade lifecycle

`ALTER EXTENSION name UPDATE [TO 'version']` runs packaged extension update scripts. The available update path can be inspected with:

```sql
SELECT * FROM pg_extension_update_paths('pg_trgm');
```

**Do not assume extension updates are reversible.** A downgrade path may not exist; rollback may require restoring a database/cluster backup or rebuilding objects. Native library upgrades may also require package replacement, restart or reindex. Read release notes and migration scripts; test representative data, query plans and application operations.

## 7. PostgreSQL major upgrade compatibility

Before `pg_upgrade`, verify compatible extension libraries and control files are installed in the new PostgreSQL installation and that vendor-supported upgrade paths exist. Follow `pg_upgrade --check` and review generated post-upgrade scripts. Extensions that store data in custom formats, background workers or specialized indexes can require extra procedures. Validate replica rebuild, logical/physical backup recovery and monitoring agent compatibility. For managed services, check the provider-specific supported versions and upgrade order.

## 8. Backup, restore and DR

Logical dumps usually represent extension membership with `CREATE EXTENSION` rather than dumping every extension-owned object. Restore environments need the extension binaries/control files and compatible versions. Physical backup/PITR preserves database state but target PostgreSQL and extension binaries must remain compatible. Verify extension availability in DR regions and restore tests before declaring recoverability.

## 9. Performance and troubleshooting

| Symptom | Likely cause | Safe response |
|---|---|---|
| `extension ... is not available` | Missing server-side package/control file | Install supported package; check server filesystem |
| `could not load library` | Missing/incompatible binary or dependency | Check PostgreSQL ABI and OS libraries |
| Upgrade path missing | No update script between versions | Consult vendor matrix; do not force version metadata |
| Requires shared_preload_libraries | Extension initializes at startup | Plan config change/restart |
| Permission denied | CREATE, schema or superuser requirement | Use approved admin; avoid broad grants |
| Query slowdown after update | Changed operator/index behavior | Compare plans, stats and indexes; test reindex if documented |
| Restore fails | Missing extension/version in target | Prepare target package and restore rehearsal |

## 10. Production runbook

Capture baseline installed versions, server/OS package versions, extension dependencies, backup age and rollback. Rehearse change in staging; approve outage/restart/reindex requirements; deploy binaries to all nodes; apply database-level update in the correct order; test SQL behavior, app workflows and failover; monitor and sign off. Never change `pg_extension.extversion` directly to bypass migration scripts.

## 11. Lab and acceptance

Use [Chapter 081 lab](../labs/081-postgresql-extensions-compatibility-and-operational-lifecycle-lab.md), [extension inspection SQL](../labs/sql/081-extension-lifecycle-inspect.sql), [compatibility matrix](../labs/acceptance/081-extension-compatibility-matrix.csv) and [acceptance scorecard](../labs/acceptance/081-extension-lifecycle-scorecard.csv).

**PASS requires:** full inventory, supported version matrix, verified installation and dependency visibility, tested upgrade path where available, backup/restore and DR compatibility evidence, rollback plan and application smoke tests. Runtime validation pending.

## References

- https://www.postgresql.org/docs/18/extend-extensions.html
- https://www.postgresql.org/docs/18/sql-createextension.html
- https://www.postgresql.org/docs/18/sql-alterextension.html
- https://www.postgresql.org/docs/18/view-pg-available-extension-versions.html
- https://www.postgresql.org/docs/18/pgupgrade.html

**Next:** Chapter 082 — PostgreSQL Version Upgrades, Compatibility Testing and Rollback Planning.
