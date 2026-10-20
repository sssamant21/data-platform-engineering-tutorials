#!/usr/bin/env python3
"""L0 documentation contract for Chapters 01–04; never executes Markdown code."""
import argparse
import json
import pathlib
import re
import sys

CHAPTERS = {
    1: ("01-mongodb-enterprise-fundamentals.md", ("prerequisite", "failure", "cleanup", "acceptance")),
    2: ("02-document-model-and-bson-types.md", ("prerequisite", "failure", "cleanup", "acceptance")),
    3: ("03-server-architecture-and-wiredtiger.md", ("prerequisite", "failure", "cleanup", "wiredtiger")),
    4: ("04-community-enterprise-advanced-and-atlas.md", ("prerequisite", "failure", "cleanup", "topology")),
}
def check(root):
    results = []
    for n, (name, terms) in CHAPTERS.items():
        path = root / name
        problems = []
        if not path.is_file():
            problems.append("missing chapter")
        else:
            text = path.read_text(encoding="utf-8")
            headings = [s.lower() for s in re.findall(r"^#{1,6}\s+(.+)$", text, re.M)]
            for term in terms:
                if not any(term in h for h in headings):
                    problems.append("missing heading contract: " + term)
            if "runtime lab validation pending" not in text.lower():
                problems.append("missing explicit runtime pending disclaimer")
            if not re.search(r"^\s*```(?:javascript|js|bash|shell|sh)", text, re.M):
                problems.append("missing runnable example fence")
        results.append({"chapter": n, "file": name, "passed": not problems, "errors": problems,
                        "runtime_certified": False})
    return {"level": "L0", "passed": all(r["passed"] for r in results),
            "runtime_certified": False, "results": results}
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    report = check(args.root)
    serialized = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")
    return 0 if report["passed"] else 1
if __name__ == "__main__":
    sys.exit(main())
