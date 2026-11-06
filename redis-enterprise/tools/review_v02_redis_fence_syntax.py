#!/usr/bin/env python3
"""Audit Redis-language Markdown fences for shell continuations and bare SCAN verbs.

Offline static analysis only. Does not execute or connect to Redis.
Language-specific concerns are potential defects, not a blanket code audit.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from collections import Counter
from validate_v02_examples import CHAPTER, find_blocks

BAD_BARE_CURSOR = re.compile(r"^\s*(SCAN|HSCAN|SSCAN|ZSCAN)\s*$", re.I)
CONTINUATION = re.compile(r"\\\s*$")


def inspect(root: Path) -> dict:
    findings = []
    chapters = 0
    redis_blocks = 0
    for file in sorted(root.glob("*.md")):
        if not CHAPTER.fullmatch(file.name):
            continue
        chapters += 1
        lines = file.read_text(encoding="utf-8-sig").splitlines()
        for b in find_blocks(lines):
            if b["language"] != "redis":
                continue
            redis_blocks += 1
            for offset, line in enumerate(b["source"].splitlines()):
                reasons = []
                if CONTINUATION.search(line):
                    reasons.append("shell_continuation_in_interactive_redis")
                if BAD_BARE_CURSOR.fullmatch(line):
                    reasons.append("cursor_command_missing_arguments")
                for reason in reasons:
                    findings.append({
                        "chapter": int(file.name[:2]), "file": file.name,
                        "line": b["line"] + 1 + offset,
                        "fence_line": b["line"], "rule": reason,
                        "excerpt": line.strip()[:160],
                        "verdict": "REVIEW_REQUIRED",
                    })
    return {"scope": "Redis-language Markdown fences only; no execution",
            "summary": {"chapters": chapters, "redis_fences": redis_blocks,
                        "syntax_review_candidates": len(findings),
                        "by_rule": dict(sorted(Counter(x["rule"] for x in findings).items()))},
            "findings": findings}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--json-file", type=Path)
    p.add_argument("--assert-chapters-clear", nargs="*", type=int, default=[])
    p.add_argument("--fail-on-any-finding", action="store_true", help="Require every chapter Redis interactive fence to avoid both scanned defects")
    args = p.parse_args()
    result = inspect(args.root)
    if args.json_file:
        args.json_file.parent.mkdir(parents=True, exist_ok=True)
        args.json_file.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("V02 REDIS INTERACTIVE SYNTAX:", json.dumps(result["summary"], sort_keys=True))
    for issue in result["findings"][:40]:
        print("V02 REDIS SYNTAX CANDIDATE:", json.dumps(issue, sort_keys=True))
    outstanding = [x for x in result["findings"] if args.fail_on_any_finding or x["chapter"] in args.assert_chapters_clear]
    if outstanding:
        print("FAIL: targeted chapters still contain bad interactive Redis syntax:",
              json.dumps(outstanding[:20]))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
