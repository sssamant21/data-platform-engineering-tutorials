#!/usr/bin/env python3
"""Read-only PostgreSQL documentation fragment verifier (stdlib only).

Usage: python validation/check_pg18_fragments.py
       python validation/check_pg18_fragments.py --output validation/pg18-fragment-results.json

Run from any directory with outbound HTTPS access. Never treats page text as
proof that an HTML fragment exists. No database, Docker or cloud access.
"""
import argparse
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urldefrag, urlparse
from urllib.request import Request, urlopen

TARGETS = [
    "https://www.postgresql.org/docs/18/runtime-config-wal.html#RUNTIME-CONFIG-WAL-RECOVERY-TARGET",
    "https://www.postgresql.org/docs/18/sql-createtable.html#SQL-CREATETABLE-STORAGE-PARAMETERS",
    "https://www.postgresql.org/docs/18/functions-admin.html#FUNCTIONS-ADMIN-DBSIZE",
]

class IDs(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = set()
    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key == "id" and value is not None:
                self.ids.add(value)
            if tag == "a" and key == "name" and value is not None:
                self.ids.add(value)

def inspect(url):
    page, fragment = urldefrag(url)
    result = {"url": url, "fragment": fragment, "status": "unverified"}
    try:
        request = Request(page, headers={"User-Agent": "PostgreSQL-DBRE-doc-link-audit/1.0"})
        with urlopen(request, timeout=15) as response:
            final_url = response.geturl()
            result["http_status"] = response.status
            result["final_url"] = final_url
            if urlparse(final_url).hostname != "www.postgresql.org" or not urlparse(final_url).path.startswith("/docs/18/"):
                result["status"] = "unexpected_redirect"
                return result
            if response.status != 200:
                result["status"] = "http_error"
                return result
            if "html" not in response.headers.get("Content-Type", "").lower():
                result["status"] = "unexpected_content_type"
                return result
            html = response.read(5_000_001)
            if len(html) > 5_000_000:
                result["status"] = "oversize_response"
                return result
            parser = IDs()
            parser.feed(html.decode("utf-8", errors="replace"))
            result["status"] = "anchor_present" if fragment in parser.ids else "anchor_missing"
            result["matching_ids"] = sorted(i for i in parser.ids if fragment.lower() in i.lower())[:20]
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        result["error"] = type(exc).__name__ + ": " + str(exc)[:200]
    return result

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, help="Optional JSON evidence output path; do not commit unreviewed network output")
    args = ap.parse_args()
    record = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "documentation_baseline": "PostgreSQL 18",
        "method": "HTTP GET + HTML id/name attribute inspection; no runtime SQL",
        "results": [inspect(url) for url in TARGETS],
    }
    rendered = json.dumps(record, indent=2, sort_keys=True) + "\n"
    print(rendered, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    return 0 if all(x["status"] == "anchor_present" for x in record["results"]) else 1

if __name__ == "__main__":
    sys.exit(main())
