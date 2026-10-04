# google-chat-notifier

Google Chat の Incoming Webhook にテキストやカードを送る Python ライブラリです。関数の完了・失敗を通知する `monitor` も利用できます。Python 3.12 以上、実行時の外部依存なし。

## インストール

GitHub からインストールする場合:

`uv` で仮想環境にインストールする場合:

```sh
uv venv
uv pip install "git+https://github.com/kumitaakira/google-chat-notifier.git"
```

既存の `uv` プロジェクトの依存関係として追加する場合:

```sh
uv add "google-chat-notifier @ git+https://github.com/kumitaakira/google-chat-notifier.git"
```

`pip` を使う場合:

```sh
python -m pip install "git+https://github.com/kumitaakira/google-chat-notifier.git"
```

ローカルのチェックアウトを `uv` で編集可能な状態としてインストールする場合:

```sh
uv venv
uv pip install -e .
```

`pip` でローカルインストールする場合:

```sh
python -m pip install .
```

### 別のローカルフォルダで使う

使いたいプロジェクトのフォルダへ移動し、このリポジトリのパスを指定します。`uv` プロジェクト（`pyproject.toml` がある場合）なら依存関係として追加できます。

```sh
cd /path/to/another-project
uv add /Users/kumitaakira/my_temp/google_chat_notifier
```

ライブラリ側の変更をそのプロジェクトにもすぐ反映したい開発中は、`uv add --editable /Users/kumitaakira/my_temp/google_chat_notifier` を使います。

`uv` プロジェクトではないフォルダで、仮想環境にだけインストールする場合:

```sh
cd /path/to/another-folder
uv venv --python 3.12
uv pip install /Users/kumitaakira/my_temp/google_chat_notifier
```

この場合、ライブラリ側の変更をすぐ反映したければ最後のコマンドを `uv pip install -e /Users/kumitaakira/my_temp/google_chat_notifier` に替えます。

## 使い方

Google Chat のスペースで Incoming Webhook を作成し、URL を環境変数に設定してください。URL に含まれる `key` と `token` は秘密情報です。

```sh
export GOOGLE_CHAT_WEBHOOK_URL='https://chat.googleapis.com/v1/spaces/.../messages?key=...&token=...'
```

```python
import os
from google_chat_notifier import GoogleChatNotifier, TextMessage

notifier = GoogleChatNotifier(os.environ["GOOGLE_CHAT_WEBHOOK_URL"])
status = notifier.send(TextMessage("デプロイを開始します"))

@notifier.monitor(task_name="日次集計")
def run_report() -> int:
    return 42

run_report()
```

`monitor` は同期関数を対象にします。元の戻り値と例外は維持され、通知やビルダーの失敗は標準エラーに警告を出して元の処理を妨げません。`@notifier.monitor` と `@notifier.monitor()` の両方を使えます。

通知内容を変える場合は `(task_name, duration_seconds, result)` と `(task_name, duration_seconds, exception)` を受け取る関数を渡します。`None` を返すとその通知を省略します。引数 `on_success=None` または `on_error=None` でも該当通知を無効にできます。

```python
from google_chat_notifier import TextMessage

@notifier.monitor(
    on_success=lambda name, seconds, result: TextMessage(f"{name}: {result}"),
    on_error=None,
)
def job():
    return "OK"
```

## 他の Webhook への拡張

`Notifier` を継承し、`send(message: BaseMessage) -> int` を実装します。`monitor` は継承できます。送信先に合うよう `default_success_builder` と `default_error_builder` を上書きできます。`BaseMessage.build_payload()` は辞書を返すため、Webhook ごとの形式変換は `send` に実装してください。

```python
from google_chat_notifier import Notifier, TextMessage

class MyNotifier(Notifier):
    def send(self, message):
        payload = message.build_payload()
        # ここで送信先の形式に合わせて送る
        return 200
```

## 開発と検証

```sh
python -m unittest discover -s tests -v
python -m pip wheel . --no-deps -w /tmp/google-chat-notifier-wheels
```

実際の送信は `GOOGLE_CHAT_WEBHOOK_URL` が設定されている環境で、次を実行します。Chat スペースにテスト通知が 1 件投稿されます。

```sh
python -m scripts.send_smoke
```
