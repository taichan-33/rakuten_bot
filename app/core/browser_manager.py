from playwright.async_api import async_playwright
from app.config import Config


class BrowserManager:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.contexts = []
        self.pages = []
        # メインページ（後方互換性用）
        self.context = None
        self.page = None

    async def launch(self):
        """ブラウザを起動しメインページを返す"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=Config.HEADLESS)

        # メインコンテキスト・ページを作成
        self.context = await self._create_context()
        self.page = await self.context.new_page()
        self._setup_download_handler(self.page)

        return self.page

    async def create_worker_pages(self, count: int = None):
        """並列処理用のページを作成"""
        if count is None:
            count = Config.PARALLEL_WORKERS

        self.contexts = []
        self.pages = []

        for _ in range(count):
            ctx = await self._create_context()
            page = await ctx.new_page()
            self._setup_download_handler(page)
            self.contexts.append(ctx)
            self.pages.append(page)

        return self.pages

    async def _create_context(self):
        """新しいコンテキストを作成"""
        return await self.browser.new_context(accept_downloads=True)

    def _setup_download_handler(self, page):
        """ダウンロードハンドラを設定"""
        page.on("download", lambda download: self._handle_download(download))

    def _handle_download(self, download):
        """ダウンロードを指定フォルダに保存"""
        import asyncio

        asyncio.create_task(self._save_download(download))

    async def _save_download(self, download):
        """非同期でダウンロードを保存"""
        import os

        filename = download.suggested_filename
        save_path = os.path.join(Config.DOWNLOAD_DIR, filename)
        await download.save_as(save_path)
        print(f"ダウンロード保存: {save_path}")

    async def close(self):
        # ワーカーコンテキストをクローズ
        for ctx in self.contexts:
            try:
                await ctx.close()
            except:
                pass

        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
