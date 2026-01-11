"""
ページ操作ユーティリティ
責務: Playwright ページ操作の共通処理（待機、クリック、イベント監視）
"""

import asyncio
from app.utils.logger import log_debug, log_warning


class PageUtils:
    """Playwright ページ操作のユーティリティクラス"""

    DEFAULT_TIMEOUT = 30000  # 30秒

    @staticmethod
    async def wait_and_click(page, selector: str, timeout: int = None) -> bool:
        """
        要素が表示されるまで待機してからクリック

        Args:
            page: Playwright ページオブジェクト
            selector: CSSセレクタまたはテキストセレクタ
            timeout: タイムアウト（ミリ秒）

        Returns:
            bool: 成功した場合True
        """
        timeout = timeout or PageUtils.DEFAULT_TIMEOUT
        try:
            locator = page.locator(selector).first
            await locator.wait_for(state="visible", timeout=timeout)
            await locator.click()
            log_debug(f"クリック成功: {selector}")
            return True
        except Exception as e:
            log_warning(f"クリック失敗 ({selector}): {e}")
            return False

    @staticmethod
    async def wait_for_popup(page, click_action, timeout: int = None):
        """
        ポップアップ（新しいタブ）を待機しながらアクションを実行

        Args:
            page: Playwright ページオブジェクト
            click_action: ポップアップを開くアクション（async callable）
            timeout: タイムアウト（ミリ秒）

        Returns:
            新しいページオブジェクト、失敗時はNone
        """
        timeout = timeout or PageUtils.DEFAULT_TIMEOUT
        try:
            # イベントベースでポップアップを監視
            popup_future = asyncio.ensure_future(
                page.wait_for_event("popup", timeout=timeout)
            )

            # クリックアクションを実行
            await click_action()

            # ポップアップを待機
            new_page = await popup_future

            # ページの読み込みを待機
            await new_page.wait_for_load_state("domcontentloaded", timeout=timeout)
            log_debug(f"ポップアップ取得成功: {new_page.url}")
            return new_page

        except Exception as e:
            log_warning(f"ポップアップ待機失敗: {e}")
            return None

    @staticmethod
    async def wait_for_download(page, click_action, timeout: int = None):
        """
        ダウンロードイベントを待機しながらアクションを実行

        Args:
            page: Playwright ページオブジェクト
            click_action: ダウンロードを開始するアクション（async callable）
            timeout: タイムアウト（ミリ秒）

        Returns:
            ダウンロードオブジェクト、失敗時はNone
        """
        timeout = timeout or PageUtils.DEFAULT_TIMEOUT
        try:
            async with page.expect_download(timeout=timeout) as download_info:
                await click_action()

            download = await download_info.value
            log_debug(f"ダウンロード開始: {download.suggested_filename}")
            return download

        except Exception as e:
            log_warning(f"ダウンロード待機失敗: {e}")
            return None

    @staticmethod
    async def wait_for_navigation(page, click_action, timeout: int = None) -> bool:
        """
        ナビゲーション完了を待機しながらアクションを実行

        Args:
            page: Playwright ページオブジェクト
            click_action: ナビゲーションを開始するアクション（async callable）
            timeout: タイムアウト（ミリ秒）

        Returns:
            bool: 成功した場合True
        """
        timeout = timeout or PageUtils.DEFAULT_TIMEOUT
        try:
            async with page.expect_navigation(timeout=timeout):
                await click_action()

            await page.wait_for_load_state("networkidle", timeout=timeout)
            log_debug(f"ナビゲーション完了: {page.url}")
            return True

        except Exception as e:
            log_warning(f"ナビゲーション待機失敗: {e}")
            return False

    @staticmethod
    async def safe_fill(page, selector: str, value: str, timeout: int = None) -> bool:
        """
        要素が表示されるまで待機してから入力

        Args:
            page: Playwright ページオブジェクト
            selector: CSSセレクタ
            value: 入力する値
            timeout: タイムアウト（ミリ秒）

        Returns:
            bool: 成功した場合True
        """
        timeout = timeout or PageUtils.DEFAULT_TIMEOUT
        try:
            locator = page.locator(selector).first
            await locator.wait_for(state="visible", timeout=timeout)
            await locator.fill(value)
            log_debug(f"入力成功: {selector}")
            return True
        except Exception as e:
            log_warning(f"入力失敗 ({selector}): {e}")
            return False

    @staticmethod
    async def find_visible_element(page, selectors: list, timeout: int = 5000):
        """
        複数のセレクタから最初に見つかった可視要素を返す

        Args:
            page: Playwright ページオブジェクト
            selectors: セレクタのリスト
            timeout: 各セレクタのタイムアウト（ミリ秒）

        Returns:
            見つかった要素、見つからない場合はNone
        """
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if await locator.is_visible(timeout=timeout):
                    return locator
            except:
                continue
        return None
