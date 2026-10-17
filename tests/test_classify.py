import unittest

from openloop.classify import CAN_WAIT, NEEDS_YOU_NOW, classify, triage
from openloop.model import OpenLoop


def loop(kind="reply_owed", urgency="normal", deadline=None, tid="t1"):
    return OpenLoop(thread_id=tid, thread_title=tid, kind=kind,
                    detail="d", deadline=deadline, urgency=urgency)


class ClassifyTests(unittest.TestCase):
    def test_high_urgency_needs_you_now(self):
        self.assertEqual(classify(loop(urgency="high")), NEEDS_YOU_NOW)

    def test_deadline_needs_you_now(self):
        self.assertEqual(classify(loop(deadline="by Friday")), NEEDS_YOU_NOW)

    def test_plain_loop_can_wait(self):
        self.assertEqual(classify(loop()), CAN_WAIT)

    def test_triage_sorts_needs_you_now_first(self):
        pairs = triage([loop(tid="a"), loop(urgency="high", tid="b")])
        self.assertEqual([p[0].thread_id for p in pairs], ["b", "a"])


if __name__ == "__main__":
    unittest.main()
