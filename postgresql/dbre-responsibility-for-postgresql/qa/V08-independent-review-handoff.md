# V08 — Independent Review Evidence Handoff

**STATE: TEMPLATE ONLY. Actual executed PostgreSQL staging tests: 0.**
No filled credentials, PHI, internal hostnames, sensitive SQL text or approval identities should be published to GitHub. Fill this only in the organization's restricted evidence system.

## Per-environment recovery acceptance

| Evidence | Actual result |
|---|---|
| Internal change approval, run ID, exact environment and Git commit | PENDING |
| Source and isolated target instance IDs / failure domains | PENDING |
| PostgreSQL version, provider, instance role, monitoring credential control | PENDING |
| Restorable backup ID and WAL/timeline / provider point | PENDING |
| Successful isolated restore with synthetic business marker | PENDING |
| Independent old-primary fencing and single-writer proof (HA only) | PENDING |
| Last recovered valid committed marker UTC | PENDING |
| Failure start UTC and APP/DATA full service acceptance UTC | PENDING |
| Measured RPO and approved RPO seconds | PENDING |
| Measured RTO and approved RTO seconds | PENDING |
| CDC correctness, endpoint/TLS/grants and client latency | PENDING |
| Billing, capacity and recovery-volume headroom | PENDING |
| Exception/corrective action and revalidation owner | PENDING |

## Independent roles (real approvers must sign)

| Approval role | Reviewer | Evidence authenticated | Decision |
|---|---|---|---|
| DBRE independent peer | PENDING | NO | PENDING |
| APP business owner | PENDING | NO | PENDING |
| DATA recovery/correctness owner | PENDING | NO | PENDING |
| PLT cloud/HA/fencing owner | PENDING | NO | PENDING |
| SEC privacy/least privilege | PENDING | NO | PENDING |
| FIN capacity and cost | PENDING | NO | PENDING |
| SM change authority | PENDING | NO | PENDING |

**No automatic certification:** The V07 evidence checker validates only metadata; its READY_FOR_INDEPENDENT_REVIEW state cannot prove the links, identity, permissions or witnessed database operation. Human board approval is required; absent staging evidence means NOT_CERTIFIED_FOR_PRODUCTION.
