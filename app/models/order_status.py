"""
注文ステータス定義
責務: ステータスの種類と意味を定義
"""

from enum import Enum


class OrderStatus(str, Enum):
    """注文処理ステータス"""

    # 完了ステータス（再処理しない）
    DONE = "DONE"  # 正常完了（領収書発行済み）
    NO_RECEIPT = "NO_RECEIPT"  # 領収書発行機能なし（仕様上発行不可）

    # 要再処理ステータス
    RETRY = "RETRY"  # 一時的エラー（タイムアウト等）→ 次回再処理
    PENDING = "PENDING"  # 未処理

    # エラーステータス（要手動確認）
    ERROR = "ERROR"  # 致命的エラー（手動確認が必要）

    @classmethod
    def should_process(cls, status: str) -> bool:
        """このステータスの注文を処理すべきか判定"""
        if status is None:
            return True
        return status in [cls.RETRY.value, cls.PENDING.value]

    @classmethod
    def is_final(cls, status: str) -> bool:
        """このステータスが最終状態か判定"""
        return status in [cls.DONE.value, cls.NO_RECEIPT.value, cls.ERROR.value]


class IssueResult:
    """領収書発行結果"""

    def __init__(self, status: OrderStatus, error_message: str = None):
        self.status = status
        self.error_message = error_message

    @classmethod
    def success(cls, filename: str = None):
        result = cls(OrderStatus.DONE)
        result.filename = filename
        return result

    @classmethod
    def no_receipt(cls, reason: str = "領収書発行機能なし"):
        return cls(OrderStatus.NO_RECEIPT, reason)

    @classmethod
    def retry(cls, reason: str):
        return cls(OrderStatus.RETRY, reason)

    @classmethod
    def error(cls, reason: str):
        return cls(OrderStatus.ERROR, reason)
