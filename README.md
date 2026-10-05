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

### 同じスレッドへ繰り返し送る

同じスペースと Webhook で固定の `thread_key` を使うと、最初の通知でスレッドを作り、以後の通知はそのスレッドへの返信になります。プロセスをまたいで同じスレッドを使う場合も同じキーを保存・再利用してください。`monitor` の通知にも適用されます。

```python
notifier = GoogleChatNotifier(
    os.environ["GOOGLE_CHAT_WEBHOOK_URL"],
    thread_key="daily-report-2026-10-04",
)
notifier.send(TextMessage("集計を開始します"))
notifier.send(TextMessage("集計が終わりました"))
```

`thread_key` を省略した送信は従来どおり新しいメッセージになります。`thread_key` は同じ Webhook が始めたスレッドを指すため、Chat 上で人が作成した既存スレッドには指定できません。Google Chat の [スレッド付き Webhook の説明](https://developers.google.com/workspace/chat/quickstart/webhooks)も参照してください。

**スレッド返信の通知:** `send()` が HTTP 200 を返しても、受信者のプッシュ通知は保証されません。このライブラリはサイレント送信を指定していません。通知を受けたい場合は、対象スペース名の横の「▼」→「お知らせ」→「すべて」を選び、対象スレッドもフォローしてください。Google Chat の日本語ヘルプでは、「すべて」で通知される返信はフォロー中のスレッドへの返信と説明されています。詳しくは [Google Chat の通知ヘルプ](https://support.google.com/chat/answer/7655718?hl=ja) を参照してください。Webhook から受信者の設定を無視して通知を強制することはできず、[強制通知は Chat アプリ認証が必要](https://developers.google.com/workspace/chat/create-messages#send-forced-notifications-or-silent-messages)です。

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

## コンポーネント集

`Notification` の `Section(widgets=[...])` に並べて使います。表の右列は主な用途です。

| コンポーネント | 用途 |
| --- | --- |
| `TextParagraph(text, color=None, bold=False)` | 説明文やリリースノート |
| `DecoratedText(text, top_label=None, bottom_label=None, start_icon=None, end_icon=None)` | 上下ラベルと前後アイコン付きのテキスト |
| `Field(label, value, ...)` / `FieldLink(...)` | ラベル付きの値、リンク付きの値 |
| `Stat(top, value, bottom="")` | 2 個ずつ横並びになる数値 |
| `Grid(items=[GridItem(...)], columns=2, title=None)` | 画像・タイトル・サブタイトルを持つタイル |
| `Row(items=[RowItem(widget, weight=1), ...])` | 最大 2 列の横並び |
| `Column(widgets=[...])` | `RowItem` の列内で複数ウィジェットを縦に並べる |
| `ButtonGroup(buttons=[Button(...)])` | セクション内の任意の位置にリンクボタンを配置 |
| `ButtonStyle.FILLED` / `OUTLINED` / `TEXT` | 塗りつぶし・枠線・枠なしのボタン |
| `Chip(label, icon=None)` / `Code(text)` | 短いタグ・等幅テキスト |
| `Image(url)` / `Divider()` / `LinkButton(label, url)` | 画像・区切り線・従来の末尾配置ボタン |

`RowItem.weight` は厳密な幅比率ではありません。Google Chat の `columns` が提供する「通常幅」と「最小幅」に大小関係を写します。`Row` の中に入れられるのはテキスト、画像、装飾テキスト、ボタンなど、Cards V2 が列内でサポートするウィジェットです。`Column` は `RowItem` の中だけで使います。セクション全体の縦方向の並びは `Section.widgets` の順序で表現します。

`ButtonStyle.TEXT` は Cards V2 の `BORDERLESS` に対応します。Webhook のボタンは URL を開く用途に限り、承認やフォーム送信の処理は行いません。`Icon` には色指定がありません。

### Icon の選び方

1. [Google Fonts の Material Symbols 一覧](https://fonts.google.com/icons)を開き、用途に合うアイコンを検索します。
2. アイコンの名前を確認し、その名前を `Icon("check_circle")` のように渡します。名前は `warning`、`database`、`cloud` などの英小文字とアンダースコアで表記します。
3. `DecoratedText(start_icon=...)`、`DecoratedText(end_icon=...)`、`Button(icon=...)` などに指定します。無効な名前は Chat 上で表示されません。

Cards V2 の [Material Icon フィールド仕様](https://developers.google.com/workspace/chat/api/reference/rest/v1/cards#materialicon)ではアイコン名を指定します。`Icon` 自体には色を付けられないため、色で状態を示す場合は `NotificationTheme` やテキストの `color` を使ってください。

```python
from google_chat_notifier import (
    Button, ButtonGroup, ButtonStyle, Column, DecoratedText, Grid, GridItem,
    Icon, Notification, NotificationTheme, Row, RowItem, Section,
    TextParagraph,
)

alert = Notification(
    style=NotificationTheme.WARNING,
    title="DB 負荷高騰",
    sections=[Section(widgets=[
        TextParagraph("CPU 使用率が 80% を超えました。", bold=True),
        DecoratedText("db-cluster-prod-01", top_label="対象", end_icon=Icon("warning")),
        Grid(columns=2, items=[
            GridItem("CPU", "85%"),
            GridItem("Memory", "60%"),
        ]),
        Row(items=[
            RowItem(Column([TextParagraph("状態: 警告"), TextParagraph("要確認")]), weight=2),
            RowItem(TextParagraph("確認中"), weight=1),
        ]),
        ButtonGroup(buttons=[
            Button("Runbook", "https://example.com/runbook", ButtonStyle.FILLED),
            Button("メトリクス", "https://example.com/metrics", ButtonStyle.OUTLINED),
        ]),
    ])],
)
notifier.send(alert)
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

スレッドと拡張コンポーネントを実送信する場合は `python -m scripts.send_thread_smoke` を実行します。Chat スペースに同じスレッドキーで 2 件投稿されます。
