# Chapter 077 — PostgreSQL Authentication, pg_hba.conf, TLS and Connection Security

**Track:** PostgreSQL DBRE/SRE | **Baseline:** PostgreSQL 18 | **Status:** Authored; runtime validation pending

## 1. Mission

Protect PostgreSQL connections with narrowly scoped host-based authentication, SCRAM-SHA-256, TLS server identity validation, protected credentials, controlled certificate rotation and auditable connection tests. Builds on [Chapter 076 — Security Architecture](076-postgresql-security-architecture-roles-and-privileges.md).

**Security invariant:** a valid password must not bypass a requirement for an encrypted, authenticated connection to the intended server.

## 2. Connection security layers

```text
Application / libpq
    -> DNS + network allowlist + firewall
    -> TLS negotiation + certificate validation
    -> pg_hba.conf FIRST matching record
    -> authentication method (SCRAM / certificate / other approved)
    -> LOGIN role and database CONNECT
    -> schema/object grants and optional RLS
```

Authentication is distinct from authorization. TLS encryption without server identity verification does not establish that the client connected to the correct server.

## 3. pg_hba.conf: first match wins

PostgreSQL evaluates records in order. The **first** record matching connection type, database, user and address is selected. If authentication then fails, PostgreSQL does **not** fall through to a later record.

Illustrative **lab-only** policy (replace subnet, roles, database and certificate paths):

```conf
# TYPE     DATABASE      USER             ADDRESS           METHOD
local      all           postgres                           peer
hostnossl  ch077_lab     all              0.0.0.0/0         reject
hostssl    ch077_lab     ch077_app        10.77.0.0/24      scram-sha-256
hostssl    ch077_lab     ch077_admin      10.77.0.0/24      scram-sha-256
```

For IPv6, create explicit matching entries where appropriate. The `hostnossl` reject example affects the named database only; do not treat it as a global policy. `hostssl` matches TLS connections only when server SSL is enabled. Avoid permissive `host all all 0.0.0.0/0 trust` or unreviewed wildcard access. Review managed-service limitations: some providers control HBA/TLS policy outside the instance.

### Inspect and validate safely

```sql
SHOW hba_file;
SELECT line_number,type,database,user_name,address,auth_method,error
FROM pg_hba_file_rules ORDER BY line_number;
```

Inspect parse errors before and after an approved reload. `pg_reload_conf()` signals a reload; verify active behavior using fresh client connections and server logs. Avoid edits that lock out all administrators. Keep an existing privileged session and an independently tested rollback path.

## 4. SCRAM-SHA-256

Use `password_encryption='scram-sha-256'` when creating or rotating password verifiers, then require `scram-sha-256` in HBA for relevant TCP clients. Merely changing `password_encryption` does **not** rewrite existing stored verifiers. Rotate legacy MD5 passwords and confirm driver compatibility before enforcement.

```sql
SHOW password_encryption;
-- Authorized lab administrator, with a secret supplied securely:
ALTER ROLE ch077_app PASSWORD :'new_password';
```

Never put a real password into repository SQL, terminal history, URLs, logs or screenshots. Prefer a secrets manager and rotation automation. Use `\password` interactively in psql when appropriate to avoid placing plaintext passwords in SQL command history.

## 5. TLS and identity verification

Server-side TLS requires `ssl=on`, a valid private key/certificate and secure filesystem permissions. Validate certificate hostname/SAN, trust chain, expiry and key custody. Prefer client `sslmode=verify-full` with an explicit trusted root CA; `require` encrypts but does not provide the same reliable hostname verification.

Example libpq connection:

```bash
psql "host=db.example.internal port=5432 dbname=ch077_lab user=ch077_app sslmode=verify-full sslrootcert=/secure/path/ca.crt"
```

The certificate must match the **host** in the connection string. Do not silently downgrade to `sslmode=prefer` or `require` to bypass a verification failure. For local Unix sockets, TLS mode is not a substitute for local peer/OS authentication policy.

## 6. Certificate-based client authentication

