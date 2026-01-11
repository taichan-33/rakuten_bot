# コマンド一覧

このプロジェクトで使用するコマンドのまとめです。Mac/Linux と Windows の両方に対応しています。

---

## セットアップ

### Mac / Linux

```bash
# 仮想環境を作成
python3 -m venv venv

# 仮想環境を有効化
source venv/bin/activate

# 依存関係をインストール
pip install -r requirements.txt

# Playwrightブラウザをインストール
playwright install chromium
```

### Windows (Command Prompt / PowerShell)

```cmd
:: 仮想環境を作成
python -m venv venv

:: 仮想環境を有効化
venv\Scripts\activate

:: 依存関係をインストール
pip install -r requirements.txt

:: Playwrightブラウザをインストール
playwright install chromium
```

---

## 実行

### Mac / Linux

```bash
# 基本実行
./run.sh

# 逐次処理モード
PARALLEL_WORKERS=1 ./run.sh

# ブラウザ表示（デバッグ）
HEADLESS=false ./run.sh
```

### Windows

```cmd
:: 基本実行 (run.batを使用)
run.bat

:: 逐次処理モード (Command Prompt)
set PARALLEL_WORKERS=1 && run.bat

:: ブラウザ表示 (Command Prompt)
set HEADLESS=false && run.bat
```

**※ PowerShell の場合:**

```powershell
$env:PARALLEL_WORKERS="1"; ./run.bat
```

---

## 期間フィルター

### Mac / Linux

```bash
DATE_FILTER_FROM=2024-01 ./run.sh
```

### Windows

```cmd
set DATE_FILTER_FROM=2024-01 && run.bat
```

---

## データベース・リセット (Clean Run)

### Mac / Linux

```bash
# DBとダウンロードファイルを削除して再実行
rm -f data.db && rm -rf downloads/* && ./run.sh
```

### Windows (Command Prompt)

```cmd
:: DBとダウンロードファイルを削除して再実行
if exist data.db del data.db
if exist downloads rmdir /s /q downloads
mkdir downloads
run.bat
```

---

## テスト

### Mac / Linux

```bash
./venv/bin/python -m pytest tests/ -v
```

### Windows

```cmd
venv\Scripts\python -m pytest tests/ -v
```

---

## 便利なコマンド

### ログ確認 (Mac/Linux)

```bash
tail -f logs/rakuten_bot.log
```

### ログ確認 (Windows PowerShell)

```powershell
Get-Content logs/rakuten_bot.log -Wait
```

---

## 定期実行（サーバー運用）

会社サーバーなどで自動実行する場合の設定例です。

### Mac / Linux (Cron)

毎日 朝 9:00 に実行する場合:

1. 編集モードに入る:

```bash
crontab -e
```

2. 以下を記述（パスは実際の環境に合わせて変更してください）:

```cron
0 9 * * * cd /Users/username/rakuten_bot && ./run.sh >> logs/cron.log 2>&1
```

### Windows (タスクスケジューラ)

1. スタートメニューから「タスクスケジューラ」を開く。
2. 「基本タスクの作成」をクリックし、名前（例: RakutenBot）を入力。
3. トリガーを設定（例: 「毎日」、開始時間 9:00）。
4. 操作で「プログラムの開始」を選択。
   - **プログラム/スクリプト**: `run.bat` のフルパス (例: `C:\rakuten_bot\run.bat`)
   - **開始 (オプション)**: プロジェクトフォルダのパス (例: `C:\rakuten_bot\`) **※これ重要です**

### 運用の注意点

1.  **二段階認証**:
    新しい環境（サーバー）で初回実行する際、二段階認証が求められる可能性が高いです。
    最初は `HEADLESS=false` （Windows なら `set HEADLESS=false` + `run.bat`）で手動実行し、認証を突破しておくことをお勧めします。

2.  **エラーハンドリング**:
    本ツールは一時的なエラーに対してリトライを行いますが、サイト構成の変更などで永続的に失敗する場合もあります。
    定期的に `report.csv` や `logs/` を確認してください。

---

## 監視スクリプト（Python）による実行

CRON やタスクスケジューラを使わず、Python スクリプト単体で 24 時間監視を行う方法です。
エラー時の自動リトライ機能が含まれています。

### Mac / Linux / Windows 共通

```bash
# 仮想環境内から実行
python app/utils/scheduler.py
```

※ デフォルトでは毎日 **9:00** に実行されます。変更したい場合は `app/utils/scheduler.py` 内の `TARGET_HOUR` を編集してください。
