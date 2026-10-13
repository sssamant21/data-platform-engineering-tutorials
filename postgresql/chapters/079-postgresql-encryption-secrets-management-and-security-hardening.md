# Chapter 079 — PostgreSQL Encryption, Secrets Management and Security Hardening

**Track:** PostgreSQL DBRE/SRE | **Baseline:** PostgreSQL 18 | **Status:** Authored; runtime validation pending

## 1. Mission

Design and verify PostgreSQL security across **data in transit, data at rest, credentials, encryption keys, backups, hosts and administrative operations**. Extend [Chapter 076 — Roles](076-postgresql-security-architecture-roles-and-privileges.md), [Chapter 077 — TLS and Authentication](077-postgresql-authentication-pg-hba-conf-tls-and-connection-security.md) and [Chapter 078 — RLS and Audit](078-postgresql-row-level-security-data-protection-and-audit-controls.md).

## 2. Threat model and control boundaries

| Threat | Primary controls | Residual risk |
|---|---|---|
| Network interception | TLS, verify-full, trusted CA, strict HBA | Compromised client or CA |
| Stolen disks/snapshots | Volume/snapshot encryption and key access control | DB sessions still see plaintext |
| Backup theft | Encrypted backups and offsite key isolation | Lost keys make recovery impossible |
| Secret exposure | Vault/Secrets Manager, least privilege, rotation | Secrets in logs/process environment |
| Privilege escalation | Role separation, patching, safe extensions | Superuser and host compromise |
| Ransomware | Immutable copies, separate backup identity, PITR | Shared admin/control plane |
| Host compromise | OS hardening, private networking, service account controls | Root can inspect DB processes/data |

**Important:** Standard community PostgreSQL does not offer a general-purpose built-in transparent data encryption feature for all heap/index/WAL files. Encryption at rest is normally provided by storage/cloud/OS layers, or by carefully designed application/column encryption for particular fields. Verify any provider- or extension-specific TDE claims separately.

## 3. Encryption in transit

Enable TLS on PostgreSQL and every application/proxy/replication hop. Prefer `sslmode=verify-full` on libpq clients and validate SAN/hostname and trust chain. `pg_stat_ssl` proves TLS was negotiated, **not** that the client verified the server identity. Monitor certificate expiry, cipher/protocol policy and key permissions.

```sql
SHOW ssl;
SHOW ssl_min_protocol_version;
SELECT a.usename,a.client_addr,s.ssl,s.version,s.cipher
FROM pg_stat_activity a JOIN pg_stat_ssl s USING(pid)
WHERE a.datname=current_database();
```

For TLS termination at a proxy, inspect **both** client-to-proxy and proxy-to-PostgreSQL legs. Do not silently downgrade to `sslmode=require` after certificate failures.

## 4. Encryption at rest

Evaluate data directory, WAL, temporary files, snapshots, crash dumps and replica volumes. Encrypt disks/volumes and backups with keys governed independently from the database administrator. Document cloud KMS/Key Vault policy, key rotation, revocation, recovery and disaster-region availability. Storage encryption does not replace SQL permissions, RLS or column controls.

For highly sensitive fields, application-side envelope encryption can reduce plaintext exposure inside the database; assess indexing/queryability, key access, rotation and application error paths. `pgcrypto` offers cryptographic functions but does not transparently encrypt all PostgreSQL storage, and server-side decryption can expose plaintext to database processes.

## 5. Backup encryption and key recovery

Encrypt backup artifacts and copied WAL, including cross-region copies. Restrict decrypt permissions and maintain key version/identifier metadata. Test an isolated restore using the exact key path required after loss of the primary region. Verify backup integrity, WAL archive continuity, key availability, restore duration and retention. A backup whose decryption key cannot be recovered is **not** an accepted backup.

## 6. Secrets management

Use a managed secret store or approved vault with separate application, migration, replication, monitoring and backup identities. Avoid plaintext passwords in Git, container images, IaC state, URLs, terminal history and incident logs. Prefer short-lived or automatically rotated credentials where supported, and limit secret-reader permissions to the relevant workload identity.

Credential rotation sequence:

