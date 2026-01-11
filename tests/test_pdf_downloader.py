"""
PdfDownloaderのテスト
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_page():
    page = AsyncMock()
    page.url = "https://example.com/receipt.pdf"

    # context.pages をモック
    mock_context = MagicMock()
    mock_context.pages = [page]
    page.context = mock_context

    return page


@pytest.mark.asyncio
async def test_download_from_page_success(mock_page):
    """ページからPDFダウンロード成功"""
    from app.utils.pdf_downloader import PdfDownloader

    # 新しいタブをシミュレート
    new_page = AsyncMock()
    new_page.url = "https://example.com/receipt.pdf"
    new_page.wait_for_load_state = AsyncMock()

    mock_response = AsyncMock()
    mock_response.ok = True
    mock_response.body = AsyncMock(return_value=b"%PDF-1.4 test content")

    new_page.context = MagicMock()
    new_page.context.request = AsyncMock()
    new_page.context.request.get = AsyncMock(return_value=mock_response)
    new_page.close = AsyncMock()

    downloader = PdfDownloader(mock_page)

    with patch("app.utils.pdf_downloader.Config") as mock_config:
        mock_config.DOWNLOAD_DIR = "/tmp"

        with patch("builtins.open", MagicMock()):
            result = await downloader._download_from_page(new_page, "test-order-123")

    assert result == "receipt_test-order-123.pdf"
    new_page.close.assert_called_once()


@pytest.mark.asyncio
async def test_download_from_new_tab_no_new_tab(mock_page):
    """新しいタブが開かない場合"""
    from app.utils.pdf_downloader import PdfDownloader

    # ページ数が変わらない
    mock_page.context.pages = [mock_page]

    downloader = PdfDownloader(mock_page)

    async def click_action():
        pass

    result = await downloader.download_from_new_tab(
        click_action, "test-order-123", check_modal=False
    )

    assert result == ""


@pytest.mark.asyncio
async def test_handle_modal(mock_page):
    """モーダル処理のテスト"""
    from app.utils.pdf_downloader import PdfDownloader

    mock_btn = AsyncMock()
    mock_btn.click = AsyncMock()

    with patch("app.utils.pdf_downloader.PageUtils") as mock_utils:
        mock_utils.find_visible_element = AsyncMock(return_value=mock_btn)

        downloader = PdfDownloader(mock_page)
        await downloader._handle_modal()

        mock_btn.click.assert_called_once()
