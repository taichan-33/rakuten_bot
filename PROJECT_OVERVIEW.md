# Rakuten Invoice Downloader Project Overview

このドキュメントでは、開発者がプロジェクトの全体像、依存関係、アーキテクチャを迅速に把握できるように、プロジェクトの詳細を解説します。

## 1. プロジェクト概要

**名称**: Rakuten Invoice Downloader (v2) - Mac Version

**目的**:
楽天市場の購入履歴から領収書（PDF など）を自動的にダウンロードし、保存・管理するための自動化ツールです。

**主な機能**:

- **自動ログイン**: Rakuten Global ID および 旧ログインフローに対応。
- **領収書スクレイピング**: 通常の楽天市場および楽天ブックスに対応。
- **Books 最適化**: 楽天ブックス注文は詳細ページへの遷移をスキップし、一覧ページから高速処理。
- **並列処理**: 複数のブラウザコンテキスト（Workers）を使用した高速処理。
- **状態管理**: SQLite を使用して、ダウンロード済み・エラー・リトライ対象などを管理。
- **耐障害性**: ネットワークタイムアウトや一時的なエラーに対するリトライ機能（ブラウザ再起動やポップアップ制御を含む）。
- **レポート出力**: 処理結果を CSV で出力。

---

## 2. 依存関係 (Dependencies)

このプロジェクトは Python 3.x で記述されており、以下の主要ライブラリに依存しています。

| ライブラリ         | 用途                               | 備考                                          |
| :----------------- | :--------------------------------- | :-------------------------------------------- |
| **playwright**     | ブラウザ自動化 (Headless Chromium) | 高速で信頼性の高いスクレイピングに使用        |
| **python-dotenv**  | 環境変数管理                       | `.env` から設定を読み込むために使用           |
| **pytest**         | テストフレームワーク               | ユニットテストおよび結合テスト用              |
| **pytest-asyncio** | 非同期テストサポート               | Playwright の非同期処理をテストするために必須 |
| **sqlite3**        | データベース                       | 標準ライブラリ。状態管理に使用                |

依存関係のインストール:

```bash
pip install -r requirements.txt
playwright install chromium
```

---

## 3. ディレクトリ構造

```text
/Users/taitai03/rakuten_bot
├── main.py                 # エントリーポイント。アプリ全体の起動と制御。
├── config.py               # 設定管理クラス (.envの読み込み)。
├── run.sh                  # 実行用シェルスクリプト。
├── requirements.txt        # Python依存パッケージリスト。
├── .env                    # 環境変数 (ユーザーID, パスワード等)。
├── data.db                 # SQLiteデータベース (実行時に生成)。
├── report.csv              # 実行結果レポート。
├── downloads/              # 領収書の保存先ディレクトリ。
├── logs/                   # アプリケーションログ。
│
├── app/
│   ├── main.py             # アプリケーションロジックのエントリーポイント。
│   │
│   ├── core/               # コアロジック
│   │   ├── authenticator.py        # ログイン処理の統括クラス。
│   │   ├── login_flows.py          # ログイン戦略クラス (Strategy Pattern)。
│   │   ├── browser_manager.py      # Playwright ブラウザインスタンス管理。
│   │   ├── order_processor.py      # [逐次処理用] 注文処理のオーケストレーター。
│   │   ├── parallel_processor.py   # [並列処理用] Workerを使用した並列処理。
│   │   └── db_manager.py           # データベース操作 (Repository Pattern)。
│   │
│   ├── handlers/           # 各ショップ対応ハンドラ (Strategy/Factory Pattern)
│   │   ├── base_handler.py         # ハンドラ基底クラス。
│   │   ├── standard_handler.py     # 通常ショップ用ハンドラ。
│   │   ├── books_handler.py        # 楽天ブックス用ハンドラ（最適化済み）。
│   │   └── factory.py              # Handler生成ファクトリ。
│   │
│   ├── models/             # データモデル
│   │   └── order_status.py         # 注文ステータス定義 (Enum)。
│   │
│   └── utils/              # ユーティリティ
│       ├── logger.py               # ロギング設定。
│       ├── retry_handler.py        # 汎用リトライロジック。
│       └── pdf_downloader.py       # PDF保存ロジック。
│
└── tests/                  # テストコード。
```

---

## 4. アーキテクチャ詳細

このプロジェクトは、保守性と拡張性を高めるためにいくつかのデザインパターンを採用しています。

### 4.1. ログイン処理 (Strategy Pattern)

