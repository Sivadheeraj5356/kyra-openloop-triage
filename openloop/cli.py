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
    ap.add_argument("--as-of", default=None, metavar="ISO-TIMESTAMP",
                    help="anchor 'now' for staleness marking (e.g. "
                         "2026-10-17T16:00:00). Without it, no stale/overdue "
                         "claims are made.")
    args = ap.parse_args(argv)

    try:
        threads = load_threads(args.export)
    except ExportError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    as_of = None
    if args.as_of:
        from datetime import datetime
        try:
            as_of = datetime.fromisoformat(args.as_of)
        except ValueError:
            print(f"error: --as-of is not valid ISO-8601: {args.as_of!r}",
                  file=sys.stderr)
            return 2
    loops = extract_loops(threads, me=args.me, as_of=as_of)
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
                "stale": loop.stale,
                "why": loop.detail,
            }
            for loop, bucket in pairs
        ], indent=2))
    else:
        print(render_brief(pairs, me=args.me), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
