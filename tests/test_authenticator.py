"""
Authenticatorのテスト
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock


@pytest.fixture
def mock_page():
    page = AsyncMock()
    type(page).url = PropertyMock(return_value="https://login.account.rakuten.com/")
    page.title = AsyncMock(return_value="ログイン")
    return page


@pytest.mark.asyncio
async def test_navigates_to_login_page(mock_page):
    """ログインページへ遷移する"""
    from app.core.authenticator import Authenticator

    with patch("app.core.authenticator.Config") as MockConfig:
        MockConfig.LOGIN_URL = "https://www.rakuten.co.jp/"
        MockConfig.PURCHASE_HISTORY_URL = "https://order.my.rakuten.co.jp/"

        auth = Authenticator(mock_page)
        await auth._navigate_to_login()

        mock_page.goto.assert_any_call("https://www.rakuten.co.jp/")


@pytest.mark.asyncio
async def test_detects_global_id_flow(mock_page):
    """Global IDログインフォームを検出する"""
    from app.core.authenticator import Authenticator

    mock_page.is_visible = AsyncMock(side_effect=[True, False, False])

    auth = Authenticator(mock_page)
    flow = await auth._detect_login_flow()

    assert flow is not None
    assert "GlobalIdLoginFlow" in type(flow).__name__


@pytest.mark.asyncio
async def test_detects_legacy_flow(mock_page):
    """旧ログインフォームを検出する"""
    from app.core.authenticator import Authenticator

    mock_page.is_visible = AsyncMock(side_effect=[False, True, False])

    auth = Authenticator(mock_page)
    flow = await auth._detect_login_flow()

    assert flow is not None
    assert "LegacyLoginFlow" in type(flow).__name__


@pytest.mark.asyncio
async def test_returns_none_when_no_login_form(mock_page):
    """ログインフォームがない場合Noneを返す"""
    from app.core.authenticator import Authenticator

    mock_page.is_visible = AsyncMock(return_value=False)

    auth = Authenticator(mock_page)
    flow = await auth._detect_login_flow()

    assert flow is None
