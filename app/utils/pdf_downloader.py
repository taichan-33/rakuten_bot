"""
PDFダウンローダー
責務: PDFファイルのダウンロード処理
"""

import asyncio
import os
from app.config import Config
from app.utils.logger import log_info, log_debug, log_warning
from app.utils.page_utils import PageUtils


class PdfDownloader:
    """PDFダウンロード専用クラス"""

    def __init__(self, page):
        self.page = page

    async def download_from_new_tab(
        self, click_action, order_id: str, check_modal: bool = True
    ) -> str:
        """
        新しいタブで開かれるPDFをダウンロード

        Args:
            click_action: PDFを開くクリックアクション（async callable）
            order_id: 注文ID
            check_modal: モーダルをチェックするかどうか

        Returns:
            保存したファイル名、失敗時は空文字列
        """
        # クリック前のページ数を記録
        initial_pages = len(self.page.context.pages)

        # クリックアクションを実行
        await click_action()

        # 少し待機
        await asyncio.sleep(2)

        # モーダルが表示された場合は確認ボタンをクリック
        if check_modal:
            await self._handle_modal()

        # 新しいタブを検出
        new_page = await self._detect_new_tab(initial_pages)
        if new_page:
            return await self._download_from_page(new_page, order_id)

        log_warning("新タブが検出されませんでした")
        return ""

    async def download_from_event(self, order_id: str, timeout: int = 10000) -> str:
        """
        ダウンロードイベントを待機してダウンロード

        Args:
            order_id: 注文ID
            timeout: タイムアウト（ミリ秒）

        Returns:
            保存したファイル名、失敗時は空文字列
        """
        try:
            async with self.page.expect_download(timeout=timeout) as download_info:
                await asyncio.sleep(1)

            download = await download_info.value
            filename = f"receipt_{order_id}.pdf"
            save_path = os.path.join(Config.DOWNLOAD_DIR, filename)
            await download.save_as(save_path)
            log_info(f"ダウンロード保存: {save_path}")
            return filename

        except Exception as e:
            log_warning(f"ダウンロード待機失敗: {e}")
            return ""

    async def _handle_modal(self):
        """モーダルが表示された場合は確認ボタンをクリック"""
        modal_selectors = [
            'button:has-text("OK")',
            'button:has-text("確認")',
            'button:has-text("はい")',
            ".modal button",
        ]
        modal_btn = await PageUtils.find_visible_element(
            self.page, modal_selectors, timeout=2000
        )
        if modal_btn:
            await modal_btn.click()
            log_info("モーダル確認ボタンクリック")
            await asyncio.sleep(2)

    async def _detect_new_tab(self, initial_count: int, max_wait: int = 5):
        """
        新しいタブを検出

        Args:
            initial_count: 初期のページ数
            max_wait: 最大待機時間（秒）

        Returns:
            新しいページ、見つからない場合はNone
        """
        for _ in range(max_wait):
            current_pages = self.page.context.pages
            if len(current_pages) > initial_count:
                return current_pages[-1]
            await asyncio.sleep(1)
        return None

    async def _download_from_page(self, page, order_id: str) -> str:
        """ページからPDFをダウンロード"""
        try:
            # ページの読み込みを待機
            await page.wait_for_load_state("load", timeout=120000)
            await asyncio.sleep(2)

            pdf_url = page.url
            log_debug(f"PDF URL: {pdf_url}")

            # PDFファイルを直接ダウンロード
            filename = f"receipt_{order_id}.pdf"
            save_path = os.path.join(Config.DOWNLOAD_DIR, filename)

            response = await page.context.request.get(pdf_url)
            if response.ok:
                pdf_content = await response.body()
                with open(save_path, "wb") as f:
                    f.write(pdf_content)
                log_info(f"PDF保存: {save_path} ({len(pdf_content)} bytes)")
                await page.close()
                return filename
            else:
                log_warning(f"PDF取得失敗: HTTP {response.status}")
                await page.close()
                return ""

        except Exception as e:
            log_warning(f"PDF保存エラー: {e}")
            try:
                await page.close()
            except:
                pass
            return ""
