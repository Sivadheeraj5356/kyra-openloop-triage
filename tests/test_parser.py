import json
import os
import tempfile
import unittest

from openloop.model import ExportError
from openloop.parser import load_threads, parse_threads


def _export(threads):
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w") as fh:
        json.dump({"threads": threads}, fh)
    return path


class ParserTests(unittest.TestCase):
    def test_valid_export_loads(self):
        path = _export([{
            "id": "t1", "title": "hi",
            "messages": [{"id": "m1", "ts": "2026-10-14T09:00:00",
                          "sender": "a", "body": "hello"}],
        }])
        try:
            threads = load_threads(path)
        finally:
            os.unlink(path)
        self.assertEqual(len(threads), 1)
        self.assertEqual(threads[0].messages[0].body, "hello")

    def test_messages_sorted_by_timestamp(self):
        path = _export([{
            "id": "t1", "title": "order",
            "messages": [
                {"id": "m2", "ts": "2026-10-14T10:00:00", "sender": "a", "body": "second"},
                {"id": "m1", "ts": "2026-10-14T09:00:00", "sender": "a", "body": "first"},
            ],
        }])
        try:
            threads = load_threads(path)
        finally:
            os.unlink(path)
        self.assertEqual([m.id for m in threads[0].messages], ["m1", "m2"])

    def test_missing_file_raises(self):
        with self.assertRaises(ExportError):
            load_threads("/nonexistent/export.json")

    def test_invalid_json_raises(self):
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as fh:
            fh.write("{not json")
        try:
            with self.assertRaises(ExportError):
                load_threads(path)
        finally:
            os.unlink(path)

    def test_missing_threads_key_raises(self):
        with self.assertRaises(ExportError):
            parse_threads({"messages": []})

    def test_bad_timestamp_raises(self):
        with self.assertRaises(ExportError):
            parse_threads({"threads": [{
                "id": "t1",
                "messages": [{"id": "m1", "ts": "yesterday-ish",
                              "sender": "a", "body": "hi"}],
            }]})

    def test_non_string_sender_raises(self):
        with self.assertRaises(ExportError):
            parse_threads({"threads": [{
                "id": "t1",
                "messages": [{"id": "m1", "ts": "2026-10-14T09:00:00",
                              "sender": 42, "body": "hi"}],
            }]})

    def test_empty_threads_is_fine(self):
        self.assertEqual(parse_threads({"threads": []}), [])


if __name__ == "__main__":
    unittest.main()
