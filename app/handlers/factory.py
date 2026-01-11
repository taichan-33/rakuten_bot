"""
OrderHandlerFactory
"""

from app.utils.logger import log_debug
from .base_handler import OrderHandler
from .books_handler import BooksOrderHandler
from .standard_handler import StandardOrderHandler


class OrderHandlerFactory:
    """URLに基づいて適切なハンドラを選択"""

    @staticmethod
    def create(page) -> OrderHandler:
        url = page.url

        if "books.rakuten.co.jp" in url:
            log_debug("BooksOrderHandler を選択")
            return BooksOrderHandler(page)
        else:
            log_debug("StandardOrderHandler を選択")
            return StandardOrderHandler(page)
