"""
OrderHandlerのテスト
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.models.order_status import OrderStatus


@pytest.fixture
def mock_page():
    return AsyncMock()


# ===== StandardOrderHandler Tests =====


@pytest.mark.asyncio
async def test_standard_handler_parse_order_id_query(mock_page):
    """StandardHandler: クエリパラメータから注文番号を抽出"""
    from app.handlers import StandardOrderHandler

    handler = StandardOrderHandler(mock_page)
    href = "https://order.my.rakuten.co.jp/?order_number=285657-20251225-0036448401"
    assert handler._parse_order_id_from_href(href) == "285657-20251225-0036448401"


@pytest.mark.asyncio
async def test_standard_handler_parse_order_id_path(mock_page):
    """StandardHandler: パスから注文番号を抽出"""
    from app.handlers import StandardOrderHandler

    handler = StandardOrderHandler(mock_page)
    href = "/purchase-history/detail/285657-20251225-0036448401"
    assert handler._parse_order_id_from_href(href) == "285657-20251225-0036448401"


@pytest.mark.asyncio
async def test_standard_handler_returns_empty_for_invalid_id(mock_page):
    """StandardHandler: 無効な注文番号は除外する"""
    from app.handlers import StandardOrderHandler

    handler = StandardOrderHandler(mock_page)
    # 数字だけだが短い
    href = "https://order.my.rakuten.co.jp/?order_number=000031092"
    assert handler._parse_order_id_from_href(href) == ""

    # 記号がおかしい
    href = "https://order.my.rakuten.co.jp/?order_number=abc-def"
    assert handler._parse_order_id_from_href(href) == ""


@pytest.mark.asyncio
async def test_standard_handler_returns_no_receipt_when_no_section(mock_page):
    """StandardHandler: 領収書セクションがない場合NO_RECEIPTを返す"""
    from app.handlers import StandardOrderHandler

    handler = StandardOrderHandler(mock_page)

    mock_element = AsyncMock()
    mock_element.is_visible = AsyncMock(return_value=False)

    mock_locator = MagicMock()
    mock_locator.first = mock_element
    mock_page.locator = MagicMock(return_value=mock_locator)

    result = await handler.issue_receipt("111111-20250101-1111111111")

    assert result.status == OrderStatus.NO_RECEIPT


# ===== BooksOrderHandler Tests =====


@pytest.mark.asyncio
async def test_books_handler_returns_no_receipt_when_no_link(mock_page):
    """BooksHandler: 領収書リンクがない場合NO_RECEIPTを返す"""
    from app.handlers import BooksOrderHandler

    handler = BooksOrderHandler(mock_page)

    mock_element = AsyncMock()
    mock_element.is_visible = AsyncMock(return_value=False)

    mock_locator = MagicMock()
    mock_locator.first = mock_element
    mock_page.locator = MagicMock(return_value=mock_locator)
    mock_page.wait_for_load_state = AsyncMock()
    mock_page.url = "http://example.com"  # URLを文字列として設定

    result = await handler.issue_receipt("111111-20250101-1111111111")

    assert result.status == OrderStatus.NO_RECEIPT


@pytest.mark.asyncio
async def test_books_handler_issue_receipt_success(mock_page):
    """BooksHandler: 領収書発行成功（新フロー）"""
    import asyncio
    from app.handlers import BooksOrderHandler
    from app.models.order_status import OrderStatus

    handler = BooksOrderHandler(mock_page)

    # 非同期戻り値用のヘルパー
    async def async_return(value):
        return value

    # 1. 共通の要素モック
    element_mock = MagicMock()
    element_mock.is_visible = MagicMock(
        side_effect=lambda *args, **kwargs: async_return(True)
    )
    element_mock.click = MagicMock(
        side_effect=lambda *args, **kwargs: async_return(None)
    )

    # page.locator(...).first
    locator_mock = MagicMock()
    locator_mock.first = element_mock
    # mock_page.locator は AsyncMock なので、同期的に値を返す MagicMock に置き換える
    mock_page.locator = MagicMock(return_value=locator_mock)

    # expect_popup のモック
    popup_page = MagicMock()
    popup_page.url = "https://example.com/receipt.pdf"
    popup_page.wait_for_load_state = MagicMock(
        side_effect=lambda *args, **kwargs: async_return(None)
    )
    popup_page.close = MagicMock(side_effect=lambda *args, **kwargs: async_return(None))

    # response
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.body = MagicMock(
        side_effect=lambda *args, **kwargs: async_return(b"%PDF-1.4...")
    )
    popup_page.request.get = MagicMock(
        side_effect=lambda *args, **kwargs: async_return(mock_response)
    )

    # wait_for_popup context manager - ここが重要
    # valueプロパティが awaitable である必要がある
    popup_info = MagicMock()
    # async with ... as popup_info: await popup_info.value
    # value を await すると page が返るようにする
    future = asyncio.Future()
    future.set_result(popup_page)
    popup_info.value = future

    mock_context = MagicMock()
    mock_context.__aenter__ = MagicMock(
        side_effect=lambda *args, **kwargs: async_return(popup_info)
    )
    mock_context.__aexit__ = MagicMock(
        side_effect=lambda *args, **kwargs: async_return(None)
    )
    # mock_page.expect_popup も AsyncMock なので MagicMock に置き換える
    mock_page.expect_popup = MagicMock(return_value=mock_context)

    # wait_for_load_state
    mock_page.wait_for_load_state = MagicMock(
        side_effect=lambda *args, **kwargs: async_return(None)
    )

    # open のモック
    from unittest.mock import mock_open, patch

    with patch("builtins.open", mock_open()), patch(
        "os.path.join", return_value="receipt_222222-20250101-2222222222.pdf"
    ), patch("app.config.Config.DOWNLOAD_DIR", "/tmp"):

        # 実行
        result = await handler.issue_receipt("222222-20250101-2222222222")

    assert result.status == OrderStatus.DONE
    assert "receipt_222222-20250101-2222222222.pdf" in result.filename


# ===== Factory Tests =====


def test_factory_returns_books_handler_for_books_url():
    """Factory: ブックスURLでBooksHandlerを返す"""
    from app.handlers import OrderHandlerFactory, BooksOrderHandler

    mock_page = MagicMock()
    mock_page.url = "https://books.rakuten.co.jp/mypage/"

    handler = OrderHandlerFactory.create(mock_page)
    assert isinstance(handler, BooksOrderHandler)


def test_factory_returns_standard_handler_for_other_url():
    """Factory: 通常URLでStandardHandlerを返す"""
    from app.handlers import OrderHandlerFactory, StandardOrderHandler

    mock_page = MagicMock()
    mock_page.url = "https://order.my.rakuten.co.jp/"

    handler = OrderHandlerFactory.create(mock_page)
    assert isinstance(handler, StandardOrderHandler)
