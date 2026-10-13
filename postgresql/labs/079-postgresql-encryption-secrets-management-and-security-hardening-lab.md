# Chapter 079 — Encryption, Secrets Management and Security Hardening Lab

**PostgreSQL 18 · Disposable lab only · Runtime pending**

## 1. Safety and prerequisites

Use a disposable PostgreSQL 18 instance, a lab-only client and TLS CA, a lab secret store or simulated secret-version inventory, and encrypted test backup storage. Never publish passwords, private keys, CA signing keys or unredacted connection strings. Do not rotate production KMS keys, certificates or database secrets in this lab.

## 2. Inventory

Run [079 inspection SQL](../labs/sql/079-encryption-secrets-hardening-inspect.sql). Record server version, TLS settings, password policy, roles, extensions, logging and UTC timestamp. Separately inventory data/WAL/backup volume encryption, key custody, snapshots, offsite backups, OS user, firewall and patch baseline.

## 3. TLS verification

Connect from a test client with `sslmode=verify-full`, trusted CA and matching hostname. Confirm the active backend appears in `pg_stat_ssl`. Test an untrusted CA and mismatched hostname; both must fail. Verify proxy-to-database and replication TLS separately when present.

## 4. Credential rotation

Provision a new **lab-only** login secret through a secure channel. Validate a new connection, update the simulated application consumer, retire the old credential and verify it fails. Observe existing pooled sessions and document their termination/reconnection policy. Never store real secrets in the evidence file.

## 5. TLS certificate rotation

Prepare a new leaf certificate for the same lab hostname, validate the SAN and trust chain, install using the supported PostgreSQL service procedure, reconnect clients and inspect the negotiated TLS version/cipher. Test rollback using an authorized old certificate only while it remains valid.

## 6. Backup and encryption verification

Create an encrypted backup of disposable test data. Verify independent key access and perform an isolated restore. Capture backup integrity result, restored transaction marker, key version and restore time. Simulate missing-key recovery in a tabletop exercise; do not delete or revoke real keys.

## 7. Privilege and host hardening

Inspect dangerous role capabilities, extension inventory, public schema CREATE, `SECURITY DEFINER` ownership and audit logging. Check filesystem permissions, process user, container privilege boundaries and firewall **outside SQL**. Document which checks cannot be performed in your environment.

## 8. Acceptance and cleanup

Complete [hardening checklist](../labs/acceptance/079-security-hardening-checklist.csv) and [rotation evidence](../labs/acceptance/079-secret-and-key-rotation-evidence.md). Remove only disposable lab resources after recording redacted evidence.

**Runtime:** pending. External encryption/KMS/OS controls require independent proof.