楽天のログイン画面はユーザーやアクセス元によって異なるため、`authenticator.py` が状況に応じて適切な戦略 (`login_flows.py`) を選択します。

- **LegacyLoginFlow**: 古い形式の入力フォーム (`name="u"`, `name="p"`) 用。
- **GlobalIdLoginFlow**: 新しい Global ID 形式 (`username` -> `Next` -> `password`) 用。

### 4.2. 注文処理 (Factory & Strategy Pattern)

ショップの種類（通常店舗、楽天ブックスなど）によってページの構造が異なるため、`OrderHandler` 抽象クラスを継承した具象クラスを実装しています。

- **StandardOrderHandler**: 一般的な楽天市場のショップ用。詳細ページに遷移して発行ボタンを探します。
- **BooksOrderHandler**: 楽天ブックス専用。**一覧ページからの直接処理**をサポートし、画面遷移を最小限に抑えることで高速化と安定性を実現しています。また、ポップアップウィンドウの制御と待機ロジックが強化されています。
- **OrderHandlerFactory**: 現在の URL や注文 ID に基づいて適切な Handler を選択・生成します。

### 4.3. データ管理 (Repository Pattern)

`DBManager` クラスが SQLite へのアクセスを隠蔽します。アプリケーション層は SQL を意識せず、`should_process(order_id)` や `update_order(...)` などのメソッドを通じて状態を操作します。

### 4.4. 並列処理モデル

`config.py` の `PARALLEL_WORKERS` が 2 以上の場合、`app.main` は `ParallelOrderProcessor` を選択します。

- 各ワーカーは独立した処理ループを持ちます。
- ページ単位で担当を割り振ることで競合を防ぎます（例: Worker 0 は 1 ページ目, Worker 1 は 2 ページ目...）。

---

## 5. データベーススキーマ

`data.db` (SQLite) 内の `orders` テーブルで各注文の状態を管理しています。

| カラム名        | 型        | 説明                         |
| :-------------- | :-------- | :--------------------------- |
| `order_id`      | TEXT (PK) | 注文番号 (Primary Key)       |
| `order_number`  | INTEGER   | 処理時の通し番号             |
| `status`        | TEXT      | 現在のステータス (下記参照)  |
| `error_message` | TEXT      | エラー時の詳細メッセージ     |
| `retry_count`   | INTEGER   | リトライ回数                 |
| `filename`      | TEXT      | ダウンロードされたファイル名 |
| `downloaded_at` | TEXT      | ダウンロード完了日時         |
| `created_at`    | TEXT      | レコード作成日時             |
| `updated_at`    | TEXT      | 最終更新日時                 |

**ステータス一覧 (`order_status.py`)**:

- `OrderStatus.DONE`: 完了 (ダウンロード済み)
- `OrderStatus.PENDING`: 未処理
- `OrderStatus.NO_RECEIPT`: 領収書ボタンなし (発行不可)
- `OrderStatus.ERROR`: エラー発生
- `OrderStatus.RETRY`: 一時的なエラー (次回再試行対象)
- `OrderStatus.SKIP`: スキップ対象（Books 電子書籍など）

---

## 6. データフロー

1. **初期化**: `RakutenBotApp` が設定の検証、DB 初期化、ブラウザ起動を行う。
2. **認証**: `Authenticator` がログインを実行。
   - 失敗時はリトライ、または処理中断。
3. **巡回 (Processing)**:
   - 購入履歴ページへ移動。
   - `OrderHandler` がページ内の注文番号リストを抽出。
4. **判定**:
   - `DBManager.should_process(order_id)` で処理済みか確認。
   - `DONE` やリトライ上限超えの場合はスキップ。
5. **実行**:
   - **Books の場合**: 一覧ページから直接発行処理開始（ポップアップ制御）。
   - **Standard の場合**: 詳細ページへ遷移し、ボタン探索。
   - ダウンロードイベントを捕捉し、ファイルを保存。
6. **記録**: 結果を DB に保存 (`update_order`)。
7. **完了**: 全ページ処理後、`DBManager.export_report()` で CSV を出力。

---

## 7. 開発ガイド

### ローカルでの実行

```bash
# 仮想環境の有効化(必要であれば)
# source venv/bin/activate

# 実行
./run.sh
```

### デバッグ設定

`.env` ファイルの `HEADLESS` を `false` に設定すると、実際にブラウザが動作する様子を確認できます。

```ini
HEADLESS=false
```

### テストの実行

```bash
# 全テスト実行
pytest tests/

# 特定のテスト実行
pytest tests/test_order_processor.py
```
