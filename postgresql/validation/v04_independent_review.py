#!/usr/bin/env python3
"""V04-B offline independent-review packet gate (non-operational).

Checks formal completeness, separation of duties, freshness and binding to
the exact V04-A staging metadata. DOES NOT authenticate evidence/identity,
connect to a database, contact change-management systems, or authorize any
failover. Green synthetic CI = code tested, NOT staging approved.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

import v04_staging_readiness as v04a

SCHEMA = "pg-ha-dr-v04b-1"
REVIEW_ROLES = ("dbre", "security_fencing", "application", "change_management")
CLAIMS = {
    "cluster_and_scope": "dbre",
    "independent_fence_write_restart_and_bypass": "security_fencing",
    "backup_archive_restore": "dbre",
    "approved_business_rpo_rto": "change_management",
    "application_routing_and_smoke": "application",
    "rollback_and_abort_conditions": "change_management",
}
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def digest(document: Any) -> str:
    """Metadata binding only, NOT an evidence authenticity signature."""
    encoded = json.dumps(document, ensure_ascii=True, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def good_sha(value: Any) -> bool:
    return (isinstance(value, str) and SHA256.fullmatch(value) is not None
            and len(set(value)) > 1)


def failure(codes: list[str], now: datetime) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "result": "NO_GO" if codes else "REVIEW_PACKET_COMPLETE_UNAUTHENTICATED",
        "reason_codes": sorted(set(codes)),
        "screened_at_utc": now.isoformat(),
        "authorization": "NONE",
        "execution": "NEVER",
        "reviewed_real_staging": False,
        "note": ("A complete self-reported review packet is NOT independent "
                 "verification or an operational GO. Confirm real identities, "
                 "authentic evidence and change approval outside this tool."),
    }


def screen(staging: Any, review: Any, *,
           now: datetime | None = None) -> dict[str, Any]:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    errors: list[str] = []
    if not isinstance(staging, dict):
        return failure(["staging_manifest_invalid"], now)
    if not isinstance(review, dict):
        return failure(["review_packet_invalid"], now)

    # A V04-B reviewer cannot override missing/stale V04-A evidence.
    stage = v04a.screen(staging, now=now)
    if stage["result"] != "EVIDENCE_COMPLETE_FOR_INDEPENDENT_REVIEW":
        errors.append("v04a_staging_no_go")
        # Only reason codes, never raw staging details/identities in output.
        errors.extend("v04a_" + code for code in stage["reason_codes"])

    if v04a.contains_secret_keys(review):
        errors.append("secret_keys_in_review_packet")
    if review.get("schema") != SCHEMA:
        errors.append("review_schema_invalid")
    if review.get("mode") != "independent_evidence_review_only":
        errors.append("review_mode_invalid")
    if review.get("decision") != "submit_to_change_authority":
        errors.append("attempted_operational_decision")
    if review.get("environment") != "staging":
        errors.append("review_non_staging_environment")

    for field in ("environment_id", "change_ticket"):
        if (not v04a.good_text(review.get(field)) or
                review.get(field) != staging.get(field)):
            errors.append(f"review_{field}_mismatch")

    cluster = staging.get("cluster")
    cluster = cluster if isinstance(cluster, dict) else {}
    if (not v04a.good_text(review.get("system_identifier")) or
            review.get("system_identifier") != cluster.get("system_identifier")):
        errors.append("review_system_identifier_mismatch")
    for field in ("window_start_utc", "window_end_utc"):
        if (not v04a.good_text(review.get(field)) or
                review.get(field) != staging.get(field)):
            errors.append(f"review_{field}_mismatch")
    try:
        canonical_digest = digest(staging)
    except (ValueError, TypeError):
        canonical_digest = None
        errors.append("staging_manifest_unhashable")
    if (not good_sha(review.get("staging_manifest_sha256")) or
            review.get("staging_manifest_sha256") != canonical_digest):
        errors.append("staging_manifest_digest_mismatch")

    preparer = review.get("prepared_by")
    if not v04a.good_text(preparer):
        errors.append("preparer_missing")
    created = v04a.parse_time(review.get("prepared_at_utc"))
    if (created is None or created > now or
            now - created > timedelta(days=7)):
        errors.append("review_packet_timestamp_missing_or_stale")
    approval_names: set[str] = set()
    initial = staging.get("approvals")
    initial = initial if isinstance(initial, dict) else {}
    for value in initial.values():
        if isinstance(value, dict) and v04a.good_text(value.get("name")):
            approval_names.add(value["name"].casefold())

    reviewers = review.get("reviewers")
    reviewers = reviewers if isinstance(reviewers, dict) else {}
    unique: set[str] = set()
    for role in REVIEW_ROLES:
        entry = reviewers.get(role)
        entry = entry if isinstance(entry, dict) else {}
        person = entry.get("name")
        seen = v04a.parse_time(entry.get("reviewed_at_utc"))
        if not v04a.good_text(person):
            errors.append(f"reviewer_{role}_missing")
        elif (person.casefold() in unique or
              (v04a.good_text(preparer) and
               person.casefold() == preparer.casefold()) or
              person.casefold() in approval_names):
            errors.append("reviewer_not_independent")
        else:
            unique.add(person.casefold())
        if (entry.get("disposition") != "verified" or
                not v04a.good_ref(entry.get("attestation_ref"))):
            errors.append(f"reviewer_{role}_attestation_missing")
        if (seen is None or seen > now or
                now - seen > timedelta(days=7) or
                (created is not None and seen < created)):
            errors.append(f"reviewer_{role}_timestamp_invalid")

    claims = review.get("claims")
    claims = claims if isinstance(claims, dict) else {}
    for key, role in CLAIMS.items():
        claim = claims.get(key)
        claim = claim if isinstance(claim, dict) else {}
        if claim.get("status") != "verified" or claim.get("reviewer_role") != role:
            errors.append(f"claim_{key}_not_independently_verified")
        if (not v04a.good_ref(claim.get("evidence_ref")) or
                not good_sha(claim.get("evidence_sha256"))):
            errors.append(f"claim_{key}_evidence_missing")
        assessed = v04a.parse_time(claim.get("observed_at_utc"))
        if assessed is None or assessed > now or now - assessed > timedelta(days=7):
            errors.append(f"claim_{key}_timestamp_invalid")
        if key == "independent_fence_write_restart_and_bypass":
            # A record must claim an independent observation, not merely say
            # "Postgres was stopped"; this remains self-attested and untrusted.
            if claim.get("observed_from_independent_control_plane") is not True:
                errors.append("independent_control_plane_observation_missing")
            observed_fence = v04a.parse_time(
                (staging.get("fencing") or {}).get("verified_at_utc")
            ) if isinstance(staging.get("fencing"), dict) else None
            if (assessed is not None and observed_fence is not None and
                    assessed < observed_fence):
                errors.append("fence_review_predates_fence_evidence")

    return failure(errors, now)


def main() -> int:
    p = argparse.ArgumentParser(description="V04-B offline review packet screening")
    p.add_argument("--staging", type=Path, required=True)
    p.add_argument("--review", type=Path, required=True)
    p.add_argument("--json-out", type=Path)
    args = p.parse_args()
    now = datetime.now(timezone.utc)
    try:
        staging = json.loads(args.staging.read_text(encoding="utf-8"))
        review = json.loads(args.review.read_text(encoding="utf-8"))
        result = screen(staging, review, now=now)
    except (OSError, UnicodeError, ValueError, TypeError) as e:
        result = failure(["invalid_or_unreadable_json"], now)
    output = json.dumps(result, indent=2) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(output, encoding="utf-8")
    print(output)
    return 0 if result["result"] == "REVIEW_PACKET_COMPLETE_UNAUTHENTICATED" else 2


if __name__ == "__main__":
    sys.exit(main())
