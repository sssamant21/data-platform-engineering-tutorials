#!/usr/bin/env python3
"""V04-D synthetic only: never certifies an actual database or staging change."""
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
from test_v04c_rehearsal_preflight import fixture as c_fixture
import v04_independent_review as b
import v04d_ch050_acceptance as d


def ts(seconds: int) -> str:
    return (NOW+timedelta(seconds=seconds)).isoformat()


def complete_synthetic():
    stage, review, preflight=c_fixture()
    record={
        "schema": d.SCHEMA, "mode":"offline_certification_review_only",
        "requested_disposition":"submit_for_external_certification_review",
        "environment":"staging",
        "environment_id":stage["environment_id"],
        "change_ticket":stage["change_ticket"],
        "system_identifier":stage["cluster"]["system_identifier"],
        "window_start_utc":stage["window_start_utc"],
        "window_end_utc":stage["window_end_utc"],
        "v04a_sha256":b.digest(stage),
        "v04b_sha256":b.digest(review),
        "v04c_sha256":b.digest(preflight),
        "v04c_preflight_screen_ref":"evidence://synthetic/preflight-record",
        "manual_change_authority_go_ref":"evidence://synthetic/manual-decision",
        "manual_change_authority_go_at_utc":ts(-45),
        "independent_fencing_recheck_ref":"evidence://synthetic/recheck",
        "rehearsal":{
            "executed":True,"outcome":"PASS", "operator":"Synthetic-Operator",
            "started_at_utc":ts(-30), "ended_at_utc":ts(-10),
            "fence_survived_restart_attempt":True,"one_writer_observed":True,
            "client_transactions_restored":True,
            "former_primary_rejoined_readonly":True,
            "no_unapproved_promotion":True,"abort_controls_observed":True,
            "client_probe_evidence_ref":"evidence://synthetic/client",
            "old_primary_fence_evidence_ref":"evidence://synthetic/fence",
            "rejoin_evidence_ref":"evidence://synthetic/rejoin",
            "timeline_evidence_ref":"evidence://synthetic/timeline",
        },
        "measured_objectives":{},
        "acceptance_gates":{},
        "negative_path_scenarios":{},
        "independent_final_signoffs":{},
    }
    spans={
        "ha_rpo_seconds":(-25,-25),
        "ha_rto_seconds":(-29,-21),
        "pitr_rpo_seconds":(-19,-19),
        "pitr_rto_seconds":(-24,-14),
    }
    for name,(lo,hi) in spans.items():
        rec={
            "observed_seconds":hi-lo,
            "start_utc":ts(lo),"end_utc":ts(hi),
            "evidence_ref":"evidence://synthetic/"+name,
            "evidence_sha256":"12345678abcdef00"*4,
        }
        if name.endswith("_rpo_seconds"):
            rec["acknowledged_commit_boundary_ref"]="evidence://synthetic/commit-boundary"
        record["measured_objectives"][name]=rec
    for field, entries in (("acceptance_gates",d.SCORECARD),
                           ("negative_path_scenarios",d.SCENARIOS)):
        for name in entries:
            record[field][name]={
                "status":"PASS","observer":"Synthetic-Witness",
                "evidence_ref":"evidence://synthetic/"+name,
                "evidence_sha256":"abcdef0012345678"*4,
            }
    for role in d.REVIEWERS:
        record["independent_final_signoffs"][role]={
            "name":"Synthetic-Cert-"+role,
            "disposition":"recommend_external_certification_review",
            "reviewed_at_utc":ts(-5),
            "attestation_ref":"evidence://synthetic/final-"+role,
        }
    return stage,review,preflight,record


