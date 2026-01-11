"""
メインアプリケーションのテスト
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch


def test_rakuten_bot_app_init():
    """アプリケーション初期化"""
    with patch("app.main.Config") as mock_config, patch(
        "app.main.BrowserManager"
    ) as mock_browser, patch("app.main.DBManager") as mock_db:
        mock_config.validate = MagicMock()

        from app.main import RakutenBotApp

        app = RakutenBotApp()

        mock_config.validate.assert_called_once()
        assert app._shutdown_requested is False


def test_should_stop_default():
    """should_stop のデフォルト値"""
    with patch("app.main.Config") as mock_config, patch(
        "app.main.BrowserManager"
    ) as mock_browser, patch("app.main.DBManager") as mock_db:
        mock_config.validate = MagicMock()

        from app.main import RakutenBotApp

        app = RakutenBotApp()

        assert app.should_stop is False


def test_should_stop_after_shutdown_request():
    """終了リクエスト後のshould_stop"""
    with patch("app.main.Config") as mock_config, patch(
        "app.main.BrowserManager"
    ) as mock_browser, patch("app.main.DBManager") as mock_db:
        mock_config.validate = MagicMock()

        from app.main import RakutenBotApp

        app = RakutenBotApp()
        app._shutdown_requested = True

        assert app.should_stop is True


def test_cleanup_calls_db_close():
    """クリーンアップでDB closeが呼ばれる"""
    with patch("app.main.Config") as mock_config, patch(
        "app.main.BrowserManager"
    ) as mock_browser, patch("app.main.DBManager") as mock_db:
        mock_config.validate = MagicMock()

        from app.main import RakutenBotApp

        app = RakutenBotApp()
        app._cleanup()

        app.db_manager.close.assert_called_once()
