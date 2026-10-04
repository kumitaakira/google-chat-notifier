import io
import json
import unittest
import urllib.error
import urllib.parse
from contextlib import redirect_stderr
from unittest.mock import patch

from google_chat_notifier import (
    Button, ButtonGroup, ButtonStyle, Column, DecoratedText, Field, Grid, GridItem,
    GoogleChatNotifier, Icon, Notification, NotificationTheme, Notifier, Row,
    RowItem, Section, TextMessage, TextParagraph,
)


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
    @patch("google_chat_notifier.google_chat.urllib.request.urlopen")
    def test_repeated_sends_use_same_thread_key(self, urlopen):
        urlopen.return_value.__enter__.return_value.status = 200
        notifier = GoogleChatNotifier(
            "https://example.invalid/webhook?key=secret&token=also-secret&messageReplyOption=old",
            thread_key="daily-report",
        )
        self.assertEqual(notifier.send(TextMessage("first")), 200)
        self.assertEqual(notifier.send(TextMessage("second")), 200)
        for call in urlopen.call_args_list:
            request = call.args[0]
            self.assertEqual(json.loads(request.data)["thread"], {"threadKey": "daily-report"})
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(request.full_url).query)
            self.assertEqual(query["key"], ["secret"])
            self.assertEqual(query["token"], ["also-secret"])
            self.assertEqual(query["messageReplyOption"], ["REPLY_MESSAGE_FALLBACK_TO_NEW_THREAD"])

    @patch("google_chat_notifier.google_chat.urllib.request.urlopen")
    def test_monitor_uses_configured_thread_key(self, urlopen):
        urlopen.return_value.__enter__.return_value.status = 200
        notifier = GoogleChatNotifier("https://example.invalid/webhook?key=k", thread_key="job-1")

        @notifier.monitor
        def job():
            return "done"

        self.assertEqual(job(), "done")
        payload = json.loads(urlopen.call_args.args[0].data)
        self.assertEqual(payload["thread"], {"threadKey": "job-1"})

    def test_invalid_thread_key_is_rejected(self):
        for key in ("", "  ", "a" * 4001):
            with self.subTest(key_length=len(key)), self.assertRaises(ValueError):
                GoogleChatNotifier("https://example.invalid", thread_key=key)

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


class ComponentTests(unittest.TestCase):
    def test_rich_components_preserve_order_and_cards_v2_fields(self):
        widgets = [
            TextParagraph("Alert\nCPU high", bold=True),
            DecoratedText("database", top_label="Resource", bottom_label="production", end_icon=Icon("warning")),
            Grid(columns=2, items=[GridItem("CPU", "85%", "https://example.com/cpu.png")]),
            Row(items=[
                RowItem(Column([Field("State", "warning"), TextParagraph("Needs attention")]), weight=2),
                RowItem(TextParagraph("Open")),
            ]),
            ButtonGroup(buttons=[
                Button("Runbook", "https://example.com/runbook", ButtonStyle.FILLED, Icon("book")),
                Button("Metrics", "https://example.com/metrics", ButtonStyle.TEXT),
            ]),
        ]
        notification = Notification(NotificationTheme.WARNING, title="Incident", sections=[Section(widgets=widgets)])
        built = notification.build_payload()["cardsV2"][0]["card"]["sections"][0]["widgets"]
        self.assertEqual([next(iter(item)) for item in built], [
            "textParagraph", "decoratedText", "grid", "columns", "buttonList",
        ])
        self.assertEqual(built[1]["decoratedText"]["endIcon"], {"materialIcon": {"name": "warning"}})
        self.assertEqual(built[2]["grid"]["items"][0]["image"]["imageUri"], "https://example.com/cpu.png")
        self.assertEqual(built[3]["columns"]["columnItems"][1]["horizontalSizeStyle"], "FILL_MINIMUM_SPACE")
        self.assertEqual(len(built[3]["columns"]["columnItems"][0]["widgets"]), 2)
        self.assertEqual([button["type"] for button in built[4]["buttonList"]["buttons"]], ["FILLED", "BORDERLESS"])

    def test_invalid_layouts_fail_instead_of_disappearing(self):
        for widget in (
            Grid(columns=0, items=[GridItem("x")]),
            Row(items=[RowItem(TextParagraph("a"))] * 3),
            Row(items=[RowItem(Grid(items=[GridItem("x")]))]),
            Row(items=[RowItem(Column([]))]),
            ButtonGroup(buttons=[]),
        ):
            with self.subTest(widget=type(widget).__name__), self.assertRaises(ValueError):
                Section(widgets=[widget]).build(NotificationTheme.INFO)


if __name__ == "__main__":
    unittest.main()
