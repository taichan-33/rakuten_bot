from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from app.utils.logger import log_info, log_error
from datetime import datetime
import os


class SlackService:
    """Slack通知サービス"""

    def __init__(self, token: str, channel_id: str):
        self.client = WebClient(token=token)
        self.channel_id = channel_id

    def send_report(self, summary: dict, csv_path: str = None) -> bool:
        """
        レポートを送信する（CSVファイルがある場合は添付）
        """
        if not self.client.token or not self.channel_id:
            log_info(
                "Slack設定（Token/Channel）が不足しているため通知をスキップします。"
            )
            return False

        try:
            # メッセージ作成
            message_text = self._create_message_text(summary)

            if csv_path and os.path.exists(csv_path):
                # ファイルアップロード
                log_info(f"CSVファイルをSlackにアップロード中: {csv_path}")
                self.client.files_upload_v2(
                    channel=self.channel_id,
                    file=csv_path,
                    title=f"RakutenBot Report {datetime.now().strftime('%Y-%m-%d')}",
                    initial_comment=message_text,
                )
            else:
                # テキストのみ送信
                self.client.chat_postMessage(channel=self.channel_id, text=message_text)

            log_info("Slack通知を送信しました")
            return True

        except SlackApiError as e:
            log_error(f"Slack APIエラー: {e.response['error']}")
            return False
        except Exception as e:
            log_error(f"Slack通知処理中にエラーが発生しました: {e}")
            return False

    def _create_message_text(self, summary: dict) -> str:
        """集計結果からメッセージテキストを作成"""
        total = sum(summary.values())
        done = summary.get("DONE", 0)
        no_receipt = summary.get("NO_RECEIPT", 0)
        retry = summary.get("RETRY", 0)
        error = summary.get("ERROR", 0)

        success_rate = (done / total * 100) if total > 0 else 0.0
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        lines = [
            f"📊 *RakutenBot 実行レポート* ({timestamp})",
            f"処理合計: {total} 件 (成功率: {success_rate:.1f}%)",
            "",
            f"✅ 成功 (保存): {done} 件",
            f"🚫 発行不可: {no_receipt} 件",
            f"🔄 リトライ待ち: {retry} 件",
            f"❌ エラー: {error} 件",
        ]

        return "\n".join(lines)
