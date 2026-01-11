"""
BooksOrderHandler
"""

import asyncio
from app.models.order_status import IssueResult
from app.utils.logger import log_info, log_debug, log_warning, log_error
from .base_handler import OrderHandler


class BooksOrderHandler(OrderHandler):
    """楽天ブックス用ハンドラ"""

    async def extract_order_ids(self) -> list:
        """一覧ページから注文番号を抽出"""
        order_ids = []

        # ブックスの注文リンク
        detail_links = self.page.locator(
            'a[href*="order_number="], a.status-info__receipt-link'
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
        ]

        for selector in link_selectors:
            try:
                link = self.page.locator(selector).first
                if await link.is_visible(timeout=2000):
                    await link.click()
                    await self.page.wait_for_load_state("networkidle")
                    await asyncio.sleep(1)
                    log_debug(f"[Books] 詳細遷移: {selector}")
                    return True
            except:
                continue

        return False

    @staticmethod
    async def is_books_order(page, order_id: str) -> bool:
        """一覧ページ上でBooksの領収書リンクを持っているか判定"""
        # ユーザー情報より: id="order_id" のdiv要素の中に a.status-info__receipt-link がある
        try:
            selector = f"#{order_id} .status-info__receipt-link, #{order_id} a[href^='javascript:postReceipt']"
            return await page.locator(selector).count() > 0
        except:
            return False

    async def issue_receipt(self, order_id: str) -> IssueResult:
        """領収書を発行"""
        try:
            log_info(f"[Books] 処理開始: {order_id} (URL: {self.page.url})")

            # 1. 領収書リンクをクリック
            if not await self._click_receipt_link(order_id):
                return IssueResult.no_receipt(
                    "領収書リンクが見つからない(リトライ停止)"
                )

            await self.page.wait_for_load_state("networkidle")
            await asyncio.sleep(3)  # 遷移待ち

            # デバッグ: 現在の状態を確認
            log_info(f"[Books] リンククリック後のURL: {self.page.url}")
            pages = self.page.context.pages
            log_info(f"[Books] 開いているページ数: {len(pages)}")

            # もし新しいページが開いていたら、そちらに切り替える必要があるかも
            if len(pages) > 1 and pages[-1] != self.page:
                new_page_opened = True
                log_info(
                    "[Books] 新しいページを検出しました。そちらを操作対象にします。"
                )
                self.page = pages[-1]

                # URLが有効になるまで待機
                for _ in range(60):
                    try:
                        if self.page.url and self.page.url != "about:blank":
                            break
                    except:
                        pass
                    await asyncio.sleep(0.5)

                try:
                    await self.page.wait_for_load_state(
                        "domcontentloaded", timeout=30000
                    )
                    await self.page.wait_for_load_state("networkidle", timeout=30000)
                except:
                    log_warning(
                        "[Books] ページロード待機タイムアウト（処理は継続します）"
                    )

                log_info(f"[Books] 操作対象ページ切り替え完了: {self.page.url}")

            # 2. 発行ボタンを待機
            btn = await self._wait_for_issue_button()
            if not btn:
                # デバッグ用HTML保存
                try:
                    with open(f"debug_books_failed_{order_id}.html", "w") as f:
                        f.write(await self.page.content())
                    log_info(f"デバッグHTML保存: debug_books_failed_{order_id}.html")
                except:
                    pass

                return IssueResult.no_receipt(
                    f"領収書発行ボタンが見つからない on {self.page.url}"
                )

            # 3. ポップアップ制御とダウンロード
            return await self._handle_popup_and_download(btn, order_id)

        except Exception as e:
            import traceback

            log_error(f"[Books] 詳細エラー: {traceback.format_exc()}")
            return IssueResult.error(f"エラー: {str(e)[:100]}")

        finally:
            if "new_page_opened" in locals() and new_page_opened:
                try:
                    if not self.page.is_closed():
                        log_info("[Books] 操作したページを閉じます")
                        await self.page.close()
                except:
                    pass

    async def _wait_for_issue_button(self):
        """領収書発行ボタンを待機して取得"""
        # ユーザー情報: input[value='領収書発行']
        btn_selector = "#receiptInputFormButton, button:has-text('発行する'), input[value='発行する'], input[value='領収書発行']"
        try:
            # first() で特定し、wait_for で可視化を待つ
            locator = self.page.locator(btn_selector).first
            await locator.wait_for(state="visible", timeout=60000)
            return locator
        except Exception as e:
            log_error(f"[Books] 発行ボタン待機中にエラー(wait_for): {str(e)}")
            return None

    async def _handle_popup_and_download(self, btn, order_id: str) -> IssueResult:
        """ポップアップを開いてPDFを保存"""
        log_info("[Books] 領収書発行ボタンをクリックします")

        try:
            async with self.page.expect_popup() as popup_info:
                await btn.click()

            page2 = await popup_info.value
            await page2.wait_for_load_state("networkidle")

            result = await self._save_pdf_from_popup(page2, order_id)
            await page2.close()
            return result
        except Exception as e:
            import traceback

            log_error(f"[Books] ポップアップエラー: {traceback.format_exc()}")
            # PDF取得失敗はリトライ対象にする
            return IssueResult.retry(f"PDF取得プロセスエラー: {str(e)[:100]}")

    async def _save_pdf_from_popup(self, page, order_id: str) -> IssueResult:
        """ポップアップページからPDFを保存"""
        from app.utils.pdf_downloader import PdfDownloader
        import os
        from app.config import Config

        pdf_url = page.url
        log_info(f"[Books] PDFページ取得: {pdf_url}")

        filename = f"receipt_{order_id}.pdf"
        save_path = os.path.join(Config.DOWNLOAD_DIR, filename)

        # 1. 直接PDF URLの場合 via request
        if pdf_url.lower().endswith(".pdf"):
            try:
                response = await page.request.get(pdf_url)
                if response.ok:
                    data = await response.body()
                    with open(save_path, "wb") as f:
                        f.write(data)
                    log_info(f"領収書保存完了: {filename}")
                    return IssueResult.success(filename)
            except:
                pass

        # 2. Fallback (PdfDownloader)
        downloader = PdfDownloader(page)
        saved_file = await downloader._download_from_page(page, order_id)

        if saved_file:
            return IssueResult.success(saved_file)

        return IssueResult.retry("PDFの保存に失敗しました")

    async def _click_receipt_link(self, order_id: str = None) -> bool:
        """領収書リンクをクリック"""
        # ページ読み込みを待機
        await self.page.wait_for_load_state("networkidle")
        await asyncio.sleep(2)

        selectors = []

        # order_idがある場合はスコープ付きセレクタを優先
        if order_id:
            selectors.extend(
                [
                    f"#{order_id} .status-info__receipt-link",
                    f"#{order_id} a[href^='javascript:postReceipt']",
                ]
            )

        # 汎用セレクタ（詳細ページやフォールバック用）
        selectors.extend(
            [
                'a[href^="javascript:postReceipt"]',
                ".status-info__receipt-link",
                'a:has-text("領収書を発行する")',
                'a:has-text("領収書")',
                'button:has-text("領収書")',
                '[data-testid="receipt-link"]',
            ]
        )

        for selector in selectors:
            try:
                element = self.page.locator(selector).first
                if await element.is_visible(timeout=5000):  # 探索は短めに
                    await element.click()
                    log_info(f"[Books] 領収書リンククリック: {selector}")
                    await asyncio.sleep(2)
                    return True
            except:
                continue

        log_warning("[Books] 領収書リンクが見つからない")
        return False
