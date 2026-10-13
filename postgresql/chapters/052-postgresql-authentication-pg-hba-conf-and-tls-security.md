# Chapter 052 — PostgreSQL Authentication, pg_hba.conf and TLS Security

**Track:** PostgreSQL DBRE/SRE · **Baseline:** PostgreSQL 18 · **Status:** Authored; runtime validation pending

## 1. Mission

Secure PostgreSQL client connections with explicit host-based authentication, SCRAM-SHA-256 password verification, TLS server identity validation and a reversible change procedure. This chapter follows [Chapter 051 — Security Architecture, Roles and Privilege Boundaries](051-postgresql-security-architecture-roles-and-privilege-boundaries.md).

## 2. Authentication architecture

```text
Client / application
    |
    | TCP / Unix-domain socket / Windows local connection
    v
Network boundary -> TLS handshake (if negotiated)
    |
    v
pg_hba.conf FIRST matching rule
    |
    +--> reject
    +--> scram-sha-256 / certificate / peer / other supported method
    |
    v
Role LOGIN + database CONNECT + object authorization
```

**Authentication is not authorization.** Successful SCRAM or certificate authentication does not imply SELECT, DDL or schema access. Network firewalls, PostgreSQL `listen_addresses`, `pg_hba.conf`, database CONNECT and role permissions are separate controls.

## 3. pg_hba.conf matching rules

PostgreSQL processes HBA records **in order**, using the first record matching connection type, database, user and client address. If that rule's authentication fails, PostgreSQL does **not** fall through to a later permissive rule. File includes and their ordering matter.

| Connection type | Purpose |
|---|---|
| `local` | Unix-domain socket connections (not ordinary TCP localhost) |
| `host` | TCP, with or without TLS |
| `hostssl` | TCP using SSL/TLS |
| `hostnossl` | TCP without TLS |
| `hostgssenc` / `hostnogssenc` | GSSAPI encryption distinction |

Windows installations generally use TCP for local client connections. A `hostssl` entry requires PostgreSQL server TLS enabled; otherwise it cannot match TLS connections.

**Example policy (illustrative; adapt actual CIDRs and roles):**

```conf
# TYPE     DATABASE    USER          ADDRESS           METHOD
hostssl    appdb       app_runtime   10.20.0.0/16      scram-sha-256
hostssl    appdb       app_readonly  10.30.0.0/16      scram-sha-256
host       all         all           0.0.0.0/0         reject
host       all         all           ::/0              reject
```

Do not copy these CIDRs or reject-all entries blindly: a misordered rule can lock out administration, monitoring and replication. Keep a validated break-glass route before changing rules. Include explicit replication connection rules if physical replication uses a separate identity.

## 4. SCRAM-SHA-256 and password lifecycle

Prefer `scram-sha-256` over MD5 for password authentication. Set `password_encryption = 'scram-sha-256'` **before setting/rotating passwords** so new stored verifiers use SCRAM. Merely changing the setting does not convert existing MD5 verifiers; affected roles must rotate their passwords. Avoid `trust`, plaintext `password`, and broad access rules for production.

```sql
SHOW password_encryption;
SELECT rolname,rolcanlogin,rolvaliduntil FROM pg_roles WHERE rolcanlogin ORDER BY rolname;
```

Use managed secret storage and rotation. Never commit database passwords, place secrets directly in command histories or expose `pg_authid.rolpassword` to logs. Password rotation should be tested with connection pools and rolling application restarts.

## 5. TLS server identity and client options

```sql
SHOW ssl;
SHOW ssl_min_protocol_version;
SHOW ssl_cert_file;
SHOW ssl_key_file;
```

For `libpq`, prefer **`sslmode=verify-full`** with a trusted CA (`sslrootcert`) and a hostname matching the certificate SAN/CN. `verify-ca` validates certificate chain but not hostname; `require` encrypts transport but does not provide the same explicit hostname-verification guarantee. Avoid `disable`, `allow` and `prefer` for security-sensitive applications where TLS is mandatory.

