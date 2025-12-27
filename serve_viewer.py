#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import os
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve NIHO/gov viewer + JSON files over HTTP.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    args = parser.parse_args()

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    os.chdir(repo_root)

    httpd = ThreadingHTTPServer((args.host, args.port), SimpleHTTPRequestHandler)
    print(f"Serving: {repo_root}")
    print(f"Viewer:  http://{args.host}:{args.port}/NIHO/gov/viewer/index.html")
    print(f"Data:    http://{args.host}:{args.port}/NIHO/gov/kamakura-fin.json")
    print("Stop with Ctrl+C")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
