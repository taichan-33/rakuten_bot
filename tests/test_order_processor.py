"""
OrderProcessorのテスト
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, PropertyMock


@pytest.fixture
def mock_page():
    page = AsyncMock()
    type(page).url = PropertyMock(return_value="https://order.my.rakuten.co.jp/")
    return page


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.should_process.return_value = True
    db.get_order_status.return_value = None
    return db


@pytest.mark.asyncio
async def test_handles_no_orders(mock_page, mock_db):
    """注文なしを正しく処理する"""
    from app.core.order_processor import OrderProcessor

    processor = OrderProcessor(mock_page, mock_db)

    mock_locator = MagicMock()
    mock_locator.count = AsyncMock(return_value=0)
    mock_page.locator = MagicMock(return_value=mock_locator)

    processed, skipped, errors = await processor._process_current_page()
    assert processed == 0
    assert skipped == 0
    assert errors == 0


@pytest.mark.asyncio
async def test_go_to_next_page_success(mock_page, mock_db):
    """次のページに遷移成功"""
    from app.core.order_processor import OrderProcessor

    processor = OrderProcessor(mock_page, mock_db)

    mock_btn = AsyncMock()
    mock_btn.is_visible = AsyncMock(return_value=True)
    mock_btn.is_enabled = AsyncMock(return_value=True)
    mock_btn.get_attribute = AsyncMock(
        side_effect=lambda k: "" if k == "class" else None
    )

    mock_locator = MagicMock()
    mock_locator.first = mock_btn
    mock_locator.all = AsyncMock(return_value=[mock_btn])
    mock_page.locator = MagicMock(return_value=mock_locator)

    assert await processor._go_to_next_page() is True
    mock_btn.click.assert_called_once()


@pytest.mark.asyncio
async def test_go_to_next_page_no_button(mock_page, mock_db):
    """次ページボタンがない場合"""
    from app.core.order_processor import OrderProcessor

    processor = OrderProcessor(mock_page, mock_db)

    mock_btn = AsyncMock()
    mock_btn.is_visible = AsyncMock(return_value=False)

    mock_locator = MagicMock()
    mock_locator.first = mock_btn
    mock_page.locator = MagicMock(return_value=mock_locator)

    assert await processor._go_to_next_page() is False