```powershell
# Configure environment-specific certificate path and identity via secure secret handling.
psql "host=db.example.internal port=5432 dbname=appdb user=app_runtime sslmode=verify-full sslrootcert=C:/secure/certs/ca.pem" -c "SELECT current_user, inet_client_addr();"
```

The hostname must match the certificate. For managed services, use the provider's CA bundle and TLS policy; do not disable verification to work around trust-chain errors. Mutual TLS uses `clientcert=verify-full` on applicable HBA records plus suitable authentication mapping; client certificates and SCRAM can be combined when required.

## 6. Observability and diagnostics

```sql
SELECT ssl,version,cipher,bits,client_dn
FROM pg_stat_ssl WHERE pid=pg_backend_pid();

SELECT line_number,type,database,user_name,address,auth_method,error
FROM pg_hba_file_rules ORDER BY line_number;
```

`pg_hba_file_rules` parses the **current file contents**, which may differ from the last successfully loaded configuration. Review parse errors, then use an approved `SELECT pg_reload_conf();` or service reload and verify connection behavior. Inspect PostgreSQL logs for rejected authentication, HBA mismatches, expired certificates and TLS handshake failures. Restrict log access because connection details may be sensitive.

## 7. Controlled change procedure

1. Inventory application identities, CIDRs, replicas, poolers, break-glass accounts and active HBA rules.
2. Record current `SHOW hba_file`, TLS settings, certificate validity and HBA parse results.
3. Stage a **backed-up** candidate HBA file; review first-match ordering and syntax, including included files.
4. Test from the actual source networks with valid credentials and `sslmode=verify-full`. Confirm non-TLS and unauthorized sources are denied.
5. Apply approved configuration, reload if appropriate, and check server logs and `pg_hba_file_rules` errors.
6. Verify new sessions (existing sessions are not necessarily reauthenticated), replication, monitoring, applications and connection pools.
7. Roll back from the known-good file if critical clients fail, reload and repeat validation.

**Abort conditions:** administrative lockout, unknown HBA parse error, certificate mismatch, replication connection failure, widespread authentication errors or unapproved CIDR expansion.

## 8. Common incidents

| Symptom | Possible cause | Investigation |
|---|---|---|
| `no pg_hba.conf entry` | Missing/misordered source, DB or user rule | Check client IP, HBA first match and TLS mode |
| `password authentication failed` | Incorrect secret, verifier mismatch, expired account | Verify role and SCRAM rotation path |
| `certificate verify failed` | CA trust or hostname mismatch | Verify chain, SAN and sslrootcert |
| TLS expected but disabled | Server `ssl=off` or client sslmode | Check server and session `pg_stat_ssl` |
| Replication breaks after change | Replication HBA rule omitted | Inspect walreceiver logs and replication identity |
| Authentication errors after rotation | Stale pooler/application credentials | Roll out secret updates and recycle connections |
| HBA edits appear ignored | File not reloaded or wrong include order | Inspect hba_file and parse diagnostics |

## 9. Lab and acceptance

[Chapter 052 lab](../labs/052-postgresql-authentication-pg-hba-conf-and-tls-security-lab.md) includes read-only SQL diagnostics, PowerShell connection probes and an HBA/TLS change acceptance checklist. HBA edits and certificate creation remain controlled, manual exercises in a disposable PostgreSQL 18 environment.

**Acceptance:** verified TLS hostname, SCRAM identity, expected HBA match, unauthorized connection rejection, and successful rollback test. **Runtime:** pending.

## Official references

- [Client authentication](https://www.postgresql.org/docs/18/client-authentication.html)
- [pg_hba.conf](https://www.postgresql.org/docs/18/auth-pg-hba-conf.html)
- [SCRAM](https://www.postgresql.org/docs/18/sasl-authentication.html)
- [SSL support](https://www.postgresql.org/docs/18/ssl-tcp.html)
- [libpq SSL](https://www.postgresql.org/docs/18/libpq-ssl.html)

**Next:** Chapter 053 — PostgreSQL Row-Level Security and Secure Application Access.
