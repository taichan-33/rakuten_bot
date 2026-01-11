"""
RetryHandlerのテスト
"""

import pytest
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_success_first_try():
    """初回成功で終了する"""
    from app.core.retry_handler import RetryHandler

    handler = RetryHandler(max_attempts=3, delay_seconds=0.01)
    action = AsyncMock()
    success_check = AsyncMock(return_value=True)

    result = await handler.execute(action, success_check, "テスト")

    assert result is True
    assert action.call_count == 1


@pytest.mark.asyncio
async def test_retries_on_failure():
    """失敗時にリトライする"""
    from app.core.retry_handler import RetryHandler

    handler = RetryHandler(max_attempts=3, delay_seconds=0.01)
    action = AsyncMock()
    success_check = AsyncMock(side_effect=[False, False, True])

    result = await handler.execute(action, success_check, "テスト")

    assert result is True
    assert action.call_count == 3


@pytest.mark.asyncio
async def test_gives_up_after_max_attempts():
    """最大試行回数後に諦める"""
    from app.core.retry_handler import RetryHandler

    handler = RetryHandler(max_attempts=2, delay_seconds=0.01)
    action = AsyncMock()
    success_check = AsyncMock(return_value=False)

    result = await handler.execute(action, success_check, "テスト")

    assert result is False
    assert action.call_count == 2


@pytest.mark.asyncio
async def test_handles_exception():
    """例外時にリトライする"""
    from app.core.retry_handler import RetryHandler

    handler = RetryHandler(max_attempts=3, delay_seconds=0.01)
    action = AsyncMock(side_effect=[Exception("Error"), Exception("Error"), None])

    result = await handler.execute(action, action_name="テスト")

    assert result is True
    assert action.call_count == 3
