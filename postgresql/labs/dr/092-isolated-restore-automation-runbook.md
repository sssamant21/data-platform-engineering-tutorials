# Chapter 092 — Isolated Restore Automation Runbook

**Status:** NOT EXECUTED

## Inputs
- Incident/change ID:
- Recovery target (time/LSN/restore point):
- Approved RPO/RTO:
- Backup generation and WAL chain:
- Source and DR storage locations:
- PostgreSQL version and timeline:
- Recovery operator and independent verifier:

## STOP gates
- Destination is isolated and disposable:
- Backup manifest and WAL continuity verified:
- Independent storage credentials and encryption keys available:
- Restore target is reachable:
- No route to production writer endpoint:
- Sufficient compute/storage and approved data access:

## Restore sequence
1. Allocate isolated destination with explicit run ID.
2. Copy/decrypt verified base backup and WAL.
3. Validate backup manifest and permissions.
4. Configure restore_command and recovery target using supported tooling.
5. Start PostgreSQL and monitor recovery.
6. Record recovered timeline, transaction markers and UTC time.
7. Run database and application acceptance checks.
8. Save redacted evidence, alerts and measured RPO/RTO.
9. Clean up only disposable restore resources.

## Production cutover
**Separate authorization required.** Confirm old primary fencing and single-writer authority per Chapter 091 before any client write routing.

## Failure handling
- Missing WAL: fail closed; preserve evidence.
- Decryption failure: escalate IAM/KMS; do not bypass controls.
- Corrupt backup: select independent verified generation.
- Unmet RPO/RTO: incident commander decides recovery alternative.
