import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from openloop.cli import main

FIXTURE = os.path.join(os.path.dirname(__file__), "..", "fixtures",
                       "sample_threads.json")


class CliTests(unittest.TestCase):
    def test_text_brief_exit_zero(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = main([FIXTURE, "--me", "me"])
        self.assertEqual(code, 0)
        text = out.getvalue()
        self.assertIn("DECISIONS BRIEF", text)
        self.assertIn("Q3 budget sign-off", text)
        self.assertIn("Vendor contract draft", text)

    def test_json_output_is_parseable(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = main([FIXTURE, "--me", "me", "--json"])
        self.assertEqual(code, 0)
        rows = json.loads(out.getvalue())
        self.assertTrue(all("bucket" in r and "kind" in r for r in rows))
        kinds = {(r["thread_id"], r["kind"]) for r in rows}
        self.assertIn(("t1", "reply_owed"), kinds)
        self.assertIn(("t2", "promise_made"), kinds)
        self.assertNotIn(("t4", "reply_owed"), kinds)  # newsletter

    def test_malformed_export_exit_two(self):
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as fh:
            fh.write("[1, 2, 3]")
        err = io.StringIO()
        try:
            with redirect_stderr(err):
                code = main([path, "--me", "me"])
        finally:
            os.unlink(path)
        self.assertEqual(code, 2)
        self.assertIn("error:", err.getvalue())

    def test_missing_file_exit_two(self):
        with redirect_stderr(io.StringIO()):
            code = main(["/nonexistent/x.json", "--me", "me"])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
