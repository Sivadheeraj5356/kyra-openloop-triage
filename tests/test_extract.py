import unittest

from openloop.extract import extract_loops
from openloop.parser import parse_threads


def make(threads):
    return parse_threads({"threads": threads})


def msg(mid, ts, sender, body):
    return {"id": mid, "ts": ts, "sender": sender, "body": body}


class ExtractTests(unittest.TestCase):
    def test_unanswered_request_is_reply_owed(self):
        threads = make([{"id": "t1", "title": "ask", "messages": [
            msg("m1", "2026-10-14T09:00:00", "priya", "Can you send the deck?"),
        ]}])
        loops = extract_loops(threads, me="me")
        self.assertEqual(len(loops), 1)
        self.assertEqual(loops[0].kind, "reply_owed")

    def test_my_reply_closes_the_loop(self):
        threads = make([{"id": "t1", "title": "ask", "messages": [
            msg("m1", "2026-10-14T09:00:00", "priya", "Can you send the deck?"),
            msg("m2", "2026-10-14T10:00:00", "me", "Sent it just now."),
        ]}])
        self.assertEqual(extract_loops(threads, me="me"), [])

    def test_open_promise_is_flagged_with_deadline(self):
        threads = make([{"id": "t1", "title": "contract", "messages": [
            msg("m1", "2026-10-14T09:00:00", "me",
                "I'll send the redlined contract by Friday."),
        ]}])
        loops = extract_loops(threads, me="me")
        self.assertEqual(len(loops), 1)
        self.assertEqual(loops[0].kind, "promise_made")
        self.assertEqual(loops[0].deadline.lower(), "by friday")

    def test_completed_promise_is_not_flagged(self):
        threads = make([{"id": "t1", "title": "contract", "messages": [
            msg("m1", "2026-10-14T09:00:00", "me", "I'll send the contract by Friday."),
            msg("m2", "2026-10-15T09:00:00", "me", "Attached is the contract, as promised."),
        ]}])
        self.assertEqual(extract_loops(threads, me="me"), [])

    def test_nudge_about_promise_is_one_loop_not_two(self):
        threads = make([{"id": "t1", "title": "contract", "messages": [
            msg("m1", "2026-10-14T09:00:00", "me", "I'll send the contract by Friday."),
            msg("m2", "2026-10-15T09:00:00", "arjun", "Any update on the contract?"),
        ]}])
        loops = extract_loops(threads, me="me")
        self.assertEqual([l.kind for l in loops], ["promise_made"])

    def test_scheduling_without_confirmation_is_open(self):
        threads = make([{"id": "t1", "title": "coffee", "messages": [
            msg("m1", "2026-10-12T11:00:00", "ravi", "Coffee Tuesday? 3pm works for me."),
            msg("m2", "2026-10-12T11:20:00", "me", "How about 4pm instead?"),
            msg("m3", "2026-10-12T11:35:00", "ravi", "Could do 4:30, does that work?"),
        ]}])
        loops = extract_loops(threads, me="me")
        self.assertEqual([l.kind for l in loops], ["scheduling_unresolved"])

    def test_confirmed_scheduling_is_closed(self):
        threads = make([{"id": "t1", "title": "dinner", "messages": [
            msg("m1", "2026-10-14T19:00:00", "ravi", "Dinner Friday? 8pm."),
            msg("m2", "2026-10-14T19:05:00", "me", "How about 8:30?"),
            msg("m3", "2026-10-14T19:07:00", "ravi", "Confirmed, see you then!"),
        ]}])
        self.assertEqual(extract_loops(threads, me="me"), [])

    def test_newsletter_sender_is_noise(self):
        threads = make([{"id": "t1", "title": "news", "messages": [
            msg("m1", "2026-10-14T08:00:00", "newsletter@digest.example",
                "Five frameworks you need. Unsubscribe anytime."),
        ]}])
        self.assertEqual(extract_loops(threads, me="me"), [])

    def test_unsubscribe_body_is_noise(self):
        threads = make([{"id": "t1", "title": "promo", "messages": [
            msg("m1", "2026-10-14T08:00:00", "deals@shop.example",
                "Big sale! View in browser. Unsubscribe here."),
        ]}])
        self.assertEqual(extract_loops(threads, me="me"), [])

    def test_empty_export_yields_no_loops(self):
        self.assertEqual(extract_loops(make([]), me="me"), [])

    def test_thread_with_no_messages_is_skipped(self):
        threads = make([{"id": "t1", "title": "empty", "messages": []}])
        self.assertEqual(extract_loops(threads, me="me"), [])

    def test_urgent_request_is_high_urgency(self):
        threads = make([{"id": "t1", "title": "fire", "messages": [
            msg("m1", "2026-10-15T07:55:00", "devon",
                "URGENT: can you check the autoscaler today? Blocking the deploy."),
        ]}])
        loops = extract_loops(threads, me="me")
        self.assertEqual(loops[0].urgency, "high")


