"""Triage classification: needs_you_now / can_wait.

Noise is removed during extraction (is_noise_thread), so classification here
only ranks the surviving open loops. Every decision is explained by the
loop's own fields - urgency plus deadline presence.
"""
from __future__ import annotations

from typing import List, Tuple

from .model import OpenLoop

NEEDS_YOU_NOW = "needs_you_now"
CAN_WAIT = "can_wait"

_BUCKET_ORDER = {NEEDS_YOU_NOW: 0, CAN_WAIT: 1}
_KIND_ORDER = {"reply_owed": 0, "promise_made": 1, "scheduling_unresolved": 2}

ACTION_STUBS = {
    "reply_owed": "draft reply for your approve/edit/ignore",
    "promise_made": "surface the commitment; draft the delivery note",
    "scheduling_unresolved": "propose a concrete time to close the thread",
}


def classify(loop: OpenLoop) -> str:
    if loop.urgency == "high":
        return NEEDS_YOU_NOW
    if loop.deadline is not None:
        return NEEDS_YOU_NOW
    return CAN_WAIT


def triage(loops: List[OpenLoop]) -> List[Tuple[OpenLoop, str]]:
    """Return (loop, bucket) pairs sorted: needs_you_now first, then by kind."""
    pairs = [(loop, classify(loop)) for loop in loops]
    pairs.sort(key=lambda p: (_BUCKET_ORDER[p[1]], _KIND_ORDER.get(p[0].kind, 9),
                              p[0].thread_id))
    return pairs
