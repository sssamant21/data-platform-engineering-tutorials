#!/usr/bin/env python3
"""Synthetic V04-E local bytes and path protection; never production evidence."""
from __future__ import annotations

from datetime import timedelta
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from test_v04_staging_readiness import NOW
from test_v04d_ch050_acceptance import complete_synthetic
import v04_independent_review as metadata
import v04e_artifact_integrity as e


class EvidenceIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="pg-v04e-synthetic-")
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.stage,self.review,self.preflight,self.acceptance=complete_synthetic()
        self.inventory={
            "schema":e.SCHEMA, "mode":"local_byte_integrity_only",
            "environment":"staging",
            "environment_id":self.acceptance["environment_id"],
            "change_ticket":self.acceptance["change_ticket"],
            "system_identifier":self.acceptance["system_identifier"],
            "artifacts":{},
        }
        rows=e.expected_rows(self.acceptance)
        for i,(role,rec) in enumerate(rows.items()):
            payload=("SYNTHETIC EVIDENCE / NOT REAL STAGING\n"+role+"\n").encode("utf-8")
            relative="redacted/item-%02d.txt" % i
            path=self.root / relative
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(payload)
            sha=hashlib.sha256(payload).hexdigest()
            rec["evidence_sha256"]=sha
            self.inventory["artifacts"][role]={
                "relative_path":relative,
                "sha256":sha,
                "size_bytes":len(payload),
                "evidence_ref":rec["evidence_ref"],
                "collector":"Synthetic-Collector",
                "source_system":"Synthetic-Lab-Fixture",
                "original_record_id":"fixture-%02d" % i,
                "collected_at_utc":(NOW-timedelta(seconds=2)).isoformat(),
                "redacted_for_review":True,
            }
        self.inventory["v04d_manifest_sha256"]=metadata.digest(self.acceptance)

    def check(self):
        return e.screen(self.acceptance,self.inventory,self.root,now=NOW)

    def must_refuse(self,code):
        v=self.check()
        self.assertEqual(v["result"],"NO_GO",v)
        self.assertIn(code,v["reason_codes"],v)
        self.assertEqual(v["certification"],"NOT_CERTIFIED")
        self.assertEqual(v["authorization"],"NONE")
        self.assertEqual(v["execution"],"NEVER")

    def first(self):
        return e.ROLES[0]

    def test_synthetic_exact_bytes_only_not_authenticated(self):
        result=self.check()
        self.assertEqual(result["result"],"LOCAL_ARTIFACT_BYTES_MATCH_METADATA_UNAUTHENTICATED",result)
        self.assertEqual(result["reason_codes"],[])
        self.assertEqual(result["checked_required_artifact_count"],len(e.ROLES))
        self.assertEqual(result["certification"],"NOT_CERTIFIED")
        self.assertFalse(result["source_systems_authenticated"])

    def test_missing_and_unexpected_roles(self):
        role=self.first()
        self.inventory["artifacts"].pop(role)
        self.must_refuse("missing_artifact_"+role.replace("/","_"))
        self.setUp_fake_not_needed = True
        self.inventory["artifacts"]["arbitrary/unapproved"]={}
        self.must_refuse("unexpected_artifact_role")

    def test_tamper_is_detected_by_sha256(self):
        role=self.first()
        file=self.root/self.inventory["artifacts"][role]["relative_path"]
        file.write_bytes(b"changed content with same original byte length??")
        self.must_refuse("file_size_type_or_hardlink_invalid_"+role.replace("/","_"))
        old=self.inventory["artifacts"][role]["size_bytes"]
        file.write_bytes(b"x"*old)
        self.must_refuse("byte_hash_mismatch_"+role.replace("/","_"))

    def test_path_traversal_and_absolute_refused(self):
        role=self.first()
        self.inventory["artifacts"][role]["relative_path"]="../outside.txt"
        self.must_refuse("unsafe_relative_path_"+role.replace("/","_"))
        self.inventory["artifacts"][role]["relative_path"]="/tmp/outside"
        self.must_refuse("unsafe_relative_path_"+role.replace("/","_"))
        self.inventory["artifacts"][role]["relative_path"]="redacted/../outside.txt"
        self.must_refuse("unsafe_relative_path_"+role.replace("/","_"))

    def test_symlinked_evidence_file_denied(self):
        role=self.first()
        file=self.root/self.inventory["artifacts"][role]["relative_path"]
        original=self.root/"original.txt"
        file.rename(original)
        try:
            file.symlink_to(original)
        except (NotImplementedError,OSError):
            self.skipTest("symlinks unavailable")
        self.must_refuse("file_symlink_disallowed_"+role.replace("/","_"))

    def test_hardlink_and_duplicate_path_denied(self):
        role=e.ROLES[0]
        file=self.root/self.inventory["artifacts"][role]["relative_path"]
        try:
            os.link(file,self.root/"hardlink.txt")
        except OSError:
            self.skipTest("hardlinks unavailable")
        self.must_refuse("file_size_type_or_hardlink_invalid_"+role.replace("/","_"))

    def test_missing_provenance_and_redaction(self):
        role=self.first()
        self.inventory["artifacts"][role]["source_system"]="<REPLACE>"
        self.must_refuse("provenance_missing_"+role.replace("/","_"))
        self.inventory["artifacts"][role]["source_system"]="Synthetic-Lab-Fixture"
        self.inventory["artifacts"][role]["redacted_for_review"]=False
        self.must_refuse("review_copy_not_marked_redacted_"+role.replace("/","_"))

    def test_changed_acceptance_record_refused(self):
        role=self.first()
        self.acceptance["acceptance_gates"][role.split("/",1)[1]]["status"]="PENDING"
        self.must_refuse("v04d_digest_mismatch")
        self.inventory["v04d_manifest_sha256"]=metadata.digest(self.acceptance)
        self.must_refuse("underlying_gate_not_passed_"+role.replace("/","_"))

    def test_invalid_checksum_reference_and_size(self):
        role=self.first()
        self.inventory["artifacts"][role]["sha256"]="0"*64
        self.must_refuse("declared_sha_mismatch_"+role.replace("/","_"))
        self.inventory["artifacts"][role]["sha256"] = e.expected_rows(self.acceptance)[role]["evidence_sha256"]
        self.inventory["artifacts"][role]["size_bytes"]=e.MAX_FILE_BYTES+1
        self.must_refuse("file_invalid_size_"+role.replace("/","_"))

    def test_prod_or_automated_certification_denied(self):
        self.inventory["environment"]="production"
        self.must_refuse("non_staging_refused")
        self.inventory["environment"]="staging"
        self.inventory["certified"]=True
        self.must_refuse("embedded_certification_or_go_refused")

    def test_unreadable_unsafe_and_malformed_packets_no_go(self):
        self.assertEqual(e.screen(None,{},self.root,now=NOW)["result"],"NO_GO")
        self.acceptance["rehearsal"]=None
        self.inventory["v04d_manifest_sha256"]=metadata.digest(self.acceptance)
        self.must_refuse("staging_rehearsal_not_recorded_pass")

    def test_public_templates_exit_nonzero_and_never_certified(self):
        cmd=[sys.executable,str(HERE/"v04e_artifact_integrity.py"),
            "--acceptance",str(HERE/"v04d_ch050_acceptance.template.json"),
            "--inventory",str(HERE/"v04e_evidence_inventory.template.json"),
            "--evidence-root",str(self.root)]
        got=subprocess.run(cmd,capture_output=True,text=True,check=False)
        self.assertEqual(got.returncode,2,got.stderr)
        report=json.loads(got.stdout)
        self.assertEqual(report["result"],"NO_GO")
        self.assertEqual(report["certification"],"NOT_CERTIFIED")
        self.assertEqual(report["authorization"],"NONE")


if __name__=="__main__":
    unittest.main()
