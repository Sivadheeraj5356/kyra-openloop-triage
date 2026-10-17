"""Command-line entry point.

Usage:
    python3 -m openloop <export.json> --me <your-handle>

Exit codes: 0 = brief rendered, 2 = export malformed/unreadable.
"""
from __future__ import annotations

import argparse
import sys

from .brief import render_brief
from .classify import triage
from .extract import extract_loops
from .model import ExportError
from .parser import load_threads


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="openloop",
        description="Offline open-loop triage for message-thread exports.",
    )
    ap.add_argument("export", help="path to a thread export JSON file")
    ap.add_argument("--me", required=True,
                    help="your sender handle as it appears in the export")
    ap.add_argument("--json", action="store_true",
                    help="emit machine-readable JSON instead of the text brief")
    args = ap.parse_args(argv)

    try:
        threads = load_threads(args.export)
    except ExportError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    loops = extract_loops(threads, me=args.me)
    pairs = triage(loops)

    if args.json:
        import json
        print(json.dumps([
            {
                "thread_id": loop.thread_id,
                "thread_title": loop.thread_title,
                "kind": loop.kind,
                "bucket": bucket,
                "deadline": loop.deadline,
                "why": loop.detail,
            }
            for loop, bucket in pairs
        ], indent=2))
    else:
        print(render_brief(pairs, me=args.me), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
