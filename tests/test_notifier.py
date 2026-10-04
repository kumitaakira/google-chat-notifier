import io
import json
import unittest
import urllib.error
from contextlib import redirect_stderr
from unittest.mock import patch

from google_chat_notifier import GoogleChatNotifier, Notifier, TextMessage


class RecordingNotifier(Notifier):
    def __init__(self):
        self.messages = []
        self.fail_send = False

    def send(self, message):
        if self.fail_send:
            raise OSError("offline")
        self.messages.append(message)
        return 200


class MonitorTests(unittest.TestCase):
    def test_success_preserves_result_and_metadata(self):
        notifier = RecordingNotifier()

        @notifier.monitor(task_name="my task")
        def work(value):
            """Original docstring."""
            return value * 2

        self.assertEqual(work(3), 6)
        self.assertEqual(work.__name__, "work")
        self.assertEqual(work.__doc__, "Original docstring.")
        self.assertIn("Task Completed: my task", notifier.messages[0].text)

    def test_error_preserves_original_exception(self):
        notifier = RecordingNotifier()
        original = ValueError("bad input")

        @notifier.monitor
        def work():
            raise original

        with self.assertRaises(ValueError) as raised:
            work()
        self.assertIs(raised.exception, original)
        self.assertIn("Task Failed: work", notifier.messages[0].text)

    def test_disable_and_custom_builders(self):
        notifier = RecordingNotifier()

        @notifier.monitor(on_success=None, on_error=lambda name, seconds, error: TextMessage(name))
        def work(value):
            if value < 0:
                raise ValueError()
            return value

        self.assertEqual(work(1), 1)
        self.assertEqual(notifier.messages, [])
        with self.assertRaises(ValueError):
            work(-1)
        self.assertEqual(notifier.messages[0].text, "work")

    def test_notification_failures_do_not_change_function_outcome(self):
        notifier = RecordingNotifier()
        notifier.fail_send = True

        @notifier.monitor()
        def work():
            return "ok"

        with redirect_stderr(io.StringIO()) as warning:
            self.assertEqual(work(), "ok")
        self.assertIn("Failed to send notification", warning.getvalue())

        @notifier.monitor(on_success=lambda *_: 1 / 0)
        def another():
            return 7

        with redirect_stderr(io.StringIO()) as warning:
            self.assertEqual(another(), 7)
        self.assertIn("on_success builder failed", warning.getvalue())


class GoogleChatTests(unittest.TestCase):
    def test_default_cards_include_result_and_error(self):
        notifier = GoogleChatNotifier("https://example.invalid/webhook")
        success = notifier.default_success_builder("job", 1.25, 0).build_payload()
        failure = notifier.default_error_builder("job", 1.25, ValueError("bad")).build_payload()
        self.assertIn("Task Completed: job", json.dumps(success))
        self.assertIn("Result", json.dumps(success))
        self.assertIn("Task Failed: job", json.dumps(failure))
        self.assertIn("bad", json.dumps(failure))

    @patch("google_chat_notifier.google_chat.urllib.request.urlopen")
    def test_send_posts_payload_and_returns_status(self, urlopen):
        response = urlopen.return_value.__enter__.return_value
        response.status = 200
        notifier = GoogleChatNotifier("https://example.invalid/webhook")
        self.assertEqual(notifier.send(TextMessage("hello")), 200)
        request, = urlopen.call_args.args
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(json.loads(request.data), {"text": "hello"})
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 10)

    @patch("google_chat_notifier.google_chat.urllib.request.urlopen")
    def test_http_error_reports_status(self, urlopen):
        urlopen.side_effect = urllib.error.HTTPError(
            "https://example.invalid", 400, "Bad Request", {}, io.BytesIO(b"invalid payload")
        )
        with self.assertRaisesRegex(RuntimeError, "Google Chat API error \\(400\\): invalid payload"):
            GoogleChatNotifier("https://example.invalid/webhook").send(TextMessage("hello"))


if __name__ == "__main__":
    unittest.main()
