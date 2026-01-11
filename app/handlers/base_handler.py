"""
注文処理ハンドラの基底クラス
"""

import asyncio
from abc import ABC, abstractmethod
from urllib.parse import urlparse, parse_qs
from app.config import Config
from app.models.order_status import IssueResult, OrderStatus
from app.utils.logger import log_info, log_debug, log_warning, log_error


class OrderHandler(ABC):
    """注文処理ハンドラの基底クラス"""

    def __init__(self, page):
        self.page = page

    @abstractmethod
    async def extract_order_ids(self) -> list:
        """一覧ページから注文番号を抽出"""
        pass

    @abstractmethod
    async def navigate_to_detail(self, order_id: str) -> bool:
        """注文詳細ページに遷移"""
        pass

    @abstractmethod
    async def issue_receipt(self, order_id: str) -> IssueResult:
        """領収書を発行"""
        pass

    # 共通メソッド
    async def _fill_addressee(self) -> bool:
        """宛名を入力（共通処理）"""
        already_issued = await self.page.locator(
            'text="一度発行済みのため"'
        ).is_visible()

        if already_issued:
            log_info("既に発行済み → 再発行")
            return False

        addressee = Config.RECEIPT_ADDRESSEE
        if not addressee:
            return False

        input_field = self.page.locator(
            'input[placeholder*="宛名"], input[placeholder*="楽天"]'
        ).first

        try:
            if await input_field.is_visible(timeout=2000):
                if await input_field.is_enabled():
                    await input_field.fill(addressee)
                    log_debug(f"宛名入力完了: {addressee}")
                    return True
        except:
            pass

        return False

    async def _click_confirm_modal(self) -> bool:
        """確認モーダルのOKボタンをクリック（共通処理）"""
        confirm_selectors = [
            'div.color-azure-light--2auXR:has-text("OK")',
            'a:has(div:has-text("OK"))',
            'button:has-text("OK")',
            'button:has-text("はい")',
            '[role="button"]:has-text("OK")',
        ]

        await asyncio.sleep(0.5)

        for selector in confirm_selectors:
            try:
                btn = self.page.locator(selector).first
                if await btn.is_visible(timeout=2000):
                    await btn.click(force=True)
                    log_debug(f"確認モーダルOKクリック: {selector}")
                    await asyncio.sleep(1)
                    return True
            except:
                continue

        return False

    def _parse_order_id_from_href(self, href: str) -> str:
        """hrefから注文番号を抽出"""
        order_id = ""
        if "order_number=" in href:
            parsed = urlparse(href)
            params = parse_qs(parsed.query)
            if "order_number" in params:
                order_id = params["order_number"][0]

        elif "/detail/" in href:
            parts = href.split("/detail/")
            if len(parts) > 1:
                order_id = parts[1].split("?")[0].split("/")[0]

        # バリデーション
        if order_id:
            import re

            if not re.match(r"^[\d-]+$", order_id):
                return ""
            if "-" not in order_id and len(order_id) < 15:
                return ""

        return order_id
