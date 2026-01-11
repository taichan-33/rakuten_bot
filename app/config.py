import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    USER_ID = os.getenv("RAKUTEN_USER_ID")
    PASSWORD = os.getenv("RAKUTEN_PASSWORD")
    SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
    SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")
    HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
    DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads")
    RECEIPT_ADDRESSEE = os.getenv("RECEIPT_ADDRESSEE", "")
    PARALLEL_WORKERS = int(os.getenv("PARALLEL_WORKERS", "3"))

    # 日付フィルター（オプション）
    # フォーマット: YYYY-MM（例: 2024-01）
    # 空の場合は全期間を処理
    DATE_FILTER_FROM = os.getenv("DATE_FILTER_FROM", "")  # 開始年月
    DATE_FILTER_TO = os.getenv("DATE_FILTER_TO", "")  # 終了年月

    # URLs
    LOGIN_URL = "https://www.rakuten.co.jp/"
    PURCHASE_HISTORY_URL = "https://order.my.rakuten.co.jp/"

    @classmethod
    def validate(cls):
        if not cls.USER_ID or not cls.PASSWORD:
            raise ValueError(
                ".env ファイルに RAKUTEN_USER_ID と RAKUTEN_PASSWORD を設定してください。"
            )
        if not os.path.exists(cls.DOWNLOAD_DIR):
            os.makedirs(cls.DOWNLOAD_DIR)

    @classmethod
    def get_date_filter_info(cls) -> str:
        """日付フィルターの情報を返す"""
        if cls.DATE_FILTER_FROM or cls.DATE_FILTER_TO:
            return f"期間: {cls.DATE_FILTER_FROM or '開始'} 〜 {cls.DATE_FILTER_TO or '現在'}"
        return "期間: 全期間"

    @classmethod
    def is_date_filter_enabled(cls) -> bool:
        """日付フィルターが有効かどうか"""
        return bool(cls.DATE_FILTER_FROM or cls.DATE_FILTER_TO)
