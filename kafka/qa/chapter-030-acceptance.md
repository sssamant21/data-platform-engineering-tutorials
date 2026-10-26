# Chapter 030 security reliability capstone automation

Run `python kafka/qa/run_chapter_030.py` independently against the persistent
Kafka 4.0.0/KRaft/Strimzi 0.47.0 secure fixture. It reuses one disposable kind
cluster for the integrated stages; no production listener, CA, ACL, policy or
production credential is modified for failure injection.

## Supported live checks

- Execute fresh Chapter 027, 028 and 029 runtimes serially in this Actions run:
  actual TLS/mTLS chain/SAN/validity and rejection checks; SCRAM authentication,
  password replacement, stale rejection and broker principal evidence; symmetric
  topic/group/transaction authorization, effective ACL drift and Secret/CR RBAC.
  Child evidence must match chapter, tested head, run ID, start time and all
  supported PASS checks. Historical reports or certification claims are rejected.
- Validate secure bootstrap Service/EndpointSlices against actual ready broker
  Pod UIDs, selectors, IPs and the SASL_SSL target port, reusing Chapter 026's
  port-parameterized pure validator. Match advertised broker DNS/IPs to each
  distinct ready broker rather than treating bootstrap alone as sufficient.
- Run a separate restricted non-root SASL_SSL Job, verifying DNS, TCP and secure
  metadata through every advertised broker with hostname verification enabled.
  Probe reserved .invalid DNS and a verified-unpublished Service port only from
  the disposable client. Require distinct DNS, TCP and Kafka discovery failures.
- Recover with six exact acks=all records and committed offsets on the authorized
  topic, full ISR and secure KRaft leader/three-voter/high-watermark evidence.
  The predeclared client failure-to-completion budget is 120 seconds; observed
  timing is a synthetic harness sample, not a production percentile SLO.

The workflow uploads the aggregate JSON, fresh child reports, client observations,
Kubernetes diagnostics and process logs after credential sanitization. Child
failures retain their own sanitized diagnostic reports. Timeouts constrain each
child process, API call, DNS lookup, socket, Kafka call, Job and whole workflow.
The complete disposable cluster is torn down even if a child process fails.
Existing standalone chapters remain independently executable and regress when
shared client changes affect them. Orchestration retains max-parallel=2.

## Full assessment remains pending

Supported runtime PASS does not award the manuscript's mandatory-gate assessment,
85-point score or enterprise certification. JSON explicitly records
capstone_assessment.status=NOT_YET_ACCEPTED and certification=NOT_CERTIFIED.

Default kind provides no CNI-enforced NetworkPolicy proof, cross-namespace
admission, external routing, cloud identity or multi-zone/storage failure domain.
Independent Jobs do not demonstrate continuous tenant availability or seamless
credential overlap. Production monitoring/alert routing, signed rollback and
break-glass governance, CA rotation planning and independent assessor signoff
remain pending. No live CA/key rotation, expired-client test or leaf renewal is
claimed. OAuth is conditional NOT_EXECUTED without a real reviewed supported
IdP/plugin; no token, issuer/audience/JWKS or refresh success is inferred from SCRAM.
Manuscript publication, implementation, supported runtime execution, full capstone
acceptance and enterprise certification remain separate evidence states.
