#!/usr/bin/env python3
"""Verify the served TLS leaf at the fixed disposable endpoint, without login."""
import argparse
import hashlib
import json
from pathlib import Path
import socket
import ssl
import struct
import sys


def certificate_fingerprint(path):
    return hashlib.sha256(ssl.PEM_cert_to_DER_cert(Path(path).read_text())).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cafile",required=True)
    parser.add_argument("--expect-cert",required=True,help="Single PEM leaf certificate")
    args=parser.parse_args()
    try:
        expected=certificate_fingerprint(args.expect_cert)
        context=ssl.create_default_context(cafile=args.cafile)
        context.minimum_version=ssl.TLSVersion.TLSv1_2
        with socket.create_connection(("127.0.0.1",55432),timeout=5) as raw:
            raw.sendall(struct.pack("!II",8,80877103))  # PostgreSQL SSLRequest
            if raw.recv(1) != b"S":
                raise ValueError("Endpoint did not accept PostgreSQL TLS negotiation")
            with context.wrap_socket(raw,server_hostname="postgresql-lab.invalid") as secured:
                actual=hashlib.sha256(secured.getpeercert(binary_form=True)).hexdigest()
                print(json.dumps({"endpoint":"127.0.0.1:55432",
                                  "hostname":"postgresql-lab.invalid",
                                  "tls":secured.version(),"cipher":secured.cipher(),
                                  "served_leaf_sha256":actual,
                                  "matches_expected":actual==expected}))
                return 0 if actual==expected else 1
    except (OSError,ValueError) as exc:
        print(f"TLS PROBE FAILED: {exc}",file=sys.stderr)
        return 2


if __name__=="__main__":
    sys.exit(main())
