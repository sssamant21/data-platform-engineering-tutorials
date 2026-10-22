#!/usr/bin/env python3
"""One-command, non-executing Kafka curriculum QA.

Run from any directory: python kafka/qa/run_qa.py --stage static
Docker + ShellCheck image required for shell lint. No Kafka labs are executed.
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

QA = Path(__file__).resolve().parent
ROOT = QA.parent
EVIDENCE = QA / "evidence"


def run(label: str, script: str, extra: list[str]) -> dict:
    command = [sys.executable, str(QA / script), *extra]
    print(f"\n== {label} ==", flush=True)
    try:
        proc = subprocess.run(command, cwd=ROOT.parent, check=False)
        return {"stage": label, "exit_code": proc.returncode,
                "status": "ERROR" if proc.returncode >= 2 else "FAIL" if proc.returncode else "PASS_OR_REVIEW"}
    except OSError as exc:
        print(f"{label}: {exc}", file=sys.stderr)
        return {"stage": label, "exit_code": 2, "status": "ERROR", "error": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=["static", "shell", "report", "kubernetes", "all-static", "strimzi"], default="static")
    parser.add_argument("--no-shell", action="store_true", help="Skip Docker ShellCheck")
    args = parser.parse_args()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    results = []
    if args.stage in ("static", "all-static"):
        results.append(run("curriculum", "audit_curriculum.py",
                           ["--root", str(ROOT), "--output", str(EVIDENCE / "repository-audit.json")]))
        results.append(run("code-blocks", "validate_code_blocks.py",
                           ["--root", str(ROOT), "--output", str(EVIDENCE / "code-block-audit.json")]))
    if args.stage in ("static", "shell", "all-static") and not args.no_shell:
        results.append(run("shellcheck", "lint_embedded_shell.py",
                           ["--root", str(ROOT), "--output", str(EVIDENCE / "shellcheck-automated.json"),
                            "--resume"]))
    if args.stage in ("static", "shell", "report", "all-static") and not args.no_shell:
        report_path = EVIDENCE / "shellcheck-automated.json"
        if report_path.exists():
            results.append(run("shellcheck-report", "summarize_shellcheck.py",
                               ["--input", str(report_path), "--output",
                                str(EVIDENCE / "shellcheck-review.md")]))
        else:
            results.append({"stage": "shellcheck-report", "exit_code": 2,
                            "status": "ERROR", "error": "No ShellCheck evidence found"})
    if args.stage in ("kubernetes", "all-static"):
        results.append(run("kubernetes-inventory", "audit_kubernetes_manifests.py",
                           ["--root", str(ROOT), "--output", str(EVIDENCE / "kubernetes-manifest-audit.json")]))
        results.append(run("kubernetes-schema", "validate_kubernetes_schemas.py",
                           ["--root", str(ROOT), "--output", str(EVIDENCE / "kubernetes-schema-audit.json"), "--docker"]))
    # Read evidence counts; exit 0 means execution succeeded, not that every item passed.
    evidence_names = {
        "kubernetes-inventory": "kubernetes-manifest-audit.json",
        "kubernetes-schema": "kubernetes-schema-audit.json",
    }
    for item in results:
        evidence_name = evidence_names.get(item["stage"])
        if evidence_name and item["exit_code"] == 0:
            try:
                counts = json.loads((EVIDENCE / evidence_name).read_text(encoding="utf-8"))["summary"]
                item["counts"] = counts
                item["status"] = "PASS_WITH_REVIEW" if counts.get("REVIEW", 0) else "PASS"
            except (OSError, KeyError, ValueError):
                item["status"] = "UNKNOWN"
    if args.stage in ("strimzi", "all-static"):
        results.append(run("strimzi-crd", "validate_strimzi_crds.py",
                           ["--root", str(ROOT), "--output", str(EVIDENCE / "strimzi-schema-audit.json"),
                            "--cache", str(EVIDENCE / "schema-cache")]))
    summary = {"generated_at_utc": datetime.now(timezone.utc).isoformat(),
               "scope": "Offline/static only. No Kubernetes/Kafka runtime lab certification.",
               "stages": results}
    (EVIDENCE / "qa-summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print("\nQA summary:")
    for item in results:
        print(f"  {item['stage']}: {item['status']} (exit {item['exit_code']})")
    print(f"Evidence: {EVIDENCE / 'qa-summary.json'}")
    return 2 if any(x["exit_code"] >= 2 for x in results) else 1 if any(x["exit_code"] for x in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
