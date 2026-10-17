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
