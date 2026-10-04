"""Post a rich card and a reply to one new Google Chat thread."""

import os
import time
import uuid

from google_chat_notifier import (
    Button, ButtonGroup, ButtonStyle, DecoratedText, GoogleChatNotifier,
    Grid, GridItem, Icon, Notification, NotificationTheme, Row, RowItem,
    Section, TextMessage, TextParagraph,
)


def main() -> None:
    key = f"notifier-smoke-{uuid.uuid4().hex}"
    notifier = GoogleChatNotifier(os.environ["GOOGLE_CHAT_WEBHOOK_URL"], thread_key=key)
    card = Notification(
        style=NotificationTheme.INFO,
        title="google-chat-notifier component smoke test",
        sections=[Section(widgets=[
            TextParagraph("Cards V2 component test", bold=True),
            DecoratedText("healthy", top_label="Status", end_icon=Icon("check_circle")),
            Grid(columns=2, items=[GridItem("CPU", "42%"), GridItem("Memory", "60%")]),
            Row(items=[RowItem(TextParagraph("Left")), RowItem(TextParagraph("Right"))]),
            ButtonGroup(buttons=[
                Button("Documentation", "https://developers.google.com/workspace/chat", ButtonStyle.OUTLINED),
                Button("Repository", "https://github.com/kumitaakira/google-chat-notifier", ButtonStyle.TEXT),
            ]),
        ])],
    )
    first_status = notifier.send(card)
    time.sleep(1.2)  # Chat incoming webhooks share a per-space rate limit.
    reply_status = notifier.send(TextMessage("Reply in the same thread"))
    print(f"thread_key={key} first_status={first_status} reply_status={reply_status}")


if __name__ == "__main__":
    main()
