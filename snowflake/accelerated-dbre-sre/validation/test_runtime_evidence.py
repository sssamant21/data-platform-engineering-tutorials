#!/usr/bin/env python3
"""V03 evidence gate regression tests; synthetic fixtures only; no Snowflake."""
from __future__ import annotations
from copy import deepcopy
import unittest
from validate_runtime_evidence import audit

FAKE_SHA = "a" * 40
QID = "01234567-89ab-cdef-0123-456789abcdef"
QID2 = "12345678-90ab-cdef-0123-456789abcdef"
def template(level=1):
    return {
        "schema_version": 1, "level": level, "execution_state": "NOT_RUN",
        "revision_sha": "", "started_at_utc": None,
        "environment": {
            "classification": "TRAINING",
            "account_alias": "SANITIZED_TRAINING",
            "warehouse_alias": "TRAINING_XS",
            "role_alias": "LAB_READONLY",
            "scratch_schema_alias": "SCRATCH_TRAINING",
        },
        "approval_reference": None, "runner_alias": None,
        "query_ids": [], "tests": [], "assertions": {},
        "cleanup_verified": False, "redaction_checked": False,
        "evidence_reference": None, "independent_reviewer_alias": None,
        "independent_review_status": "PENDING",
    }
def executed(level=1):
    d = template(level)
    d.update({
        "execution_state": "EXECUTED", "revision_sha": FAKE_SHA,
        "started_at_utc": "2026-10-30T18:00:00Z",
        "approval_reference": "APPROVED_CHANGE_TICKET",
        "runner_alias": "REDACTED_OPERATOR",
        "query_ids": [QID, QID2],
        "cleanup_verified": True, "redaction_checked": True,
        "evidence_reference": "PRIVATE_EVIDENCE_REGISTER",
    })
    req = {
        1: ("session_context","sample_values","temporary_table","aggregates","assertion","session_cleanup"),
        2: ("session_context","role_visibility","generated_rows","tagged_history","tag_cleanup"),
        3: ("session_context","namespace_check","generated_table","assertion","query_profile","session_cleanup"),
    }
    d["tests"] = [{"id": k, "status": "PASS", "query_id": QID} for k in req.get(level, ())]
    if level == 1:
        d["assertions"] = {
            "values_rows": 3, "training_rows": 3, "east_count": 2,
            "east_sales": 170, "west_count": 1, "west_sales": 80,
            "smoke_result": "PASS",
        }
    elif level == 2:
        d["assertions"] = {"generated_rows": 100, "tag_cleanup": "CONFIRMED"}
    return d

class EvidenceTests(unittest.TestCase):
    def test_not_run_safe_template(self):
        self.assertEqual("NOT_RUN", audit(template())["outcome"])
    def test_block_prod_environment(self):
        d = executed()
        d["environment"]["classification"] = "PRODUCTION"
        self.assertEqual("REJECTED", audit(d)["outcome"])
    def test_block_admin_role(self):
        d = executed()
        d["environment"]["role_alias"] = "ACCOUNTADMIN"
        self.assertEqual("REJECTED", audit(d)["outcome"])
    def test_block_embedded_secret_key(self):
        d = executed()
        d["password"] = "SHOULD_NOT_BE_HERE"
        self.assertEqual("REJECTED", audit(d)["outcome"])
    def test_block_missing_query_ids(self):
        d = executed()
        d["query_ids"] = []
        self.assertEqual("REJECTED", audit(d)["outcome"])
    def test_block_fake_query_id_shape(self):
        d = executed()
        d["query_ids"] = ["abc"]
        self.assertEqual("REJECTED", audit(d)["outcome"])
    def test_block_wrong_assertion(self):
        d = executed()
        d["assertions"]["east_sales"] = 999
        self.assertEqual("REJECTED", audit(d)["outcome"])
    def test_block_missing_required_test(self):
        d = executed()
        d["tests"] = d["tests"][:-1]
        self.assertEqual("REJECTED", audit(d)["outcome"])
    def test_block_failed_required_test(self):
        d = executed()
        d["tests"][0]["status"] = "BLOCKED"
        self.assertEqual("REJECTED", audit(d)["outcome"])
    def test_block_undocumented_test(self):
        d = executed()
        d["tests"].append({"id":"drop_database", "status":"PASS", "query_id":QID})
        self.assertEqual("REJECTED", audit(d)["outcome"])
    def test_block_notrun_claiming_reviewed(self):
        d = template()
        d["independent_review_status"] = "APPROVED"
        self.assertEqual("REJECTED", audit(d)["outcome"])
    def test_l1_synthetic_eligible_for_review_only(self):
        self.assertEqual("READY_FOR_INDEPENDENT_REVIEW", audit(executed())["outcome"])
    def test_l2_synthetic_eligible_for_review_only(self):
        self.assertEqual("READY_FOR_INDEPENDENT_REVIEW", audit(executed(2))["outcome"])
    def test_block_unredacted_sql(self):
        d = executed()
        d["tests"][0]["sql_text"] = "SELECT * FROM PATIENTS"
        self.assertEqual("REJECTED", audit(d)["outcome"])
    def test_block_missing_redaction_attestation(self):
        d = executed()
        d["redaction_checked"] = False
        self.assertEqual("REJECTED", audit(d)["outcome"])
    def test_block_missing_cleanup(self):
        d = executed()
        d["cleanup_verified"] = False
        self.assertEqual("REJECTED", audit(d)["outcome"])
    def test_block_unapproved_reviewer(self):
        d = executed()
        d["independent_review_status"] = "APPROVED"
        self.assertEqual("REJECTED", audit(d)["outcome"])
    def test_reviewer_alias_required(self):
        d = executed()
        d["independent_review_status"] = "APPROVED"
        d["independent_reviewer_alias"] = "APPROVED_REVIEWER"
        self.assertEqual("READY_FOR_INDEPENDENT_REVIEW", audit(d)["outcome"])
    def test_no_execution_without_results(self):
        d = template()
        d["execution_state"] = "EXECUTED"
        self.assertEqual("REJECTED", audit(d)["outcome"])

if __name__ == "__main__":
    unittest.main()
