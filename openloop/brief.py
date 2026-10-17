"""Render the decisions brief: one line per open loop, plus a summary header."""
from __future__ import annotations

from typing import List, Tuple

from .classify import ACTION_STUBS, CAN_WAIT, NEEDS_YOU_NOW
from .model import OpenLoop


def render_brief(pairs: List[Tuple[OpenLoop, str]], me: str) -> str:
    now = [p for p in pairs if p[1] == NEEDS_YOU_NOW]
    later = [p for p in pairs if p[1] == CAN_WAIT]
    lines = [
        f"DECISIONS BRIEF for {me}",
        f"{len(now)} need(s) you now, {len(later)} can wait.",
        "",
    ]
    def emit(bucket: str, items) -> None:
        if not items:
            return
        lines.append(f"== {bucket.replace('_', ' ').upper()} ==")
        for loop, _ in items:
            flag = " [deadline: %s]" % loop.deadline if loop.deadline else ""
            lines.append(f"- [{loop.kind}] {loop.thread_title}{flag}")
            lines.append(f"    why: {loop.detail}")
            lines.append(f"    next: {ACTION_STUBS.get(loop.kind, 'review')}")
        lines.append("")
    emit(NEEDS_YOU_NOW, now)
    emit(CAN_WAIT, later)
    if not pairs:
        lines.append("No open loops found. Inbox zero, at least by these rules.")
    return "\n".join(lines).rstrip() + "\n"
