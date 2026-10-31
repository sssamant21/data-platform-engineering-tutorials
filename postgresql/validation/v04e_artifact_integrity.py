#!/usr/bin/env python3
"""V04-E local artifact byte-integrity and provenance-metadata audit.

Read-only. Never opens a database, connects to a network, authenticates source
systems, approves failover, or issues a Chapter 050 certification. Accept only
copies already transferred into an approved, private evidence directory.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys
from typing import Any

import v04_staging_readiness as a
import v04_independent_review as b
import v04d_ch050_acceptance as d

SCHEMA = "pg-ha-dr-v04e-1"
MAX_FILE_BYTES = 16 * 1024 * 1024
ROLES = tuple(
    [f"acceptance/{k}" for k in d.SCORECARD] +
    [f"scenario/{k}" for k in d.SCENARIOS] +
    [f"measurement/{k}" for k in d.METRICS]
)


def report(errors: list[str], count: int, now: datetime) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "result": ("NO_GO" if errors else
                   "LOCAL_ARTIFACT_BYTES_MATCH_METADATA_UNAUTHENTICATED"),
        "reason_codes": sorted(set(errors)),
        "checked_required_artifact_count": count,
        "required_artifact_count": len(ROLES),
        "checked_at_utc": now.isoformat(),
        "certification": "NOT_CERTIFIED",
        "authorization": "NONE",
        "execution": "NEVER",
        "source_systems_authenticated": False,
        "note": ("Local byte hashes and self-reported provenance metadata "
                 "do not authenticate original logs, independent fencing, "
                 "human approvals or business recovery. External review "
                 "and staging authorization are mandatory."),
    }


def expected_rows(acceptance: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for prefix, field, names in (
        ("acceptance", "acceptance_gates", d.SCORECARD),
        ("scenario", "negative_path_scenarios", d.SCENARIOS),
        ("measurement", "measured_objectives", d.METRICS),
    ):
        section=acceptance.get(field)
        section=section if isinstance(section, dict) else {}
        for name in names:
            row=section.get(name)
            rows[prefix + "/" + name] = row if isinstance(row, dict) else {}
    return rows


def safe_relative(name: Any) -> PurePosixPath | None:
    if not isinstance(name, str) or not name or "\\" in name:
        return None
    path=PurePosixPath(name)
    if (path.is_absolute() or path.as_posix() != name or
            any(part in (".", "..") for part in name.split("/")) or
            ":" in name or name.startswith("~")):
        return None
    return path


def hash_local(root: Path, relative: PurePosixPath,
               declared_bytes: Any) -> tuple[str | None, str | None]:
    if not isinstance(declared_bytes, int) or isinstance(declared_bytes, bool):
        return None, "invalid_size"
    if not 0 < declared_bytes <= MAX_FILE_BYTES:
        return None, "invalid_size"
    try:
        target=root
        for part in relative.parts:
            target=target/part
            if target.is_symlink():
                return None,"symlink_disallowed"
        if not target.is_file():
            return None, "not_regular_file"
        before=target.stat()
        if (not stat.S_ISREG(before.st_mode) or
                before.st_nlink != 1 or before.st_size != declared_bytes):
            return None, "size_type_or_hardlink_invalid"
        if target.resolve(strict=True).is_relative_to(root.resolve(strict=True)) is False:
            return None, "outside_evidence_directory"
        h=hashlib.sha256()
        with target.open("rb") as handle:
            fd_stat=os.fstat(handle.fileno())
            if (fd_stat.st_ino != before.st_ino or
                    fd_stat.st_dev != before.st_dev):
                return None,"file_replaced_during_read"
            total=0
            for block in iter(lambda: handle.read(256*1024),b""):
                total+=len(block)
                if total>MAX_FILE_BYTES:
                    return None,"size_limit_exceeded"
                h.update(block)
        after=target.stat()
        if (total != declared_bytes or after.st_size != declared_bytes or
                before.st_mtime_ns != after.st_mtime_ns or
                before.st_ino != after.st_ino):
            return None,"file_changed_during_read"
        return h.hexdigest(),None
    except (OSError, ValueError):
        return None,"file_unreadable"


def screen(acceptance: Any, inventory: Any, root: Path, *,
           now: datetime | None = None) -> dict[str, Any]:
    now=(now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    errors: list[str]=[]
    if not isinstance(acceptance,dict) or not isinstance(inventory,dict):
        return report(["invalid_packet"],0,now)
    if a.contains_secret_keys(inventory):
        errors.append("secret_key_in_inventory")
    if acceptance.get("schema")!=d.SCHEMA or (
            acceptance.get("mode")!="offline_certification_review_only"):
        errors.append("invalid_v04d_packet")
    if inventory.get("schema")!=SCHEMA or (
            inventory.get("mode")!="local_byte_integrity_only"):
        errors.append("invalid_v04e_mode_or_schema")
    if inventory.get("environment")!="staging" or acceptance.get("environment")!="staging":
        errors.append("non_staging_refused")
    for k in ("environment_id","change_ticket","system_identifier"):
        if (not a.good_text(inventory.get(k)) or
                inventory.get(k)!=acceptance.get(k)):
            errors.append(k+"_binding_mismatch")
    if (inventory.get("certified") is not None or
            inventory.get("operational_go") is not None):
        errors.append("embedded_certification_or_go_refused")
    try:
        digest=b.digest(acceptance)
    except (ValueError,TypeError):
        digest=None
    if (not b.good_sha(inventory.get("v04d_manifest_sha256")) or
            inventory.get("v04d_manifest_sha256")!=digest):
        errors.append("v04d_digest_mismatch")
    rehearsal=acceptance.get("rehearsal")
    rehearsal=rehearsal if isinstance(rehearsal,dict) else {}
    if rehearsal.get("executed") is not True or (
            rehearsal.get("outcome")!="PASS"):
        errors.append("staging_rehearsal_not_recorded_pass")

    items=inventory.get("artifacts")
    items=items if isinstance(items,dict) else {}
    for key in items:
        if key not in ROLES:
            errors.append("unexpected_artifact_role")
    paths: set[str]=set()
    expected=expected_rows(acceptance)
    matched=0

    if root.is_symlink() or not root.is_dir():
        errors.append("evidence_root_missing_or_symlink")

    for role in ROLES:
        record=items.get(role)
        if not isinstance(record,dict):
            errors.append("missing_artifact_"+role.replace("/","_"))
            continue
        original=expected[role]
        if role.startswith(("acceptance/","scenario/")) and original.get("status")!="PASS":
            errors.append("underlying_gate_not_passed_"+role.replace("/","_"))
        ref=original.get("evidence_ref")
        sha=original.get("evidence_sha256")
        if not a.good_ref(ref) or not b.good_sha(sha):
            errors.append("underlying_reference_missing_"+role.replace("/","_"))
        if record.get("evidence_ref")!=ref:
            errors.append("reference_mismatch_"+role.replace("/","_"))
        if not b.good_sha(record.get("sha256")) or record.get("sha256")!=sha:
            errors.append("declared_sha_mismatch_"+role.replace("/","_"))
        for meta in ("collector","source_system","original_record_id"):
            if not a.good_text(record.get(meta)):
                errors.append("provenance_missing_"+role.replace("/","_"))
        if record.get("redacted_for_review") is not True:
            errors.append("review_copy_not_marked_redacted_"+role.replace("/","_"))
        observed=a.parse_time(record.get("collected_at_utc"))
        if observed is None or observed>now:
            errors.append("collection_timestamp_invalid_"+role.replace("/","_"))
        rel=safe_relative(record.get("relative_path"))
        if rel is None:
            errors.append("unsafe_relative_path_"+role.replace("/","_"))
            continue
        if rel.as_posix() in paths:
            errors.append("duplicate_evidence_path")
            continue
        paths.add(rel.as_posix())
        if "evidence_root_missing_or_symlink" in errors:
            continue
        actual,err=hash_local(root,rel,record.get("size_bytes"))
        if err:
            errors.append("file_"+err+"_"+role.replace("/","_"))
            continue
        if actual!=record.get("sha256"):
            errors.append("byte_hash_mismatch_"+role.replace("/","_"))
            continue
        # Bytes match both the inventory's claim and the V04-D metadata claim.
        if (actual==sha and record.get("evidence_ref")==ref and
                observed is not None and observed<=now and
                record.get("redacted_for_review") is True):
            matched+=1
    return report(errors,matched,now)


def main() -> int:
    p=argparse.ArgumentParser(description="V04-E offline local evidence integrity screen")
    p.add_argument("--acceptance",type=Path,required=True)
    p.add_argument("--inventory",type=Path,required=True)
    p.add_argument("--evidence-root",type=Path,required=True)
    p.add_argument("--json-out",type=Path)
    args=p.parse_args()
    now=datetime.now(timezone.utc)
    try:
        acceptance=json.loads(args.acceptance.read_text(encoding="utf-8"))
        inventory=json.loads(args.inventory.read_text(encoding="utf-8"))
        out=screen(acceptance,inventory,args.evidence_root,now=now)
    except (OSError,UnicodeError,ValueError,TypeError):
        out=report(["unreadable_or_invalid_json"],0,now)
    encoded=json.dumps(out,indent=2)+"\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True,exist_ok=True)
        args.json_out.write_text(encoded,encoding="utf-8")
    print(encoded)
    return 0 if out["result"]=="LOCAL_ARTIFACT_BYTES_MATCH_METADATA_UNAUTHENTICATED" else 2


if __name__=="__main__":
    sys.exit(main())
