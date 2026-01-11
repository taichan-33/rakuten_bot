"""
LoginFlowsのテスト
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock


@pytest.fixture
def mock_page():
    page = AsyncMock()
    type(page).url = PropertyMock(return_value="https://order.my.rakuten.co.jp/")
    return page


@pytest.mark.asyncio
async def test_global_id_flow_fills_credentials(mock_page):
    """GlobalIdLoginFlowがユーザー名とパスワードを入力する"""
    from app.core.login_flows import GlobalIdLoginFlow

    with patch("app.core.login_flows.Config") as MockConfig:
        MockConfig.USER_ID = "test_user"
        MockConfig.PASSWORD = "test_pass"

        flow = GlobalIdLoginFlow(mock_page)
        mock_page.wait_for_selector = AsyncMock()
        mock_page.locator = MagicMock(
            return_value=AsyncMock(is_visible=AsyncMock(return_value=False))
        )

        await flow.execute()

        mock_page.fill.assert_any_call('input[name="username"]', "test_user")
        mock_page.fill.assert_any_call('input[name="password"]', "test_pass")


@pytest.mark.asyncio
async def test_legacy_flow_fills_credentials(mock_page):
    """LegacyLoginFlowがu/pフィールドに入力する"""
    from app.core.login_flows import LegacyLoginFlow

    mock_page.is_visible = AsyncMock(return_value=True)

    with patch("app.core.login_flows.Config") as MockConfig:
        MockConfig.USER_ID = "test_user"
        MockConfig.PASSWORD = "test_pass"

        flow = LegacyLoginFlow(mock_page)
        await flow.execute()

        mock_page.fill.assert_any_call('input[name="u"]', "test_user")
        mock_page.fill.assert_any_call('input[name="p"]', "test_pass")
