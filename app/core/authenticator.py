"""
認証管理クラス
責務: ログインプロセス全体の制御（戦略選択、リトライ、ポップアップ処理）
"""

import asyncio
from app.config import Config
from app.core.retry_handler import RetryHandler
from app.core.login_flows import LegacyLoginFlow, GlobalIdLoginFlow
from app.utils.logger import log_info, log_debug, log_warning, log_error


class Authenticator:
    """ログイン処理を統括するクラス"""

    def __init__(self, page):
        self.page = page
        self.retry_handler = RetryHandler(max_attempts=3, delay_seconds=2.0)

    async def login(self):
        """ログイン処理のメインエントリーポイント"""
        log_info("ログイン中...")

        # 購入履歴ページへアクセス（ログインリダイレクトを誘発）
        await self._navigate_to_login()

        # ログインフローを検出して実行
        success = await self._execute_login_with_retry()

        if success:
            log_info("ログインシーケンス完了")
            await self._post_login_wait()
            await self._close_popups()
        else:
            log_warning("ログインに失敗した可能性があります")
            log_debug(f"現在のURL: {self.page.url}")

    async def _navigate_to_login(self):
        """ログインページへ遷移"""
        await self.page.goto(Config.LOGIN_URL)
        await self.page.goto(Config.PURCHASE_HISTORY_URL)
        await self.page.wait_for_load_state("domcontentloaded")
        await self.page.wait_for_load_state("networkidle")

    async def _execute_login_with_retry(self) -> bool:
        """リトライ付きでログインを実行"""
        # ログインフォームを検出
        flow = await self._detect_login_flow()

        if flow is None:
            log_info("ログインフォームが見つかりませんでした（既にログイン済み？）")
            log_debug(f"現在のURL: {self.page.url}")
            return "login.account.rakuten.com" not in self.page.url

        # リトライ付きで実行
        return await self.retry_handler.execute(
            action=flow.execute, success_check=flow.is_logged_in, action_name="ログイン"
        )

    async def _detect_login_flow(self):
        """ログインフォームの種類を検出し、適切な戦略を返す"""
        selectors_and_flows = [
            ('input[name="username"]', GlobalIdLoginFlow),
            ('input[name="u"]', LegacyLoginFlow),
            ('input[id="loginInner_u"]', LegacyLoginFlow),
        ]

        for selector, flow_class in selectors_and_flows:
            try:
                if await self.page.is_visible(selector, timeout=2000):
                    log_info(f"ログインフォーム検出: {selector}")
                    return flow_class(self.page)
            except:
                continue

        return None

    async def _post_login_wait(self):
        """ログイン後の待機処理"""
        log_info("ページ読み込み待機中...")
        await asyncio.sleep(3)
        try:
            await self.page.wait_for_load_state("networkidle", timeout=15000)
        except:
            log_warning("ページ読み込みタイムアウト、続行します")
        log_info(f"ログイン後のURL: {self.page.url}")

    async def _close_popups(self):
        """一般的なポップアップを閉じる"""
        close_selectors = [
            'button[class*="close"]',
            'div[class*="modal"] .close',
        ]
        for selector in close_selectors:
            try:
                if await self.page.is_visible(selector, timeout=1000):
                    await self.page.click(selector)
                    log_debug(f"ポップアップを閉じました: {selector}")
            except:
                pass