if __name__ == "__main__":
    unittest.main()


class AdversarialTests(unittest.TestCase):
    def test_quoted_promise_in_my_message_is_not_mine(self):
        # I quote THEIR words; the promise must not be attributed to me.
        threads = make([{"id": "t1", "title": "catering", "messages": [
            msg("m1", "2026-10-14T09:00:00", "me",
                'You said "I\'ll handle the catering" - glad we agree.'),
        ]}])
        self.assertEqual(extract_loops(threads, me="me"), [])

    def test_quoted_promise_in_their_message_creates_no_promise_loop(self):
        threads = make([{"id": "t1", "title": "files", "messages": [
            msg("m1", "2026-10-14T09:00:00", "priya",
                'Per your "I will send the files" note, please send them.'),
        ]}])
        loops = extract_loops(threads, me="me")
        self.assertEqual([l.kind for l in loops], ["reply_owed"])

    def test_negated_promise_is_not_a_commitment(self):
        threads = make([{"id": "t1", "title": "report", "messages": [
            msg("m1", "2026-10-14T09:00:00", "me",
                "I don't think I'll have the report by Friday."),
        ]}])
        self.assertEqual(extract_loops(threads, me="me"), [])

    def test_negated_promise_variant(self):
        threads = make([{"id": "t1", "title": "numbers", "messages": [
            msg("m1", "2026-10-14T09:00:00", "me",
                "I'm not sure I can get you the numbers by Friday, sorry."),
        ]}])
        self.assertEqual(extract_loops(threads, me="me"), [])

    def test_same_message_completion_closes_promise(self):
        threads = make([{"id": "t1", "title": "draft", "messages": [
            msg("m1", "2026-10-14T09:00:00", "me",
                "I'll send the full report by Friday; attached is the draft."),
        ]}])
        self.assertEqual(extract_loops(threads, me="me"), [])

    def test_no_reply_needed_suppresses_loop(self):
        threads = make([{"id": "t1", "title": "fyi", "messages": [
            msg("m1", "2026-10-14T09:00:00", "lina",
                "Can you glance at the deck sometime? No need to reply, just FYI."),
        ]}])
        self.assertEqual(extract_loops(threads, me="me"), [])

    def test_self_resolved_request_is_closed(self):
        threads = make([{"id": "t1", "title": "deck", "messages": [
            msg("m1", "2026-10-14T09:00:00", "priya", "Can you send the deck?"),
            msg("m2", "2026-10-14T09:20:00", "priya", "Never mind, found it."),
        ]}])
        self.assertEqual(extract_loops(threads, me="me"), [])

    def test_stale_only_with_as_of_anchor(self):
        threads = make([{"id": "t1", "title": "old ask", "messages": [
            msg("m1", "2026-09-01T09:00:00", "priya",
                "Can you review the plan before Monday?"),
        ]}])
        from datetime import datetime
        anchored = extract_loops(threads, me="me",
                                 as_of=datetime(2026, 10, 17, 16, 0, 0))
        self.assertEqual(len(anchored), 1)
        self.assertTrue(anchored[0].stale)
        self.assertIsNone(anchored[0].deadline)
        from openloop.classify import classify, CAN_WAIT
        self.assertEqual(classify(anchored[0]), CAN_WAIT)
        # without an anchor, no staleness is claimed
        unanchored = extract_loops(threads, me="me")
        self.assertFalse(unanchored[0].stale)
        self.assertIsNotNone(unanchored[0].deadline)

    def test_fresh_loop_not_marked_stale(self):
        threads = make([{"id": "t1", "title": "new ask", "messages": [
            msg("m1", "2026-10-16T09:00:00", "priya", "Can you send the deck?"),
        ]}])
        from datetime import datetime
        loops = extract_loops(threads, me="me",
                              as_of=datetime(2026, 10, 17, 16, 0, 0))
        self.assertFalse(loops[0].stale)

    def test_completion_in_another_thread_is_a_known_miss(self):
        # DOCUMENTED LIMIT: delivery in a different thread does not close the
        # promise; threads are analyzed independently.
        threads = make([
            {"id": "t1", "title": "contract", "messages": [
                msg("m1", "2026-10-14T09:00:00", "me",
                    "I'll send the contract by Friday."),
            ]},
            {"id": "t2", "title": "unrelated", "messages": [
                msg("m2", "2026-10-15T09:00:00", "me",
                    "Attached is the contract, as promised."),
            ]},
        ])
        loops = extract_loops(threads, me="me")
        self.assertEqual([l.kind for l in loops], ["promise_made"])
