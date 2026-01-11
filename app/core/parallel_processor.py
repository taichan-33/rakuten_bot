"""
並列注文処理クラス（ページ単位）
責務: 各ワーカーが異なるページを担当して並列処理
"""

import asyncio
from app.config import Config
from app.core.db_manager import DBManager
from app.handlers import OrderHandlerFactory, StandardOrderHandler, BooksOrderHandler
from app.models.order_status import OrderStatus, IssueResult
from app.utils.logger import log_info, log_debug, log_warning, log_error, log_separator


class ParallelOrderProcessor:
    """ページ単位で注文を並列処理"""

    def __init__(self, worker_pages: list, db_manager: DBManager):
        self.worker_pages = worker_pages
        self.db = db_manager
        self.worker_count = len(worker_pages)
        self.should_stop = lambda: False  # デフォルトは常にFalse

    async def process_all(self):
        """全ワーカーで並列処理開始"""
        log_separator()
        log_info(f"並列処理開始 (ワーカー数: {self.worker_count})")

        # 各ワーカーを起動（それぞれ異なるページを処理）
        tasks = []
        for worker_id in range(self.worker_count):
            page = self.worker_pages[worker_id]
            task = self._worker_loop(worker_id, page)
            tasks.append(task)

        # 全ワーカーの完了を待機
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 結果集計
        total_processed = 0
        total_skipped = 0
        total_errors = 0

        for result in results:
            if isinstance(result, Exception):
                log_error(f"ワーカーエラー: {result}")
                total_errors += 1
            else:
                processed, skipped, errors = result
                total_processed += processed
                total_skipped += skipped
                total_errors += errors

        log_separator()
        log_info("全ワーカー処理完了:")
        log_info(f"  成功: {total_processed} 件")
        log_info(f"  スキップ: {total_skipped} 件")
        log_info(f"  エラー: {total_errors} 件")

    async def _worker_loop(self, worker_id: int, page) -> tuple:
        """ワーカーのメインループ - 担当ページを順次処理"""
        processed = 0
        skipped = 0
        errors = 0

        # 最初のページに遷移
        try:
            await page.goto(Config.PURCHASE_HISTORY_URL, timeout=30000)
            await page.wait_for_load_state("domcontentloaded", timeout=15000)
        except Exception as e:
            log_warning(f"[W{worker_id}] 初期ページ読み込みタイムアウト: {e}")
        await asyncio.sleep(2)

        # 担当ページまでスキップ（Worker 0 → page 1, Worker 1 → page 2...）
        for _ in range(worker_id):
            if not await self._go_to_next_page(page):
                log_info(f"[W{worker_id}] 担当ページなし - 終了")
                return processed, skipped, errors
            await asyncio.sleep(1)

        page_num = worker_id + 1

        while True:
            if self.should_stop():
                log_info(f"[W{worker_id}] 終了がリクエストされました")
                break

            log_info(f"[W{worker_id}] ページ {page_num} 処理中...")

            # 現在のページを処理
            p, s, e = await self._process_page(worker_id, page)
            processed += p
            skipped += s
            errors += e

            # 次の担当ページへ（worker_count ページ分スキップ）
            moved = False
            for _ in range(self.worker_count):
                if not await self._go_to_next_page(page):
                    log_info(f"[W{worker_id}] 最終ページ到達")
                    return processed, skipped, errors
                await asyncio.sleep(0.5)
                moved = True

            if not moved:
                break

            page_num += self.worker_count

        return processed, skipped, errors

    async def _process_page(self, worker_id: int, page) -> tuple:
        """1ページ分の注文を処理"""
        processed = 0
        skipped = 0
        errors = 0

        # 現在のページURLを保存
        current_url = page.url

        # 注文番号を抽出
        handler = StandardOrderHandler(page)
        order_ids = await handler.extract_order_ids()

        if not order_ids:
            return 0, 0, 0

        for order_id in order_ids:
            # DBチェック
            if not self.db.should_process(order_id):
                skipped += 1
                continue

            log_debug(f"[W{worker_id}] 処理: {order_id}")

            try:
                # 現在のページに戻る
                await page.goto(current_url)
                # networkidle -> domcontentloaded に緩和
                await page.wait_for_load_state("domcontentloaded")
                await asyncio.sleep(0.5)

                # Books判定（一覧ページで処理できるか確認）
                if await BooksOrderHandler.is_books_order(page, order_id):
                    log_debug(f"[W{worker_id}] Books注文検出(一覧処理): {order_id}")
                    issue_handler = BooksOrderHandler(page)
                else:
                    # 詳細ページに遷移
                    if not await self._navigate_to_detail(page, order_id):
                        log_warning(f"[W{worker_id}] 遷移失敗: {order_id}")
                        errors += 1
                        continue

                    # ハンドラ選択
                    issue_handler = OrderHandlerFactory.create(page)

                # 発行処理
                result = await issue_handler.issue_receipt(order_id)

                # DB更新
                self.db.update_order(
                    order_id,
                    result.status.value,
                    filename=getattr(result, "filename", None),
                    error_message=result.error_message,
                )

                if result.status == OrderStatus.DONE:
                    log_info(f"[W{worker_id}] 完了: {order_id}")
                    processed += 1
                elif result.status == OrderStatus.NO_RECEIPT:
                    skipped += 1
                else:
                    errors += 1

            except Exception as e:
                log_error(f"[W{worker_id}] エラー: {order_id} - {e}")
                errors += 1

        # 処理完了後、確実に一覧ページに戻る（ページネーションのため）
        try:
            if page.url != current_url:
                await page.goto(current_url)
                await page.wait_for_load_state("domcontentloaded")
                await asyncio.sleep(1)
        except Exception as e:
            log_warning(f"[W{worker_id}] 一覧ページ復帰エラー: {e}")

        return processed, skipped, errors

    async def _navigate_to_detail(self, page, order_id: str) -> bool:
        """注文詳細ページに遷移"""
        selectors = [
            f'a[href*="order_number={order_id}"]',
            f'a[href*="/detail/{order_id}"]',
        ]

        for selector in selectors:
            try:
                link = page.locator(selector).first
                if await link.is_visible(timeout=2000):
                    await link.click()
                    await page.wait_for_load_state("domcontentloaded")
                    await asyncio.sleep(1)
                    return True
            except:
                continue

        return False

    async def _go_to_next_page(self, page) -> bool:
        """次のページに遷移"""
        selectors = [
            'a:has-text("次のページ")',  # 一般的
            'a:has-text("次へ")',
            'button[aria-label="Next page"]',
            'button[aria-label="next"]',
            'button[aria-label="次へ"]',
            "li.next a",
            ".pagination__next",
            'a[class*="pagination"][rel="next"]',
        ]

        for selector in selectors:
            try:
                # 複数ある可能性があるので全件チェック
                elements = await page.locator(selector).all()
                for btn in elements:
                    if await btn.is_visible():
                        # disabled チェック
                        class_attr = await btn.get_attribute("class") or ""
                        is_disabled = await btn.get_attribute("disabled")

                        if "disabled" in class_attr.lower() or is_disabled is not None:
                            continue

                        # クリック
                        try:
                            await btn.click(timeout=3000)
                            await page.wait_for_load_state("domcontentloaded")
                            await asyncio.sleep(2)
                            log_info(f"次のページへ遷移: {selector}")
                            return True
                        except:
                            continue
            except:
                continue

        log_info("次のページが見つかりません（終了）")

        # デバッグ: HTMLを保存
        try:
            with open("debug_pagination_failed.html", "w", encoding="utf-8") as f:
                f.write(await page.content())
            log_info("デバッグ用HTMLを保存しました: debug_pagination_failed.html")
        except:
            pass

        return False
