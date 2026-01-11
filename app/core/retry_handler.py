"""
リトライ処理を担当するユーティリティクラス
責務: リトライロジックの抽象化
"""

import asyncio
from typing import Callable, Optional
from app.utils.logger import log_info, log_debug, log_warning


class RetryHandler:
    """リトライ処理を汎用的に扱うクラス"""

    def __init__(self, max_attempts: int = 3, delay_seconds: float = 2.0):
        self.max_attempts = max_attempts
        self.delay_seconds = delay_seconds

    async def execute(
        self,
        action: Callable,
        success_check: Optional[Callable] = None,
        action_name: str = "処理",
    ) -> bool:
        """
        リトライ付きで非同期アクションを実行

        Args:
            action: 実行する非同期関数
            success_check: 成功判定を行う非同期関数 (Trueで成功)
            action_name: ログ出力用の処理名

        Returns:
            bool: 成功したかどうか
        """
        for attempt in range(1, self.max_attempts + 1):
            try:
                log_info(f"{action_name} 試行 {attempt}/{self.max_attempts}")
                await action()

                if success_check:
                    await asyncio.sleep(self.delay_seconds)
                    if await success_check():
                        log_info(f"{action_name} 成功")
                        return True
                    else:
                        log_warning(f"{action_name} 失敗、リトライします...")
                else:
                    # 成功判定がない場合は実行完了=成功とみなす
                    return True

            except Exception as e:
                log_warning(f"{action_name} でエラー: {e}")
                if attempt < self.max_attempts:
                    log_debug(f"{self.delay_seconds}秒後にリトライします...")
                    await asyncio.sleep(self.delay_seconds)

        log_warning(
            f"{action_name} は {self.max_attempts} 回試行しましたが失敗しました"
        )
        return False
