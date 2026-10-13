# Chapter 052 — Authentication, pg_hba.conf and TLS Security Lab

**PostgreSQL 18 · Disposable lab instance · Runtime validation pending.**

## 1. Preconditions

Use a dedicated PostgreSQL 18 server with administrator access, secure test credentials, trusted test CA and DNS hostname matching its server certificate. Preserve an independent administrative connection and known-good `pg_hba.conf` backup. Do not perform HBA edits on production.

## 2. Inspect current state

```powershell
psql -X -v ON_ERROR_STOP=1 -h localhost -U postgres -d postgres -f postgresql/labs/sql/052-inspect.sql
```

Record HBA path, TLS status, SCRAM default, HBA parse errors, active session TLS cipher and server log path.

## 3. Positive TLS test

```powershell
$env:PGSSLMODE = "verify-full"
$env:PGSSLROOTCERT = "C:\secure\certs\lab-ca.pem"
psql -h db.lab.internal -U ch052_app -d ch052_lab -c "SELECT current_user;"
```

Create `ch052_app` and `ch052_lab` only within a dedicated test instance using a secure password-management process. Never commit passwords.

## 4. Negative tests

- Connect with `sslmode=disable` from a network where only `hostssl` is allowed; expect denial.
- Connect with a hostname absent from the certificate using `sslmode=verify-full`; expect certificate hostname verification failure.
- Connect from an unapproved CIDR or using an unapproved role; expect rejection.
- Test an incorrect password with SCRAM; expect authentication failure.

Keep test secrets out of terminal history and captured evidence.

## 5. Controlled HBA change

1. Back up `pg_hba.conf` and include files.
2. Stage narrowly scoped `hostssl` SCRAM rule above explicit rejects.
3. Inspect `pg_hba_file_rules` and fix errors.
4. Reload using the approved admin procedure; confirm fresh sessions authenticate.
5. Recheck TLS cipher and PostgreSQL logs.
6. Restore known-good HBA, reload and verify the rollback path.

## 6. Acceptance worksheet

| Gate | Expected | Result |
|---|---|---|
| HBA parsed | No errors | |
| SCRAM password policy | scram-sha-256 | |
| Valid hostname and CA | verify-full succeeds | |
| Wrong hostname | Rejected | |
| Non-TLS connection | Rejected | |
| Unapproved source/role | Rejected | |
| Admin break-glass access | Preserved | |
| Replication/monitoring | Uninterrupted | |
| Rollback | Verified | |

**Runtime:** pending.
