# Chapter 079 — Secret and Key Rotation Evidence

**Status:** NOT EXECUTED / NOT VERIFIED

## Environment
- PostgreSQL version:
- Lab host / client:
- Secret store (name only):
- TLS CA identifier (not private key):
- Storage/backup key identifier (not key material):
- Approved change and owner:
- UTC execution window:

## Credential rotation
- Old credential version ID (redacted):
- New credential version ID (redacted):
- New connection succeeds:
- Old credential rejected:
- Pool reconnection observed:
- Rollback verified:
- Evidence:

## TLS certificate rotation
- Previous certificate serial / expiry:
- New certificate serial / expiry:
- SAN matches hostname:
- Trusted CA and verify-full:
- Wrong-hostname test rejected:
- Untrusted CA test rejected:
- Replica/proxy connection health:
- Evidence:

## Encryption and recovery
- Data/WAL volume encryption evidence:
- Backup encryption evidence:
- Independent key recovery:
- Isolated restore completed:
- WAL/transaction marker verified:
- Evidence:

## Security and signoff
- Exceptions / residual risks:
- SQL audit review:
- External KMS/OS verification:
- Owner signoff:
- Final status: NOT VERIFIED

Never attach passwords, private keys, tokens, or plaintext sensitive data.
