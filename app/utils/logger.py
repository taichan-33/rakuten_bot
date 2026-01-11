"""
ログ管理モジュール
責務: ログのコンソール出力とファイル出力を一元管理
"""

import logging
import os
from datetime import datetime

# ログディレクトリ
LOG_DIR = os.path.join(os.getcwd(), "logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# ログファイル名 (日付付き)
LOG_FILE = os.path.join(LOG_DIR, f"app_{datetime.now().strftime('%Y%m%d')}.log")


# ロガー設定
def setup_logger(name: str = "rakuten_bot") -> logging.Logger:
    """ロガーを設定して返す"""
    logger = logging.getLogger(name)

    # 既に設定済みの場合はそのまま返す
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # フォーマット
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # コンソールハンドラ
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # ファイルハンドラ
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


# デフォルトロガー
logger = setup_logger()


def log_info(message: str):
    """情報ログ"""
    logger.info(message)


def log_debug(message: str):
    """デバッグログ (ファイルのみ)"""
    logger.debug(message)


def log_warning(message: str):
    """警告ログ"""
    logger.warning(message)


def log_error(message: str):
    """エラーログ"""
    logger.error(message)


def log_separator():
    """セパレータを出力"""
    logger.info("=" * 50)
