#!/usr/bin/env python3
"""Regression tests for the Snowflake accelerated-track static SQL guard.

No Snowflake connection is made. Tests use only Python's standard library.
"""
from __future__ import annotations
import unittest
import validate_courses as validator


class UnsafeSQLTest(unittest.TestCase):
    def assert_blocked(self, sql: str) -> None:
        self.assertTrue(validator.unsafe_sql_statements(sql), sql)

    def assert_allowed(self, sql: str) -> None:
        self.assertEqual([], validator.unsafe_sql_statements(sql), sql)

    def test_safe_queries_and_show(self):
        self.assert_allowed("SELECT CURRENT_USER(); SHOW WAREHOUSES; SHOW GRANTS;")

    def test_allowed_session_tag_operations(self):
        self.assert_allowed(
            "ALTER SESSION SET QUERY_TAG = 'snowflake_dbre_sre_l2_runtime_smoke';"
            "ALTER SESSION UNSET QUERY_TAG;"
        )

    def test_safe_temporary_table_and_training_insert(self):
        self.assert_allowed(
            "CREATE TEMP TABLE DBRE_SRE_L1_QA_20261030 (ID NUMBER);"
            "INSERT INTO DBRE_SRE_L1_QA_20261030 VALUES (1);"
        )

    def test_controlled_recovery_training_table(self):
        self.assert_allowed(
            "CREATE TABLE DBRE_SRE_L6_RECOVERY (ID NUMBER);"
            "INSERT INTO DBRE_SRE_L6_RECOVERY VALUES (1);"
        )

    def test_comments_not_executed(self):
        self.assert_allowed(
            "-- DROP TABLE PROD;\nSELECT 1; -- GRANT ROLE ACCOUNTADMIN TO USER X\n"
            "/* ALTER WAREHOUSE PROD SUSPEND; */ SHOW WAREHOUSES;"
        )

    def test_multiline_drop(self):
        self.assert_blocked("DROP\nTABLE PROD;")

    def test_multiline_warehouse_alter(self):
        self.assert_blocked("ALTER\nWAREHOUSE PROD SUSPEND;")

    def test_replace_variant(self):
        self.assert_blocked("CREATE OR\n REPLACE TABLE PROD (ID NUMBER);")

    def test_grant_after_select(self):
        self.assert_blocked("SELECT 1;\nGRANT ROLE ACCOUNTADMIN TO USER X;")

    def test_prohibited_insert_target(self):
        self.assert_blocked("INSERT INTO PROD.PATIENTS VALUES (1);")

    def test_prohibited_create_target(self):
        self.assert_blocked("CREATE TABLE PROD.PATIENTS (ID NUMBER);")

    def test_prohibited_privilege_escalation(self):
        self.assert_blocked("USE ROLE ACCOUNTADMIN;")

    def test_delete_in_cte(self):
        self.assert_blocked("WITH X AS (DELETE FROM PROD) SELECT * FROM X;")

    def test_semicolon_injection(self):
        self.assert_blocked("SELECT CURRENT_USER(); DROP TABLE PROD;")

    def test_invalid_session_change(self):
        self.assert_blocked("ALTER SESSION SET STATEMENT_TIMEOUT_IN_SECONDS = 0;")

    def test_l3_training_create_as_select(self):
        self.assert_allowed(
            "CREATE TEMP TABLE DBRE_SRE_L3_QA_20261030 AS "
            "SELECT ORDER_ID FROM (SELECT ROW_NUMBER() OVER (ORDER BY SEQ4()) AS ORDER_ID "
            "FROM TABLE(GENERATOR(ROWCOUNT => 1000)));"
        )

    def test_l3_arithmetic_expectations(self):
        orders = list(range(1, 1001))
        self.assertEqual(1000, len(orders))
        self.assertEqual(54110, sum(10 + (i % 90) for i in orders))
        filtered = [i for i in orders if i % 10 == 1]
        self.assertEqual(100, len(filtered))
        self.assertEqual(5060, sum(10 + (i % 90) for i in filtered))

    def test_l4_monitoring_read_only(self):
        self.assert_allowed(
            "SELECT WAREHOUSE_NAME, SUM(CREDITS_USED) "
            "FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY "
            "GROUP BY WAREHOUSE_NAME;"
        )

    def test_l4_disallow_monitoring_role_escalation(self):
        self.assert_blocked("GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO ROLE PUBLIC;")


    def test_l5_read_only_role_discovery(self):
        self.assert_allowed(
            "SELECT CURRENT_ROLE(), CURRENT_SECONDARY_ROLES();"
            "SHOW GRANTS; SHOW ROLES;"
        )

    def test_l5_login_audit_aggregate(self):
        self.assert_allowed(
            "SELECT IS_SUCCESS, COUNT(*) AS N "
            "FROM SNOWFLAKE.ACCOUNT_USAGE.LOGIN_HISTORY "
            "GROUP BY IS_SUCCESS;"
        )

    def test_l6_retention_and_historical_select(self):
        self.assert_allowed(
            "SHOW PARAMETERS LIKE 'MIN_DATA_RETENTION_TIME_IN_DAYS' IN ACCOUNT;"
            "SHOW PARAMETERS LIKE 'DATA_RETENTION_TIME_IN_DAYS' IN DATABASE DBRE_SRE_LAB;"
            "SELECT COUNT(*) FROM DBRE_SRE_L6_RECOVERY AT (OFFSET => -60);"
        )

    def test_l6_drop_training_table_is_forbidden(self):
        self.assert_blocked("DROP TABLE DBRE_SRE_L6_RECOVERY;")

    def test_l7_read_only_incident_metrics(self):
        self.assert_allowed(
            "SELECT QUERY_ID, ERROR_CODE, QUEUED_OVERLOAD_TIME "
            "FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY_BY_SESSION(RESULT_LIMIT => 1000));"
        )

    def test_l7_no_incident_query_cancellation(self):
        self.assert_blocked("CALL SYSTEM$CANCEL_QUERY('test-id');")


if __name__ == "__main__":
    unittest.main()
