"""
注文処理オーケストレーター
責務: 注文処理の全体フロー制御、ページネーション、DB連携
"""

import asyncio
from app.config import Config
from app.core.db_manager import DBManager
from app.handlers import OrderHandlerFactory, BooksOrderHandler
from app.models.order_status import OrderStatus, IssueResult
from app.utils.logger import log_info, log_debug, log_warning, log_error, log_separator


class OrderProcessor:
    """注文処理のオーケストレーター"""

    MAX_ORDER_RETRY = 3  # 最大リトライ回数

    def __init__(self, page, db_manager: DBManager):
        self.page = page
        self.db = db_manager
        self.should_stop = lambda: False  # デフォルトは常にFalse

    async def process_all(self):
        """全ページの注文を処理"""
        log_separator()
        log_info("注文履歴を処理中...")

        total_processed = 0
        total_skipped = 0
        total_errors = 0
        page_num = 1

        # 最初のページに遷移（日付フィルター適用）
        await self._navigate_to_purchase_history()

        while True:
            if self.should_stop():
                log_info("終了がリクエストされました。処理を中断します。")
                break

            log_info(f"--- ページ {page_num} ---")

            # このページを処理
            processed, skipped, errors = await self._process_current_page()

            total_processed += processed
            total_skipped += skipped
            total_errors += errors

            # 次のページへ
            if not await self._go_to_next_page():
                log_info("最後のページに到達しました")
                break

            page_num += 1

        log_separator()
        log_info("全ページ処理完了:")
        log_info(f"  成功: {total_processed} 件")
        log_info(f"  スキップ: {total_skipped} 件")
        log_info(f"  エラー/リトライ: {total_errors} 件")

    async def _process_current_page(self) -> tuple:
        """現在のページの注文を処理"""
        # 現在のページURLを保存（詳細から戻る時に使用）
        self._current_list_url = self.page.url

        # 一覧ページでは Standard ハンドラで注文番号を抽出
        list_handler = OrderHandlerFactory.create(self.page)

        # 注文番号を抽出
        order_ids = await list_handler.extract_order_ids()

        if not order_ids:
            log_warning("このページに注文が見つかりませんでした。")
            return 0, 0, 0

        log_info(f"このページに {len(order_ids)} 件の注文を検出")

        processed = 0
        skipped = 0
        errors = 0

        for i, order_id in enumerate(order_ids):
            # DBチェック（遷移前に判定）
            if not self.db.should_process(order_id):
                status = self.db.get_order_status(order_id)
                log_info(f"[{i + 1}/{len(order_ids)}] スキップ ({status}): {order_id}")
                skipped += 1
                continue

            log_info(f"[{i + 1}/{len(order_ids)}] 処理中: {order_id}")

            try:
                # 現在の一覧ページに戻る（ページ番号を保持）
                await self._navigate_to_current_list_page()

                # Books判定（一覧ページで処理できるか確認）
                if await BooksOrderHandler.is_books_order(self.page, order_id):
                    log_info(f"Books注文検出(一覧処理): {order_id}")
                    handler = BooksOrderHandler(self.page)
                else:
                    # 詳細ページに遷移（汎用ナビゲーション）
                    if not await self._navigate_to_detail(order_id):
                        log_warning(f"詳細遷移失敗: {order_id}")
                        errors += 1
                        continue

                    # 詳細ページのURLでハンドラを選択
                    handler = OrderHandlerFactory.create(self.page)
                    log_debug(f"ハンドラ選択: {handler.__class__.__name__}")

                # 領収書発行（リトライ付き）
                result = await self._process_with_retry(handler, order_id, i + 1)

                if result.status == OrderStatus.DONE:
                    processed += 1
                elif result.status == OrderStatus.NO_RECEIPT:
                    skipped += 1
                else:
                    errors += 1

            except Exception as e:
                log_error(f"処理エラー: {e}")
                errors += 1

        return processed, skipped, errors

    async def _process_with_retry(
        self, handler, order_id: str, order_number: int
    ) -> IssueResult:
        """リトライ付き発行処理"""
        result = None

        for attempt in range(self.MAX_ORDER_RETRY):
            if attempt > 0:
                log_info(f"リトライ {attempt + 1}/{self.MAX_ORDER_RETRY}")
                await asyncio.sleep(2)

            result = await handler.issue_receipt(order_id)

            if result.status in [
                OrderStatus.DONE,
                OrderStatus.NO_RECEIPT,
                OrderStatus.ERROR,
            ]:
                self._update_db(order_id, result, order_number)
                return result

            if result.status == OrderStatus.RETRY:
                log_warning(f"リトライ対象: {result.error_message}")
                continue

        # 最大リトライ到達 → RETRYとして保存（次回実行時にまたリトライするため）
        # ただし、DBManager側で総リトライ回数が上限を超えたらERRORになる
        msg = f"{self.MAX_ORDER_RETRY}回リトライ失敗: {result.error_message if result else '不明'}"
        log_warning(f"最大リトライ回数到達: {order_id} -> 次回以降に持ち越し")

        final_result = IssueResult.retry(msg)

        self.db.update_order(
            order_id,
            OrderStatus.RETRY.value,
            error_message=final_result.error_message,
            increment_retry=True,  # ここでDBのretry_countを+1
            order_number=order_number,
        )
        return final_result

    def _update_db(self, order_id: str, result: IssueResult, order_number: int):
        """発行結果をDBに保存"""
        self.db.update_order(
            order_id,
            result.status.value,
            filename=getattr(result, "filename", None),
            error_message=result.error_message,
            order_number=order_number,
        )

    async def _navigate_to_purchase_history(self):
        """購入履歴ページ（1ページ目）に遷移（日付フィルター適用）"""
        url = Config.PURCHASE_HISTORY_URL

        # 日付フィルターが設定されている場合はURLに追加
        if Config.is_date_filter_enabled():
            params = []
            if Config.DATE_FILTER_FROM:
                # YYYY-MM形式からyear, monthを抽出
                parts = Config.DATE_FILTER_FROM.split("-")
                if len(parts) == 2:
                    params.append(f"year={parts[0]}")
                    params.append(f"month={parts[1]}")
            if params:
                url = f"{url}?{'&'.join(params)}"
                log_info(f"日付フィルター適用: {Config.DATE_FILTER_FROM}")

        await self.page.goto(url)
        await self.page.wait_for_load_state("networkidle")
        await asyncio.sleep(2)

    async def _navigate_to_current_list_page(self):
        """現在の一覧ページに戻る（ページ番号を保持）"""
        if hasattr(self, "_current_list_url") and self._current_list_url:
            await self.page.goto(self._current_list_url)
            await self.page.wait_for_load_state("networkidle")
            await asyncio.sleep(1)
        else:
            await self._navigate_to_purchase_history()

    async def _navigate_to_detail(self, order_id: str) -> bool:
        """注文詳細ページに遷移（汎用）"""
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
                    log_debug(f"詳細遷移: {selector}")
                    return True
            except:
                continue

        return False

    async def _go_to_next_page(self) -> bool:
        """次のページに遷移"""
        # ページネーションボタンを探す前に、確実に一覧ページに戻る
        await self._navigate_to_current_list_page()

        next_btn_selectors = [
            'a:has-text("次のページ")',  # 一般的
            'a:has-text("次へ")',
            'button[aria-label="Next page"]',
            'button[aria-label="next"]',
            'button[aria-label="次へ"]',
            "li.next a",
            ".pagination__next",
            'a[class*="pagination"][rel="next"]',
        ]

        for selector in next_btn_selectors:
            try:
                elements = await self.page.locator(selector).all()
                for btn in elements:
                    if await btn.is_visible():
                        # disabled チェック
                        class_attr = await btn.get_attribute("class") or ""
                        is_disabled = await btn.get_attribute("disabled")

                        if "disabled" in class_attr.lower() or is_disabled is not None:
                            continue

                        await btn.click(timeout=3000)
                        await self.page.wait_for_load_state("networkidle")
                        await asyncio.sleep(2)
                        self._current_list_url = self.page.url
                        log_info(
                            f"次のページへ遷移: {self._current_list_url} (selector: {selector})"
                        )
                        return True
            except:
                continue

        log_info("次のページが見つかりません（終了）")
        # デバッグ: HTML保存
        try:
            with open("debug_pagination_failed.html", "w", encoding="utf-8") as f:
                f.write(await self.page.content())
            log_info("デバッグ用HTMLを保存しました: debug_pagination_failed.html")
        except:
            pass

        return False
