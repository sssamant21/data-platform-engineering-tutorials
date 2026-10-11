# Module 03 — Security Acceptance Evidence

**Audience:** DBRE/SRE. **Default status:** Pending; this is an unexecuted template.

Instance/environment:
PostgreSQL build and deployment owner:
Application/driver/pooler versions:
Change reference and evidence window:
Reviewer and review date:
Selected pgAudit version/track, if required:
Evidence location and access policy:

| Gate | Scope and evidence | Status | Reviewer / gap / next action |
|---|---|---|---|
| Ownership/runtime separation | Chapter 011 actual owner/membership and denied-operation probes | Pending | |
| Authentication | Chapter 012 intended/forbidden tuples and real credential tests | Pending | |
| TLS | Chapter 013 name/chain checks, plaintext denial and served-leaf rotation | Pending | |
| Credential lifecycle | Chapter 014 adopted version, fresh login, old admission/session retirement | Pending | |
| Listener exposure | Chapter 015 OS listener and interface inventory | Pending | |
| Intended production source | Actual allowed-source path and authenticated operation | Pending | |
| Forbidden production source | Controlled network denial with identity/path recorded | Pending | |
| Audit event coverage | Required actors/classes/objects, success/denial and expected gaps | Pending | |
| Delivery/retrieval | Central event correlation, ingestion lag and protected retrieval | Pending | |
| Retention/access | Approved retention, log access and secret-exposure review | Pending | |
| Failure behavior | Destination outage, rotation/restart and volume/latency tests | Pending | |
| Cleanup/rollback | Original lab baseline restored; exceptions owned/time-bounded | Pending | |

Event ledger:

| Token/time | Login / execution role | Endpoint/source | Expected event | Observed local record | Observed central record | Result |
|---|---|---|---|---|---|---|

Keep secret values, password verifiers, private keys and sensitive query payloads out of this report.

Decision: Pending
Open mandatory gates:
Accepted exceptions with owner/expiry:
Required follow-up tests:
Reviewer rationale:

A local log, a successful readiness check or a stored certificate is insufficient to mark its corresponding end-to-end gate Pass. Not applicable requires a deployment-specific reason; it must not hide a required unexecuted test.
