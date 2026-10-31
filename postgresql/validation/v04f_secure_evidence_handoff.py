#!/usr/bin/env python3
"""V04-F private evidence handoff metadata cross-check (offline only).

No network, PostgreSQL connections, cloud access, credential handling, or
operational actions. Local SHA-256 and self-attested source-review receipts
cannot independently authenticate original evidence or certify HA/DR.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
from typing import Any

import v04_staging_readiness as a
import v04_independent_review as b
import v04e_artifact_integrity as e

SCHEMA="pg-ha-dr-v04f-1"
MAX_RECEIPT_AGE=timedelta(days=30)


def verdict(errors: list[str], checked: int, now: datetime) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "result": "NO_GO" if errors else "HANDOFF_METADATA_COMPLETE_UNAUTHENTICATED",
        "reason_codes": sorted(set(errors)),
        "handoff_records_checked": checked,
        "expected_records": len(e.ROLES),
        "checked_at_utc": now.isoformat(),
        "source_systems_authenticated_by_tool": False,
        "certification": "NOT_CERTIFIED",
        "authorization": "NONE",
        "execution": "NEVER",
        "note": ("Self-reported export/transfer/source-review attestations and "
                 "matching local hashes do NOT prove evidence authenticity, "
                 "fencing effectiveness, identity, or staging approval. "
                 "The independent human reviewers must verify original systems."),
    }


def screen(acceptance: Any, inventory: Any, handoff: Any, root: Path, *,
           now: datetime | None = None) -> dict[str, Any]:
    now=(now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    errors: list[str]=[]
    if any(not isinstance(x,dict) for x in (acceptance,inventory,handoff)):
        return verdict(["invalid_input_packet"],0,now)
    intake=e.screen(acceptance,inventory,root,now=now)
    if intake["result"]!="LOCAL_ARTIFACT_BYTES_MATCH_METADATA_UNAUTHENTICATED":
        errors.append("v04e_local_byte_integrity_no_go")
        # Do not include user names or original evidence content in the report.
        errors.extend("v04e_"+x for x in intake["reason_codes"])

    if a.contains_secret_keys(handoff):
        errors.append("sensitive_keys_not_allowed")
    if handoff.get("schema")!=SCHEMA or handoff.get("mode")!="offline_handoff_review_only":
        errors.append("handoff_schema_or_mode_invalid")
    if any(x.get("environment")!="staging" for x in (acceptance,inventory,handoff)):
        errors.append("non_staging_environment_refused")
    if handoff.get("requested_disposition")!="request_independent_source_review":
        errors.append("automatic_approval_refused")
    if handoff.get("operational_go") is not None or handoff.get("certified") is not None:
        errors.append("embedded_operational_go_refused")
    for field in ("environment_id","change_ticket","system_identifier"):
        if (not a.good_text(handoff.get(field)) or
            handoff.get(field)!=acceptance.get(field) or
            handoff.get(field)!=inventory.get(field)):
            errors.append(field+"_binding_mismatch")
    for field,doc in (("v04d_manifest_sha256",acceptance),
                      ("v04e_inventory_sha256",inventory)):
        try:
            original=b.digest(doc)
        except (ValueError,TypeError):
            original=None
        if not b.good_sha(handoff.get(field)) or handoff.get(field)!=original:
            errors.append(field+"_mismatch")

    if not a.good_ref(handoff.get("approved_private_transfer_policy_ref")):
        errors.append("approved_private_transfer_policy_missing")
    if not a.good_ref(handoff.get("retention_and_access_policy_ref")):
        errors.append("retention_and_access_policy_missing")
    entries=handoff.get("records")
    entries=entries if isinstance(entries,dict) else {}
    extra=set(entries)-set(e.ROLES)
    if extra:
        errors.append("unexpected_evidence_role")
    inventory_records=inventory.get("artifacts")
    inventory_records=inventory_records if isinstance(inventory_records,dict) else {}
    original=e.expected_rows(acceptance)
    receipt_ids=set()
    checked=0
    for role in e.ROLES:
        suffix=role.replace("/","_")
        row=entries.get(role)
        inv=inventory_records.get(role)
        if not isinstance(row,dict):
            errors.append("missing_handoff_"+suffix)
            continue
        if not isinstance(inv,dict):
            errors.append("missing_inventory_"+suffix)
            continue
        src=original[role]
        for key,expected in (
            ("redacted_review_sha256",inv.get("sha256")),
            ("redacted_review_evidence_ref",inv.get("evidence_ref")),
            ("source_system",inv.get("source_system")),
            ("original_record_id",inv.get("original_record_id")),
        ):
            if not a.good_text(row.get(key)) or row.get(key)!=expected:
                errors.append("handoff_"+key+"_mismatch_"+suffix)
        if row.get("redacted_review_sha256")!=src.get("evidence_sha256"):
            errors.append("handoff_acceptance_sha_mismatch_"+suffix)
        for name in ("original_artifact_sha256","reviewed_source_sha256"):
            if not b.good_sha(row.get(name)):
                errors.append("original_source_digest_missing_"+suffix)
        if (b.good_sha(row.get("original_artifact_sha256")) and
                row.get("original_artifact_sha256")!=row.get("reviewed_source_sha256")):
            errors.append("original_source_digest_mismatch_"+suffix)
        for key in ("original_source_record_ref","export_attestation_ref",
                    "private_transfer_receipt_ref","receiver_attestation_ref",
                    "independent_source_review_ref"):
            if not a.good_ref(row.get(key)):
                errors.append("source_or_handoff_reference_missing_"+suffix)
        receipt=row.get("receipt_id")
        if not a.good_text(receipt):
            errors.append("receipt_id_missing_"+suffix)
        elif receipt in receipt_ids:
            errors.append("duplicate_receipt_id")
        else:
            receipt_ids.add(receipt)

        collector=inv.get("collector")
        exporter=row.get("exported_by")
        receiver=row.get("received_by")
        verifier=row.get("source_verified_by")
        people=(collector,exporter,receiver,verifier)
        if not all(a.good_text(x) for x in people):
            errors.append("handoff_named_participants_missing_"+suffix)
        elif len({x.casefold() for x in people})!=4:
            errors.append("handoff_roles_not_independent_"+suffix)

        collected=a.parse_time(inv.get("collected_at_utc"))
        exported=a.parse_time(row.get("exported_at_utc"))
        received=a.parse_time(row.get("received_at_utc"))
        verified=a.parse_time(row.get("source_verified_at_utc"))
        if (any(t is None for t in (collected,exported,received,verified)) or
                not (collected <= exported <= received <= verified <= now) or
                now-verified>MAX_RECEIPT_AGE):
            errors.append("handoff_chronology_or_age_invalid_"+suffix)
        if row.get("independent_source_review_result")!="reported_verified":
            errors.append("source_review_not_recorded_"+suffix)
        if row.get("private_transfer_confirmed") is not True:
            errors.append("private_transfer_not_confirmed_"+suffix)
        if row.get("source_reviewed_against_original") is not True:
            errors.append("original_source_comparison_not_recorded_"+suffix)
        if row.get("redaction_approved") is not True:
            errors.append("redaction_approval_not_recorded_"+suffix)
        if not a.good_ref(row.get("redaction_approval_ref")):
            errors.append("redaction_approval_reference_missing_"+suffix)
        if (row.get("redacted_review_sha256")==inv.get("sha256") and
                row.get("original_record_id")==inv.get("original_record_id")):
            checked+=1

    return verdict(errors,checked,now)


def main() -> int:
    p=argparse.ArgumentParser(description="Offline source-handoff metadata audit")
    p.add_argument("--acceptance",required=True,type=Path)
    p.add_argument("--inventory",required=True,type=Path)
    p.add_argument("--handoff",required=True,type=Path)
    p.add_argument("--evidence-root",required=True,type=Path)
    p.add_argument("--json-out",type=Path)
    args=p.parse_args()
    now=datetime.now(timezone.utc)
    try:
        docs=[json.loads(getattr(args,k).read_text(encoding="utf-8"))
              for k in ("acceptance","inventory","handoff")]
        out=screen(*docs,args.evidence_root,now=now)
    except (OSError,UnicodeError,TypeError,ValueError):
        out=verdict(["invalid_or_unreadable_json"],0,now)
    encoded=json.dumps(out,indent=2)+"\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True,exist_ok=True)
        args.json_out.write_text(encoded,encoding="utf-8")
    print(encoded)
    return 0 if out["result"]=="HANDOFF_METADATA_COMPLETE_UNAUTHENTICATED" else 2


if __name__=="__main__":
    sys.exit(main())
