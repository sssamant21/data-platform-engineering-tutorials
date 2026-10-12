#!/usr/bin/env python3
"""Loopback-only disposable Alertmanager capture. Ctrl+C stops it."""
import argparse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import re

ALLOWED = ("alertname", "severity", "owner", "environment", "cluster", "job", "instance")


def summarize(payload):
    if not isinstance(payload, dict) or payload.get("status") not in ("firing", "resolved"):
        raise ValueError("invalid webhook status")
    alerts = payload.get("alerts")
    if not isinstance(alerts, list) or len(alerts) > 20:
        raise ValueError("bounded alert list required")
    result = []
    for alert in alerts:
        if not isinstance(alert, dict) or alert.get("status") not in ("firing", "resolved"):
            raise ValueError("invalid alert")
        labels = alert.get("labels")
        if not isinstance(labels, dict):
            raise ValueError("labels required")
        selected = {}
        for key in ALLOWED:
            value = labels.get(key)
            if value is not None:
                if not isinstance(value, str) or len(value) > 128:
                    raise ValueError("invalid label")
                selected[key] = value
        if selected.get("environment") != "lab" or selected.get("cluster") != "chapter004":
            raise ValueError("outside disposable lab")
        result.append({"status": alert["status"], "labels": selected})
    return {"received_at": datetime.now(timezone.utc).isoformat(),
            "status": payload["status"], "alerts": result}


def guard(output):
    raw = os.environ.get("PG_LAB_ROOT", "")
    if os.getuid() == 0 or not re.fullmatch(r"/tmp/postgresql-dbre-lab\.[A-Za-z0-9]+", raw):
        raise ValueError("non-root Chapter 004 owner and PG_LAB_ROOT required")
    root = Path(raw)
    if root.is_symlink() or not root.is_dir() or root.stat().st_uid != os.getuid():
        raise ValueError("real owned lab root required")
    marker = root / "LAB_MARKER"
    if marker.is_symlink() or marker.read_text().strip() != "postgresql18-dbre-sre-disposable":
        raise ValueError("invalid lab marker")
    if not re.fullmatch(r"[A-Za-z0-9_-]+\.jsonl", output):
        raise ValueError("simple output basename required")
    directory = root / "c025-evidence"
    directory.mkdir(mode=0o700, exist_ok=True)
    if directory.is_symlink() or directory.stat().st_uid != os.getuid() or (directory.stat().st_mode & 0o777) != 0o700:
        raise ValueError("private owned evidence directory required")
    return directory / output


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", default="notifications.jsonl")
    args = cli.parse_args()
    os.umask(0o077)
    try:
        path = guard(args.output)
        with path.open("x", encoding="utf-8") as output:
            class Handler(BaseHTTPRequestHandler):
                def do_POST(self):
                    self.connection.settimeout(2)
                    try:
                        if self.path != "/events":
                            self.send_error(404)
                            return
                        size = int(self.headers.get("Content-Length", "0"))
                        if not 0 < size <= 262144:
                            self.send_error(413)
                            return
                        record = summarize(json.loads(self.rfile.read(size)))
                        output.write(json.dumps(record) + "\n")
                        output.flush()
                        self.send_response(200)
                        self.end_headers()
                    except (ValueError, TypeError, OSError):
                        self.send_error(400)
                def log_message(self, *args):
                    pass
            with HTTPServer(("127.0.0.1", 19093), Handler) as server:
                server.timeout = 1
                print(f"Local capture: {path}; Ctrl+C to stop", flush=True)
                try:
                    server.serve_forever()
                except KeyboardInterrupt:
                    pass
    except (ValueError, OSError) as exc:
        cli.exit(2, f"Capture refused/failed: {exc}\n")


if __name__ == "__main__":
    main()
