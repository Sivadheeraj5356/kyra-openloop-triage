"""Data model for thread exports and extracted open loops."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


class ExportError(ValueError):
    """Raised when a thread export file is malformed."""


@dataclass
class Message:
    id: str
    ts: str
    sender: str
    body: str


@dataclass
class Thread:
    id: str
    title: str
    messages: List[Message] = field(default_factory=list)


@dataclass
class OpenLoop:
    thread_id: str
    thread_title: str
    kind: str            # reply_owed | promise_made | scheduling_unresolved
    detail: str          # human-readable reason this loop is open
    deadline: Optional[str] = None   # extracted deadline phrase, if any
    urgency: str = "normal"          # high | normal
    triggered_ts: str = ""           # ts of the message that opened the loop
    stale: bool = False              # set only when an --as-of anchor was given
