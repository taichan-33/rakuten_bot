import requests
import json
from datetime import datetime
from app.utils.logger import log_info, log_error


class SlackNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send_report(self, summary: dict, csv_path: str = None):
        """
        実行結果サマリーをSlackに送信する
        """
        if not self.webhook_url:
            log_info(
                "Slack Webhook URLがお知らせされていません。通知をスキップします。"
            )
            return

        try:
            # 集計
            total = sum(summary.values())
            done = summary.get("DONE", 0)
            no_receipt = summary.get("NO_RECEIPT", 0)
            skipped = summary.get(
                "PENDING", 0
            )  # PENDINGは実際には完了時のstatusには残らないはずだが...
            # DBManager.get_summary()の実装依存。DONE, NO_RECEIPT, RETRY, ERRORあたり。
            retry = summary.get("RETRY", 0)
            error = summary.get("ERROR", 0)

            # PENDING除外して計算したほうがいいかもだが、simpleに
            success_rate = (done / total * 100) if total > 0 else 0.0

            # メッセージ作成
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = {
                "text": f"bot execution completed at {timestamp}",
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "📊 RakutenBot 実行レポート",
                            "emoji": True,
                        },
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*処理合計:*\n{total} 件"},
                            {
                                "type": "mrkdwn",
                                "text": f"*成功率:*\n{success_rate:.1f}%",
                            },
                        ],
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*✅ 成功 (保存):*\n{done} 件"},
                            {
                                "type": "mrkdwn",
                                "text": f"*🚫 発行不可 (なし):*\n{no_receipt} 件",
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*🔄 リトライ待ち:*\n{retry} 件",
                            },
                            {"type": "mrkdwn", "text": f"*❌ エラー:*\n{error} 件"},
                        ],
                    },
                ],
            }

            if csv_path:
                message["blocks"].append(
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": f"📄 *CSVレポート出力先:* `{csv_path}`\n(※Webhookではファイル添付不可のためパスのみ表示)",
                            }
                        ],
                    }
                )

            response = requests.post(
                self.webhook_url,
                data=json.dumps(message),
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                log_info("Slack通知を送信しました")
            else:
                log_error(f"Slack通知送信失敗: {response.status_code} {response.text}")

        except Exception as e:
            log_error(f"Slack通知処理中にエラーが発生しました: {e}")
