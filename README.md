# Open Loop Triage

An offline, deterministic CLI that reads a local export of message threads,
finds the **open loops** (replies you owe, follow-ups you promised, scheduling
threads that never closed), and renders a short **decisions brief**: what needs
you now, what can wait, and why - with a suggested next action for each.

Built as a working sample inspired by the product direction published on
[kyrainterface.com](https://kyrainterface.com/) and its manifesto: connect your
apps, surface replies you owe and follow-ups you promised, drop the noise, and
bring you the decisions that need a human - with local processing first. This
tool is that loop, end to end, in miniature: local-only, explainable, and with
a human-approval stub on every item.

## What it does

| Loop kind | Pattern detected | Suggested action |
|---|---|---|
| `reply_owed` | Newest inbound message asks/requests something; no reply from you since | draft reply for approve/edit/ignore |
| `promise_made` | You said "I'll send X by Friday" and nothing later looks like the delivery | surface the commitment, draft the delivery note |
| `scheduling_unresolved` | Multi-message scheduling back-and-forth with no confirmation | propose a concrete time |

Newsletters, notifications, and promo mail are filtered out as noise. A nudge
("any update?") about an open promise is merged into that promise instead of
double-counting. Every brief line carries the exact reason the loop was
opened - no black box.

## Honest limits

- **Heuristics, not an LLM.** Rules are regex/string patterns over message
  text. They are transparent and testable, and they will misjudge messages
  whose meaning depends on context the patterns don't capture.
- **Synthetic fixtures only.** `fixtures/sample_threads.json` is invented
  sample data. No real mailbox, no private messages, no third-party code.
- **No integrations.** No email/calendar APIs, no cloud calls, no API keys.
  Input is a JSON export; output is text or JSON.
- **No claim about Kyra's internals.** This is original code written against
  their public product description, not a reconstruction of their system.

## Usage

```bash
python3 -m openloop fixtures/sample_threads.json --me me
python3 -m openloop fixtures/sample_threads.json --me me --json
```

Exit codes: `0` = brief rendered, `2` = export malformed or unreadable.

Input format (`--me` is your sender handle as it appears in the export):

```json
{
  "threads": [
    {
      "id": "t1",
      "title": "Q3 budget sign-off",
      "messages": [
        {"id": "m1", "ts": "2026-10-14T09:12:00", "sender": "priya",
         "body": "Can you review the Q3 numbers before Thursday?"}
      ]
    }
  ]
}
```

## Example output

```
DECISIONS BRIEF for me
4 need(s) you now, 1 can wait.

== NEEDS YOU NOW ==
- [reply_owed] Q3 budget sign-off [deadline: before Thursday]
    why: Last message from priya asks or requests something; no reply from you since.
    next: draft reply for your approve/edit/ignore
- [promise_made] Vendor contract draft [deadline: by Friday]
    why: You said "I'll send the redlined contract by Friday."; they have since nudged for an update.
    next: surface the commitment; draft the delivery note
...
```

## Tests

Python 3.9+, standard library only. Tests use `unittest` style, so they run
under either runner:

```bash
python3 -m unittest discover -s tests        # 28 tests
python3 -m pytest tests                      # if pytest is installed
```

Tests cover parsing validation (including malformed-input failure cases),
each extraction rule and its negative case, classification and ordering, and
CLI exit codes.

## Layout

```
openloop/
  model.py      data types + ExportError
  parser.py     load/validate thread exports
  extract.py    the open-loop rules (all heuristics live here)
  classify.py   needs_you_now / can_wait + ordering
  brief.py      text brief rendering
  cli.py        argument handling, exit codes
fixtures/       synthetic sample export
tests/          28 unittest-style tests
```