When mutual TLS is required, configure `ssl_ca_file` and `clientcert=verify-full` on the appropriate `hostssl` HBA record; pair with an approved authentication method and identity mapping. `cert` authentication requires an authenticated client certificate and maps certificate identity to database identity, optionally through `pg_ident.conf`. Verify SAN/CN mapping behavior and client certificate expiration with your PostgreSQL version and policy. Do not conflate server certificate verification with client certificate authentication.

## 7. Connection-string and secret hygiene

- Use dedicated service identities, short-lived credentials where supported, rotation and revocation.
- Avoid `PGPASSWORD` for persistent automation; use managed secrets or a tightly permissioned `PGPASSFILE`.
- Restrict `.pgpass` / passfile permissions; libpq rejects insecure Unix passfiles.
- Protect certificates, private keys and CA bundles separately.
- Avoid secrets in shell command arguments, environment dumps, connection URIs and CI logs.
- Ensure proxies and connection pools enforce TLS **on each hop**, not just client-to-proxy.
- Monitor session counts, authentication failures and certificate expiry.

## 8. Runtime verification

From an authorized session:

```sql
SELECT a.pid,a.usename,a.client_addr,s.ssl,s.version,s.cipher
FROM pg_stat_activity a
JOIN pg_stat_ssl s USING(pid)
WHERE a.datname=current_database();
```

`pg_stat_ssl.ssl` confirms TLS for the backend connection; it does not prove that the **client** validated the server certificate hostname. Validate client-side `verify-full` separately using trusted/untrusted CA and wrong-hostname tests.

## 9. Authentication troubleshooting

| Symptom | Likely cause | Safe next step |
|---|---|---|
| No pg_hba.conf entry | Missing matching host/db/user/CIDR/TLS record | Inspect rule order and client source address |
| Password authentication failed | Wrong secret, disabled login or verifier mismatch | Check role LOGIN, rotation and SCRAM compatibility |
| SSL off but hostssl only | Client did not negotiate TLS | Use explicit verify-full; check server SSL |
| Certificate verify failed | Wrong CA, expired cert or hostname mismatch | Repair trust chain/hostname, do not downgrade |
| Peer authentication failed | OS user does not map to database user | Check local HBA and identity mapping |
| Connection refused / timeout | Listener, firewall, DNS or proxy | Check transport before HBA |
| TLS works but query denied | Authorization failure | Audit role membership, CONNECT, schema/table grants |

Do not expose secrets while collecting logs. Review `log_connections`, `log_disconnections` and authentication error logs under approved retention controls.

## 10. Safe change and rollback runbook

1. Inventory current HBA/TLS policy, client drivers, service identities and certificates.
2. Confirm rollback access and preserve the original config securely.
3. Validate certificate chain, hostname and client trust distribution in staging.
4. Add narrow HBA rules **before** removing old ones, with reviewed ordering and expiry plan.
5. Check `pg_hba_file_rules.error`, reload if appropriate, test **new** connections.
6. Verify TLS and authentication from each application/proxy path; test deliberate denials.
7. Rotate passwords/certificates through approved procedures, accounting for connection pools.
8. Remove temporary rules, capture evidence and update the runbook.

## 11. Lab and acceptance

Use [Chapter 077 lab](../labs/077-postgresql-authentication-pg-hba-conf-tls-and-connection-security-lab.md), [read-only SQL](../labs/sql/077-authentication-tls-inspect.sql), [example HBA policy](../labs/config/077-pg-hba-example.conf) and [acceptance scorecard](../labs/acceptance/077-authentication-tls-scorecard.csv).

**PASS requires:** successful approved SCRAM+TLS login; plaintext TCP rejection; invalid CA and hostname rejection; correct first-match HBA ordering; least-privilege role permissions; TLS session visibility; and documented rollback. Runtime validation pending.

## References

- https://www.postgresql.org/docs/18/auth-pg-hba-conf.html
- https://www.postgresql.org/docs/18/auth-password.html
- https://www.postgresql.org/docs/18/ssl-tcp.html
- https://www.postgresql.org/docs/18/libpq-ssl.html
- https://www.postgresql.org/docs/18/monitoring-stats.html

**Next:** Chapter 078 — PostgreSQL Row-Level Security, Data Protection and Audit Controls.
