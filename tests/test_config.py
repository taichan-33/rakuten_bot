"""
Configのテスト
"""

import pytest
import tempfile
import os
from unittest.mock import patch


def test_validates_missing_credentials():
    """認証情報不足で例外を投げる"""
    from app.config import Config

    with patch.object(Config, "USER_ID", None), patch.object(Config, "PASSWORD", None):
        with pytest.raises(ValueError):
            Config.validate()


def test_creates_download_dir():
    """ダウンロードディレクトリを作成する"""
    from app.config import Config

    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = os.path.join(tmpdir, "test_downloads")

        with patch.object(Config, "USER_ID", "user"), patch.object(
            Config, "PASSWORD", "pass"
        ), patch.object(Config, "DOWNLOAD_DIR", test_dir):

            Config.validate()
            assert os.path.exists(test_dir)


def test_date_filter_info_with_from():
    """日付フィルター情報（開始のみ）"""
    from app.config import Config

    with patch.object(Config, "DATE_FILTER_FROM", "2024-01"), patch.object(
        Config, "DATE_FILTER_TO", ""
    ):
        info = Config.get_date_filter_info()
        assert "2024-01" in info


def test_date_filter_info_without_filter():
    """日付フィルター情報（フィルターなし）"""
    from app.config import Config

    with patch.object(Config, "DATE_FILTER_FROM", ""), patch.object(
        Config, "DATE_FILTER_TO", ""
    ):
        info = Config.get_date_filter_info()
        assert "全期間" in info


def test_is_date_filter_enabled_true():
    """日付フィルター有効判定"""
    from app.config import Config

    with patch.object(Config, "DATE_FILTER_FROM", "2024-01"), patch.object(
        Config, "DATE_FILTER_TO", ""
    ):
        assert Config.is_date_filter_enabled() is True


def test_is_date_filter_disabled():
    """日付フィルター無効判定"""
    from app.config import Config

    with patch.object(Config, "DATE_FILTER_FROM", ""), patch.object(
        Config, "DATE_FILTER_TO", ""
    ):
        assert Config.is_date_filter_enabled() is False
