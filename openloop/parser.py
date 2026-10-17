"""Load and validate a message-thread export.

Expected JSON shape (see fixtures/sample_threads.json):

    {
      "threads": [
        {
          "id": "t1",
          "title": "Q3 budget sign-off",
          "messages": [
            {"id": "m1", "ts": "2026-10-14T09:12:00", "sender": "priya", "body": "..."}
          ]
        }
      ]
    }

`ts` is an ISO-8601 local timestamp. Messages are sorted by `ts` on load, so
exports do not need to be pre-ordered.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import List

from .model import ExportError, Message, Thread


def _parse_ts(raw, ctx: str) -> str:
    if not isinstance(raw, str):
        raise ExportError(f"{ctx}: 'ts' must be an ISO-8601 string")
    try:
        datetime.fromisoformat(raw)
    except ValueError:
        raise ExportError(f"{ctx}: 'ts' is not valid ISO-8601: {raw!r}")
    return raw


def load_threads(path: str) -> List[Thread]:
    """Read a thread export from disk and return validated Thread objects."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        raise ExportError(f"export file not found: {path}")
    except json.JSONDecodeError as exc:
        raise ExportError(f"export file is not valid JSON: {exc}")
    return parse_threads(data)


def parse_threads(data) -> List[Thread]:
    if not isinstance(data, dict) or "threads" not in data:
        raise ExportError("export must be a JSON object with a 'threads' array")
    raw_threads = data["threads"]
    if not isinstance(raw_threads, list):
        raise ExportError("'threads' must be an array")

    threads: List[Thread] = []
    for i, rt in enumerate(raw_threads):
        ctx = f"threads[{i}]"
        if not isinstance(rt, dict):
            raise ExportError(f"{ctx}: each thread must be an object")
        tid = rt.get("id")
        if not isinstance(tid, str) or not tid:
            raise ExportError(f"{ctx}: 'id' must be a non-empty string")
        title = rt.get("title", tid)
        if not isinstance(title, str):
            raise ExportError(f"{ctx}: 'title' must be a string")
        raw_msgs = rt.get("messages", [])
        if not isinstance(raw_msgs, list):
            raise ExportError(f"{ctx}: 'messages' must be an array")

        msgs: List[Message] = []
        for j, rm in enumerate(raw_msgs):
            mctx = f"{ctx}.messages[{j}]"
            if not isinstance(rm, dict):
                raise ExportError(f"{mctx}: each message must be an object")
            for key in ("id", "sender", "body"):
                if not isinstance(rm.get(key), str):
                    raise ExportError(f"{mctx}: '{key}' must be a string")
            msgs.append(Message(
                id=rm["id"],
                ts=_parse_ts(rm.get("ts"), mctx),
                sender=rm["sender"],
                body=rm["body"],
            ))
        msgs.sort(key=lambda m: m.ts)
        threads.append(Thread(id=tid, title=title, messages=msgs))
    return threads
