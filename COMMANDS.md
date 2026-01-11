# コマンド一覧

このプロジェクトで使用するコマンドのまとめです。

---

## セットアップ

```bash
# 仮想環境を作成
python -m venv venv

# 仮想環境を有効化
source venv/bin/activate

# 依存関係をインストール
pip install -r requirements.txt

# Playwrightブラウザをインストール
playwright install chromium
```

---

## 実行

### 基本実行

```bash
./run.sh
```

### 逐次処理モード（並列処理なし）

```bash
PARALLEL_WORKERS=1 ./run.sh
```

### ワーカー数を指定

```bash
PARALLEL_WORKERS=5 ./run.sh
```

### ブラウザを表示して実行（デバッグ用）

```bash
HEADLESS=false ./run.sh
```

---

## 期間フィルター

### 特定の年月のみ処理

```bash
DATE_FILTER_FROM=2024-01 ./run.sh
```

### 期間を指定して処理

```bash
DATE_FILTER_FROM=2024-01 DATE_FILTER_TO=2024-12 ./run.sh
```

### 全期間を処理（デフォルト）

```bash
./run.sh
```

---

## テスト

### 全テスト実行

```bash
./venv/bin/python -m pytest tests/ -v
```

### 特定のテストファイルを実行

```bash
./venv/bin/python -m pytest tests/test_order_handler.py -v
```

### カバレッジ付きテスト

```bash
./venv/bin/python -m pytest tests/ --cov=. --cov-report=html
```

---

## データベース

### DB と PDF をリセットして実行

```bash
rm -f data.db && rm -rf downloads/* && ./run.sh
```

### DB の内容を確認

```bash
sqlite3 data.db "SELECT * FROM orders;"
```

### ステータス別に確認

```bash
sqlite3 data.db "SELECT status, COUNT(*) FROM orders GROUP BY status;"
```

---

## レポート

### CSV レポートを確認

```bash
cat report.csv
```

### ダウンロードしたファイルを確認

```bash
ls -la downloads/
```

---

## トラブルシューティング

### ブラウザを再インストール

```bash
playwright install --force chromium
```

### 依存関係を更新

```bash
pip install --upgrade -r requirements.txt
```

### ログをリアルタイムで確認

```bash
tail -f logs/rakuten_bot.log
```
