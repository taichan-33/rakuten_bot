# Rakuten Invoice Downloader (v2) - Mac Version

楽天購入履歴から領収書を自動ダウンロードする Bot です。
TDD（テスト駆動開発）ベースで構築されており、安定性と保守性を重視しています。

## 環境

- OS: macOS
- Python: 3.x
- Browser: Chromium (Playwright)

## セットアップ

1. **Python のインストール**
   Python 3.x をインストールしてください。

2. **依存関係のインストール**
   ターミナルで以下を実行します。

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   playwright install chromium
   ```

3. **環境変数 (.env) の設定**
   `.env` ファイルを作成し、以下の情報を入力してください。

   ```ini
   RAKUTEN_USER_ID=your_user_id
   RAKUTEN_PASSWORD=your_password
   HEADLESS=true  # false にするとブラウザが表示されます (デバッグ用)
   RECEIPT_ADDRESSEE=楽天 太郎  # 領収書の宛名
   ```

4. **実行権限の付与**
   ```bash
   chmod +x run.sh
   ```

## 実行方法

### 手動実行

```bash
./run.sh
```

### 自動実行 (Cron)

`crontab -e` で以下を設定してください（例: 毎日 2:00 に実行）。
※ `/path/to/rakuten_bot` は実際のパスに書き換えてください。

```bash
0 2 * * * /path/to/rakuten_bot/run.sh >> /path/to/rakuten_bot/cron.log 2>&1
```

## 仕組み

1. **起動**: DB がない場合は初期化 (`data.db`)。
2. **ログイン**: 楽天にヘッドレスブラウザでログイン。
3. **巡回**: 直近の注文履歴を確認。
   - ステータスが `DONE` ならスキップ。
   - `領収書発行` ボタンが有効ならダウンロード -> `downloads/` -> `DONE`。
   - ボタンが無効 (配送中など) なら `PENDING`。
   - エラー時は `ERROR`。
4. **レポート**: 結果を `report.csv` に出力。

## 開発・テスト

テストコードは `tests/` ディレクトリにあります。

```bash
source venv/bin/activate
pytest tests/
```
