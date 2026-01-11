"""
ParallelOrderProcessorのテスト
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.should_process.return_value = True
    db.get_order_status.return_value = None
    return db


@pytest.fixture
def mock_pages():
    """3つのモックページを作成"""
    pages = []
    for _ in range(3):
        page = AsyncMock()
        page.url = "https://order.my.rakuten.co.jp/"
        pages.append(page)
    return pages


def test_worker_count(mock_pages, mock_db):
    """ワーカー数が正しく設定される"""
    from app.core.parallel_processor import ParallelOrderProcessor

    processor = ParallelOrderProcessor(mock_pages, mock_db)

    assert processor.worker_count == 3


@pytest.mark.asyncio
async def test_go_to_next_page_success(mock_pages, mock_db):
    """次ページ遷移成功"""
    from app.core.parallel_processor import ParallelOrderProcessor

    processor = ParallelOrderProcessor(mock_pages, mock_db)

    mock_btn = AsyncMock()
    mock_btn.is_visible = AsyncMock(return_value=True)
    mock_btn.is_enabled = AsyncMock(return_value=True)
    mock_btn.get_attribute = AsyncMock(
        side_effect=lambda k: "" if k == "class" else None
    )

    mock_locator = MagicMock()
    mock_locator.first = mock_btn
    mock_locator.all = AsyncMock(return_value=[mock_btn])
    mock_pages[0].locator = MagicMock(return_value=mock_locator)

    result = await processor._go_to_next_page(mock_pages[0])

    assert result is True
    mock_btn.click.assert_called_once()


@pytest.mark.asyncio
async def test_go_to_next_page_no_button(mock_pages, mock_db):
    """次ページボタンがない"""
    from app.core.parallel_processor import ParallelOrderProcessor

    processor = ParallelOrderProcessor(mock_pages, mock_db)

    mock_btn = AsyncMock()
    mock_btn.is_visible = AsyncMock(return_value=False)

    mock_locator = MagicMock()
    mock_locator.first = mock_btn
    mock_pages[0].locator = MagicMock(return_value=mock_locator)

    result = await processor._go_to_next_page(mock_pages[0])

    assert result is False


@pytest.mark.asyncio
async def test_navigate_to_detail_success(mock_pages, mock_db):
    """詳細ページ遷移成功"""
    from app.core.parallel_processor import ParallelOrderProcessor

    processor = ParallelOrderProcessor(mock_pages, mock_db)

    mock_link = AsyncMock()
    mock_link.is_visible = AsyncMock(return_value=True)

    mock_locator = MagicMock()
    mock_locator.first = mock_link
    mock_pages[0].locator = MagicMock(return_value=mock_locator)

    result = await processor._navigate_to_detail(mock_pages[0], "12345")

    assert result is True
    mock_link.click.assert_called_once()


@pytest.mark.asyncio
async def test_navigate_to_detail_not_found(mock_pages, mock_db):
    """詳細リンクが見つからない"""
    from app.core.parallel_processor import ParallelOrderProcessor

    processor = ParallelOrderProcessor(mock_pages, mock_db)

    mock_link = AsyncMock()
    mock_link.is_visible = AsyncMock(return_value=False)

    mock_locator = MagicMock()
    mock_locator.first = mock_link
    mock_pages[0].locator = MagicMock(return_value=mock_locator)

    result = await processor._navigate_to_detail(mock_pages[0], "12345")

    assert result is False