1. Inventory dependencies: app pools, HA manager, replicas, exporters, jobs and backup agents.
2. Provision the new secret through a controlled channel; validate authentication in a fresh session.
3. Coordinate deployment and pool reconnection; observe failures and old-session persistence.
4. Revoke old credentials after confirming consumers migrated; record evidence.
5. Verify secret version, ownership, expiration, alerting and rollback procedure.

For zero-downtime rotation, use **two distinct login roles** or provider-specific rotation workflows when appropriate; `ALTER ROLE ... PASSWORD` replaces one password verifier and does not support overlapping passwords for the same role.

## 7. Certificate and key rotation

Maintain separate inventories for TLS private keys, CA roots, storage encryption keys and backup encryption keys. A TLS leaf certificate rotation is different from a CA rotation; distribute new trust before replacing the certificate when possible. Validate client hostname verification, replication links, proxy connectivity and rollback. Plan for key compromise: revoke access, rotate credentials, re-encrypt where necessary and assess historical snapshot/backup exposure.

## 8. Host, container and managed-service hardening

- Run PostgreSQL as a dedicated non-root OS identity with restricted data directory and key permissions.
- Restrict inbound network paths to known application, management and replication sources.
- Apply supported PostgreSQL/OS patches and security advisories; test minor-version upgrades.
- Restrict `shared_preload_libraries`, `CREATE EXTENSION`, untrusted procedural languages and privileged extensions.
- Minimize superusers, `CREATEROLE`, `BYPASSRLS`, `pg_read_server_files`, `pg_write_server_files` and `pg_execute_server_program`.
- Protect audit logs, metrics, core dumps and database error messages from exposing secrets.
- Review `search_path`, `SECURITY DEFINER` functions, public schema CREATE, RLS bypass and default privileges.
- For containers, use read-only root filesystems where compatible, scoped mounts, non-root runtime, admission policy and restricted Kubernetes secrets/RBAC.
- In managed PostgreSQL, document which controls belong to the cloud provider and which remain customer responsibilities.

## 9. Security posture inspection

Use [079 read-only inspection SQL](../labs/sql/079-encryption-secrets-hardening-inspect.sql) for SSL, logging, password encryption, role capabilities, preload libraries and extension inventory. Complement SQL with **external evidence** for storage encryption, KMS policies, secret store access, backup encryption, firewall, OS patches and filesystem permissions. SQL cannot prove those controls.

## 10. Hardening runbook

1. Inventory production assets, service accounts, regions, replicas, storage, backups and key stores.
2. Assign risk severity and owner for each gap; never paste secrets into tickets.
3. Verify recovery path before modifying keys, HBA, certificates or storage configuration.
4. Implement changes in staging, test app/proxy/replication connectivity and restore.
5. Apply changes through approved maintenance and rollback windows.
6. Verify expected denies, TLS, credential rotation and backup decryption.
7. Preserve redacted evidence and re-run audits after upgrades or configuration drift.

## 11. Lab and acceptance

Use [Chapter 079 lab](../labs/079-postgresql-encryption-secrets-management-and-security-hardening-lab.md), [inspection SQL](../labs/sql/079-encryption-secrets-hardening-inspect.sql), [hardening checklist](../labs/acceptance/079-security-hardening-checklist.csv) and [rotation evidence template](../labs/acceptance/079-secret-and-key-rotation-evidence.md).

**PASS requires:** encrypted and identity-verified connections; independently evidenced storage/backup encryption; working secret and TLS rotation; secure privileges; backup decryption/restore; and safe rollback. Mark cloud/OS controls NOT VERIFIED if only SQL was inspected. Runtime validation pending.

## References

- https://www.postgresql.org/docs/18/ssl-tcp.html
- https://www.postgresql.org/docs/18/libpq-ssl.html
- https://www.postgresql.org/docs/18/auth-password.html
- https://www.postgresql.org/docs/18/encryption-options.html
- https://www.postgresql.org/docs/18/pgcrypto.html
- https://www.postgresql.org/docs/18/predefined-roles.html

**Next:** Chapter 080 — PostgreSQL Security Operations, Incident Response and Compliance Acceptance Project.
