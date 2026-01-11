"""
メインエントリーポイント
責務: アプリケーション全体の起動と制御
"""

import asyncio
import signal
from app.config import Config
from app.core.browser_manager import BrowserManager
from app.core.authenticator import Authenticator
from app.core.order_processor import OrderProcessor
from app.core.parallel_processor import ParallelOrderProcessor
from app.core.db_manager import DBManager
from app.utils.logger import log_info, log_warning, log_error, log_separator
from app.utils.slack_notifier import SlackNotifier


class RakutenBotApp:
    def __init__(self):
        Config.validate()
        self.browser_manager = BrowserManager()
        self.db_manager = DBManager()
        self.slack_notifier = SlackNotifier(Config.SLACK_WEBHOOK_URL)
        self._shutdown_requested = False

    def _setup_signal_handlers(self):
        """Ctrl+C で安全に終了するためのハンドラを設定"""

        def signal_handler(signum, frame):
            if not self._shutdown_requested:
                self._shutdown_requested = True
                log_warning("終了シグナルを受信しました。安全に終了します...")

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    @property
    def should_stop(self) -> bool:
        """終了が要求されているかどうか"""
        return self._shutdown_requested

    async def run(self):
        from datetime import datetime

        # DBのフォーマットに合わせる ("%Y-%m-%d %H:%M:%S")
        start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self._setup_signal_handlers()

        log_separator()
        log_info("楽天請求書ダウンロードBot 起動")
        log_info(Config.get_date_filter_info())
        log_separator()

        try:
            # セットアップ
            page = await self.browser_manager.launch()

            # 認証
            auth = Authenticator(page)
            await auth.login()

            if self.should_stop:
                log_info("終了がリクエストされました")
                return

            # 並列処理モード判定
            if Config.PARALLEL_WORKERS > 1:
                await self._run_parallel(page)
            else:
                await self._run_sequential(page)

            # レポート出力
            self.db_manager.export_report(since=start_time)

        except Exception as e:
            log_error(f"アプリケーションエラーが発生しました: {e}")
        finally:
            # 完了・中断・エラーに関わらずレポートを出力
            try:
                self.db_manager.export_report(since=start_time)

                # Slack通知
                summary = self.db_manager.get_summary(since=start_time)
                self.slack_notifier.send_report(summary, "report.csv")

            except Exception as ex:
                log_error(f"レポート出力/通知失敗: {ex}")

            self._cleanup()

    def _cleanup(self):
        """安全なクリーンアップ処理"""
        log_info("クリーンアップ中...")
        try:
            # DBを閉じる
            self.db_manager.close()
        except:
            pass
        log_separator()
        log_info("Bot 終了")
        log_separator()

    async def _run_sequential(self, page):
        """逐次処理モード"""
        processor = OrderProcessor(page, self.db_manager)
        processor.should_stop = lambda: self.should_stop
        await processor.process_all()

    async def _run_parallel(self, page):
        """並列処理モード"""
        log_info(f"並列処理モード: {Config.PARALLEL_WORKERS} ワーカー")

        # ワーカーページを作成
        worker_pages = await self.browser_manager.create_worker_pages()

        # 各ワーカーでログイン
        for i, worker_page in enumerate(worker_pages):
            if self.should_stop:
                return
            log_info(f"ワーカー {i} ログイン中...")
            worker_auth = Authenticator(worker_page)
            await worker_auth.login()

        # 並列処理開始
        processor = ParallelOrderProcessor(worker_pages, self.db_manager)
        processor.should_stop = lambda: self.should_stop
        await processor.process_all()


async def main():
    app = RakutenBotApp()
    try:
        await app.run()
    finally:
        await app.browser_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