class V04DTests(unittest.TestCase):
    def setUp(self):
        self.stage,self.review,self.preflight,self.record=complete_synthetic()

    def eval(self):
        return d.screen(self.stage,self.review,self.preflight,self.record,now=NOW)

    def refuse(self,reason):
        got=self.eval()
        self.assertEqual(got["result"],"NO_GO",got)
        self.assertIn(reason,got["reason_codes"],got)
        self.assertEqual(got["certification"],"NOT_CERTIFIED")
        self.assertEqual(got["authorization"],"NONE")
        self.assertEqual(got["execution"],"NEVER")

    def test_complete_synthetic_packet_never_certifies(self):
        got=self.eval()
        self.assertEqual(got["result"],"READY_FOR_EXTERNAL_CERTIFICATION_REVIEW",got)
        self.assertEqual(got["reason_codes"],[])
        self.assertEqual(got["certification"],"NOT_CERTIFIED")
        self.assertFalse(got["evidence_authenticated_by_tool"])

    def test_public_template_has_no_staging_certification(self):
        packets=[
            "v04_staging_evidence.template.json",
            "v04_independent_review.template.json",
            "v04c_rehearsal_request.template.json",
            "v04d_ch050_acceptance.template.json"
        ]
        docs=[json.loads((HERE/p).read_text(encoding="utf-8")) for p in packets]
        got=d.screen(*docs,now=NOW)
        self.assertEqual(got["result"],"NO_GO")
        self.assertIn("actual_staging_rehearsal_not_proven",got["reason_codes"])
        self.assertEqual(got["certification"],"NOT_CERTIFIED")

    def test_no_go_without_actual_exercise_and_fence(self):
        self.record["rehearsal"]["executed"]=False
        self.refuse("actual_staging_rehearsal_not_proven")
        self.stage,self.review,self.preflight,self.record=complete_synthetic()
        self.record["rehearsal"]["fence_survived_restart_attempt"]=False
        self.refuse("rehearsal_fence_survived_restart_attempt_unproven")

    def test_no_go_unless_external_manual_go_exists(self):
        self.record["manual_change_authority_go_ref"]="<UNVERIFIED>"
        self.refuse("external_manual_authority_record_missing")
        self.stage,self.review,self.preflight,self.record=complete_synthetic()
        self.record["manual_change_authority_go_at_utc"]=ts(-10)
        self.refuse("external_go_time_invalid")
        self.stage,self.review,self.preflight,self.record=complete_synthetic()
        self.record["v04c_preflight_screen_ref"]=""
        self.refuse("v04c_preflight_audit_missing")

    def test_prior_packet_binding_prevents_reuse(self):
        for key in ("v04a_sha256","v04b_sha256","v04c_sha256"):
            with self.subTest(key=key):
                self.stage,self.review,self.preflight,self.record=complete_synthetic()
                self.record[key]="a"*64
                self.refuse(key+"_mismatch")
        self.stage,self.review,self.preflight,self.record=complete_synthetic()
        self.record["change_ticket"]="SOME-OTHER-TICKET"
        self.refuse("change_ticket_binding_mismatch")

    def test_writes_cannot_shift_to_production_or_trigger_automatic_go(self):
        self.record["environment"]="production"
        self.refuse("non_staging_environment")
        self.stage,self.review,self.preflight,self.record=complete_synthetic()
        self.record["operational_go"]=True
        self.refuse("embedded_go_or_certification_refused")
        self.stage,self.review,self.preflight,self.record=complete_synthetic()
        self.record["certified"]=True
        self.refuse("embedded_go_or_certification_refused")
        self.stage,self.review,self.preflight,self.record=complete_synthetic()
        self.record["requested_disposition"]="CERTIFIED"
        self.refuse("machine_or_self_certification_refused")

    def test_all_metrics_enforce_approved_real_targets(self):
        for metric in d.METRICS:
            with self.subTest(metric=metric):
                self.stage,self.review,self.preflight,self.record=complete_synthetic()
                self.record["measured_objectives"][metric]["observed_seconds"]=100000
                self.refuse(metric+"_exceeds_approved_target")
                self.stage,self.review,self.preflight,self.record=complete_synthetic()
                self.record["measured_objectives"][metric]["observed_seconds"]=None
                self.refuse(metric+"_measured_missing")
                self.stage,self.review,self.preflight,self.record=complete_synthetic()
                self.record["measured_objectives"][metric]["observed_seconds"]=1
                self.refuse(metric+"_arithmetic_mismatch")

    def test_rpo_requires_commit_boundary_evidence(self):
        self.record["measured_objectives"]["ha_rpo_seconds"].pop(
            "acknowledged_commit_boundary_ref")
        self.refuse("ha_rpo_seconds_commit_boundary_missing")

    def test_every_ch050_acceptance_row_is_mandatory(self):
        for row in d.SCORECARD:
            with self.subTest(row=row):
                self.stage,self.review,self.preflight,self.record=complete_synthetic()
                self.record["acceptance_gates"][row]["status"]="PENDING"
                self.refuse("acceptance_gates_"+row+"_not_passed")

    def test_negative_path_scenarios_are_mandatory(self):
        for row in d.SCENARIOS:
            with self.subTest(row=row):
                self.stage,self.review,self.preflight,self.record=complete_synthetic()
                self.record["negative_path_scenarios"][row]["evidence_ref"]="<NOT-RUN>"
                self.refuse("negative_path_scenarios_"+row+"_evidence_missing")

    def test_final_signoffs_after_rehearsal_and_distinct(self):
        self.record["independent_final_signoffs"]["dbre"]["disposition"]="pending"
        self.refuse("final_dbre_signature_missing")
        self.stage,self.review,self.preflight,self.record=complete_synthetic()
        self.record["independent_final_signoffs"]["dbre"]["reviewed_at_utc"]=ts(-40)
        self.refuse("final_dbre_timestamp_invalid")
        self.stage,self.review,self.preflight,self.record=complete_synthetic()
        self.record["independent_final_signoffs"]["dbre"]["name"]="Synthetic-Operator"
        self.refuse("final_signoff_not_independent")
        self.stage,self.review,self.preflight,self.record=complete_synthetic()
        self.record["independent_final_signoffs"]["dbre"]["name"]=(
            self.record["independent_final_signoffs"]["application"]["name"])
        self.refuse("final_signoff_not_independent")

    def test_approved_window_and_preaction_fencing_are_hard_gates(self):
        self.record["rehearsal"]["started_at_utc"]=ts(-3700)
        self.refuse("rehearsal_window_or_timeline_invalid")
        self.stage,self.review,self.preflight,self.record=complete_synthetic()
        self.preflight["fresh_observations"]["independent_fence"][
            "observed_at_utc"]=ts(-1000)
        self.record["v04c_sha256"]=b.digest(self.preflight)
        self.refuse("pre_rehearsal_independent_fence_stale")
        self.stage,self.review,self.preflight,self.record=complete_synthetic()
        self.preflight["authorities"]["change_authority"]["attested_at_utc"]=ts(-1)
        self.record["v04c_sha256"]=b.digest(self.preflight)
        self.refuse("pre_rehearsal_approvals_invalid")

    def test_secret_keys_rejected(self):
        self.record["rehearsal"]["access_token"]="bad"
        self.refuse("sensitive_keys_in_record")

    def test_cli_templates_exit_2_with_not_certified(self):
        args=[]
        for flag,path in (
            ("--staging","v04_staging_evidence.template.json"),
            ("--review","v04_independent_review.template.json"),
            ("--preflight","v04c_rehearsal_request.template.json"),
            ("--acceptance","v04d_ch050_acceptance.template.json")):
            args.extend([flag,str(HERE/path)])
        p=subprocess.run([sys.executable,str(HERE/"v04d_ch050_acceptance.py")]+args,
                         capture_output=True,text=True,check=False)
        self.assertEqual(2,p.returncode,p.stderr)
        result=json.loads(p.stdout)
        self.assertEqual(result["result"],"NO_GO")
        self.assertEqual(result["certification"],"NOT_CERTIFIED")

    def test_unreadable_cli_packet_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/"invalid.json"
            p.write_text("{bad",encoding="utf-8")
            args=[]
            for flag in ("staging","review","preflight","acceptance"):
                args+=["--"+flag,str(p)]
            x=subprocess.run([sys.executable,str(HERE/"v04d_ch050_acceptance.py")]+args,
                             capture_output=True,text=True,check=False)
            self.assertEqual(2,x.returncode)
            self.assertIn('"certification": "NOT_CERTIFIED"',x.stdout)


if __name__=="__main__":
    unittest.main()
