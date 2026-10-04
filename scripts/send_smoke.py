"""Send exactly one live smoke-test notification to Google Chat."""

import os

from google_chat_notifier import BaseMessage, GoogleChatNotifier


class SmokeNotifier(GoogleChatNotifier):
    last_status: int | None = None

    def send(self, message: BaseMessage) -> int:
        self.last_status = super().send(message)
        return self.last_status


def main() -> None:
    url = os.environ["GOOGLE_CHAT_WEBHOOK_URL"]
    notifier = SmokeNotifier(url)

    @notifier.monitor(task_name="google-chat-notifier 実送信テスト")
    def smoke_test() -> str:
        return "monitor success"

    smoke_test()
    if notifier.last_status is None:
        raise RuntimeError("monitor did not successfully send a notification")
    print(f"Google Chat HTTP status: {notifier.last_status}")


if __name__ == "__main__":
    main()
