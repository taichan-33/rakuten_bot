"""
ログインフロー戦略クラス群
責務: 各ログイン方式の具体的な操作手順
"""

import asyncio
from abc import ABC, abstractmethod
from app.config import Config
from app.utils.logger import log_info, log_debug, log_warning


class LoginFlowStrategy(ABC):
    """ログインフロー戦略の基底クラス"""

    def __init__(self, page):
        self.page = page

    @abstractmethod
    async def execute(self) -> bool:
        """ログインフローを実行し、成功したかどうかを返す"""
        pass

    async def is_logged_in(self) -> bool:
        """ログイン成功判定"""
        return "login.account.rakuten.com" not in self.page.url


class LegacyLoginFlow(LoginFlowStrategy):
    """旧ログインフロー (input[name="u"], input[name="p"])"""

    async def execute(self) -> bool:
        log_info("旧ログインフローを実行します")
        try:
            # ユーザーID入力
            user_selector = 'input[name="u"]'
            if not await self.page.is_visible(user_selector):
                user_selector = 'input[id="loginInner_u"]'

            await self.page.fill(user_selector, Config.USER_ID)
            log_debug(f"ユーザーID入力完了: {user_selector}")

            # パスワード入力
            pass_selector = 'input[name="p"]'
            if not await self.page.is_visible(pass_selector):
                pass_selector = 'input[id="loginInner_p"]'

            await self.page.fill(pass_selector, Config.PASSWORD)
            log_debug("パスワード入力完了")

            # 送信
            await self.page.click('input[type="submit"]')
            await self.page.wait_for_load_state("networkidle")

            return await self.is_logged_in()

        except Exception as e:
            log_warning(f"旧ログインフローでエラー: {e}")
            return False


class GlobalIdLoginFlow(LoginFlowStrategy):
    """新ログインフロー (Rakuten Global ID)"""

    async def execute(self) -> bool:
        log_info("新ログインフロー(Global ID)を実行します")
        try:
            # ユーザー名入力
            user_selector = 'input[name="username"]'
            await self.page.fill(user_selector, Config.USER_ID)
            log_debug("ユーザー名入力完了")

            # 「次へ」ボタンをクリック
            await self._click_next_button()

            # パスワード欄の待機
            pass_selector = 'input[name="password"]'
            await self.page.wait_for_selector(
                pass_selector, state="visible", timeout=10000
            )

            # パスワード入力
            await self.page.fill(pass_selector, Config.PASSWORD)
            log_debug("パスワード入力完了")

            # 送信ボタンをクリック
            await self._click_submit_button(pass_selector)

            # ログイン成功確認
            return await self._wait_for_login_success()

        except Exception as e:
            log_warning(f"新ログインフローでエラー: {e}")
            return False

    async def _click_next_button(self):
        """次へボタンをクリック"""
        # ID または role based セレクター
        next_selectors = [
            "#cta011",  # 次へボタンのID
            '[id^="cta"]:has-text("次へ")',
            'div[role="button"]:has-text("次へ")',
            '[role="button"]:has-text("次へ")',
            'button:has-text("次へ")',
            'button:has-text("Next")',
        ]

        for selector in next_selectors:
            try:
                btn = self.page.locator(selector).first
                if await btn.is_visible(timeout=2000):
                    await btn.click(force=True)
                    log_debug(f"次へボタンをクリック: {selector}")
                    await asyncio.sleep(1)
                    return
            except:
                continue

        # フォールバック: Enterキー
        await self.page.press('input[name="username"]', "Enter")
        log_debug("Enterキーで次へ")
        await asyncio.sleep(1)

    async def _click_submit_button(self, pass_selector: str):
        """ログイン送信（Enterキーを使用）"""
        await self.page.press(pass_selector, "Enter")
        log_debug("Enterキーで送信")
        await asyncio.sleep(2)

    async def _wait_for_login_success(self, max_wait: int = 10) -> bool:
        """ログイン成功を待機"""
        for _ in range(max_wait // 2):
            if await self.is_logged_in():
                log_info("ログイン成功を検出しました")
                return True
            await asyncio.sleep(2)

        # まだログインページにいる場合、Enterキーで再試行
        if not await self.is_logged_in():
            log_info("まだログインページにいます。Enterキーで再試行...")
            await self.page.press('input[name="password"]', "Enter")
            await asyncio.sleep(3)

        return await self.is_logged_in()
