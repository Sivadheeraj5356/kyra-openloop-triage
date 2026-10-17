"""Deterministic open-loop extraction rules.

Three loop kinds, each grounded in an observable message pattern:

- reply_owed:            the ball is in my court - the newest inbound message
                         asks something or requests action and I have not
                         replied since.
- promise_made:          I committed to something ("I'll send the report by
                         Friday") and there is no later message from me that
                         looks like the delivery.
- scheduling_unresolved: the thread is a scheduling back-and-forth with no
                         confirmation yet.

Every rule is a plain string/regex heuristic. The point is transparency: each
returned OpenLoop carries the exact reason it was opened.
"""
from __future__ import annotations

import re
from typing import List, Optional

from .model import Message, OpenLoop, Thread

REQUEST_RE = re.compile(
    r"(\?|can you|could you|would you|please (send|share|review|confirm|advise)"
    r"|let me know|need (your|you to)|get back to me|what do you think"
    r"|any update|following up|gentle reminder|can u|pls|please find)",
    re.IGNORECASE,
)

PROMISE_RE = re.compile(
    r"(\bi'll\b|\bi will\b|\bi can get|\bwill send\b|\bwill share\b"
    r"|\bget back to you\b|\bcircle back\b|\bfollow up\b|\bi'?ll have\b"
    r"|\blet me send|\bi'?ll send|\bi'?ll check|\bi'?ll look)",
    re.IGNORECASE,
)

DEADLINE_RE = re.compile(
    r"\b(by|before|until|no later than)\s+"
    r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday"
    r"|eod|cob|eow|tomorrow|tonight|next week|end of (day|week)"
    r"|\d{1,2}(:\d{2})?\s*(am|pm)|\d{1,2}[/-]\d{1,2})"
    r"|\btomorrow\b|\btonight\b|\bnext week\b|\bend of (day|week)\b|\beod\b",
    re.IGNORECASE,
)

URGENT_RE = re.compile(
    r"\b(urgent|asap|immediately|right away|today|eod|blocking|blocked|critical"
    r"|time[- ]sensitive|as soon as)\b",
    re.IGNORECASE,
)

COMPLETION_RE = re.compile(
    r"\b(attached|here'?s the|here is the|sending over|sent it|as promised"
    r"|done\b|shared the doc|link below|ppt attached|pdf attached)\b",
    re.IGNORECASE,
)

SCHEDULE_RE = re.compile(
    r"\b(works for me|how about|does .{0,20} work|schedule|reschedule|meet|meeting"
    r"|call\b|sync\b|catch up|coffee|lunch|\d{1,2}(:\d{2})?\s?(am|pm)\b"
    r"|monday|tuesday|wednesday|thursday|friday)\b",
    re.IGNORECASE,
)

CONFIRM_RE = re.compile(
    r"\b(confirmed|locks? (it|that) in|locked in|booked|see you (then|there|on)"
    r"|calendar invite|invite sent|it'?s a (date|plan)|done,? see you)\b",
    re.IGNORECASE,
)

NOISE_SENDER_RE = re.compile(
    r"(no[-_]?reply|donotreply|newsletter|notifications?@|updates?@|digest"
    r"|marketing|promo|mailer|bounce)",
    re.IGNORECASE,
)

NOISE_BODY_RE = re.compile(
    r"\b(unsubscribe|view in browser|email preferences|manage your subscription"
    r"|you are receiving this (email|newsletter))\b",
    re.IGNORECASE,
)

RESOLUTION_ACK_RE = re.compile(
    r"\b(thanks,? that'?s all|got it,? thanks|perfect,? thanks|all set"
    r"|that answers it|makes sense,? thanks)\b",
    re.IGNORECASE,
)


def is_noise_thread(thread: Thread) -> bool:
    """Newsletters, automated notifications, and FYI blasts are not loops."""
    if not thread.messages:
        return False
    first = thread.messages[0]
    if NOISE_SENDER_RE.search(first.sender):
        return True
    joined = "\n".join(m.body for m in thread.messages[:3])
    return bool(NOISE_BODY_RE.search(joined))


