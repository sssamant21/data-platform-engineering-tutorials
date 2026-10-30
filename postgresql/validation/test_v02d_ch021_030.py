#!/usr/bin/env python3
"""V02-D Chapter 021-030 contracts and offline evidence helper regression tests.

No PostgreSQL, network requests, shell lifecycle, data deletion or live probes.
"""
import copy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
IDS = [f"{x:03}" for x in range(21, 31)]
REQUIRED = {
 "021": ["021-lab-operation-probe.py", "021-slo-evaluate.py"],
 "022": ["022-database-statistics-snapshot.sql", "022-statistics-window-delta.py"],
 "023": ["023-query-statistics-snapshot.sql", "023-query-window-rank.py"],
 "024": ["024-correlate-json-logs.py", "024-lab-trace-workload.py"],
 "025": ["025-lab-alert-receiver.py"],
 "026": ["026-collect-lab-triage.sh", "026-triage-snapshot.sql"],
 "027": ["027-plan-summary.py", "027-read-plan.sql", "027-write-plan-rollback.sql"],
 "028": ["028-statistics-setup.sql", "028-statistics-plan.sql",
         "028-statistics-inventory.sql"],
 "029": ["029-resource-window.sh", "029-resource-snapshot.sql",
         "029-resource-workload.sql"],
 "030": ["030-project-setup.sql", "030-request-probe.py",
         "030-project-observer.sql", "030-project-plan.sql"],
}

def module(name):
    spec = importlib.util.spec_from_file_location("v02d_" + name, SCRIPTS / name)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

SLO = module("021-slo-evaluate.py")
STAT = module("022-statistics-window-delta.py")
RANK = module("023-query-window-rank.py")
LOG = module("024-correlate-json-logs.py")
ALERT = module("025-lab-alert-receiver.py")
PLAN = module("027-plan-summary.py")
T0 = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)


def statistics_sample(epoch=0, **overrides):
    sample = {
        "schema_version": 1, "source_id": "chapter004-primary-55432",
        "server_addr": "127.0.0.1", "server_port": 55432,
        "server_version_num": 180003, "postmaster_start": (T0 - timedelta(days=1)).isoformat(),
        "in_recovery": False, "database_oid": 16390, "database_name": "c022_stats",
        "track_counts": "on", "stats_reset": (T0 - timedelta(days=1)).isoformat(),
        "snapshot_at": (T0 + timedelta(seconds=epoch)).isoformat(),
        "sampled_at": (T0 + timedelta(seconds=epoch, microseconds=10000)).isoformat(),
        "counters": {k: epoch * (i + 1) for i, k in enumerate(STAT.COUNTERS)},
        "gauges": {"numbackends": 2},
    }
    sample.update(overrides)
    return sample


def statement_sample(seconds=0, *, calls=0, exec_ms=0.0):
    return {
        "schema_version": 1, "source_id": "chapter004-primary-55432",
        "server_addr": "127.0.0.1", "server_port": 55432,
        "server_version_num": 180003, "postmaster_start": (T0 - timedelta(days=1)).isoformat(),
        "in_recovery": False, "database_oid": 16390, "role_oid": 16391,
        "extension_version": "1.12", "policy": {
            "compute_query_id": "on", "track": "top", "track_utility": "off",
            "track_planning": "off"
        },
        "global_reset": (T0 - timedelta(hours=1)).isoformat(),
        "dealloc": 0, "sampled_at": (T0 + timedelta(seconds=seconds)).isoformat(),
        "truncated": False,
        "entries": [{
            "userid": 16391, "dbid": 16390, "queryid": "123456789",
            "toplevel": True, "stats_since": (T0 - timedelta(minutes=5)).isoformat(),
            "calls": calls, "total_exec_time": exec_ms, "rows": calls,
            "shared_blks_hit": calls * 2, "shared_blks_read": 0,
            "temp_blks_written": 0,
        }]
    }


