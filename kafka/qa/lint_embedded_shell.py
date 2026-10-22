#!/usr/bin/env python3
"""Automated, non-executing ShellCheck QA for Kafka Markdown shell fences.

Requires Docker and the koalaman/shellcheck:stable image.
Run from repo root: python kafka/qa/lint_embedded_shell.py
Only extracted text is sent to ShellCheck, never executed as shell commands.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from validate_code_blocks import extract

SHELL_LANGS = {"bash", "sh", "shell", "console"}
IMAGE = "koalaman/shellcheck:stable"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("kafka"))
    parser.add_argument("--output", type=Path, default=Path("kafka/qa/evidence/shellcheck-automated.json"))
    parser.add_argument("--limit", type=int, default=0, help="0 checks all blocks")
    parser.add_argument("--resume", action="store_true", help="Reuse previously recorded block results")
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        print(f"Missing root: {root}", file=sys.stderr)
        return 2
    output = args.output.resolve()
    previous = {}
    if args.resume and output.exists():
        try:
            for item in json.loads(output.read_text(encoding="utf-8-sig")).get("blocks", []):
                if "key" in item:
                    previous[item["key"]] = item
        except (ValueError, OSError) as exc:
            print(f"Cannot resume: {exc}", file=sys.stderr)
            return 2
    blocks = []
    for file in sorted(root.rglob("*.md")):
        relative = file.relative_to(root).as_posix()
        for start, end, language, body, unclosed in extract(file.read_text(encoding="utf-8-sig")):
            if language not in SHELL_LANGS:
                continue
            import hashlib
            digest = hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]
            key = f"{relative}:{start}:{digest}"
            if key in previous:
                blocks.append(previous[key])
                continue
            if args.limit and len(blocks) >= args.limit:
                break
            item = {"key": key, "path": relative, "start_line": start, "end_line": end,
                    "language": language, "diagnostics": []}
            if unclosed:
                item.update(status="FAIL", error="Unclosed code fence")
            elif not body.strip():
                item.update(status="SKIP", reason="Empty shell block")
            else:
                shell = "sh" if language == "sh" else "bash"
                command = ["docker", "run", "--rm", "-i", "--network", "none",
                           "--read-only", "--cap-drop", "ALL", "--security-opt",
                           "no-new-privileges", IMAGE, "-s", shell, "-f", "json", "-"]
                try:
                    # Bytes prevent Windows text-mode CRLF rewriting (SC1017).
                    process = subprocess.run(command, input=(body + "\n").encode("utf-8"),
                                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                             timeout=45, check=False)
                    data = json.loads(process.stdout.decode("utf-8-sig") or "[]")
                    if not isinstance(data, list):
                        raise ValueError("Unexpected ShellCheck JSON format")
                    item["diagnostics"] = [
                        {"rule": f"SC{d.get('code')}", "severity": d.get("level"),
                         "message": d.get("message"), "line": start + d.get("line", 1)}
                        for d in data
                    ]
                    if process.returncode not in (0, 1):
                        item.update(status="ERROR", error=process.stderr.decode("utf-8", "replace")[:1000])
                    else:
                        item["status"] = "REVIEW" if data else "PASS"
                except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
                    item.update(status="ERROR", error=str(exc))
            blocks.append(item)
            if len(blocks) % 25 == 0:
                print(f"Processed {len(blocks)} blocks...", flush=True)
                save(output, blocks, complete=False)
        if args.limit and len(blocks) >= args.limit:
            break
    save(output, blocks, complete=(args.limit == 0))
    counts = Counter(b["status"] for b in blocks)
    print(f"ShellCheck: {len(blocks)} blocks; {dict(counts)}")
    print(f"Evidence: {output}")
    return 2 if counts["ERROR"] else 1 if counts["FAIL"] else 0


def save(path: Path, blocks: list[dict], complete: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    report = {"generated_at_utc": datetime.now(timezone.utc).isoformat(),
              "complete_scan": complete,
              "summary": dict(Counter(b["status"] for b in blocks)),
              "scope": "ShellCheck static lint only; REVIEW is not a runtime failure; no labs executed.",
              "blocks": blocks}
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


if __name__ == "__main__":
    raise SystemExit(main())