def _deadline_in(text: str) -> Optional[str]:
    m = DEADLINE_RE.search(text)
    return m.group(0).strip() if m else None


def _urgency(text: str, deadline: Optional[str]) -> str:
    if URGENT_RE.search(text):
        return "high"
    if deadline and re.search(r"\b(today|tonight|eod|end of day)\b", deadline, re.IGNORECASE):
        return "high"
    return "normal"


def _extract_reply_owed(thread: Thread, me: str) -> Optional[OpenLoop]:
    others_last: Optional[Message] = None
    for msg in thread.messages:
        if msg.sender == me:
            # my reply closes whatever came before it
            others_last = None
        else:
            others_last = msg
    if others_last is None:
        return None
    if RESOLUTION_ACK_RE.search(others_last.body):
        return None
    if REQUEST_RE.search(others_last.body):
        deadline = _deadline_in(others_last.body)
        return OpenLoop(
            thread_id=thread.id,
            thread_title=thread.title,
            kind="reply_owed",
            detail=f"Last message from {others_last.sender} asks or requests "
                   f"something; no reply from you since.",
            deadline=deadline,
            urgency=_urgency(others_last.body, deadline),
        )
    return None


def _extract_promise_made(thread: Thread, me: str) -> Optional[OpenLoop]:
    my_msgs = [m for m in thread.messages if m.sender == me]
    for msg in reversed(my_msgs):
        if PROMISE_RE.search(msg.body):
            later_mine = [m for m in my_msgs if m.ts > msg.ts]
            if any(COMPLETION_RE.search(m.body) for m in later_mine):
                return None
            if COMPLETION_RE.search(msg.body) and not _deadline_in(msg.body):
                return None
            deadline = _deadline_in(msg.body)
            nudged = any(
                m.sender != me and m.ts > msg.ts
                and re.search(r"any update|following up|reminder|did you", m.body, re.IGNORECASE)
                for m in thread.messages
            )
            return OpenLoop(
                thread_id=thread.id,
                thread_title=thread.title,
                kind="promise_made",
                detail=(
                    f"You said \"{msg.body.strip()[:80]}\""
                    + ("; they have since nudged for an update." if nudged
                       else "; no later message from you looks like the delivery.")
                ),
                deadline=deadline,
                urgency=_urgency(msg.body + (" urgent" if nudged else ""), deadline),
            )
    return None


def _extract_scheduling(thread: Thread, me: str) -> Optional[OpenLoop]:
    if len(thread.messages) < 3:
        return None
    sched_hits = sum(1 for m in thread.messages if SCHEDULE_RE.search(m.body))
    if sched_hits < 2:
        return None
    if any(CONFIRM_RE.search(m.body) for m in thread.messages):
        return None
    last = thread.messages[-1]
    waiting_on = "you" if last.sender != me else last.sender
    return OpenLoop(
        thread_id=thread.id,
        thread_title=thread.title,
        kind="scheduling_unresolved",
        detail=f"{sched_hits} scheduling messages, no confirmation; "
               f"latest message is from {last.sender}.",
        urgency=_urgency(last.body, _deadline_in(last.body)),
    )


def extract_loops(threads: List[Thread], me: str) -> List[OpenLoop]:
    loops: List[OpenLoop] = []
    for thread in threads:
        if not thread.messages or is_noise_thread(thread):
            continue
        promise = _extract_promise_made(thread, me)
        if promise is not None:
            loops.append(promise)
        sched = _extract_scheduling(thread, me)
        if sched is not None:
            loops.append(sched)
        else:
            reply = _extract_reply_owed(thread, me)
            if reply is not None and not _is_promise_nudge(thread, me, promise):
                loops.append(reply)
    return loops


NUDGE_RE = re.compile(
    r"\b(any update|following up|gentle reminder|did you|still waiting"
    r"|checking in|bump)\b",
    re.IGNORECASE,
)


def _is_promise_nudge(thread: Thread, me: str, promise: Optional[OpenLoop]) -> bool:
    """An inbound nudge about an open promise is the same loop, not a second one."""
    if promise is None or not thread.messages:
        return False
    last = thread.messages[-1]
    return last.sender != me and bool(NUDGE_RE.search(last.body))
