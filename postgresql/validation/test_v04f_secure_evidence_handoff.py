#!/usr/bin/env python3
"""V04-F offline synthetic chain-of-custody regression; NEVER real staging."""
from __future__ import annotations

from datetime import timedelta
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from test_v04_staging_readiness import NOW
from test_v04e_artifact_integrity import EvidenceIntegrityTests
import v04_independent_review as b
import v04e_artifact_integrity as e
import v04f_secure_evidence_handoff as f


def timestamp(delta_ms: int) -> str:
    return (NOW+timedelta(milliseconds=delta_ms)).isoformat()


class HandoffTests(unittest.TestCase):
    def setUp(self):
        fixture=EvidenceIntegrityTests(methodName="test_synthetic_exact_bytes_only_not_authenticated")
        fixture.setUp()
        self.addCleanup(fixture.temp.cleanup)
        self.root=fixture.root
        self.acceptance=fixture.acceptance
        self.inventory=fixture.inventory
        self.handoff={
            "schema":f.SCHEMA, "mode":"offline_handoff_review_only",
            "requested_disposition":"request_independent_source_review",
            "environment":"staging",
            "environment_id":self.inventory["environment_id"],
            "change_ticket":self.inventory["change_ticket"],
            "system_identifier":self.inventory["system_identifier"],
            "v04d_manifest_sha256":b.digest(self.acceptance),
            "v04e_inventory_sha256":b.digest(self.inventory),
            "approved_private_transfer_policy_ref":"evidence://synthetic/transfer-policy",
            "retention_and_access_policy_ref":"evidence://synthetic/retention-policy",
            "records":{},
        }
        for i,role in enumerate(e.ROLES):
            artifact=self.inventory["artifacts"][role]
            self.handoff["records"][role]={
                "receipt_id":"SYNTHETIC-RECEIPT-%02d" % i,
                "original_record_id":artifact["original_record_id"],
                "source_system":artifact["source_system"],
                "original_artifact_sha256":"0123456789abcdef"*4,
                "reviewed_source_sha256":"0123456789abcdef"*4,
                "original_source_record_ref":f"evidence://synthetic/original/{i}",
                "redacted_review_sha256":artifact["sha256"],
                "redacted_review_evidence_ref":artifact["evidence_ref"],
                "exported_by":"Synthetic-Exporter",
                "exported_at_utc":timestamp(-1500),
                "export_attestation_ref":f"evidence://synthetic/export/{i}",
                "received_by":"Synthetic-Receiver",
                "received_at_utc":timestamp(-1000),
                "receiver_attestation_ref":f"evidence://synthetic/receive/{i}",
                "private_transfer_receipt_ref":f"evidence://synthetic/transfer/{i}",
                "source_verified_by":"Synthetic-Independent-Reviewer",
                "source_verified_at_utc":timestamp(-500),
                "independent_source_review_ref":f"evidence://synthetic/review/{i}",
                "independent_source_review_result":"reported_verified",
                "source_reviewed_against_original":True,
                "redaction_approved":True,
                "redaction_approval_ref":f"evidence://synthetic/redaction/{i}",
                "private_transfer_confirmed":True,
            }

    def check(self):
        return f.screen(self.acceptance,self.inventory,self.handoff,self.root,now=NOW)

    def first(self):
        return e.ROLES[0]

    def refuse(self,code):
        out=self.check()
        self.assertEqual("NO_GO",out["result"],out)
        self.assertIn(code,out["reason_codes"],out)
        self.assertEqual("NOT_CERTIFIED",out["certification"])
        self.assertEqual("NONE",out["authorization"])
        self.assertEqual("NEVER",out["execution"])

    def test_all_synthetic_receipts_still_unverified(self):
        out=self.check()
        self.assertEqual("HANDOFF_METADATA_COMPLETE_UNAUTHENTICATED",out["result"],out)
        self.assertEqual(20,out["handoff_records_checked"])
        self.assertFalse(out["source_systems_authenticated_by_tool"])
        self.assertEqual("NOT_CERTIFIED",out["certification"])

    def test_missing_receipt_never_passes(self):
        role=self.first()
        del self.handoff["records"][role]
        self.refuse("missing_handoff_"+role.replace("/","_"))

    def test_extra_role_and_duplicate_receipt_denied(self):
        self.handoff["records"]["unapproved/extra"]={}
        self.refuse("unexpected_evidence_role")
        self.handoff["records"].pop("unapproved/extra")
        self.handoff["records"][e.ROLES[1]]["receipt_id"]=self.handoff["records"][e.ROLES[0]]["receipt_id"]
        self.refuse("duplicate_receipt_id")

    def test_distinct_export_receiver_collector_reviewer(self):
        role=self.first()
        entry=self.handoff["records"][role]
        entry["source_verified_by"]=entry["exported_by"]
        self.refuse("handoff_roles_not_independent_"+role.replace("/","_"))
        entry["source_verified_by"]="Synthetic-Independent-Reviewer"
        entry["exported_by"]=self.inventory["artifacts"][role]["collector"]
        self.refuse("handoff_roles_not_independent_"+role.replace("/","_"))

    def test_wrong_original_record_or_source_system_denied(self):
        role=self.first()
        entry=self.handoff["records"][role]
        entry["original_record_id"]="OTHER"
        self.refuse("handoff_original_record_id_mismatch_"+role.replace("/","_"))
        entry["original_record_id"]=self.inventory["artifacts"][role]["original_record_id"]
        entry["source_system"]="Unknown system"
        self.refuse("handoff_source_system_mismatch_"+role.replace("/","_"))

    def test_original_source_sha_mismatch_denied(self):
        role=self.first()
        self.handoff["records"][role]["reviewed_source_sha256"]="fedcba9876543210"*4
        self.refuse("original_source_digest_mismatch_"+role.replace("/","_"))

    def test_transfer_chronology_and_future_review_denied(self):
        role=self.first()
        entry=self.handoff["records"][role]
        entry["received_at_utc"]=timestamp(-1900)
        self.refuse("handoff_chronology_or_age_invalid_"+role.replace("/","_"))
        entry["received_at_utc"]=timestamp(-1000)
        entry["source_verified_at_utc"]=timestamp(1000)
        self.refuse("handoff_chronology_or_age_invalid_"+role.replace("/","_"))

    def test_missing_independent_source_review_denied(self):
        role=self.first()
        entry=self.handoff["records"][role]
        entry["source_reviewed_against_original"]=False
        self.refuse("original_source_comparison_not_recorded_"+role.replace("/","_"))
        entry["source_reviewed_against_original"]=True
        entry["independent_source_review_result"]="pending"
        self.refuse("source_review_not_recorded_"+role.replace("/","_"))
        entry["independent_source_review_result"]="reported_verified"
        entry["independent_source_review_ref"]="<REPLACE>"
        self.refuse("source_or_handoff_reference_missing_"+role.replace("/","_"))

    def test_missing_redaction_and_transfer_approvals_denied(self):
        role=self.first()
        entry=self.handoff["records"][role]
        entry["redaction_approved"]=False
        self.refuse("redaction_approval_not_recorded_"+role.replace("/","_"))
        entry["redaction_approved"]=True
        entry["private_transfer_confirmed"]=False
        self.refuse("private_transfer_not_confirmed_"+role.replace("/","_"))
        entry["private_transfer_confirmed"]=True
        self.handoff["approved_private_transfer_policy_ref"]=""
        self.refuse("approved_private_transfer_policy_missing")

    def test_changed_original_review_copy_or_inventory_denied(self):
        role=self.first()
        entry=self.handoff["records"][role]
        entry["redacted_review_sha256"]="abcdef0123456789"*4
        self.refuse("handoff_redacted_review_sha256_mismatch_"+role.replace("/","_"))
        entry["redacted_review_sha256"]=self.inventory["artifacts"][role]["sha256"]
        self.inventory["artifacts"][role]["original_record_id"]="tampered"
        self.refuse("v04e_inventory_sha256_mismatch")

    def test_modified_local_bytes_fail_v04e_first(self):
        role=self.first()
        p=self.root/self.inventory["artifacts"][role]["relative_path"]
        p.write_bytes(b"corrupted local evidence")
        self.refuse("v04e_local_byte_integrity_no_go")

    def test_wrong_ticket_and_prod_refused(self):
        self.handoff["change_ticket"]="WRONG"
        self.refuse("change_ticket_binding_mismatch")
        self.handoff["change_ticket"]=self.inventory["change_ticket"]
        self.handoff["environment"]="production"
        self.refuse("non_staging_environment_refused")

    def test_embedded_automated_go_and_secrets_denied(self):
        self.handoff["operational_go"]=True
        self.refuse("embedded_operational_go_refused")
        self.handoff.pop("operational_go")
        self.handoff["api_key"]="never stored"
        self.refuse("sensitive_keys_not_allowed")

    def test_public_templates_and_invalid_json_exit_no_go(self):
        argv=[
            "--acceptance",str(HERE/"v04d_ch050_acceptance.template.json"),
            "--inventory",str(HERE/"v04e_evidence_inventory.template.json"),
            "--handoff",str(HERE/"v04f_handoff.template.json"),
            "--evidence-root",str(self.root),
        ]
        cli=[sys.executable,str(HERE/"v04f_secure_evidence_handoff.py")]
        done=subprocess.run(cli+argv,capture_output=True,text=True,check=False)
        self.assertEqual(2,done.returncode,done.stderr)
        packet=json.loads(done.stdout)
        self.assertEqual("NO_GO",packet["result"])
        self.assertEqual("NOT_CERTIFIED",packet["certification"])
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"bad.json"
            p.write_text("{bad",encoding="utf-8")
            bad=subprocess.run(cli+["--acceptance",str(p),"--inventory",str(p),
                                "--handoff",str(p),"--evidence-root",str(td)],
                               capture_output=True,text=True,check=False)
            self.assertEqual(2,bad.returncode)
            self.assertIn('"result": "NO_GO"',bad.stdout)


if __name__=="__main__":
    unittest.main()
