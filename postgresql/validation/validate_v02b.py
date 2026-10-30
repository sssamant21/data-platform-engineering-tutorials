#!/usr/bin/env python3
"""V02-B static cleanup safeguard checks. Does not connect to PostgreSQL."""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLEANUP_IDS = ("032", "033", "034", "035", "036", "038", "039", "040", "047", "048")
SETUP_IDS = ("032", "033", "034", "035", "036")


def run():
    errors, inspected = [], []
    for chapter in CLEANUP_IDS:
        script = ROOT / "labs" / "sql" / f"{chapter}-cleanup.sql"
        docs = list((ROOT / "labs").glob(f"{chapter}-*-lab.md"))
        if not script.is_file() or len(docs) != 1:
            errors.append({"chapter": chapter, "error": "cleanup SQL or unique lab document missing"})
            continue
        source = script.read_text(encoding="utf-8")
        guide = docs[0].read_text(encoding="utf-8")
        required = (
            r"\if :{?expected_db}",
            r"\if :{?expected_system_id}",
            r"\if :{?confirm_cleanup}",
            "current_database() = :'expected_db'",
            "pg_control_system()",
            "current_setting('server_version_num')",
            "NOT pg_is_in_recovery()",
            f"= '{chapter}-DROP'",
            r"\gset",
            r"\if :cleanup_permitted",
            "SELECT 1/0 AS refusal_nonzero;",
        )
        missing = [x for x in required if x not in source]
        if missing:
            errors.append({"chapter": chapter, "error": "missing cleanup protection", "patterns": missing})
        if f"-v confirm_cleanup={chapter}-DROP" not in guide or "-v expected_system_id=" not in guide:
            errors.append({"chapter": chapter, "error": "lab guide missing expected invocation"})
        inspected.append({"chapter": chapter, "script": script.name, "lab": docs[0].name,
                          "static_guards_present": not missing})
    # A psql \\quit 3 does not set a nonzero shell exit status.
    # Fail static validation on unsafe psql refusal branches.
    for script in (ROOT / "labs" / "sql").glob("*.sql"):
        content = script.read_text(encoding="utf-8")
        if r"\\quit 3" in content:
            errors.append({"chapter": script.name,
                           "error": "unsafe psql \\quit 3: use ON_ERROR_STOP and a SQL-error refusal"})
    for chapter in SETUP_IDS:
        path = ROOT / "labs" / "sql" / f"{chapter}-setup.sql"
        if not path.is_file():
            errors.append({"chapter": chapter, "error": "setup missing"})
        elif re.search(r"\bDROP\s+SCHEMA\b", path.read_text(encoding="utf-8"), re.I):
            errors.append({"chapter": chapter, "error": "automatic schema drop returned to setup"})
    return {"version": "V02-B", "status": "FAIL" if errors else "PASS_STATIC_GUARD_CHECK",
            "runtime_execution": "NOT_EXECUTED", "cleanup_scripts_checked": len(inspected),
            "setup_scripts_checked": len(SETUP_IDS), "errors": errors, "inspected": inspected}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    result = run()
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    raise SystemExit(1 if result["errors"] else 0)
