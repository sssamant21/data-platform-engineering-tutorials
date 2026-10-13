# Chapter 077 — Authentication, pg_hba.conf, TLS and Connection Security Lab

**PostgreSQL 18 · Disposable lab only · Runtime pending**

## 1. Prerequisites and safety

Use a disposable PostgreSQL 18 instance with network access and an independently available administrative session. Provision a dedicated `ch077_lab` database and `ch077_app` login with an approved secret supplied outside Git. Generate a **lab-only** CA and a server certificate whose SAN matches the hostname clients will use. Keep private keys outside the repository. Do not edit production `pg_hba.conf`.

## 2. Baseline inspection

As an authorized administrator, run [077 inspection SQL](../labs/sql/077-authentication-tls-inspect.sql). Record `SHOW hba_file`, `SHOW ssl`, `SHOW password_encryption`, `pg_hba_file_rules` errors, certificate expiry and listener configuration.

## 3. Authentication policy

Review [example HBA file](../labs/config/077-pg-hba-example.conf) and adapt its subnet and roles to your lab. Preserve the original file, maintain an existing admin connection, check syntax and reload via the supported service process. Confirm **new connections** see the intended policy.

## 4. Positive test

From a lab client with the trusted CA, connect using `sslmode=verify-full` and the exact server certificate hostname. Confirm the expected database role and `pg_stat_ssl.ssl=true`. Validate database CONNECT and least-privilege table access.

## 5. Negative tests

- Attempt plaintext TCP (`sslmode=disable`): should be rejected.
- Attempt TLS with an untrusted CA: `verify-full` should fail.
- Attempt TLS with a mismatched hostname: `verify-full` should fail.
- Attempt incorrect password with the correct TLS settings: should fail.
- Attempt a nonallowlisted client source/role: should fail.
- Verify that a rejected first matching HBA rule does not fall through to a later permissive rule.

Record SQLSTATE or libpq error, client hostname, redacted logs and UTC time. Never include plaintext passwords or private keys in evidence.

## 6. Rotation and rollback

Rotate a **lab** password using a secure interactive method; test new and old secrets. Replace the lab certificate with a renewed certificate and verify client trust. Restore original HBA configuration and verify an approved connection. Record recovery from an intentionally invalid rule **without** locking out administration.

## 7. Acceptance

Complete [077 scorecard](../labs/acceptance/077-authentication-tls-scorecard.csv). Any skipped negative test remains NOT VERIFIED. A successful `pg_stat_ssl` query alone does not prove client-side hostname verification.

**Runtime:** pending.
