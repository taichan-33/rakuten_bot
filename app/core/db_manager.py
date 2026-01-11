"""
データベース管理クラス
責務: 注文情報の永続化とレポート出力
"""

import sqlite3
import csv
from datetime import datetime
from app.models.order_status import OrderStatus


class DBManager:
    MAX_RETRY_COUNT = 3  # 最大リトライ回数

    def __init__(self, db_path="data.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """データベースとテーブルを初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                order_number INTEGER,
                status TEXT,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                filename TEXT,
                downloaded_at TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """
        )
        conn.commit()
        conn.close()

    def get_order_status(self, order_id: str) -> str:
        """注文のステータスを取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM orders WHERE order_id = ?", (order_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None

    def get_retry_count(self, order_id: str) -> int:
        """注文のリトライ回数を取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT retry_count FROM orders WHERE order_id = ?", (order_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0

    def should_process(self, order_id: str) -> bool:
        """この注文を処理すべきか判定"""
        status = self.get_order_status(order_id)

        # 最終ステータスはスキップ
        if OrderStatus.is_final(status):
            return False

        # リトライ回数チェック
        if status == OrderStatus.RETRY.value:
            retry_count = self.get_retry_count(order_id)
            if retry_count >= self.MAX_RETRY_COUNT:
                # 最大リトライ回数に到達 → エラーに切り替え
                self.update_order(
                    order_id,
                    OrderStatus.ERROR.value,
                    error_message="最大リトライ回数に到達",
                )
                return False

        return OrderStatus.should_process(status)

    def update_order(
        self,
        order_id: str,
        status: str,
        filename: str = None,
        error_message: str = None,
        increment_retry: bool = False,
        order_number: int = None,
    ):
        """注文ステータスを更新または挿入"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute(
            "SELECT 1, retry_count FROM orders WHERE order_id = ?", (order_id,)
        )
        result = cursor.fetchone()
        exists = result is not None
        current_retry = result[1] if result else 0

        retry_count = current_retry + 1 if increment_retry else current_retry

        # DONE ステータスの場合はダウンロード日時を設定
        downloaded_at = now if status == "DONE" else None

        if exists:
            if status == "DONE":
                cursor.execute(
                    """
                    UPDATE orders 
                    SET status = ?, filename = ?, error_message = ?, 
                        retry_count = ?, downloaded_at = ?, updated_at = ?
                    WHERE order_id = ?
                """,
                    (
                        status,
                        filename,
                        error_message,
                        retry_count,
                        downloaded_at,
                        now,
                        order_id,
                    ),
                )
            else:
                cursor.execute(
                    """
                    UPDATE orders 
                    SET status = ?, filename = ?, error_message = ?, 
                        retry_count = ?, updated_at = ?
                    WHERE order_id = ?
                """,
                    (status, filename, error_message, retry_count, now, order_id),
                )
        else:
            cursor.execute(
                """
                INSERT INTO orders 
                (order_id, order_number, status, filename, downloaded_at, error_message, retry_count, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    order_id,
                    order_number,
                    status,
                    filename,
                    downloaded_at,
                    error_message,
                    retry_count,
                    now,
                    now,
                ),
            )

        conn.commit()
        conn.close()

    def get_summary(self, since: str = None) -> dict:
        """ステータス別の集計を取得 (since以降)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if since:
            cursor.execute(
                """
                SELECT status, COUNT(*) 
                FROM orders 
                WHERE updated_at >= ?
                GROUP BY status
                """,
                (since,),
            )
        else:
            cursor.execute(
                """
                SELECT status, COUNT(*) 
                FROM orders 
                GROUP BY status
                """
            )

        results = cursor.fetchall()
        conn.close()
        return {row[0]: row[1] for row in results}

    def get_pending_orders(self) -> list:
        """再処理対象の注文IDリストを取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT order_id FROM orders 
            WHERE status IN (?, ?) AND retry_count < ?
        """,
            (OrderStatus.RETRY.value, OrderStatus.PENDING.value, self.MAX_RETRY_COUNT),
        )
        results = cursor.fetchall()
        conn.close()
        return [row[0] for row in results]

    def export_report(self, csv_path="report.csv", since: str = None):
        """データをCSVにエクスポート"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if since:
            cursor.execute(
                "SELECT * FROM orders WHERE updated_at >= ? ORDER BY updated_at DESC",
                (since,),
            )
        else:
            cursor.execute("SELECT * FROM orders ORDER BY updated_at DESC")

        rows = cursor.fetchall()

        if cursor.description:
            column_names = [desc[0] for desc in cursor.description]
        else:
            column_names = []

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if column_names:
                writer.writerow(column_names)
            writer.writerows(rows)

        conn.close()

        # サマリーを出力
        summary = self.get_summary(since)
        print(f"\n=== 実行サマリー ===")
        print(f"完了 (DONE): {summary.get('DONE', 0)} 件")
        print(f"発行不可 (NO_RECEIPT): {summary.get('NO_RECEIPT', 0)} 件")
        print(f"リトライ待ち (RETRY): {summary.get('RETRY', 0)} 件")
        print(f"エラー (ERROR): {summary.get('ERROR', 0)} 件")
        print(f"レポート出力: {csv_path}")

    def close(self):
        """DBリソースを解放（安全終了用）"""
        # SQLiteはコネクションをメソッドごとに開閉しているため特別な処理不要
        pass
