"""
StandardOrderHandler
"""

import asyncio
from app.models.order_status import IssueResult
from app.utils.logger import log_info, log_debug
from .base_handler import OrderHandler


class StandardOrderHandler(OrderHandler):
    """通常の楽天ショップ用ハンドラ"""

    async def extract_order_ids(self) -> list:
        """一覧ページから注文番号を抽出"""
        order_ids = []

        detail_links = self.page.locator(
            'a[href*="order_number="], a[href*="/detail/"]'
        )
        count = await detail_links.count()

        for i in range(count):
            try:
                link = detail_links.nth(i)
                href = await link.get_attribute("href")

                if href:
                    order_id = self._parse_order_id_from_href(href)
                    if order_id and order_id not in order_ids:
                        order_ids.append(order_id)
            except:
                continue

        return order_ids

    async def navigate_to_detail(self, order_id: str) -> bool:
        """注文詳細ページに遷移"""
        link_selectors = [
            f'a[href*="order_number={order_id}"]',
            f'a[href*="/detail/{order_id}"]',
        ]

        for selector in link_selectors:
            try:
                link = self.page.locator(selector).first
                if await link.is_visible(timeout=2000):
                    await link.click()
                    await self.page.wait_for_load_state("networkidle")
                    await asyncio.sleep(1)
                    log_debug(f"[Standard] 詳細遷移: {selector}")
                    return True
            except:
                continue

        return False

    async def issue_receipt(self, order_id: str) -> IssueResult:
        """領収書を発行"""
        try:
            # 1. 領収書セクションをクリック
            if not await self._click_receipt_section():
                # 30秒(デフォルト等)探しても見つからなければ、発行不可とみなす
                return IssueResult.no_receipt(
                    "領収書セクションが見つからない(リトライ停止)"
                )

            # 2. 宛名入力
            needs_confirm = await self._fill_addressee()

            # 3. 発行ボタンをクリック
            if not await self._click_issue_button():
                return IssueResult.no_receipt("発行ボタンが見つからない(リトライ停止)")

            # 4. 確認モーダル
            if needs_confirm:
                await self._click_confirm_modal()

            await asyncio.sleep(3)
            log_info(f"領収書発行完了: {order_id}")
            return IssueResult.success(f"receipt_{order_id}.pdf")

        except asyncio.TimeoutError:
            return IssueResult.retry("タイムアウト")
        except Exception as e:
            return IssueResult.error(f"エラー: {str(e)[:100]}")

    async def _click_receipt_section(self) -> bool:
        """領収書セクションをクリック"""
        selectors = [
            'span:has-text("領収書")',
            'text="領収書"',
            'text="領収書・請求書"',
            'a:has-text("領収書")',
        ]

        for selector in selectors:
            try:
                element = self.page.locator(selector).first
                if await element.is_visible(timeout=10000):  # 10秒に延長
                    await element.click()
                    log_info(f"[Standard] 領収書セクションクリック: {selector}")
                    await asyncio.sleep(1)
                    return True
            except:
                continue

        return False

    async def _click_issue_button(self) -> bool:
        """発行ボタンをクリック"""
        selectors = [
            'button[aria-label="発行する"]',
            'button:has-text("発行する")',
            'span:has-text("発行する")',
        ]

        for selector in selectors:
            try:
                btn = self.page.locator(selector).first
                if await btn.is_visible(timeout=10000):  # 10秒に延長
                    await btn.click()
                    log_info("発行ボタンをクリック")
                    await asyncio.sleep(1)
                    return True
            except:
                continue

        return False
