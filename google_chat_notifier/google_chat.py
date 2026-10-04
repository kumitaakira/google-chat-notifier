"""Google Chat incoming webhook implementation."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .base import Notifier
from .cards import BaseMessage, Field, Icon, Notification, NotificationTheme, Section, Stat


def default_success_builder(task_name: str, duration: float, result: Any) -> BaseMessage:
    widgets = [Stat(top="Duration", value=f"{duration:.2f}s")]
    if result is not None:
        widgets.append(Field(label="Result", value=str(result)))
    return Notification(
        style=NotificationTheme.SUCCESS,
        title=f"Task Completed: {task_name}",
        sections=[Section(widgets=widgets)],
    )


def default_error_builder(task_name: str, duration: float, error: Exception) -> BaseMessage:
    return Notification(
        style=NotificationTheme.ERROR,
        title=f"Task Failed: {task_name}",
        sections=[
            Section(widgets=[Stat(top="Duration", value=f"{duration:.2f}s")]),
            Section(
                header="Error Details",
                widgets=[Field(
                    label=type(error).__name__,
                    value=str(error) or "<No details>",
                    icon=Icon("bug_report"),
                    color="#DB4437",
                )],
            ),
        ],
    )


class GoogleChatNotifier(Notifier):
    """Send messages to a Google Chat space via an incoming webhook."""

    def __init__(self, webhook_url: str, *, thread_key: str | None = None):
        if not webhook_url:
            raise ValueError("webhook_url must be provided")
        if thread_key is not None and (not thread_key.strip() or len(thread_key) > 4000):
            raise ValueError("thread_key must contain 1 to 4000 characters")
        self.webhook_url = webhook_url
        self.thread_key = thread_key

    def _request_url(self) -> str:
        if self.thread_key is None:
            return self.webhook_url
        parts = urllib.parse.urlsplit(self.webhook_url)
        query = [
            (key, value)
            for key, value in urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
            if key != "messageReplyOption"
        ]
        query.append(("messageReplyOption", "REPLY_MESSAGE_FALLBACK_TO_NEW_THREAD"))
        return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(query)))

    def default_success_builder(self, task_name: str, duration: float, result: Any) -> BaseMessage:
        return default_success_builder(task_name, duration, result)

    def default_error_builder(self, task_name: str, duration: float, error: Exception) -> BaseMessage:
        return default_error_builder(task_name, duration, error)

    def send(self, message: BaseMessage) -> int:
        payload = message.build_payload()
        if self.thread_key is not None:
            payload = {**payload, "thread": {"threadKey": self.thread_key}}
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self._request_url(),
            data=data,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.status
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Google Chat API error ({exc.code}): {body}") from exc