class Review021030(unittest.TestCase):
    def test_chapter_to_lab_and_scripts(self):
        for ch in IDS:
            labs = list((ROOT / "labs").glob(ch + "-*-lab.md"))
            chapters = list((ROOT / "chapters").glob(ch + "-*.md"))
            with self.subTest(chapter=ch):
                self.assertEqual(len(labs), 1)
                self.assertEqual(len(chapters), 1)
                self.assertIn("../labs/" + labs[0].name,
                              chapters[0].read_text(encoding="utf-8"))
                lab = labs[0].read_text(encoding="utf-8")
                for source in REQUIRED[ch]:
                    self.assertTrue((SCRIPTS / source).is_file(), source)
                    self.assertIn(source, lab, source)

    def test_setup_sql_hard_rejects_wrong_cluster(self):
        for ch in ("028", "030"):
            script = (SCRIPTS / f"{ch}-" + "setup.sql") if False else (
                SCRIPTS / ("028-statistics-setup.sql" if ch == "028" else "030-project-setup.sql"))
            text = script.read_text(encoding="utf-8")
            with self.subTest(chapter=ch):
                for guard in (
                    "BEGIN;", "DO $lab_target$", "current_database() <> 'ops_lab'",
                    "current_user <> 'lab_admin'", "pg_is_in_recovery()",
                    "inet_server_port() IS DISTINCT FROM 55432",
                    "current_setting('server_version_num')",
                    "current_setting('data_directory')",
                    "RAISE EXCEPTION", "$lab_target$;", "COMMIT;",
                ):
                    self.assertIn(guard, text)

    def test_slo_quality_and_burn_arithmetic(self):
        events = [(T0 + timedelta(seconds=i), True, status, Decimal(duration))
                  for i, (status, duration) in enumerate(((True, 100), (True, 500), (False, 100)))]
        outcome = SLO.evaluate(events, T0 + timedelta(seconds=10), 60,
                               Decimal(250), Decimal("0.9"), Decimal("0.8"), 5)
        self.assertEqual(outcome["quality"], "LOW_VOLUME")
        self.assertEqual(outcome["availability"]["good"], 2)
        self.assertEqual(outcome["timely_success"]["good"], 1)
        self.assertEqual(outcome["availability"]["bad"], 1)
        self.assertEqual(outcome["timely_success"]["bad"], 2)
        self.assertEqual(outcome["excluded"], 0)

    def test_slo_empty_and_bad_targets(self):
        empty = SLO.evaluate([], T0, 60, Decimal(250), Decimal(".99"),
                             Decimal(".9"), 1)
        self.assertEqual(empty["quality"], "NO_EVENTS")
        self.assertIsNone(empty["availability"]["sli"])
        for target in (Decimal("0"), Decimal("1"), Decimal("NaN")):
            with self.subTest(target=target), self.assertRaises(ValueError):
                SLO.evaluate([], T0, 60, Decimal(250), target, Decimal(".9"), 1)

    def test_statistics_interval_and_reset_rejection(self):
        before, after = statistics_sample(0), statistics_sample(60)
        result = STAT.compare(before, after)
        self.assertEqual(result["snapshot_elapsed_seconds"], "60")
        self.assertEqual(result["deltas"]["xact_commit"], 60)
        self.assertTrue(result["valid"])
        reset = copy.deepcopy(after)
        reset["stats_reset"] = (T0 + timedelta(seconds=30)).isoformat()
        with self.assertRaisesRegex(ValueError, "incompatible window"):
            STAT.compare(before, reset)
        reset = copy.deepcopy(after)
        reset["counters"]["deadlocks"] = -1
        with self.assertRaises(ValueError):
            STAT.compare(before, reset)

    def test_statements_rank_and_epoch_exclusion(self):
        before = statement_sample(0, calls=5, exec_ms=50.0)
        after = statement_sample(60, calls=15, exec_ms=450.0)
        result = RANK.compare(before, after)
        self.assertEqual(len(result["ranked"]), 1)
        self.assertEqual(result["ranked"][0]["delta"]["calls"], "10")
        self.assertEqual(result["ranked"][0]["delta"]["total_exec_time"], "400.0")
        changed = copy.deepcopy(after)
        changed["entries"][0]["stats_since"] = (T0 + timedelta(seconds=2)).isoformat()
        result = RANK.compare(before, changed)
        self.assertEqual(len(result["ranked"]), 0)
        self.assertEqual(len(result["excluded"]), 1)

    def test_statements_malformed_sample_fails_closed(self):
        with self.assertRaises(ValueError):
            RANK.index([{"schema_version": 1}])
        sample = statement_sample()
        sample["entries"] = [None]
        with self.assertRaisesRegex(ValueError, "entry object"):
            RANK.index(sample)
        sample = statement_sample()
        sample["truncated"] = True
        with self.assertRaises(ValueError):
            RANK.index(sample)

    def test_sanitized_log_correlation_not_plaintext_export(self):
        trace_id = "0123456789abcdef" * 2
        trace = {
            "trace_id": trace_id, "span_id": "0123456789abcdef",
            "source_id": "chapter004-primary-55432", "database": "c024_logs",
            "application_name": "c024_" + trace_id, "pid": 12345,
            "session_id": "12345678.3039", "start": T0.isoformat(),
            "end": (T0 + timedelta(seconds=2)).isoformat(),
            "duration_ms": 1000.0, "outcome": "success",
        }
        log = {
            "application_name": trace["application_name"],
            "dbname": "c024_logs", "pid": 12345, "session_id": "12345678.3039",
            "timestamp": (T0 + timedelta(milliseconds=1000)).isoformat(),
            "line_num": 1, "error_severity": "LOG",
            "message": "duration: 1000.000 ms statement: SELECT secret FROM table",
            "query_id": 123,
        }
        result = LOG.correlate([log, log], [trace], "chapter004-primary-55432")
        self.assertEqual(result["duplicate_records_skipped"], 1)
        self.assertEqual(result["traces"][0]["server_events"][0]["kind"], "completed_duration")
        self.assertNotIn("secret", str(result))
        with self.assertRaisesRegex(ValueError, "conflicting duplicate"):
            changed = dict(log, message="different sensitive statement")
            LOG.correlate([log, changed], [trace], "chapter004-primary-55432")

    def test_alert_receiver_rejects_foreign_cluster(self):
        def alarm(cluster="chapter004", status="firing"):
            return {"status": status, "alerts": [{
                "status": status, "labels": {
                    "alertname": "PgDatabaseProbeFailed", "environment": "lab",
                    "cluster": cluster, "owner": "sre"
                }
            }]}
        result = ALERT.summarize(alarm())
        self.assertEqual(result["alerts"][0]["labels"]["cluster"], "chapter004")
        with self.assertRaisesRegex(ValueError, "outside disposable lab"):
            ALERT.summarize(alarm(cluster="production"))
        with self.assertRaises(ValueError):
            ALERT.summarize(alarm(status="unknown"))

    def test_explain_plan_summary_numeric_and_recursive_nodes(self):
        doc = [{"Plan": {
            "Node Type": "Aggregate", "Plan Rows": 1, "Actual Rows": 1,
            "Actual Loops": 1, "Shared Hit Blocks": 2, "Plans": [{
                "Node Type": "Seq Scan", "Plan Rows": 10, "Actual Rows": 5,
                "Actual Loops": 2
            }]
        }, "Planning Time": 0.12, "Execution Time": 1.5}]
        out = PLAN.summarize(doc)
        self.assertEqual(len(out["nodes"]), 2)
        self.assertEqual(out["nodes"][1]["approx_rows_across_loops"], 10)
        self.assertEqual(out["nodes"][1]["actual_to_estimated_rows"], 0.5)
        self.assertIn("Shared Hit Blocks", out["nodes"][0]["buffers_as_reported_inclusive"])
        with self.assertRaisesRegex(ValueError, "actual rows and loops"):
            bad = copy.deepcopy(doc)
            del bad[0]["Plan"]["Actual Loops"]
            PLAN.summarize(bad)
        with self.assertRaises(ValueError):
            PLAN.summarize([{"Plan": {"Node Type": "Seq Scan", "Plan Rows": -1}}])


if __name__ == "__main__":
    unittest.main()
