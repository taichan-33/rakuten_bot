"""
PageUtilsのテスト
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_page():
    page = AsyncMock()
    page.url = "https://example.com"
    return page


@pytest.mark.asyncio
async def test_wait_and_click_success(mock_page):
    """wait_and_click: 成功ケース"""
    from app.utils.page_utils import PageUtils

    mock_locator = AsyncMock()
    mock_locator.wait_for = AsyncMock()
    mock_locator.click = AsyncMock()

    mock_page.locator = MagicMock(return_value=MagicMock(first=mock_locator))

    result = await PageUtils.wait_and_click(mock_page, "button#test")

    assert result is True
    mock_locator.wait_for.assert_called_once()
    mock_locator.click.assert_called_once()


@pytest.mark.asyncio
async def test_wait_and_click_timeout(mock_page):
    """wait_and_click: タイムアウトで失敗"""
    from app.utils.page_utils import PageUtils

    mock_locator = AsyncMock()
    mock_locator.wait_for = AsyncMock(side_effect=Exception("Timeout"))

    mock_page.locator = MagicMock(return_value=MagicMock(first=mock_locator))

    result = await PageUtils.wait_and_click(mock_page, "button#test")

    assert result is False


@pytest.mark.asyncio
async def test_find_visible_element_found(mock_page):
    """find_visible_element: 要素が見つかる"""
    from app.utils.page_utils import PageUtils

    mock_locator = AsyncMock()
    mock_locator.is_visible = AsyncMock(return_value=True)

    mock_page.locator = MagicMock(return_value=MagicMock(first=mock_locator))

    result = await PageUtils.find_visible_element(mock_page, ["#btn1", "#btn2"])

    assert result is not None


@pytest.mark.asyncio
async def test_find_visible_element_not_found(mock_page):
    """find_visible_element: 要素が見つからない"""
    from app.utils.page_utils import PageUtils

    mock_locator = AsyncMock()
    mock_locator.is_visible = AsyncMock(return_value=False)

    mock_page.locator = MagicMock(return_value=MagicMock(first=mock_locator))

    result = await PageUtils.find_visible_element(mock_page, ["#btn1", "#btn2"])

    assert result is None


@pytest.mark.asyncio
async def test_safe_fill_success(mock_page):
    """safe_fill: 成功ケース"""
    from app.utils.page_utils import PageUtils

    mock_locator = AsyncMock()
    mock_locator.wait_for = AsyncMock()
    mock_locator.fill = AsyncMock()

    mock_page.locator = MagicMock(return_value=MagicMock(first=mock_locator))

    result = await PageUtils.safe_fill(mock_page, "input#email", "test@example.com")

    assert result is True
    mock_locator.fill.assert_called_once_with("test@example.com")


@pytest.mark.asyncio
async def test_safe_fill_timeout(mock_page):
    """safe_fill: タイムアウトで失敗"""
    from app.utils.page_utils import PageUtils

    mock_locator = AsyncMock()
    mock_locator.wait_for = AsyncMock(side_effect=Exception("Timeout"))

    mock_page.locator = MagicMock(return_value=MagicMock(first=mock_locator))

    result = await PageUtils.safe_fill(mock_page, "input#email", "test@example.com")

    assert result is False
